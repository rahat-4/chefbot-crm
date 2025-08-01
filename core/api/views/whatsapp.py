import logging
import json
import time
from typing import Dict, Any
from openai import OpenAI
from datetime import datetime, timedelta

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings

from apps.organization.models import WhatsappBot
from apps.restaurant.models import Client, Reservation, RestaurantTable, Menu
from apps.restaurant.choices import ReservationStatus, TableStatus, MenuStatus

from common.whatsapp import send_whatsapp_reply
from common.crypto import decrypt_data


logger = logging.getLogger(__name__)


@csrf_exempt
def whatsapp_bot(request):
    """Main WhatsApp bot endpoint"""
    whatsapp_number = request.POST.get("From", "")
    incoming_message = request.POST.get("Body", "").strip()
    twilio_number = request.POST.get("To", "")
    twilio_sid = request.POST.get("AccountSid", "")

    if not (twilio_sid and twilio_number and whatsapp_number and incoming_message):
        return JsonResponse({"status": "error", "message": "Missing required data"})

    try:
        bot = WhatsappBot.objects.filter(twilio_number=twilio_number).first()
        if not bot:
            logger.error(f"No bot found for Twilio number: {twilio_number}")
            return JsonResponse({"status": "error", "message": "Bot not found"})

        # Decrypt credentials
        openai_key = decrypt_data(bot.openai_key, settings.CRYPTO_PASSWORD)
        openai_client = OpenAI(api_key=openai_key)
        assistant_id = decrypt_data(bot.assistant_id, settings.CRYPTO_PASSWORD)
        twilio_auth_token = decrypt_data(
            bot.twilio_auth_token, settings.CRYPTO_PASSWORD
        )

        # Get or create client
        customer, created = Client.objects.get_or_create(
            whatsapp_number=whatsapp_number, defaults={"organization": bot.organization}
        )

        # Create thread for new customers
        if created or not customer.thread_id:
            thread = openai_client.beta.threads.create()
            customer.thread_id = thread.id
            customer.save()

        # Check for active runs and cancel them if necessary
        cancel_active_runs(openai_client, customer.thread_id)

        # Add user message to thread
        openai_client.beta.threads.messages.create(
            thread_id=customer.thread_id, role="user", content=incoming_message
        )

        # Create and process run
        run = openai_client.beta.threads.runs.create(
            thread_id=customer.thread_id, assistant_id=assistant_id
        )

        # Process the run with improved error handling
        reply = process_assistant_run(openai_client, customer, run, bot.organization)

        if reply:
            # Send reply via WhatsApp
            send_result = send_whatsapp_reply(
                whatsapp_number, reply, twilio_sid, twilio_auth_token, twilio_number
            )

            if send_result:
                logger.info("Reply sent successfully")
                return JsonResponse({"status": "ok", "reply": reply})
            else:
                logger.error("Failed to send WhatsApp reply")

    except Exception as e:
        logger.error(f"Error in whatsapp_bot: {str(e)}")

    # Fallback response
    fallback_message = "⚠️ Sorry, something went wrong. Please try again."
    try:
        send_whatsapp_reply(
            whatsapp_number,
            fallback_message,
            twilio_sid,
            twilio_auth_token,
            twilio_number,
        )
    except Exception as e:
        logger.error(f"Failed to send fallback message: {str(e)}")

    return JsonResponse({"status": "ok", "fallback": True})


def cancel_active_runs(openai_client: OpenAI, thread_id: str):
    """Cancel any active runs on the thread"""
    try:
        runs = openai_client.beta.threads.runs.list(thread_id=thread_id, limit=5)

        for run in runs.data:
            if run.status in ["queued", "in_progress", "requires_action"]:
                logger.info(f"Cancelling active run: {run.id}")
                try:
                    openai_client.beta.threads.runs.cancel(
                        thread_id=thread_id, run_id=run.id
                    )
                    # Wait a bit for cancellation to process
                    time.sleep(0.5)
                except Exception as e:
                    logger.warning(f"Failed to cancel run {run.id}: {str(e)}")

    except Exception as e:
        logger.warning(f"Error checking for active runs: {str(e)}")


