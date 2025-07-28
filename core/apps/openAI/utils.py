from django.utils import timezone

import os
from openai import OpenAI

from apps.authentication.models import Client

from .models import ChatThread

client = OpenAI(api_key=os.environ.get("OPENAI_API"))


def get_or_create_thread(phone_number: str) -> str:
    customer = Client.objects.filter(phone=phone_number).first()

    if not customer:
        customer = Client.objects.create(phone=phone_number)

    try:
        thread_obj = ChatThread.objects.get(customer=customer)

        thread_obj.last_used = timezone.now()
        thread_obj.save()
        return thread_obj.thread_id
    except ChatThread.DoesNotExist:
        thread = client.beta.threads.create()

        ChatThread.objects.create(
            customer=customer,
            thread_id=thread.id,
        )
        return thread.id
