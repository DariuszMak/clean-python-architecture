import os
from typing import TypedDict


class RedisConfig(TypedDict):
    host: str
    port: int


class EmailConfig(TypedDict):
    host: str
    port: int
    http_port: int


def get_postgres_uri() -> str:
    host = os.environ.get("DB_HOST", "localhost")
    port = 54321 if host == "localhost" else 5432

    password = os.environ.get("DB_PASSWORD")

    user, db_name = "allocation", "allocation"
    return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"


def get_api_url() -> str:
    host = os.environ.get("API_HOST", "localhost")
    port = 5005 if host == "localhost" else 80
    return f"http://{host}:{port}"


def get_redis_host_and_port() -> RedisConfig:
    host = os.environ.get("REDIS_HOST", "localhost")
    port = 6378 if host == "localhost" else 6379
    return {"host": host, "port": port}


def get_email_host_and_port() -> EmailConfig:
    host = os.environ.get("EMAIL_HOST", "localhost")
    port = 11025 if host == "localhost" else 1025
    http_port = 18025 if host == "localhost" else 8025
    return {"host": host, "port": port, "http_port": http_port}
