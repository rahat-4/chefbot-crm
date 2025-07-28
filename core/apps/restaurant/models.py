from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.core.exceptions import ValidationError

from phonenumber_field.modelfields import PhoneNumberField

from common.models import BaseModel

from apps.authentication.models import Client
from apps.organization.models import Organization

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
)
from .utils import get_restaurant_media_path_prefix


User = get_user_model()


class Menu(BaseModel):
    image = models.ImageField(
        upload_to=get_restaurant_media_path_prefix, blank=True, null=True
    )
    name = models.CharField(
        unique=True, db_index=True, max_length=255, help_text="Title of the dish."
    )
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    ingredients = ArrayField(models.CharField(max_length=255), blank=True, null=True)
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
        verbose_name = "Dish"
        verbose_name_plural = "Dishes"

    def __str__(self):
        return self.name


class SalesLevel(BaseModel):
    """Sales level configuration for chatbot selling aggressiveness."""

    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Name of the sales level configuration.",
    )
    level = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Sales aggressiveness level (1-5)",
    )
    personalization_enabled = models.BooleanField(
        default=False, help_text="Enable personalized recommendations for (Level 4+)."
    )

    class Meta:
        verbose_name = "Sales Level Configuration"
        verbose_name_plural = "Sales Level Configurations"

    def __str__(self):
        return f"Level {self.level} - Name: {self.name}"

    def clean(self):

        if self.level == 2:
            if not self.menu_reward_type:
                raise ValidationError("Menu reward type is required for level 2.")
            if not self.menu_reward_label:
                raise ValidationError("Menu reward label is required for level 2.")


class Reward(BaseModel):
    type = models.CharField(
        max_length=20, choices=RewardType.choices, help_text="Type of the reward."
    )
    label = models.CharField(
        max_length=255, help_text="Label for the reward (e.g., 'Free Drink')."
    )
    custom_reward = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Custom reward description (if applicable).",
    )

    def __str__(self):
        return f"UID: {self.uid} | Type: {self.type}"


class PromotionTrigger(BaseModel):
    type = models.CharField(
        max_length=20, choices=TriggerType.choices, help_text="Type of the trigger."
    )
    count = models.DateTimeField()
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Description of the trigger (e.g., 'Birthday Promotion').",
    )

    def __str__(self):
        return f"UID: {self.uid} | Type: {self.type}"


class Promotion(BaseModel):
    title = models.CharField(
        max_length=255, unique=True, help_text="Title of the promotion."
    )
    message = models.TextField(
        help_text="Message displayed in the chatbot for this promotion."
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
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="promotions"
    )
    reward = models.ForeignKey(
        Reward,
        on_delete=models.CASCADE,
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
    name = models.CharField(max_length=255, unique=True)
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

    def __str__(self):
        return f"UID: {self.uid} | Name: {self.name}"


class Reservation(BaseModel):
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="reservations"
    )
    reservation_phone = PhoneNumberField(blank=True, null=True)
    reservation_date = models.DateField()
    reservation_time = models.TimeField()
    end_time = models.DateTimeField(blank=True, null=True)
    guests = models.PositiveSmallIntegerField()
    notes = models.TextField(blank=True, null=True)
    reservation_status = models.CharField(
        max_length=20,
        choices=ReservationStatus.choices,
        default=ReservationStatus.PLACED,
    )
    cancelled_by = models.CharField(
        max_length=20,
        choices=ReservationCancelledBy.choices,
        default=ReservationCancelledBy.SYSTEM,
    )
    cancellation_reason = models.TextField(blank=True, null=True)
    booking_reminder_sent = models.BooleanField(default=False)
    booking_reminder_sent_at = models.TimeField(blank=True, null=True)

    # FK
    menus = models.ManyToManyField(Menu, blank=True, related_name="reservation_menus")
    table = models.ForeignKey(
        RestaurantTable, on_delete=models.CASCADE, related_name="reservations_table"
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="organization_reservations"
    )

    class Meta:
        verbose_name = "Reservation"
        verbose_name_plural = "Reservations"

    def save(self, *args, **kwargs):
        if self.cancelled_by == ReservationStatus.CANCELLED:
            if not self.cancellation_reason:
                raise ValidationError(
                    "Cancellation reason is required for cancelled reservations."
                )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"UID: {self.uid} | Date: {self.date} | Time: {self.time}"
