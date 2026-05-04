FROM python:3.14-alpine AS builder

RUN apk add --no-cache --virtual .build-deps \
    gcc \
    musl-dev \
    postgresql-dev \
    python3-dev

RUN apk add --no-cache libpq

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

COPY pyproject.toml /app/

RUN uv sync --dev
RUN uv pip install -e .

COPY src/ /app/src/
COPY tests/ /app/tests/

FROM python:3.14-alpine

RUN apk add --no-cache libpq

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

COPY src/ /app/src/
COPY tests/ /app/tests/

