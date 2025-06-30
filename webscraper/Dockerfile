FROM python:3.13-slim

# Installiere notwendige Pakete
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    gnupg \
    xz-utils \
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

# Firefox installieren (architekturabhängig)
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then \
    FIREFOX_URL="https://download.mozilla.org/?product=firefox-latest-ssl&os=linux64&lang=de"; \
    elif [ "$ARCH" = "arm64" ]; then \
    FIREFOX_URL="https://download.mozilla.org/?product=firefox-latest-ssl&os=linux64-aarch64&lang=de"; \
    else \
    echo "Nicht unterstützte Architektur: $ARCH" && exit 1; \
    fi && \
    wget -O firefox.tar.xz "$FIREFOX_URL" && \
    tar -xJf firefox.tar.xz && \
    mv firefox /opt/firefox && \
    ln -s /opt/firefox/firefox /usr/bin/firefox && \
    rm firefox.tar.xz

WORKDIR /webscraper

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .
