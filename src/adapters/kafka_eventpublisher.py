import json
import logging
from dataclasses import asdict
from typing import TYPE_CHECKING, Any, cast

from kafka import KafkaProducer

from src.helpers.circuit_breaker import kafka_publish_breaker
from src.helpers.config import config

if TYPE_CHECKING:
    from src.domain import events

_producer: KafkaProducer | None = None


def get_producer() -> KafkaProducer:
    global _producer
    if _producer is None:
        bootstrap_servers = config.get_kafka_bootstrap_servers()
        _producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
    return _producer


def publish(topic: str, event: events.Event) -> None:
    logging.info("publishing to kafka: topic=%s, event=%s", topic, event)
    producer = get_producer()
    payload = asdict(cast("Any", event))
    kafka_publish_breaker.call(producer.send, topic, payload)
    producer.flush()
