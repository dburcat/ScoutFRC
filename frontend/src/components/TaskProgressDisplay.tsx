import React from "react";
import { useTaskProgress, TaskProgressUpdate } from "@/hooks/useTaskProgress";
import { AlertCircle, CheckCircle, Loader, X } from "lucide-react";

interface TaskProgressDisplayProps {
  taskId: string | null;
  enabled?: boolean;
  onComplete?: (result: unknown) => void;
  onError?: (error: string) => void;
  showDetails?: boolean;
  title?: string;
}

/**
 * Displays real-time task progress with visual feedback
 *
 * Shows progress bar, current stage, and status updates as task progresses.
 *
 * @param taskId - Celery task ID to monitor (null to disable)
 * @param enabled - Whether to connect (default: true)
 * @param onComplete - Callback when task succeeds
 * @param onError - Callback when task fails
 * @param showDetails - Show detailed progress info (default: false)
 * @param title - Optional title/label for the task
 */
export function TaskProgressDisplay({
  taskId,
  enabled = true,
  onComplete,
  onError,
  showDetails = false,
  title = "Processing",
}: TaskProgressDisplayProps) {
  const { isConnected, progress, error } = useTaskProgress(taskId, enabled);

  // Call callbacks when status changes
  React.useEffect(() => {
    if (progress?.status === "SUCCESS" && onComplete) {
      onComplete(progress.result);
    }
  }, [progress?.status, progress?.result, onComplete]);

  React.useEffect(() => {
    if (error && onError) {
      onError(error);
    }
  }, [error, onError]);

  if (!enabled || !taskId) {
    return null;
  }

  const isComplete = progress?.status === "SUCCESS";
  const isFailed = progress?.status === "FAILURE" || error;
  const isProcessing =
    progress?.status === "PROGRESS" || progress?.status === "STARTED";
  const isPending = progress?.status === "PENDING" || !isConnected;

  const percentage = progress?.percentage || 0;
  const stage = progress?.stage || "initializing";

  return (
    <div className="w-full bg-slate-900 border border-slate-700 rounded-lg p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isComplete && <CheckCircle className="w-5 h-5 text-green-400" />}
          {isFailed && <AlertCircle className="w-5 h-5 text-red-400" />}
          {(isProcessing || isPending) && (
            <Loader className="w-5 h-5 text-blue-400 animate-spin" />
          )}
          <span className="text-sm font-medium text-slate-100">{title}</span>
        </div>
        <span
          className={`text-xs font-mono ${
            isComplete
              ? "text-green-400"
              : isFailed
                ? "text-red-400"
                : "text-slate-400"
          }`}
        >
          {isComplete ? "Complete" : isFailed ? "Failed" : "Processing"}
        </span>
      </div>

      {/* Progress bar */}
      <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${
            isComplete
              ? "bg-green-500"
              : isFailed
                ? "bg-red-500"
                : "bg-blue-500"
          }`}
          style={{ width: `${percentage}%` }}
        />
      </div>

      {/* Status text */}
      <div className="flex items-center justify-between text-xs text-slate-400">
        <span className="capitalize">{stage}</span>
        <span className="font-mono">
          {progress?.current || 0} / {progress?.total || 0}
        </span>
      </div>

      {/* Percentage */}
      <div className="text-right text-sm font-bold text-slate-200">
        {percentage}%
      </div>

      {/* Error message */}
      {error && (
        <div className="mt-2 p-2 bg-red-900/30 border border-red-700/50 rounded text-xs text-red-200">
          {error}
        </div>
      )}

      {/* Detailed info */}
      {showDetails && progress && (
        <div className="mt-3 p-2 bg-slate-800/50 rounded text-xs text-slate-300 space-y-1 font-mono">
          <div>Stage: {progress.stage}</div>
          <div>Status: {progress.status}</div>
          {progress.result && (
            <div>Result: {JSON.stringify(progress.result).substring(0, 50)}...</div>
          )}
        </div>
      )}

      {/* Connection indicator */}
      {!isConnected && !isComplete && !isFailed && (
        <div className="text-xs text-yellow-400 text-center">
          {isPending ? "Waiting for server..." : "Reconnecting..."}
        </div>
      )}
    </div>
  );
}

/**
 * Lightweight progress indicator (compact version)
 *
 * Shows just the progress bar and percentage, useful for inline display
 */
export function TaskProgressBar({
  taskId,
  enabled = true,
  compact = false,
}: {
  taskId: string | null;
  enabled?: boolean;
  compact?: boolean;
}) {
  const { progress, error } = useTaskProgress(taskId, enabled);

  if (!enabled || !taskId) {
    return null;
  }

  const percentage = progress?.percentage || 0;

  if (compact) {
    return (
      <div className="flex items-center gap-2">
        <div className="flex-1 bg-slate-800 rounded-full h-1.5 overflow-hidden">
          <div
            className="h-full bg-blue-500 transition-all duration-300"
            style={{ width: `${percentage}%` }}
          />
        </div>
        <span className="text-xs font-mono text-slate-400 min-w-10">
          {percentage}%
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-400">{progress?.stage || "initializing"}</span>
        <span className="font-bold text-slate-200">{percentage}%</span>
      </div>
      <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
        <div
          className="h-full bg-blue-500 transition-all duration-300"
          style={{ width: `${percentage}%` }}
        />
      </div>
      {error && <div className="text-xs text-red-400">{error}</div>}
    </div>
  );
}
