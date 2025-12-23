import json
import logging
import time
from datetime import datetime, date, timedelta, time as dtime
from openai import OpenAI
from typing import Dict, Any, Optional, List
from collections import Counter


from django.core import serializers

from apps.restaurant.choices import (
    PromotionSentLogStatus,
    ReservationStatus,
    TableStatus,
    MenuStatus,
    ReservationCancelledBy,
)
from apps.restaurant.models import (
    Client,
    Reservation,
    RestaurantTable,
    Menu,
    RestaurantDocument,
    Promotion,
    PromotionSentLog,
    SalesLevel,
)

logger = logging.getLogger(__name__)

logger.info("OpenAI utils loaded")


def cancel_active_runs(openai_client: OpenAI, thread_id: str) -> None:
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
                    time.sleep(0.5)  # Wait for cancellation to process
                except Exception as e:
                    logger.warning(f"Failed to cancel run {run.id}: {str(e)}")

    except Exception as e:
        logger.warning(f"Error checking for active runs: {str(e)}")


def process_assistant_run(
    openai_client: OpenAI,
    customer: Client,
    run,
    organization,
    request,
    twilio_sid,
    twilio_auth_token,
    twilio_number,
    whatsapp_number,
    state: Dict[str, Any],
) -> Optional[str]:
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
                openai_client,
                customer,
                run_status,
                organization,
                request,
                twilio_sid,
                twilio_auth_token,
                twilio_number,
                whatsapp_number,
                state,
            ):
                logger.error("Failed to handle required actions")
                return None

        elif run_status.status in ["failed", "cancelled", "expired"]:
            logger.error(f"Run failed with status: {run_status.status}")
            return None

        elif run_status.status in ["queued", "in_progress"]:
            time.sleep(1)  # Wait before checking again
        else:
            logger.warning(f"Unknown run status: {run_status.status}")
            time.sleep(1)

    logger.error(f"Run exceeded maximum iterations ({max_iterations})")
    return None


def get_assistant_response(openai_client: OpenAI, thread_id: str) -> Optional[str]:
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


def handle_required_actions(
    openai_client: OpenAI,
    customer: Client,
    run_status,
    organization,
    request,
    twilio_sid,
    twilio_auth_token,
    twilio_number,
    whatsapp_number,
    state: Dict[str, Any],
) -> bool:
    """Handle required actions and submit tool outputs"""
    if not (
        run_status.required_action and run_status.required_action.submit_tool_outputs
    ):
        return False

    tool_outputs = []

    for call in run_status.required_action.submit_tool_outputs.tool_calls:
        logger.info(f"Processing tool call: {call.function.name}")

        # try:
        # Route function calls to appropriate handlers
        function_handlers = {
            "get_restaurant_information": lambda: handle_get_restaurant_information(
                call, organization
            ),
            "send_menu_pdf": lambda: handle_send_menu_pdf(
                organization,
                request,
                twilio_sid,
                twilio_auth_token,
                twilio_number,
                whatsapp_number,
                state,
            ),
            "get_menu_items": lambda: handle_get_menu_items(call, organization),
            "get_available_tables": lambda: handle_get_available_tables(
                call, organization
            ),
            "book_table": lambda: handle_book_table(call, organization, customer),
            "add_menu_to_reservation": lambda: handle_add_menu_to_reservation(
                call, organization
            ),
            "reschedule_reservation": lambda: handle_reschedule_reservation(
                call, organization, customer
            ),
            "get_customer_reservations": lambda: handle_get_customer_reservations(
                call, organization, customer
            ),
            "cancel_reservation": lambda: handle_cancel_reservation(
                call, organization, customer
            ),
            "get_priority_menu_items": lambda: handle_get_priority_menu_items(
                call, organization
            ),
            "get_personalized_recommendations": lambda: handle_get_personalized_recommendations(
                call, organization, customer
            ),
            "get_available_promotions": lambda: handle_get_available_promotions(
                call, organization
            ),
            "client_profile_update": lambda: handle_client_profile_update(
                call, customer
            ),
        }

        handler = function_handlers.get(call.function.name)
        if handler:
            result = handler()
            logger.info(f"{call.function.name} result-------------------->: {result}")
            if call.function.name == "send_menu_pdf" and result:
                media_available = True
        else:
            result = {"error": f"Unknown function: {call.function.name}"}
            logger.warning(f"Unknown function called: {call.function.name}")

        tool_outputs.append({"tool_call_id": call.id, "output": json.dumps(result)})

        logger.info(f"Tool outputs: {tool_outputs}")

        # except Exception as e:
        #     logger.error(f"Error processing tool call {call.function.name}: {str(e)}")
        #     tool_outputs.append(
        #         {
        #             "tool_call_id": call.id,
        #             "output": json.dumps({"error": f"Tool execution failed: {str(e)}"}),
        #         }
        #     )

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


