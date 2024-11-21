FROM python:3.13-slim

WORKDIR /webscraper

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY webscraper.py .

RUN apt-get update && apt-get install -y cron

COPY cronjob /etc/cron.d/scraper-cron

RUN chmod 0644 /etc/cron.d/scraper-cron && \
    crontab /etc/cron.d/scraper-cron
RUN touch /var/log/cron.log

CMD ["sh", "-c", "cron && tail -f /var/log/cron.log"]
