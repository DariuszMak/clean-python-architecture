from __future__ import annotations

import json
from unittest import mock

import pybreaker
import pytest

from src.adapters.notifications import EmailNotifications
from src.domain.events import Allocated
from src.helpers.circuit_breaker import database_breaker, email_breaker, redis_publish_breaker
from src.service_layer.unit_of_work import SqlAlchemyUnitOfWork


def test_redis_publish_breaker_opens_after_repeated_failures() -> None:
    import src.adapters.redis_eventpublisher as redis_eventpublisher

    event = Allocated(order_id="o1", stock_keeping_unit="sku1", quantity=1, batch_reference="b1")

    with mock.patch.object(redis_eventpublisher, "r") as fake_redis:
        fake_redis.publish.side_effect = ConnectionError("redis down")

        for _ in range(redis_publish_breaker.fail_max):
            with pytest.raises(ConnectionError):
                redis_eventpublisher.publish("channel", event)

        assert redis_publish_breaker.current_state == "open"

        with pytest.raises(pybreaker.CircuitBreakerError):
            redis_eventpublisher.publish("channel", event)


def test_redis_publish_breaker_stays_closed_on_success() -> None:
    import src.adapters.redis_eventpublisher as redis_eventpublisher

    event = Allocated(order_id="o1", stock_keeping_unit="sku1", quantity=1, batch_reference="b1")

    with mock.patch.object(redis_eventpublisher, "r") as fake_redis:
        fake_redis.publish.return_value = 1

        redis_eventpublisher.publish("channel", event)

        assert redis_publish_breaker.current_state == "closed"
        fake_redis.publish.assert_called_once_with("channel", json.dumps(event.__dict__))


def test_email_breaker_opens_after_repeated_failures() -> None:
    with mock.patch("smtplib.SMTP") as fake_smtp_cls:
        fake_server = mock.MagicMock()
        fake_smtp_cls.return_value = fake_server
        fake_server.sendmail.side_effect = ConnectionRefusedError("smtp down")

        notifications = EmailNotifications()

        for _ in range(email_breaker.fail_max):
            with pytest.raises(ConnectionRefusedError):
                notifications.send("dest@example.com", "message")

        assert email_breaker.current_state == "open"

        with pytest.raises(pybreaker.CircuitBreakerError):
            notifications.send("dest@example.com", "message")


def test_email_breaker_stays_closed_on_success() -> None:
    with mock.patch("smtplib.SMTP") as fake_smtp_cls:
        fake_server = mock.MagicMock()
        fake_smtp_cls.return_value = fake_server

        notifications = EmailNotifications()
        notifications.send("dest@example.com", "message")

        assert email_breaker.current_state == "closed"
        fake_server.sendmail.assert_called_once()


def test_database_breaker_opens_after_repeated_commit_failures() -> None:
    fake_session_factory = mock.MagicMock()
    fake_session = mock.MagicMock()
    fake_session_factory.return_value = fake_session
    fake_session.commit.side_effect = ConnectionError("db down")

    unit_of_work = SqlAlchemyUnitOfWork(fake_session_factory)

    with unit_of_work:
        for _ in range(database_breaker.fail_max):
            with pytest.raises(ConnectionError):
                unit_of_work.commit()

        assert database_breaker.current_state == "open"

        with pytest.raises(pybreaker.CircuitBreakerError):
            unit_of_work.commit()


def test_database_breaker_stays_closed_on_success() -> None:
    fake_session_factory = mock.MagicMock()
    fake_session = mock.MagicMock()
    fake_session_factory.return_value = fake_session

    unit_of_work = SqlAlchemyUnitOfWork(fake_session_factory)

    with unit_of_work:
        unit_of_work.commit()

    assert database_breaker.current_state == "closed"
    fake_session.commit.assert_called_once()
