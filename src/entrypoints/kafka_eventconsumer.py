import json
from typing import Any

import structlog
from kafka import KafkaConsumer

from src.bootstrap import bootstrap
from src.domain.commands import ChangeBatchQuantity
from src.helpers.config import config

logger = structlog.get_logger(__name__)


def main() -> None:
    logger.info("Kafka consumer starting")
    bus: Any = bootstrap()
    bootstrap_servers = config.get_kafka_bootstrap_servers()
    consumer = KafkaConsumer(
        "change_batch_quantity",
        bootstrap_servers=bootstrap_servers,
        group_id="allocation_group",
        auto_offset_reset="earliest",
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )

    for message in consumer:
        handle_change_batch_quantity(message.value, bus)


def handle_change_batch_quantity(data: dict[str, Any], bus: Any) -> None:
    logger.info("handling %s", data)
    cmd: ChangeBatchQuantity = ChangeBatchQuantity(
        reference=data["batch_reference"],
        quantity=data["quantity"],
    )
    bus.handle(cmd)


if __name__ == "__main__":
    main()
