from django.utils import timezone

import os
from openai import OpenAI

from apps.restaurant.models import Client, ClientMessage


client = OpenAI(api_key=os.environ.get("OPENAI_API"))


def get_or_create_thread(whatsapp_number: str) -> str:
    try:
        client_obj = Client.objects.get(whatsapp_number=whatsapp_number)

        client_obj.last_visit = timezone.now()
        client_obj.save()
        return client_obj.thread_id
    except Client.DoesNotExist:
        thread = client.beta.threads.create()

        Client.objects.create(
            thread_id=thread.id,
        )
        return thread.id
