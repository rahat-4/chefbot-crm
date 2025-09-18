from rest_framework.generics import (
    ListAPIView,
    RetrieveUpdateDestroyAPIView,
    get_object_or_404,
)
from rest_framework import filters

from django_filters.rest_framework import DjangoFilterBackend


from apps.organization.choices import OrganizationType
from apps.restaurant.models import Client, ClientMessage

from common.permissions import IsOwner

from ..serializers.clients import ClientSerializer, ClientMessageSerializer


class ClientListView(ListAPIView):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [IsOwner]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ["name", "phone", "whatsapp_number", "email"]

    def get_queryset(self):
        user = self.request.user

        return self.queryset.filter(
            organization__organization_users__user=user,
            organization__organization_type=OrganizationType.RESTAURANT,
        )


class ClientDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [IsOwner]

    def get_object(self):
        client_uid = self.kwargs.get("client_uid")

        return get_object_or_404(self.queryset, uid=client_uid)


class ClientMessageListView(ListAPIView):
    queryset = ClientMessage.objects.all()
    serializer_class = ClientMessageSerializer
    pagination_class = None

    def get_queryset(self):
        client_uid = self.kwargs["client_uid"]
        client = get_object_or_404(Client, uid=client_uid)

        self.queryset = self.queryset.filter(client=client)

        return self.queryset.order_by("created_at")
