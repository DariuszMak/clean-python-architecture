from unittest import mock

from allocation.bootstrap import bootstrap
from allocation.service_layer.messagebus import MessageBus


def test_bootstrap_creates_default_uow_when_none_given() -> None:
    fake_session_factory = mock.MagicMock()
    fake_session = mock.MagicMock()
    fake_session_factory.return_value = fake_session

    with (
        mock.patch(
            "allocation.service_layer.unit_of_work.DEFAULT_SESSION_FACTORY",
            fake_session_factory,
        ),
        mock.patch("allocation.adapters.orm.start_mappers"),
        mock.patch("allocation.adapters.notifications.EmailNotifications") as MockNotif,
    ):
        MockNotif.return_value = mock.MagicMock()
        bus = bootstrap(
            start_orm=False,
            uow=None,  # ← triggers line 24
            notifications=mock.MagicMock(),
            publish=lambda *_: None,
        )

    assert isinstance(bus, MessageBus)


def test_bootstrap_creates_default_notifications_when_none_given() -> None:
    from tests.unit.test_handlers import FakeUnitOfWork  # reuse existing fake

    with mock.patch("allocation.bootstrap.EmailNotifications") as MockNotif:
        mock_notif_instance = mock.MagicMock()
        MockNotif.return_value = mock_notif_instance

        bus = bootstrap(
            start_orm=False,
            uow=FakeUnitOfWork(),
            notifications=None,  # ← triggers line 27
            publish=lambda *_: None,
        )

    assert isinstance(bus, MessageBus)
    MockNotif.assert_called_once()
