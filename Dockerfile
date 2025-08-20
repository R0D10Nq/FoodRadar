# Базовый образ с системными либами для GeoDjango
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_NO_CACHE_DIR=off

# Системные зависимости для PostGIS/GDAL + psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gdal-bin \
    libgdal-dev \
    libproj-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

# Устанавливаем питон-зависимости
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt

# Код монтируется volume-ом из хоста, поэтому тут ничего не копируем

EXPOSE 8000
