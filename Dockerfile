# Use the official Playwright Python image
FROM mcr.microsoft.com/playwright/python:v1.50.0-noble

# Set working directory
WORKDIR /app

# Copy project files into the container
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and browsers
RUN pip install playwright && playwright install

# Set timezone
ENV TZ=Asia/Kolkata

# Run scrapers by default
CMD ["python", "-u", "run_all_scrapers.py"]
