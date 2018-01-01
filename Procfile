web: cd django & web: waitress-serve --port=$PORT lucidcontrol.wsgi:application
worker: cd django & celery worker -A lucidcontrol worker --beat -l info 