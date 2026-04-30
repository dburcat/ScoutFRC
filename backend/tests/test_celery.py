"""
Integration tests for Celery task dispatch and result retrieval.

These tests run against a live Redis broker. They are skipped automatically
when Redis is not reachable (e.g. in offline CI environments).
"""

import pytest
from typing import cast
from celery import Task
from celery.result import AsyncResult
from app.celery_app import celery_app
from app.tasks.sample import ping, add


def _redis_available() -> bool:
    try:
        import redis as redis_lib  # type: ignore[import]
        r = redis_lib.from_url("redis://localhost:6379/0", socket_connect_timeout=2)
        r.ping()
        return True
    except Exception:
        return False


skip_no_redis = pytest.mark.skipif(
    not _redis_available(),
    reason="Redis not reachable — skipping Celery integration tests",
)

# Typed references so Pylance resolves .delay() / .get()
_ping: Task = cast(Task, ping)
_add: Task = cast(Task, add)


@skip_no_redis
def test_ping_task_dispatches_and_returns() -> None:
    """ping task should complete and return a pong response."""
    result: AsyncResult = _ping.delay()
    outcome: dict = result.get(timeout=15)  # type: ignore[assignment]

    assert outcome["status"] == "pong"
    assert "task_id" in outcome
    assert "timestamp" in outcome


@skip_no_redis
def test_add_task_returns_correct_sum() -> None:
    """add task should return the correct arithmetic result."""
    result: AsyncResult = _add.delay(3, 4)
    assert result.get(timeout=15) == 7  # type: ignore[misc]


@skip_no_redis
def test_celery_app_broker_connection() -> None:
    """Celery app should be able to connect to the Redis broker."""
    conn = celery_app.connection_for_write()
    conn.ensure_connection(max_retries=2)
    conn.release()


@skip_no_redis
def test_task_result_stored_in_backend() -> None:
    """Completed task result should be retrievable by task ID."""
    result: AsyncResult = _ping.delay()
    result.get(timeout=15)  # type: ignore[misc]

    stored = AsyncResult(result.id, app=celery_app)
    assert stored.state == "SUCCESS"
    assert stored.result["status"] == "pong"  # type: ignore[index]