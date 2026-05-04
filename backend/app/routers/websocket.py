"""
WebSocket endpoint for real-time task progress and updates.

GET /ws/tasks/{task_id}  — WebSocket connection for task progress updates
"""

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status, Query
from app.services.websocket_service import get_ws_manager, TaskProgressUpdate

websocket_router = APIRouter(tags=["websocket"])


@websocket_router.websocket("/ws/tasks/{task_id}")
async def websocket_task_progress(
    websocket: WebSocket,
    task_id: str,
    include_snapshot: bool = Query(True, description="Send current task status on connect")
):
    """
    WebSocket endpoint for real-time task progress updates.
    
    **Parameters:**
    - `task_id`: Celery task ID to monitor
    - `include_snapshot`: If true, send current task status immediately (default: true)
    
    **Events received:**
    - `task_progress`: Task state changed with progress info
    - `task_complete`: Task finished successfully
    - `task_failed`: Task failed with error
    - `error`: WebSocket or processing error
    
    **Example client:**
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/ws/tasks/abc-def-123');
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      console.log(msg.type, msg.data);
    };
    ```
    """
    await websocket.accept()
    manager = get_ws_manager()

    try:
        # Subscribe to task updates
        await manager.subscribe(websocket, task_id)

        # Send current task status snapshot if requested
        if include_snapshot:
            snapshot = await manager.get_task_status_snapshot(task_id)
            if snapshot:
                payload = {
                    "type": "task_snapshot",
                    "data": snapshot,
                }
                await websocket.send_json(payload)
            else:
                # Task not found or pending
                payload = {
                    "type": "task_snapshot",
                    "data": {
                        "task_id": task_id,
                        "state": "PENDING",
                        "message": "Task pending or not found",
                    },
                }
                await websocket.send_json(payload)

        # Keep connection alive and process incoming messages
        while True:
            # This will block until a message is received or connection closes
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                command = msg.get("command")

                # Handle client commands
                if command == "ping":
                    # Echo ping for keepalive checks
                    await websocket.send_json({"type": "pong"})
                elif command == "unsubscribe":
                    # Client explicitly unsubscribes from task
                    await manager.unsubscribe(websocket, task_id)
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "data": {"task_id": task_id}
                    })
                elif command == "status":
                    # Client requests current status snapshot
                    snapshot = await manager.get_task_status_snapshot(task_id)
                    await websocket.send_json({
                        "type": "task_snapshot",
                        "data": snapshot or {"task_id": task_id, "state": "UNKNOWN"}
                    })
                else:
                    # Unknown command
                    await websocket.send_json({
                        "type": "error",
                        "data": {"error": f"Unknown command: {command}"}
                    })
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "data": {"error": "Invalid JSON in message"}
                })

    except WebSocketDisconnect:
        # Client disconnected cleanly
        await manager.disconnect(websocket)
    except Exception as exc:
        # Unexpected error
        try:
            await websocket.send_json({
                "type": "error",
                "data": {"error": f"Server error: {str(exc)}"}
            })
        except Exception:
            pass  # Connection already closed
        finally:
            await manager.disconnect(websocket)
            await websocket.close(code=status.WS_1011_SERVER_ERROR)
