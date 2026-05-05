import uuid


def random_suffix() -> str:
    return uuid.uuid4().hex[:6]


def random_sku(name: str = "") -> str:
    return f"sku-{name}-{random_suffix()}"


def random_batchref(name: str = "") -> str:
    return f"batch-{name}-{random_suffix()}"


def random_orderid(name: str = "") -> str:
    return f"order-{name}-{random_suffix()}"
