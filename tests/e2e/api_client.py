from typing import Any

import requests
from requests import Response

from allocation import config

TIMEOUT: int = 5


def post_to_add_batch(
    referenceerence: Any, stock_keeping_unit: Any, quantity: Any, estimated_time_of_arrival: Any
) -> None:
    url: str = config.get_api_url()
    r = requests.post(
        f"{url}/add_batch",
        json={
            "referenceerence": referenceerence,
            "stock_keeping_unit": stock_keeping_unit,
            "quantity": quantity,
            "estimated_time_of_arrival": estimated_time_of_arrival,
        },
        timeout=TIMEOUT,
    )
    assert r.status_code == 201


def post_to_allocate(
    orderid: Any,
    stock_keeping_unit: Any,
    quantity: Any,
    expect_success: bool = True,
) -> Response:
    url: str = config.get_api_url()
    r: Response = requests.post(
        f"{url}/allocate",
        json={
            "orderid": orderid,
            "stock_keeping_unit": stock_keeping_unit,
            "quantity": quantity,
        },
        timeout=TIMEOUT,
    )
    if expect_success:
        assert r.status_code == 202
    return r


def get_allocation(orderid: Any) -> Response:
    url: str = config.get_api_url()
    return requests.get(f"{url}/allocations/{orderid}", timeout=TIMEOUT)
