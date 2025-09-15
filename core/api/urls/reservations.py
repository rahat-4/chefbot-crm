from django.urls import path

from ..views.reservations import (
    ReservationListView,
    ReservationDetailView,
    ReservationMessageListView,
)

urlpatterns = [
    path(
        "/<uuid:reservation_uid>/messages",
        ReservationMessageListView.as_view(),
        name="reservation.message-list",
    ),
    path(
        "/<uuid:reservation_uid>",
        ReservationDetailView.as_view(),
        name="reservation.detail",
    ),
    path("", ReservationListView.as_view(), name="reservation.list"),
]
