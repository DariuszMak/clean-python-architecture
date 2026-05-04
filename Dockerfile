FROM python:3.14-slim

ENV PYTHONPATH=.

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

RUN apk add --no-cache --virtual .build-deps gcc postgresql-dev musl-dev python3-dev
RUN apk add libpq

COPY pyproject.toml uv.lock* /src/
COPY src/ /src/

WORKDIR /src
RUN uv pip install --system --group dev -e .

RUN apk del --no-cache .build-deps

COPY tests/ /tests/