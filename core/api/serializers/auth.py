from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import serializers

from apps.authentication.models import RegistrationSession
from apps.authentication.choices import UserType

User = get_user_model()


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["uid", "avatar", "first_name", "last_name", "email"]


class UserRegistrationSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistrationSession
        fields = [
            "uid",
            "avatar",
            "first_name",
            "last_name",
            "email",
            "phone",
            "gender",
            "date_of_birth",
        ]

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value

    def create(self, validated_data):
        return RegistrationSession.objects.create(
            user_type=UserType.OWNER, **validated_data
        )


class UserPasswordSetSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        errors = {}

        password = attrs.get("password")
        confirm_password = attrs.get("confirm_password")

        session_uid = self.context["view"].kwargs.get("session_uid")
        session = RegistrationSession.objects.filter(uid=session_uid).first()

        if not session:
            errors["session"] = ["Invalid session."]

        try:
            validate_password(password)
        except DjangoValidationError as e:
            errors["password"] = e.messages

        if password != confirm_password:
            errors["confirm_password"] = ["Password do not match."]

        if errors:
            raise serializers.ValidationError(errors)

        self.session = session

        return attrs

    def create(self, validated_data):
        user = User.objects.create_user(
            avatar=self.session.avatar,
            email=self.session.email,
            password=validated_data["password"],
            first_name=self.session.first_name,
            last_name=self.session.last_name,
            phone=self.session.phone,
            gender=self.session.gender,
            date_of_birth=self.session.date_of_birth,
        )

        self.session.delete()

        return user
