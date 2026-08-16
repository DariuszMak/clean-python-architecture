from __future__ import annotations

import importlib
import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from unittest import mock

import pytest
from fastapi.testclient import TestClient

import src.entrypoints.fastapi_app as fastapi_module
import src.entrypoints.kafka_eventconsumer as consumer
from src.service_layer.handlers import InvalidStockKeepingUnitError

if TYPE_CHECKING:
    from collections.abc import Generator

FAKE_BUS = mock.MagicMock()
BOOTSTRAP_PATH = "src.bootstrap.bootstrap"


@pytest.fixture()
def api_client() -> Generator[tuple[TestClient, Any]]:
    with mock.patch(BOOTSTRAP_PATH, return_value=FAKE_BUS):
        importlib.reload(fastapi_module)

        with TestClient(fastapi_module.app) as client:
            yield client, fastapi_module


def test_add_batch_returns_201(
    api_client: tuple[TestClient, Any],
) -> None:
    client, _ = api_client

    FAKE_BUS.reset_mock()

    resp = client.post(
        "/add_batch",
        json={
            "reference": "b1",
            "stock_keeping_unit": "SMALL-TABLE",
            "quantity": 10,
            "estimated_time_of_arrival": None,
        },
    )

    assert resp.status_code == 201
    assert resp.json() == {"status": "OK"}

    FAKE_BUS.handle.assert_called_once()


def test_add_batch_with_estimated_time_of_arrival(
    api_client: tuple[TestClient, Any],
) -> None:
    client, _ = api_client

    FAKE_BUS.reset_mock()

    estimated_time_of_arrival_str = (datetime.now(tz=UTC).date() + timedelta(days=5)).isoformat()

    resp = client.post(
        "/add_batch",
        json={
            "reference": "b2",
            "stock_keeping_unit": "LAMP",
            "quantity": 5,
            "estimated_time_of_arrival": estimated_time_of_arrival_str,
        },
    )

    assert resp.status_code == 201


def test_allocate_returns_202(
    api_client: tuple[TestClient, Any],
) -> None:
    client, _ = api_client

    FAKE_BUS.reset_mock()

    resp = client.post(
        "/allocate",
        json={
            "order_id": "o1",
            "stock_keeping_unit": "SMALL-TABLE",
            "quantity": 3,
        },
    )

    assert resp.status_code == 202
    assert resp.json() == {"status": "OK"}


def test_allocate_returns_400_on_invalid_stock_keeping_unit(
    api_client: tuple[TestClient, Any],
) -> None:
    client, _ = api_client

    FAKE_BUS.reset_mock()

    FAKE_BUS.handle.side_effect = InvalidStockKeepingUnitError("Invalid stock_keeping_unit GHOST")

    resp = client.post(
        "/allocate",
        json={
            "order_id": "o1",
            "stock_keeping_unit": "GHOST",
            "quantity": 3,
        },
    )

    assert resp.status_code == 400
    assert resp.json() == {"message": "Invalid stock_keeping_unit GHOST"}

    FAKE_BUS.handle.side_effect = None


def test_allocations_view_returns_200(
    api_client: tuple[TestClient, Any],
) -> None:
    client, fastapi_module = api_client

    FAKE_BUS.reset_mock()

    with mock.patch.object(
        fastapi_module,
        "allocations",
        return_value=[
            {
                "stock_keeping_unit": "SMALL-TABLE",
                "batch_reference": "b1",
            }
        ],
    ):
        resp = client.get("/allocations/o1")

    assert resp.status_code == 200
    assert resp.json() == [
        {
            "stock_keeping_unit": "SMALL-TABLE",
            "batch_reference": "b1",
        }
    ]


def test_allocations_view_returns_404_when_empty(
    api_client: tuple[TestClient, Any],
) -> None:
    client, fastapi_module = api_client

    FAKE_BUS.reset_mock()

    with mock.patch.object(
        fastapi_module,
        "allocations",
        return_value=[],
    ):
        resp = client.get("/allocations/unknown")

    assert resp.status_code == 404


def _make_kafka_message(
    data: dict[str, Any],
) -> dict[str, str]:
    return {
        "type": "message",
        "data": json.dumps(data),
    }


@pytest.fixture()
def consumer_module() -> Generator[tuple[Any, mock.MagicMock]]:
    fake_kafka_instance = mock.MagicMock()

    with (
        mock.patch(
            "kafka.KafkaConsumer",
            return_value=fake_kafka_instance,
        ),
        mock.patch(
            BOOTSTRAP_PATH,
            return_value=FAKE_BUS,
        ),
    ):
        importlib.reload(consumer)
        yield consumer, fake_kafka_instance


def test_handle_change_batch_quantity(
    consumer_module: tuple[Any, mock.MagicMock],
) -> None:
    consumer, _ = consumer_module

    FAKE_BUS.reset_mock()

    msg = _make_kafka_message({
        "batch_reference": "b1",
        "quantity": 25,
    })

    consumer.handle_change_batch_quantity(msg, FAKE_BUS)