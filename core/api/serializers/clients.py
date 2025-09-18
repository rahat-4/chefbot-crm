from rest_framework import serializers

from apps.restaurant.models import Client, ClientMessage


class ClientSerializer(serializers.ModelSerializer):
    history = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = [
            "uid",
            "name",
            "phone",
            "whatsapp_number",
            "email",
            "date_of_birth",
            "last_visit",
            "preferences",
            "allergens",
            "special_notes",
            "history",
        ]
        read_only_fields = [
            "uid",
            "name",
            "phone",
            "whatsapp_number",
            "email",
            "date_of_birth",
            "last_visit",
            "preferences",
            "allergens",
            "history",
        ]

    def get_history(self, obj):
        history = []
        for reservation in obj.reservations.all().order_by("-reservation_date"):
            history.append(
                {
                    "reservation_uid": reservation.uid,
                    "reservation_name": reservation.reservation_name,
                    "reservation_date": reservation.reservation_date,
                    "reservation_time": reservation.reservation_time,
                    "menu": [menu.name for menu in reservation.menus.all()],
                }
            )
        return history


class ClientMessageSerializer(serializers.ModelSerializer):
    client = serializers.CharField(source="client.whatsapp_number", read_only=True)

    class Meta:
        model = ClientMessage
        fields = ["uid", "client", "role", "message", "media_url", "sent_at"]
