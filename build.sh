#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status.
set -e

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Create any new migrations
python manage.py makemigrations

# Apply database migrations
python manage.py migrate

# Create default groups
python manage.py create_groups

# Create superuser if environment variables are set
python manage.py create_superuser