"""Configuración del sistema de gestión de obras.

Los valores sensibles o que cambian entre la PC local y el servidor se leen
del archivo .env (ver .env.example).
"""

import os
from pathlib import Path

from django.contrib.messages import constants as mensajes
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(nombre, defecto=False):
    valor = os.getenv(nombre)
    if valor is None:
        return defecto
    return valor.strip().lower() in ("1", "true", "si", "sí", "yes", "on")


def env_lista(nombre, defecto=""):
    return [v.strip() for v in os.getenv(nombre, defecto).split(",") if v.strip()]


NOMBRE_ESTUDIO = os.getenv("NOMBRE_ESTUDIO", "Saez Sanchez Arquitectos")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-inseguro-solo-para-uso-local")
DEBUG = env_bool("DEBUG", True)
ALLOWED_HOSTS = env_lista("ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_lista("CSRF_TRUSTED_ORIGINS")
SITIO_URL = os.getenv("SITIO_URL", "http://127.0.0.1:8000").rstrip("/")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "huey.contrib.djhuey",
    "apps.core",
    "apps.cuentas",
    "apps.auditoria",
    "apps.obras",
    "apps.plantillas",
    # Se activan a medida que se construye cada sección:
    "apps.documentos",
    # "apps.notificaciones",
    # "apps.aprobaciones",
    # "apps.comunicados",
    # "apps.portal",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.auditoria.middleware.RequestActualMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.globales",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "data" / "db.sqlite3",
    }
}

AUTH_USER_MODEL = "cuentas.Usuario"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "core:inicio"
LOGOUT_REDIRECT_URL = "login"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-ar"
TIME_ZONE = os.getenv("ZONA_HORARIA", "America/Argentina/Buenos_Aires")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Los archivos subidos NUNCA se sirven directo: se descargan por vistas que
# verifican permisos. Por eso no hay MEDIA_URL publicada en urls.py.
MEDIA_ROOT = BASE_DIR / "media"
MAX_ARCHIVO_MB = int(os.getenv("MAX_ARCHIVO_MB", "300"))
EXTENSIONES_BLOQUEADAS = {
    ".exe", ".bat", ".cmd", ".com", ".msi", ".scr", ".ps1", ".vbs", ".js",
    ".jar", ".sh", ".dll", ".html", ".htm", ".svg",
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MESSAGE_TAGS = {mensajes.ERROR: "danger"}

# --- Email ---
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.filebased.EmailBackend")
EMAIL_FILE_PATH = BASE_DIR / "data" / "emails"
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "Estudio <no-responder@estudio.local>")

# --- WhatsApp ---
WHATSAPP_BACKEND = os.getenv("WHATSAPP_BACKEND", "simulado")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
WHATSAPP_PLANTILLA = os.getenv("WHATSAPP_PLANTILLA", "aviso_estudio")
WHATSAPP_IDIOMA = os.getenv("WHATSAPP_IDIOMA", "es_AR")
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v21.0")
WHATSAPP_LOG_SIMULADO = BASE_DIR / "data" / "whatsapp_simulado.log"

# --- Aprobaciones ---
ENLACE_DIAS_VALIDEZ = int(os.getenv("ENLACE_DIAS_VALIDEZ", "7"))

# --- Tareas en segundo plano (Huey sobre SQLite, sin Redis) ---
HUEY = {
    "huey_class": "huey.SqliteHuey",
    "name": "gestion_obras",
    "filename": str(BASE_DIR / "data" / "tareas.db"),
    "immediate": env_bool("TAREAS_INMEDIATAS", True),
    "consumer": {"workers": 2, "worker_type": "thread"},
}

# Solo tomar la IP de X-Forwarded-For si hay un proxy de confianza adelante.
CONFIAR_EN_PROXY = env_bool("CONFIAR_EN_PROXY", False)

# --- Publicado en internet (DEBUG=false, detrás de nginx con HTTPS) ---
if not DEBUG:
    # Cada versión de los estilos y scripts tiene su propio nombre (app.3f2a….css), así el navegador
    # nunca se queda con una versión vieja después de actualizar.
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"},
    }
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    if CONFIAR_EN_PROXY:
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {"archivo": {"class": "logging.FileHandler", "filename": BASE_DIR / "data" / "errores.log"}},
        "loggers": {
            "django": {"handlers": ["archivo"], "level": "ERROR"},
            # Bots que prueban direcciones ajenas: no ensuciar el registro de errores.
            "django.security.DisallowedHost": {"handlers": [], "propagate": False},
        },
    }
