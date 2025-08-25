from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
    get_object_or_404,
)

from apps.restaurant.models import Reservation
from apps.organization.choices import OrganizationType

from common.permissions import IsOwner
from common.filters import ReservationDateRangeFilter

from ..serializers.reservations import ReservationSerializer
from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend


class ReservationListView(ListCreateAPIView):
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer
    permission_classes = [IsOwner]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = ReservationDateRangeFilter
    search_fields = [
        "client__name",
        "client__phone",
        "client__whatsapp_number",
        "reservation_name",
        "reservation_phone",
    ]
    ordering_fields = ["reservation_date"]

    def get_queryset(self):
        user = self.request.user

        return self.queryset.filter(
            organization__organization_users__user=user,
            organization__organization_type=OrganizationType.RESTAURANT,
        )


class ReservationDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer
    permission_classes = [IsOwner]

    def get_object(self):
        reservation_uid = self.kwargs.get("reservation_uid")

        return get_object_or_404(self.queryset, uid=reservation_uid)
