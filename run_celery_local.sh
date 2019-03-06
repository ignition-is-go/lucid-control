#!/bin/sh

# wait for RabbitMQ server to start
# sleep 10

#  switch to the django directory
cd ./django  
# run Celery worker for our project myproject with Celery configuration stored in Celeryconf
# su -m myuser -c "celery worker -A myproject.celeryconf -Q default -n default@%h"
celery -A lucidcontrol worker -l debug --without-gossip --without-mingle --without-heartbeat