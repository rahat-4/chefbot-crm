def get_media_path_prefix(instance: object, filename: str) -> str:
    return f"restaurant/{instance.name}/{filename}"
