from datetime import UTC, datetime, timedelta

from allocation.domain.model import Batch

today = datetime.now(tz=UTC).date()
tomorrow = today + timedelta(days=1)


# model.py line 62 — __repr__
def test_batch_repr() -> None:
    batch = Batch("batch-001", "SMALL-TABLE", qty=20, eta=None)
    assert repr(batch) == "<Batch batch-001>"


# model.py line 64-65 — __eq__ when other is not a Batch
def test_batch_eq_with_non_batch() -> None:
    batch = Batch("batch-001", "SMALL-TABLE", qty=20, eta=None)
    assert batch != "not-a-batch"
    assert batch != 42
    assert batch != None  # noqa: E711


# model.py lines 66-70 — __gt__ branches
def test_batch_gt_self_has_no_eta() -> None:
    no_eta = Batch("b1", "SKU", 10, eta=None)
    with_eta = Batch("b2", "SKU", 10, eta=tomorrow)
    assert not (no_eta > with_eta)
    assert not (no_eta > no_eta)


def test_batch_gt_other_has_no_eta() -> None:
    with_eta = Batch("b1", "SKU", 10, eta=tomorrow)
    no_eta = Batch("b2", "SKU", 10, eta=None)
    assert with_eta > no_eta


def test_batch_gt_both_have_eta() -> None:
    earlier = Batch("b1", "SKU", 10, eta=today)
    later = Batch("b2", "SKU", 10, eta=tomorrow)
    assert later > earlier
    assert not (earlier > later)
