FROM seleniarm/standalone-chromium:latest

# Switch to root to install Python
USER root

# Install Python and pip
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Create symlink for python command
RUN ln -s /usr/bin/python3 /usr/bin/python

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# ChromeDriver is already installed in the base image at /usr/bin/chromedriver
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Start the application
CMD ["python", "main.py"]