from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import unquote, urlparse


BASE_DIR = Path(__file__).resolve().parent.parent


def _csv_env(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _env(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def _bool_env(name: str, default: str) -> bool:
    return _env(name, default).lower() in {"1", "true", "yes", "on"}


def _append_unique(values: list[str], *entries: str) -> list[str]:
    for entry in entries:
        if entry and entry not in values:
            values.append(entry)
    return values


def _database_from_url(database_url: str) -> dict[str, str]:
    parsed = urlparse(database_url)
    scheme = parsed.scheme.lower()

    if scheme in {"postgres", "postgresql", "postgresql+psycopg", "postgresql+psycopg2"}:
        engine = "django.db.backends.postgresql"
    elif scheme == "sqlite":
        engine = "django.db.backends.sqlite3"
    else:
        engine = scheme

    if engine == "django.db.backends.sqlite3":
        name = parsed.path or ":memory:"
        if name == "/:memory:":
            name = ":memory:"
        return {"ENGINE": engine, "NAME": name}

    return {
        "ENGINE": engine,
        "NAME": parsed.path.lstrip("/"),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or ""),
    }


def _database_config() -> dict[str, str]:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        return _database_from_url(database_url)

    db_engine = _env("DJANGO_DB_ENGINE", "django.db.backends.postgresql")
    db_name = _env(
        "DJANGO_DB_NAME",
        "bunge_mkononi" if db_engine.endswith("postgresql") else str(BASE_DIR / "db.sqlite3"),
    )
    if db_engine.endswith("sqlite3") and not os.path.isabs(db_name):
        db_name = str(BASE_DIR / db_name)

    return {
        "ENGINE": db_engine,
        "NAME": db_name,
        "USER": _env("DJANGO_DB_USER", "postgres" if db_engine.endswith("postgresql") else ""),
        "PASSWORD": _env("DJANGO_DB_PASSWORD", ""),
        "HOST": _env("DJANGO_DB_HOST", "localhost" if db_engine.endswith("postgresql") else ""),
        "PORT": _env("DJANGO_DB_PORT", "5432" if db_engine.endswith("postgresql") else ""),
    }


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        normalized_key = key.strip()
        normalized_value = value.strip().strip('"').strip("'")
        if os.environ.get(normalized_key) in {None, ""}:
            os.environ[normalized_key] = normalized_value


_load_env_file(BASE_DIR / ".env")


SECRET_KEY = _env("DJANGO_SECRET_KEY", "django-insecure-change-me-for-local-dev")
_is_render = os.getenv("RENDER", "").lower() == "true" or bool(os.getenv("RENDER_EXTERNAL_HOSTNAME"))
DEBUG = _bool_env("DJANGO_DEBUG", "0" if _is_render else "1")
ALLOWED_HOSTS = _csv_env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
if _is_render:
    _append_unique(ALLOWED_HOSTS, ".onrender.com")
render_hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if render_hostname:
    _append_unique(ALLOWED_HOSTS, render_hostname)

frontend_origin = _env("DJANGO_FRONTEND_ORIGIN", "https://bunge-mkononi.vercel.app")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "apps.legislative.apps.LegislativeConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "bunge_backend.urls"

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

WSGI_APPLICATION = "bunge_backend.wsgi.application"
ASGI_APPLICATION = "bunge_backend.asgi.application"

DATABASES = {"default": _database_config()}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
if not DEBUG:
    SESSION_COOKIE_SAMESITE = "None"
    CSRF_COOKIE_SAMESITE = "None"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if _is_render else None

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AFRICASTALKING_USERNAME = _env("AFRICASTALKING_USERNAME", "sandbox")
AFRICASTALKING_API_KEY = _env("AFRICASTALKING_API_KEY", "")
AFRICASTALKING_SHORT_CODE = _env("AFRICASTALKING_SHORT_CODE", "")
AFRICASTALKING_SMS_TIMEOUT = int(_env("AFRICASTALKING_SMS_TIMEOUT", "20"))

CORS_ALLOWED_ORIGINS = _csv_env("DJANGO_CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
CORS_ALLOW_CREDENTIALS = True
if frontend_origin:
    _append_unique(CORS_ALLOWED_ORIGINS, frontend_origin)
CSRF_TRUSTED_ORIGINS = _csv_env("DJANGO_CSRF_TRUSTED_ORIGINS", "")
if not CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS = list(CORS_ALLOWED_ORIGINS)
if _is_render:
    _append_unique(CSRF_TRUSTED_ORIGINS, "https://*.onrender.com")
if render_hostname:
    _append_unique(CSRF_TRUSTED_ORIGINS, f"https://{render_hostname}")
if frontend_origin:
    _append_unique(CSRF_TRUSTED_ORIGINS, frontend_origin)

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}
