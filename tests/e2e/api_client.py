from typing import Any, cast

import requests
from requests import Response

from allocation import config

TIMEOUT: int = 5


def post_to_add_batch(ref: Any, sku: Any, qty: Any, eta: Any) -> None:
    url: str = cast("str", config.get_api_url())
    r = requests.post(
        f"{url}/add_batch",
        json={"ref": ref, "sku": sku, "qty": qty, "eta": eta},
        timeout=TIMEOUT,
    )
    assert r.status_code == 201


def post_to_allocate(
    orderid: Any,
    sku: Any,
    qty: Any,
    expect_success: bool = True,
) -> Response:
    url: str = cast("str", config.get_api_url())
    r: Response = requests.post(
        f"{url}/allocate",
        json={
            "orderid": orderid,
            "sku": sku,
            "qty": qty,
        },
        timeout=TIMEOUT,
    )
    if expect_success:
        assert r.status_code == 202
    return r


def get_allocation(orderid: Any) -> Response:
    url: str = cast("str", config.get_api_url())
    return requests.get(f"{url}/allocations/{orderid}", timeout=TIMEOUT)
