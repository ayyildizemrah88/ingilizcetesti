web: gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 4 --threads 2 --timeout 120 run:app
worker: celery -A celery_config worker --loglevel=info --concurrency=4
beat: celery -A celery_config beat --loglevel=info
