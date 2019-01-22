#!/bin/sh

# wait for RabbitMQ server to start
sleep 10

#  switch to the django directory
cd /app/django  
# run Celery worker for our project myproject with Celery configuration stored in Celeryconf
# su -m myuser -c "celery worker -A myproject.celeryconf -Q default -n default@%h"
su -m myuser -c "celery -A lucidcontrol beat -l debug --scheduler=django_celery_beat.schedulers:DatabaseScheduler -without-gossip --without-mingle --without-heartbeat"