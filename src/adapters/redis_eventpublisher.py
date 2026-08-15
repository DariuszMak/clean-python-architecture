import json
import logging
from dataclasses import asdict
from typing import TYPE_CHECKING, Any, cast

import redis
import structlog

from src.helpers.circuit_breaker import redis_publish_breaker
from src.helpers.config import config

if TYPE_CHECKING:
    from domain import events

logger = structlog.get_logger(__name__)

r = redis.Redis(**cast("dict[str, Any]", config.get_redis_host_and_port()))


def publish(channel: str, event: events.Event) -> None:
    logging.info("publishing: channel=%s, event=%s", channel, event)
    redis_publish_breaker.call(r.publish, channel, json.dumps(asdict(cast("Any", event))))
