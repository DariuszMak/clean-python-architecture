import shutil
import subprocess  # noqa: S404
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
import redis
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import clear_mappers, sessionmaker
from tenacity import retry, stop_after_delay, wait_fixed

from allocation import config
from allocation.adapters.orm import metadata
from allocation.adapters.orm import start_mappers as start_mappers_untyped

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from sqlalchemy.engine import Engine

pytest.register_assert_rewrite("tests.e2e.api_client")

get_api_url: Callable[[], str] = config.get_api_url
get_redis_host_and_port: Callable[[], dict[str, Any]] = config.get_redis_host_and_port
get_postgres_uri: Callable[[], str] = config.get_postgres_uri
wait_for_postgres_to_come_up_untyped: Callable[[Engine], Any] = None  # replaced below
wait_for_webapp_to_come_up_untyped: Callable[[], requests.Response] = None  # replaced below
wait_for_redis_to_come_up_untyped: Callable[[], bool] = None  # replaced below

start_mappers_typed: Callable[[], None] = start_mappers_untyped


@pytest.fixture
def in_memory_sqlite_db() -> Engine:
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)
    return engine


@pytest.fixture
def sqlite_session_factory(in_memory_sqlite_db: Engine):
    return sessionmaker(bind=in_memory_sqlite_db)


@pytest.fixture
def mappers() -> Generator[None]:
    start_mappers_typed()
    yield
    clear_mappers()


@retry(stop=stop_after_delay(10))
def wait_for_postgres_to_come_up(engine: Engine) -> Any:
    return engine.connect()


@retry(stop=stop_after_delay(30), wait=wait_fixed(0.5))
def wait_for_webapp_to_come_up() -> requests.Response:
    return requests.get(get_api_url(), timeout=5)


@retry(stop=stop_after_delay(10))
def wait_for_redis_to_come_up() -> bool:
    r = redis.Redis(**get_redis_host_and_port())
    return r.ping()


@pytest.fixture(scope="session")
def postgres_db() -> Engine:
    engine = create_engine(get_postgres_uri(), isolation_level="SERIALIZABLE")
    wait_for_postgres_to_come_up(engine)
    metadata.create_all(engine)
    return engine


@pytest.fixture
def postgres_session_factory(postgres_db: Engine):
    return sessionmaker(bind=postgres_db)


@pytest.fixture
def postgres_session(postgres_session_factory):
    return postgres_session_factory()


@pytest.fixture
def restart_api() -> None:
    (Path(__file__).parent / "../src/allocation/entrypoints/flask_app.py").touch()
    time.sleep(2)
    wait_for_webapp_to_come_up()


@pytest.fixture
def restart_redis_pubsub() -> None:
    wait_for_redis_to_come_up()
    if not shutil.which("docker-compose"):
        return

    docker_path = shutil.which("docker-compose")

    if docker_path:
        subprocess.run([docker_path, "restart", "-t", "0", "redis_pubsub"], check=True)  # noqa: S603
    else:
        raise FileNotFoundError("Could not find docker-compose in PATH")