def process_assistant_run(
    openai_client: OpenAI, customer: Client, run, organization
) -> str:
    """Process the assistant run and return the response"""
    max_iterations = 30
    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        try:
            run_status = openai_client.beta.threads.runs.retrieve(
                thread_id=customer.thread_id, run_id=run.id
            )
        except Exception as e:
            logger.error(f"Error retrieving run status: {str(e)}")
            return None

        logger.info(
            f"Assistant run status: {run_status.status} (iteration {iteration})"
        )

        if run_status.status == "completed":
            logger.info("Assistant run completed")
            return get_assistant_response(openai_client, customer.thread_id)

        elif run_status.status == "requires_action":
            logger.info("Processing required actions")

            if not handle_required_actions(
                openai_client, customer, run_status, organization
            ):
                logger.error("Failed to handle required actions")
                return None

        elif run_status.status in ["failed", "cancelled", "expired"]:
            logger.error(f"Run failed with status: {run_status.status}")
            return None

        elif run_status.status in ["queued", "in_progress"]:
            # Wait before checking again
            time.sleep(1)
        else:
            logger.warning(f"Unknown run status: {run_status.status}")
            time.sleep(1)

    logger.error(f"Run exceeded maximum iterations ({max_iterations})")
    return None


def handle_required_actions(
    openai_client: OpenAI, customer: Client, run_status, organization
) -> bool:
    """Handle required actions and submit tool outputs"""
    if not (
        run_status.required_action and run_status.required_action.submit_tool_outputs
    ):
        return False

    tool_outputs = []

    for call in run_status.required_action.submit_tool_outputs.tool_calls:
        logger.info(f"Processing tool call: {call.function.name}")

        try:
            if call.function.name == "book_table":
                result = handle_book_table(call, organization, customer)
                logger.info(f"Book table result: {result}")
            elif call.function.name == "get_menu_items":
                result = handle_get_menu_items(call, organization)
                logger.info(f"Get menu items result: {result}")
            elif call.function.name == "add_menu_to_reservation":
                result = handle_add_menu_to_reservation(call, organization)
                logger.info(f"Add menu to reservation result: {result}")
            else:
                result = {"error": f"Unknown function: {call.function.name}"}
                logger.warning(f"Unknown function called: {call.function.name}")

            tool_outputs.append({"tool_call_id": call.id, "output": json.dumps(result)})

        except Exception as e:
            logger.error(f"Error processing tool call {call.function.name}: {str(e)}")
            tool_outputs.append(
                {
                    "tool_call_id": call.id,
                    "output": json.dumps({"error": f"Tool execution failed: {str(e)}"}),
                }
            )

    # Submit tool outputs
    try:
        openai_client.beta.threads.runs.submit_tool_outputs(
            thread_id=customer.thread_id,
            run_id=run_status.id,
            tool_outputs=tool_outputs,
        )
        return True
    except Exception as e:
        logger.error(f"Error submitting tool outputs: {str(e)}")
        return False


def get_assistant_response(openai_client: OpenAI, thread_id: str) -> str:
    """Get the latest assistant response from the thread"""
    try:
        messages = openai_client.beta.threads.messages.list(
            thread_id=thread_id, limit=10
        )

        for message in messages.data:
            if (
                message.role == "assistant"
                and message.content
                and len(message.content) > 0
            ):
                if message.content[0].type == "text":
                    reply = message.content[0].text.value
                    logger.info(f"Assistant reply: {reply}")
                    return reply

        logger.warning("No assistant text response found")
        return None

    except Exception as e:
        logger.error(f"Error getting assistant response: {str(e)}")
        return None


