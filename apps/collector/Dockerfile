FROM python:3.12-slim

WORKDIR /app

COPY apps/collector/pyproject.toml apps/collector/
COPY apps/collector/src apps/collector/src
COPY infra infra
COPY examples/policies examples/policies
COPY examples/evals examples/evals

RUN pip install --no-cache-dir ./apps/collector

ENV AFR_HOST=0.0.0.0
ENV AFR_PORT=4318

EXPOSE 4318

CMD ["afr-collector"]