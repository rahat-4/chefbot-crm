import json
import requests
from celery import shared_task
from datetime import timedelta
from openai import OpenAI

from django.conf import settings
from django.db.models import Count, Q
from django.utils import timezone

from apps.organization.choices import MessageTemplateType
from apps.restaurant.models import Client, Promotion, PromotionSentLog, Reservation
from apps.restaurant.choices import TriggerType, ReservationStatus, YearlyCategory


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
    today = timezone.localdate()

    promotions = Promotion.objects.filter(
        is_enabled=True,
        valid_from__lte=today,
        valid_to__gte=today,
    )

    print(f"Found {promotions.count()} promotions to process.")

    for promotion in promotions:
        trigger = promotion.trigger
        whatsapp_bot = getattr(promotion.organization, "whatsapp_bots", None)

        if not whatsapp_bot:
            print("Skipping promotion: no WhatsApp bot configured.")
            continue

        # Decrypt Twilio credentials
        try:
            twilio_auth_token = decrypt_data(
                whatsapp_bot.twilio_auth_token, settings.CRYPTO_PASSWORD
            )
            twilio_sid = decrypt_data(whatsapp_bot.twilio_sid, settings.CRYPTO_PASSWORD)
            twilio_number = whatsapp_bot.twilio_number
        except Exception as e:
            print(f"Skipping promotion due to credential error: {e}")
            continue

        def send_for_clients(clients_qs, template_type):
            template_message = promotion.organization.message_templates.filter(
                type=template_type
            ).first()
            if not template_message:
                print("No message template configured for this promotion.")
                return

            org_name = promotion.organization.name
            reward_label = getattr(promotion.reward, "label", "")

            # ✅ Exclude clients who already received this promotion
            already_sent_ids = PromotionSentLog.objects.filter(
                promotion=promotion
            ).values_list("client_id", flat=True)

            clients_qs = clients_qs.exclude(id__in=already_sent_ids)

            for client in clients_qs:
                to = getattr(client, "whatsapp_number", None)
                if not to:
                    continue

                content_variables = {
                    "1": (client.name or to),
                    "2": org_name,
                    "3": reward_label,
                }

                send_whatsapp_template(
                    twilio_number,
                    to,
                    twilio_sid,
                    twilio_auth_token,
                    template_message.content_sid,
                    content_variables,
                )

                # ✅ Track the sent promotion
                PromotionSentLog.objects.create(
                    promotion=promotion,
                    client=client,
                    message_template=template_message,
                )

        if trigger.type == TriggerType.YEARLY and trigger.days_before is not None:
            target_date = today + timedelta(days=trigger.days_before)

            if trigger.yearly_category == YearlyCategory.BIRTHDAY:
                clients = Client.objects.filter(
                    date_of_birth__month=target_date.month,
                    date_of_birth__day=target_date.day,
                    organization=promotion.organization,
                ).only("id", "name", "whatsapp_number")
                send_for_clients(clients, MessageTemplateType.BIRTHDAY)

            elif trigger.yearly_category == YearlyCategory.ANNIVERSARY:
                clients = Client.objects.filter(
                    anniversary_date__month=target_date.month,
                    anniversary_date__day=target_date.day,
                    organization=promotion.organization,
                ).only("id", "name", "whatsapp_number")
                send_for_clients(clients, MessageTemplateType.ANNIVERSARY)

            else:
                print(f"Unknown yearly category: {trigger.yearly_category}")

        elif (
            trigger.type == TriggerType.INACTIVITY
            and trigger.inactivity_days is not None
        ):
            cutoff_date = today - timedelta(days=trigger.inactivity_days)
            clients = (
                Client.objects.filter(
                    last_visit__lt=cutoff_date,
                    organization=promotion.organization,
                    reservations__reservation_status=ReservationStatus.COMPLETED,
                )
                .distinct()
                .only("id", "name", "whatsapp_number")
            )
            send_for_clients(clients, MessageTemplateType.INACTIVITY)

        elif (
            trigger.type == TriggerType.RESERVATION_COUNT
            and trigger.min_count is not None
        ):
            clients = (
                Client.objects.filter(organization=promotion.organization)
                .annotate(
                    res_count=Count(
                        "reservations",
                        filter=Q(
                            reservations__reservation_status=ReservationStatus.COMPLETED
                        ),
                    )
                )
                .filter(res_count__gte=trigger.min_count)
                .only("id", "name", "whatsapp_number")
            )
            send_for_clients(clients, MessageTemplateType.RESERVATION_COUNT)

        elif trigger.type == TriggerType.MENU_SELECTED:
            clients = Client.objects.filter(organization=promotion.organization).only(
                "id", "name", "whatsapp_number"
            )
            send_for_clients(clients, MessageTemplateType.MENU_SELECTED)

        else:
            print(f"Unknown or improperly configured trigger: {trigger}")


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

    print(f"Found {reservations.count()} reservations.")

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

        message_template = reservation.organization.message_templates.filter(
            type=MessageTemplateType.REMINDER
        ).first()

        if not message_template:
            print(
                f"Skipping reservation {reservation.id}: no reminder template configured."
            )
            continue

        content_variables = {
            "1": reservation.organization.name,
            "2": reservation.reservation_name,
            "3": reservation.reservation_time.strftime("%I:%M %p"),
        }

        print(
            f"Sending reservation reminder to  '{reservation.id}' ({reservation.reservation_name})"
        )
        if reservation.client.whatsapp_number:
            send_whatsapp_template(
                twilio_number,
                reservation.client.whatsapp_number,
                twilio_sid,
                twilio_auth_token,
                message_template.content_sid,
                content_variables,
            )

            # Mark reminder as sent
            reservation.booking_reminder_sent = True
            reservation.save(update_fields=["booking_reminder_sent"])
