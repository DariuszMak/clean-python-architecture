import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, cast

from allocation.adapters import orm, redis_eventpublisher
from allocation.adapters.notifications import AbstractNotifications, EmailNotifications
from allocation.service_layer import handlers, messagebus
from allocation.service_layer.unit_of_work import AbstractUnitOfWork as AppAbstractUnitOfWork
from allocation.service_layer.unit_of_work import SqlAlchemyUnitOfWork

if TYPE_CHECKING:
    from allocation.service_layer.messagebus import AbstractUnitOfWork as BusAbstractUnitOfWork

PublishCallable = Callable[..., Any]
HandlerCallable = Callable[..., Any]
InjectedHandler = Callable[[Any], Any]


def bootstrap(
    start_orm: bool = True,
    uow: AppAbstractUnitOfWork | None = None,
    notifications: AbstractNotifications | None = None,
    publish: PublishCallable = redis_eventpublisher.publish,
) -> messagebus.MessageBus:
    if uow is None:
        uow = SqlAlchemyUnitOfWork()

    if notifications is None:
        notifications = EmailNotifications()

    if start_orm:
        orm.start_mappers()

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

    bus_uow = cast("BusAbstractUnitOfWork", uow)

    return messagebus.MessageBus(
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
