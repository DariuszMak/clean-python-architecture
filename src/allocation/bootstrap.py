import inspect
from collections.abc import Callable
from typing import Any

from allocation.adapters.notifications import AbstractNotifications, EmailNotifications
from allocation.adapters.orm import start_mappers
from allocation.adapters.redis_eventpublisher import publish
from allocation.service_layer.handlers import COMMAND_HANDLERS, EVENT_HANDLERS
from allocation.service_layer.messagebus import MessageBus
from allocation.service_layer.unit_of_work import AbstractUnitOfWork, SqlAlchemyUnitOfWork

PublishCallable = Callable[..., Any]
HandlerCallable = Callable[..., Any]
InjectedHandler = Callable[[Any], Any]


def bootstrap(
    start_orm: bool = True,
    uow: AbstractUnitOfWork | None = None,
    notifications: AbstractNotifications | None = None,
    publish: PublishCallable = publish,
) -> MessageBus:
    if uow is None:
        uow = SqlAlchemyUnitOfWork()

    if notifications is None:
        notifications = EmailNotifications()

    if start_orm:
        start_mappers()

    dependencies: dict[str, Any] = {
        "uow": uow,
        "notifications": notifications,
        "publish": publish,
    }

    injected_event_handlers = {
        event_type: [inject_dependencies(handler, dependencies) for handler in event_handlers]
        for event_type, event_handlers in EVENT_HANDLERS.items()
    }

    injected_command_handlers = {
        command_type: inject_dependencies(handler, dependencies) for command_type, handler in COMMAND_HANDLERS.items()
    }

    bus_uow: AbstractUnitOfWork = uow

    return MessageBus(
        uow=bus_uow,
        event_handlers=injected_event_handlers,
        command_handlers=injected_command_handlers,
    )


def inject_dependencies(
    handler: HandlerCallable,
    dependencies: dict[str, Any],
) -> InjectedHandler:
    params = inspect.signature(handler).parameters
    deps = {name: dependency for name, dependency in dependencies.items() if name in params}

    def wrapper(message: Any) -> Any:
        return handler(message, **deps)

    return wrapper
