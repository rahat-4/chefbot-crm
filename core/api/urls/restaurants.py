from django.urls import path

from ..views.restaurants import (
    RestaurantCreateView,
    RestaurantDetailView,
    ServicesListView,
    ServiceDetailView,
)

urlpatterns = [
    path(
        "/services/<uuid:service_uid>",
        ServiceDetailView.as_view(),
        name="service-detail",
    ),
    path("/services", ServicesListView.as_view(), name="services-list"),
    path(
        "/<uuid:restaurant_uid>",
        RestaurantDetailView.as_view(),
        name="restaurant-detail",
    ),
    path("", RestaurantCreateView.as_view(), name="restaurant-create"),
]
