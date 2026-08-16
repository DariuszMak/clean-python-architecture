import json

import pytest
from tenacity import Retrying, stop_after_delay

from tests.e2e.api_client import get_allocation, post_to_add_batch, post_to_allocate
from tests.e2e.kafka_client import publish_message, subscribe_to
from tests.random_references import random_batch_reference, random_order_id, random_stock_keeping_unit


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
@pytest.mark.usefixtures("restart_kafka_eventconsumer")
def test_change_batch_quantity_leading_to_reallocation() -> None:

    order_id, stock_keeping_unit = random_order_id(), random_stock_keeping_unit()
    earlier_batch, later_batch = random_batch_reference("old"), random_batch_reference("newer")

    subscription = subscribe_to("line_allocated")

    post_to_add_batch(earlier_batch, stock_keeping_unit, quantity=10, estimated_time_of_arrival="2011-01-02")
    post_to_add_batch(later_batch, stock_keeping_unit, quantity=10, estimated_time_of_arrival="2011-01-03")
    r = post_to_allocate(order_id, stock_keeping_unit, 10)
    assert r.ok
    response = get_allocation(order_id)
    assert response.json()[0]["batch_reference"] == earlier_batch

    publish_message("change_batch_quantity", {"batch_reference": earlier_batch, "quantity": 5})

    for attempt in Retrying(stop=stop_after_delay(10), reraise=True):
        with attempt:
            message = subscription.get_message(timeout=30)
            if message:
                data = json.loads(message["data"]) if isinstance(message["data"], str) else message["data"]
                if data["order_id"] == order_id and data["batch_reference"] == later_batch:
                    return
            raise AssertionError(f"Did not receive reallocation message for order {order_id} to batch {later_batch}")
