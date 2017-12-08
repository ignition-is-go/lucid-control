web: cd django & gunicorn lucidcontrol.wsgi --log-file=-
worker: cd django & celery worker -A lucidcontrol worker -l debug 