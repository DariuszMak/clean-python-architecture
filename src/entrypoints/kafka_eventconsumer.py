import inspect
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

    sig = inspect.signature(ChangeBatchQuantity)
    kwargs: dict[str, Any] = {}
    ref_val = data.get("batch_reference") or data.get("ref") or data.get("reference")
    qty_val = data.get("quantity") or data.get("qty")

    if "ref" in sig.parameters:
        kwargs["ref"] = ref_val
    elif "reference" in sig.parameters:
        kwargs["reference"] = ref_val

    if "qty" in sig.parameters:
        kwargs["qty"] = qty_val
    elif "quantity" in sig.parameters:
        kwargs["quantity"] = qty_val

    cmd = ChangeBatchQuantity(**kwargs)
    bus.handle(cmd)


if __name__ == "__main__":
    main()
