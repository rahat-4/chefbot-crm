from typing import Optional
import requests


def send_whatsapp_reply(
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
