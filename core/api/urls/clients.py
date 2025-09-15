from django.urls import path

from ..views.clients import ClientListView, ClientDetailView, ClientMessageListView

urlpatterns = [
    path(
        "/<uuid:client_uid>/messages",
        ClientMessageListView.as_view(),
        name="whatsapp.client-message-list",
    ),
    path("/<uuid:client_uid>", ClientDetailView.as_view(), name="client-detail"),
    path("", ClientListView.as_view(), name="client-list"),
]
