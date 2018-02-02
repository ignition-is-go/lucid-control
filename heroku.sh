#!/bin/bash
celery worker -A app.celery & 
cd django
gunicorn lucidcontrol.wsgi --log-file=-
