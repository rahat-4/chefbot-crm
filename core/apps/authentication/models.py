from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone

from phonenumber_field.modelfields import PhoneNumberField
from django.contrib.postgres.fields import ArrayField

from common.models import BaseModel

from .choices import UserGender, UserStatus, UserType
from .managers import UserManager
from .utils import get_user_media_path_prefix


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    phone = PhoneNumberField(unique=True, blank=True, null=True)
    email = models.EmailField(max_length=255, unique=True)
    avatar = models.ImageField(
        "Avatar",
        upload_to=get_user_media_path_prefix,
        blank=True,
        null=True,
    )
    gender = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=UserGender.choices,
        default=UserGender.MALE,
    )
    date_of_birth = models.DateField(blank=True, null=True)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(blank=True, null=True)
    status = models.CharField(
        max_length=10,
        choices=UserStatus.choices,
        default=UserStatus.ACTIVE,
    )
    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        default=UserType.OWNER,
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return f"UID: {self.uid} | Email: {self.email}"


class RegistrationSession(BaseModel):
    avatar = models.ImageField(
        "Avatar",
        upload_to=get_user_media_path_prefix,
        blank=True,
        null=True,
    )
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    phone = PhoneNumberField(blank=True, null=True)
    email = models.EmailField(max_length=255, unique=True)
    gender = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=UserGender.choices,
        default=UserGender.MALE,
    )
    date_of_birth = models.DateField(blank=True, null=True)
    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        default=UserType.OWNER,
    )

    # # Organization
    # organization_logo = models.ImageField(
    #     upload_to=get_user_media_path_prefix, blank=True, null=True
    # )
    # organization_name = models.CharField(max_length=255)
    # organization_phone = PhoneNumberField(unique=True, blank=True, null=True)
    # organization_email = models.EmailField(max_length=255, unique=True)
    # organization_description = models.TextField(blank=True, null=True)
    # organization_website = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"UID: {self.uid} | User Email: {self.email}"


class Customer(BaseModel):
    avatar = models.ImageField(
        "Avatar",
        upload_to=get_user_media_path_prefix,
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=255, blank=True, null=True)
    phone = PhoneNumberField(unique=True)
    date_of_birth = models.DateField(blank=True, null=True)
    last_visit = models.DateTimeField(blank=True, null=True)
    preferences = ArrayField(models.CharField(max_length=255), blank=True, null=True)
    allergens = ArrayField(models.CharField(max_length=255), blank=True, null=True)
    special_notes = models.TextField(blank=True, null=True)
