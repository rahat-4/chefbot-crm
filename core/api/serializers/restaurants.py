import logging
import re
from collections import defaultdict

from django.conf import settings
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
from apps.restaurant.models import (
    Client,
    Menu,
    Reward,
    Promotion,
    PromotionTrigger,
    RestaurantTable,
    Reservation,
    RestaurantDocument,
)

from openai import OpenAI


logger = logging.getLogger(__name__)


class OpeningHoursSerializer(serializers.ModelSerializer):

    class Meta:
        model = OpeningHours
        exclude = ["organization", "created_at", "updated_at"]


class RestaurantSerializer(serializers.ModelSerializer):
    opening_hours = OpeningHoursSerializer(many=True, required=False)

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
        queryset=Menu.objects.all(),
        many=True,
        slug_field="uid",
        required=False,
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
        read_only_fields = ["allergens", "macronutrients"]  # AI-generated fields

    def _get_restaurant_from_context(self):
        """Get restaurant from context or view kwargs"""
        view = self.context.get("view")
        if not view:
            return None
        restaurant_uid = view.kwargs.get("restaurant_uid")
        if restaurant_uid:
            return Organization.objects.filter(uid=restaurant_uid).first()
        return None

    def validate_recommended_combinations(self, value):
        if value and len(value) > 5:
            raise serializers.ValidationError(
                "You can select a maximum of 5 recommended combinations."
            )
        return value

    def validate_ingredients(self, value):
        """Validate ingredients format and quantities"""
        if not value:
            return value

        # Pattern to match quantity with unit
        quantity_pattern = r"^[0-9]*\.?[0-9]+[a-zA-Z]+$"

        for ingredient, quantity in value.items():
            if not ingredient.strip():
                raise serializers.ValidationError("Ingredient name cannot be empty.")
            if not quantity.strip():
                raise serializers.ValidationError(
                    "Ingredient quantity cannot be empty."
                )
            if not re.match(quantity_pattern, quantity.strip()):
                raise serializers.ValidationError(
                    f"Invalid quantity format for '{ingredient}'. "
                    "Use format like '500g', '2cups', '1.5kg', '250ml'"
                )
        return value

    def validate(self, attrs):
        """Validate menu data"""
        errors = {}
        restaurant = self._get_restaurant_from_context()
        name = attrs.get("name")

        if not restaurant:
            errors["restaurant"] = ["Invalid restaurant."]
        else:
            # Check for duplicate menu names in the same restaurant
            queryset = Menu.objects.filter(organization=restaurant, name=name)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)

            if queryset.exists():
                errors["name"] = [
                    "A menu with this name already exists in this restaurant."
                ]

        # Validate upselling constraints
        upselling_priority = attrs.get("upselling_priority", 1)

        if not 1 <= upselling_priority <= 5:
            errors["upselling_priority"] = ["Must be between 1 and 5."]

        if upselling_priority > 1:
            # Count how many other menus in this org have same priority and upselling enabled
            conflict_qs = Menu.objects.filter(
                organization=restaurant,
                enable_upselling=True,
                upselling_priority=upselling_priority,
            )
            if self.instance:
                conflict_qs = conflict_qs.exclude(pk=self.instance.pk)

            if conflict_qs.count() >= 5:
                errors["upselling_priority"] = [
                    f"Only 5 menus can have upselling priority level {upselling_priority}."
                ]

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def to_representation(self, instance):
        """Customize output representation"""
        representation = super().to_representation(instance)

        # Show recommended combinations as names instead of UIDs
        representation["recommended_combinations"] = [
            {"uid": menu.uid, "name": menu.name}
            for menu in instance.recommended_combinations.all()
        ]

        return representation

    def _auto_generate_nutrition_info(self, validated_data):
        """Generate nutrition info based on ingredients with quantities"""
        ingredients = validated_data.get("ingredients", {})

        if ingredients:
            # Convert ingredients dict to formatted list for AI
            formatted_ingredients = []
            for ingredient, quantity in ingredients.items():
                formatted_ingredients.append(f"{ingredient} ({quantity})")

            print(f"Generating nutrition info for: {formatted_ingredients}")  # Debug

            openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

            # Call the AI function with formatted ingredients
            response = generate_nutrition_info(formatted_ingredients, openai_client)

            if "error" not in response:
                validated_data["allergens"] = response.get("allergens", [])
                validated_data["macronutrients"] = response.get("macronutrients", {})
            else:
                print(f"Nutrition generation error: {response['error']}")
                # Keep existing values or set empty defaults
                validated_data["allergens"] = validated_data.get("allergens", [])
                validated_data["macronutrients"] = validated_data.get(
                    "macronutrients", {}
                )

        return validated_data

    def create(self, validated_data):
        """Create menu with auto-generated nutrition info"""
        restaurant = self._get_restaurant_from_context()
        if restaurant:
            validated_data["organization"] = restaurant

        validated_data = self._auto_generate_nutrition_info(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Update menu with auto-generated nutrition info"""
        # Only regenerate nutrition if ingredients changed
        if "ingredients" in validated_data:
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
        ]


class PromotionTriggerSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromotionTrigger
        fields = ["uid", "type", "days_before", "description"]


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


class RestaurantClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = [
            "uid",
            "name",
            "email",
            "phone_number",
            "number_of_people",
            "date",
            "time",
            "notes",
        ]


class RestaurantReservationSerializer(serializers.ModelSerializer):
    client = serializers.SlugRelatedField(
        slug_field="uid", queryset=Client.objects.all()
    )
    menus = serializers.SlugRelatedField(
        slug_field="uid", queryset=Menu.objects.all(), many=True
    )
    table = serializers.SlugRelatedField(
        slug_field="uid", queryset=RestaurantTable.objects.all()
    )

    class Meta:
        model = Reservation
        fields = [
            "uid",
            "client",
            "reservation_name",
            "reservation_phone",
            "reservation_date",
            "reservation_time",
            "reservation_end_time",
            "reservation_reason",
            "guests",
            "notes",
            "reservation_status",
            "cancelled_by",
            "booking_reminder_sent",
            "booking_reminder_sent_at",
            "menus",
            "table",
        ]

    def create(self, validated_data):
        menus = validated_data.pop("menus", [])
        reservation = super().create(validated_data)
        reservation.menus.set(menus)
        return reservation


class RestaurantDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantDocument
        fields = [
            "uid",
            "file",
        ]
