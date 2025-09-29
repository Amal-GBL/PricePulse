# Use Ubuntu 22.04 base
FROM ubuntu:22.04

# Install system dependencies for Playwright / browsers
RUN apt-get update && apt-get install -y \
    python3.11 python3-pip curl wget git \
    libnss3 libatk-bridge2.0-0 libxss1 libgtk-3-0 \
    libgbm-dev libasound2 libpangocairo-1.0-0 \
    fonts-liberation xvfb && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install Python dependencies
RUN python3 -m pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install playwright
RUN playwright install chromium

# Set display for any headful browser usage
ENV DISPLAY=:99

# Default command: run all scrapers
CMD ["python3", "run_all_scrapers.py"]
