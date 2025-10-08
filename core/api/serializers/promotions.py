from django.db import transaction

from rest_framework import serializers

from apps.restaurant.models import (
    Menu,
    Promotion,
    PromotionTrigger,
    PromotionSentLog,
    Reward,
)
from apps.restaurant.choices import TriggerType, YearlyCategory
from apps.organization.models import Organization, MessageTemplate


class MenuSerializer(serializers.ModelSerializer):
    class Meta:
        model = Menu
        fields = [
            "uid",
            "name",
            "description",
            "price",
            "ingredients",
            "category",
            "classification",
        ]


class RewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reward
        fields = ["uid", "type", "label", "promo_code"]


class PromotionTriggerSerializer(serializers.ModelSerializer):
    menus = serializers.SlugRelatedField(
        queryset=Menu.objects.all(),
        slug_field="uid",
        many=True,
        required=False,
    )

    class Meta:
        model = PromotionTrigger
        fields = [
            "uid",
            "type",
            "yearly_category",
            "menus",
            "days_before",
            "inactivity_days",
            "min_count",
        ]

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["menus"] = MenuSerializer(instance.menus.all(), many=True).data
        return rep


class PromotionSerializer(serializers.ModelSerializer):
    reward = RewardSerializer()
    trigger = PromotionTriggerSerializer()
    organization = serializers.SlugRelatedField(
        queryset=Organization.objects.all(), slug_field="uid"
    )
    message_template = serializers.SlugRelatedField(
        queryset=MessageTemplate.objects.all(), slug_field="uid"
    )

    class Meta:
        model = Promotion
        fields = [
            "uid",
            "title",
            "message_template",
            "reward",
            "organization",
            "valid_from",
            "valid_to",
            "trigger",
            "is_enabled",
        ]

    def validate(self, data):
        errors = {}

        organization = data.get("organization")

        if organization and not hasattr(organization, "whatsapp_bots"):
            errors["promotion"] = "Cannot create promotion: WhatsApp bot is missing."

        # Promotion trigger validation
        trigger = data.get("trigger")

        if trigger:
            if trigger.get("type") == TriggerType.YEARLY:
                if not trigger.get("yearly_category"):
                    errors["trigger"] = {
                        "yearly_category": "yearly_category is required when type is Yearly."
                    }
                if trigger.get(
                    "yearly_category"
                ) == YearlyCategory.BIRTHDAY and not trigger.get("days_before"):
                    errors["trigger"] = {
                        "days_before": "days before is required when type is Birthday."
                    }
                if trigger.get(
                    "yearly_category"
                ) == YearlyCategory.ANNIVERSARY and not trigger.get("days_before"):
                    errors["trigger"] = {
                        "days_before": "days before is required when type is Anniversary."
                    }
            elif trigger.get("type") == TriggerType.MENU_SELECTED:
                if not trigger.get("menus") or len(trigger.get("menus")) == 0:
                    errors["trigger"] = {
                        "menus": "At least one menu must be selected when type is Menu Selected."
                    }

            elif trigger.get("type") == TriggerType.INACTIVITY and not trigger.get(
                "inactivity_days"
            ):
                errors["trigger"] = {
                    "inactivity_days": "Inactivity days is required when type is Inactivity."
                }
            elif trigger.get("type") == "RESERVATION_COUNT" and not trigger.get(
                "min_count"
            ):
                errors["trigger"] = {
                    "min_count": "Minimum count is required when type is Reservation Count."
                }

        # Validation 1: Start date must be ≤ end date
        valid_from = data.get("valid_from")
        valid_to = data.get("valid_to")

        if valid_from and valid_to and valid_from > valid_to:
            errors["valid_from"] = "Start date must be less than or equal to end date"

        # Validation 2: Maximum of 10 active promotions allowed
        organization = data.get("organization")
        is_enabled = data.get("is_enabled", True)

        if is_enabled and organization:
            active_count = Promotion.objects.filter(
                organization=organization, is_enabled=True
            ).count()

            # If updating existing promotion, don't count it
            if self.instance and self.instance.is_enabled:
                active_count -= 1

            if active_count >= 10:
                errors["organization"] = (
                    "Maximum of 10 active promotions allowed simultaneously"
                )

        if errors:
            raise serializers.ValidationError(errors)

        return data

    def to_representation(self, instance):
        rep = super().to_representation(instance)

        rep["organization"] = {
            "uid": instance.organization.uid,
            "name": instance.organization.name,
        }

        return rep

    def create(self, validated_data):
        with transaction.atomic():
            reward_data = validated_data.pop("reward")
            trigger_data = validated_data.pop("trigger")
            menus_data = trigger_data.pop("menus", [])

            print("---------trigger_data--------", trigger_data)
            print("---------menus_data--------", menus_data)

            organization = validated_data.get("organization")

            reward = Reward.objects.create(organization=organization, **reward_data)

            promotion_trigger = PromotionTrigger.objects.create(**trigger_data)

            if menus_data != []:
                promotion_trigger.menus.set(menus_data)

            promotion = Promotion.objects.create(
                reward=reward, trigger=promotion_trigger, **validated_data
            )

            return promotion

    def update(self, instance, validated_data):
        with transaction.atomic():
            reward_data = validated_data.pop("reward", None)
            trigger_data = validated_data.pop("trigger", None)
            menus_data = trigger_data.pop("menus", None)

            if reward_data:
                for attr, value in reward_data.items():
                    setattr(instance.reward, attr, value)
                instance.reward.save()

            if trigger_data:
                for attr, value in trigger_data.items():
                    setattr(instance.trigger, attr, value)
                instance.trigger.save()

            if menus_data is not None:
                instance.trigger.menus.set(menus_data)

            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            return instance


class PromotionSentLogSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    client_whatsapp = serializers.CharField(
        source="client.whatsapp_number", read_only=True
    )

    class Meta:
        model = PromotionSentLog
        fields = [
            "uid",
            "client_name",
            "client_whatsapp",
            "status",
            "sent_at",
        ]
