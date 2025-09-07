# Frontend Dockerfile
FROM python:3.12.11-alpine

WORKDIR /app

# Install dependencies
COPY requirements-frontend.txt .
# Install system dependencies
RUN apk add --no-cache \
    libstdc++ \
    gcc \
    musl-dev \
    && rm -rf /var/cache/apk/*

RUN pip install --no-cache-dir -r requirements-frontend.txt

# Copy the streamlit app
COPY src/frontend.py .

# Expose Streamlit port
EXPOSE 8501

# Run Streamlit
CMD ["streamlit", "run", "frontend.py", "--server.port=8501", "--server.address=0.0.0.0"]
