import logging

from django.db import transaction

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from decouple import config

from common.openAI.generate_nutritions import generate_nutrition_info
from common.crypto import encrypt_data, decrypt_data, hash_key

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


logger = logging.getLogger(__name__)


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
            if opening_hours != []:
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
    recommended_combinations = serializers.SlugRelatedField(
        queryset=Menu.objects.none(),
        many=True,
        slug_field="uid",
    )

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        restaurant = self._get_restaurant_from_context()
        if restaurant:
            self.fields["recommended_combinations"].queryset = Menu.objects.filter(
                organization=restaurant
            )

    def _get_restaurant_from_context(self):
        view = self.context.get("view")
        if not view:
            return None
        restaurant_uid = view.kwargs.get("restaurant_uid")
        return Organization.objects.filter(uid=restaurant_uid).first()

    def validate(self, attrs):
        errors = {}
        restaurant = self._get_restaurant_from_context()

        if not restaurant:
            errors["restaurant"] = ["Invalid restaurant."]
        elif Menu.objects.filter(
            organization=restaurant, name=attrs.get("name")
        ).exists():
            errors["name"] = [
                "A menu with this name already exists in this restaurant."
            ]

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["recommended_combinations"] = [
            menu.name for menu in instance.recommended_combinations.all()
        ]
        return representation

    def _auto_generate_nutrition_info(self, validated_data):
        ingredients = validated_data.get("ingredients", [])
        if ingredients:
            response = generate_nutrition_info(ingredients)
            validated_data["allergens"] = response.get("allergens", [])
            validated_data["macronutrients"] = response.get("macronutrients", {})
        return validated_data

    def create(self, validated_data):
        validated_data = self._auto_generate_nutrition_info(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self._auto_generate_nutrition_info(validated_data)
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
            "twilio_number",
        ]

    def validate(self, attrs):
        organization_uid = self.context["view"].kwargs.get("restaurant_uid")

        organization = Organization.objects.filter(uid=organization_uid).first()

        if not organization:
            raise ValidationError({"organization": "Invalid organization."})

        whatsappbot = WhatsappBot.objects.filter(organization=organization).first()

        if whatsappbot:
            raise ValidationError(
                {"chatbot_name": "A WhatsappBot already exists for this restaurant."}
            )

        self.organization = organization

        return attrs

    def create(self, validated_data):
        from apps.openAI.gpt_assistants import create_assistant, update_assistant
        from apps.openAI.tools import function_tools
        from apps.openAI.instructions import restaurant_assistant_instruction

        tools = function_tools(validated_data["sales_level"])
        instructions = restaurant_assistant_instruction(self.organization.name)

        update_assistant(
            "asst_FAOpOpfdxUpnz69qonPjzr0v",
            "WhatsApp-based restaurant reservation assistant",
            instructions,
            tools,
        )
        crypto_password = config("CRYPTO_PASSWORD")

        validated_data["hashed_key"] = hash_key(validated_data["twilio_sid"])
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
        validated_data["twilio_number"] = f"whatsapp:{validated_data['twilio_number']}"

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
