FROM python:3.13-slim

# Installiere notwendige Pakete
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    gnupg \
    && apt-get clean

# Füge den Google Chrome-Signing-Key und das Repository hinzu
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor > /etc/apt/trusted.gpg.d/google.gpg && \
    sh -c "echo 'deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main' > /etc/apt/sources.list.d/google-chrome.list"

# Installiere Google Chrome
RUN apt-get update && apt-get install -y google-chrome-stable

# Installiere den passenden Chrome WebDriver
RUN wget -q "https://storage.googleapis.com/chrome-for-testing-public/136.0.7091.0/linux64/chromedriver-linux64.zip" && \
    unzip chromedriver-linux64.zip -d /usr/local/bin/ && \
    rm chromedriver-linux64.zip

WORKDIR /webscraper

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .
