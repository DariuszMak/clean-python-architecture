FROM python:3.14-alpine

ENV PYTHONPATH=src

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

RUN apk add --no-cache --virtual .build-deps gcc postgresql-dev musl-dev python3-dev
RUN apk add --no-cache libpq

COPY pyproject.toml uv.lock* /tmp/project/

WORKDIR /tmp/project

RUN uv pip install --system --group dev -e .

RUN apk del --no-cache .build-deps

WORKDIR /src

COPY src/ /src/
COPY tests/ /tests/