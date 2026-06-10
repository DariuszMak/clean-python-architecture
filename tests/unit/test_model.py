from datetime import UTC, datetime, timedelta

from src.domain.model import Batch

today = datetime.now(tz=UTC).date()
tomorrow = today + timedelta(days=1)


def test_batch_repr() -> None:
    batch = Batch("batch-001", "SMALL-TABLE", quantity=20, estimated_time_of_arrival=None)
    assert repr(batch) == "<Batch batch-001>"


def test_batch_eq_with_non_batch() -> None:
    batch = Batch("batch-001", "SMALL-TABLE", quantity=20, estimated_time_of_arrival=None)
    assert batch != "not-a-batch"
    assert batch != 42
    assert batch is not None


def test_batch_gt_self_has_no_estimated_time_of_arrival() -> None:
    no_estimated_time_of_arrival = Batch("b1", "STOCKKEEPINGUNIT", 10, estimated_time_of_arrival=None)
    with_estimated_time_of_arrival = Batch("b2", "STOCKKEEPINGUNIT", 10, estimated_time_of_arrival=tomorrow)
    assert not (no_estimated_time_of_arrival > with_estimated_time_of_arrival)
    assert not (no_estimated_time_of_arrival > no_estimated_time_of_arrival)


def test_batch_gt_other_has_no_estimated_time_of_arrival() -> None:
    with_estimated_time_of_arrival = Batch("b1", "STOCKKEEPINGUNIT", 10, estimated_time_of_arrival=tomorrow)
    no_estimated_time_of_arrival = Batch("b2", "STOCKKEEPINGUNIT", 10, estimated_time_of_arrival=None)
    assert with_estimated_time_of_arrival > no_estimated_time_of_arrival


def test_batch_gt_both_have_estimated_time_of_arrival() -> None:
    earlier = Batch("b1", "STOCKKEEPINGUNIT", 10, estimated_time_of_arrival=today)
    later = Batch("b2", "STOCKKEEPINGUNIT", 10, estimated_time_of_arrival=tomorrow)
    assert later > earlier
    assert not (earlier > later)
