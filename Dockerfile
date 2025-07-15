# Dockerfile for TestPilot Backend
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r backend/requirements.txt

# Copy backend and shared code
COPY backend/ ./backend/
COPY shared/ ./shared/

# Expose port
EXPOSE 5000

# Set environment variables for production
ENV ENVIRONMENT=production
ENV USE_REDIS=true
ENV REDIS_URL=redis://redis:6379/0

# Start the Flask app
CMD ["python3", "backend/app.py"] 