from django.db import models
from django.utils.translation import gettext_lazy as _


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


class WebsiteLanguage(models.TextChoices):
    ENGLISH = "ENGLISH", _("English")
    GERMAN = "GERMAN", _("German")

    def __str__(self):
        return self.label
