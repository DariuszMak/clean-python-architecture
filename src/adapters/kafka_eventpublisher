import json
import logging
from dataclasses import asdict
from typing import TYPE_CHECKING, Any, cast

from kafka import KafkaProducer
import structlog

from src.helpers.circuit_breaker import kafka_publish_breaker
from src.helpers.config import config

if TYPE_CHECKING:
    from domain import events

logger = structlog.get_logger(__name__)


def _get_producer() -> KafkaProducer:
    cfg = config.get_kafka_host_and_port()
    return KafkaProducer(
        bootstrap_servers=f"{cfg['host']}:{cfg['port']}",
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )


def publish(channel: str, event: events.Event) -> None:
    logging.info("publishing: channel=%s, event=%s", channel, event)
    producer = _get_producer()
    payload = asdict(cast("Any", event))
    kafka_publish_breaker.call(producer.send, channel, payload)
    producer.flush()
    producer.close()