FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FARI_DATA_DIR=/data

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY webapp ./webapp
COPY tools ./tools
COPY tests ./tests
COPY spec ./spec
COPY sparta/sparta-attack-3.2.json ./sparta/sparta-attack-3.2.json

RUN mkdir -p /data/evidence /data/attack_flows /data/sbom

EXPOSE 8081

CMD ["gunicorn", "--bind", "0.0.0.0:8081", "--workers", "2", "--threads", "4", "--timeout", "120", "webapp.app:app"]
