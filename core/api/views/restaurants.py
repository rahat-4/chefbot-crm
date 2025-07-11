from rest_framework.generics import (
    CreateAPIView,
    ListCreateAPIView,
    RetrieveUpdateAPIView,
    RetrieveUpdateDestroyAPIView,
)

from apps.organization.models import Organization, Services
from apps.organization.choices import OrganizationType

from common.permissions import IsAdmin, IsOwner

from ..serializers.restaurants import RestaurantSerializer, ServicesSerializer


class ServicesListView(ListCreateAPIView):
    queryset = Services.objects.all()
    serializer_class = ServicesSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            self.permission_classes = [IsAdmin]
        else:
            self.permission_classes = [IsOwner]
        return super().get_permissions()


class ServiceDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Services.objects.all()
    serializer_class = ServicesSerializer
    permission_classes = [IsAdmin]

    def get_object(self):
        service_uid = self.kwargs.get("service_uid")

        return self.queryset.get(uid=service_uid)


class RestaurantCreateView(CreateAPIView):
    queryset = Organization.objects.all()
    serializer_class = RestaurantSerializer
    permission_classes = [IsOwner]


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
