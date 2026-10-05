# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

# Системні залежності для psycopg (бінарний пакет уже вшитий, тому лише мінімум)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

# Простий healthcheck: чи відповідає корінь API
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
    CMD curl -f http://localhost:8000/ || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
