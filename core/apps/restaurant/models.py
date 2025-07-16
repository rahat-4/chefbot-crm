from django.db import models

from django.contrib.postgres.fields import ArrayField

from common.models import BaseModel

from apps.organization.models import Organization

from .choices import CategoryChoices, ClassificationChoices, MenuStatus
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
