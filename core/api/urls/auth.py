from django.urls import path

from ..views.auth import (
    UserRegistrationSessionView,
    UserPasswordSetView,
    UserChangePasswordView,
    LoginView,
    LogoutView,
    MeView,
)

urlpatterns = [
    path("/me", MeView.as_view(), name="me"),
    path("/logout", LogoutView.as_view(), name="logout"),
    # path("/login", LoginView.as_view(), name="login"),
    path("/change-password", UserChangePasswordView.as_view(), name="change-password"),
    path(
        "/<uuid:session_uid>/password-set",
        UserPasswordSetView.as_view(),
        name="verify-email",
    ),
    path(
        "/registration", UserRegistrationSessionView.as_view(), name="user-registration"
    ),
]
