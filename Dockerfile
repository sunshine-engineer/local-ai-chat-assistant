# syntax=docker/dockerfile:1
# File: Dockerfile
# Purpose: Build the Python application image with runtime dependencies and packaged defaults.
# Maintainer: sunshine-engineer
# Modified: 2026-10-23
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --timeout=120 --retries=5 -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
