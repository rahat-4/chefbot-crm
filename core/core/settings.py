from datetime import timedelta
from decouple import config
from pathlib import Path
import os
from corsheaders.defaults import default_headers

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY")
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = [
    "194.164.77.123",
    "127.0.0.1",
    "localhost",
    "crm.chef-bot.de",
    "api.chef-bot.de",
    "chef-bot.de",
]


DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "phonenumber_field",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "drf_spectacular",
    "corsheaders",
    "channels",
    "django_celery_beat",
]

PROJECT_APPS = [
    "apps.authentication",
    "apps.organization",
    "apps.restaurant",
    "apps.openAI",
    "common",
]


INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + PROJECT_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"
APPEND_SLASH = False
AUTH_USER_MODEL = "authentication.User"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST"),
        "PORT": config("DB_PORT"),
    }
}

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
}


SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=90),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "ChefBot API",
    "DESCRIPTION": "Restaurant management chatbot API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# Email settings
SENDGRID_API_KEY = config("SENDGRID_API_KEY")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL")
OPENAI_API_KEY = config("OPENAI_API")


# Twilio
TWILIO_ACCOUNT_SID = config("MY_TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = config("MY_TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = config("TWILIO_WHATSAPP_NUMBER")

# Crypto password
CRYPTO_PASSWORD = config("CRYPTO_PASSWORD")

# OpenAI
ASSISTANT_ID = config("ASSISTANT_ID")

# Webhook url
WEBHOOK_URL = config("WEBHOOK_URL")

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://194.164.77.123:8000",
    "http://194.164.77.123:3000",
    "https://crm.chef-bot.de",
    "http://crm.chef-bot.de",
    "https://api.chef-bot.de",
    "https://chef-bot.de",
]

ACCESS_CONTROL_ALLOW_ORIGIN = [
    "http://localhost:3000",
    "http://194.164.77.123:8000",
    "http://194.164.77.123:3000",
    "https://crm.chef-bot.de",
    "http://crm.chef-bot.de",
    "https://api.chef-bot.de",
    "https://chef-bot.de",
]

CORS_ALLOW_HEADERS = list(default_headers) + [
    "authorization",
    "content-type",
    "accept",
    # add other headers if needed
]


# Logging configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": os.path.join(BASE_DIR, "whatsapp_bot.log"),
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": True,
        },
        "api.views.whatsapp": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "api.views.restaurants": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "api.serializers.restaurants": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "api.serializers.reservations": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "apps.openAI.utils": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}


# Channels configuration
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("redis", 6379)],
        },
    },
}


# Cookie settings for HTTP production
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "None"  # if cross-site cookies needed
SESSION_COOKIE_HTTPONLY = True  # keep for security

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "None"  # if cross-site cookies needed
CSRF_COOKIE_HTTPONLY = False  # allow frontend to read CSRF token


# Celery Configuration
CELERY_BROKER_URL = "redis://redis:6379/0"
CELERY_RESULT_BACKEND = "redis://redis:6379/0"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"


from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "send-scheduled-promotions-daily": {
        "task": "common.tasks.send_scheduled_promotions",
        "schedule": crontab(hour=6, minute=41),
    },
    # Reservation reminder task - run every 10 minutes
    "reservation-reminder-task": {
        "task": "common.tasks.reservation_reminder",
        "schedule": crontab(minute="*/5"),
    },
}
