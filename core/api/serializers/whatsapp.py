from decouple import config
from openai import OpenAI

from django.db import transaction
from django.conf import settings

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.restaurant.choices import RewardCategory, RewardType

from apps.openAI.gpt_assistants import create_assistant, update_assistant
from apps.openAI.tools import function_tools
from apps.openAI.instructions import build_assistant_instruction
from apps.organization.models import Organization
from apps.restaurant.models import Client, Reward, SalesLevel, WhatsappBot

from common.crypto import decrypt_data, encrypt_data, hash_key


class RewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reward
        fields = ["uid", "type", "label", "reward_category"]


class SalesLevelSerializer(serializers.ModelSerializer):
    reward = RewardSerializer()

    class Meta:
        model = SalesLevel
        fields = [
            "name",
            "level",
            "reward_enabled",
            "priority_dish_enabled",
            "personalization_enabled",
            "reward",
        ]


class RestaurantWhatsAppSerializer(serializers.ModelSerializer):
    organization = serializers.SerializerMethodField()
    organization_uid = serializers.CharField(write_only=True)
    webhook_url = serializers.SerializerMethodField()
    sales_level = SalesLevelSerializer(read_only=True)

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
        data = super().to_representation(instance)
        encrypted_fields = [
            "openai_key",
            "assistant_id",
            "twilio_sid",
            "twilio_auth_token",
        ]
        for field in encrypted_fields:
            value = data.get(field)
            if isinstance(value, dict) and "data" in value:
                data[field] = value["data"]
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
            raise ValidationError({"organization_uid": "Invalid restaurant UID."})

        if WhatsappBot.objects.filter(organization=organization).exists():
            raise ValidationError(
                {"chatbot_name": "A WhatsappBot already exists for this restaurant."}
            )

        attrs["organization"] = organization
        return attrs

    def create(self, validated_data):
        validated_data.pop("organization_uid", None)

        with transaction.atomic():
            # Create Sales Level 1
            organization = validated_data["organization"]
            sales_level, _ = SalesLevel.objects.get_or_create(
                organization=organization,
                level=1,
                defaults={"name": "Reservations Only"},
            )

            # Create Assistant
            client = OpenAI(api_key=validated_data["openai_key"])
            assistant = create_assistant(
                client,
                f"{organization.name} whatsapp reservation assistant with sales level 1",
                build_assistant_instruction(organization.name),
                function_tools(),
            )

            # Encrypt sensitive fields
            crypto_password = config("CRYPTO_PASSWORD")
            validated_data.update(
                {
                    "hashed_key": hash_key(validated_data["twilio_sid"]),
                    "openai_key": encrypt_data(
                        validated_data["openai_key"], crypto_password
                    ),
                    "assistant_id": encrypt_data(assistant.id, crypto_password),
                    "twilio_sid": encrypt_data(
                        validated_data["twilio_sid"], crypto_password
                    ),
                    "twilio_auth_token": encrypt_data(
                        validated_data["twilio_auth_token"], crypto_password
                    ),
                    "twilio_number": f"whatsapp:{validated_data['twilio_number']}",
                    "sales_level": sales_level,
                }
            )

            return super().create(validated_data)


