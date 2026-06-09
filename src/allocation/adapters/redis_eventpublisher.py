import json
import logging
from dataclasses import asdict
from typing import TYPE_CHECKING, Any, cast
import structlog
import redis

from allocation import config

if TYPE_CHECKING:
    from allocation.domain import events

logger = structlog.get_logger(__name__)

r = redis.Redis(**cast("dict[str, Any]", config.get_redis_host_and_port()))


def publish(channel: str, event: events.Event) -> None:
    logging.info("publishing: channel=%s, event=%s", channel, event)
    r.publish(channel, json.dumps(asdict(cast("Any", event))))
