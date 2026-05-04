FROM python:3.14-alpine

RUN apk add --no-cache --virtual .build-deps gcc postgresql-dev musl-dev python3-dev
RUN apk add libpq
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_PROJECT_ENVIRONMENT=/opt/venv

RUN mkdir -p /src
COPY src/ /src/
COPY tests/ /tests/
COPY pyproject.toml /src/

WORKDIR /src
RUN uv sync --dev
RUN uv pip install -e /src --system

RUN apk del --no-cache .build-deps