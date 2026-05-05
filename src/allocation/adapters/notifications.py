import abc
import smtplib
from typing import Any

from allocation import config


class AbstractNotifications(abc.ABC):
    @abc.abstractmethod
    def send(self, destination: str, message: str) -> None:
        raise NotImplementedError


DEFAULT_HOST: str = config.get_email_host_and_port()["host"]
DEFAULT_PORT: int = config.get_email_host_and_port()["port"]


class EmailNotifications(AbstractNotifications):
    def __init__(self, smtp_host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
        self.server: smtplib.SMTP = smtplib.SMTP(smtp_host, port=port)
        self.server.noop()

    def send(self, destination: str, message: str) -> None:
        msg: str = f"Subject: allocation service notification\n{message}"
        self.server.sendmail(
            from_addr="allocations@example.com",
            to_addrs=[destination],
            msg=msg,
        )
