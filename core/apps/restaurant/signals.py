from django.db.models.signals import post_save
from django.dispatch import receiver

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import ClientMessage


@receiver(post_save, sender=ClientMessage)
def send_realtime_update(sender, instance, created, **kwargs):
    channel_layer = get_channel_layer()
    client_uid = str(instance.client.uid)
    async_to_sync(channel_layer.group_send)(
        f"realtime_updates_{client_uid}",
        {
            "type": "chat_message",
            "data": {
                "action": "created" if created else "updated",
                "model": sender.__name__,
                "data": {
                    "uid": str(instance.uid),
                    "client": instance.client.whatsapp_number,
                    "role": instance.role,
                    "message": instance.message,
                    "media_url": instance.media_url,
                    "sent_at": (
                        instance.sent_at.isoformat() if instance.sent_at else None
                    ),
                },
            },
        },
    )
