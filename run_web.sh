#!/bin/sh

# wait for PSQL server to start
sleep 1

cd /app/django  
# prepare init migration
su -m myuser -c "python manage.py makemigrations lucid_api checkin"  
# migrate db, so we have the latest db schema
su -m myuser -c "python manage.py migrate"  
# start development server on public ip interface, on port 8000
su -m myuser -c "python manage.py runserver 0.0.0.0:8000"
# su -m myuser -c "gunicorn lucidcontrol.wsgi --log-level=-"