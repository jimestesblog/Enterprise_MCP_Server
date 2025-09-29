# syntax=docker/dockerfile:1.7
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOST=0.0.0.0 \
    HEALTH_PORT=8080 \
    CONFIG_PATH=/app/config/tools.yaml

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY mcp_server ./mcp_server
COPY config ./config
COPY README.md ./

EXPOSE 8080

CMD ["python", "-m", "mcp_server"]
