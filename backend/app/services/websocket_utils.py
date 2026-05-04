"""
Utilities for broadcasting task progress updates via WebSocket.

Tasks should use emit_task_progress() to send real-time updates to connected clients.
"""

import asyncio
from typing import Any, Optional
from app.services.websocket_service import get_ws_manager, TaskProgressUpdate


async def emit_task_progress(
    task_id: str,
    status: str,
    stage: str,
    current: int,
    total: int,
    result: Any = None,
    error: Optional[str] = None,
) -> None:
    """
    Emit a task progress update to all subscribed WebSocket clients.
    
    This is typically called from within a Celery task to provide real-time
    feedback on processing progress.
    
    Args:
        task_id: The Celery task ID
        status: Task status (PENDING, STARTED, PROGRESS, SUCCESS, FAILURE)
        stage: Current processing stage (e.g., "detecting", "tracking", "identifying")
        current: Current progress count
        total: Total work items
        result: Result data if task completed
        error: Error message if task failed
    
    Example:
        ```python
        @celery_app.task(bind=True)
        def my_task(self):
            total_items = 100
            for i in range(total_items):
                # Process item i
                await emit_task_progress(
                    task_id=self.request.id,
                    status="PROGRESS",
                    stage="processing",
                    current=i+1,
                    total=total_items,
                )
        ```
    """
    try:
        # Calculate percentage
        percentage = int((current / total * 100)) if total > 0 else 0

        # Create update
        update = TaskProgressUpdate(
            task_id=task_id,
            status=status,
            current=current,
            total=total,
            stage=stage,
            percentage=percentage,
            result=result,
            error=error,
        )

        # Get manager and broadcast
        manager = get_ws_manager()
        await manager.broadcast_task_progress(update)

    except Exception as exc:
        # Log but don't raise - we don't want WebSocket errors to break task processing
        print(f"Error broadcasting task progress for {task_id}: {exc}")


def emit_task_progress_sync(
    task_id: str,
    status: str,
    stage: str,
    current: int,
    total: int,
    result: Any = None,
    error: Optional[str] = None,
) -> None:
    """
    Synchronous wrapper for emit_task_progress.
    
    For use in synchronous Celery tasks or contexts where we need to emit
    progress but can't await async functions directly.
    
    Creates a new event loop if needed and runs the async emission.
    
    Args:
        See emit_task_progress for parameter documentation
    """
    try:
        # Try to get running loop first
        try:
            loop = asyncio.get_running_loop()
            # If we get here, we're already in an async context
            # Create a task but don't await it (fire-and-forget)
            asyncio.create_task(
                emit_task_progress(task_id, status, stage, current, total, result, error)
            )
        except RuntimeError:
            # No running loop, create a new one
            asyncio.run(
                emit_task_progress(task_id, status, stage, current, total, result, error)
            )
    except Exception as exc:
        print(f"Error in emit_task_progress_sync: {exc}")


async def emit_task_error(
    task_id: str,
    error_message: str,
    error_type: str = "processing",
) -> None:
    """
    Emit an error message to all subscribed clients for a task.
    
    Args:
        task_id: The Celery task ID
        error_message: Human-readable error message
        error_type: Type of error (e.g., "validation", "processing", "general")
    """
    try:
        manager = get_ws_manager()
        await manager.broadcast_error(task_id, error_message, error_type)
    except Exception as exc:
        print(f"Error broadcasting task error for {task_id}: {exc}")
