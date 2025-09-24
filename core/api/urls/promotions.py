from django.urls import path

from ..views.promotions import (
    PromotionListView,
    PromotionDetailView,
    PromotionSentLogListView,
)

urlpatterns = [
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
