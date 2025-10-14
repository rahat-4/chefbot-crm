from django.urls import path

from ..views.whatsapp import (
    whatsapp_bot,
    RestaurantWhatsAppListView,
    RestaurantWhatsAppDetailView,
    WhatsappClientListView,
    WhatsappClientExportExcelView,
)

urlpatterns = [
    path("/bot", whatsapp_bot, name="whatsapp-bot"),
    path(
        "/<uuid:whatsapp_bot_uid>/clients/export-excel",
        WhatsappClientExportExcelView.as_view(),
        name="whatsapp.client-export",
    ),
    path(
        "/<uuid:whatsapp_bot_uid>/clients",
        WhatsappClientListView.as_view(),
        name="whatsapp.client-list",
    ),
    path(
        "/<uuid:whatsapp_bot_uid>",
        RestaurantWhatsAppDetailView.as_view(),
        name="restaurant.whatsapp-detail",
    ),
    path("", RestaurantWhatsAppListView.as_view(), name="restaurant.whatsapp-list"),
]
