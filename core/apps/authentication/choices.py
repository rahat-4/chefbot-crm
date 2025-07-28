from django.db import models


class UserStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    ACTIVE = "ACTIVE", "Active"
    BANNED = "BANNED", "Banned"
    DELETED = "DELETED", "Deleted"


class UserGender(models.TextChoices):
    MALE = "MALE", "Male"
    FEMALE = "FEMALE", "Female"
    OTHER = "OTHER", "Other"


class UserType(models.TextChoices):
    ADMIN = "ADMIN", "Admin"
    OWNER = "OWNER", "Owner"
    CUSTOMER = "CUSTOMER", "Customer"


class ClientSource(models.TextChoices):
    WHATSAPP = "WHATSAPP", "WhatsApp"
    MANUAL = "MANUAL", "Manual"


class ClientMessageRole(models.TextChoices):
    USER = "USER", "User"
    ASSISTANT = "ASSISTANT", "Assistant"
