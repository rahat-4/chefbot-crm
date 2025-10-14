from django.http import HttpResponse

from rest_framework.generics import (
    ListAPIView,
    RetrieveUpdateDestroyAPIView,
    get_object_or_404,
)
from rest_framework import filters
from rest_framework.views import APIView

from django_filters.rest_framework import DjangoFilterBackend


from apps.organization.choices import OrganizationType
from apps.restaurant.models import Client, ClientMessage

from common.permissions import IsOwner
from common.excels import (
    generate_excel,
    get_timestamped_filename,
    format_phone_number,
    format_day_month,
)

from ..serializers.clients import ClientSerializer, ClientMessageSerializer


class ClientListView(ListAPIView):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [IsOwner]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ["name", "phone", "whatsapp_number", "email"]

    def get_queryset(self):
        user = self.request.user

        return self.queryset.filter(
            organization__organization_users__user=user,
            organization__organization_type=OrganizationType.RESTAURANT,
        )


class ClientDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [IsOwner]

    def get_object(self):
        client_uid = self.kwargs.get("client_uid")

        return get_object_or_404(self.queryset, uid=client_uid)


class ClientMessageListView(ListAPIView):
    queryset = ClientMessage.objects.all()
    serializer_class = ClientMessageSerializer
    pagination_class = None

    def get_queryset(self):
        client_uid = self.kwargs["client_uid"]
        client = get_object_or_404(Client, uid=client_uid)

        self.queryset = self.queryset.filter(client=client)

        return self.queryset.order_by("created_at")


class ClientExportExcelView(APIView):

    def get(self, request, *args, **kwargs):
        user = request.user

        clients = Client.objects.filter(
            organization__organization_users__user=user,
            organization__organization_type=OrganizationType.RESTAURANT,
        )

        title = "Clients"
        headers = [
            "Name",
            "Phone",
            "WhatsApp Number",
            "Email",
            "Source",
            "Date of Birth",
            "Anniversary",
            "Last Visit",
            "Preferences",
            "Allergens",
            "Special Notes",
        ]

        client_data = []
        for client in clients:
            client_data.append(
                {
                    "Name": client.name,
                    "Phone": format_phone_number(client.phone),
                    "WhatsApp Number": client.whatsapp_number,
                    "Email": client.email or "",
                    "Source": client.source,
                    "Date of Birth": format_day_month(client.date_of_birth),
                    "Anniversary Date": format_day_month(client.anniversary_date),
                    "Last Visit": (
                        client.last_visit.strftime("%Y-%m-%d %H:%M")
                        if client.last_visit
                        else ""
                    ),
                    "Preferences": (
                        ", ".join(client.preferences)
                        if isinstance(client.preferences, list)
                        else client.preferences or ""
                    ),
                    "Allergens": (
                        ", ".join(client.allergens)
                        if isinstance(client.allergens, list)
                        else ""
                    ),
                    "Special Notes": client.special_notes or "",
                }
            )

        excel_file = generate_excel(title, headers, client_data)
        filename = get_timestamped_filename("client_data")

        response = HttpResponse(
            excel_file.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f"attachment; filename={filename}"

        return response
