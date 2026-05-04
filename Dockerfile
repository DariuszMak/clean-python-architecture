FROM python:3.14-alpine

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

RUN apk add --no-cache --virtual .build-deps gcc postgresql-dev musl-dev python3-dev
RUN apk add libpq

COPY pyproject.toml uv.lock* /tmp/app/
WORKDIR /tmp/app

RUN uv sync --no-dev

RUN apk del --no-cache .build-deps

RUN mkdir -p /src
COPY src/ /src/
WORKDIR /src
RUN uv pip install --system -e .

COPY tests/ /tests/

WORKDIR /src