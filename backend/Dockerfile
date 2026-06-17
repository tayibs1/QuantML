# QuantML API — FastAPI on uvicorn.
#
# Build context is the repo root (see docker-compose.yml), so the image can carry
# the ml/ package the API imports lazily plus the JSON artifacts it serves from
# data/. The heavy parquet (data/raw, data/processed) is excluded via .dockerignore.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app
WORKDIR /app/backend

# install deps first so they cache across code changes
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# api code + the lazily-imported ml package + shipped artifacts
COPY backend/ /app/backend/
COPY ml/ /app/ml/
COPY data/ /app/data/

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