def handle_get_restaurant_information(call, organization) -> Dict[str, Any]:
    """Handle get_restaurant_information tool call"""
    try:
        args = json.loads(call.function.arguments)
        query = args.get("query", "all_info").lower()

        # Serialize opening hours
        opening_hours = serializers.serialize("json", organization.opening_hours.all())

        # Build complete restaurant information
        restaurant_info = {
            "name": organization.name,
            "phone": str(organization.phone) if organization.phone else None,
            "email": organization.email,
            "website": organization.website,
            "country": organization.country,
            "city": organization.city,
            "street": organization.street,
            "zip_code": organization.zip_code,
            "opening_hours": opening_hours,
        }

        logger.info(f"Opening hours: {opening_hours}")

        # Filter based on query if specific information requested
        query_mapping = {
            "name": {"name": restaurant_info["name"]},
            "phone_number": {"phone": restaurant_info["phone"]},
            "email": {"email": restaurant_info["email"]},
            "website": {"website": restaurant_info["website"]},
            "address": {
                "street": restaurant_info["street"],
                "city": restaurant_info["city"],
                "zip_code": restaurant_info["zip_code"],
                "country": restaurant_info["country"],
            },
            "location": {
                "street": restaurant_info["street"],
                "city": restaurant_info["city"],
                "country": restaurant_info["country"],
            },
            "opening_hours": {"opening_hours": opening_hours},
            "contact_info": {
                "phone": restaurant_info["phone"],
                "email": restaurant_info["email"],
            },
        }

        if query in query_mapping:
            return {"status": "success", "query": query, **query_mapping[query]}

        # Return all information for 'all_info' or unrecognized queries
        return {"status": "success", "query": "complete_information", **restaurant_info}

    except Exception as e:
        logger.error(f"Error in handle_get_restaurant_information: {str(e)}")
        return {"error": f"Failed to get restaurant information: {str(e)}"}


def handle_client_profile_update(call, customer: Client) -> Dict[str, Any]:
    """Handle client_profile_update tool call"""
    try:
        args = json.loads(call.function.arguments)
        logger.info(f"Client profile update arguments: {args}")

        # Update client profile fields
        updatable_fields = [
            "preferences",
            "allergens",
            "date_of_birth",
            "anniversary_date",
        ]

        for field in updatable_fields:
            if field in args:
                setattr(customer, field, args[field])

        customer.save()

        return {
            "status": "success",
            "message": "Client profile updated successfully",
        }

    except Exception as e:
        logger.error(f"Error in handle_client_profile_update: {str(e)}")
        return {"error": f"Failed to update client profile: {str(e)}"}


def handle_send_menu_pdf(
    organization,
    request,
    account_sid,
    auth_token,
    from_number,
    to_number,
    state: Dict[str, Any],
) -> Optional[dict]:
    """Handle send_menu_pdf tool call"""
    from twilio.rest import Client

    # Menu pdf file
    menus = RestaurantDocument.objects.filter(
        organization=organization, name="menu"
    ).first()

    menu_pdf_url = None
    if menus and menus.file:
        if request:
            menu_pdf_url = request.build_absolute_uri(menus.file.url)
        else:
            menu_pdf_url = menus.file.url

    if menu_pdf_url:
        client = Client(account_sid, auth_token)

        message = client.messages.create(
            media_url=[menu_pdf_url],
            from_=from_number,
            to=to_number,
        )

        state["media_available"] = True

        # Return a JSON-serializable dict instead of MessageInstance
        return {
            "sid": message.sid,
            "status": message.status,
            "to": message.to,
            "from": message.from_,
            "media_url": menu_pdf_url,
        }

    return None


def handle_get_menu_items(call, organization) -> Dict[str, Any]:
    """Handle get_menu_items tool call"""
    try:
        args = json.loads(call.function.arguments)
        logger.info(f"Get all menu arguments: {args}")

        category = args.get("category", None)
        classification = args.get("classification", None)

        if not (category and classification):
            return {"error": "Missing category and classification"}

        # Build menu filter
        menu_filter = {
            "organization": organization,
            "status": MenuStatus.ACTIVE,
            "category": category,
            "classification": classification,
        }

        # Get menu items
        menu_items = Menu.objects.filter(**menu_filter).order_by("category", "name")

        if not menu_items.exists():
            return {
                "status": "no_items",
                "message": f"No {classification.lower()} items available in {category.replace('_', ' ').title()} category",
                "category": category,
                "classification": classification,
            }

        # Format menu items for display
        items = []
        for item in menu_items:
            allergens_str = ", ".join(item.allergens) if item.allergens else "None"
            ingredients_str = (
                ", ".join(item.ingredients) if item.ingredients else "Not specified"
            )

            items.append(
                {
                    "name": item.name,
                    "recommended_combinations": list(
                        item.recommended_combinations.all().values_list(
                            "name", flat=True
                        )
                    ),
                    "description": item.description or "No description available",
                    "price": float(item.price),
                    "ingredients": ingredients_str,
                    "category": item.category,
                    "classification": item.classification,
                    "allergens": allergens_str,
                    "macronutrients": item.macronutrients,
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


def handle_get_available_tables(call, organization) -> Dict[str, Any]:
    """Handle get_available_tables tool call"""
    # try:
    args = json.loads(call.function.arguments)
    logger.info(f"Get available tables arguments: {args}")

    guests = args.get("guests")
    date_str = args.get("date")
    time_str = args.get("time")

    logger.info(f"Guests: {guests}, Date: {date_str}, Time: {time_str}")

    if not date_str:
        return {"error": "Date is required"}

    if not guests:
        return {"error": "Number of guests is required"}

    reservation_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    reservation_time = None

    if time_str:
        reservation_time = datetime.strptime(time_str, "%H:%M").time()

    # Check if requested date is in the past
    if reservation_date < date.today():
        return {"error": "Cannot check availability for past dates"}

    # Check if requested time is in the past
    if reservation_time and reservation_time < datetime.now().time():
        return {"error": "Cannot check availability for past times"}

    # Get all tables for the organization
    all_tables = RestaurantTable.objects.filter(
        organization=organization,
        capacity__gte=guests,
        status=TableStatus.AVAILABLE,
    )

    if not all_tables.exists():
        return {
            "status": "no_tables",
            "message": "No tables available at the restaurant",
        }

    available_tables = []
    busy_tables = []

    for table in all_tables:
        is_available = is_table_available(table, reservation_date, reservation_time)

        table_info = {
            "uid": str(table.uid),
            "name": table.name,
            "time": str(reservation_time) if reservation_time else None,
        }

        if is_available:
            available_tables.append(table_info)
        else:
            busy_tables.append(table_info)

    # If specific time requested but no tables available, suggest alternatives
    suggestions = []
    if time_str and available_tables == []:
        suggestions = get_alternative_time_slots(
            reservation_date, 2, organization, limit=3
        )

    return {
        "status": "success",
        "date": date_str,
        "time": time_str,
        "available_tables": available_tables,
        "total_available": len(available_tables),
        "total_busy": len(busy_tables),
        "suggestions": suggestions if available_tables == [] else [],
    }

    # except Exception as e:
    #     logger.error(f"Error in handle_get_available_tables: {str(e)}")
    #     return {"error": f"Failed to get available tables: {str(e)}"}


def handle_book_table(call, organization, customer: Client) -> Dict[str, Any]:
    """Handle book_table tool call"""
    try:
        args = json.loads(call.function.arguments)
        logger.info(f"Book table arguments: {args}")

        # Extract required data
        reservation_name = args.get("reservation_name")
        reservation_phone = args.get("reservation_phone")
        reservation_date_str = args.get("date")
        reservation_time_str = args.get("time")
        guests = args.get("guests")
        booking_reason = args.get("booking_reason", "")
        reason_for_visit_date = args.get("reason_for_visit_date", "")
        promo_code = args.get("promo_code", "")

        reservation_date = datetime.strptime(reservation_date_str, "%Y-%m-%d").date()
        reservation_time = datetime.strptime(reservation_time_str, "%H:%M").time()

        # For client profile updates
        preferences = args.get("preferences", "")
        allergens = args.get("allergens", "")
        date_of_birth = args.get("date_of_birth", "")
        anniversary_date = args.get("anniversary_date", "")
        if preferences:
            customer.preferences = preferences
            customer.save()
        if allergens:
            customer.allergens = allergens
            customer.save()
        if date_of_birth:
            customer.date_of_birth = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
            customer.save()
        if anniversary_date:
            customer.anniversary_date = datetime.strptime(
                anniversary_date, "%Y-%m-%d"
            ).date()
            customer.save()

        # Extract optional data
        special_notes = args.get("special_notes", "")

        promotion = None
        sales_level_reward = None

        if booking_reason and reason_for_visit_date:
            reason_for_visit_date = datetime.strptime(
                reason_for_visit_date, "%Y-%m-%d"
            ).date()

            if booking_reason.lower() == "birthday":
                customer.date_of_birth = reason_for_visit_date
            elif booking_reason.lower() == "anniversary":
                customer.anniversary_date = reason_for_visit_date

            customer.save()

        sales_level = SalesLevel.objects.filter(organization=organization).first()

        if sales_level and (
            sales_level.level == 2 or sales_level.reward_enabled is True
        ):
            if sales_level.reward is not None:
                sales_level_reward = sales_level.reward

        if promo_code:
            try:
                promotion = Promotion.objects.filter(
                    organization=organization, reward__promo_code=promo_code
                ).first()

                if promotion and promotion.valid_to < date.today():
                    return {"error": "Promo code has expired."}
            except Promotion.DoesNotExist:
                return {"error": "Invalid promo code."}

            try:
                already_used = PromotionSentLog.objects.filter(
                    client=customer,
                    promotion=promotion,
                    status=PromotionSentLogStatus.USED,
                ).exists()
                if already_used:
                    return {"error": "Promo code has already been used."}
            except Exception as e:
                logger.error(f"Error checking promo code usage: {str(e)}")
                return {"error": "Error validating promo code."}

        # Validate required fields
        if not all(
            [
                reservation_name,
                reservation_date_str,
                reservation_time_str,
                guests,
            ]
        ):
            missing_fields = []
            if not reservation_name:
                missing_fields.append("reservation_name")
            if not reservation_date_str:
                missing_fields.append("date")
            if not reservation_time_str:
                missing_fields.append("time")
            if not guests:
                missing_fields.append("guests")

            return {
                "error": f"Missing required booking information: {', '.join(missing_fields)}"
            }

        # Validate reservation is not in the past
        reservation_datetime = datetime.combine(reservation_date, reservation_time)
        if reservation_datetime <= datetime.now():
            return {"error": "Cannot make reservations for past dates/times"}

        # Validate guest count
        try:
            guests = int(guests)
            if guests <= 0:
                return {"error": "Number of guests must be positive"}
        except (ValueError, TypeError):
            return {"error": "Invalid number of guests"}

        # Find suitable tables
        suitable_tables = RestaurantTable.objects.filter(
            organization=organization,
            capacity__gte=guests,
            status=TableStatus.AVAILABLE,
        ).order_by("capacity")

        logger.info(
            f"Found {suitable_tables.count()} suitable tables for {guests} guests"
        )

        if not suitable_tables.exists():
            return {
                "status": "no_suitable_tables",
                "message": f"No tables available for {guests} guests",
            }

        # Find an available table
        selected_table = None
        for table in suitable_tables:
            if is_table_available(table, reservation_date, reservation_time):
                selected_table = table
                break

        if not selected_table:
            # Get alternative time suggestions
            suggestions = get_alternative_time_slots(
                reservation_date, guests, organization, limit=3
            )
            return {
                "status": "time_unavailable",
                "message": f"No tables available at {reservation_time_str} on {reservation_date_str}",
                "suggestions": suggestions,
            }

        if not reservation_phone:
            reservation_phone = customer.whatsapp_number

        # Create the reservation
        try:
            reservation = Reservation.objects.create(
                client=customer,
                reservation_name=reservation_name,
                reservation_date=reservation_date,
                reservation_time=reservation_time,
                guests=guests,
                table=selected_table,
                organization=organization,
                reservation_reason=booking_reason,
                notes=special_notes,
                promo_code=promotion.reward if promotion else None,
                sales_level_reward=sales_level_reward if sales_level_reward else None,
                reservation_phone=reservation_phone,
                reservation_status=ReservationStatus.PLACED,
            )

            if promotion:
                PromotionSentLog.objects.filter(
                    client=customer, promotion=promotion
                ).update(status=PromotionSentLogStatus.USED)

            return {
                "status": "success",
                "reservation_uid": str(reservation.uid),
                "table_name": selected_table.name,
                "table_category": selected_table.category,
                "table_position": selected_table.position or "Standard seating",
                "table_capacity": selected_table.capacity,
                "date": str(reservation.reservation_date),
                "time": str(reservation.reservation_time),
                "guests": guests,
                "reservation_name": reservation_name,
                "booking_reason": booking_reason,
                "special_notes": special_notes,
                "reservation_phone": reservation_phone,
                "promo_code": promo_code if promotion else None,
            }

        except Exception as e:
            logger.error(f"Error creating reservation: {str(e)}")
            return {"error": f"Failed to create reservation: {str(e)}"}

    except Exception as e:
        logger.error(f"Error in handle_book_table: {str(e)}")
        return {"error": f"Booking failed: {str(e)}"}


def handle_add_menu_to_reservation(call, organization) -> Dict[str, Any]:
    """Handle add_menu_to_reservation tool call"""
    try:
        args = json.loads(call.function.arguments)
        logger.info(f"Add menu to reservation arguments: {args}")

        reservation_uid = args.get("reservation_uid")
        menu_items = args.get("menu_items", [])

        if not reservation_uid:
            return {"error": "Reservation UID is required"}

        if not menu_items:
            return {"error": "At least one menu item is required"}

        # Get the reservation
        try:
            reservation = Reservation.objects.get(
                uid=reservation_uid,
                organization=organization,
                reservation_status__in=[
                    ReservationStatus.PLACED,
                    ReservationStatus.INPROGRESS,
                ],
            )
        except Reservation.DoesNotExist:
            return {"error": "Reservation not found or already completed/cancelled"}

        # Process menu items
        added_items = []
        failed_items = []

        for item_data in menu_items:
            menu_name = item_data.get("menu_name", "").strip()

            if not menu_name:
                failed_items.append("Missing menu name")
                continue

            try:
                # Find the menu item (case-insensitive search)
                menu_item = Menu.objects.get(
                    name__iexact=menu_name,
                    organization=organization,
                    status=MenuStatus.ACTIVE,
                )

                # Add to reservation
                reservation.menus.add(menu_item)

                added_items.append(
                    {
                        "name": menu_item.name,
                        "recommended_combinations": list(
                            menu_item.recommended_combinations.all().values_list(
                                "name", flat=True
                            )
                        ),
                    }
                )

            except Menu.DoesNotExist:
                failed_items.append(f"Menu item '{menu_name}' not found or unavailable")
                logger.warning(
                    f"Menu item '{menu_name}' not found for restaurant {organization}"
                )

        if not added_items and failed_items:
            return {
                "status": "failed",
                "message": "No menu items could be added",
                "failed_items": failed_items,
            }

        return {
            "status": "success" if added_items else "partial",
            "reservation_uid": reservation_uid,
            "added_items": added_items,
            "failed_items": failed_items,
            "total_items_added": len(added_items),
            "message": f"Successfully added {len(added_items)} menu items"
            + (f". {len(failed_items)} items failed." if failed_items else ""),
        }

    except Exception as e:
        logger.error(f"Error in handle_add_menu_to_reservation: {str(e)}")
        return {"error": f"Failed to add menu items: {str(e)}"}


def handle_reschedule_reservation(call, organization, customer) -> Dict[str, Any]:
    """Handle reschedule_reservation tool call"""
    try:
        args = json.loads(call.function.arguments)
        logger.info(f"Reschedule reservation arguments: {args}")

        # Extract original reservation identifiers
        original_date_str = args.get("original_reservation_date")
        original_time_str = args.get("original_reservation_time", None)

        if not original_date_str:
            return {"error": "Original reservation date is required"}

        original_reservation_date = datetime.strptime(
            original_date_str, "%Y-%m-%d"
        ).date()

        # Find the original reservation
        if original_time_str:
            try:
                original_reservation_time = datetime.strptime(
                    original_time_str, "%H:%M"
                ).time()
            except ValueError:
                return {
                    "error": "Invalid original reservation time format. Please use HH:MM."
                }

            original_reservation = Reservation.objects.filter(
                client=customer,
                reservation_date=original_reservation_date,
                reservation_time=original_reservation_time,
                organization=organization,
            ).first()
        else:
            reservations = Reservation.objects.filter(
                client=customer,
                reservation_date=original_reservation_date,
                organization=organization,
            )

            if reservations.count() > 1:
                reserved_times = list(
                    reservations.values_list("reservation_time", flat=True)
                )
                return {
                    "status": "need_time_selection",
                    "message": "Multiple reservations found for that date. Please specify the original time to reschedule.",
                    "available_times": [str(rt) for rt in reserved_times],
                }

            original_reservation = reservations.first()

        if not original_reservation:
            return {
                "error": "No reservation found with the given original date and time."
            }

        # Check if original reservation can be rescheduled
        if original_reservation.reservation_status in [
            ReservationStatus.CANCELLED,
            ReservationStatus.COMPLETED,
            ReservationStatus.RESCHEDULED,
        ]:
            return {
                "error": f"Cannot reschedule reservation — it's already {original_reservation.reservation_status.lower()}."
            }

        # Store original reservation details for transfer
        original_details = {
            "reservation_name": original_reservation.reservation_name,
            "reservation_phone": original_reservation.reservation_phone,
            "use_whatsapp": original_reservation.use_whatsapp,
            "guests": original_reservation.guests,
            "booking_reason": original_reservation.booking_reason,
            "special_notes": original_reservation.special_notes,
            "original_date": str(original_reservation.reservation_date),
            "original_time": str(original_reservation.reservation_time),
        }

        # Create new reservation with updated details
        # Use provided new data, fall back to original if not provided
        new_args = {
            "reservation_name": args.get(
                "reservation_name", original_details["reservation_name"]
            ),
            "reservation_phone": args.get(
                "reservation_phone", original_details["reservation_phone"]
            ),
            "use_whatsapp": args.get("use_whatsapp", original_details["use_whatsapp"]),
            "date": args.get("date"),  # This should be the new date
            "time": args.get("time"),  # This should be the new time
            "guests": args.get("guests", original_details["guests"]),
            "booking_reason": args.get(
                "booking_reason", original_details["booking_reason"]
            ),
            "special_notes": args.get(
                "special_notes", original_details["special_notes"]
            ),
        }

        # Create a mock call object for handle_book_table
        class MockCall:
            def __init__(self, arguments):
                self.function = type(
                    "obj", (object,), {"arguments": json.dumps(arguments)}
                )

        mock_call = MockCall(new_args)

        # Create new reservation using existing book_table logic
        booking_result = handle_book_table(mock_call, organization, customer)

        if booking_result.get("status") == "success":
            # Mark original reservation as rescheduled
            original_reservation.reservation_status = ReservationStatus.RESCHEDULED
            original_reservation.save()

            # Return success with both original and new details
            return {
                "status": "success",
                "message": "Reservation successfully rescheduled.",
                "original_details": original_details,
                "new_details": {
                    "reservation_name": booking_result.get("reservation_name"),
                    "reservation_date": booking_result.get("reservation_date"),
                    "reservation_time": booking_result.get("reservation_time"),
                    "guests": booking_result.get("guests"),
                    "table_name": booking_result.get("table_name"),
                    "reservation_uid": booking_result.get("reservation_uid"),
                },
            }
        else:
            return {
                "error": f"Failed to create new reservation: {booking_result.get('error', 'Unknown error')}"
            }

    except Exception as e:
        logger.error(f"Error in handle_reschedule_reservation: {str(e)}")
        return {"error": f"Failed to reschedule reservation: {str(e)}"}


# New function to get customer reservations
def handle_get_customer_reservations(call, organization, customer) -> Dict[str, Any]:
    """ "Handle get_customer_reservations tool call"""
    try:
        args = json.loads(call.function.arguments)
        logger.info(f"Get customer reservations arguments: {args}")

        reservation_date = args.get("reservation_date", None)
        reservation_status = args.get("reservation_status", None)

        if not reservation_date:
            return {"error": "Reservation date is required"}
        if not reservation_status:
            return {"error": "Reservation status is required"}

        reservation_date = datetime.strptime(reservation_date, "%Y-%m-%d").date()

        # Build filter criteria
        filter_criteria = {
            "client": customer,
            "organization": organization,
            "reservation_date": reservation_date,
            "reservation_status": reservation_status,
        }

        # Fetch reservations based on filter criteria
        reservations = Reservation.objects.filter(**filter_criteria)

        if not reservations.exists():
            return {"error": "No reservations found for the specified criteria."}

        # Return the list of reservations
        return {
            "status": "success",
            "reservations": [
                {
                    "reservation_name": res.reservation_name,
                    "reservation_phone": res.reservation_phone,
                    "reservation_date": str(res.reservation_date),
                    "reservation_time": str(res.reservation_time),
                    "reservation_end_time": (
                        str(res.reservation_end_time)
                        if res.reservation_end_time
                        else None
                    ),
                    "reservation_reason": res.reservation_reason,
                    "guests": f"{res.guests} guests",
                    "notes": res.notes,
                    "cancellation_reason": res.cancellation_reason,
                    "menus": [menu.name for menu in res.menus.all()],
                    "reservation_uid": str(res.uid),
                }
                for res in reservations
            ],
        }

    except Exception as e:
        logger.error(f"Error in handle_get_customer_reservations: {str(e)}")
        return {"error": f"Failed to get customer reservations: {str(e)}"}


# Updated handle_cancel_reservation to work with reschedule workflow
def handle_cancel_reservation(call, organization, customer) -> Dict[str, Any]:
    """Handle cancel_reservation tool call"""
    try:
        args = json.loads(call.function.arguments)
        logger.info(f"Cancel reservation arguments: {args}")

        date_str = args.get("reservation_date")
        reservation_time_str = args.get("reservation_time")

        if not date_str:
            return {"error": "Reservation confirmation date is required"}

        reservation_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        # If specific time is given
        if reservation_time_str:
            try:
                reservation_time = datetime.strptime(
                    reservation_time_str, "%H:%M"
                ).time()
            except ValueError:
                return {
                    "error": "Invalid reservation time format. Please use HH:MM (24h format)."
                }

            reservation = Reservation.objects.filter(
                client=customer,
                reservation_date=reservation_date,
                reservation_time=reservation_time,
                organization=organization,
                reservation_status__in=[
                    ReservationStatus.PLACED,
                    ReservationStatus.INPROGRESS,
                    ReservationStatus.RESCHEDULED,
                ],
            ).first()

            if not reservation:
                return {"error": "No reservation found with the given date and time."}

        else:
            reservations = Reservation.objects.filter(
                client=customer,
                reservation_date=reservation_date,
                organization=organization,
                reservation_status__in=[
                    ReservationStatus.PLACED,
                    ReservationStatus.INPROGRESS,
                    ReservationStatus.RESCHEDULED,
                ],
            )

            if not reservations.exists():
                return {"error": "No reservation found for the provided date."}

            if reservations.count() > 1:
                reserved_times = list(
                    reservations.values_list("reservation_time", flat=True)
                )
                return {
                    "status": "need_time_selection",
                    "message": "Multiple reservations found for that date. Please specify the time to cancel.",
                    "available_times": [str(rt) for rt in reserved_times],
                }

            reservation = reservations.first()

        # Check if already cancelled or completed
        if reservation.reservation_status in [
            ReservationStatus.CANCELLED,
            ReservationStatus.COMPLETED,
        ]:
            return {
                "error": f"Cannot cancel reservation — it's already {reservation.reservation_status.lower()}."
            }

        # Check if reservation is in the past
        reservation_datetime = datetime.combine(
            reservation.reservation_date, reservation.reservation_time
        )
        if reservation_datetime <= datetime.now():
            return {"error": "Cannot cancel a past reservation."}

        # Store details for confirmation
        original_details = {
            "reservation_phone": reservation.reservation_phone,
            "reservation_name": reservation.reservation_name,
            "date": str(reservation.reservation_date),
            "time": str(reservation.reservation_time),
            "guests": reservation.guests,
            "table_name": reservation.table.name,
            "original_status": reservation.reservation_status,
        }

        # Cancel the reservation
        reservation.reservation_status = ReservationStatus.CANCELLED
        reservation.cancelled_by = ReservationCancelledBy.CUSTOMER
        reservation.save()

        logger.info(
            f"Reservation cancelled: {reservation.reservation_date} at {reservation.reservation_time}"
        )

        return {
            "status": "success",
            "message": "Reservation successfully cancelled.",
            **original_details,
        }

    except Exception as e:
        logger.error(f"Error in handle_cancel_reservation: {str(e)}")
        return {"error": f"Failed to cancel reservation: {str(e)}"}


def handle_get_personalized_recommendations(
    call, organization, customer
) -> Dict[str, Any]:
    """Handle get_personalized_recommendations tool call"""
    try:
        args = json.loads(call.function.arguments)
        logger.info(f"Get personalized recommendations arguments: {args}")

        limit = args.get("limit", 5)

        # Fetch customer's past reservations
        past_reservations = Reservation.objects.filter(
            client=customer,
            organization=organization,
            # reservation_status=ReservationStatus.COMPLETED,
        ).prefetch_related("menus")

        if not past_reservations.exists():
            return {
                "status": "no_past_reservations",
                "message": "No past reservations found for personalized recommendations.",
            }

        # Aggregate menu item frequencies
        item_counter = Counter()
        for reservation in past_reservations:
            for menu_item in reservation.menus.all():
                item_counter[menu_item] += 1

        if not item_counter:
            return {
                "status": "no_recommendations",
                "message": "No menu items found in past orders for recommendations.",
            }

        # Get the most common items
        most_common_items = item_counter.most_common(limit)

        recommendations = [
            {
                "name": item.name,
                "times_ordered": count,
                "uid": str(item.uid),
            }
            for item, count in most_common_items
        ]

        return {
            "status": "success",
            "recommendations": recommendations,
            "total_recommendations": len(recommendations),
        }

    except Exception as e:
        logger.error(f"Error in handle_get_personalized_recommendations: {str(e)}")
        return {"error": f"Failed to get personalized recommendations: {str(e)}"}


def handle_get_available_promotions(call, organization) -> Dict[str, Any]:
    """Handle get_available_promotions tool call"""
    try:
        # Fetch active promotions for the organization
        promotions_qs = Promotion.objects.filter(
            organization=organization,
            valid_from__lte=date.today(),
            valid_to__gte=date.today(),
            is_enabled=True,
        ).select_related("reward")

        if not promotions_qs.exists():
            return {
                "status": "no_promotions",
                "message": "No active promotions available at the moment.",
            }

        # Format promotions for display
        promotions = []
        for promo in promotions_qs:
            promotions.append(
                {
                    "uid": str(promo.uid),
                    "valid_from": str(promo.valid_from),
                    "valid_to": str(promo.valid_to),
                    "reward": (
                        {
                            "type": (
                                promo.reward.get_type_display()
                                if promo.reward
                                else None
                            ),
                            "label": promo.reward.label if promo.reward else None,
                            "promo_code": (
                                promo.reward.promo_code if promo.reward else None
                            ),
                        }
                        if promo.reward
                        else None
                    ),
                }
            )

        return {
            "status": "success",
            "promotions": promotions,
            "total_promotions": len(promotions),
        }

    except Exception as e:
        logger.error(f"Error in handle_get_available_promotions: {str(e)}")
        return {"error": f"Failed to get available promotions: {str(e)}"}


def handle_get_priority_menu_items(call, organization) -> Dict[str, Any]:
    """Handle get_priority_menu_items tool call"""
    try:
        # Fetch menu items marked as priority or recommended
        priority_items_qs = (
            Menu.objects.filter(
                organization=organization,
                status=MenuStatus.ACTIVE,
                enable_upselling=True,
            )
            .order_by("category", "name")
            .values("uid", "name", "upselling_priority")
        )

        if not priority_items_qs.exists():
            return {
                "status": "no_priority_items",
                "message": "No priority or recommended menu items available.",
            }

        # Convert UUID to string
        priority_items = [
            {
                "uid": str(item["uid"]),
                "name": item["name"],
                "upselling_priority": item["upselling_priority"],
            }
            for item in priority_items_qs
        ]

        return {
            "status": "success",
            "items": priority_items,
            "total_items": len(priority_items),
        }

    except Exception as e:
        logger.error(f"Error in handle_get_priority_menu_items: {str(e)}")
        return {"error": f"Failed to get priority menu items: {str(e)}"}


def is_table_available(
    table: RestaurantTable,
    reservation_date: date,
    reservation_time: Optional[dtime] = None,
) -> bool:
    """Check if a table is available at the specified date and time"""
    try:
        base_filter = {
            "table": table,
            "reservation_date": reservation_date,
            "reservation_end_time__isnull": True,
            "reservation_status__in": [
                ReservationStatus.PLACED,
                ReservationStatus.INPROGRESS,
            ],
        }

        # Only apply time range if reservation_time is provided
        if reservation_time is not None:
            base_dt = datetime.combine(reservation_date, reservation_time)
            start_time = (base_dt - timedelta(hours=1, minutes=30)).time()
            end_time = (base_dt + timedelta(hours=1, minutes=30)).time()
            base_filter["reservation_time__range"] = (start_time, end_time)

        conflicting_reservations = Reservation.objects.filter(**base_filter)
        return not conflicting_reservations.exists()

    except Exception as e:
        print(f"Error in is_table_available: {e}")
        return False


def get_alternative_time_slots(
    date: date, guests: int, organization, limit: int = 3
) -> List[Dict[str, Any]]:
    """Get alternative available time slots for the same date"""
    try:
        # Common restaurant time slots
        time_slots = [
            "09:00",
            "09:30",
            "10:00",
            "10:30",
            "11:00",
            "11:30",
            "12:00",
            "12:30",
            "13:00",
            "13:30",
            "14:00",
            "18:00",
            "18:30",
            "19:00",
            "19:30",
            "20:00",
            "20:30",
            "21:00",
            "21:30",
            "22:00",
            "22:30",
            "23:00",
            "23:30",
        ]

        alternatives = []
        suitable_tables = RestaurantTable.objects.filter(
            organization=organization,
            capacity__gte=guests,
            status=TableStatus.AVAILABLE,
        )

        for time_str in time_slots:
            if len(alternatives) >= limit:
                break

            try:
                time_obj = datetime.strptime(time_str, "%H:%M").time()
                available_count = 0

                for table in suitable_tables:
                    if is_table_available(table, date, time_obj):
                        available_count += 1

                if available_count > 0:
                    alternatives.append(
                        {"time": time_str, "available_tables": available_count}
                    )

            except ValueError:
                continue

        return alternatives

    except Exception as e:
        logger.error(f"Error getting alternative time slots: {str(e)}")
        return []
