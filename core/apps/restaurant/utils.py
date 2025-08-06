import random
import string


def get_restaurant_media_path_prefix(instance: object, filename: str) -> str:
    return f"restaurant/{instance.name}/{filename}"


def get_client_media_path_prefix(instance: object, filename: str) -> str:
    return f"client/{instance.whatsapp_number}/{filename}"


def generate_reservation_code(instance: object) -> str:
    name_part = instance.reservation_name[:3].upper().ljust(3, "X")
    random_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

    return f"{name_part}-{random_part}"
