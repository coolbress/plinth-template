"""Django settings, read from the environment.

Nothing secret is written here. Production sets `DJANGO_SECRET_KEY`,
`DJANGO_ALLOWED_HOSTS` and `DATABASE_URL` in the host's environment; the entry
point (`__main__.py`) refuses to start without them. `DJANGO_DEBUG=1`
turns debug on for local work only.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlsplit

from django.core.management.utils import get_random_secret_key

PACKAGE_DIR = Path(__file__).resolve().parent

DEBUG = os.environ.get("DJANGO_DEBUG") == "1"

# A key made per process when none is set: tests and local commands run, and a
# production start without one is refused in `__main__`, never served with a
# key that changes on every restart.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or get_random_secret_key()

ALLOWED_HOSTS = [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h]
if DEBUG:
    ALLOWED_HOSTS += ["localhost", "127.0.0.1"]


def database(url: str | None) -> dict[str, object]:
    """`DATABASE_URL` as Django's DATABASES entry; SQLite in the working directory when unset."""
    if not url:
        return {"ENGINE": "django.db.backends.sqlite3", "NAME": Path.cwd() / "db.sqlite3"}
    parts = urlsplit(url)
    if parts.scheme not in ("postgres", "postgresql"):
        raise ValueError(f"DATABASE_URL must be a postgres:// URL, not {parts.scheme}://")
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": unquote(parts.path.lstrip("/")),
        "USER": unquote(parts.username or ""),
        "PASSWORD": unquote(parts.password or ""),
        "HOST": parts.hostname or "",
        "PORT": str(parts.port or ""),
        "CONN_MAX_AGE": 60,
        # Connection options in the query (`?sslmode=verify-full`) reach psycopg as given.
        "OPTIONS": dict(parse_qsl(parts.query)),
    }


DATABASES = {"default": database(os.environ.get("DATABASE_URL"))}

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Right after security: it answers /static/ before the rest runs.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = f"{__package__}.urls"

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

ASGI_APPLICATION = f"{__package__}.asgi.application"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
# Django sets the process time zone from this; UTC keeps log timestamps in one zone.
TIME_ZONE = "UTC"
STATIC_URL = "static/"
# `collectstatic` writes here; the image runs it at build time, inside the
# package so the run stage carries the files, and WhiteNoise serves them.
STATIC_ROOT = PACKAGE_DIR / "staticfiles"

# Behind the host's TLS proxy: production answers over HTTPS only.
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    # The health check is asked over plain HTTP from inside the host and the image check.
    SECURE_REDIRECT_EXEMPT = [r"^healthz$"]
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 3600

# HSTS preload and include-subdomains are the owner's choice, not a default:
# preload is hard to undo, and subdomains reach the whole domain. To turn one
# on, set SECURE_HSTS_PRELOAD or SECURE_HSTS_INCLUDE_SUBDOMAINS to True above
# and remove its check here. `ci / deploy-check` passes either way.
SILENCED_SYSTEM_CHECKS = [
    "security.W005",  # SECURE_HSTS_INCLUDE_SUBDOMAINS
    "security.W021",  # SECURE_HSTS_PRELOAD
]
