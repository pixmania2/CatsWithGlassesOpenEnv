# Dockerfile — PTPA OpenEnv Environment
# Build:  docker build -t ptpa-env .
# Run:    docker run -p 8000:8000 -e OPENAI_API_KEY=$OPENAI_API_KEY ptpa-env

FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (layer caching)
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy source
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Start server
CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
