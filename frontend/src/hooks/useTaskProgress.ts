import { useEffect, useState, useCallback, useRef } from "react";

/**
 * Task progress update event
 */
export interface TaskProgressUpdate {
  task_id: string;
  status: string;
  current: number;
  total: number;
  stage: string;
  percentage: number;
  result?: unknown;
  error?: string | null;
}

/**
 * WebSocket message from server
 */
export interface WebSocketMessage {
  type:
    | "task_progress"
    | "task_complete"
    | "task_failed"
    | "task_snapshot"
    | "error"
    | "pong"
    | "unsubscribed";
  data: unknown;
}

/**
 * Hook for connecting to WebSocket task progress updates
 *
 * @param taskId - The Celery task ID to monitor
 * @param enabled - Whether to connect (default: true)
 * @param includeSnapshot - Send current task status on connect (default: true)
 * @returns Object with connection state and current progress
 *
 * @example
 * ```tsx
 * const { isConnected, progress, error } = useTaskProgress("task-123", true);
 *
 * return (
 *   <div>
 *     {isConnected ? `Processing: ${progress?.percentage}%` : "Connecting..."}
 *     {error && <p>Error: {error}</p>}
 *   </div>
 * );
 * ```
 */
export function useTaskProgress(
  taskId: string | null,
  enabled: boolean = true,
  includeSnapshot: boolean = true
) {
  const [isConnected, setIsConnected] = useState(false);
  const [progress, setProgress] = useState<TaskProgressUpdate | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [taskSnapshot, setTaskSnapshot] = useState<unknown>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();

  const connect = useCallback(() => {
    if (!taskId || !enabled) {
      return;
    }

    try {
      // Determine WebSocket protocol and host
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = import.meta.env.VITE_API_URL?.replace(/^https?:\/\//, "") ||
        window.location.host;
      const baseUrl = `${protocol}//${host}`;
      const url = `${baseUrl}/ws/tasks/${taskId}?include_snapshot=${includeSnapshot}`;

      console.log(`[WebSocket] Connecting to ${url}`);
      const ws = new WebSocket(url);

      ws.onopen = () => {
        console.log(`[WebSocket] Connected to task ${taskId}`);
        setIsConnected(true);
        setError(null);
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);

          switch (message.type) {
            case "task_progress": {
              const data = message.data as TaskProgressUpdate;
              console.log(
                `[WebSocket] Progress: ${data.stage} ${data.percentage}%`
              );
              setProgress(data);
              break;
            }
            case "task_snapshot": {
              console.log("[WebSocket] Received task snapshot");
              setTaskSnapshot(message.data);
              break;
            }
            case "task_complete": {
              console.log("[WebSocket] Task completed");
              const data = message.data as TaskProgressUpdate;
              setProgress({
                ...data,
                status: "SUCCESS",
                percentage: 100,
              });
              break;
            }
            case "task_failed": {
              console.log("[WebSocket] Task failed");
              const data = message.data as TaskProgressUpdate;
              setProgress({
                ...data,
                status: "FAILURE",
              });
              setError(data.error || "Task failed");
              break;
            }
            case "error": {
              const errorData = message.data as { error: string };
              console.error("[WebSocket] Error:", errorData.error);
              setError(errorData.error);
              break;
            }
            case "pong": {
              // Keepalive response
              console.debug("[WebSocket] Received pong");
              break;
            }
            default:
              console.debug("[WebSocket] Unknown message type:", message.type);
          }
        } catch (err) {
          console.error("[WebSocket] Error parsing message:", err);
          setError("Failed to parse WebSocket message");
        }
      };

      ws.onerror = (event) => {
        console.error("[WebSocket] WebSocket error:", event);
        setError("WebSocket connection error");
        setIsConnected(false);
      };

      ws.onclose = () => {
        console.log("[WebSocket] Connection closed");
        setIsConnected(false);
        wsRef.current = null;

        // Attempt reconnection after delay
        if (enabled && taskId) {
          console.log("[WebSocket] Scheduling reconnection...");
          reconnectTimeoutRef.current = setTimeout(connect, 3000);
        }
      };

      wsRef.current = ws;
    } catch (err) {
      console.error("[WebSocket] Connection error:", err);
      setError(`Connection error: ${err instanceof Error ? err.message : String(err)}`);
      setIsConnected(false);
    }
  }, [taskId, enabled, includeSnapshot]);

  // Setup connection on mount or when deps change
  useEffect(() => {
    if (!enabled || !taskId) {
      // Clean up if disabled
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      return;
    }

    connect();

    return () => {
      // Cleanup on unmount
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [taskId, enabled, connect]);

  /**
   * Send a ping to the server to verify connection is alive
   */
  const sendPing = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ command: "ping" }));
    }
  }, []);

  /**
   * Unsubscribe from task updates
   */
  const unsubscribe = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ command: "unsubscribe" }));
    }
  }, []);

  /**
   * Request current task status
   */
  const requestStatus = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ command: "status" }));
    }
  }, []);

  /**
   * Force reconnection
   */
  const reconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    connect();
  }, [connect]);

  return {
    isConnected,
    progress,
    error,
    taskSnapshot,
    sendPing,
    unsubscribe,
    requestStatus,
    reconnect,
  };
}
