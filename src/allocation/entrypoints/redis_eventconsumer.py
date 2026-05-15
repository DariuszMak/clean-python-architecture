import json
import logging
from typing import TYPE_CHECKING, Any

import redis

from allocation import config
from allocation.bootstrap import bootstrap
from allocation.domain.commands import ChangeBatchQuantity

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = logging.getLogger(__name__)

RedisMessage = dict[str, Any]


RedisHostPort = dict[str, Any]


redis_settings: Mapping[str, Any] = config.get_redis_host_and_port()
r: redis.Redis[Any] = redis.Redis(**redis_settings)


def main() -> None:
    logger.info("Redis pubsub starting")
    bus: Any = bootstrap()
    pubsub: Any = r.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe("change_batch_quantity")

    for m in pubsub.listen():
        handle_change_batch_quantity(m, bus)


def handle_change_batch_quantity(m: RedisMessage, bus: Any) -> None:
    logger.info("handling %s", m)
    data: dict[str, Any] = json.loads(m["data"])
    cmd: ChangeBatchQuantity = ChangeBatchQuantity(
        referenceerence=data["batch_reference"],
        quantity=data["quantity"],
    )
    bus.handle(cmd)


if __name__ == "__main__":
    main()
