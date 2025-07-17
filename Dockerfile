# Start from an official Python base image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy your requirements file first
COPY requirements.txt .

# Install your Python packages (add gunicorn here)
RUN pip install --no-cache-dir -r requirements.txt

# Install system dependencies, including libreoffice
RUN apt-get update && \
    apt-get install -y libreoffice --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Copy the rest of your application code
COPY . .

# Tell Render what command to run when the app starts
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "app:app"]
