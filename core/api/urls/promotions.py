from django.urls import path

from ..views.promotions import (
    PromotionListView,
    PromotionDetailView,
    PromotionSentLogListView,
    PromotionReportExportExcelView,
)

urlpatterns = [
    path(
        "/<uuid:promotion_uid>/sent-logs/export-excel",
        PromotionReportExportExcelView.as_view(),
        name="promotion.report.excel",
    ),
    path(
        "/<uuid:promotion_uid>/sent-logs",
        PromotionSentLogListView.as_view(),
        name="promotion.sent_logs",
    ),
    path(
        "/<uuid:promotion_uid>", PromotionDetailView.as_view(), name="promotion.detail"
    ),
    path("", PromotionListView.as_view(), name="promotion.list"),
]
