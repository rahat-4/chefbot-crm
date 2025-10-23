import logging

from datetime import datetime, date, timedelta

from rest_framework.response import Response
from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateAPIView,
    RetrieveUpdateDestroyAPIView,
    ValidationError,
    RetrieveDestroyAPIView,
)
from rest_framework.views import APIView

from rest_framework import filters
from django_filters.rest_framework import DjangoFilterBackend


from apps.organization.models import (
    Organization,
    OpeningHours,
    MessageTemplate,
)
from apps.organization.choices import OrganizationType
from apps.restaurant.choices import MenuStatus, RewardCategory
from apps.restaurant.models import (
    RestaurantTable,
    Menu,
    Reservation,
    RestaurantDocument,
    Promotion,
)

from common.permissions import IsOwner
from common.filters import ReservationFilter

from ..serializers.restaurants import (
    RestaurantSerializer,
    RestaurantTableSerializer,
    RestaurantMenuSerializer,
    MessageTemplateSerializer,
    RestaurantMenuAllergensSerializer,
    RestaurantDocumentSerializer,
    RestaurantDashboardSerializer,
    RestaurantPromotionsSerializer,
)

logger = logging.getLogger(__name__)


class RestaurantListView(ListCreateAPIView):
    queryset = Organization.objects.all()
    serializer_class = RestaurantSerializer
    permission_classes = [IsOwner]

    def get_queryset(self):
        user = self.request.user

        return self.queryset.filter(
            organization_users__user=user,
            organization_type=OrganizationType.RESTAURANT,
        )


class RestaurantDetailView(RetrieveUpdateAPIView):
    queryset = Organization.objects.all()
    serializer_class = RestaurantSerializer
    permission_classes = [IsOwner]

    def get_object(self):
        restaurant_uid = self.kwargs.get("restaurant_uid")
        user = self.request.user

        restaurant = self.queryset.get(
            uid=restaurant_uid,
            organization_users__user=user,
            organization_type=OrganizationType.RESTAURANT,
        )

        return restaurant


class RestaurantTableListView(ListCreateAPIView):
    queryset = RestaurantTable.objects.all()
    serializer_class = RestaurantTableSerializer
    permission_classes = [IsOwner]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status"]

    def perform_create(self, serializer):
        restaurant_uid = self.kwargs.get("restaurant_uid")
        organization = Organization.objects.get(uid=restaurant_uid)

        serializer.save(organization=organization)
        return super().perform_create(serializer)

    def get_queryset(self):
        organization_uid = self.kwargs.get("restaurant_uid")
        return self.queryset.filter(organization__uid=organization_uid)


class RestaurantTableDetailView(RetrieveUpdateDestroyAPIView):
    queryset = RestaurantTable.objects.all()
    serializer_class = RestaurantTableSerializer
    permission_classes = [IsOwner]

    def get_object(self):
        restaurant_uid = self.kwargs.get("restaurant_uid")
        table_uid = self.kwargs.get("table_uid")

        return self.queryset.get(organization__uid=restaurant_uid, uid=table_uid)


class RestaurantMenuListView(ListCreateAPIView):
    serializer_class = RestaurantMenuSerializer
    permission_classes = [IsOwner]

    def get_queryset(self):
        restaurant_uid = self.kwargs.get("restaurant_uid")
        return Menu.objects.filter(
            status=MenuStatus.ACTIVE,
            organization__uid=restaurant_uid,
        )

    def perform_create(self, serializer):
        restaurant_uid = self.kwargs.get("restaurant_uid")
        restaurant = Organization.objects.filter(uid=restaurant_uid).first()

        if not restaurant:
            raise ValidationError({"organization": "Invalid restaurant."})

        serializer.save(organization=restaurant)


class RestaurantMenuDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Menu.objects.filter(status=MenuStatus.ACTIVE)
    serializer_class = RestaurantMenuSerializer
    permission_classes = [IsOwner]

    def get_object(self):
        organization_uid = self.kwargs.get("restaurant_uid")
        menu_uid = self.kwargs.get("menu_uid")

        return self.queryset.get(organization__uid=organization_uid, uid=menu_uid)


