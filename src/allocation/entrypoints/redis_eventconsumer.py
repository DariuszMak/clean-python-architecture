import json
import logging
from typing import Any, Dict

import redis

from allocation import bootstrap, config
from allocation.domain import commands

logger = logging.getLogger(__name__)

RedisMessage = Dict[str, Any]


RedisHostPort = Dict[str, Any]


redis_settings: RedisHostPort = config.get_redis_host_and_port()
r: redis.Redis = redis.Redis(**redis_settings)


def main() -> None:
    logger.info("Redis pubsub starting")
    bus: Any = bootstrap.bootstrap()
    pubsub: Any = r.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe("change_batch_quantity")

    for m in pubsub.listen():
        handle_change_batch_quantity(m, bus)


def handle_change_batch_quantity(m: RedisMessage, bus: Any) -> None:
    logger.info("handling %s", m)
    data: Dict[str, Any] = json.loads(m["data"])
    cmd: commands.ChangeBatchQuantity = commands.ChangeBatchQuantity(
        ref=data["batchref"],
        qty=data["qty"],
    )
    bus.handle(cmd)


if __name__ == "__main__":
    main()