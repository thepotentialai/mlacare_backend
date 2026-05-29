import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

# Charge mlacare_backend/.env pour le dev local (os.getenv ne lit pas .env tout seul).
load_dotenv(BASE_DIR / '.env')

def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')

_DEFAULT_DEV_SECRET_KEY = (
    'django-insecure-#i$zsz1zp7p3u--mk+4gv0tbfb(puw2v54v+&&0tvw6p-8#9am'
)

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', _DEFAULT_DEV_SECRET_KEY)

DEBUG = env_bool('DEBUG', True)

ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv(
        'ALLOWED_HOSTS',
        'localhost,127.0.0.1,mlacare.mladoctors.org' if not DEBUG else 'localhost,127.0.0.1',
    ).split(',')
    if h.strip()
]

if not DEBUG:
    if SECRET_KEY == _DEFAULT_DEV_SECRET_KEY:
        raise ImproperlyConfigured(
            'Production requires DJANGO_SECRET_KEY (do not use the default dev key).'
        )
    if not ALLOWED_HOSTS:
        raise ImproperlyConfigured('Production requires ALLOWED_HOSTS to list at least one host.')

# ─── Applications ────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'django_filters',
    # Local apps
    'accounts',
    'agents',
    'patients',
    'visits',
    'notifications',
    'payments',
    'admin_api',
    'matching',  # kept for migration history only — app logic removed
]

# ─── Middleware ───────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'mlacare.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'mlacare.wsgi.application'

# ─── Database (PostgreSQL only) ──────────────────────────────────────────────
# Local par defaut quand DEBUG=True; forcer via USE_LOCAL_DB.
USE_LOCAL_DB = env_bool('USE_LOCAL_DB', DEBUG)

if USE_LOCAL_DB:
    db_name = os.getenv('LOCAL_PGDATABASE', 'mlacare_db')
    db_user = os.getenv('LOCAL_PGUSER', 'postgres')
    db_password = os.getenv('LOCAL_PGPASSWORD', '')
    db_host = os.getenv('LOCAL_PGHOST', 'localhost')
    db_port = os.getenv('LOCAL_PGPORT', '5432')
    db_sslmode = os.getenv('LOCAL_PGSSLMODE', 'disable')
else:
    db_name = os.getenv('PGDATABASE', 'mlacare_db')
    db_user = os.getenv('PGUSER', 'postgres')
    db_password = os.getenv('PGPASSWORD', '')
    db_host = os.getenv('PGHOST', 'localhost')
    db_port = os.getenv('PGPORT', '5432')
    db_sslmode = os.getenv('PGSSLMODE', 'require')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': db_name,
        'USER': db_user,
        'PASSWORD': db_password,
        'HOST': db_host,
        'PORT': db_port,
        'CONN_MAX_AGE': int(os.getenv('DB_CONN_MAX_AGE', '60')),
        'OPTIONS': {
            'sslmode': db_sslmode,
        },
    }
}

if not DEBUG and not USE_LOCAL_DB:
    if not db_password:
        raise ImproperlyConfigured('Production requires PGPASSWORD for the remote database.')
    if db_host in ('', 'localhost', '127.0.0.1'):
        raise ImproperlyConfigured(
            'Production requires a remote PGHOST (not localhost) when USE_LOCAL_DB is false.'
        )

# ─── Custom user model & auth ────────────────────────────────────────────────
AUTH_USER_MODEL = 'accounts.User'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# ─── Password validation ─────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─── Django REST Framework ────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# ─── Simple JWT ──────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=2),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# ─── CORS ────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        'CORS_ALLOWED_ORIGINS',
        (
            'https://mlacare.mladoctors.org'
            if not DEBUG
            else 'http://localhost:5173,http://localhost:5174,http://localhost:3000'
        ),
    ).split(',')
    if origin.strip()
]

CORS_ALLOW_CREDENTIALS = True

# ─── Internationalization ─────────────────────────────────────────────────────
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Abidjan'
USE_I18N = True
USE_TZ = True

# ─── Static & Media files ────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Sur hébergement type O2switch (Passenger), les fichiers media ne sont pas dans le docroot :
# activez pour servir /media/ via Django (OK pour trafic modéré).
SERVE_MEDIA_VIA_DJANGO = os.getenv('SERVE_MEDIA_VIA_DJANGO', 'False').lower() in (
    '1', 'true', 'yes'
)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── Production (HTTPS, cookies, proxy) ─────────────────────────────────────
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

    if env_bool('SECURE_SSL_REDIRECT', True):
        SECURE_SSL_REDIRECT = True

    hsts = os.getenv('SECURE_HSTS_SECONDS', '')
    if hsts.isdigit():
        SECURE_HSTS_SECONDS = int(hsts)
        SECURE_HSTS_INCLUDE_SUBDOMAINS = (
            env_bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', False)
        )
        SECURE_HSTS_PRELOAD = (
            env_bool('SECURE_HSTS_PRELOAD', False)
        )

CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',')
    if o.strip()
]

# ─── Email ───────────────────────────────────────────────────────────────────
# SMTP par défaut en local et en prod (OTP, etc.). Sans serveur mail, définissez
# EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend dans .env.
EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND',
    'django.core.mail.backends.smtp.EmailBackend',
)
EMAIL_HOST = os.getenv('EMAIL_HOST', 'mladoctors.org')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '465'))
EMAIL_USE_SSL = env_bool('EMAIL_USE_SSL', True)
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', False)
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'assistance@mladoctors.org')
# Mot de passe du compte mail (obligatoire pour l’envoi SMTP hors console)
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

DEFAULT_FROM_EMAIL = os.getenv(
    'DEFAULT_FROM_EMAIL',
    f'MLACare <{EMAIL_HOST_USER}>',
)

# PayGate (mobile money FLOOZ/TMONEY)
PAYGATE_KEY = os.getenv('PAYGATE_KEY')
