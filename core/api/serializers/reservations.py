import logging
from django.db import transaction
from django.utils import timezone

from rest_framework import serializers

from apps.organization.models import Organization
from apps.restaurant.models import (
    Client,
    Menu,
    Reservation,
    RestaurantTable,
    ClientMessage,
    Reward,
    Promotion,
)
from apps.restaurant.choices import (
    ReservationCancelledBy,
    ReservationStatus,
    ClientMessageRole,
)

from common.whatsapp import send_cancellation_notification

logger = logging.getLogger(__name__)


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = [
            "uid",
            "name",
            "phone",
            "whatsapp_number",
            "email",
            "source",
            "date_of_birth",
            "last_visit",
            "preferences",
            "allergens",
            "special_notes",
        ]


class RewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reward
        fields = [
            "uid",
            "type",
            "label",
            "promo_code",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["uid", "promo_code", "created_at", "updated_at"]


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


class TableSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantTable
        fields = ["uid", "name", "capacity", "category", "position", "status"]


class ReservationSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(write_only=True)
    client_phone = serializers.CharField(write_only=True)
    client_allergens = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
        write_only=True,
    )
    menus = serializers.SlugRelatedField(
        queryset=Menu.objects.all(),
        slug_field="uid",
        many=True,
        required=False,
    )
    table = serializers.SlugRelatedField(
        queryset=RestaurantTable.objects.all(), slug_field="uid"
    )
    organization = serializers.SlugRelatedField(
        queryset=Organization.objects.all(), slug_field="uid"
    )
    client = ClientSerializer(read_only=True)
    promo_code = serializers.SlugRelatedField(
        queryset=Promotion.objects.all(),
        slug_field="uid",
        required=False,
    )

    class Meta:
        model = Reservation
        fields = [
            "uid",
            "client_name",
            "client_phone",
            "client_allergens",
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
            "cancellation_reason",
            "booking_reminder_sent",
            "booking_reminder_sent_at",
            "menus",
            "table",
            "promo_code",
            "organization",
        ]

        read_only_fields = ["uid", "cancelled_by", "reservation_end_time"]

    def validate(self, attrs):
        reservation_status = attrs.get("reservation_status")
        cancellation_reason = attrs.get("cancellation_reason")

        if reservation_status == ReservationStatus.CANCELLED:
            if not cancellation_reason:
                raise serializers.ValidationError(
                    {
                        "cancellation_reason": "This field is required when cancelling a reservation."
                    }
                )
            # Automatically set cancelled_by to SYSTEM
            attrs["cancelled_by"] = ReservationCancelledBy.SYSTEM

        return attrs

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep["menus"] = MenuSerializer(instance.menus.all(), many=True).data
        rep["table"] = TableSerializer(instance.table).data
        rep["organization"] = {
            "uid": instance.organization.uid,
            "name": instance.organization.name,
        }
        rep["promo_code"] = (
            RewardSerializer(instance.promo_code).data if instance.promo_code else None
        )
        return rep

    def create(self, validated_data):
        with transaction.atomic():
            client_name = validated_data.pop("client_name")
            client_phone = validated_data.pop("client_phone")
            client_allergens = validated_data.pop("client_allergens", [])

            client, created = Client.objects.get_or_create(
                whatsapp_number=client_phone,
                organization=validated_data["organization"],
                defaults={
                    "name": client_name,
                    "phone": client_phone,
                    "allergens": client_allergens,
                },
            )

            if not created:
                updated = False
                if client.name != client_name:
                    client.name = client_name
                    updated = True
                if client.allergens != client_allergens:
                    client.allergens = client_allergens
                    updated = True
                if updated:
                    client.save()

            validated_data["client"] = client

            # Reward
            promotion = validated_data.pop("promo_code", None)
            if promotion:
                validated_data["promo_code"] = promotion.reward

            # Reservation data
            menus_data = validated_data.pop("menus", [])
            reservation_status = validated_data.get("reservation_status")
            reservation = Reservation.objects.create(**validated_data)

            # ✅ Auto-set reservation_end_time and client.last_visit if completed
            if reservation_status == ReservationStatus.COMPLETED:
                now = timezone.now()
                reservation.reservation_end_time = now
                reservation.save()
                reservation.client.last_visit = now
                reservation.client.save()
            if menus_data:
                reservation.menus.set(menus_data)
            return reservation

    def update(self, instance, validated_data):
        with transaction.atomic():
            menus_data = validated_data.pop("menus", None)
            promotion = validated_data.pop("promo_code", None)
            client_name = validated_data.pop("client_name", None)
            client_phone = validated_data.pop("client_phone", None)
            client_allergens = validated_data.pop("client_allergens", None)

            if any([client_name, client_phone, client_allergens is not None]):
                client = instance.client
                updated = False

                if client_name and client.name != client_name:
                    client.name = client_name
                    updated = True

                if client_phone and client.whatsapp_number != client_phone:
                    client.whatsapp_number = client_phone
                    updated = True

                if (
                    client_allergens is not None
                    and client.allergens != client_allergens
                ):
                    client.allergens = client_allergens
                    updated = True

                if updated:
                    client.save()
            reservation_status = validated_data.get(
                "reservation_status", instance.reservation_status
            )
            for attr, value in validated_data.items():
                setattr(instance, attr, value)

            # Reward
            if promotion:
                instance.promo_code = promotion.reward

            # ✅ Auto-set reservation_end_time and last_visit on COMPLETED status
            if reservation_status == ReservationStatus.COMPLETED:
                now = timezone.now()
                instance.reservation_end_time = now
                instance.client.last_visit = now
                instance.client.save()

            instance.save()
            if menus_data is not None:
                instance.menus.set(menus_data)

            # Send notification if reservation is cancelled
            if (
                "reservation_status" in validated_data
                and validated_data["reservation_status"] == ReservationStatus.CANCELLED
            ):
                whatsapp_number = instance.client.whatsapp_number
                twilio_number = instance.organization.whatsapp_bots.twilio_number
                message = (
                    f"❌ Your reservation on 📅 {instance.reservation_date} at ⏰ {instance.reservation_time} has been cancelled.\n"
                    f"📝**{instance.cancellation_reason}**\n"
                    "We hope to see you again soon! 😊"
                )

                send_cancellation_notification(twilio_number, whatsapp_number, message)

            return instance


class ReservationMessageSerializer(serializers.ModelSerializer):
    client = serializers.CharField(source="client.whatsapp_number", read_only=True)

    class Meta:
        model = ClientMessage
        fields = ["uid", "client", "role", "message", "media_url", "sent_at"]
