import requests
from tenacity import retry, retry_if_exception_type, stop_after_delay, wait_fixed

from src.helpers.config import config

url = config.get_api_url()


@retry(
    stop=stop_after_delay(10),
    wait=wait_fixed(0.5),
    retry=retry_if_exception_type((requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout)),
)
def post_to_add_batch(ref: str, sku: str, quantity: int, estimated_time_of_arrival: str | None) -> requests.Response:
    return requests.post(
        f"{url}/add_batch",
        json={
            "reference": ref,
            "stock_keeping_unit": sku,
            "quantity": quantity,
            "estimated_time_of_arrival": estimated_time_of_arrival,
        },
        timeout=10,
    )


@retry(
    stop=stop_after_delay(10),
    wait=wait_fixed(0.5),
    retry=retry_if_exception_type((requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout)),
)
def post_to_allocate(order_id: str, sku: str, quantity: int) -> requests.Response:
    return requests.post(
        f"{url}/allocate",
        json={
            "order_id": order_id,
            "stock_keeping_unit": sku,
            "quantity": quantity,
        },
        timeout=10,
    )


@retry(
    stop=stop_after_delay(10),
    wait=wait_fixed(0.5),
    retry=retry_if_exception_type((requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout)),
)
def get_allocation(order_id: str) -> requests.Response:
    return requests.get(f"{url}/allocations/{order_id}", timeout=10)