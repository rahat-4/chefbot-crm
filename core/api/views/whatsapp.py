import logging
import json
import requests

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

from twilio.rest import Client as TwilioClient
import os
import time
from openai import OpenAI

from django.conf import settings

from apps.openAI.gpt_assistants import create_assistant, assistant_list
from apps.openAI.utils import get_or_create_thread
from apps.openAI.tools import tools
from apps.restaurant.models import Client, Reservation

logger = logging.getLogger(__name__)


twilio_client = TwilioClient(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
client = OpenAI(api_key=os.environ.get("OPENAI_API"))


import requests
from typing import Optional


def send_whatsapp_reply(to: str, message: str) -> Optional[dict]:
    """
    Send a WhatsApp message via Twilio API

    Args:
        to: Phone number in E.164 format (e.g., '+1234567890')
        message: Message content to send

    Returns:
        Response data if successful, None if failed
    """
    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json"

    data = {
        "From": settings.TWILIO_WHATSAPP_NUMBER,
        "To": f"whatsapp:{to}",
        "Body": message,
    }

    auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    try:
        response = requests.post(url, data=data, auth=auth)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending WhatsApp message: {e}")
        return None


def get_number_only(text):
    return "".join(char for char in text if char.isdigit())


@csrf_exempt
def whatsapp_bot(request):
    from_number = get_number_only(request.POST.get("From", ""))
    incoming_message = request.POST.get("Body", "").strip()

    thread_id = get_or_create_thread(from_number)

    # Send user message
    client.beta.threads.messages.create(
        thread_id, role="user", content=incoming_message
    )

    # Run assistant
    run = client.beta.threads.runs.create(
        thread_id=thread_id, assistant_id=settings.ASSISTANT_ID
    )

    # Pull until completed
    while True:
        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread_id, run_id=run.id
        )

        if run_status.status == "completed":
            logger.info("completed")
            break
        elif run_status.status == "requires_action":
            logger.info("requires_action")
            for call in run_status.required_action.submit_tool_outputs.tool_calls:
                logger.info(f"Tool call: {call.function.name}")
                if call.function.name == "check_customer_status":
                    logger.info("check_customer_status")
                    logger.info(call.function.__dict__)
                    args = json.loads(call.function.arguments)
                    phone = args["phone"]

                    customer = Client.objects.filter(phone=phone).first()
                    if customer:
                        result = {"status": "existing", "name": customer.name}
                    else:
                        result = {"status": "new"}

                    client.beta.threads.runs.submit_tool_output(
                        thread_id=thread_id,
                        run_id=run.id,
                        tool_output=[
                            {"tool_call_id": call.id, "output": json.dumps(result)}
                        ],
                    )
                elif call.function.name == "book_table":
                    logger.info("book_table")
                    args = json.loads(call.function.argmuents)
                    Reservation.objects.create(
                        customer=customer,
                        date=args["date"],
                        time=args["time"],
                        guests=args["guests"],
                        notes=args["notes"],
                    )

                    client.beta.threads.runs.submit_tool_output(
                        thread_id=thread_id,
                        run_id=run.id,
                        tool_output=[
                            {
                                "tool_call_id": call.id,
                                "output": json.dumps({"status": "success"}),
                            }
                        ],
                    )

            time.sleep(1)
        else:
            time.sleep(1)

    # Get assistant response
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    for message in messages:
        if message.role == "assistant" and message.content[0].type == "text":
            logger.info(f"Assistant reply: {message.content[0].text.value}")
            reply = message.content[0].text.value
            send_whatsapp_reply(from_number, reply)
            logger.info(f"Reply sent")
            return JsonResponse({"status": "ok", "reply": reply})

    send_whatsapp_reply(from_number, "⚠️ Sorry, something went wrong.")

    return JsonResponse({"status": "ok", "fallback": True})
