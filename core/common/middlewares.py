import logging

from django.utils.translation import activate
from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed

logger = logging.getLogger(__name__)


class JWTAuthCookieMiddleware:
    """
    Middleware to extract JWT token from HttpOnly cookies and add it to the Authorization header
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip certain paths to avoid unnecessary processing
        skip_paths = ["/admin/", "/static/", "/media/"]

        if not any(request.path.startswith(path) for path in skip_paths):
            # Check if Authorization header is already present
            auth_header = request.META.get("HTTP_AUTHORIZATION")

            if not auth_header or not auth_header.startswith("Bearer "):
                # Get access token from HttpOnly cookie
                access_token = request.COOKIES.get("access_token")

                if access_token:
                    # Add Bearer token to request headers
                    request.META["HTTP_AUTHORIZATION"] = f"Bearer {access_token}"
                    logger.debug(
                        f"JWT token added from cookie for path: {request.path}"
                    )
                else:
                    logger.debug(
                        f"No access token found in cookies for path: {request.path}"
                    )
            else:
                logger.debug(
                    f"Authorization header already present for path: {request.path}"
                )

        response = self.get_response(request)
        return response


class LanguageMiddleware(MiddlewareMixin):
    """
    Middleware to activate language based on JWT authenticated user's preference
    """

    def process_request(self, request):
        user = None

        # Try to authenticate user from JWT token
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")

        if auth_header.startswith("Bearer "):
            try:
                jwt_auth = JWTAuthentication()
                token = auth_header.split(" ")[1]
                validated_token = jwt_auth.get_validated_token(token)
                user = jwt_auth.get_user(validated_token)
            except (AuthenticationFailed, IndexError, AttributeError, Exception):
                # If JWT authentication fails, continue without user
                pass

        # If we have a user, use their language preference
        if user and user.is_authenticated:
            language_map = {
                "ENGLISH": "en",
                "GERMAN": "de",
            }
            language_code = language_map.get(user.language, "en")
            activate(language_code)
        else:
            # Fallback to Accept-Language header for unauthenticated requests
            accept_language = request.META.get("HTTP_ACCEPT_LANGUAGE", "en")
            language_code = accept_language.split(",")[0].split("-")[0][:2]

            if language_code in ["en", "de"]:
                activate(language_code)
            else:
                activate("en")
