"""
Django settings for lucidcontrol project.

Generated by 'django-admin startproject' using Django 1.11.7.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.11/ref/settings/
"""

import os
import logging
import dj_database_url

from kombu import Exchange, Queue

# heroku check
IS_HEROKU = os.path.isdir("/app/.heroku")

# local env hack
if not IS_HEROKU and not os.environ.get("DATABASE_URL"):
    import re
    import os

    with open('../.env','r') as fp:
        document = fp.read()

        # regex search for key and values in the .env file and assign to variables
        d = re.findall(r'(?P<key>[\w\d_]+)=\"(?P<value>[^\"]*)\"\n?', document)

        # write the key and value pairs to the os environment
        for (key, value) in d:
            os.environ[key] = value

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'p$t$je+)lah9bwozfj(w%n(6z!%vm*5mj0cj3wxk(foe4-p#&u'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*"]


# Application definition

INSTALLED_APPS = [
    'material.theme.bluegrey',
    'material',
    'material.frontend',
    'material.admin',
    'rest_framework',
    'lucid_api.apps.LucidApiConfig',
    'checkin.apps.CheckinConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_celery_beat',
    'import_export',
    'constance',
    'constance.backends.database',
]

MIDDLEWARE = [
    # Simplified static file serving.
    # https://warehouse.python.org/project/whitenoise/
    'whitenoise.middleware.WhiteNoiseMiddleware',
    # Django Stock
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'lucidcontrol.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'lucidcontrol.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

if "LIVE_DATABASE_URL" in os.environ.keys():
    key = "LIVE_DATABASE_URL"
else:
    key = "DATABASE_URL"

db_from_env = dj_database_url.config(env=key, conn_max_age=500)

DATABASES = {
    'default': db_from_env
}

# Import-Export settings
IMPORT_EXPORT_USE_TRANSACTIONS = True

# Constance for live settings
CONSTANCE_BACKEND = 'constance.backends.database.DatabaseBackend'

CONSTANCE_CONFIG = {
    'THE_ANSWER': (42, 'Answer to the Ultimate Question of Life, '
                       'The Universe, and Everything'),
}

# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/Los_Angeles'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

# Extra places for collectstatic to find static files.
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)

# Simplified static file serving.
# https://warehouse.python.org/project/whitenoise/

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

###################
# Celery Settings
###################

CELERY_BROKER_URL = os.environ.get('CLOUDAMQP_URL' )
BROKER_URL = CELERY_BROKER_URL

# We don't want to have dead connections stored on rabbitmq, so we have to negotiate using heartbeats
BROKER_HEARTBEAT = '?heartbeat=30'  
if not BROKER_URL.endswith(BROKER_HEARTBEAT):  
    BROKER_URL += BROKER_HEARTBEAT

BROKER_POOL_LIMIT = 1  
BROKER_CONNECTION_TIMEOUT = 10

# Celery configuration

# configure queues, currently we have only one
CELERY_DEFAULT_QUEUE = 'default'  
CELERY_QUEUES = (  
    Queue('default', Exchange('default'), routing_key='default'),
)

# Sensible settings for celery
CELERY_ALWAYS_EAGER = False  
CELERY_ACKS_LATE = True  
CELERY_TASK_PUBLISH_RETRY = True  
CELERY_DISABLE_RATE_LIMITS = False

# By default we will ignore result
# If you want to see results and try out tasks interactively, change it to False
# Or change this setting on tasks level
CELERY_IGNORE_RESULT = True  
CELERY_SEND_TASK_ERROR_EMAILS = False  
CELERY_TASK_RESULT_EXPIRES = 600

# Set redis as celery result backend
# CELERY_RESULT_BACKEND = 'redis://%s:%d/%d' % (REDIS_HOST, REDIS_PORT, REDIS_DB)  
# CELERY_REDIS_MAX_CONNECTIONS = 1

CELERYD_HIJACK_ROOT_LOGGER = False  
CELERYD_PREFETCH_MULTIPLIER = 1  
CELERYD_MAX_TASKS_PER_CHILD = 1000  

CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True
CELERYBEAT_SCHEDULER = 'django_celery_beat.schedulers.DatabaseScheduler'

# logging

LOG_LEVEL = str(os.environ.get('LOG_LEVEL',"info"))

if LOG_LEVEL:
    if LOG_LEVEL.lower()[0] == 'w': LOG_LEVEL_TYPE = logging.WARN
    if LOG_LEVEL.lower()[0] == 'e': LOG_LEVEL_TYPE = logging.ERROR
    if LOG_LEVEL.lower()[0] == 'i': LOG_LEVEL_TYPE = logging.INFO
    if LOG_LEVEL.lower()[0] == 'd': LOG_LEVEL_TYPE = logging.DEBUG
    if LOG_LEVEL.lower()[0] == 'c': LOG_LEVEL_TYPE = logging.CRITICAL

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers':{
        'console':{
            'class': 'logging.StreamHandler'
        },
    },
    'loggers': {
        'lucid_api': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'checkin': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'lucidcontrol': {
            'handlers': ['console'],
            'level': 'DEBUG',
        }
    }
}