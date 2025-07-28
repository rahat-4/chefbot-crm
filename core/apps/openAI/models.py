from django.db import models

from common.models import BaseModel

from apps.authentication.models import Client


class ChatThread(BaseModel):
    customer = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="assistant_apis"
    )
    thread_id = models.CharField(max_length=255)
    last_used = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("thread_id", "customer")

    def __str__(self):
        return f"Thread: {self.thread_id}"
