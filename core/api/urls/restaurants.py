from django.urls import path

from ..views.restaurants import (
    RestaurantMenuAllergensView,
    RestaurantMenuDetailView,
    RestaurantMenuListView,
    RestaurantTableListView,
    RestaurantTableDetailView,
    RestaurantListView,
    RestaurantDetailView,
    RestaurantDocumentListView,
    RestaurantDashboardView,
    RestaurantAnalyticsView,
)

urlpatterns = [
    path(
        "/<uuid:restaurant_uid>/analytics",
        RestaurantAnalyticsView.as_view(),
        name="restaurant.analytics",
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
        "/<uuid:restaurant_uid>/dashboard",
        RestaurantDashboardView.as_view(),
        name="restaurant.dashboard",
    ),
    path(
        "/<uuid:restaurant_uid>/documents",
        RestaurantDocumentListView.as_view(),
        name="restaurant.document-list",
    ),
    path(
        "/<uuid:restaurant_uid>/tables/<uuid:table_uid>",
        RestaurantTableDetailView.as_view(),
        name="restaurant.table-detail",
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
