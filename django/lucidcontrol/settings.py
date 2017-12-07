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


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'p$t$je+)lah9bwozfj(w%n(6z!%vm*5mj0cj3wxk(foe4-p#&u'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*"]

# heroku check
IS_HEROKU = os.path.isdir("/app/.heroku")


# Application definition

INSTALLED_APPS = [
    'material',
    'material.frontend',
    'material.admin',
    'rest_framework',
    'lucid_api.apps.LucidApiConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
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
        'DIRS': [],
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

db_from_env = dj_database_url.config(conn_max_age=500, default="sqlite:///db.sqlite3")

DATABASES = {
    'default': db_from_env
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

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_URL = '/static/'



# local env hack
if not IS_HEROKU:
    import re
    import os

    with open('../.env','r') as fp:
        document = fp.read()

        # regex search for key and values in the .env file and assign to variables
        d = re.findall(r'(?P<key>[\w\d_]+)=\"(?P<value>[^\"]*)\"\n?', document)

        # write the key and value pairs to the os environment
        for (key, value) in d:
            os.environ[key] = value

# Celery Settings
CELERY_BROKER_URL = os.environ.get('CLOUDAMQP_URL' )
BROKER_URL = CELERY_BROKER_URL
# from CELERY + DJANGO in DOCKER tutorial, not necessary

# RABBIT_HOSTNAME = os.environ.get('RABBIT_PORT_5672_TCP', 'rabbit')

# if RABBIT_HOSTNAME.startswith('tcp://'):  
#     RABBIT_HOSTNAME = RABBIT_HOSTNAME.split('//')[1]

# BROKER_URL = os.environ.get('BROKER_URL',  
#                             '')
# if not BROKER_URL:  
#     BROKER_URL = 'amqp://{user}:{password}@{hostname}/{vhost}/'.format(
#         user=os.environ.get('RABBIT_ENV_USER', 'admin'),
#         password=os.environ.get('RABBIT_ENV_RABBITMQ_PASS', 'mypass'),
#         hostname=RABBIT_HOSTNAME,
#         vhost=os.environ.get('RABBIT_ENV_VHOST', ''))

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

# Don't use pickle as serializer, json is much safer
CELERY_TASK_SERIALIZER = "json"  
CELERY_ACCEPT_CONTENT = ['application/json']

CELERYD_HIJACK_ROOT_LOGGER = False  
CELERYD_PREFETCH_MULTIPLIER = 1  
CELERYD_MAX_TASKS_PER_CHILD = 1000  

CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

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
        }
    }
}