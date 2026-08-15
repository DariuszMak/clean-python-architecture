import shutil
import subprocess  # noqa: S404
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
import redis
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, clear_mappers, sessionmaker
from tenacity import retry, stop_after_delay, wait_fixed

from src.adapters.orm import metadata, start_mappers
from src.helpers.circuit_breaker import reset_all_breakers
from src.helpers.config import config

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from sqlalchemy.engine import Engine


pytest.register_assert_rewrite("tests.e2e.api_client")

get_api_url: Callable[[], str] = config.get_api_url
get_redis_host_and_port: Callable[[], config.RedisConfig] = config.get_redis_host_and_port
get_postgres_uri: Callable[[], str] = config.get_postgres_uri

start_mappers_typed: Callable[[], None] = start_mappers

wait_for_postgres_to_come_up_untyped: Callable[[Engine], Any] | None = None
wait_for_webapp_to_come_up_untyped: Callable[[], requests.Response] | None = None
wait_for_redis_to_come_up_untyped: Callable[[], bool] | None = None


@pytest.fixture(autouse=True)
def _reset_circuit_breakers() -> None:
    reset_all_breakers()


@pytest.fixture
def in_memory_sqlite_db() -> Generator[Engine]:
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def sqlite_session_factory(
    in_memory_sqlite_db: Engine,
) -> sessionmaker[Session]:
    return sessionmaker(bind=in_memory_sqlite_db)


@pytest.fixture
def mappers() -> Generator[Any]:
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
    cfg = get_redis_host_and_port()
    r = redis.Redis(host=cfg["host"], port=cfg["port"])
    return bool(r.ping())


@pytest.fixture(scope="session")
def postgres_db() -> Engine:
    engine = create_engine(get_postgres_uri(), isolation_level="SERIALIZABLE")
    wait_for_postgres_to_come_up(engine)
    metadata.create_all(engine)
    return engine


@pytest.fixture
def postgres_session_factory(
    postgres_db: Engine,
) -> sessionmaker[Session]:
    return sessionmaker(bind=postgres_db)


@pytest.fixture
def postgres_session(
    postgres_session_factory: sessionmaker[Session],
) -> Session:
    return postgres_session_factory()


@pytest.fixture
def restart_api() -> None:
    (Path(__file__).parent / "../src/entrypoints/fastapi_app.py").touch()
    time.sleep(2)
    wait_for_webapp_to_come_up()


@pytest.fixture
def restart_redis_pubsub() -> None:
    wait_for_redis_to_come_up()

    if not shutil.which("docker-compose"):
        return

    docker_path = shutil.which("docker-compose")

    if docker_path:
        subprocess.run(  # noqa: S603
            [docker_path, "restart", "-t", "0", "redis_pubsub"],
            check=True,
        )
    else:
        raise FileNotFoundError("Could not find docker-compose in PATH")
    