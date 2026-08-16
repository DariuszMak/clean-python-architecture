import shutil
import subprocess  # noqa: S404
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
import requests
from hypothesis import HealthCheck, settings
from kafka import KafkaConsumer
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, clear_mappers, sessionmaker
from tenacity import retry, retry_if_exception_type, stop_after_delay, wait_fixed

from src.adapters.orm import metadata, start_mappers
from src.helpers.circuit_breaker import reset_all_breakers
from src.helpers.config import config

if TYPE_CHECKING:
    from collections.abc import Callable, Generator

    from sqlalchemy.engine import Engine

# Disable Hypothesis deadline globally for test setup overhead
settings.register_profile("ci", deadline=None, suppress_health_check=[HealthCheck.too_slow])
settings.load_profile("ci")

pytest.register_assert_rewrite("tests.e2e.api_client")

get_api_url: Callable[[], str] = config.get_api_url
get_kafka_host_and_port: Callable[[], config.KafkaConfig] = config.get_kafka_host_and_port
get_postgres_uri: Callable[[], str] = config.get_postgres_uri

start_mappers_typed: Callable[[], None] = start_mappers


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


@retry(
    stop=stop_after_delay(30),
    wait=wait_fixed(0.5),
    retry=retry_if_exception_type((requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout)),
)
def wait_for_webapp_to_come_up() -> requests.Response:
    return requests.get(get_api_url(), timeout=5)


@retry(stop=stop_after_delay(10))
def wait_for_kafka_to_come_up() -> bool:
    cfg = get_kafka_host_and_port()
    consumer = KafkaConsumer(bootstrap_servers=f"{cfg['host']}:{cfg['port']}")
    consumer.topics()
    consumer.close()
    return True


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
def restart_kafka_eventconsumer() -> None:
    wait_for_kafka_to_come_up()

    cmd = None
    if shutil.which("docker"):
        cmd = ["docker", "compose", "restart", "-t", "0", "kafka_eventconsumer"]
    elif shutil.which("docker-compose"):
        cmd = ["docker-compose", "restart", "-t", "0", "kafka_eventconsumer"]

    if cmd:
        subprocess.run(cmd, check=True)  # noqa: S603
        time.sleep(2)
