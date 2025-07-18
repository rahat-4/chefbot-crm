from django.db import transaction

from rest_framework import serializers

from common.openai_api import generate_nutrition_info

from apps.organization.choices import OrganizationType
from apps.organization.models import (
    Organization,
    OrganizationUser,
    OpeningHours,
    Services,
    OrganizationServices,
)
from apps.restaurant.choices import CategoryChoices, ClassificationChoices
from apps.restaurant.models import Menu


class ServicesSerializer(serializers.ModelSerializer):

    class Meta:
        model = Services
        fields = ["uid", "name", "description"]


class OpeningHoursSerializer(serializers.ModelSerializer):

    class Meta:
        model = OpeningHours
        exclude = ["organization", "created_at", "updated_at"]


class RestaurantSerializer(serializers.ModelSerializer):
    service_list = serializers.SlugRelatedField(
        queryset=Services.objects.all(), many=True, slug_field="uid", write_only=True
    )
    services = serializers.SerializerMethodField()
    opening_hours = OpeningHoursSerializer(many=True)

    class Meta:
        model = Organization
        fields = [
            "uid",
            "logo",
            "name",
            "whatsapp_number",
            "email",
            "description",
            "website",
            "country",
            "city",
            "street",
            "zip_code",
            "service_list",
            "services",
            "opening_hours",
        ]

    def get_services(self, obj):
        services = Services.objects.filter(organization_services__organization=obj)
        return ServicesSerializer(services, many=True).data

    def create(self, validated_data):
        with transaction.atomic():
            service_list = validated_data.pop("service_list", [])
            opening_hours = validated_data.pop("opening_hours", [])
            organization = Organization.objects.create(
                organization_type=OrganizationType.RESTAURANT, **validated_data
            )

            OrganizationUser.objects.create(
                organization=organization,
                user=self.context["request"].user,
            )

            for service in service_list:
                OrganizationServices.objects.create(
                    organization=organization, service=service
                )

            for opening_hour in opening_hours:
                OpeningHours.objects.create(organization=organization, **opening_hour)
            return organization

    def update(self, instance, validated_data):
        with transaction.atomic():
            service_list = validated_data.pop("service_list", [])
            opening_hours = validated_data.pop("opening_hours", [])

            for attr, value in validated_data.items():
                setattr(instance, attr, value)

            instance.save()

            # Services
            if service_list is not None:
                OrganizationServices.objects.filter(organization=instance).delete()
                for service in service_list:
                    OrganizationServices.objects.create(
                        organization=instance, service=service
                    )

            # Opening Hours
            if opening_hours is not None:
                OpeningHours.objects.filter(organization=instance).delete()
                for opening_hour in opening_hours:
                    OpeningHours.objects.create(organization=instance, **opening_hour)
            return instance


class RestaurantMenuSerializer(serializers.ModelSerializer):

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

    def create(self, validated_data):
        ingredients = validated_data.get("ingredients", [])

        if ingredients:
            response = generate_nutrition_info(ingredients)

            validated_data["allergens"] = response["allergens"]
            validated_data["macronutrients"] = response["macronutrients"]

        return super().create(validated_data)

    def update(self, instance, validated_data):
        ingredients = validated_data.get("ingredients", [])

        if ingredients:
            response = generate_nutrition_info(ingredients)

            validated_data["allergens"] = response["allergens"]
            validated_data["macronutrients"] = response["macronutrients"]

        return super().update(instance, validated_data)


class RestaurantMenuAllergensSerializer(serializers.ModelSerializer):

    class Meta:
        model = Menu
        fields = ["allergens"]
