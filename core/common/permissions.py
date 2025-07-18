from rest_framework.permissions import BasePermission

from apps.authentication.choices import UserType


class IsAdmin(BasePermission):
    """
    Custom permission to only allow admin users to access certain views.
    """

    def has_permission(self, request, view):
        # Check if the user is authenticated and is an admin
        return (
            request.user and request.user.is_authenticated and request.user.is_superuser
        )


class IsOwner(BasePermission):
    """
    Custom permission to only allow owner to access certain views.
    """

    def has_permission(self, request, view):
        # Check if the user is authenticated and is an owner
        return (
            request.user
            and request.user.is_authenticated
            and request.user.user_type == UserType.OWNER
        )
