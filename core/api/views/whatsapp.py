import logging
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

logger = logging.getLogger(__name__)


@csrf_exempt
def whatsapp_bot(request):
    incoming_message = request.POST.get("Body", "").lower()

    logger.info(f"Incoming WhatsApp message: {incoming_message}")

    return HttpResponse("OK")
