import logging
from openai import OpenAI

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
    get_object_or_404,
)

from apps.openAI.utils import cancel_active_runs, process_assistant_run
from apps.organization.models import Organization, WhatsappBot
from apps.restaurant.models import RestaurantDocument
from apps.restaurant.models import Client, ClientMessage
from apps.restaurant.choices import ClientMessageRole

from common.crypto import decrypt_data
from common.whatsapp import send_whatsapp_message


from ..serializers.whatsapp import (
    RestaurantWhatsAppSerializer,
    RestaurantWhatsAppDetailSerializer,
    WhatsappClientListSerializer,
)

logger = logging.getLogger(__name__)


@csrf_exempt
def whatsapp_bot(request):
    """Main WhatsApp bot endpoint"""
    profile_name = request.POST.get("ProfileName", "")
    whatsapp_number = request.POST.get("From", "")
    incoming_message = request.POST.get("Body", "").strip()
    twilio_number = request.POST.get("To", "")

    if not all([twilio_number, whatsapp_number, incoming_message]):
        logger.error("Missing required WhatsApp data")
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
        twilio_sid = decrypt_data(bot.twilio_sid, settings.CRYPTO_PASSWORD)

        instruction = openai_client.beta.assistants.retrieve(assistant_id).instructions
        print("Instruction------------------------------->:", instruction)

        # Get or create client
        customer, created = Client.objects.get_or_create(
            whatsapp_number=whatsapp_number.replace("whatsapp:", "").strip(),
            organization=bot.organization,
            defaults={"name": profile_name},
        )

        # Save message history to database
        ClientMessage.objects.create(
            client=customer,
            role=ClientMessageRole.USER,
            message=incoming_message,
        )

        # Create thread for new customers
        if created or not customer.thread_id:
            thread = openai_client.beta.threads.create()
            customer.thread_id = thread.id
            customer.save()
            logger.info(f"Created new thread for customer: {customer.whatsapp_number}")

        # Check for active runs and cancel them if necessary
        cancel_active_runs(openai_client, customer.thread_id)

        # Add user message to thread
        openai_client.beta.threads.messages.create(
            thread_id=customer.thread_id, role="user", content=incoming_message
        )

        # Create and process run
        run = openai_client.beta.threads.runs.create(
            thread_id=customer.thread_id,
            assistant_id=assistant_id,
        )

        # Cheack media available in incoming message
        state = {"media_available": False}

        # Process the run
        reply = process_assistant_run(
            openai_client,
            customer,
            run,
            bot.organization,
            request,
            twilio_sid,
            twilio_auth_token,
            twilio_number,
            whatsapp_number,
            state,
        )

        if reply:
            # Send reply via WhatsApp
            send_result = send_whatsapp_message(
                whatsapp_number, reply, twilio_sid, twilio_auth_token, twilio_number
            )

            if send_result:
                menu_pdf_url = None
                if state.get("media_available"):
                    # Menu pdf file
                    menus = RestaurantDocument.objects.filter(
                        organization=bot.organization, name="menu"
                    ).first()

                    if menus and menus.file:
                        if request:
                            menu_pdf_url = request.build_absolute_uri(menus.file.url)
                        else:
                            menu_pdf_url = menus.file.url

                # Save message history to database
                ClientMessage.objects.create(
                    client=customer,
                    message=reply,
                    media_url=menu_pdf_url if menu_pdf_url else None,
                )
                logger.info(f"Reply sent successfully to {whatsapp_number}")
                return JsonResponse({"status": "ok", "reply": reply})
            else:
                logger.error("Failed to send WhatsApp reply")

    except Exception as e:
        logger.error(f"Error in whatsapp_bot: {str(e)}")

    # Fallback response
    fallback_message = "⚠️ Sorry, something went wrong. Please try again in a moment."
    try:
        send_whatsapp_message(
            whatsapp_number,
            fallback_message,
            twilio_sid,
            twilio_auth_token,
            twilio_number,
        )
        logger.info("Fallback message sent")
    except Exception as e:
        logger.error(f"Failed to send fallback message: {str(e)}")

    return JsonResponse({"status": "ok", "fallback": True})


class RestaurantWhatsAppListView(ListCreateAPIView):
    queryset = WhatsappBot.objects.all()
    serializer_class = RestaurantWhatsAppSerializer

    def get_queryset(self):
        organizations = Organization.objects.for_user(self.request.user).restaurants()
        return self.queryset.filter(organization__in=organizations)


class RestaurantWhatsAppDetailView(RetrieveUpdateDestroyAPIView):
    queryset = WhatsappBot.objects.all()
    serializer_class = RestaurantWhatsAppDetailSerializer

    def get_object(self):
        whatsapp_bot_uid = self.kwargs["whatsapp_bot_uid"]
        return self.queryset.get(uid=whatsapp_bot_uid)


class WhatsappClientListView(ListAPIView):
    queryset = Client.objects.all()
    serializer_class = WhatsappClientListSerializer

    def get_queryset(self):
        whatsapp_bot_uid = self.kwargs["whatsapp_bot_uid"]
        whatsapp_bot = get_object_or_404(WhatsappBot, uid=whatsapp_bot_uid)

        self.queryset = self.queryset.filter(organization=whatsapp_bot.organization)
        return self.queryset.order_by("-created_at")
