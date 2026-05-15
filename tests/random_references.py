import uuid


def random_suffix() -> str:
    return uuid.uuid4().hex[:6]


def random_stock_keeping_unit(name: str = "") -> str:
    return f"stock_keeping_unit-{name}-{random_suffix()}"


def random_batchreference(name: str = "") -> str:
    return f"batch-{name}-{random_suffix()}"


def random_orderid(name: str = "") -> str:
    return f"order-{name}-{random_suffix()}"
