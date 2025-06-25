#!/bin/sh

set -e

echo "Migrations starten..."
python manage.py migrate

echo ""

echo "Superuser anlegen..."
python create_superuser.py

echo ""

echo "Webserver starten (Gunicorn)..."
exec gunicorn rptu4you.wsgi:application --bind 0.0.0.0:8000 --workers 3
