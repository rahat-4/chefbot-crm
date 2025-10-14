from django.http import HttpResponse

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
from common.excels import generate_excel, get_timestamped_filename

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


class PromotionReportExportExcelView(APIView):
    permission_classes = [IsOwner]

    def get(self, request, *args, **kwargs):
        user = request.user
        promotion_uid = self.kwargs.get("promotion_uid")

        try:
            promotion = Promotion.objects.get(
                uid=promotion_uid,
                organization__organization_users__user=user,
                organization__organization_type=OrganizationType.RESTAURANT,
            )
        except Promotion.DoesNotExist:
            return Response({"detail": "Promotion not found."}, status=404)

        sent_logs = PromotionSentLog.objects.filter(promotion=promotion).select_related(
            "client"
        )

        title = f"Promotion - {promotion.title}"
        headers = ["Client Name", "WhatsApp", "Status", "Sent At"]

        data = []
        for log in sent_logs:
            data.append(
                {
                    "Client Name": log.client.name,
                    "WhatsApp": log.client.whatsapp_number,
                    "Status": log.status,
                    "Sent At": (
                        log.sent_at.strftime("%Y-%m-%d %H:%M") if log.sent_at else ""
                    ),
                }
            )

        excel_file = generate_excel(title, headers, data)
        filename = get_timestamped_filename("promotion_report")

        response = HttpResponse(
            excel_file.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f"attachment; filename={filename}"

        return response
