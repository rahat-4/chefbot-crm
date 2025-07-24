from django.core.management.base import BaseCommand

from apps.organization.models import Organization
from apps.restaurant.models import SalesLevel


class Command(BaseCommand):
    help = "Create default sales levels for all restaurants"

    def handle(self, *args, **kwargs):
        SalesLevel.objects.all().delete()

        sales_level_names = [
            "Reservations only (no additional input required)",
            "Configuration of menu reward (dropdown + text field)",
            "Prioritization section becomes visible (rate dishes)",
            "Checkbox “Enable personalized recommendations",
            "Promotion module (rule builder) is unlocked",
        ]

        SalesLevel.objects.bulk_create(
            [
                SalesLevel(
                    name=name,
                    level=index + 1,
                )
                for index, name in enumerate(sales_level_names)
            ]
        )
