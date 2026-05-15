import pytest

from tests.e2e.api_client import get_allocation, post_to_add_batch, post_to_allocate
from tests.random_references import random_batch_reference, random_orderid, random_stock_keeping_unit


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_happy_path_returns_202_and_batch_is_allocated() -> None:
    orderid = random_orderid()
    stock_keeping_unit, otherstock_keeping_unit = random_stock_keeping_unit(), random_stock_keeping_unit("other")
    earlybatch = random_batch_reference("1")
    laterbatch = random_batch_reference("2")
    otherbatch = random_batch_reference("3")

    post_to_add_batch(laterbatch, stock_keeping_unit, 100, "2011-01-02")
    post_to_add_batch(earlybatch, stock_keeping_unit, 100, "2011-01-01")
    post_to_add_batch(otherbatch, otherstock_keeping_unit, 100, None)

    r = post_to_allocate(orderid, stock_keeping_unit, quantity=3)
    assert r.status_code == 202

    r = get_allocation(orderid)
    assert r.ok
    assert r.json() == [
        {"stock_keeping_unit": stock_keeping_unit, "batch_reference": earlybatch},
    ]


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_unhappy_path_returns_400_and_error_message() -> None:
    unknown_stock_keeping_unit, orderid = random_stock_keeping_unit(), random_orderid()

    r = post_to_allocate(
        orderid,
        unknown_stock_keeping_unit,
        quantity=20,
        expect_success=False,
    )
    assert r.status_code == 400
    assert r.json()["message"] == f"Invalid stock_keeping_unit {unknown_stock_keeping_unit}"

    r = get_allocation(orderid)
    assert r.status_code == 404
