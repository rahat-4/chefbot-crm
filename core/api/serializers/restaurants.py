import logging
import re
from decouple import config
from openai import OpenAI


from django.conf import settings
from django.db import transaction

from rest_framework import serializers
from rest_framework.exceptions import ValidationError


from common.openAI.generate_nutritions import generate_nutrition_info
from common.crypto import decrypt_data, encrypt_data, hash_key

from apps.organization.choices import OrganizationType
from apps.organization.models import (
    Organization,
    OrganizationUser,
    OpeningHours,
    WhatsappBot,
)
from apps.restaurant.models import (
    Promotion,
    Reward,
    Menu,
    RestaurantTable,
    Reservation,
    RestaurantDocument,
    SalesLevel,
)

from apps.openAI.gpt_assistants import create_assistant, update_assistant
from apps.openAI.tools import function_tools
from apps.openAI.instructions import (
    sales_level_one_assistant_instruction,
    sales_level_two_assistant_instruction,
    sales_level_three_assistant_instruction,
)

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

            # Add default sales level
            SalesLevel.objects.create(
                organization=organization, name="Reservation", level=1
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
    class Meta:
        model = Promotion
        fields = ["uid", "title", "message"]


class RestaurantDashboardSerializer(serializers.Serializer):
    today_reservation = serializers.IntegerField()
    next_reservation = ReservationSlimSerializer(read_only=True)
    sales_level = serializers.IntegerField()
    active_promotions = ReservationPromotionSlimSerializer(many=True, read_only=True)


class RestaurantWhatsAppSerializer(serializers.ModelSerializer):
    organization = serializers.SerializerMethodField()
    organization_uid = serializers.CharField(write_only=True)
    webhook_url = serializers.SerializerMethodField()

    class Meta:
        model = WhatsappBot
        fields = [
            "uid",
            "chatbot_name",
            "chatbot_language",
            "chatbot_tone",
            "chatbot_custom_tone",
            "sales_level",
            "openai_key",
            "assistant_id",
            "twilio_sid",
            "twilio_auth_token",
            "twilio_number",
            "organization",
            "organization_uid",
            "webhook_url",
        ]

        read_only_fields = ["uid", "sales_level", "assistant_id"]

    def to_representation(self, instance):
        """Override to show only encrypted data (not salt) in API response"""
        data = super().to_representation(instance)

        # Fields that contain encrypted data with salt
        encrypted_fields = [
            "openai_key",
            "assistant_id",
            "twilio_sid",
            "twilio_auth_token",
        ]

        for field in encrypted_fields:
            field_value = data.get(field)
            if isinstance(field_value, dict) and "data" in field_value:
                # Show only the encrypted data part in response
                data[field] = field_value["data"]

        return data

    def get_webhook_url(self, obj):
        return settings.WEBHOOK_URL

    def get_organization(self, obj):
        return obj.organization.name

    def validate(self, attrs):
        org_uid = attrs.get("organization_uid")
        try:
            organization = Organization.objects.get(uid=org_uid)
        except Organization.DoesNotExist:
            raise ValidationError({"organization_uid": "Invalid organization UID."})

        if WhatsappBot.objects.filter(organization=organization).exists():
            raise ValidationError(
                {"chatbot_name": "A WhatsappBot already exists for this restaurant."}
            )

        attrs["organization"] = organization
        return attrs

    def create(self, validated_data):
        with transaction.atomic():
            validated_data.pop("organization_uid")

            # Assistant creation
            client = OpenAI(api_key=validated_data["openai_key"])

            tools = function_tools(1)
            instructions = sales_level_one_assistant_instruction(
                validated_data["organization"].name
            )

            assistant = create_assistant(
                client,
                f"{validated_data['organization'].name} whatsapp reservation assistant",
                instructions,
                tools,
            )

            print("==========================", assistant.id)

            # tt = update_assistant(
            #     client=client,
            #     assistant_id="asst_T0a0NjZRF4kkiv4EBxYDBUF7",
            #     assistant_name=f"{validated_data['organization'].name} whatsapp reservation assistant",
            #     instructions=instructions,
            #     tools=tools,
            # )
            # print("==================================", tt)

            crypto_password = config("CRYPTO_PASSWORD")

            validated_data["hashed_key"] = hash_key(validated_data["twilio_sid"])
            validated_data["openai_key"] = encrypt_data(
                validated_data["openai_key"], crypto_password
            )
            validated_data["assistant_id"] = encrypt_data(assistant.id, crypto_password)
            validated_data["twilio_sid"] = encrypt_data(
                validated_data["twilio_sid"], crypto_password
            )
            validated_data["twilio_auth_token"] = encrypt_data(
                validated_data["twilio_auth_token"], crypto_password
            )
            validated_data["twilio_number"] = (
                f"whatsapp:{validated_data['twilio_number']}"
            )
            validated_data["sales_level"] = 1

            return super().create(validated_data)


class RewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reward
        fields = ["uid", "type", "label"]


class RestaurantWhatsAppDetailSerializer(serializers.ModelSerializer):
    organization = serializers.SerializerMethodField()
    webhook_url = serializers.SerializerMethodField()

    class Meta:
        model = WhatsappBot
        fields = [
            "uid",
            "chatbot_name",
            "chatbot_language",
            "chatbot_tone",
            "chatbot_custom_tone",
            "sales_level",
            "openai_key",
            "assistant_id",
            "twilio_sid",
            "twilio_auth_token",
            "twilio_number",
            "organization",
            "webhook_url",
        ]
        read_only_fields = [
            "uid",
            "openai_key",
            "assistant_id",
            "twilio_sid",
            "twilio_auth_token",
            "twilio_number",
            "organization",
            "webhook_url",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get the instance to check sales_level
        instance = kwargs.get("instance")

        # For updates (PUT/PATCH), add reward field for writing
        if self.context.get("request") and self.context["request"].method in [
            "PUT",
            "PATCH",
        ]:
            request_data = self.context["request"].data
            sales_level = request_data.get("sales_level")

            # If sales_level is 2 or instance already has sales_level 2, include reward field
            if sales_level == 2 or (instance and instance.sales_level == 2):
                self.fields["reward"] = RewardSerializer(write_only=True)

        # For GET requests, add reward field for reading
        if self.context.get("request") and self.context["request"].method in ["GET"]:
            # For GET requests, check instance sales_level (not request data)
            if instance and instance.sales_level == 2:
                self.fields["reward"] = RewardSerializer(read_only=True)

    def get_webhook_url(self, obj):
        return settings.WEBHOOK_URL

    def validate(self, attrs):
        errors = {}

        # Check if sales_level is 2 but reward is missing or empty
        if attrs.get("sales_level") == 2 and not attrs.get("reward"):
            errors["reward"] = ["This field is required when sales_level is 2."]

        # If there are errors, raise ValidationError
        if errors:
            raise ValidationError(errors)

        return attrs

    def get_organization(self, obj):
        return obj.organization.name

    def to_representation(self, instance):
        """Override to show only encrypted data (not salt) in API response"""
        data = super().to_representation(instance)

        # Fields that contain encrypted data with salt
        encrypted_fields = [
            "openai_key",
            "assistant_id",
            "twilio_sid",
            "twilio_auth_token",
        ]

        for field in encrypted_fields:
            field_value = data.get(field)
            if isinstance(field_value, dict) and "data" in field_value:
                # Show only the encrypted data part in response
                data[field] = field_value["data"]

        # Add reward data for GET requests when sales_level is 2
        if instance.sales_level == 2:
            try:
                reward = Reward.objects.get(organization=instance.organization)
                data["reward"] = RewardSerializer(reward).data
            except Reward.DoesNotExist:
                data["reward"] = None

        return data

    def update(self, instance, validated_data):
        """Custom update method to handle reward when sales_level changes"""
        reward_data = validated_data.pop("reward", None)

        # Update the instance
        instance = super().update(instance, validated_data)

        # Assistant update
        openai_key = decrypt_data(
            instance.openai_key,
            settings.CRYPTO_PASSWORD,
        )
        assistant_id = decrypt_data(
            instance.assistant_id,
            settings.CRYPTO_PASSWORD,
        )
        client = OpenAI(api_key=openai_key)

        if instance.sales_level == 1:
            tools = function_tools(1)
            instructions = sales_level_one_assistant_instruction(
                instance.organization.name
            )

            tt = update_assistant(
                client=client,
                assistant_id=assistant_id,
                assistant_name=f"{instance.organization.name} whatsapp reservation assistant",
                instructions=instructions,
                tools=tools,
            )

        # Handle reward based on sales_level
        elif instance.sales_level == 2 and reward_data is not None:
            # Delete existing reward and create new one
            Reward.objects.filter(organization=instance.organization).delete()
            existing_reward = Reward.objects.create(
                organization=instance.organization, **reward_data
            )

            tools = function_tools(1)
            instructions = sales_level_two_assistant_instruction(
                instance.organization.name, existing_reward.type, existing_reward.label
            )

            tt = update_assistant(
                client=client,
                assistant_id=assistant_id,
                assistant_name=f"{instance.organization.name} whatsapp reservation assistant",
                instructions=instructions,
                tools=tools,
            )
        elif instance.sales_level == 3:
            # Ensure a reward exists for level 3 as well
            reward = Reward.objects.filter(organization=instance.organization).first()
            if not reward:
                reward = Reward.objects.create(organization=instance.organization)

            tools = function_tools(1)
            instructions = sales_level_three_assistant_instruction(
                instance.organization.name, reward.type, reward.label
            )

            tt = update_assistant(
                client=client,
                assistant_id=assistant_id,
                assistant_name=f"{instance.organization.name} whatsapp reservation assistant",
                instructions=instructions,
                tools=tools,
            )

        return instance
