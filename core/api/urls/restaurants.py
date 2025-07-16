from django.urls import path

from ..views.restaurants import (
    RestaurantMenuDetailView,
    RestaurantMenuListView,
    RestaurantCreateView,
    RestaurantDetailView,
    ServicesListView,
    ServiceDetailView,
)

urlpatterns = [
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
    path("", RestaurantCreateView.as_view(), name="restaurant.list"),
    path(
        "/services/<uuid:service_uid>",
        ServiceDetailView.as_view(),
        name="restaurant.service-detail",
    ),
    path("/services", ServicesListView.as_view(), name="restaurant.services-list"),
]
