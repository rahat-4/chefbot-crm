from rest_framework import serializers

from apps.restaurant.models import Client


class ClientSerializers(serializers.ModelSerializer):
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
            "created_at",
        ]
