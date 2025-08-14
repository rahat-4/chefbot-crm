import random

from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.core.exceptions import ValidationError

from phonenumber_field.modelfields import PhoneNumberField

from common.models import BaseModel

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
    ClientMessageRole,
    ClientSource,
)
from .utils import (
    get_restaurant_media_path_prefix,
    get_client_media_path_prefix,
    generate_reservation_code,
    validate_ingredients,
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
    price = models.DecimalField(max_digits=10, decimal_places=2)
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
        return f"{self.organization.name} - {self.name}"


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
    # Menu reward for Level 2+
    menu_reward = models.ForeignKey(
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

        # Level 2+ requires menu reward
        if self.level >= 2 and not self.menu_reward:
            raise ValidationError("Menu reward is required for level 2 and above.")

        # Level 1 shouldn't have menu reward
        if self.level == 1 and self.menu_reward:
            raise ValidationError("Level 1 should not have a menu reward.")

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
        max_length=100,  # Max 100 chars as per requirements
        help_text="Label for the reward (e.g., 'Free tiramisu for pre-ordered menu').",
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="rewards"
    )

    def __str__(self):
        return f"{self.get_type_display()}: {self.label}"

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

    def __str__(self):
        return f"UID: {self.uid} | Whatsapp: {self.whatsapp_number}"


class ClientMessage(BaseModel):
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="client_messages"
    )
    role = models.CharField(
        max_length=20,
        choices=ClientMessageRole.choices,
        default=ClientMessageRole.ASSISTANT,
    )
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"UID: {self.uid} | Role: {self.role}"


class Reservation(BaseModel):
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="reservations"
    )
    reservation_code = models.CharField(max_length=10, unique=True, db_index=True)
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
        self.reservation_code = generate_reservation_code(self)
        if self.cancelled_by == ReservationStatus.CANCELLED:
            if not self.cancellation_reason:
                raise ValidationError(
                    "Cancellation reason is required for cancelled reservations."
                )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"UID: {self.uid} | Date: {self.reservation_date} | Time: {self.reservation_time}"
