from unittest.mock import MagicMock

from src.domain import commands
from src.entrypoints.kafka_eventconsumer import handle_change_batch_quantity


def test_handle_change_batch_quantity_dispatches_command():
    fake_bus = MagicMock()
    payload = {"batch_reference": "batch-001", "quantity": 25}

    handle_change_batch_quantity(payload, fake_bus)

    fake_bus.handle.assert_called_once_with(
        commands.ChangeBatchQuantity(reference="batch-001", quantity=25)
    )
