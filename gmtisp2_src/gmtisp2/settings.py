"""
Django settings for gmtisp2 project.
"""
import os
import sys
import environ
from pathlib import Path
from celery.schedules import crontab
from datetime import timedelta

# Initialize environment variables
env = environ.Env()
env.read_env()  # Load .env file

# Base directory
BASE_DIR = Path(__file__).resolve().parent
APPS_DIR = BASE_DIR / 'appshere'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool('DEBUG', default=True)

SECRET_KEY = env.str('SECRET_KEY', default='qxzmw^f)nl+lv#@lytar9sahcq73vu=(4dan+1u1n1_s3qv%33')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['127.0.0.1', 'localhost'])

# Detect testing and shell commands
TESTING = 'test' in sys.argv
PARALLEL = '--parallel' in sys.argv
SHELL = 'shell' in sys.argv or 'shell_plus' in sys.argv

# Application definition
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'openwisp_users.accounts',
    'django_extensions',

    # all-auth
    'allauth',
    'allauth.account',  
    'allauth.socialaccount',
    'allauth.socialaccount.providers.facebook',
    'allauth.socialaccount.providers.google',

    'openwisp_users',
    'openwisp_utils',
    'openwisp_utils.admin_theme',
    'rest_framework',
    'rest_framework.authtoken',
    'django.contrib.admin',
    'admin_auto_filters',
    'django.contrib.sites',
    'drf_yasg',
    'reversion',
    'django_filters',

    'widget_tweaks',
    'django_recaptcha',

]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'openwisp_users.middleware.PasswordExpirationMiddleware',
]

AUTH_USER_MODEL = 'openwisp_users.User'
SITE_ID = 1

LOGIN_URL = 'account_login'
LOGIN_REDIRECT_URL = '/dashboard/'

ROOT_URLCONF = 'gmtisp2.urls'

# Templates configuration
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR.parent / 'templates'],
        # 'APP_DIRS': True,
        'OPTIONS': {
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'openwisp_utils.loaders.DependencyLoader',
                'django.template.loaders.app_directories.Loader',
            ],
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'openwisp_utils.admin_theme.context_processor.menu_groups',
            ],
        },
    }
]

AUTHENTICATION_BACKENDS = [
    'openwisp_users.backends.UsersAuthenticationBackend',
]

WSGI_APPLICATION = 'gmtisp2.wsgi.application'

# Database config
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# try:
#     from .db import *
# except ImportError:
#     raise

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'openwisp_users.password_validation.PasswordReuseValidator'},
]

# Internationalization settings
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static and media files settings
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR.parent / 'media'
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR.parent / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR.parent / 'static']

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST')
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
EMAIL_PORT = env('EMAIL_PORT')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_SUBJECT_PREFIX = env('EMAIL_SUBJECT_PREFIX', default='[GMTISP2] ')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')
NOTIFY_EMAIL = env('NOTIFY_EMAIL')
EMAIL_TIMEOUT = 5

ADMINS = [('Kwame Amissah', 'selftestproject@gmail.com')]
MANAGERS = ADMINS

# Social accounts configuration
SOCIALACCOUNT_PROVIDERS = {
    'facebook': {
        'METHOD': 'oauth2',
        'SCOPE': ['email', 'public_profile'],
        'AUTH_PARAMS': {'auth_type': 'reauthenticate'},
        'INIT_PARAMS': {'cookie': True},
        'FIELDS': ['id', 'email', 'name', 'first_name', 'last_name', 'verified'],
        'VERIFIED_EMAIL': True,
    },
    'google': {'SCOPE': ['profile', 'email'], 'AUTH_PARAMS': {'access_type': 'online'}},
}

ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL = 'email_confirmation_success'
ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL = 'email_confirmation_success'

