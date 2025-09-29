from django.urls import path, include


urlpatterns = [
    path("/promotions", include("api.urls.promotions")),
    path("/reservations", include("api.urls.reservations")),
    path("/auth", include("api.urls.auth")),
    path("/restaurants", include("api.urls.restaurants")),
    path("/whatsapp", include("api.urls.whatsapp")),
    path("/clients", include("api.urls.clients")),
]
