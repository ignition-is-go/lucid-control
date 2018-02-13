#!/bin/sh

# wait for PSQL server to start
sleep 10

cd /app/django  
# prepare init migration
python manage.py makemigrations
# migrate db, so we have the latest db schema
python manage.py migrate

python manage.py collectstatic --noinput

# run waitress
waitress-serve --port=$PORT lucidcontrol.wsgi:application