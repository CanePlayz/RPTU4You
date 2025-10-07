FROM node:24-alpine AS tailwind-build
WORKDIR /app

# Kopiere package.json und installiere Abhängigkeiten
COPY frontend/tailwind/package*.json ./tailwind/
RUN cd tailwind \
    && npm install

# Kopiere die Frontend-Dateien als Tailwind-Input und baue die CSS-Datei
COPY frontend/tailwind ./tailwind
COPY frontend/templates ./templates
RUN mkdir -p static/css \
    && cd tailwind \
    && npm run build:css

FROM python:3.13-slim
WORKDIR /app

# Installiere Python-Pakete
COPY frontend/requirements.txt ./
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Kopiere den Frontend-Code
COPY frontend /app

# Kopiere die gebaute Tailwind CSS-Datei aus dem vorherigen Build-Stadium
COPY --from=tailwind-build /app/static/css/tailwind-built.css ./static/css/tailwind-built.css

# Erstelle einen unprivilegierten Benutzer für Celery
RUN useradd -m -u 1001 celeryuser
RUN chown -R celeryuser:celeryuser /app

EXPOSE 8000
