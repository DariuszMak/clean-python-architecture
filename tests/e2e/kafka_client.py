import json
import uuid
from typing import Any

from kafka import KafkaConsumer, KafkaProducer

from src.helpers.config import config

get_kafka_host_and_port = config.get_kafka_host_and_port


class KafkaSubscription:
    def __init__(self, topic: str) -> None:
        cfg = get_kafka_host_and_port()
        self.consumer = KafkaConsumer(
            topic,
            bootstrap_servers=f"{cfg['host']}:{cfg['port']}",
            auto_offset_reset="latest",
            group_id=f"test-group-{uuid.uuid4().hex}",
            consumer_timeout_ms=1000,
        )

    def get_message(self, timeout: int = 30) -> dict[str, Any] | None:
        import time

        start = time.time()
        while time.time() - start < timeout:
            records = self.consumer.poll(timeout_ms=1000)
            for _tp, msgs in records.items():
                for msg in msgs:
                    val = msg.value.decode("utf-8") if isinstance(msg.value, bytes) else msg.value
                    return {"data": val}
        return None


def subscribe_to(channel: str) -> KafkaSubscription:
    return KafkaSubscription(channel)


def publish_message(channel: str, message: Any) -> None:
    cfg = get_kafka_host_and_port()
    producer = KafkaProducer(
        bootstrap_servers=f"{cfg['host']}:{cfg['port']}",
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    producer.send(channel, message)
    producer.flush()
    producer.close()
