from django.contrib.auth import get_user_model
from django.db import models

from phonenumber_field.modelfields import PhoneNumberField

from common.models import BaseModel

from .choices import OrganizationStatus, OrganizationType, DaysOfWeek
from .utils import get_organization_media_path_prefix

User = get_user_model()


class Organization(BaseModel):
    logo = models.ImageField(
        upload_to=get_organization_media_path_prefix, blank=True, null=True
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="children",
    )
    whatsapp_number = models.CharField(
        unique=True, db_index=True, max_length=255, blank=True, null=True
    )  # Needs to be modify
    whatsapp_enabled = models.BooleanField(default=False)  # Will remove in future
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=OrganizationStatus.choices,
        default=OrganizationStatus.ACTIVE,
    )
    organization_type = models.CharField(
        max_length=20,
        choices=OrganizationType.choices,
        default=OrganizationType.RESTAURANT,
    )
    country = models.CharField()  # Needs to be modify
    city = models.CharField(max_length=255)
    street = models.CharField(max_length=255)
    zip_code = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
        if self.email:
            # Normalize and lowercase email
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class OrganizationUser(BaseModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="organization_users"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="organization_users"
    )

    class Meta:
        unique_together = ("organization", "user")

    def __str__(self):
        return f"{self.organization.name} - {self.user.email}"


class OpeningHours(BaseModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="opening_hours"
    )
    day = models.CharField(max_length=20, choices=DaysOfWeek.choices)
    open_time = models.TimeField(blank=True, null=True)
    close_time = models.TimeField(blank=True, null=True)
    is_closed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.day}: {self.open_time} - {self.close_time}"


class WhatsappBot(BaseModel):
    chatbot_name = models.CharField(max_length=255)
    sales_level = models.PositiveSmallIntegerField(default=1)
    openai_key = models.CharField(max_length=255)
    assistant_id = models.CharField(unique=True, max_length=255)
    twilio_sid = models.CharField(unique=True, max_length=255)
    twilio_auth_token = models.CharField(unique=True, max_length=255)
    whatsapp_sender = models.CharField(max_length=100)

    # OneToOneField
    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, related_name="whatsapp_bots"
    )

    class Meta:
        unique_together = (
            "organization",
            "openai_key",
            "assistant_id",
            "twilio_sid",
            "twilio_auth_token",
            "whatsapp_sender",
        )

    def __str__(self):
        return self.chatbot_name