def handle_book_table(call, organization, customer: Client) -> Dict[str, Any]:
    """Handle book_table tool call"""
    try:
        args = json.loads(call.function.arguments)
        logger.info(f"Book table arguments: {args}")

        # Extract required data
        customer_name = args.get("customer_name")
        phone_number = args.get("phone_number")
        reservation_date = args.get("date")
        reservation_time = args.get("time")
        guests = args.get("guests")

        # Extract optional data
        special_occasion = args.get("special_occasion")
        preferred_position = args.get("preferred_position")
        table_category = args.get("table_category")
        allergens = args.get("allergens", [])
        birthday = args.get("birthday")
        special_notes = args.get("special_notes")

        # Validate required fields
        if not all(
            [customer_name, phone_number, reservation_date, reservation_time, guests]
        ):
            return {
                "error": "Missing required booking information (name, phone, date, time, guests)"
            }

        # Update customer information
        customer.name = customer_name
        customer.save()

        # Validate and parse date/time
        try:
            reservation_date = datetime.strptime(reservation_date, "%Y-%m-%d").date()
            reservation_time = datetime.strptime(reservation_time, "%H:%M").time()
        except ValueError as e:
            return {"error": f"Invalid date or time format: {str(e)}"}

        # Validate guest count
        try:
            guests = int(guests)
            if guests <= 0:
                return {"error": "Number of guests must be positive"}
        except (ValueError, TypeError):
            return {"error": "Invalid number of guests"}

        # Build table filter based on preferences
        table_filter = {
            "organization": organization,
            "capacity__gte": guests,
            "status": TableStatus.AVAILABLE,
        }

        # Add category filter if specified
        if table_category:
            table_filter["category"] = table_category

        # Find suitable tables
        suitable_tables = RestaurantTable.objects.filter(**table_filter).order_by(
            "capacity"
        )

        # If preferred position is specified, try to find tables with that position first
        if preferred_position:
            position_tables = suitable_tables.filter(
                position__icontains=preferred_position
            )
            if position_tables.exists():
                suitable_tables = position_tables

        logger.info(
            f"Found {suitable_tables.count()} suitable tables for {guests} guests"
        )

        if not suitable_tables.exists():
            # Try without category/position filters if none found
            fallback_tables = RestaurantTable.objects.filter(
                organization=organization,
                capacity__gte=guests,
                status=TableStatus.AVAILABLE,
            ).order_by("capacity")

            if fallback_tables.exists():
                suitable_tables = fallback_tables
                logger.info(
                    f"Using fallback search: found {suitable_tables.count()} tables"
                )
            else:
                return {
                    "status": "unavailable",
                    "message": f"No tables available for {guests} guests",
                }

        # Try to find an available table
        for table in suitable_tables:
            if is_table_available(table, reservation_date, reservation_time):
                # Create reservation notes
                notes_parts = []
                if special_occasion:
                    notes_parts.append(f"Special occasion: {special_occasion}")
                if special_notes:
                    notes_parts.append(special_notes)

                reservation_notes = "; ".join(notes_parts)

                # Create the reservation
                reservation = Reservation.objects.create(
                    client=customer,
                    reservation_date=reservation_date,
                    reservation_time=reservation_time,
                    guests=guests,
                    table=table,
                    organization=organization,
                    notes=reservation_notes,
                    reservation_phone=(
                        phone_number
                        if phone_number != customer.whatsapp_number
                        else None
                    ),
                )

                # Update customer information
                update_customer_info(customer, [], allergens, birthday)

                return {
                    "status": "success",
                    "reservation_uid": str(reservation.uid),
                    "table_name": table.name,
                    "table_category": table.category,
                    "table_position": table.position or "Standard seating",
                    "date": str(reservation.reservation_date),
                    "time": str(reservation.reservation_time),
                    "guests": guests,
                    "customer_name": customer_name,
                    "special_occasion": special_occasion or "",
                    "special_notes": reservation_notes,
                }

        # No available tables found
        return {
            "status": "unavailable",
            "message": "No tables available for the selected time. Please try a different time.",
        }

    except Exception as e:
        logger.error(f"Error in handle_book_table: {str(e)}")
        return {"error": f"Booking failed: {str(e)}"}


def handle_get_menu_items(call, organization) -> Dict[str, Any]:
    """Handle get_menu_items tool call"""
    try:
        args = json.loads(call.function.arguments)
        logger.info(f"Get menu items arguments: {args}")

        category = args.get("category")
        classification = args.get("classification")

        if not all([category, classification]):
            return {"error": "Missing category or classification"}

        # Get menu items based on filters
        menu_items = Menu.objects.filter(
            organization=organization,
            category=category,
            classification=classification,
            status=MenuStatus.ACTIVE,
        ).order_by("name")

        if not menu_items.exists():
            return {
                "status": "no_items",
                "message": f"No {classification.lower()} items available in {category.replace('_', ' ').title()} category",
            }

        # Format menu items for display
        items = []
        for item in menu_items:
            allergens_str = ", ".join(item.allergens) if item.allergens else "None"
            ingredients_str = ", ".join(item.ingredients) if item.ingredients else ""

            items.append(
                {
                    "name": item.name,
                    "description": item.description or "",
                    "price": float(item.price),
                    "allergens": allergens_str,
                    "ingredients": ingredients_str,
                    "uid": str(item.uid),
                }
            )

        return {
            "status": "success",
            "category": category.replace("_", " ").title(),
            "classification": classification.title(),
            "items": items,
            "total_items": len(items),
        }

    except Exception as e:
        logger.error(f"Error in handle_get_menu_items: {str(e)}")
        return {"error": f"Failed to get menu items: {str(e)}"}


