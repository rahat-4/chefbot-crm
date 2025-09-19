from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
    get_object_or_404,
)

from apps.restaurant.models import Promotion, MessageTemplate
from apps.organization.choices import OrganizationType

from common.permissions import IsOwner

from ..serializers.promotions import PromotionSerializer


class PromotionListView(ListCreateAPIView):
    queryset = Promotion.objects.all()
    serializer_class = PromotionSerializer
    permission_classes = [IsOwner]

    def get_queryset(self):
        user = self.request.user

        return self.queryset.filter(
            organization__organization_users__user=user,
            organization__organization_type=OrganizationType.RESTAURANT,
        )


class PromotionDetailView(RetrieveUpdateDestroyAPIView):
    queryset = Promotion.objects.all()
    serializer_class = PromotionSerializer
    permission_classes = [IsOwner]

    def get_object(self):
        promotion_uid = self.kwargs.get("promotion_uid")

        return get_object_or_404(self.queryset, uid=promotion_uid)
