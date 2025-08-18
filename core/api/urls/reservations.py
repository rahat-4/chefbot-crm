from django.urls import path

from ..views.reservations import ReservationListView, ReservationDetailView

urlpatterns = [
    path(
        "/<uuid:reservation_uid>",
        ReservationDetailView.as_view(),
        name="reservation-detail",
    ),
    path("", ReservationListView.as_view(), name="reservation-list"),
]
