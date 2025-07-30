# import logging
# import json
# import requests

# from django.views.decorators.csrf import csrf_exempt
# from django.http import JsonResponse

# from twilio.rest import Client as TwilioClient
# import os
# import time
# from openai import OpenAI

# from django.conf import settings

# from apps.openAI.gpt_assistants import create_assistant, assistant_list
# from apps.openAI.utils import get_or_create_thread
# from apps.openAI.tools import tools
# from apps.restaurant.models import Client, Reservation

# logger = logging.getLogger(__name__)


# twilio_client = TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
# client = OpenAI(api_key=os.environ.get("OPENAI_API"))


# import requests
# from typing import Optional


# def send_whatsapp_reply(to: str, message: str) -> Optional[dict]:
#     """
#     Send a WhatsApp message via Twilio API

#     Args:
#         to: Phone number in E.164 format (e.g., '+1234567890')
#         message: Message content to send

#     Returns:
#         Response data if successful, None if failed
#     """
#     url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"

#     data = {
#         "From": settings.TWILIO_WHATSAPP_NUMBER,
#         "To": f"whatsapp:{to}",
#         "Body": message,
#     }

#     auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

#     try:
#         response = requests.post(url, data=data, auth=auth)
#         response.raise_for_status()
#         return response.json()
#     except requests.exceptions.RequestException as e:
#         print(f"Error sending WhatsApp message: {e}")
#         return None


# def get_number_only(text):
#     return "".join(char for char in text if char.isdigit())


# @csrf_exempt
# def whatsapp_bot(request):
#     from_number = get_number_only(request.POST.get("From", ""))
#     incoming_message = request.POST.get("Body", "").strip()

#     thread_id = get_or_create_thread(from_number)

#     # Send user message
#     client.beta.threads.messages.create(
#         thread_id, role="user", content=incoming_message
#     )

#     # Run assistant
#     run = client.beta.threads.runs.create(
#         thread_id=thread_id, assistant_id=settings.ASSISTANT_ID
#     )

#     # Pull until completed
#     while True:
#         run_status = client.beta.threads.runs.retrieve(
#             thread_id=thread_id, run_id=run.id
#         )

#         if run_status.status == "completed":
#             logger.info("completed")
#             break
#         elif run_status.status == "requires_action":
#             logger.info("requires_action")
#             for call in run_status.required_action.submit_tool_outputs.tool_calls:
#                 logger.info(f"Tool call: {call.function.name}")
#                 if call.function.name == "check_customer_status":
#                     logger.info("check_customer_status")
#                     logger.info(call.function.__dict__)
#                     args = json.loads(call.function.arguments)
#                     phone = args["phone"]

#                     customer = Client.objects.filter(phone=phone).first()
#                     if customer:
#                         result = {"status": "existing", "name": customer.name}
#                     else:
#                         result = {"status": "new"}

#                     client.beta.threads.runs.submit_tool_output(
#                         thread_id=thread_id,
#                         run_id=run.id,
#                         tool_output=[
#                             {"tool_call_id": call.id, "output": json.dumps(result)}
#                         ],
#                     )
#                 elif call.function.name == "book_table":
#                     logger.info("book_table")
#                     args = json.loads(call.function.argmuents)
#                     Reservation.objects.create(
#                         customer=customer,
#                         date=args["date"],
#                         time=args["time"],
#                         guests=args["guests"],
#                         notes=args["notes"],
#                     )

#                     client.beta.threads.runs.submit_tool_output(
#                         thread_id=thread_id,
#                         run_id=run.id,
#                         tool_output=[
#                             {
#                                 "tool_call_id": call.id,
#                                 "output": json.dumps({"status": "success"}),
#                             }
#                         ],
#                     )

#             time.sleep(1)
#         else:
#             time.sleep(1)

#     # Get assistant response
#     messages = client.beta.threads.messages.list(thread_id=thread_id)
#     for message in messages:
#         if message.role == "assistant" and message.content[0].type == "text":
#             logger.info(f"Assistant reply: {message.content[0].text.value}")
#             reply = message.content[0].text.value
#             send_whatsapp_reply(from_number, reply)
#             logger.info(f"Reply sent")
#             return JsonResponse({"status": "ok", "reply": reply})

#     send_whatsapp_reply(from_number, "⚠️ Sorry, something went wrong.")

#     return JsonResponse({"status": "ok", "fallback": True})
from typing import Dict, Any
import logging
import json
from datetime import time, datetime
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

from apps.restaurant.models import Client, Reservation, RestaurantTable
from apps.openAI.utils import get_or_create_thread, check_table_availability
from common.whatsapp import send_whatsapp_reply

from django.conf import settings

from openai import OpenAI

logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.OPENAI_API_KEY)


