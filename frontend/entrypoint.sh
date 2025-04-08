#!/bin/sh

set -e

echo "Migrations starten..."
python manage.py migrate

echo ""

echo "Superuser anlegen..."
python create_superuser.py

echo ""

echo "Django starten..."
python manage.py runserver 0.0.0.0:8000
