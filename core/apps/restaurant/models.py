import random

from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from phonenumber_field.modelfields import PhoneNumberField

from common.models import BaseModel

from apps.organization.models import Organization, MessageTemplate
from datetime import datetime, timedelta

from .choices import (
    CategoryChoices,
    ClassificationChoices,
    MenuStatus,
    RewardType,
    TriggerType,
    ReservationStatus,
    ReservationCancelledBy,
    TableCategory,
    TableStatus,
    ClientMessageRole,
    ClientSource,
    RestaurantDocumentType,
    YearlyCategory,
    PromotionSentLogStatus,
    RewardCategory,
    OrganizationLanguage,
    ChatbotTone,
)
from .utils import (
    get_restaurant_media_path_prefix,
    get_client_media_path_prefix,
    validate_ingredients,
    unique_number_generator,
)


User = get_user_model()


class Menu(BaseModel):
    image = models.ImageField(
        upload_to=get_restaurant_media_path_prefix, blank=True, null=True
    )
    name = models.CharField(
        db_index=True, max_length=255, help_text="Title of the dish."
    )
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    ingredients = models.JSONField(
        default=dict,
        blank=True,
        validators=[validate_ingredients],
        help_text='Ingredients with quantities, e.g., {"milk": "500ml", "onion": "200g"}',
    )
    category = models.CharField(
        max_length=30, choices=CategoryChoices.choices, default=CategoryChoices.STARTERS
    )
    classification = models.CharField(
        max_length=30,
        choices=ClassificationChoices.choices,
        default=ClassificationChoices.MEAT,
    )
    status = models.CharField(
        max_length=30, choices=MenuStatus.choices, default=MenuStatus.ACTIVE
    )

    # AI-generated
    allergens = ArrayField(models.CharField(max_length=255), blank=True, null=True)
    macronutrients = models.JSONField(default=dict, blank=True, null=True)

    # Upselling
    upselling_priority = models.PositiveSmallIntegerField(default=1)
    enable_upselling = models.BooleanField(default=False)

    # Recommended combinations
    recommended_combinations = models.ManyToManyField(
        "self", blank=True, symmetrical=False
    )

    # FK
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="menus"
    )

    class Meta:
        verbose_name = "Menu"
        verbose_name_plural = "Menus"

        unique_together = ["organization", "name"]

    def get_formatted_ingredients_for_ai(self):
        """Convert ingredients dict to formatted list for AI processing"""
        if not self.ingredients:
            return []

        formatted_ingredients = []
        for ingredient, quantity in self.ingredients.items():
            formatted_ingredients.append(f"{ingredient} ({quantity})")

        return formatted_ingredients

    def __str__(self):
        return f"{self.organization.name} - {self.name} - Category: {self.category} - Classification: {self.classification} - Upselling: {self.enable_upselling} - Priority: {self.upselling_priority}"


class SalesLevel(BaseModel):
    """Sales level configuration for chatbot selling aggressiveness."""

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="sales_levels"
    )
    name = models.CharField(
        max_length=255,
        help_text="Name of the sales level configuration.",
    )
    level = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Sales aggressiveness level (1-5)",
    )
    personalization_enabled = models.BooleanField(
        default=False, help_text="Enable personalized recommendations (Level 4+)."
    )
    reward_enabled = models.BooleanField(
        default=False, help_text="Indicates if a reward has been added for this level."
    )
    priority_dish_enabled = models.BooleanField(
        default=False, help_text="Enable priority dish promotion (Level 3+)."
    )
    # Reward for Level 2+
    reward = models.ForeignKey(
        "Reward",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales_levels",
        help_text="Menu reward for level 2+",
    )

    class Meta:
        verbose_name = "Sales Level Configuration"
        verbose_name_plural = "Sales Level Configurations"
        unique_together = ["organization", "level"]

    def __str__(self):
        return f"Level {self.level} - {self.name} ({self.organization.name})"

    def clean(self):
        super().clean()

        # Level 2+ requires reward
        if self.level >= 2 and not self.reward:
            raise ValidationError("Reward is required for level 2 and above.")

        # Level 1 shouldn't have reward
        if self.level == 1 and self.reward:
            raise ValidationError("Level 1 should not have a reward.")

        # Personalization only for level 4+
        if self.personalization_enabled and self.level < 4:
            raise ValidationError(
                "Personalization can only be enabled for level 4 and above."
            )


class Reward(BaseModel):
    type = models.CharField(
        max_length=20, choices=RewardType.choices, help_text="Type of the reward."
    )
    label = models.CharField(
        max_length=24,
        help_text="Label for the reward (e.g., 'Free tiramisu for pre-ordered menu').",
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="rewards"
    )
    promo_code = models.CharField(max_length=100, unique=True, blank=True, null=True)
    reward_category = models.CharField(
        max_length=20, choices=RewardCategory.choices, default=RewardCategory.PROMOTION
    )

    def save(self, *args, **kwargs):
        if not self.promo_code:
            type_part = self.type[:3].upper()
            self.promo_code = f"{type_part}{unique_number_generator(self)}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_type_display()}: {self.label} , Category: {self.reward_category}"


