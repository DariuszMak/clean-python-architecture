from __future__ import annotations

from typing import Any

import pybreaker
import structlog

logger = structlog.get_logger(__name__)


class CircuitBreakerListener(pybreaker.CircuitBreakerListener):
    def state_change(self, cb: pybreaker.CircuitBreaker, old_state: Any, new_state: Any) -> None:
        logger.warning(
            "Circuit breaker state change",
            breaker=cb.name,
            old_state=old_state.name,
            new_state=new_state.name,
        )

    def failure(self, cb: pybreaker.CircuitBreaker, exc: Exception) -> None:
        logger.warning("Circuit breaker failure", breaker=cb.name, error=str(exc))


def make_circuit_breaker(name: str, fail_max: int = 5, reset_timeout: int = 60) -> pybreaker.CircuitBreaker:
    return pybreaker.CircuitBreaker(
        fail_max=fail_max,
        reset_timeout=reset_timeout,
        listeners=[CircuitBreakerListener()],
        name=name,
    )


redis_publish_breaker: pybreaker.CircuitBreaker = make_circuit_breaker("redis_publish")
email_breaker: pybreaker.CircuitBreaker = make_circuit_breaker("email_notifications")
database_breaker: pybreaker.CircuitBreaker = make_circuit_breaker("database")

ALL_BREAKERS: tuple[pybreaker.CircuitBreaker, ...] = (
    redis_publish_breaker,
    email_breaker,
    database_breaker,
)


def reset_all_breakers() -> None:
    for breaker in ALL_BREAKERS:
        breaker.close()
