from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from common.models import BaseModel

from apps.organization.models import Organization

from .choices import CategoryChoices, ClassificationChoices, MenuStatus, MenuRewardType
from .utils import get_restaurant_media_path_prefix


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

    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, related_name="sales_level"
    )
    level = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Sales aggressiveness level (1-5)",
    )
    menu_reward_type = models.CharField(
        max_length=20,
        choices=MenuRewardType.choices,
        blank=True,
        null=True,
        help_text="Menu reward configuration for (Level 2+)",
    )
    menu_reward_label = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Label used in chatbot messages.",
    )
    personalization_enabled = models.BooleanField(
        default=False, help_text="Enable personalized recommendations for (Level 4+)."
    )

    class Meta:
        verbose_name = "Sales Level Configuration"
        verbose_name_plural = "Sales Level Configurations"

    def __str__(self):
        return f"{self.organization.name} - Level {self.level}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.level == 2:
            if not self.menu_reward_type:
                raise ValidationError("Menu reward type is required for level 2.")

    @property
    def is_upselling_active(self):
        """Check if upselling is enabled (Level 3+)."""
        return self.level >= 3

    @property
    def is_personalization_available(self):
        """Check if personalization is available (Level 4+)."""
        return self.level >= 4

    @property
    def is_promotion_module_available(self):
        """Check if promotion module is available (Level 5)."""
        return self.level == 5
