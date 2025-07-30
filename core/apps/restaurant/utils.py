def get_restaurant_media_path_prefix(instance: object, filename: str) -> str:
    return f"restaurant/{instance.name}/{filename}"


def get_client_media_path_prefix(instance: object, filename: str) -> str:
    return f"client/{instance.whatsapp_number}/{filename}"
