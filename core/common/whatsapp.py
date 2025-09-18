import logging
import requests
from typing import Optional

from django.conf import settings
from django.http import JsonResponse

from apps.organization.models import WhatsappBot

from common.crypto import decrypt_data

logger = logging.getLogger(__name__)


def send_whatsapp_message(
    to: str, message: str, twilio_sid: str, twilio_auth_token: str, twilio_number: str
) -> Optional[dict]:
    """
    Send a whatsapp message via Twilio API

    Args:
        to: Phone number in E164 format (e.g., '+1234567890')
        message: Message content to send

    Returns:
        Response data if successful, None if failed
    """

    url = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json"

    data = {
        "From": twilio_number,
        "To": to,
        "Body": message,
    }

    auth = (twilio_sid, twilio_auth_token)

    try:
        response = requests.post(url, data=data, auth=auth)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending WhatsApp message: {e}")
        return None


def send_cancellation_notification(twilio_number, whatsapp_number, message):
    """Send cancellation notification via WhatsApp"""

    if not all([twilio_number, whatsapp_number, message]):
        logger.error("Missing required WhatsApp data")
        return JsonResponse({"status": "error", "message": "Missing required data"})

    try:
        bot = WhatsappBot.objects.filter(twilio_number=twilio_number).first()
        if not bot:
            logger.error(f"Twilio number not found: {twilio_number}")
            return JsonResponse(
                {"status": "error", "message": "Whatsapp number not found"}
            )

        twilio_auth_token = decrypt_data(
            bot.twilio_auth_token, settings.CRYPTO_PASSWORD
        )
        twilio_sid = decrypt_data(bot.twilio_sid, settings.CRYPTO_PASSWORD)

        # Send reply via WhatsApp
        send_result = send_whatsapp_message(
            whatsapp_number,
            message,
            twilio_sid,
            twilio_auth_token,
            twilio_number,
        )

        if send_result:
            logger.info(f"Message sent successfully to {whatsapp_number}")
            return JsonResponse({"status": "ok"})
        else:
            logger.error("Failed to send WhatsApp message")

    except Exception as e:
        logger.error(f"Error in send_cancellation_notification: {str(e)}")
