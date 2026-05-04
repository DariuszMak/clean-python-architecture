FROM python:3.14-alpine

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

RUN apk add --no-cache --virtual .build-deps gcc postgresql-dev musl-dev python3-dev
RUN apk add libpq

COPY pyproject.toml uv.lock* /src/
COPY src/ /src/

WORKDIR /src
RUN uv sync --no-install-project --group dev

RUN apk del --no-cache .build-deps

RUN uv pip install -e .

COPY tests/ /tests/
