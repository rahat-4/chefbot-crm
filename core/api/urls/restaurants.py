from django.urls import path

from ..views.restaurants import (
    RestaurantPromotionListView,
    RestaurantWhatsAppBotDetailView,
    RestaurantWhatsAppBotListView,
    RestaurantMenuAllergensView,
    RestaurantMenuDetailView,
    RestaurantMenuListView,
    RestaurantTableListView,
    RestaurantListView,
    RestaurantDetailView,
)

urlpatterns = [
    path(
        "/<uuid:restaurant_uid>/promotions",
        RestaurantPromotionListView.as_view(),
        name="restaurant.promotions-list",
    ),
    path(
        "/<uuid:restaurant_uid>/whatsapp-bot/<uuid:whatsapp_bot_uid>",
        RestaurantWhatsAppBotDetailView.as_view(),
        name="restaurant.whatsapp-bot-detail",
    ),
    path(
        "/<uuid:restaurant_uid>/whatsapp-bot",
        RestaurantWhatsAppBotListView.as_view(),
        name="restaurant.whatsapp-bot",
    ),
    path(
        "/<uuid:restaurant_uid>/menu/<uuid:menu_uid>/allergens",
        RestaurantMenuAllergensView.as_view(),
        name="restaurant.menu-allergens",
    ),
    path(
        "/<uuid:restaurant_uid>/menu/<uuid:menu_uid>",
        RestaurantMenuDetailView.as_view(),
        name="restaurant.menu-detail",
    ),
    path(
        "/<uuid:restaurant_uid>/menu",
        RestaurantMenuListView.as_view(),
        name="restaurant.menu-list",
    ),
    path(
        "/<uuid:restaurant_uid>/tables",
        RestaurantTableListView.as_view(),
        name="restaurant.table-list",
    ),
    path(
        "/<uuid:restaurant_uid>",
        RestaurantDetailView.as_view(),
        name="restaurant.detail",
    ),
    path("", RestaurantListView.as_view(), name="restaurant.list"),
]
