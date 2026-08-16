from unittest import mock

from src.bootstrap import bootstrap
from src.service_layer.messagebus import MessageBus
from tests.unit.test_handlers import FakeUnitOfWork

from src.bootstrap import bootstrap
from src.domain import events

def test_bootstrap_creates_default_unit_of_work_when_none_given() -> None:
    fake_session_factory = mock.MagicMock()
    fake_session = mock.MagicMock()
    fake_session_factory.return_value = fake_session

    with (
        mock.patch(
            "src.service_layer.unit_of_work.DEFAULT_SESSION_FACTORY",
            fake_session_factory,
        ),
        mock.patch("src.adapters.orm.start_mappers"),
        mock.patch("src.adapters.notifications.EmailNotifications") as mock_notif,
    ):
        mock_notif.return_value = mock.MagicMock()
        bus = bootstrap(
            start_orm=False,
            unit_of_work=None,
            notifications=mock.MagicMock(),
            publish=lambda *_: None,
        )

    assert isinstance(bus, MessageBus)


def test_bootstrap_creates_default_notifications_when_none_given() -> None:

    with mock.patch("src.bootstrap.EmailNotifications") as mock_notif:
        mock_notif_instance = mock.MagicMock()
        mock_notif.return_value = mock_notif_instance

        bus = bootstrap(
            start_orm=False,
            unit_of_work=FakeUnitOfWork(),
            notifications=None,
            publish=lambda *_: None,
        )

    assert isinstance(bus, MessageBus)
    mock_notif.assert_called_once()


def test_bootstrap_injects_kafka_publisher_by_default():
    bus = bootstrap(start_orm=False)

    assert bus.event_handlers[events.OutOfStock] is not None