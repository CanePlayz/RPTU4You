FROM python:3.13-slim

# Installiere notwendige Pakete
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    gnupg \
    fonts-liberation \
    libxss1 \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libnspr4 \
    libnss3 \
    libu2f-udev \
    libgbm1 \
    xdg-utils \
    && apt-get clean

# Chrome installieren
RUN wget -q "https://storage.googleapis.com/chrome-for-testing-public/134.0.6998.35/linux64/chrome-linux64.zip" && \
    unzip chrome-linux64.zip && \
    mv chrome-linux64 /opt/chrome && \
    ln -s /opt/chrome/chrome /usr/bin/google-chrome && \
    rm chrome-linux64.zip

# Installiere den passenden Chrome WebDriver
RUN wget -q "https://storage.googleapis.com/chrome-for-testing-public/134.0.6998.35/linux64/chromedriver-linux64.zip" && \
    unzip chromedriver-linux64.zip -d /usr/local/bin/ && \
    rm chromedriver-linux64.zip

WORKDIR /webscraper

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .
