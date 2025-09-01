from django.urls import path

from ..views.promotions import PromotionListView, PromotionDetailView

urlpatterns = [
    path(
        "/<uuid:promotion_uid>", PromotionDetailView.as_view(), name="promotion-detail"
    ),
    path("", PromotionListView.as_view(), name="promotion-list"),
]
