from django.contrib.auth import get_user_model

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import CreateAPIView

from apps.authentication.models import RegistrationSession

from ..serializers.auth import (
    UserRegistrationSessionSerializer,
    UserPasswordSetSerializer,
)

User = get_user_model()


class UserRegistrationSessionView(CreateAPIView):
    queryset = RegistrationSession.objects.all()
    serializer_class = UserRegistrationSessionSerializer
    permission_classes = []


class UserPasswordSetView(APIView):
    serializer_class = UserPasswordSetSerializer
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={"view": self})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"password": "Password set successfully."}, status=status.HTTP_200_OK
        )
