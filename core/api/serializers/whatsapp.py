from decouple import config
from openai import OpenAI

from django.db import transaction
from django.conf import settings

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.restaurant.choices import RewardType

from apps.openAI.gpt_assistants import create_assistant, update_assistant
from apps.openAI.tools import function_tools
from apps.openAI.instructions import (
    sales_level_one_assistant_instruction,
    sales_level_two_assistant_instruction,
    sales_level_three_assistant_instruction,
)
from apps.organization.models import Organization, WhatsappBot
from apps.restaurant.models import Reward

from common.crypto import decrypt_data, encrypt_data, hash_key


class RewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reward
        fields = ["uid", "type", "label"]


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