# Logging configuration
LOG_LEVEL = env('LOG_LEVEL', default='ERROR')
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'django.server': {
            '()': 'django.utils.log.ServerFormatter',
            'format': '[{server_time}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': LOG_LEVEL,
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR.parent / 'django_errors.log',
            'maxBytes': 1024 * 1024 * 5,
            'backupCount': 3,
            'delay': True,
            'formatter': 'verbose',
        },
        'console': {
            'level': LOG_LEVEL,
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'django.server': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'django.server',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': [],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# Caching configuration
if not PARALLEL:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': 'redis://localhost/1',
            'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient', 'TIMEOUT': 5},
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'openwisp-users',
        }
    }

# Celery configuration
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://127.0.0.1:6379/2')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://127.0.0.1:6379/2')

CELERY_TASK_DEFAULT_RETRY_DELAY = 30
CELERY_TASK_MAX_RETRIES = 3
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_TIMEZONE = 'Africa/Accra'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

CELERYD_LOG_LEVEL = 'DEBUG'
CELERYD_LOG_FILE = '/etc/systemd/system/gmtisp2_celery.log'
CELERYD_CONCURRENCY = 4
CELERYD_PREFETCH_MULTIPLIER = 1

CELERY_BEAT_SCHEDULE = {
    'sync_data_from_mikrotik_every_30_seconds': {
        'task': 'appshere.billings.tasks.sync_data_from_mikrotik',
        'schedule': timedelta(seconds=30),
    },
    'password_expiry_email': {
        'task': 'openwisp_users.tasks.password_expiration_email',
        'schedule': crontab(hour=1, minute=0),
    },
}

# External services
ROUTER_IP = env('ROUTER_IP')
ROUTER_USERNAME = env('ROUTER_USERNAME')
ROUTER_PASSWORD = env('ROUTER_PASSWORD')

PAYSTACK_SECRET_KEY = env('PAYSTACK_SECRET_KEY')
PAYSTACK_PUBLIC_KEY = env('PAYSTACK_PUBLIC_KEY')
PAYSTACK_CALLBACK_URL = env('PAYSTACK_CALLBACK_URL', default='http://127.0.0.1/payment/verify/')

RECAPTCHA_PUBLIC_KEY = env('RECAPTCHA_SITE_KEY')
RECAPTCHA_PRIVATE_KEY = env('RECAPTCHA_SECRET_KEY')


# debug_toolbar
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE.append('debug_toolbar.middleware.DebugToolbarMiddleware')

    def show_toolbar(request):
        return True

    DEBUG_TOOLBAR_CONFIG = {
        'DISABLE_PANELS': ['debug_toolbar.panels.redirects.RedirectsPanel'], 
        'SHOW_TEMPLATE_CONTEXT': True,
        'INTERCEPT_REDIRECTS': False,
        'SHOW_TOOLBAR_CALLBACK': show_toolbar
    }




# ------------------------------------------------------------------ production
if not DEBUG:
    # Load secret key and sensitive data from environment variables
    SECRET_KEY = env.str('SECRET_KEY_LIVE')
    PAYPAL_CLIENT_ID = env('PAYPAL_LIVE_CLIENT_ID')
    PAYPAL_SECRET_KEY = env('PAYPAL_LIVE_SECRET_KEY')

    # Restrict allowed hosts
    ALLOWED_HOSTS = env.list('ALLOWED_HOSTS_LIVE', default=['192.168.137.4'])

    # # Enforce SSL/TLS settings (Commented out if SSL is not used)
    # SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    # SECURE_SSL_REDIRECT = True
    # SESSION_COOKIE_SECURE = True  # Secure cookies over HTTPS
    # SESSION_EXPIRE_AT_BROWSER_CLOSE = True
    # CSRF_COOKIE_SECURE = True  # Secure CSRF cookie

    # # HTTP Strict Transport Security (HSTS) (Commented out if SSL is not used)
    # SECURE_HSTS_SECONDS = 31536000  # 1 year
    # SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    # SECURE_HSTS_PRELOAD = True

    # Content security policies
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True

    # Frame Denial
    SECURE_FRAME_DENY = True

    # CORS settings (optional, only needed for CORS with HTTPS)
    # CORS_REPLACE_HTTPS_REFERER = True