class PromotionTrigger(BaseModel):
    type = models.CharField(
        max_length=20, choices=TriggerType.choices, help_text="Type of the trigger."
    )
    yearly_category = models.CharField(
        max_length=20,
        choices=YearlyCategory.choices,
        blank=True,
        null=True,
        help_text="Category for yearly triggers (e.g., Birthday, Anniversary).",
    )
    days_before = models.PositiveSmallIntegerField(
        default=0,
        blank=True,
        null=True,
        help_text="Number of days before the event to trigger the promotion.",
    )
    min_count = models.PositiveIntegerField(
        default=0,
        blank=True,
        null=True,
        help_text="Minimum reservation count to trigger the promotion.",
    )
    inactivity_days = models.PositiveIntegerField(
        default=0,
        blank=True,
        null=True,
        help_text="Number of inactivity days to trigger the promotion.",
    )
    menus = models.ManyToManyField(Menu, blank=True, related_name="promotion_triggers")

    def clean(self):
        super().clean()

        if self.type == TriggerType.YEARLY:
            if not self.yearly_category:
                raise ValidationError(
                    {
                        "yearly_category": "yearly_category is required when type is YEARLY."
                    }
                )
            if self.yearly_category in (
                YearlyCategory.BIRTHDAY,
                YearlyCategory.ANNIVERSARY,
            ):
                if self.days_before is None:
                    raise ValidationError(
                        {
                            "days_before": f"days_before is required when yearly_category is {self.yearly_category}."
                        }
                    )

        # Don’t validate many-to-many here (menus) if instance is new (no pk)
        if self.type == TriggerType.INACTIVITY:
            if self.inactivity_days is None or self.inactivity_days <= 0:
                raise ValidationError(
                    {
                        "inactivity_days": "inactivity_days must be a positive integer for INACTIVITY trigger."
                    }
                )

        if self.type == TriggerType.RESERVATION_COUNT:
            if self.min_count is None or self.min_count <= 0:
                raise ValidationError(
                    {
                        "min_count": "min_count must be a positive integer for RESERVATION_COUNT trigger."
                    }
                )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"UID: {self.uid} | Type: {self.type}"


class Promotion(BaseModel):
    title = models.CharField(
        max_length=255, unique=True, help_text="Title of the promotion."
    )
    valid_from = models.DateField(
        help_text="Start date of the promotion.",
    )
    valid_to = models.DateField(
        help_text="End date of the promotion.",
    )
    is_enabled = models.BooleanField(
        default=True, help_text="Is the promotion currently active?"
    )

    # FK
    message_template = models.ForeignKey(
        MessageTemplate,
        on_delete=models.CASCADE,
        related_name="promotion_templates",
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="promotions"
    )
    reward = models.ForeignKey(
        Reward,
        on_delete=models.SET_NULL,
        related_name="promotions",
        blank=True,
        null=True,
    )
    trigger = models.ForeignKey(
        PromotionTrigger, on_delete=models.CASCADE, related_name="promotions"
    )

    class Meta:
        verbose_name = "Promotion"
        verbose_name_plural = "Promotions"

    def __str__(self):
        return f"UID: {self.uid} | Title: {self.title} | Active: {self.is_enabled}"


class RestaurantTable(BaseModel):
    name = models.CharField(max_length=255)
    capacity = models.PositiveSmallIntegerField()
    category = models.CharField(
        max_length=20, choices=TableCategory.choices, default=TableCategory.SINGLE
    )
    position = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=TableStatus.choices,
        default=TableStatus.AVAILABLE,
    )

    # FK
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="tables"
    )

    class Meta:
        verbose_name = "Table"
        verbose_name_plural = "Tables"
        unique_together = ["organization", "name"]

    def __str__(self):
        return f"UID: {self.uid} | Name: {self.name} | Restaurant: {self.organization.name}"


class Client(BaseModel):
    avatar = models.ImageField(
        "Avatar",
        upload_to=get_client_media_path_prefix,
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=255, blank=True, null=True)
    phone = PhoneNumberField(unique=True, blank=True, null=True)
    whatsapp_number = models.CharField(max_length=100)
    email = models.EmailField(max_length=255, unique=True, blank=True, null=True)
    source = models.CharField(
        max_length=20, choices=ClientSource.choices, default=ClientSource.WHATSAPP
    )
    date_of_birth = models.DateField(blank=True, null=True)
    anniversary_date = models.DateField(blank=True, null=True)
    last_visit = models.DateTimeField(blank=True, null=True)
    preferences = ArrayField(models.CharField(max_length=255), blank=True, null=True)
    allergens = ArrayField(models.CharField(max_length=255), blank=True, null=True)
    special_notes = models.TextField(blank=True, null=True)
    thread_id = models.CharField(max_length=255, blank=True, null=True)

    organization = models.ForeignKey(
        "organization.Organization",
        on_delete=models.CASCADE,
        related_name="organization_clients",
    )

    def save(self, *args, **kwargs):
        if self.whatsapp_number and self.whatsapp_number.startswith("whatsapp:"):
            self.whatsapp_number = self.whatsapp_number.replace("whatsapp:", "").strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"UID: {self.uid} | Whatsapp: {self.whatsapp_number} | Thread ID: {self.thread_id} | Restaurant: {self.organization.name}"


