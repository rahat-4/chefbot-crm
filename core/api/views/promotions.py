from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
    get_object_or_404,
)
from rest_framework.views import APIView
from rest_framework.response import Response

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
    queryset = PromotionSentLog.objects.all()
    serializer_class = PromotionSentLogSerializer
    permission_classes = [IsOwner]

    def list(self, request, *args, **kwargs):
        # Get the related promotion object
        promotion_uid = self.kwargs.get("promotion_uid")

        try:
            promotion = Promotion.objects.get(uid=promotion_uid)
        except Promotion.DoesNotExist:
            return Response({"detail": "Promotion not found."}, status=404)

        queryset = self.get_queryset().filter(promotion=promotion)

        # Compute additional statistics
        total_send = queryset.filter(promotion=promotion).count()
        total_failed = queryset.filter(
            promotion=promotion, status=PromotionSentLogStatus.FAILED
        ).count()
        total_delivered = queryset.filter(
            promotion=promotion, status=PromotionSentLogStatus.DELIVERED
        ).count()
        total_converted = Reservation.objects.filter(
            promo_code=promotion.reward
        ).count()

        # Serialize the data
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
