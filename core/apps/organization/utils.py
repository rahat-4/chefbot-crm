def get_organization_media_path_prefix(instance, filename):
    return f"organization/{instance.organization.uid}/{filename}"
