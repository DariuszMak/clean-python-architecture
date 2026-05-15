import uuid


def random_suffix() -> str:
    return uuid.uuid4().hex[:6]


def random_stock_keeping_unit(name: str = "") -> str:
    return f"stock_keeping_unit-{name}-{random_suffix()}"


def random_batch_reference(name: str = "") -> str:
    return f"batch-{name}-{random_suffix()}"


def random_order_id(name: str = "") -> str:
    return f"order-{name}-{random_suffix()}"
