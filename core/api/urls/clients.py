from django.urls import path

from ..views.clients import ClientListView, ClientDetailView

urlpatterns = [
    path("", ClientListView.as_view(), name="client-list"),
    path("/<uuid:client_uid>", ClientDetailView.as_view(), name="client-detail"),
]
