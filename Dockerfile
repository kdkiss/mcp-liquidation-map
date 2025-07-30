FROM seleniarm/standalone-chromium:latest

# Switch to root to install Python
USER root

# Install Python and pip
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip in the virtual environment
RUN /opt/venv/bin/pip install --no-cache-dir --upgrade pip

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# ChromeDriver is already installed in the base image at /usr/bin/chromedriver
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Start the application using the virtual environment's Python
CMD ["/opt/venv/bin/python", "main.py"]