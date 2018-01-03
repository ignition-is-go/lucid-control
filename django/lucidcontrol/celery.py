from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lucidcontrol.settings')

from django.conf import settings  # noqa

import logging
logger = logging.getLogger(__name__)

app = Celery('lucidcontrol')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings') #, namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    logger.info("Doing periodic tasks!")



@app.task
def test(text):
    logger.info("TESTED! %s", text)
    print("TESTED PRINT ", text)

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))