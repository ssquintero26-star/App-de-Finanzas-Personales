"""Configuración de despliegue: DJANGO_SETTINGS_MODULE=fintrack.production."""

import os
from copy import deepcopy

from django.core.exceptions import ImproperlyConfigured

from . import settings as base_settings
from .settings import *  # noqa: F401,F403

DEBUG = False
SECRET_KEY = os.environ.get("SECRET_KEY", "")
if (
    len(SECRET_KEY) < 50
    or len(set(SECRET_KEY)) < 5
    or SECRET_KEY.startswith("django-insecure-")
):
    raise ImproperlyConfigured(
        "Producción requiere SECRET_KEY aleatoria de al menos 50 caracteres."
    )

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "").split(",")
    if host.strip()
]
if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "Configura ALLOWED_HOSTS con los dominios del servidor, sin '*'."
    )

CSRF_TRUSTED_ORIGINS = [
    value.strip()
    for value in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if value.strip()
]
CORS_ALLOWED_ORIGINS = [
    value.strip()
    for value in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")
    if value.strip()
]
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = (
    os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", "False").lower() == "true"
)
SECURE_HSTS_PRELOAD = os.getenv("SECURE_HSTS_PRELOAD", "False").lower() == "true"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
if os.getenv("TRUST_PROXY_HTTPS", "False").lower() == "true":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

MIDDLEWARE = [
    base_settings.MIDDLEWARE[0],
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *base_settings.MIDDLEWARE[1:],
]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}
DATABASES = deepcopy(base_settings.DATABASES)
DATABASES["default"]["OPTIONS"] = {"timeout": 20}
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
