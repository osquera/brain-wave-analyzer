# Backend Dockerfile
FROM python:3.12.11-alpine

WORKDIR /app

# Set environment variables
ENV PRODUCTION_MODE=1

# Install system dependencies
RUN apk add --no-cache \
    libstdc++ \
    gcc \
    musl-dev \
    && rm -rf /var/cache/apk/*

# Copy requirements and install dependencies
COPY requirements-backend.txt .
RUN pip install --no-cache-dir -r requirements-backend.txt

COPY src/backend.py .

# Create directories for static files
RUN mkdir -p static/figures

# Expose API port
EXPOSE 8000

# Run the API
CMD ["python", "backend.py"]
