#!/usr/bin/env python3
"""
Manual WebSocket client for testing Phase 2 Tier 7 real-time updates.

Usage:
    python scripts/test_websocket_client.py --task-id abc-123-def
    python scripts/test_websocket_client.py --task-id abc-123-def --verbose
    python scripts/test_websocket_client.py --task-id abc-123-def --duration 30
"""

import asyncio
import json
import argparse
import sys
from datetime import datetime
from typing import Optional

try:
    import websockets
except ImportError:
    print("❌ websockets library not found")
    print("Install with: pip install websockets")
    sys.exit(1)


class WebSocketClient:
    """Simple WebSocket client for testing task progress."""

    def __init__(
        self,
        task_id: str,
        host: str = "localhost",
        port: int = 8000,
        verbose: bool = False,
        duration: Optional[int] = None,
    ):
        self.task_id = task_id
        self.url = f"ws://{host}:{port}/ws/tasks/{task_id}"
        self.verbose = verbose
        self.duration = duration
        self.start_time = datetime.now()
        self.message_count = 0
        self.last_percentage = 0

    def log(self, msg: str, level: str = "INFO"):
        """Log message with timestamp."""
        now = datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] [{level}] {msg}")

    async def connect_and_listen(self):
        """Connect to WebSocket and listen for messages."""
        self.log(f"Connecting to {self.url}")

        try:
            async with websockets.connect(self.url) as ws:
                self.log("✅ Connected", "SUCCESS")

                while True:
                    # Check timeout
                    if self.duration:
                        elapsed = (datetime.now() - self.start_time).total_seconds()
                        if elapsed > self.duration:
                            self.log(f"Timeout reached ({self.duration}s)", "WARN")
                            break

                    try:
                        # Receive message with timeout
                        try:
                            msg_text = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        except asyncio.TimeoutError:
                            self.log("No message received (5s timeout)", "DEBUG")
                            # Send keepalive ping
                            await ws.send(json.dumps({"command": "ping"}))
                            continue

                        # Parse message
                        try:
                            msg = json.loads(msg_text)
                        except json.JSONDecodeError:
                            self.log(f"Invalid JSON: {msg_text[:100]}", "ERROR")
                            continue

                        self.message_count += 1
                        await self.handle_message(msg)

                    except websockets.exceptions.ConnectionClosed:
                        self.log("Connection closed by server", "WARN")
                        break

        except Exception as exc:
            self.log(f"Connection error: {exc}", "ERROR")

    async def handle_message(self, msg: dict):
        """Handle incoming message."""
        msg_type = msg.get("type")
        data = msg.get("data", {})

        if msg_type == "task_snapshot":
            self.log(
                f"📸 Snapshot: state={data.get('state')}, "
                f"message={data.get('message')}",
                "INFO",
            )

        elif msg_type == "task_progress":
            percentage = data.get("percentage", 0)
            stage = data.get("stage", "unknown")
            current = data.get("current", 0)
            total = data.get("total", 0)

            # Progress bar
            bar_length = 30
            filled = int(bar_length * percentage / 100)
            bar = "█" * filled + "░" * (bar_length - filled)

            # Only log every 5% change to reduce noise
            if percentage % 5 == 0 and percentage != self.last_percentage:
                self.log(
                    f"⏳ {bar} {percentage}% | {stage} ({current}/{total})",
                    "PROGRESS",
                )
                self.last_percentage = percentage

            if self.verbose:
                self.log(f"   Full data: {json.dumps(data, indent=2)}", "DEBUG")

        elif msg_type == "task_complete":
            percentage = data.get("percentage", 0)
            result = data.get("result")
            self.log(f"✅ Task complete: {percentage}%", "SUCCESS")
            if result and self.verbose:
                self.log(f"   Result: {json.dumps(result, indent=2)}", "DEBUG")

        elif msg_type == "task_failed":
            error = data.get("error", "Unknown error")
            self.log(f"❌ Task failed: {error}", "ERROR")
            if self.verbose:
                self.log(f"   Full data: {json.dumps(data, indent=2)}", "DEBUG")

        elif msg_type == "error":
            error = data.get("error", "Unknown error")
            error_type = data.get("error_type", "general")
            self.log(f"⚠️  Error ({error_type}): {error}", "ERROR")

        elif msg_type == "pong":
            if self.verbose:
                self.log("🏓 Pong received", "DEBUG")

        else:
            self.log(f"Unknown message type: {msg_type}", "WARN")
            if self.verbose:
                self.log(f"   Data: {json.dumps(data, indent=2)}", "DEBUG")

    async def run(self):
        """Run the client."""
        try:
            await self.connect_and_listen()
        except KeyboardInterrupt:
            self.log("Interrupted by user", "WARN")
        finally:
            elapsed = (datetime.now() - self.start_time).total_seconds()
            self.log(
                f"Disconnected. Messages received: {self.message_count}, "
                f"Duration: {elapsed:.1f}s",
                "INFO",
            )


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="WebSocket client for testing task progress",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --task-id abc-123-def
  %(prog)s --task-id abc-123-def --verbose
  %(prog)s --task-id abc-123-def --duration 60 --host 192.168.1.100
        """,
    )

    parser.add_argument(
        "--task-id",
        required=True,
        help="Celery task ID to monitor",
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="WebSocket server host (default: localhost)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="WebSocket server port (default: 8000)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--duration",
        type=int,
        help="Max duration in seconds (default: unlimited)",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("🔌 WebSocket Task Progress Monitor")
    print("=" * 60)
    print()

    client = WebSocketClient(
        task_id=args.task_id,
        host=args.host,
        port=args.port,
        verbose=args.verbose,
        duration=args.duration,
    )

    await client.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"Fatal error: {exc}", file=sys.stderr)
        sys.exit(1)
