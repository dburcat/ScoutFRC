"""
Sample tasks — used to verify Celery + Redis are working correctly.
Also provides the task dispatched by the /health/celery endpoint.
"""

import logging
import time
from typing import cast

from celery import Task
from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="tasks.ping",
    bind=True,
    queue="default",
    max_retries=3,
    default_retry_delay=5,
)
def _ping(self) -> dict:
    """Trivial round-trip task — returns broker timestamp."""
    logger.info("ping task executing (task_id=%s)", self.request.id)
    return {"status": "pong", "task_id": self.request.id, "timestamp": time.time()}

ping: Task = cast(Task, _ping)


@celery_app.task(
    name="tasks.add",
    bind=True,
    queue="default",
)
def _add(self, a: float, b: float) -> float:
    """Trivial arithmetic task used in integration tests."""
    logger.info("add(%s, %s) executing", a, b)
    return a + b

add: Task = cast(Task, _add)