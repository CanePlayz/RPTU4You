FROM node:20-alpine AS tailwind-build
WORKDIR /app

# Install Tailwind dependencies once so layers stay cacheable
COPY frontend/tailwind/package*.json ./tailwind/
RUN cd tailwind \
    && npm install --production=false --no-audit --progress=false

# Build the project CSS artifact using the full frontend source as content input
COPY frontend ./
RUN cd tailwind \
    && npm run build:css

FROM python:3.11-slim
WORKDIR /app

COPY frontend/requirements.txt ./
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Application source
COPY frontend /app

# Use the Tailwind CSS artifact built in the Node stage
COPY --from=tailwind-build /app/static/css/tailwind-built.css ./static/css/tailwind-built.css

# Erstelle einen unprivilegierten Benutzer für Celery
RUN useradd -m -u 1001 celeryuser
RUN chown -R celeryuser:celeryuser /app

EXPOSE 8000
