from django.urls import path

from ..views.auth import UserRegistrationSessionView, UserPasswordSetView

urlpatterns = [
    path(
        "/registration", UserRegistrationSessionView.as_view(), name="user-registration"
    ),
    path(
        "/<uuid:session_uid>/password-set",
        UserPasswordSetView.as_view(),
        name="verify-email",
    ),
]
