from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
    get_object_or_404,
)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.restaurant.models import Promotion, PromotionSentLog, Reservation
from apps.restaurant.choices import PromotionSentLogStatus
from apps.organization.models import MessageTemplate
from apps.organization.choices import OrganizationType

from common.permissions import IsOwner

from ..serializers.promotions import PromotionSerializer, PromotionSentLogSerializer


class PromotionListView(ListCreateAPIView):
    queryset = Promotion.objects.all()
    serializer_class = PromotionSerializer
    permission_classes = [IsOwner]

    def get_queryset(self):
        user = self.request.user

        return self.queryset.filter(
            organization__organization_users__user=user,
            organization__organization_type=OrganizationType.RESTAURANT,
        )


class PromotionDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Promotion.objects.all()
    serializer_class = PromotionSerializer
    permission_classes = [IsOwner]

    def get_object(self):
        promotion_uid = self.kwargs.get("promotion_uid")

        return get_object_or_404(self.queryset, uid=promotion_uid)


class PromotionSentLogListView(ListAPIView):
    serializer_class = PromotionSentLogSerializer
    permission_classes = [IsOwner]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["client__name", "client__whatsapp_number"]
    ordering_fields = ["sent_at", "client__name"]

    def get_queryset(self):
        promotion_uid = self.kwargs.get("promotion_uid")
        return PromotionSentLog.objects.filter(promotion__uid=promotion_uid)

    def list(self, request, *args, **kwargs):
        # Get the related promotion object
        promotion_uid = self.kwargs.get("promotion_uid")

        try:
            promotion = Promotion.objects.get(uid=promotion_uid)
        except Promotion.DoesNotExist:
            return Response({"detail": "Promotion not found."}, status=404)

        # Get filtered and searched queryset
        queryset = self.filter_queryset(self.get_queryset())

        # Compute additional statistics based on the unfiltered logs
        total_send = self.get_queryset().count()
        total_failed = (
            self.get_queryset().filter(status=PromotionSentLogStatus.FAILED).count()
        )
        total_delivered = (
            self.get_queryset().filter(status=PromotionSentLogStatus.DELIVERED).count()
        )
        total_converted = Reservation.objects.filter(
            promo_code=promotion.reward
        ).count()

        # Serialize the filtered logs
        serializer = self.get_serializer(queryset, many=True)

        response_data = {
            "title": promotion.title,
            "total_send": total_send,
            "total_delivered": total_delivered,
            "total_failed": total_failed,
            "total_converted": total_converted,
            "logs": serializer.data,
        }

        return Response(response_data)
