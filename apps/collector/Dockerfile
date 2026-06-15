FROM python:3.12-slim

WORKDIR /app

COPY apps/collector/pyproject.toml apps/collector/src ./apps/collector/
COPY infra/sqlite/schema.sql ./infra/sqlite/schema.sql

RUN pip install --no-cache-dir ./apps/collector

ENV AFR_DATABASE_PATH=/data/afr.db
ENV AFR_HOST=0.0.0.0
ENV AFR_PORT=4318

EXPOSE 4318

CMD ["afr-collector"]