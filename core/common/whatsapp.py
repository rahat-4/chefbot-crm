from typing import Optional
import requests

from django.conf import settings


def send_whatsapp_reply(to: str, message: str) -> Optional[dict]:
    """
    Send a whatsapp message via Twilio API

    Args:
        to: Phone number in E164 format (e.g., '+1234567890')
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
