import django_filters

from apps.restaurant.models import Reservation


class ReservationDateRangeFilter(django_filters.FilterSet):
    reservation_date_after = django_filters.DateFilter(
        field_name="reservation_date", lookup_expr="gte"
    )
    reservation_date_before = django_filters.DateFilter(
        field_name="reservation_date", lookup_expr="lte"
    )

    class Meta:
        model = Reservation
        fields = [
            "reservation_date_after",
            "reservation_date_before",
            "reservation_status",
            "cancelled_by",
        ]
