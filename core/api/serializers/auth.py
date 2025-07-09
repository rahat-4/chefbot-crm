from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction

from rest_framework import serializers

from apps.authentication.models import RegistrationSession
from apps.authentication.choices import UserType


class UserRegistrationSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistrationSession
        fields = [
            "avatar",
            "first_name",
            "last_name",
            "email",
            "phone",
            "gender",
            "date_of_birth",
        ]

    def create(self, validated_data):
        return RegistrationSession.objects.create(
            user_type=UserType.OWNER, **validated_data
        )


class UserPasswordSetSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        password = attrs.get("password")
        confirm_password = attrs.get("confirm_password")

        if password != confirm_password:
            raise serializers.ValidationError("Passwords do not match.")

        try:
            validate_password(password)
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": e.messages})

        return attrs

    def create(self, validated_data):
        with transaction.atomic():
            session_uid = self.context["view"].kwargs.get("session_uid")
            session = RegistrationSession.objects.filter(uid=session_uid).first()

            if not session:
                raise serializers.ValidationError("Invalid session UID.")

            user = get_user_model().objects.create_user(
                email=session.email,
                password=validated_data["password"],
                first_name=session.first_name,
                last_name=session.last_name,
                phone=session.phone,
                gender=session.gender,
                date_of_birth=session.date_of_birth,
            )

            session.delete()

            return user
