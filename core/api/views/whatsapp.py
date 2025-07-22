import logging

from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse


from twilio.rest import Client
import os

logger = logging.getLogger(__name__)


TWILIO_ACCOUNT_SID="MG2ae700e7ddc9130d60188dd0ee9d6315"
TWILIO_AUTH_TOKEN="eb31fdf55378f6d14ceacd90bb97a5a4"
TWILIO_WHATSAPP_NUMBER="whatsapp:+17373772458"


client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
@csrf_exempt
def whatsapp_bot(request):
    incoming_message = request.POST.get("Body", "").lower()
    logger.info(f"Incoming WhatsApp message: {incoming_message}")


    return HttpResponse("OK")