class RestaurantMenuAllergensView(RetrieveUpdateAPIView):
    queryset = Menu.objects.filter(status=MenuStatus.ACTIVE)
    serializer_class = RestaurantMenuAllergensSerializer
    permission_classes = [IsOwner]

    def get_object(self):
        organization_uid = self.kwargs.get("restaurant_uid")
        menu_uid = self.kwargs.get("menu_uid")

        return self.queryset.get(organization__uid=organization_uid, uid=menu_uid)

    def perform_update(self, serializer):
        serializer.save(
            organization=self.request.user.organization_users.first().organization
        )
        return super().perform_update(serializer)


class RestaurantDocumentListView(ListCreateAPIView):
    queryset = RestaurantDocument.objects.all()
    serializer_class = RestaurantDocumentSerializer
    permission_classes = [IsOwner]

    def get_queryset(self):
        restaurant_uid = self.kwargs.get("restaurant_uid")
        return self.queryset.filter(organization__uid=restaurant_uid)

    def perform_create(self, serializer):
        restaurant_uid = self.kwargs.get("restaurant_uid")
        organization = Organization.objects.get(uid=restaurant_uid)

        # Delete existing menu document if it exists
        existing_doc = RestaurantDocument.objects.filter(
            organization=organization, name="menu"
        ).first()
        if existing_doc:
            existing_doc.file.delete(save=False)  # delete file from storage
            existing_doc.delete()  # delete old DB record

        # Save new document
        serializer.save(organization=organization, name="menu")


class RestaurantDocumentDetailView(RetrieveDestroyAPIView):
    queryset = RestaurantDocument.objects.all()
    serializer_class = RestaurantDocumentSerializer
    permission_classes = [IsOwner]

    def get_object(self):
        restaurant_uid = self.kwargs.get("restaurant_uid")
        document_uid = self.kwargs.get("document_uid")

        return self.queryset.get(organization__uid=restaurant_uid, uid=document_uid)


class RestaurantDashboardView(APIView):
    permission_classes = [IsOwner]

    def get_active_promotion(self, organization):
        today = date.today()
        return organization.promotions.filter(
            is_enabled=True, valid_from__lte=today, valid_to__gte=today
        )

    def get(self, request, *args, **kwargs):
        restaurant_uid = self.kwargs.get("restaurant_uid")
        organization = Organization.objects.filter(uid=restaurant_uid).first()

        if not organization:
            return Response({"error": "Invalid restaurant."}, status=404)

        # Gather dashboard data
        data = {
            "today_reservation": Reservation.objects.filter(
                organization=organization, reservation_date=datetime.today()
            ).count(),
            "next_reservation": Reservation.objects.filter(
                organization=organization, reservation_time__gt=datetime.now()
            )
            .order_by("reservation_time")
            .first(),
            "sales_level": (
                organization.sales_levels.first().level
                if organization.sales_levels.first()
                else 0
            ),
            "active_promotions": self.get_active_promotion(organization),
        }

        serializer = RestaurantDashboardSerializer(data)

        return Response(serializer.data)


class RestaurantAnalyticsTopDishesView(APIView):
    def filter_menus(self, restaurant_uid, category=None):
        """Filter menus by restaurant and optional category."""
        menus = Menu.objects.filter(organization__uid=restaurant_uid)
        if category:
            menus = menus.filter(category=category)
        return menus

    def get(self, request, *args, **kwargs):
        restaurant_uid = self.kwargs.get("restaurant_uid")

        # Query params
        category = request.query_params.get("category")
        time_range = request.query_params.get("time_range")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        top_dishes = {}

        menus = self.filter_menus(restaurant_uid, category)
        reservations = Reservation.objects.filter(
            organization__uid=restaurant_uid, menus__in=menus
        )

        filtered_reservations = (
            ReservationFilter(reservations)
            .filter(time_range, start_date, end_date)
            .values_list("menus__name", flat=True)
        )

        for dish in filtered_reservations:
            top_dishes[dish] = top_dishes.get(dish, 0) + 1

        total_orders = sum(top_dishes.values()) or 1  # Avoid division by zero

        top_dishes_list = [
            {
                "name": name,
                "orders": count,
                "share_of_total_sales": round((count / total_orders) * 100, 2),
            }
            for name, count in top_dishes.items()
        ]

        return Response(top_dishes_list)


