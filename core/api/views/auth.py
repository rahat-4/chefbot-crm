import logging

from django.contrib.auth import get_user_model

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import CreateAPIView

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from apps.authentication.models import RegistrationSession

from ..serializers.auth import (
    UserRegistrationSessionSerializer,
    UserPasswordSetSerializer,
)

User = get_user_model()


logger = logging.getLogger("django.request")


def is_development(request):
    host_name = request.META.get("HTTP_HOST").split(":")[0]

    return host_name in ["localhost", "127.0.0.1"]


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


class LoginView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        errors = {}

        email = request.data.get("email")
        password = request.data.get("password")

        user = User.objects.filter(email=email).first()

        if not user:
            errors["email"] = ["User with this email does not exist."]
        elif not user.check_password(password):
            errors["password"] = ["Password is incorrect."]

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        response = super().post(request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK:
            access_token = response.data.get("access")
            refresh_token = response.data.get("refresh")

            access_max_age = 60 * 15 * 60  # 15 hours
            refresh_max_age = 60 * 60 * 24  # 1 days

            # Cookie settings based on environment
            # is_dev = is_development(request)

            cookie_settings = {"httponly": True, "samesite": "Lax", "secure": False}

            response.set_cookie(
                key="access_token",
                value=access_token,
                max_age=access_max_age,
                **cookie_settings,
            )
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                max_age=refresh_max_age,
                **cookie_settings,
            )

            response.data = {
                "message": "Successfully logged in.",
            }

        return response


class LogoutView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.COOKIES.get("refresh_token")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except TokenError:
            pass
        except Exception as e:
            logger.warning(f"Error during logout token blacklisting: {e}")

        response = Response(
            {"message": "Successfully logged out."}, status=status.HTTP_200_OK
        )

        # Delete cookies -- only path/domain can be speified, not secure/httponly
        response.delete_cookie("access_token", path="/")
        response.delete_cookie("refresh_token", path="/")

        return response
