from django.urls import path

from ..views.whatsapp import (
    whatsapp_bot,
    RestaurantWhatsAppListView,
    RestaurantWhatsAppDetailView,
)

urlpatterns = [
    path("/bot", whatsapp_bot, name="whatsapp-bot"),
    path(
        "/<uuid:whatsapp_bot_uid>",
        RestaurantWhatsAppDetailView.as_view(),
        name="restaurant.whatsapp-detail",
    ),
    path("", RestaurantWhatsAppListView.as_view(), name="restaurant.whatsapp-list"),
]
