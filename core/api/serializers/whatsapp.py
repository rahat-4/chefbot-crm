from decouple import config
from openai import OpenAI

from django.db import transaction

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.openAI.gpt_assistants import create_assistant
from apps.openAI.tools import function_tools
from apps.openAI.instructions import restaurant_assistant_instruction
from apps.organization.models import Organization, WhatsappBot

from common.crypto import encrypt_data, hash_key


class RestaurantWhatsAppSerializer(serializers.ModelSerializer):
    organization = serializers.SerializerMethodField()
    organization_uid = serializers.CharField(write_only=True)

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
            "organization",
            "organization_uid",
        ]

        read_only_fields = ["uid", "sales_level", "assistant_id"]

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
            instructions = restaurant_assistant_instruction(
                validated_data["organization"].name
            )

            assistant = create_assistant(
                client,
                "WhatsApp-based restaurant reservation assistant",
                instructions,
                tools,
            )

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
