from django.db import transaction

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from decouple import config

from common.openAI.generate_nutritions import generate_nutrition_info
from common.crypto import encrypt_data, decrypt_data

from apps.organization.choices import OrganizationType
from apps.organization.models import (
    Organization,
    OrganizationUser,
    OpeningHours,
    WhatsappBot,
)
from apps.restaurant.choices import CategoryChoices, ClassificationChoices
from apps.restaurant.models import (
    Menu,
    Reward,
    Promotion,
    PromotionTrigger,
    RestaurantTable,
)


class OpeningHoursSerializer(serializers.ModelSerializer):

    class Meta:
        model = OpeningHours
        exclude = ["organization", "created_at", "updated_at"]


class RestaurantSerializer(serializers.ModelSerializer):
    opening_hours = OpeningHoursSerializer(many=True)

    class Meta:
        model = Organization
        fields = [
            "uid",
            "logo",
            "name",
            "whatsapp_number",
            "whatsapp_enabled",
            "email",
            "description",
            "website",
            "country",
            "city",
            "street",
            "zip_code",
            "opening_hours",
        ]

    def validate(self, attrs):
        errors = {}

        if attrs.get("whatsapp_enabled") and not attrs.get("whatsapp_number"):
            errors["whatsapp_number"] = ["This field is required."]

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def create(self, validated_data):
        with transaction.atomic():
            opening_hours = validated_data.pop("opening_hours", [])
            organization = Organization.objects.create(
                organization_type=OrganizationType.RESTAURANT, **validated_data
            )

            OrganizationUser.objects.create(
                organization=organization,
                user=self.context["request"].user,
            )

            for opening_hour in opening_hours:
                OpeningHours.objects.create(organization=organization, **opening_hour)
            return organization

    def update(self, instance, validated_data):
        with transaction.atomic():
            opening_hours = validated_data.pop("opening_hours", [])

            for attr, value in validated_data.items():
                setattr(instance, attr, value)

            instance.save()

            # Opening Hours
            if opening_hours is not None:
                OpeningHours.objects.filter(organization=instance).delete()
                for opening_hour in opening_hours:
                    OpeningHours.objects.create(organization=instance, **opening_hour)
            return instance


class RestaurantTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantTable
        fields = [
            "uid",
            "name",
            "capacity",
            "category",
            "position",
            "status",
        ]


class RestaurantMenuSerializer(serializers.ModelSerializer):

    class Meta:
        model = Menu
        fields = [
            "uid",
            "image",
            "name",
            "description",
            "price",
            "ingredients",
            "category",
            "classification",
            "allergens",
            "macronutrients",
            "upselling_priority",
            "enable_upselling",
            "recommended_combinations",
        ]

    def create(self, validated_data):
        ingredients = validated_data.get("ingredients", [])

        if ingredients:
            response = generate_nutrition_info(ingredients)

            validated_data["allergens"] = response["allergens"]
            validated_data["macronutrients"] = response["macronutrients"]

        return super().create(validated_data)

    def update(self, instance, validated_data):
        ingredients = validated_data.get("ingredients", [])

        if ingredients:
            response = generate_nutrition_info(ingredients)

            validated_data["allergens"] = response["allergens"]
            validated_data["macronutrients"] = response["macronutrients"]

        return super().update(instance, validated_data)


class RestaurantMenuAllergensSerializer(serializers.ModelSerializer):

    class Meta:
        model = Menu
        fields = ["allergens"]


class RestaurantWhatsAppBotSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsappBot
        fields = [
            "uid",
            "chatbot_name",
            "sales_level",
            "openai_key",
            "assistant_id",
            "twilio_sid",
            "twilio_auth_token",
            "whatsapp_sender",
        ]

    def validate(self, attrs):
        organization_uid = self.context["view"].kwargs.get("restaurant_uid")

        whatsappbot = WhatsappBot.objects.filter(
            organization__uid=organization_uid
        ).first()

        if whatsappbot:
            raise ValidationError(
                {"chatbot_name": "A WhatsappBot already exists for this organization."}
            )

        return attrs

    def create(self, validated_data):
        crypto_password = config("CRYPTO_PASSWORD")

        validated_data["openai_key"] = encrypt_data(
            validated_data["openai_key"], crypto_password
        )
        validated_data["assistant_id"] = encrypt_data(
            validated_data["assistant_id"], crypto_password
        )
        validated_data["twilio_sid"] = encrypt_data(
            validated_data["twilio_sid"], crypto_password
        )
        validated_data["twilio_auth_token"] = encrypt_data(
            validated_data["twilio_auth_token"], crypto_password
        )

        return super().create(validated_data)


class RestaurantWhatsAppBotUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsappBot
        fields = [
            "sales_level",
        ]


class RewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reward
        fields = [
            "uid",
            "type",
            "label",
            "custom_reward",
        ]


class PromotionTriggerSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromotionTrigger
        fields = ["uid", "type", "count", "description"]


class RestaurantPromotionSerializer(serializers.ModelSerializer):
    reward = RewardSerializer()
    trigger = PromotionTriggerSerializer()

    class Meta:
        model = Promotion
        fields = [
            "uid",
            "title",
            "message",
            "reward",
            "trigger",
            "valid_from",
            "valid_to",
            "is_enabled",
        ]

    def create(self, validated_data):
        with transaction.atomic():
            reward_data = validated_data.pop("reward", None)
            trigger_data = validated_data.pop("trigger", None)

            reward = Reward.objects.create(**reward_data) if reward_data else None
            trigger = (
                PromotionTrigger.objects.create(**trigger_data)
                if trigger_data
                else None
            )

            promotion = Promotion.objects.create(
                **validated_data, reward=reward, trigger=trigger
            )
            return promotion
