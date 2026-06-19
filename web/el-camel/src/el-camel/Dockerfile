FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app.py .
COPY templates/ templates/
COPY docs/ docs/
COPY static/ static/

# Expose port
EXPOSE 80

# Run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:80", "--access-logfile", "-", "--error-logfile", "-", "--timeout", "30", "app:app"]
