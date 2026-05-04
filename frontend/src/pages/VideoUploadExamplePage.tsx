"""
Example integration of Phase 2 Tier 7 WebSocket in video upload flow.

This example demonstrates:
1. Uploading a match video
2. Monitoring real-time progress via WebSocket
3. Handling completion and errors
4. Displaying visual feedback

Copy this pattern to any component that needs task monitoring.
"""

import React, { useState } from "react";
import { useTaskProgress } from "@/hooks/useTaskProgress";
import { TaskProgressDisplay, TaskProgressBar } from "@/components/TaskProgressDisplay";
import api from "@/api/client";
import { Upload, CheckCircle, AlertCircle } from "lucide-react";

/**
 * VideoUploadPage Component
 *
 * Shows how to:
 * - Upload a video file
 * - Dispatch processing task
 * - Monitor progress in real-time
 * - Handle completion/errors
 */
export function VideoUploadPage() {
  const [matchId, setMatchId] = useState<number | null>(null);
  const [eventId, setEventId] = useState<string>("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<boolean>(false);

  // Connect to WebSocket for real-time progress
  const { isConnected, progress, error: wsError } = useTaskProgress(
    taskId,
    taskId !== null // Only connect if we have a task
  );

  /**
   * Handle file selection
   */
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;

    // Validate file type
    const validTypes = ["video/mp4", "video/quicktime", "video/x-msvideo", "video/x-matroska"];
    if (!validTypes.includes(selectedFile.type)) {
      setError(`Invalid file type: ${selectedFile.type}. Expected video file.`);
      return;
    }

    // Validate file size (max 2GB)
    const maxSize = 2 * 1024 * 1024 * 1024;
    if (selectedFile.size > maxSize) {
      setError(`File too large: ${selectedFile.size / (1024 * 1024 * 1024).toFixed(2)}GB`);
      return;
    }

    setFile(selectedFile);
    setError(null);
  };

  /**
   * Upload video and dispatch processing task
   */
  const handleUpload = async () => {
    if (!file || !matchId || !eventId) {
      setError("Please select match, event, and video file");
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(false);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("alliance_red", "254,1678,118");
      formData.append("alliance_blue", "1690,3476,2910");
      formData.append("event_id", eventId);

      const response = await api.post(
        `/matches/${matchId}/video`,
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );

      const { task_id } = response.data;
      console.log("Task created:", task_id);

      setTaskId(task_id);
      setFile(null);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to upload video";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Handle task completion
   */
  const handleTaskComplete = (result: unknown) => {
    console.log("Task completed!", result);
    setSuccess(true);
    setTaskId(null);
  };

  /**
   * Handle task error
   */
  const handleTaskError = (error: string) => {
    console.error("Task error:", error);
    setError(`Processing error: ${error}`);
    setTaskId(null);
  };

  /**
   * Reset form for another upload
   */
  const handleReset = () => {
    setTaskId(null);
    setFile(null);
    setError(null);
    setSuccess(false);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6">
      <div className="max-w-2xl mx-auto space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Upload className="w-8 h-8" />
            Match Video Upload & Processing
          </h1>
          <p className="text-slate-400 mt-2">
            Upload a match video to analyze robot movements in real-time
          </p>
        </div>

        {/* Progress Display (if task is active) */}
        {taskId ? (
          <div className="space-y-4">
            <TaskProgressDisplay
              taskId={taskId}
              enabled={true}
              onComplete={handleTaskComplete}
              onError={handleTaskError}
              showDetails={true}
              title="Processing Match Video"
            />

            {/* Summary */}
            <div className="bg-slate-900 border border-slate-700 rounded-lg p-4">
              <div className="text-sm text-slate-400 space-y-2">
                <div>
                  <span className="font-semibold">Status:</span>{" "}
                  {isConnected ? "🟢 Connected" : "🔴 Connecting..."}
                </div>
                <div>
                  <span className="font-semibold">Task ID:</span>{" "}
                  <code className="text-xs bg-slate-800 px-2 py-1 rounded">
                    {taskId.substring(0, 12)}...
                  </code>
                </div>
              </div>
            </div>

            {/* Reset Button */}
            <button
              onClick={handleReset}
              className="w-full py-2 bg-slate-700 hover:bg-slate-600 rounded"
            >
              ← Upload Another Video
            </button>
          </div>
        ) : success ? (
          /* Success State */
          <div className="space-y-4">
            <div className="bg-green-900/30 border border-green-700 rounded-lg p-6 text-center space-y-2">
              <CheckCircle className="w-12 h-12 text-green-400 mx-auto" />
              <h2 className="text-2xl font-bold text-green-400">
                Processing Complete!
              </h2>
              <p className="text-green-200">
                Movement tracks have been analyzed and saved
              </p>
            </div>

            <button
              onClick={handleReset}
              className="w-full py-3 bg-green-600 hover:bg-green-700 rounded font-semibold"
            >
              Upload Another Video
            </button>
          </div>
        ) : (
          /* Upload Form */
          <div className="space-y-4">
            {/* Match ID Input */}
            <div>
              <label className="block text-sm font-medium mb-2">Match ID *</label>
              <input
                type="number"
                value={matchId || ""}
                onChange={(e) => setMatchId(parseInt(e.target.value) || null)}
                placeholder="e.g., 123"
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-white"
              />
            </div>

            {/* Event ID Input */}
            <div>
              <label className="block text-sm font-medium mb-2">Event ID *</label>
              <input
                type="text"
                value={eventId}
                onChange={(e) => setEventId(e.target.value)}
                placeholder="e.g., 2024casj"
                className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-white"
              />
            </div>

            {/* File Upload */}
            <div>
              <label className="block text-sm font-medium mb-2">Video File *</label>
              <div className="border-2 border-dashed border-slate-700 rounded-lg p-6 text-center cursor-pointer hover:border-slate-500 transition">
                <input
                  type="file"
                  accept="video/*"
                  onChange={handleFileChange}
                  className="hidden"
                  id="video-upload"
                />
                <label htmlFor="video-upload" className="cursor-pointer block">
                  {file ? (
                    <div>
                      <CheckCircle className="w-8 h-8 text-green-400 mx-auto mb-2" />
                      <p className="font-semibold">{file.name}</p>
                      <p className="text-sm text-slate-400">
                        {(file.size / (1024 * 1024)).toFixed(1)} MB
                      </p>
                    </div>
                  ) : (
                    <div>
                      <Upload className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                      <p className="font-semibold">Click to select video</p>
                      <p className="text-sm text-slate-400">
                        or drag and drop (MP4, MOV, AVI, MKV)
                      </p>
                    </div>
                  )}
                </label>
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 flex gap-3">
                <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold text-red-400">Error</p>
                  <p className="text-sm text-red-200">{error}</p>
                </div>
              </div>
            )}

            {/* Upload Button */}
            <button
              onClick={handleUpload}
              disabled={!file || !matchId || !eventId || loading}
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:cursor-not-allowed rounded font-semibold transition"
            >
              {loading ? "Uploading..." : "Upload & Process"}
            </button>
          </div>
        )}

        {/* Info Box */}
        <div className="bg-slate-900 border border-slate-700 rounded-lg p-4 text-sm text-slate-300 space-y-2">
          <p className="font-semibold">ℹ️ How it works:</p>
          <ol className="list-decimal list-inside space-y-1">
            <li>Select a match and event</li>
            <li>Choose a match video file (MP4, MOV, AVI, MKV)</li>
            <li>Click "Upload & Process"</li>
            <li>Watch real-time progress updates via WebSocket</li>
            <li>See final results with movement tracks and statistics</li>
          </ol>
        </div>
      </div>
    </div>
  );
}

export default VideoUploadPage;
