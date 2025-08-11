import random
import re
import string

from django.core.exceptions import ValidationError


def get_restaurant_media_path_prefix(instance: object, filename: str) -> str:
    return f"restaurant/{instance.name}/{filename}"


def get_client_media_path_prefix(instance: object, filename: str) -> str:
    return f"client/{instance.whatsapp_number}/{filename}"


def generate_reservation_code(instance: object) -> str:
    name_part = instance.reservation_name[:3].upper().ljust(3, "X")
    random_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

    return f"{name_part}-{random_part}"


def validate_ingredients(value):
    """Validate ingredients format: {ingredient_name: quantity_with_unit}"""
    if not isinstance(value, dict):
        raise ValidationError("Ingredients must be a dictionary.")

    # Pattern to match quantity with unit (e.g., "500g", "2cups", "1.5kg", "250ml")
    quantity_pattern = r"^[0-9]*\.?[0-9]+[a-zA-Z]+$"

    for ingredient, quantity in value.items():
        if not isinstance(ingredient, str) or not isinstance(quantity, str):
            raise ValidationError("Ingredient name and quantity must be strings.")
        if not ingredient.strip():
            raise ValidationError("Ingredient name cannot be empty.")
        if not quantity.strip():
            raise ValidationError("Ingredient quantity cannot be empty.")
        if not re.match(quantity_pattern, quantity.strip()):
            raise ValidationError(
                f"Invalid quantity format for '{ingredient}'. Use format like '500g', '2cups', '1.5kg'"
            )
