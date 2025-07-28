from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateAPIView,
    RetrieveUpdateDestroyAPIView,
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
)

from common.permissions import IsAdmin, IsOwner

from ..serializers.restaurants import (
    RestaurantSerializer,
    RestaurantTableSerializer,
    RestaurantMenuSerializer,
    RestaurantMenuAllergensSerializer,
    RestaurantWhatsAppBotSerializer,
    RestaurantPromotionSerializer,
)


class RestaurantListView(ListCreateAPIView):
    queryset = Organization.objects.all()
    serializer_class = RestaurantSerializer
    permission_classes = [IsOwner]

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
    queryset = Menu.objects.filter(status=MenuStatus.ACTIVE)
    serializer_class = RestaurantMenuSerializer
    permission_classes = [IsOwner]

    def get_queryset(self):
        organization_uid = self.kwargs.get("restaurant_uid")
        return self.queryset.filter(organization__uid=organization_uid)

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.user.organization_users.first().organization
        )
        return super().perform_create(serializer)


class RestaurantMenuDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Menu.objects.filter(status=MenuStatus.ACTIVE)
    serializer_class = RestaurantMenuSerializer
    permission_classes = [IsOwner]

    def get_object(self):
        organization_uid = self.kwargs.get("restaurant_uid")
        menu_uid = self.kwargs.get("menu_uid")

        return self.queryset.get(organization__uid=organization_uid, uid=menu_uid)

    def perform_destroy(self, instance):
        instance.status = MenuStatus.DELETED
        instance.save()

        return instance


class RestaurantWhatsAppBotListView(ListCreateAPIView):
    queryset = WhatsappBot.objects.all()
    serializer_class = RestaurantWhatsAppBotSerializer
    permission_classes = [IsOwner]

    def perform_create(self, serializer):
        restaurant_uid = self.kwargs.get("restaurant_uid")
        organization = Organization.objects.get(uid=restaurant_uid)

        serializer.save(organization=organization)
        return super().perform_create(serializer)


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
