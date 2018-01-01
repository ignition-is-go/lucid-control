#!/bin/sh

# wait for PSQL server to start
sleep 10

cd /app/django  
# prepare init migration
su -m myuser -c "python manage.py makemigrations"  
# migrate db, so we have the latest db schema
su -m myuser -c "python manage.py migrate"  

su -m myuser -c "waitress-serve --port=$PORT lucidcontrol.wsgi:application"