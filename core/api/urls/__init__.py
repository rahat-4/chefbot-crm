from django.urls import path, include


urlpatterns = [
    path("/auth", include("api.urls.auth")),
    path("/restaurants", include("api.urls.restaurants")),
]
