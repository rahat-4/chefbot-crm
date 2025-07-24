from django.urls import path

from ..views.restaurants import (
    RestaurantPromotionListView,
    RestaurantMenuAllergensView,
    RestaurantMenuDetailView,
    RestaurantMenuListView,
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
        "/<uuid:restaurant_uid>",
        RestaurantDetailView.as_view(),
        name="restaurant.detail",
    ),
    path("", RestaurantListView.as_view(), name="restaurant.list"),
]