class RestaurantWhatsAppDetailSerializer(serializers.ModelSerializer):
    organization = serializers.SerializerMethodField()
    webhook_url = serializers.SerializerMethodField()
    sales_level = SalesLevelSerializer()
    reward = RewardSerializer(source="sales_level.reward", read_only=True)

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
            "reward",
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
            "reward",
        ]

    def get_webhook_url(self, obj):
        return settings.WEBHOOK_URL

    def get_organization(self, obj):
        return obj.organization.name

    def validate(self, attrs):
        sales_level = attrs.get("sales_level")
        if sales_level and isinstance(sales_level, dict):
            level = sales_level.get("level")
            reward = sales_level.get("reward")

            if level == 2 and not reward:
                raise ValidationError(
                    {"sales_level": ["Reward is required for sales level 2."]}
                )

        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        encrypted_fields = [
            "openai_key",
            "assistant_id",
            "twilio_sid",
            "twilio_auth_token",
        ]

        for field in encrypted_fields:
            value = data.get(field)
            if isinstance(value, dict) and "data" in value:
                data[field] = value["data"]

        return data

    def update(self, instance, validated_data):
        sales_level_data = validated_data.pop("sales_level", None)
        sales_level = instance.sales_level
        organization = instance.organization
        reward = None

        # Decrypt sensitive data
        openai_key = decrypt_data(instance.openai_key, settings.CRYPTO_PASSWORD)
        assistant_id = decrypt_data(instance.assistant_id, settings.CRYPTO_PASSWORD)
        client = OpenAI(api_key=openai_key)

        if sales_level_data:
            level = sales_level_data.get("level", sales_level.level)
            reward_enabled = sales_level_data.get("reward_enabled", False)
            priority_dish_enabled = sales_level_data.get("priority_dish_enabled", False)
            personalization_enabled = sales_level_data.get(
                "personalization_enabled", False
            )
            reward_data = sales_level_data.get("reward")

            # Handle reward (create new if needed)
            if level in [2, 3, 4] and (reward_enabled or reward_data):
                reward = self._replace_reward(organization, reward_data)
                sales_level.reward = reward
            elif level == 2 and not reward_data:
                raise ValidationError(
                    {"sales_level": ["Reward is required for sales level 2."]}
                )

            sales_level, _ = SalesLevel.objects.get_or_create(
                organization=organization,
                level=level,
                defaults={"name": self._get_sales_level_name(level)},
            )
            # Set name and other properties
            sales_level.level = level
            sales_level.name = self._get_sales_level_name(level)
            sales_level.reward_enabled = reward_enabled
            sales_level.priority_dish_enabled = priority_dish_enabled
            sales_level.personalization_enabled = personalization_enabled
            sales_level.save()

            validated_data["sales_level"] = sales_level

            # Update Assistant
            self._update_assistant(
                client,
                assistant_id,
                organization.name,
                level,
                reward,
                reward_enabled,
                priority_dish_enabled,
                personalization_enabled,
            )

        return super().update(instance, validated_data)

    def _replace_reward(self, organization, reward_data):
        """Delete old reward and create new one"""
        Reward.objects.filter(
            organization=organization,
            reward_category=RewardCategory.SALES_LEVEL,
        ).delete()

        return Reward.objects.create(
            organization=organization,
            reward_category=RewardCategory.SALES_LEVEL,
            **reward_data,
        )

    def _update_assistant(
        self,
        client,
        assistant_id,
        org_name,
        level,
        reward=None,
        reward_enabled=False,
        priority_dish_enabled=False,
        personalization_enabled=False,
    ):
        tools = function_tools()

        if level == 1:
            instructions = build_assistant_instruction(restaurant_name=org_name)
        elif level == 2 and reward:
            instructions = build_assistant_instruction(
                restaurant_name=org_name,
                sales_level=2,
                reward_type=reward.type,
                reward_label=reward.label,
            )
        elif level == 3:
            instructions = (
                build_assistant_instruction(
                    restaurant_name=org_name,
                    sales_level=3,
                    reward_type=reward.type,
                    reward_label=reward.label,
                )
                if reward and reward_enabled
                else build_assistant_instruction(
                    restaurant_name=org_name, sales_level=3
                )
            )
        elif level == 4:
            if reward and reward_enabled and priority_dish_enabled:
                instructions = build_assistant_instruction(
                    restaurant_name=org_name,
                    sales_level=4,
                    reward_type=reward.type,
                    reward_label=reward.label,
                    priority_dish_enabled=True,
                )
            elif reward and reward_enabled:
                instructions = build_assistant_instruction(
                    restaurant_name=org_name,
                    sales_level=4,
                    reward_type=reward.type,
                    reward_label=reward.label,
                )
            elif priority_dish_enabled:
                instructions = build_assistant_instruction(
                    restaurant_name=org_name, sales_level=4, priority_dish_enabled=True
                )
            else:
                instructions = build_assistant_instruction(
                    restaurant_name=org_name, sales_level=4
                )
        elif level == 5:
            if priority_dish_enabled and personalization_enabled:
                instructions = build_assistant_instruction(
                    restaurant_name=org_name,
                    sales_level=5,
                    priority_dish_enabled=True,
                    personalization_enabled=True,
                )
            elif priority_dish_enabled:
                instructions = build_assistant_instruction(
                    restaurant_name=org_name,
                    sales_level=5,
                    priority_dish_enabled=True,
                )
            elif personalization_enabled:
                instructions = build_assistant_instruction(
                    restaurant_name=org_name,
                    sales_level=5,
                    personalization_enabled=True,
                )
            else:
                instructions = build_assistant_instruction(
                    restaurant_name=org_name, sales_level=5
                )
        else:
            return  # No update for unknown level

        update_assistant(
            client=client,
            assistant_id=assistant_id,
            assistant_name=f"{org_name} WhatsApp assistant - Level {level}",
            instructions=instructions,
            tools=tools,
        )

    def _get_sales_level_name(self, level):
        """Returns friendly name for sales level"""
        return {
            1: "Reservations Only",
            2: "Menu Rewards",
            3: "Dish Prioritization",
            4: "Personalized Recommendations",
            5: "Promotions Module",
        }.get(level, f"Sales Level {level}")


class WhatsappClientListSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    last_message_sent_at = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = [
            "uid",
            "name",
            "whatsapp_number",
            "last_message",
            "last_message_sent_at",
        ]
        read_only_fields = ["uid"]

    def get_last_message(self, obj):
        last_msg = obj.client_messages.order_by("-sent_at").first()
        return last_msg.message if last_msg else None

    def get_last_message_sent_at(self, obj):
        last_msg = obj.client_messages.order_by("-sent_at").first()
        return last_msg.sent_at if last_msg else None
