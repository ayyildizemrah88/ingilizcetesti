web: gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 4 --threads 2 --timeout 120 run:app
worker: celery -A app.celery_app:celery worker --loglevel=info --concurrency=4
beat: celery -A app.celery_app:celery beat --loglevel=info
