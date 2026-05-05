import json
from typing import Any

import redis

from allocation import config

get_redis_host_and_port = config.get_redis_host_and_port

r = redis.Redis(**get_redis_host_and_port())
r_any: Any = r


def subscribe_to(channel: str) -> Any:
    pubsub = r_any.pubsub()
    pubsub.subscribe(channel)
    confirmation = pubsub.get_message(timeout=3)
    assert confirmation["type"] == "subscribe"
    return pubsub


def publish_message(channel: str, message: Any) -> None:
    r_any.publish(channel, json.dumps(message))