class PromotionSentLog(BaseModel):
    promotion = models.ForeignKey(
        Promotion, on_delete=models.CASCADE, related_name="sent_logs"
    )
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="promotion_logs"
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    message_template = models.ForeignKey(
        MessageTemplate, null=True, blank=True, on_delete=models.SET_NULL
    )
    status = models.CharField(
        max_length=20,
        choices=PromotionSentLogStatus.choices,
        default=PromotionSentLogStatus.SENT,
    )

    class Meta:
        unique_together = ("promotion", "client")

    def is_expired(self):
        return (
            self.promotion.valid_to < timezone.now().date()
            or self.status == PromotionSentLogStatus.USED
        )

    def __str__(self):
        return f"Client: {self.client.whatsapp_number} | Trigger Type: {self.promotion.trigger.type} | Yearly Category: {self.promotion.trigger.yearly_category} | Sent At: {self.sent_at}"


class Reservation(BaseModel):
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="reservations"
    )
    reservation_name = models.CharField(max_length=255, blank=True, null=True)
    reservation_phone = models.CharField(max_length=100, blank=True, null=True)
    reservation_date = models.DateField()
    reservation_time = models.TimeField()
    reservation_end_time = models.DateTimeField(blank=True, null=True)
    reservation_reason = models.TextField(blank=True, null=True)
    guests = models.PositiveSmallIntegerField()
    notes = models.TextField(blank=True, null=True)
    reservation_status = models.CharField(
        max_length=20,
        choices=ReservationStatus.choices,
        default=ReservationStatus.PLACED,
    )
    cancelled_by = models.CharField(
        max_length=20,
        blank=True,
        choices=ReservationCancelledBy.choices,
    )
    cancellation_reason = models.TextField(blank=True, null=True)
    booking_reminder_sent = models.BooleanField(default=False)
    booking_reminder_sent_at = models.DateTimeField(blank=True, null=True)

    # FK
    menus = models.ManyToManyField(Menu, blank=True, related_name="reservation_menus")
    table = models.ForeignKey(
        RestaurantTable, on_delete=models.CASCADE, related_name="reservations_table"
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="organization_reservations"
    )
    promo_code = models.ForeignKey(
        Reward,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="reservation_promo_code",
    )
    sales_level_reward = models.ForeignKey(
        Reward,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="reservation_sales_level_reward",
    )

    class Meta:
        verbose_name = "Reservation"
        verbose_name_plural = "Reservations"
        ordering = ["-created_at"]

    def __str__(self):
        return f"UID: {self.uid} | Date: {self.reservation_date} | Time: {self.reservation_time} | Restaurant: {self.organization.name} | Status: {self.reservation_status}"

    def save(self, *args, **kwargs):
        """
        Sets the booking_reminder_sent_at field to 30 minutes before the reservation.
        """
        # Combine reservation_date and reservation_time into a single datetime object
        naive_datetime = datetime.combine(self.reservation_date, self.reservation_time)

        # Make timezone-aware
        aware_datetime = timezone.make_aware(
            naive_datetime, timezone.get_current_timezone()
        )

        # Calculate and set booking_reminder_sent_at based on organization's reservation_booking_reminder
        self.booking_reminder_sent_at = aware_datetime - timedelta(
            minutes=self.organization.reservation_booking_reminder
        )

        super().save(*args, **kwargs)


class ClientMessage(BaseModel):
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="client_messages",
    )
    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="reservation_messages",
    )
    role = models.CharField(
        max_length=20,
        choices=ClientMessageRole.choices,
        default=ClientMessageRole.ASSISTANT,
    )
    message = models.TextField()
    media_url = models.URLField(blank=True, null=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"UID: {self.uid} | Role: {self.role}"


class RestaurantDocument(BaseModel):
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="documents"
    )
    name = models.CharField(max_length=255)
    document_type = models.CharField(
        max_length=10,
        choices=RestaurantDocumentType.choices,
        default=RestaurantDocumentType.PDF,
    )
    file = models.FileField(
        upload_to=get_restaurant_media_path_prefix,
        help_text="Upload PDF, DOCX, or image file.",
    )

    class Meta:
        verbose_name = "Restaurant Document"
        verbose_name_plural = "Restaurant Documents"

    def __str__(self):
        return f"{self.name} ({self.document_type}) - {self.organization.name}"


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
        on_delete=models.CASCADE,
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
            "twilio_sid",
            "twilio_auth_token",
            "twilio_number",
        )

    def __str__(self):
        return f"{self.chatbot_name} - {self.uid}, Restaurant: {self.organization.name}"
