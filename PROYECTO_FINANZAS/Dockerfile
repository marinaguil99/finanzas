# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Asegura que notified.json existe (si no se monta)
RUN touch notified.json

ENTRYPOINT ["python3", "scripts/check_buybacks_finnhub.py"]
