import logging

from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateAPIView,
    RetrieveUpdateDestroyAPIView,
    ValidationError,
)

from apps.organization.models import Organization
from apps.organization.choices import OrganizationType
from apps.restaurant.choices import MenuStatus
from apps.restaurant.models import (
    RestaurantTable,
    Menu,
    Reservation,
    RestaurantDocument,
)

from common.permissions import IsOwner

from ..serializers.restaurants import (
    RestaurantSerializer,
    RestaurantTableSerializer,
    RestaurantMenuSerializer,
    RestaurantMenuAllergensSerializer,
    RestaurantDocumentSerializer,
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


class RestaurantTableDetailView(RetrieveUpdateDestroyAPIView):
    queryset = RestaurantTable.objects.all()
    serializer_class = RestaurantTableSerializer
    permission_classes = [IsOwner]

    def get_object(self):
        restaurant_uid = self.kwargs.get("restaurant_uid")
        table_uid = self.kwargs.get("table_uid")

        return self.queryset.get(organization__uid=restaurant_uid, uid=table_uid)


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


class RestaurantDocumentListView(ListCreateAPIView):
    queryset = RestaurantDocument.objects.all()
    serializer_class = RestaurantDocumentSerializer
    permission_classes = [IsOwner]

    def get_queryset(self):
        restaurant_uid = self.kwargs.get("restaurant_uid")
        return self.queryset.filter(organization__uid=restaurant_uid)

    def perform_create(self, serializer):
        restaurant_uid = self.kwargs.get("restaurant_uid")
        organization = Organization.objects.get(uid=restaurant_uid)

        # Delete existing menu document if it exists
        existing_doc = RestaurantDocument.objects.filter(
            organization=organization, name="menu"
        ).first()
        if existing_doc:
            existing_doc.file.delete(save=False)  # delete file from storage
            existing_doc.delete()  # delete old DB record

        # Save new document
        serializer.save(organization=organization, name="menu")
