# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install the required dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Chromium and the Chrome WebDriver for Selenium
RUN apt-get update && apt-get install -y chromium-driver

# Set environment variables for headless Chrome
ENV SELENIUM_HEADLESS=true
ENV SELENIUM_DRIVER=chrome
ENV SELENIUM_DRIVER_PATH=/usr/bin/chromedriver

# Expose the port the app runs on
EXPOSE 5000

# Run the application
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
