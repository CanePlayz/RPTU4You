# ---- Tailwind CSS ----
#FROM node:20-alpine AS tailwind-build
#WORKDIR /app
#COPY frontend/tailwind/package.json frontend/tailwind/package-lock.json ./tailwind/
#RUN cd tailwind && npm install
#COPY frontend/tailwind/ ./tailwind/
#COPY frontend/static/css/ ./static/css/
#RUN cd tailwind && npm run build:css

FROM python:3.11-slim
WORKDIR /app
COPY frontend /app
#COPY --from=tailwind-build /app/static/css/tailwind-built.css ./static/css/tailwind-built.css

COPY frontend/requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Erstelle einen unprivilegierten Benutzer für Celery
RUN useradd -m -u 1001 celeryuser
RUN chown -R celeryuser:celeryuser /app

EXPOSE 8000
