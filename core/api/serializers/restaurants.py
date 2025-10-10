import logging
import re
from openai import OpenAI
from datetime import datetime, timedelta, time

from django.conf import settings
from django.db import transaction

from rest_framework import serializers


from common.openAI.generate_nutritions import generate_nutrition_info

from apps.organization.choices import OrganizationType
from apps.organization.models import (
    Organization,
    OrganizationUser,
    OpeningHours,
    MessageTemplate,
)
from apps.restaurant.models import (
    Promotion,
    Menu,
    RestaurantTable,
    Reservation,
    RestaurantDocument,
    WhatsappBot,
)


logger = logging.getLogger(__name__)


class WhatsappBotSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhatsappBot
        exclude = ["organization"]


class OpeningHoursSerializer(serializers.ModelSerializer):

    class Meta:
        model = OpeningHours
        exclude = ["organization", "created_at", "updated_at"]


class RestaurantSerializer(serializers.ModelSerializer):
    opening_hours = OpeningHoursSerializer(many=True, required=False)
    whatsappbot = WhatsappBotSerializer(source="whatsapp_bots", read_only=True)

    class Meta:
        model = Organization
        fields = [
            "uid",
            "logo",
            "name",
            "whatsapp_number",
            "whatsapp_enabled",
            "whatsappbot",
            "email",
            "description",
            "website",
            "country",
            "city",
            "street",
            "zip_code",
            "reservation_booking_reminder",
            "opening_hours",
        ]

    def validate(self, attrs):
        opening_hours = attrs.get("opening_hours", [])
        errors = {}

        # Validate WhatsApp logic
        if attrs.get("whatsapp_enabled") and not attrs.get("whatsapp_number"):
            errors["whatsapp_number"] = [
                "This field is required when WhatsApp is enabled."
            ]

        # Validate each day's opening hours
        opening_hours_errors = {}

        for index, day in enumerate(opening_hours):
            day_errors = {}

            is_closed = day.get("is_closed", False)

            # Default times to 00:00:00 if not provided
            opening_start = day.get("opening_start_time") or time(0, 0)
            opening_end = day.get("opening_end_time") or time(0, 0)
            break_start = day.get("break_start_time") or time(0, 0)
            break_end = day.get("break_end_time") or time(0, 0)

            if (
                any(
                    t == time(0, 0)
                    for t in [opening_start, opening_end, break_start, break_end]
                )
                and not is_closed
            ):
                opening_hours_errors[f"{day['day'].capitalize()}"] = [
                    "All fields must be provided unless the day is marked as closed."
                ]
            elif not is_closed:
                # Validate opening times
                if opening_start >= opening_end:
                    opening_hours_errors[f"{day['day'].capitalize()}"] = [
                        "Opening start time must be before end time."
                    ]

                # Validate break times if not all zero
                if (break_start != time(0, 0)) or (break_end != time(0, 0)):
                    if not (opening_start <= break_start < break_end <= opening_end):
                        opening_hours_errors[f"{day['day'].capitalize()}"] = [
                            "Break time must be within the opening hours range."
                        ]
                    else:
                        break_duration = datetime.combine(
                            datetime.today(), break_end
                        ) - datetime.combine(datetime.today(), break_start)

                        if break_duration > timedelta(hours=2):
                            opening_hours_errors[f"{day['day'].capitalize()}"] = [
                                "Break time cannot exceed 2 hours."
                            ]

            if day_errors:
                opening_hours_errors[f"{day['day'].capitalize()}"] = day_errors

        if opening_hours_errors:
            errors["opening_hours"] = opening_hours_errors

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

    def validate_name(self, value):
        """Validate table name uniqueness within the same restaurant"""
        restaurant = self.context.get("view").kwargs.get("restaurant_uid")
        if not restaurant:
            return value

        queryset = RestaurantTable.objects.filter(
            organization__uid=restaurant, name=value
        )
        if self.instance:
            queryset = queryset.exclude(uid=self.instance.uid)

        if queryset.exists():
            raise serializers.ValidationError(
                "A table with this name already exists in this restaurant."
            )
        return value


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

    def validate_price(self, value):
        """Validate price is between 0 and 1000"""
        if value is not None and not (0 < value < 1000):
            raise serializers.ValidationError("Price must be between 0 and 1000.")
        return value

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


class RestaurantDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantDocument
        fields = [
            "uid",
            "file",
        ]


class ReservationSlimSerializer(serializers.ModelSerializer):
    menu_selected = serializers.SerializerMethodField()

    class Meta:
        model = Reservation
        fields = [
            "uid",
            "reservation_date",
            "reservation_time",
            "guests",
            "menu_selected",
        ]

    def get_menu_selected(self, obj):
        return obj.menus.exists()


class ReservationPromotionSlimSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="message_template.type", read_only=True)

    class Meta:
        model = Promotion
        fields = ["uid", "title", "type"]


class RestaurantDashboardSerializer(serializers.Serializer):
    today_reservation = serializers.IntegerField()
    next_reservation = ReservationSlimSerializer(read_only=True)
    sales_level = serializers.IntegerField()
    active_promotions = ReservationPromotionSlimSerializer(many=True, read_only=True)


class MessageTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageTemplate
        fields = [
            "uid",
            "name",
            "content_sid",
            "content_variables",
            "content",
        ]


class RestaurantPromotionsSerializer(serializers.ModelSerializer):
    reward_type = serializers.CharField(source="reward.type", read_only=True)
    reward_label = serializers.CharField(source="reward.label", read_only=True)

    class Meta:
        model = Promotion
        fields = ["uid", "reward_type", "reward_label"]
