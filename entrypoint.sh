#!/bin/bash
set -e

echo "Waiting for database to be ready..."
# Give database a moment to be ready (Render handles this, but good to be safe)
sleep 2

echo "Running database migrations..."
python manage.py migrate --noinput

echo "Starting Gunicorn..."
exec gunicorn --bind 0.0.0.0:8000 --timeout 120 --workers 2 --access-logfile - --error-logfile - university_api.wsgi:application

