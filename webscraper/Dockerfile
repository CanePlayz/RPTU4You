FROM python:3.13-slim

RUN apt-get update && apt-get install -y cron

WORKDIR /webscraper

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .
