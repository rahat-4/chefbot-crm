from datetime import datetime, timedelta
import django_filters

from django.utils.timezone import now

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


class ReservationFilter:
    def __init__(self, reservations):
        self.reservations = reservations
        self.today = now().date()

    def filter(self, time_range=None, start_date=None, end_date=None):
        if time_range:
            self._apply_time_range_filter(time_range)

        if start_date and end_date:
            self._apply_custom_date_filter(start_date, end_date)

        return self.reservations

    def _apply_time_range_filter(self, time_range):
        if time_range == "today":
            self.reservations = self.reservations.filter(reservation_date=self.today)

        elif time_range == "yesterday":
            self.reservations = self.reservations.filter(
                reservation_date=self.today - timedelta(days=1)
            )

        elif time_range == "last_7_days":
            self.reservations = self.reservations.filter(
                reservation_date__gte=self.today - timedelta(days=7)
            )

        elif time_range == "last_30_days":
            self.reservations = self.reservations.filter(
                reservation_date__gte=self.today - timedelta(days=30)
            )

        elif time_range == "this_week":
            start_of_week = self.today - timedelta(days=self.today.weekday())
            self.reservations = self.reservations.filter(
                reservation_date__gte=start_of_week
            )

        elif time_range == "last_week":
            start_of_last_week = self.today - timedelta(days=self.today.weekday() + 7)
            end_of_last_week = start_of_last_week + timedelta(days=6)
            self.reservations = self.reservations.filter(
                reservation_date__range=(start_of_last_week, end_of_last_week)
            )

        elif time_range == "this_month":
            self.reservations = self.reservations.filter(
                reservation_date__month=self.today.month,
                reservation_date__year=self.today.year,
            )

        elif time_range == "last_month":
            last_month = self.today.month - 1 or 12
            year = self.today.year if self.today.month != 1 else self.today.year - 1
            self.reservations = self.reservations.filter(
                reservation_date__month=last_month,
                reservation_date__year=year,
            )

    def _apply_custom_date_filter(self, start_date, end_date):
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            self.reservations = self.reservations.filter(
                reservation_date__range=(start, end)
            )
        except ValueError:
            self.reservations = self.reservations.none()
