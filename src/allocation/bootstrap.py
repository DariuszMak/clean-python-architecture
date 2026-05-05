import inspect
from collections.abc import Callable
from typing import Any

from allocation.adapters import orm, redis_eventpublisher
from allocation.adapters.notifications import AbstractNotifications, EmailNotifications
from allocation.service_layer import handlers, messagebus, unit_of_work

PublishCallable = Callable[..., Any]
HandlerCallable = Callable[..., Any]
InjectedHandler = Callable[[Any], Any]


def bootstrap(
    start_orm: bool = True,
    uow: unit_of_work.AbstractUnitOfWork | None = None,
    notifications: AbstractNotifications | None = None,
    publish: PublishCallable = redis_eventpublisher.publish,
) -> messagebus.MessageBus:
    if uow is None:
        uow = unit_of_work.SqlAlchemyUnitOfWork()

    if notifications is None:
        notifications = EmailNotifications()

    if start_orm:
        start_mappers: Callable[[], None] = orm.start_mappers
        start_mappers()

    dependencies: dict[str, Any] = {
        "uow": uow,
        "notifications": notifications,
        "publish": publish,
    }

    injected_event_handlers = {
        event_type: [inject_dependencies(handler, dependencies) for handler in event_handlers]
        for event_type, event_handlers in handlers.EVENT_HANDLERS.items()
    }

    injected_command_handlers = {
        command_type: inject_dependencies(handler, dependencies)
        for command_type, handler in handlers.COMMAND_HANDLERS.items()
    }

    return messagebus.MessageBus(
        uow=uow,
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
