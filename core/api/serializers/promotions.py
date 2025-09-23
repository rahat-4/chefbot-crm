from django.db import transaction

from rest_framework import serializers

from apps.restaurant.models import Promotion, PromotionTrigger, Reward
from apps.restaurant.choices import TriggerType, YearlyCategory
from apps.organization.models import Organization, MessageTemplate


class RewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reward
        fields = ["uid", "type", "label", "promo_code"]


class PromotionTriggerSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromotionTrigger
        fields = [
            "uid",
            "type",
            "yearly_category",
            "days_before",
            "inactivity_days",
            "min_count",
        ]


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

            organization = validated_data.get("organization")

            reward = Reward.objects.create(organization=organization, **reward_data)

            promotion_trigger = PromotionTrigger.objects.create(**trigger_data)

            promotion = Promotion.objects.create(
                reward=reward, trigger=promotion_trigger, **validated_data
            )

            return promotion

    def update(self, instance, validated_data):
        with transaction.atomic():
            reward_data = validated_data.pop("reward", None)
            trigger_data = validated_data.pop("trigger", None)

            if reward_data:
                for attr, value in reward_data.items():
                    setattr(instance.reward, attr, value)
                instance.reward.save()

            if trigger_data:
                for attr, value in trigger_data.items():
                    setattr(instance.trigger, attr, value)
                instance.trigger.save()

            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()

            return instance
