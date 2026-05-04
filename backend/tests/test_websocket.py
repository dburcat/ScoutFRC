"""
Tests for WebSocket real-time task progress updates.

Tests connection management, message broadcasting, and task integration.
"""

import pytest
import asyncio
import json
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from app.main import app
from app.services.websocket_service import (
    WebSocketConnectionManager,
    TaskProgressUpdate,
    EventType,
)
from app.services.websocket_utils import emit_task_progress, emit_task_error


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


class TestWebSocketConnectionManager:
    """Test the WebSocket connection manager."""

    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe(self):
        """Test subscribing and unsubscribing connections."""
        manager = WebSocketConnectionManager()
        
        # Create mock websockets
        ws1 = MagicMock()
        ws2 = MagicMock()
        
        # Subscribe
        await manager.subscribe(ws1, "task-1")
        assert manager.get_active_task_count() == 1
        assert manager.get_active_connection_count() == 1
        
        # Subscribe another client to same task
        await manager.subscribe(ws2, "task-1")
        assert manager.get_active_connection_count() == 2
        
        # Unsubscribe one
        await manager.unsubscribe(ws1, "task-1")
        assert manager.get_active_connection_count() == 1
        
        # Unsubscribe other
        await manager.unsubscribe(ws2, "task-1")
        assert manager.get_active_task_count() == 0
        assert manager.get_active_connection_count() == 0

    @pytest.mark.asyncio
    async def test_disconnect_cleanup(self):
        """Test that disconnect cleans up all subscriptions."""
        manager = WebSocketConnectionManager()
        
        ws1 = MagicMock()
        
        # Subscribe to multiple tasks
        await manager.subscribe(ws1, "task-1")
        await manager.subscribe(ws1, "task-2")
        assert manager.get_active_task_count() == 2
        
        # Disconnect
        await manager.disconnect(ws1)
        assert manager.get_active_task_count() == 0
        assert manager.get_active_connection_count() == 0

    @pytest.mark.asyncio
    async def test_broadcast_task_progress(self):
        """Test broadcasting task progress updates."""
        manager = WebSocketConnectionManager()
        
        ws1 = MagicMock()
        ws2 = MagicMock()
        
        # Setup async mocks for send_text
        ws1.send_text = MagicMock(return_value=asyncio.sleep(0))
        ws2.send_text = MagicMock(return_value=asyncio.sleep(0))
        
        # Subscribe
        await manager.subscribe(ws1, "task-1")
        await manager.subscribe(ws2, "task-1")
        
        # Create and broadcast update
        update = TaskProgressUpdate(
            task_id="task-1",
            status="PROGRESS",
            current=50,
            total=100,
            stage="processing",
            percentage=50,
        )
        
        await manager.broadcast_task_progress(update)
        
        # Verify both clients received message
        assert ws1.send_text.call_count >= 1
        assert ws2.send_text.call_count >= 1

    @pytest.mark.asyncio
    async def test_broadcast_error(self):
        """Test broadcasting error messages."""
        manager = WebSocketConnectionManager()
        
        ws1 = MagicMock()
        ws1.send_text = MagicMock(return_value=asyncio.sleep(0))
        
        await manager.subscribe(ws1, "task-1")
        
        # Broadcast error
        await manager.broadcast_error("task-1", "Processing failed", "validation")
        
        # Verify error was sent
        assert ws1.send_text.call_count >= 1

    def test_task_progress_update_to_dict(self):
        """Test TaskProgressUpdate serialization."""
        update = TaskProgressUpdate(
            task_id="task-1",
            status="PROGRESS",
            current=25,
            total=100,
            stage="detecting",
            percentage=25,
            error=None,
        )
        
        data = update.to_dict()
        assert data["task_id"] == "task-1"
        assert data["percentage"] == 25
        assert data["stage"] == "detecting"
        assert "error" in data


class TestWebSocketUtilities:
    """Test WebSocket utility functions."""

    @pytest.mark.asyncio
    async def test_emit_task_progress(self):
        """Test emitting task progress."""
        with patch("app.services.websocket_utils.get_ws_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.broadcast_task_progress = MagicMock(
                return_value=asyncio.sleep(0)
            )
            mock_get_manager.return_value = mock_manager
            
            # Emit progress
            await emit_task_progress(
                task_id="task-1",
                status="PROGRESS",
                stage="processing",
                current=50,
                total=100,
            )
            
            # Verify broadcast was called
            assert mock_manager.broadcast_task_progress.called

    @pytest.mark.asyncio
    async def test_emit_task_error(self):
        """Test emitting task errors."""
        with patch("app.services.websocket_utils.get_ws_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.broadcast_error = MagicMock(return_value=asyncio.sleep(0))
            mock_get_manager.return_value = mock_manager
            
            # Emit error
            await emit_task_error(
                task_id="task-1",
                error_message="Test error",
                error_type="processing",
            )
            
            # Verify broadcast was called
            assert mock_manager.broadcast_error.called


class TestWebSocketEndpoint:
    """Test the WebSocket endpoint."""

    def test_websocket_endpoint_exists(self, client):
        """Test that WebSocket endpoint is available."""
        # Note: TestClient doesn't support WebSocket testing directly
        # This is a placeholder for integration tests using websockets library
        pass


# ── Integration test examples (requires asyncio test runner) ──────────────────

@pytest.mark.asyncio
async def test_full_task_progress_flow():
    """
    Integration test: task dispatching with WebSocket progress updates.
    
    This is a pseudo-code example of how the flow works:
    
    1. Client uploads video → task created
    2. Client connects to WebSocket: ws://localhost:8000/ws/tasks/task-id
    3. Backend starts processing, calls emit_task_progress_sync()
    4. emit_task_progress_sync() broadcasts to all connected clients
    5. Client receives updates in real-time
    6. Task completes, final update sent
    7. Client disconnects
    """
    # This would require a real WebSocket client library like websockets
    # Example with websockets library (not included in tests):
    
    # async with websockets.connect("ws://localhost:8000/ws/tasks/abc-123") as ws:
    #     # Receive messages
    #     msg = await ws.recv()
    #     data = json.loads(msg)
    #     assert data["type"] == "task_snapshot"
    #
    #     # Wait for progress updates
    #     for _ in range(10):
    #         msg = await ws.recv()
    #         data = json.loads(msg)
    #         assert data["type"] in ["task_progress", "task_complete"]
    
    pass
