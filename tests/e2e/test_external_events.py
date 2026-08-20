import json
import time

import pytest

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

    start_time = time.time()
    timeout = 15
    while time.time() - start_time < timeout:
        message = subscription.get_message(timeout=1)
        if message:
            data = json.loads(message["data"]) if isinstance(message["data"], str) else message["data"]
            if data.get("order_id") == order_id and data.get("batch_reference") == later_batch:
                return

    raise AssertionError(f"Did not receive reallocation message for order {order_id} to batch {later_batch}")


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
@pytest.mark.usefixtures("restart_kafka_eventconsumer")
def test_change_batch_quantity_that_still_covers_allocation_does_not_reallocate() -> None:

    order_id, stock_keeping_unit = random_order_id(), random_stock_keeping_unit()
    batch = random_batch_reference()

    post_to_add_batch(batch, stock_keeping_unit, quantity=10, estimated_time_of_arrival=None)
    r = post_to_allocate(order_id, stock_keeping_unit, 5)
    assert r.ok
    response = get_allocation(order_id)
    assert response.json()[0]["batch_reference"] == batch

    subscription = subscribe_to("line_allocated")

    publish_message("change_batch_quantity", {"batch_reference": batch, "quantity": 8})

    time.sleep(3)

    message = subscription.get_message(timeout=5)
    if message:
        data = json.loads(message["data"]) if isinstance(message["data"], str) else message["data"]
        assert data.get("order_id") != order_id

    response = get_allocation(order_id)
    assert response.json()[0]["batch_reference"] == batch


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
@pytest.mark.usefixtures("restart_kafka_eventconsumer")
def test_change_batch_quantity_reallocates_one_of_several_orders_on_the_shrunk_batch() -> None:

    order_id_1, order_id_2 = random_order_id("1"), random_order_id("2")
    stock_keeping_unit = random_stock_keeping_unit()
    earlier_batch, later_batch = random_batch_reference("old"), random_batch_reference("newer")

    subscription = subscribe_to("line_allocated")

    post_to_add_batch(earlier_batch, stock_keeping_unit, quantity=20, estimated_time_of_arrival="2011-01-02")
    post_to_add_batch(later_batch, stock_keeping_unit, quantity=20, estimated_time_of_arrival="2011-01-03")

    r = post_to_allocate(order_id_1, stock_keeping_unit, 10)
    assert r.ok
    r = post_to_allocate(order_id_2, stock_keeping_unit, 10)
    assert r.ok

    assert get_allocation(order_id_1).json()[0]["batch_reference"] == earlier_batch
    assert get_allocation(order_id_2).json()[0]["batch_reference"] == earlier_batch

    publish_message("change_batch_quantity", {"batch_reference": earlier_batch, "quantity": 10})

    start_time = time.time()
    timeout = 15
    while time.time() - start_time < timeout:
        message = subscription.get_message(timeout=1)
        if message:
            data = json.loads(message["data"]) if isinstance(message["data"], str) else message["data"]
            if data.get("order_id") in {order_id_1, order_id_2} and data.get("batch_reference") == later_batch:
                reallocated_order = data["order_id"]
                remaining_order = order_id_2 if reallocated_order == order_id_1 else order_id_1

                assert get_allocation(reallocated_order).json()[0]["batch_reference"] == later_batch
                assert get_allocation(remaining_order).json()[0]["batch_reference"] == earlier_batch
                return

    raise AssertionError(
        f"Did not receive reallocation message for either {order_id_1} or {order_id_2} to batch {later_batch}"
    )
