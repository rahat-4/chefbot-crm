from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView

from apps.restaurant.models import SalesLevel

from ..serializers.sales_level import SalesLevelSerializer


class SalesLevelListView(ListAPIView):
    queryset = SalesLevel.objects.all()
    serializer_class = SalesLevelSerializer
    permission_classes = []


class SalesLevelDetailView(RetrieveUpdateAPIView):
    queryset = SalesLevel.objects.all()
    serializer_class = SalesLevelSerializer
    permission_classes = []

    def get_object(self):
        uid = self.kwargs.get("sales_level_uid")
        return SalesLevel.objects.get(uid=uid)
