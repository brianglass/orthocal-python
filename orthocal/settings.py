"""
Django settings for orthocal project.

Generated by 'django-admin startproject' using Django 4.1.4.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.1/ref/settings/
"""

import os
import zoneinfo

from pathlib import Path

from django.utils.translation import gettext_lazy as _

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
# We probably don't actually use this in this particular project, but it
# never hurts to be prepared.
SECRET_KEY = os.environ.get('SECRET_KEY', 'Twas Brillig and the Slithy Toves')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['*']

# This is because we're sitting behind the Firebase proxy. If this is not run
# behind a proxy, these should be disabled.
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True
SECURE_PROXY_SSL_HEADER = 'HTTP_X_FORWARDED_PROTO', 'https'

# Application definition

INSTALLED_APPS = [
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',

    # Third party apps
    'corsheaders',
    'fullurl',
    'typogrify',
    'ninja',

    # internal apps
    'orthocal',
    'bible',
    'calendarium',
    'alexa',
    'commemorations',
]

MIDDLEWARE = [
    'django.middleware.gzip.GZipMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'orthocal.middleware.cache_control',
]

ROOT_URLCONF = 'orthocal.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'orthocal.context_processors.globals',
            ],
        },
    },
]

WSGI_APPLICATION = 'orthocal.wsgi.application'

FIXTURE_DIRS = [BASE_DIR / 'fixtures']

# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'TEST': {
            # The default is to use an in-memory DB for tests. We give the test
            # DB an explicit name so that a file is created. This is so tha twe
            # can use the --keepdb option during test runs to avoid having the
            # scriptures ingested each time we run tests.
            'NAME': BASE_DIR / 'test_db.sqlite3',
        }
    }
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console'],
            'propagate': True,
        },
        'alexa': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'DEBUG',
        },
        'bible': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'DEBUG',
        },
        'calendarium': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'DEBUG',
        },
        'orthocal': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'DEBUG',
        },
    },
}

# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGES = (
    ('en', _('English')),
    ('ro', _('Romanian')),
)
LANGUAGE_CODE = 'en-us'

TIME_ZONE = os.environ.get('TZ', 'America/Los_Angeles')

USE_I18N = True
USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_URL = 'media/'
STATIC_ROOT = BASE_DIR / 'static'

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CORS_ALLOW_ALL_ORIGINS = True

NINJA_DOCS_VIEW = 'redoc'

ORTHOCAL_ICAL_TZ = zoneinfo.ZoneInfo(TIME_ZONE)
ORTHOCAL_ICAL_TTL = 12  # hours
ORTHOCAL_PUBLIC_URL = os.environ.get('BASE_URL', 'https://orthocal.info')
ORTHOCAL_MAX_AGE = 60 * 60
ORTHOCAL_LANGUAGES = 'en', 'ro'

try:
    from .local_settings import *
except ImportError:
    pass
