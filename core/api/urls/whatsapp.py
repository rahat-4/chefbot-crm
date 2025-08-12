from django.urls import path

from ..views.whatsapp import whatsapp_bot, RestaurantWhatsAppListView

urlpatterns = [
    path("/bot", whatsapp_bot, name="whatsapp-bot"),
    path("", RestaurantWhatsAppListView.as_view(), name="restaurant.whatsapp-list"),
]
