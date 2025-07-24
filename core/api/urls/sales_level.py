from django.urls import path

from ..views.sales_level import SalesLevelListView, SalesLevelDetailView

urlpatterns = [
    path(
        "/<uuid:sales_level_uid>",
        SalesLevelDetailView.as_view(),
        name="sales_level_detail",
    ),
    path("", SalesLevelListView.as_view(), name="sales_level_list"),
]
