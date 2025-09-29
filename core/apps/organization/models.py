from django.contrib.auth import get_user_model
from django.db import models

from phonenumber_field.modelfields import PhoneNumberField
from django.contrib.postgres.fields import ArrayField

from common.models import BaseModel

from .choices import (
    ChatbotTone,
    DaysOfWeek,
    OrganizationLanguage,
    OrganizationStatus,
    OrganizationType,
    ReservationDuration,
    ReservationReminder,
    MessageTemplateType,
)
from .managers import OrganizationQuerySet
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
    phone = PhoneNumberField(unique=True, db_index=True, blank=True, null=True)
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
    organization_language = models.CharField(
        max_length=20,
        choices=OrganizationLanguage.choices,
        default=OrganizationLanguage.ENGLISH,
    )
    country = models.CharField()  # Needs to be modify
    city = models.CharField(max_length=255)
    street = models.CharField(max_length=255)
    zip_code = models.CharField(max_length=255)

    # For restaurants
    reservation_booking_reminder = models.PositiveIntegerField(
        choices=ReservationReminder.choices, default=ReservationReminder.MINUTES_30
    )

    objects = OrganizationQuerySet.as_manager()

    def save(self, *args, **kwargs):
        if self.email:
            # Normalize and lowercase email
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.uid}"


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
    opening_start_time = models.TimeField(blank=True, null=True)
    opening_end_time = models.TimeField(blank=True, null=True)
    break_start_time = models.TimeField(blank=True, null=True)
    break_end_time = models.TimeField(blank=True, null=True)
    is_closed = models.BooleanField(default=False)

    def __str__(self):
        return f"Restaurant: {self.organization.name} - {self.day}: Closed: {self.is_closed}"


class WhatsappBot(BaseModel):
    chatbot_name = models.CharField(max_length=255)
    chatbot_language = models.CharField(
        max_length=20,
        choices=OrganizationLanguage.choices,
        default=OrganizationLanguage.ENGLISH,
    )
    chatbot_tone = models.CharField(
        max_length=20,
        choices=ChatbotTone.choices,
        default=ChatbotTone.CASUAL,
    )
    chatbot_custom_tone = models.TextField(blank=True, null=True)
    max_response_length = models.PositiveIntegerField(default=150)
    sales_level = models.OneToOneField(
        "restaurant.SalesLevel",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="whatsapp_sales_levels",
    )
    openai_key = models.JSONField(default=dict)
    assistant_id = models.JSONField(default=dict)
    twilio_sid = models.JSONField(default=dict)
    twilio_auth_token = models.JSONField(default=dict)
    twilio_number = models.CharField(max_length=100)
    hashed_key = models.CharField(max_length=500)

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
            "twilio_number",
        )

    def __str__(self):
        return f"{self.chatbot_name} - {self.uid}"


class MessageTemplate(BaseModel):
    name = models.CharField(max_length=255)
    content_sid = models.CharField(max_length=255)
    content = models.TextField()
    content_variables = models.JSONField(default=dict)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="message_templates"
    )
    type = models.CharField(
        max_length=20,
        choices=MessageTemplateType.choices,
        default=MessageTemplateType.REMINDER,
    )

    class Meta:
        verbose_name = "Message Template"
        verbose_name_plural = "Message Templates"
        unique_together = ["organization", "name"]

    def __str__(self):
        return f"UID: {self.uid} | Name: {self.name} | Organization: {self.organization.name}"
