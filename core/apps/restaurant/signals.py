from django.db.models.signals import post_save
from django.dispatch import receiver

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import ClientMessage


@receiver(post_save, sender=ClientMessage)
def send_realtime_update(sender, instance, created, **kwargs):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "realtime_updates",
        {
            "type": "chat_message",
            "data": {
                "action": "created" if created else "updated",
                "model": sender.__name__,
                "data": {
                    # "uid": str(instance.uid),
                    # "name": getattr(instance.client, "name", None),
                    "role": getattr(instance, "role", None),
                    "message": getattr(instance, "message", None),
                    "sent_at": (
                        getattr(instance, "sent_at", None).isoformat()
                        if getattr(instance, "sent_at", None)
                        else None
                    ),
                },
            },
        },
    )
