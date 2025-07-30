FROM python:3.9-slim

# Set specific versions for Chrome and ChromeDriver
ENV CHROME_VERSION="114.0.5735.90-1"
ENV CHROMEDRIVER_VERSION="114.0.5735.90"
ENV SELENIUM_VERSION="4.10.0"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    unzip \
    xvfb \
    xauth \
    xfonts-100dpi \
    xfonts-75dpi \
    xfonts-scalable \
    xfonts-cyrillic \
    x11-apps \
    openjdk-11-jre-headless \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome for Selenium
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable=${CHROME_VERSION} \
    && rm -rf /var/lib/apt/lists/*

# Install ChromeDriver
RUN wget -q "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip" \
    && unzip chromedriver_linux64.zip \
    && mv chromedriver /usr/local/bin/chromedriver \
    && chmod +x /usr/local/bin/chromedriver \
    && rm chromedriver_linux64.zip

# Install Selenium Grid Server
RUN wget -q "https://github.com/SeleniumHQ/selenium/releases/download/selenium-${SELENIUM_VERSION}/selenium-server-4.10.0.jar" \
    && mv selenium-server-4.10.0.jar /usr/local/bin/selenium-server.jar

# Set up working directory
WORKDIR /app

# Set display port and dbus env to avoid hanging
ENV DISPLAY=:99
ENV DBUS_SESSION_BUS_ADDRESS=/dev/null

# Set Chrome to run in headless mode
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROME_PATH=/usr/lib/chromium-browser/

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create a non-root user and switch to it
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && chown -R appuser:appuser /app
USER appuser

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application with Xvfb and Selenium Grid
CMD Xvfb :99 -screen 0 1024x768x16 & \
    export DISPLAY=:99 && \
    java -jar /usr/local/bin/selenium-server.jar standalone \
        --driver-implementation chrome \
        --driver-executable /usr/local/bin/chromedriver \
        --port 4444 & \
    sleep 10 && \
    uvicorn main:app --host 0.0.0.0 --port 8000