@csrf_exempt
def whatsapp_bot(request):
    """Main WhatsApp bot endpoint"""
    try:
        from_number = request.POST.get("From", "")
        incoming_message = request.POST.get("Body", "").strip()

        if not from_number or not incoming_message:
            return JsonResponse({"status": "error", "message": "Missing required data"})

        # Format phone number
        formatted_phone = from_number

        # Get or create thread
        thread_id = get_or_create_thread(from_number, organization_uid)

        # Send user message to thread
        client.beta.threads.messages.create(
            thread_id=thread_id, role="user", content=incoming_message
        )

        # Run assistant
        run = client.beta.threads.runs.create(
            thread_id=thread_id, assistant_id=settings.ASSISTANT_ID
        )

        # Process the run
        max_iterations = 30  # Prevent infinite loops
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread_id, run_id=run.id
            )

            if run_status.status == "completed":
                logger.info("Assistant run completed")
                break

            elif run_status.status == "requires_action":
                logger.info("Processing required actions")
                tool_outputs = []

                for call in run_status.required_action.submit_tool_outputs.tool_calls:
                    logger.info(f"Processing tool call: {call.function.name}")

                    try:
                        if call.function.name == "check_customer_status":
                            result = handle_check_customer_status(call, formatted_phone)
                        elif call.function.name == "book_table":
                            result = handle_book_table(call, formatted_phone)
                        else:
                            result = {
                                "error": f"Unknown function: {call.function.name}"
                            }

                        tool_outputs.append(
                            {"tool_call_id": call.id, "output": json.dumps(result)}
                        )

                    except Exception as e:
                        logger.error(
                            f"Error processing tool call {call.function.name}: {e}"
                        )
                        tool_outputs.append(
                            {
                                "tool_call_id": call.id,
                                "output": json.dumps({"error": str(e)}),
                            }
                        )

                # Submit tool outputs
                client.beta.threads.runs.submit_tool_outputs(
                    thread_id=thread_id, run_id=run.id, tool_outputs=tool_outputs
                )

            elif run_status.status in ["failed", "cancelled", "expired"]:
                logger.error(f"Run failed with status: {run_status.status}")
                break

            time.sleep(1)

        # Get assistant response
        messages = client.beta.threads.messages.list(thread_id=thread_id)

        for message in messages:
            if message.role == "assistant" and message.content[0].type == "text":
                reply = message.content[0].text.value
                logger.info(f"Assistant reply: {reply}")

                # Send reply via WhatsApp
                send_result = send_whatsapp_reply(formatted_phone, reply)
                if send_result:
                    logger.info("Reply sent successfully")
                    return JsonResponse({"status": "ok", "reply": reply})
                else:
                    logger.error("Failed to send WhatsApp reply")

        # Fallback response
        fallback_message = "⚠️ Sorry, something went wrong. Please try again."
        send_whatsapp_reply(formatted_phone, fallback_message)
        return JsonResponse({"status": "ok", "fallback": True})

    except Exception as e:
        logger.error(f"Error in whatsapp_bot: {e}")
        return JsonResponse({"status": "error", "message": str(e)})


def handle_check_customer_status(call, phone: str) -> Dict[str, Any]:
    """Handle check_customer_status tool call"""
    try:
        args = json.loads(call.function.arguments)
        phone_to_check = args.get("phone", phone)

        # Look for existing customer
        customer = Client.objects.filter(
            whatsapp_number__icontains=phone_to_check
        ).first()

        if customer:
            return {
                "status": "existing",
                "name": customer.name or "Valued Customer",
                "phone": customer.whatsapp_number,
                "preferences": customer.preferences or [],
                "last_visit": (
                    customer.last_visit.isoformat() if customer.last_visit else None
                ),
            }
        else:
            return {"status": "new"}

    except Exception as e:
        logger.error(f"Error in handle_check_customer_status: {e}")
        return {"error": str(e)}


def handle_book_table(call, phone: str) -> Dict[str, Any]:
    """Handle book_table tool call"""
    try:
        args = json.loads(call.function.arguments)

        # Extract required data
        name = args.get("name")
        customer_phone = args.get("phone", phone)
        reservation_date = args.get("date")
        reservation_time = args.get("time")
        guests = args.get("guests")

        # Optional data
        preferences = args.get("preferences", [])
        birthday = args.get("birthday")

        # Validate required fields
        if not all([name, customer_phone, reservation_date, reservation_time, guests]):
            return {"error": "Missing required booking information"}

        # Check table availability
        organization_id = settings.DEFAULT_ORGANIZATION_ID  # Set your default org ID
        availability = check_table_availability(
            reservation_date, reservation_time, guests, organization_id
        )

        if not availability["available"]:
            response = {"status": "unavailable", "message": availability["message"]}
            if availability["suggestions"]:
                response["suggestions"] = availability["suggestions"]
            return response

        # Get or create customer
        customer, created = Client.objects.get_or_create(
            whatsapp_number=customer_phone,
            defaults={
                "name": name,
                "preferences": preferences,
                "organization_id": organization_id,
            },
        )

        # Update customer info if existing
        if not created:
            if not customer.name:
                customer.name = name
            if preferences and not customer.preferences:
                customer.preferences = preferences
            customer.save()

        # Set birthday if provided
        if birthday and not customer.date_of_birth:
            try:
                customer.date_of_birth = datetime.strptime(birthday, "%Y-%m-%d").date()
                customer.save()
            except ValueError:
                logger.warning(f"Invalid birthday format: {birthday}")

        # Select the best available table
        selected_table_info = availability["tables"][0]  # Take first available
        selected_table = RestaurantTable.objects.get(id=selected_table_info["id"])

        # Create reservation
        reservation = Reservation.objects.create(
            client=customer,
            reservation_date=datetime.strptime(reservation_date, "%Y-%m-%d").date(),
            reservation_time=datetime.strptime(reservation_time, "%H:%M").time(),
            guests=guests,
            table=selected_table,
            organization_id=organization_id,
            reservation_status="placed",
        )

        return {
            "status": "success",
            "reservation_id": str(reservation.uid),
            "table_name": selected_table.name,
            "date": reservation_date,
            "time": reservation_time,
            "guests": guests,
            "customer_name": customer.name,
        }

    except Exception as e:
        logger.error(f"Error in handle_book_table: {e}")
        return {"error": str(e)}
