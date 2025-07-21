FROM python:3.13-slim

WORKDIR /app

COPY frontend/requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY frontend /app

# Erstelle einen unprivilegierten Benutzer für Celery
RUN useradd -m -u 1001 celeryuser
RUN chown -R celeryuser:celeryuser /app

EXPOSE 8000
