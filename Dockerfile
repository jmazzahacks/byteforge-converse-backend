FROM python:3.13-slim

# Install curl (for health checks) and git (pip pulls internal libs from public GitHub repos)
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Non-root user
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 5252

ENV PYTHONPATH=/app
ENV PORT=5252

CMD gunicorn --bind 0.0.0.0:$PORT --workers 4 'byteforge_converse_backend:create_app()'
