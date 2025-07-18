def get_restaurant_media_path_prefix(instance: object, filename: str) -> str:
    return f"restaurant/{instance.name}/{filename}"
