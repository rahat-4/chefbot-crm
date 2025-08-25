from django.urls import path

from ..views.clients import ClientListView

urlpatterns = [
    path("", ClientListView.as_view(), name="client-list"),
]
