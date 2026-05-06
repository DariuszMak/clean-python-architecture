import logging
from collections.abc import Callable
from typing import Protocol

from allocation.domain import events
from allocation.domain.commands import Command

logger = logging.getLogger(__name__)

Message = Command | events.Event


class AbstractUnitOfWork(Protocol):
    def collect_new_events(self) -> list[events.Event]: ...


EventHandler = Callable[[events.Event], None]
CommandHandler = Callable[[Command], None]


class MessageBus:
    def __init__(
        self,
        uow: AbstractUnitOfWork,
        event_handlers: dict[type[events.Event], list[EventHandler]],
        command_handlers: dict[type[Command], CommandHandler],
    ):
        self.uow = uow
        self.event_handlers = event_handlers
        self.command_handlers = command_handlers
        self.queue: list[Message] = []

    def handle(self, message: Message) -> None:
        self.queue = [message]
        while self.queue:
            message = self.queue.pop(0)
            if isinstance(message, events.Event):
                self.handle_event(message)
            elif isinstance(message, Command):
                self.handle_command(message)
            else:
                raise TypeError(f"{message} was not an Event or Command")

    def handle_event(self, event: events.Event) -> None:
        for handler in self.event_handlers[type(event)]:
            try:
                logger.debug("Event %s with handler %s", event, handler)
                handler(event)
                self.queue.extend(self.uow.collect_new_events())
            except Exception:
                logger.exception("Event exception %s", event)
                continue

    def handle_command(self, command: Command) -> None:
        logger.debug("Command %s", command)
        try:
            handler = self.command_handlers[type(command)]
            handler(command)
            self.queue.extend(self.uow.collect_new_events())
        except Exception:
            logger.exception("Command exception %s", command)
            raise
