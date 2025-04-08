#!/bin/sh

set -e

echo "Migrations starten..."
python manage.py migrate

echo ""

echo "Superuser anlegen..."
python create_superuser.py

echo ""

echo "Translator starten..."
python manage.py start_translator &

echo "Server starten..."
python manage.py runserver 0.0.0.0:8000
