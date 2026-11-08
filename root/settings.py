import os
from pathlib import Path

from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in {'1', 'true', 'yes', 'on'}


def env_list(name, default=''):
    return [item.strip() for item in os.environ.get(name, default).split(',') if item.strip()]


_INSECURE_DEV_KEY = 'django-insecure-change-me-in-.env'
SECRET_KEY = os.environ.get('SECRET_KEY', _INSECURE_DEV_KEY)

# Standart holda yopiq: .env da DEBUG unutilsa, debug sahifalari ochilib qolmaydi.
DEBUG = env_bool('DEBUG')

if not DEBUG and SECRET_KEY == _INSECURE_DEV_KEY:
    raise ImproperlyConfigured(
        "DEBUG=False, lekin SECRET_KEY berilmagan - hammaga ma'lum kalit bilan production "
        "ishga tushirilmaydi (sessiyalarni soxtalashtirish mumkin bo'lardi)."
    )

ALLOWED_HOSTS = env_list('ALLOWED_HOSTS', 'localhost,127.0.0.1')
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS')

LOGIN_URL = 'home'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.sitemaps',
    'django.contrib.staticfiles',
    'apps',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'root.urls'

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

WSGI_APPLICATION = 'root.wsgi.application'
AUTH_USER_MODEL = 'apps.User'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'zuno'),
        'USER': os.environ.get('DB_USER', 'zuno'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', '127.0.0.1'),
        'PORT': os.environ.get('DB_PORT', '5434'),
        'CONN_MAX_AGE': 60,
        'CONN_HEALTH_CHECKS': True,
    }
}

# Limitlar barcha gunicorn workerlari uchun umumiy bo'lishi uchun productionda Redis kerak
REDIS_URL = os.environ.get('REDIS_URL', '')
CACHES = {
    'default': (
        {'BACKEND': 'django.core.cache.backends.redis.RedisCache', 'LOCATION': REDIS_URL}
        if REDIS_URL else
        {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'zuno'}
    )
}

# Faqat ishonchli reverse-proxy ortida yoqing, aks holda IP'ni soxtalashtirish mumkin
TRUST_X_FORWARDED_FOR = env_bool('TRUST_X_FORWARDED_FOR')

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'uz'
LANGUAGES = [('uz', "O'zbekcha")]
TIME_ZONE = 'Asia/Tashkent'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'static'
STATIC_ROOT.mkdir(exist_ok=True)  # WhiteNoise papka bo'lmasa ogohlantiradi
STATICFILES_DIRS = [('apps', BASE_DIR / 'apps' / 'apps')]
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        'BACKEND': (
            'django.contrib.staticfiles.storage.StaticFilesStorage' if DEBUG
            else 'whitenoise.storage.CompressedStaticFilesStorage'
        ),
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
SERVE_MEDIA = env_bool('SERVE_MEDIA', DEBUG)

MESSAGE_TAGS = {
    messages.ERROR: 'danger',
}

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'

if env_bool('HTTPS_ONLY'):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

LOG_DIR = BASE_DIR / 'logs'
LOG_HANDLERS = {'console': {'class': 'logging.StreamHandler', 'formatter': 'plain'}}
if env_bool('LOG_TO_FILE'):
    LOG_DIR.mkdir(exist_ok=True)
    LOG_HANDLERS['file'] = {
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': LOG_DIR / 'zuno.log',
        'maxBytes': 5 * 1024 * 1024,
        'backupCount': 3,
        'formatter': 'plain',
    }

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {'plain': {'format': '{asctime} {levelname} {name}: {message}', 'style': '{'}},
    'handlers': LOG_HANDLERS,
    'root': {'handlers': list(LOG_HANDLERS), 'level': 'INFO'},
}
