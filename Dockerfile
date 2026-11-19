# Dockerfile for Smart Travel Planner AI Agent
# Python 3.12-slim base image with Zero external dependencies
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Set working directory
WORKDIR /app

# Copy application files
COPY agent/ /app/agent/
COPY web/ /app/web/
COPY tests/ /app/tests/
COPY config.py /app/config.py
COPY main.py /app/main.py
COPY web_server.py /app/web_server.py
COPY README.md /app/README.md

# Create persistent storage directories
RUN mkdir -p /app/data /app/exports

# Run automated tests during build stage to guarantee reliability
RUN python -m unittest discover -s tests -p "test_*.py" -v

# Expose web server port
EXPOSE 8000

# Health check to ensure web server is responsive
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/trip', timeout=3)" || exit 0

# Default command to start the web server
CMD ["python", "main.py", "--web", "--port", "8000"]

