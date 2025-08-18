import logging

from django.shortcuts import get_object_or_404

from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateAPIView,
    RetrieveUpdateDestroyAPIView,
    ValidationError,
)

from apps.organization.models import Organization, WhatsappBot
from apps.organization.choices import OrganizationType
from apps.restaurant.choices import CategoryChoices, ClassificationChoices, MenuStatus
from apps.restaurant.models import (
    RestaurantTable,
    Menu,
    Reward,
    Promotion,
    PromotionTrigger,
    Reservation,
)

from common.permissions import IsAdmin, IsOwner

from ..serializers.restaurants import (
    RestaurantSerializer,
    RestaurantTableSerializer,
    RestaurantMenuSerializer,
    RestaurantMenuAllergensSerializer,
    RestaurantWhatsAppBotSerializer,
    RestaurantWhatsAppBotUpdateSerializer,
    RestaurantPromotionSerializer,
    RestaurantReservationSerializer,
)


logger = logging.getLogger(__name__)


class RestaurantListView(ListCreateAPIView):
    queryset = Organization.objects.all()
    serializer_class = RestaurantSerializer
    permission_classes = [IsOwner]

    def get_queryset(self):
        user = self.request.user

        return self.queryset.filter(
            organization_users__user=user,
            organization_type=OrganizationType.RESTAURANT,
        )

    # def get_permissions(self):
    #     if self.request.method == "POST":
    #         self.permission_classes = [IsOwner]
    #     else:
    #         self.permission_classes = [IsAdmin]
    #     return super().get_permissions()


class RestaurantDetailView(RetrieveUpdateAPIView):
    queryset = Organization.objects.all()
    serializer_class = RestaurantSerializer
    permission_classes = [IsOwner]

    def get_object(self):
        restaurant_uid = self.kwargs.get("restaurant_uid")
        user = self.request.user

        restaurant = self.queryset.get(
            uid=restaurant_uid,
            organization_users__user=user,
            organization_type=OrganizationType.RESTAURANT,
        )

        return restaurant


class RestaurantTableListView(ListCreateAPIView):
    queryset = RestaurantTable.objects.all()
    serializer_class = RestaurantTableSerializer
    permission_classes = [IsOwner]

    def perform_create(self, serializer):
        restaurant_uid = self.kwargs.get("restaurant_uid")
        organization = Organization.objects.get(uid=restaurant_uid)

        serializer.save(organization=organization)
        return super().perform_create(serializer)

    def get_queryset(self):
        organization_uid = self.kwargs.get("restaurant_uid")
        return self.queryset.filter(organization__uid=organization_uid)


class RestaurantMenuListView(ListCreateAPIView):
    serializer_class = RestaurantMenuSerializer
    permission_classes = [IsOwner]

    def get_queryset(self):
        restaurant_uid = self.kwargs.get("restaurant_uid")
        return Menu.objects.filter(
            status=MenuStatus.ACTIVE,
            organization__uid=restaurant_uid,
        )

    def perform_create(self, serializer):
        restaurant_uid = self.kwargs.get("restaurant_uid")
        restaurant = Organization.objects.filter(uid=restaurant_uid).first()

        if not restaurant:
            raise ValidationError({"organization": "Invalid organization."})

        serializer.save(organization=restaurant)


class RestaurantMenuDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Menu.objects.filter(status=MenuStatus.ACTIVE)
    serializer_class = RestaurantMenuSerializer
    permission_classes = [IsOwner]

    def get_object(self):
        organization_uid = self.kwargs.get("restaurant_uid")
        menu_uid = self.kwargs.get("menu_uid")

        return self.queryset.get(organization__uid=organization_uid, uid=menu_uid)


class RestaurantWhatsAppBotListView(ListCreateAPIView):
    serializer_class = RestaurantWhatsAppBotSerializer
    permission_classes = [IsOwner]

    def get_organization(self):
        """Get organization from URL parameter with caching."""
        if not hasattr(self, "_organization"):
            restaurant_uid = self.kwargs.get("restaurant_uid")
            if not restaurant_uid:
                raise ValidationError("Restaurant UID is required.")

            self._organization = get_object_or_404(
                Organization.objects.select_related("parent"), uid=restaurant_uid
            )
        return self._organization

    def get_queryset(self):
        """Get queryset filtered by organization or its parent."""
        organization = self.get_organization()

        # Use parent organization if it exists, otherwise use the organization itself
        target_org = organization.parent or organization

        return WhatsappBot.objects.filter(organization=target_org)

    def perform_create(self, serializer):
        """Create WhatsApp bot for the organization."""
        organization = self.get_organization()
        serializer.save(organization=organization)


class RestaurantWhatsAppBotDetailView(RetrieveUpdateAPIView):
    queryset = WhatsappBot.objects.all()
    serializer_class = RestaurantWhatsAppBotSerializer
    permission_classes = [IsOwner]

    def get_object(self):
        organization_uid = self.kwargs.get("restaurant_uid")
        whatsapp_bot_uid = self.kwargs.get("whatsapp_bot_uid")

        return self.queryset.get(
            organization__uid=organization_uid, uid=whatsapp_bot_uid
        )

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return RestaurantWhatsAppBotUpdateSerializer
        return RestaurantWhatsAppBotSerializer


class RestaurantMenuAllergensView(RetrieveUpdateAPIView):
    queryset = Menu.objects.filter(status=MenuStatus.ACTIVE)
    serializer_class = RestaurantMenuAllergensSerializer
    permission_classes = [IsOwner]

    def get_object(self):
        organization_uid = self.kwargs.get("restaurant_uid")
        menu_uid = self.kwargs.get("menu_uid")

        return self.queryset.get(organization__uid=organization_uid, uid=menu_uid)

    def perform_update(self, serializer):
        serializer.save(
            organization=self.request.user.organization_users.first().organization
        )
        return super().perform_update(serializer)


class RestaurantPromotionListView(ListCreateAPIView):
    queryset = Promotion.objects.all()
    serializer_class = RestaurantPromotionSerializer
    permission_classes = [IsOwner]

    def get_queryset(self):
        organization_uid = self.kwargs.get("restaurant_uid")
        return self.queryset.filter(organization__uid=organization_uid)

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.user.organization_users.first().organization
        )
        return super().perform_create(serializer)


class RestaurantReservationListView(ListCreateAPIView):
    queryset = Reservation.objects.all()
    serializer_class = RestaurantReservationSerializer
    permission_classes = [IsOwner]

    def get_queryset(self):
        organization_uid = self.kwargs.get("restaurant_uid")
        return self.queryset.filter(organization__uid=organization_uid)
