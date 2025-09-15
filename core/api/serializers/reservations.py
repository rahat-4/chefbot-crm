from django.db import transaction

from rest_framework import serializers

from apps.organization.models import Organization
from apps.restaurant.models import (
    Client,
    Menu,
    Reservation,
    RestaurantTable,
    ClientMessage,
)
from apps.restaurant.choices import (
    ReservationCancelledBy,
    ReservationStatus,
    ClientMessageRole,
)

from common.whatsapp import send_cancellation_notification


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
    client = serializers.SlugRelatedField(
        queryset=Client.objects.all(), slug_field="uid"
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
            "cancellation_reason",
            "booking_reminder_sent",
            "booking_reminder_sent_at",
            "menus",
            "table",
            "organization",
        ]

        read_only_fields = ["uid", "cancelled_by"]

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
        rep["client"] = ClientSerializer(instance.client).data
        rep["menus"] = MenuSerializer(instance.menus.all(), many=True).data
        rep["table"] = TableSerializer(instance.table).data
        rep["organization"] = {
            "uid": instance.organization.uid,
            "name": instance.organization.name,
        }
        return rep

    def create(self, validated_data):
        menus_data = validated_data.pop("menus", [])
        reservation = Reservation.objects.create(**validated_data)
        if menus_data:
            reservation.menus.set(menus_data)
        return reservation

    def update(self, instance, validated_data):
        with transaction.atomic():
            menus_data = validated_data.pop("menus", None)
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
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
