from django.urls import path

from ..views.auth import (
    UserRegistrationSessionView,
    UserPasswordSetView,
    LoginView,
    LogoutView,
)

urlpatterns = [
    path("/logout", LogoutView.as_view(), name="logout"),
    path("/login", LoginView.as_view(), name="login"),
    path(
        "/<uuid:session_uid>/password-set",
        UserPasswordSetView.as_view(),
        name="verify-email",
    ),
    path(
        "/registration", UserRegistrationSessionView.as_view(), name="user-registration"
    ),
]
