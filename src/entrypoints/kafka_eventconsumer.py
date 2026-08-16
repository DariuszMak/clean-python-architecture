import json
from typing import TYPE_CHECKING, Any

from kafka import KafkaConsumer
import structlog

from src.bootstrap import bootstrap
from src.domain.commands import ChangeBatchQuantity
from src.helpers.config import config

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = structlog.get_logger(__name__)

KafkaMessage = dict[str, Any]


KafkaHostPort = dict[str, Any]


kafka_settings: Mapping[str, Any] = config.get_kafka_host_and_port()


def main() -> None:
    logger.info("Kafka consumer starting")
    bus: Any = bootstrap()
    consumer = KafkaConsumer(
        "change_batch_quantity",
        bootstrap_servers=f"{kafka_settings['host']}:{kafka_settings['port']}",
        group_id="allocation-group",
        auto_offset_reset="earliest",
    )

    for m in consumer:
        handle_change_batch_quantity(m, bus)


def handle_change_batch_quantity(m: Any, bus: Any) -> None:
    logger.info("handling %s", m)
    if isinstance(m, dict) and "data" in m:
        raw_data = m["data"]
        data: dict[str, Any] = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
    elif hasattr(m, "value"):
        val = m.value
        data = json.loads(val.decode("utf-8")) if isinstance(val, bytes) else json.loads(val) if isinstance(val, str) else val
    else:
        data = m
    cmd: ChangeBatchQuantity = ChangeBatchQuantity(
        reference=data["batch_reference"],
        quantity=data["quantity"],
    )
    bus.handle(cmd)


if __name__ == "__main__":
    main()