def handle_add_menu_to_reservation(call, organization) -> Dict[str, Any]:
    """Handle add_menu_to_reservation tool call"""
    try:
        args = json.loads(call.function.arguments)
        logger.info(f"Add menu to reservation arguments: {args}")

        reservation_uid = args.get("reservation_uid")
        menu_items = args.get("menu_items", [])

        if not all([reservation_uid, menu_items]):
            return {"error": "Missing reservation UID or menu items"}

        # Get the reservation
        try:
            reservation = Reservation.objects.get(
                uid=reservation_uid, organization=organization
            )
        except Reservation.DoesNotExist:
            return {"error": "Reservation not found"}

        # Process menu items
        added_items = []
        failed_items = []

        for item_data in menu_items:
            menu_name = item_data.get("menu_name")
            quantity = item_data.get("quantity", 1)

            if not menu_name:
                failed_items.append("Missing menu name")
                continue

            try:
                # Find the menu item
                menu_item = Menu.objects.get(
                    name__iexact=menu_name,
                    organization=organization,
                    status=MenuStatus.ACTIVE,
                )

                # Add to reservation (create multiple entries for quantity > 1)
                for _ in range(quantity):
                    reservation.menus.add(menu_item)

                added_items.append(
                    {
                        "name": menu_item.name,
                        "quantity": quantity,
                        "price": float(menu_item.price),
                        "total_price": float(menu_item.price) * quantity,
                    }
                )

            except Menu.DoesNotExist:
                failed_items.append(f"Menu item '{menu_name}' not found")
                logger.warning(
                    f"Menu item '{menu_name}' not found for organization {organization}"
                )

        # Calculate total
        total_price = sum(item["total_price"] for item in added_items)

        result = {
            "status": "success" if added_items else "failed",
            "reservation_uid": reservation_uid,
            "added_items": added_items,
            "failed_items": failed_items,
            "total_items_added": len(added_items),
            "total_price": total_price,
        }

        if failed_items:
            result["message"] = (
                f"Some items could not be added: {'; '.join(failed_items)}"
            )

        return result

    except Exception as e:
        logger.error(f"Error in handle_add_menu_to_reservation: {str(e)}")
        return {"error": f"Failed to add menu items: {str(e)}"}


def is_table_available(
    table: RestaurantTable, reservation_date, reservation_time
) -> bool:
    """Check if a table is available at the specified date and time"""
    try:
        # Check for conflicting reservations within ±2 hours
        start_time = (
            datetime.combine(reservation_date, reservation_time) - timedelta(hours=2)
        ).time()
        end_time = (
            datetime.combine(reservation_date, reservation_time) + timedelta(hours=2)
        ).time()

        conflicting_reservations = Reservation.objects.filter(
            table=table,
            reservation_date=reservation_date,
            reservation_time__range=(start_time, end_time),
        ).exclude(reservation_status=ReservationStatus.COMPLETED)

        if conflicting_reservations.exists():
            logger.info(
                f"Table {table.name} has {conflicting_reservations.count()} conflicting reservations"
            )
            return False

        return True

    except Exception as e:
        logger.error(f"Error checking table availability: {str(e)}")
        return False


def update_customer_info(
    customer: Client, menu_preferences: list, allergens: list, birthday: str
):
    """Update customer preferences, allergens, and birthday if not already set"""
    try:
        updated = False

        # Update menu preferences (merge with existing preferences)
        if menu_preferences:
            existing_preferences = customer.preferences or []
            # Add new preferences that aren't already in the list
            new_preferences = [
                pref for pref in menu_preferences if pref not in existing_preferences
            ]
            if new_preferences:
                customer.preferences = existing_preferences + new_preferences
                updated = True
                logger.info(f"Added menu preferences: {new_preferences}")

        # Update allergens (merge with existing allergens)
        if allergens:
            existing_allergens = customer.allergens or []
            # Add new allergens that aren't already in the list
            new_allergens = [
                allergen for allergen in allergens if allergen not in existing_allergens
            ]
            if new_allergens:
                customer.allergens = existing_allergens + new_allergens
                updated = True
                logger.info(f"Added allergens: {new_allergens}")

        # Save birthday if valid and not already set
        if birthday and not customer.date_of_birth:
            try:
                customer.date_of_birth = datetime.strptime(birthday, "%Y-%m-%d").date()
                updated = True
                logger.info("Customer birthday updated")
            except ValueError:
                logger.warning(f"Invalid birthday format: {birthday}")

        if updated:
            customer.save()
            logger.info("Customer information updated successfully")

    except Exception as e:
        logger.error(f"Error updating customer info: {str(e)}")
