from __future__ import annotations

import importlib
import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from unittest import mock

import pytest

import allocation.entrypoints.flask_app as flask_module
import allocation.entrypoints.redis_eventconsumer as consumer
from allocation.service_layer.handlers import InvalidSkuError

if TYPE_CHECKING:
    from collections.abc import Generator

    from flask.testing import FlaskClient

FAKE_BUS = mock.MagicMock()
BOOTSTRAP_PATH = "allocation.bootstrap.bootstrap"


@pytest.fixture()
def flask_client() -> Generator[tuple[FlaskClient, Any]]:
    with mock.patch(BOOTSTRAP_PATH, return_value=FAKE_BUS):
        importlib.reload(flask_module)
        flask_module.app.config["TESTING"] = True

        with flask_module.app.test_client() as client:
            yield client, flask_module


def test_add_batch_returns_201(
    flask_client: tuple[FlaskClient, Any],
) -> None:
    client, _ = flask_client

    FAKE_BUS.reset_mock()

    resp = client.post(
        "/add_batch",
        json={
            "ref": "b1",
            "sku": "SMALL-TABLE",
            "quantity": 10,
            "eta": None,
        },
    )

    assert resp.status_code == 201
    assert resp.get_json() == {"status": "OK"}

    FAKE_BUS.handle.assert_called_once()


def test_add_batch_with_eta(
    flask_client: tuple[FlaskClient, Any],
) -> None:
    client, _ = flask_client

    FAKE_BUS.reset_mock()

    eta_str = (datetime.now(tz=UTC).date() + timedelta(days=5)).isoformat()

    resp = client.post(
        "/add_batch",
        json={
            "ref": "b2",
            "sku": "LAMP",
            "quantity": 5,
            "eta": eta_str,
        },
    )

    assert resp.status_code == 201


def test_allocate_returns_202(
    flask_client: tuple[FlaskClient, Any],
) -> None:
    client, _ = flask_client

    FAKE_BUS.reset_mock()

    resp = client.post(
        "/allocate",
        json={
            "orderid": "o1",
            "sku": "SMALL-TABLE",
            "quantity": 3,
        },
    )

    assert resp.status_code == 202
    assert resp.get_json() == {"status": "OK"}


def test_allocate_returns_400_on_invalid_sku(
    flask_client: tuple[FlaskClient, Any],
) -> None:
    client, _ = flask_client

    FAKE_BUS.reset_mock()

    FAKE_BUS.handle.side_effect = InvalidSkuError("Invalid sku GHOST")

    resp = client.post(
        "/allocate",
        json={
            "orderid": "o1",
            "sku": "GHOST",
            "quantity": 3,
        },
    )

    assert resp.status_code == 400
    assert resp.get_json() == {"message": "Invalid sku GHOST"}

    FAKE_BUS.handle.side_effect = None


def test_allocations_view_returns_200(
    flask_client: tuple[FlaskClient, Any],
) -> None:
    client, flask_module = flask_client

    FAKE_BUS.reset_mock()

    with mock.patch.object(
        flask_module,
        "allocations",
        return_value=[
            {
                "sku": "SMALL-TABLE",
                "batchref": "b1",
            }
        ],
    ):
        resp = client.get("/allocations/o1")

    assert resp.status_code == 200
    assert resp.get_json() == [
        {
            "sku": "SMALL-TABLE",
            "batchref": "b1",
        }
    ]


def test_allocations_view_returns_404_when_empty(
    flask_client: tuple[FlaskClient, Any],
) -> None:
    client, flask_module = flask_client

    FAKE_BUS.reset_mock()

    with mock.patch.object(
        flask_module,
        "allocations",
        return_value=[],
    ):
        resp = client.get("/allocations/unknown")

    assert resp.status_code == 404


def _make_redis_message(
    data: dict[str, Any],
) -> dict[str, str]:
    return {
        "type": "message",
        "data": json.dumps(data),
    }


@pytest.fixture()
def consumer_module() -> Generator[tuple[Any, mock.MagicMock]]:
    fake_redis_instance = mock.MagicMock()

    with (
        mock.patch(
            "redis.Redis",
            return_value=fake_redis_instance,
        ),
        mock.patch(
            BOOTSTRAP_PATH,
            return_value=FAKE_BUS,
        ),
    ):
        importlib.reload(consumer)
        yield consumer, fake_redis_instance


def test_handle_change_batch_quantity(
    consumer_module: tuple[Any, mock.MagicMock],
) -> None:
    consumer, _ = consumer_module

    FAKE_BUS.reset_mock()

    msg = _make_redis_message({
        "batchref": "b1",
        "quantity": 25,
    })

    consumer.handle_change_batch_quantity(
        msg,
        FAKE_BUS,
    )

    FAKE_BUS.handle.assert_called_once()

    cmd = FAKE_BUS.handle.call_args[0][0]

    assert cmd.ref == "b1"
    assert cmd.quantity == 25


def test_main_subscribes_and_handles_messages(
    consumer_module: tuple[Any, mock.MagicMock],
) -> None:
    consumer, fake_redis_instance = consumer_module

    FAKE_BUS.reset_mock()

    fake_pubsub = mock.MagicMock()

    fake_redis_instance.pubsub.return_value = fake_pubsub

    msg = _make_redis_message({
        "batchref": "b2",
        "quantity": 50,
    })

    fake_pubsub.listen.return_value = iter([msg])

    with mock.patch.object(
        consumer,
        "bootstrap",
        return_value=FAKE_BUS,
    ):
        consumer.main()

    fake_pubsub.subscribe.assert_called_once_with("change_batch_quantity")

    FAKE_BUS.handle.assert_called_once()
