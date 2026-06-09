import inspect
from collections.abc import Callable
from typing import Any

from src.adapters.notifications import AbstractNotifications, EmailNotifications
from src.adapters.orm import start_mappers
from src.adapters.redis_eventpublisher import publish
from src.helpers.logging_setup import logging_setup
from src.service_layer.handlers import COMMAND_HANDLERS, EVENT_HANDLERS
from src.service_layer.messagebus import AbstractUnitOfWork, MessageBus
from src.service_layer.unit_of_work import SqlAlchemyUnitOfWork

PublishCallable = Callable[..., Any]
HandlerCallable = Callable[..., Any]
InjectedHandler = Callable[[Any], Any]

logging_setup()


def bootstrap(
    start_orm: bool = True,
    unit_of_work: AbstractUnitOfWork | None = None,
    notifications: AbstractNotifications | None = None,
    publish: PublishCallable = publish,
) -> MessageBus:

    if unit_of_work is None:
        uow: AbstractUnitOfWork = SqlAlchemyUnitOfWork()
    else:
        uow = unit_of_work

    if notifications is None:
        notif: AbstractNotifications = EmailNotifications()
    else:
        notif = notifications

    if start_orm:
        start_mappers()

    dependencies: dict[str, Any] = {
        "unit_of_work": uow,
        "notifications": notif,
        "publish": publish,
    }

    injected_event_handlers = {
        event_type: [inject_dependencies(handler, dependencies) for handler in event_handlers]
        for event_type, event_handlers in EVENT_HANDLERS.items()
    }

    injected_command_handlers = {
        command_type: inject_dependencies(handler, dependencies) for command_type, handler in COMMAND_HANDLERS.items()
    }

    bus_unit_of_work: AbstractUnitOfWork = unit_of_work

    return MessageBus(
        unit_of_work=bus_unit_of_work,
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
