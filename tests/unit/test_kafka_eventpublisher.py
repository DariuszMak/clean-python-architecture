from unittest.mock import MagicMock, patch

import pytest

from src.adapters.kafka_eventpublisher import publish
from src.domain import events


@pytest.fixture
def mock_kafka_producer():
    with patch("src.adapters.kafka_eventpublisher.get_producer") as mock_get:
        producer_instance = MagicMock()
        mock_get.return_value = producer_instance
        yield producer_instance


def test_publish_sends_event_to_kafka_topic(mock_kafka_producer):
    event = events.OutOfStock(sku="SMALL-TABLE")

    publish(topic="out_of_stock", event=event)

    mock_kafka_producer.send.assert_called_once_with(
        "out_of_stock",
        {"sku": "SMALL-TABLE"},
    )
    mock_kafka_producer.flush.assert_called_once()