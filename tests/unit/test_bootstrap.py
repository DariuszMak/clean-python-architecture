from unittest import mock

from bootstrap import bootstrap
from service_layer.messagebus import MessageBus
from tests.unit.test_handlers import FakeUnitOfWork


def test_bootstrap_creates_default_unit_of_work_when_none_given() -> None:
    fake_session_factory = mock.MagicMock()
    fake_session = mock.MagicMock()
    fake_session_factory.return_value = fake_session

    with (
        mock.patch(
            "service_layer.unit_of_work.DEFAULT_SESSION_FACTORY",
            fake_session_factory,
        ),
        mock.patch("adapters.orm.start_mappers"),
        mock.patch("adapters.notifications.EmailNotifications") as mock_notif,
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

    with mock.patch("bootstrap.EmailNotifications") as mock_notif:
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
