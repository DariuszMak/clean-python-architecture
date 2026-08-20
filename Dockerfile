FROM python:3.14-alpine

ENV PYTHONPATH=.

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

RUN apk add --no-cache --virtual .build-deps gcc postgresql-dev musl-dev python3-dev
RUN apk add --no-cache libpq

WORKDIR /app

COPY pyproject.toml uv.lock* ./
COPY src/ ./src/
COPY tests/ ./tests/

RUN uv pip install --system --group dev -e .

RUN apk del --no-cache .build-deps