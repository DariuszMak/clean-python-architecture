import pytest

from tests.e2e.api_client import get_allocation, post_to_add_batch, post_to_allocate
from tests.random_references import random_batch_reference, random_order_id, random_stock_keeping_unit


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_happy_path_returns_202_and_batch_is_allocated() -> None:
    order_id = random_order_id()
    stock_keeping_unit, otherstock_keeping_unit = random_stock_keeping_unit(), random_stock_keeping_unit("other")
    earlybatch = random_batch_reference("1")
    laterbatch = random_batch_reference("2")
    otherbatch = random_batch_reference("3")

    post_to_add_batch(laterbatch, stock_keeping_unit, 100, "2011-01-02")
    post_to_add_batch(earlybatch, stock_keeping_unit, 100, "2011-01-01")
    post_to_add_batch(otherbatch, otherstock_keeping_unit, 100, None)

    r = post_to_allocate(order_id, stock_keeping_unit, quantity=3)
    assert r.status_code == 202

    r = get_allocation(order_id)
    assert r.ok
    assert r.json() == [
        {"stock_keeping_unit": stock_keeping_unit, "batch_reference": earlybatch},
    ]


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_unhappy_path_returns_400_and_error_message() -> None:
    unknown_stock_keeping_unit, order_id = random_stock_keeping_unit(), random_order_id()

    r = post_to_allocate(
        order_id,
        unknown_stock_keeping_unit,
        quantity=20,
        expect_success=False,
    )
    assert r.status_code == 400
    assert r.json()["message"] == f"Invalid stock_keeping_unit {unknown_stock_keeping_unit}"

    r = get_allocation(order_id)
    assert r.status_code == 404


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_allocate_prefers_current_stock_over_shipments() -> None:
    order_id = random_order_id()
    stock_keeping_unit = random_stock_keeping_unit()
    in_stock_batch = random_batch_reference("in-stock")
    shipment_batch = random_batch_reference("shipment")

    post_to_add_batch(shipment_batch, stock_keeping_unit, 100, "2011-01-02")
    post_to_add_batch(in_stock_batch, stock_keeping_unit, 100, None)

    r = post_to_allocate(order_id, stock_keeping_unit, quantity=10)
    assert r.status_code == 202

    r = get_allocation(order_id)
    assert r.ok
    assert r.json() == [
        {"stock_keeping_unit": stock_keeping_unit, "batch_reference": in_stock_batch},
    ]


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_returns_404_for_order_with_no_allocations() -> None:
    order_id = random_order_id()

    r = get_allocation(order_id)
    assert r.status_code == 404


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_allocate_with_insufficient_stock_returns_202_but_records_no_allocation() -> None:
    order_id = random_order_id()
    stock_keeping_unit = random_stock_keeping_unit()
    batch = random_batch_reference()

    post_to_add_batch(batch, stock_keeping_unit, 5, None)

    r = post_to_allocate(order_id, stock_keeping_unit, quantity=10)
    assert r.status_code == 202

    r = get_allocation(order_id)
    assert r.status_code == 404


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_second_order_falls_back_to_next_batch_once_first_is_exhausted() -> None:
    order_id_1, order_id_2 = random_order_id("1"), random_order_id("2")
    stock_keeping_unit = random_stock_keeping_unit()
    earlybatch = random_batch_reference("early")
    laterbatch = random_batch_reference("later")

    post_to_add_batch(earlybatch, stock_keeping_unit, 5, "2011-01-01")
    post_to_add_batch(laterbatch, stock_keeping_unit, 5, "2011-01-02")

    r = post_to_allocate(order_id_1, stock_keeping_unit, quantity=5)
    assert r.status_code == 202

    r = post_to_allocate(order_id_2, stock_keeping_unit, quantity=5)
    assert r.status_code == 202

    r = get_allocation(order_id_1)
    assert r.ok
    assert r.json() == [
        {"stock_keeping_unit": stock_keeping_unit, "batch_reference": earlybatch},
    ]

    r = get_allocation(order_id_2)
    assert r.ok
    assert r.json() == [
        {"stock_keeping_unit": stock_keeping_unit, "batch_reference": laterbatch},
    ]


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_allocations_for_different_stock_keeping_units_do_not_interfere() -> None:
    order_id = random_order_id()
    stock_keeping_unit_a = random_stock_keeping_unit("a")
    stock_keeping_unit_b = random_stock_keeping_unit("b")
    batch_a = random_batch_reference("a")
    batch_b = random_batch_reference("b")

    post_to_add_batch(batch_a, stock_keeping_unit_a, 10, None)
    post_to_add_batch(batch_b, stock_keeping_unit_b, 10, None)

    r = post_to_allocate(order_id, stock_keeping_unit_a, quantity=1)
    assert r.status_code == 202

    r = post_to_allocate(order_id, stock_keeping_unit_b, quantity=1)
    assert r.status_code == 202

    r = get_allocation(order_id)
    assert r.ok
    assert sorted(r.json(), key=lambda a: a["stock_keeping_unit"]) == sorted(
        [
            {"stock_keeping_unit": stock_keeping_unit_a, "batch_reference": batch_a},
            {"stock_keeping_unit": stock_keeping_unit_b, "batch_reference": batch_b},
        ],
        key=lambda a: a["stock_keeping_unit"],
    )


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_adding_larger_batch_allows_order_that_first_batch_alone_could_not_cover() -> None:
    order_id = random_order_id()
    stock_keeping_unit = random_stock_keeping_unit()
    too_small_batch = random_batch_reference("small")
    sufficient_batch = random_batch_reference("sufficient")

    post_to_add_batch(too_small_batch, stock_keeping_unit, 5, None)
    post_to_add_batch(sufficient_batch, stock_keeping_unit, 20, None)

    r = post_to_allocate(order_id, stock_keeping_unit, quantity=8)
    assert r.status_code == 202

    r = get_allocation(order_id)
    assert r.ok
    assert r.json() == [
        {"stock_keeping_unit": stock_keeping_unit, "batch_reference": sufficient_batch},
    ]
