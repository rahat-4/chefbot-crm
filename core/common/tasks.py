import json
import requests
from celery import shared_task
from datetime import timedelta
from openai import OpenAI

from django.conf import settings
from django.db.models import Count
from django.utils import timezone

from apps.organization.choices import MessageTemplateType
from apps.restaurant.models import Client, Promotion, Reservation
from apps.restaurant.choices import TriggerType, ReservationStatus


from .crypto import decrypt_data


def send_whatsapp_template(
    from_number, to, twilio_sid, twilio_auth_token, template_sid, content_variables
):
    url = f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}/Messages.json"

    data = {
        "From": from_number,
        "To": f"whatsapp:{to}",
        "ContentSid": template_sid,
        "ContentVariables": json.dumps(content_variables),
    }

    auth = (twilio_sid, twilio_auth_token)

    try:
        response = requests.post(url, data=data, auth=auth)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending message: {e}")
        return None


@shared_task
def send_scheduled_promotions() -> None:
    """
    Run daily to check upcoming events and schedule promotions.
    """
    today = timezone.now().date()

    promotions = Promotion.objects.filter(
        is_enabled=True,
        valid_from__lte=today,
        valid_to__gte=today,
    )

    print(f"Found {promotions.count()} promotions to process.")

    for promotion in promotions:
        trigger = promotion.trigger
        whatsapp_bot = promotion.organization.whatsapp_bots

        if not whatsapp_bot:
            print("Skipping promotion: no WhatsApp bot configured.")
            continue

        # Decrypt credentials
        openai_key = decrypt_data(whatsapp_bot.openai_key, settings.CRYPTO_PASSWORD)
        openai_client = OpenAI(api_key=openai_key)  # might be used later
        assistant_id = decrypt_data(whatsapp_bot.assistant_id, settings.CRYPTO_PASSWORD)
        twilio_auth_token = decrypt_data(
            whatsapp_bot.twilio_auth_token, settings.CRYPTO_PASSWORD
        )
        twilio_sid = decrypt_data(whatsapp_bot.twilio_sid, settings.CRYPTO_PASSWORD)
        twilio_number = whatsapp_bot.twilio_number

        clients = Client.objects.none()  # default empty queryset

        # Handle trigger types
        if trigger.type == TriggerType.BIRTHDAY and trigger.days_before is not None:
            target_date = today + timedelta(days=trigger.days_before)
            clients = Client.objects.filter(
                date_of_birth__month=target_date.month,
                date_of_birth__day=target_date.day,
                organization=promotion.organization,
            )

        elif (
            trigger.type == TriggerType.INACTIVITY
            and trigger.inactivity_days is not None
        ):
            cutoff_date = today - timedelta(days=trigger.inactivity_days)
            clients = Client.objects.filter(
                last_visit__lt=cutoff_date,
                organization=promotion.organization,
            )

        elif (
            trigger.type == TriggerType.RESERVATION_COUNT
            and trigger.min_count is not None
        ):
            clients = (
                Client.objects.filter(organization=promotion.organization)
                .annotate(res_count=Count("reservations"))
                .filter(res_count__gte=trigger.min_count)
            )
        elif trigger.type == TriggerType.MENU_SELECTED:
            clients = Client.objects.filter(
                organization=promotion.organization,
            )
        else:
            print(f"Unknown or improperly configured trigger: {trigger}")
            continue

        # Send messages to matched clients
        template_sid = "HX4a57d9016c9cfd2c0739b5aa5863eac4"
        for client in clients:
            content_variables = {
                "1": client.name or client.whatsapp_number,
                "2": promotion.organization.name,
                "3": "10",
            }

            print(
                f"Sending promotion '{promotion.id}' to client '{client.id}' ({client.whatsapp_number})"
            )
            if client.whatsapp_number:
                send_whatsapp_template(
                    twilio_number,
                    client.whatsapp_number,
                    twilio_sid,
                    twilio_auth_token,
                    template_sid,
                    content_variables,
                )

        print(f"Processed promotion {promotion.id} with {clients.count()} clients.")


@shared_task
def reservation_reminder() -> None:
    """
    Run periodically (e.g., every 5 minutes via a cron job or Celery)
    to send reservation reminders scheduled to be sent now.
    """

    now = timezone.now()
    time_window_start = now - timedelta(minutes=5)
    time_window_end = now

    reservations = Reservation.objects.filter(
        reservation_status=ReservationStatus.PLACED,
        booking_reminder_sent=False,
        booking_reminder_sent_at__range=(time_window_start, time_window_end),
    )

    print(f"Time------------------------------------------>{now}")

    print(f"Found {reservations.count()} reservations for tomorrow.")

    for reservation in reservations:
        whatsapp_bot = getattr(reservation.organization, "whatsapp_bots", None)

        if not whatsapp_bot:
            print(f"Skipping reservation {reservation.id}: no WhatsApp bot configured.")
            continue

        # Decrypt credentials
        twilio_auth_token = decrypt_data(
            whatsapp_bot.twilio_auth_token, settings.CRYPTO_PASSWORD
        )
        twilio_sid = decrypt_data(whatsapp_bot.twilio_sid, settings.CRYPTO_PASSWORD)
        twilio_number = whatsapp_bot.twilio_number

        template_sid = reservation.organization.message_templates.filter(
            type=MessageTemplateType.REMINDER
        ).first()

        print(f"Template SID-------------------------->{template_sid}")

        if not template_sid:
            print(
                f"Skipping reservation {reservation.id}: no reminder template configured."
            )
            continue

        content_variables = {
            "1": reservation.organization.name,
            "2": reservation.reservation_name,
            "3": "test",
        }
        # "3": reservation.reservation_time.strftime("%I:%M %p"),

        print(
            f"Sending reservation reminder to  '{reservation.id}' ({reservation.reservation_name})"
        )
        print(f"-------------------------->{reservation.client.whatsapp_number}")
        if reservation.client.whatsapp_number:
            send_whatsapp_template(
                twilio_number,
                reservation.client.whatsapp_number,
                twilio_sid,
                twilio_auth_token,
                template_sid,
                content_variables,
            )

            # Mark reminder as sent
            reservation.booking_reminder_sent = True
            reservation.save(update_fields=["booking_reminder_sent"])