class RestaurantAnalyticsMostVisitedView(APIView):
    def time_slots(self, opening_hours):
        """Generate 2-hour slots per opening hour record."""
        slots = []
        slot_duration = timedelta(hours=2)

        for opening_hour in opening_hours:
            if (
                opening_hour.is_closed
                or not opening_hour.opening_start_time
                or not opening_hour.opening_end_time
            ):
                continue

            start_dt = datetime.combine(date.today(), opening_hour.opening_start_time)
            end_dt = datetime.combine(date.today(), opening_hour.opening_end_time)
            if start_dt >= end_dt:
                continue

            break_start = (
                datetime.combine(date.today(), opening_hour.break_start_time)
                if opening_hour.break_start_time
                else None
            )
            break_end = (
                datetime.combine(date.today(), opening_hour.break_end_time)
                if opening_hour.break_end_time
                else None
            )

            current = start_dt
            day_slots = []
            while current + slot_duration <= end_dt:
                slot_start = current.time()
                slot_end = (current + slot_duration).time()

                # Skip if overlaps break period
                if break_start and break_end:
                    if not (
                        current + slot_duration <= break_start or current >= break_end
                    ):
                        current += slot_duration
                        continue

                day_slots.append((slot_start, slot_end))
                current += slot_duration

            if day_slots:
                slots.append({"day": opening_hour.day, "slots": day_slots})

        return slots

    def get(self, request, *args, **kwargs):
        restaurant_uid = self.kwargs.get("restaurant_uid")

        # Query params
        time_range = request.query_params.get("time_range")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        slots = []
        opening_hours = OpeningHours.objects.filter(organization__uid=restaurant_uid)

        for opening_hour in self.time_slots(opening_hours):
            day_name = opening_hour["day"]
            slots.append({"day": day_name, "visits": []})

            # Map day name -> Django weekday integer
            day_map = {
                "SUNDAY": 1,
                "MONDAY": 2,
                "TUESDAY": 3,
                "WEDNESDAY": 4,
                "THURSDAY": 5,
                "FRIDAY": 6,
                "SATURDAY": 7,
            }
            day_number = day_map.get(day_name)

            for slot_start, slot_end in opening_hour["slots"]:
                reservations = Reservation.objects.filter(
                    organization__uid=restaurant_uid,
                    reservation_time__range=(slot_start, slot_end),
                    reservation_date__week_day=day_number,
                )

                total_reservations = ReservationFilter(reservations).filter(
                    time_range, start_date, end_date
                )

                slots[-1]["visits"].append(
                    {
                        "slot": f"{slot_start.strftime('%H:%M')}-{slot_end.strftime('%H:%M')}",
                        "count": total_reservations.count(),
                    }
                )

        return Response(slots)


class MessageTemplateListView(ListCreateAPIView):
    queryset = MessageTemplate.objects.all()
    serializer_class = MessageTemplateSerializer
    permission_classes = [IsOwner]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
    ]
    search_fields = ["name"]

    def get_queryset(self):
        restaurant_uid = self.kwargs.get("restaurant_uid")

        return self.queryset.filter(
            organization__uid=restaurant_uid,
            organization__organization_type=OrganizationType.RESTAURANT,
        )


class RestaurantPromotionListView(ListAPIView):
    queryset = Promotion.objects.all()
    serializer_class = RestaurantPromotionsSerializer
    permission_classes = [IsOwner]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ["reward_type", "reward_label"]
    ordering_fields = ["created_at", "valid_from", "valid_to"]

    def get_queryset(self):
        restaurant_uid = self.kwargs.get("restaurant_uid")
        user = self.request.user

        return self.queryset.filter(
            organization__uid=restaurant_uid,
            organization__organization_users__user=user,
            organization__organization_type=OrganizationType.RESTAURANT,
            is_enabled=True,
            valid_to__gte=date.today(),
            reward__reward_category=RewardCategory.PROMOTION,
        )
