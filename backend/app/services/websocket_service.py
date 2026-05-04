"""
WebSocket connection management and broadcasting service.

Handles concurrent WebSocket connections, task progress subscriptions,
and broadcasting real-time updates to connected clients.
"""

from typing import Dict, Set, Callable, Any
import json
import asyncio
from dataclasses import dataclass
from enum import Enum

from fastapi import WebSocket
from celery.result import AsyncResult


class EventType(str, Enum):
    """WebSocket event types for real-time updates."""
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETE = "task_complete"
    TASK_FAILED = "task_failed"
    DATA_UPDATE = "data_update"
    ERROR = "error"


@dataclass
class TaskProgressUpdate:
    """Task progress event payload."""
    task_id: str
    status: str  # PENDING, STARTED, PROGRESS, SUCCESS, FAILURE
    current: int
    total: int
    stage: str
    percentage: int
    result: Any = None
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "current": self.current,
            "total": self.total,
            "stage": self.stage,
            "percentage": self.percentage,
            "result": self.result,
            "error": self.error,
        }


class WebSocketConnectionManager:
    """
    Manages WebSocket connections and broadcasts updates.
    
    Thread-safe with asyncio support for multiple concurrent connections.
    """

    def __init__(self):
        # task_id -> set of connected clients
        self._task_subscriptions: Dict[str, Set[WebSocket]] = {}
        # connection -> set of subscribed task_ids
        self._connection_subscriptions: Dict[WebSocket, Set[str]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, websocket: WebSocket, task_id: str) -> None:
        """
        Subscribe a WebSocket connection to task progress updates.
        
        Args:
            websocket: The connected WebSocket
            task_id: The Celery task ID to subscribe to
        """
        async with self._lock:
            if task_id not in self._task_subscriptions:
                self._task_subscriptions[task_id] = set()
            self._task_subscriptions[task_id].add(websocket)

            if websocket not in self._connection_subscriptions:
                self._connection_subscriptions[websocket] = set()
            self._connection_subscriptions[websocket].add(task_id)

    async def unsubscribe(self, websocket: WebSocket, task_id: str) -> None:
        """
        Unsubscribe a connection from a task's progress updates.
        
        Args:
            websocket: The WebSocket connection
            task_id: The task ID to unsubscribe from
        """
        async with self._lock:
            if task_id in self._task_subscriptions:
                self._task_subscriptions[task_id].discard(websocket)
                if not self._task_subscriptions[task_id]:
                    del self._task_subscriptions[task_id]

            if websocket in self._connection_subscriptions:
                self._connection_subscriptions[websocket].discard(task_id)

    async def disconnect(self, websocket: WebSocket) -> None:
        """
        Disconnect a WebSocket and clean up all subscriptions.
        
        Args:
            websocket: The WebSocket connection to disconnect
        """
        async with self._lock:
            if websocket in self._connection_subscriptions:
                task_ids = self._connection_subscriptions[websocket].copy()
                for task_id in task_ids:
                    if task_id in self._task_subscriptions:
                        self._task_subscriptions[task_id].discard(websocket)
                        if not self._task_subscriptions[task_id]:
                            del self._task_subscriptions[task_id]
                del self._connection_subscriptions[websocket]

    async def broadcast_task_progress(self, update: TaskProgressUpdate) -> None:
        """
        Broadcast a task progress update to all subscribed clients.
        
        Args:
            update: The TaskProgressUpdate to broadcast
        """
        if update.task_id not in self._task_subscriptions:
            return

        disconnected = set()
        payload = {
            "type": EventType.TASK_PROGRESS,
            "data": update.to_dict(),
        }
        message = json.dumps(payload)

        # Broadcast to all subscribed connections (non-blocking, collect failures)
        for websocket in list(self._task_subscriptions[update.task_id]):
            try:
                await websocket.send_text(message)
            except Exception:
                # Connection likely closed, mark for cleanup
                disconnected.add(websocket)

        # Cleanup disconnected clients
        for websocket in disconnected:
            await self.disconnect(websocket)

    async def broadcast_error(
        self, 
        task_id: str, 
        error_message: str,
        error_type: str = "general"
    ) -> None:
        """
        Broadcast an error message to all subscribers of a task.
        
        Args:
            task_id: The task ID
            error_message: Error message to broadcast
            error_type: Type of error (e.g., "validation", "processing", "general")
        """
        if task_id not in self._task_subscriptions:
            return

        disconnected = set()
        payload = {
            "type": EventType.ERROR,
            "data": {
                "task_id": task_id,
                "error": error_message,
                "error_type": error_type,
            },
        }
        message = json.dumps(payload)

        for websocket in list(self._task_subscriptions[task_id]):
            try:
                await websocket.send_text(message)
            except Exception:
                disconnected.add(websocket)

        for websocket in disconnected:
            await self.disconnect(websocket)

    def get_active_task_count(self) -> int:
        """Get the number of actively monitored tasks."""
        return len(self._task_subscriptions)

    def get_active_connection_count(self) -> int:
        """Get the number of active WebSocket connections."""
        return len(self._connection_subscriptions)

    async def get_task_status_snapshot(self, task_id: str) -> dict | None:
        """
        Get the current Celery task status snapshot.
        
        Args:
            task_id: The Celery task ID
            
        Returns:
            Dictionary with task info or None if task not found
        """
        result = AsyncResult(task_id)
        if result.state == "PENDING":
            return None

        return {
            "task_id": task_id,
            "state": result.state,
            "result": result.result if result.successful() else None,
            "info": result.info if result.state == "PROGRESS" else None,
            "error": str(result.info) if result.failed() else None,
        }


# Global instance
_ws_manager: WebSocketConnectionManager | None = None


def get_ws_manager() -> WebSocketConnectionManager:
    """Get or initialize the global WebSocket manager."""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketConnectionManager()
    return _ws_manager
