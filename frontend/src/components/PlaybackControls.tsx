import React, { useState, useEffect } from "react";
import { Play, Pause, SkipBack, SkipForward, Volume2 } from "lucide-react";

/**
 * Playback Controls Component
 *
 * Controls for replaying robot movement trajectories:
 * - Play/pause
 * - Scrubber (seek to frame)
 * - Speed control
 * - Phase filter (auto/teleop/endgame)
 */

export interface PlaybackPhase {
  name: "auto" | "teleop" | "endgame";
  label: string;
  startTime: number;
  endTime: number;
}

interface PlaybackControlsProps {
  totalFrames: number;
  currentFrame: number;
  isPlaying: boolean;
  speed: number;
  phases?: PlaybackPhase[];
  onPlay: () => void;
  onPause: () => void;
  onSeek: (frame: number) => void;
  onSpeedChange: (speed: number) => void;
  onPhaseChange?: (phase: string) => void;
  fps?: number;
}

export function PlaybackControls({
  totalFrames,
  currentFrame,
  isPlaying,
  speed,
  phases = [
    { name: "auto", label: "Auto", startTime: 0, endTime: 15 },
    { name: "teleop", label: "Teleop", startTime: 15, endTime: 135 },
    { name: "endgame", label: "Endgame", startTime: 135, endTime: 150 },
  ],
  onPlay,
  onPause,
  onSeek,
  onSpeedChange,
  onPhaseChange,
  fps = 30,
}: PlaybackControlsProps) {
  const [selectedPhase, setSelectedPhase] = useState<string>("all");

  const handlePhaseChange = (phase: string) => {
    setSelectedPhase(phase);
    onPhaseChange?.(phase);
  };

  // Convert frame to time
  const timeSeconds = (currentFrame / fps).toFixed(1);
  const totalSeconds = (totalFrames / fps).toFixed(1);

  const handleProgressChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const frame = parseInt(e.target.value);
    onSeek(frame);
  };

  const handleSpeedChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onSpeedChange(parseFloat(e.target.value));
  };

  const handlePrevFrame = () => {
    onSeek(Math.max(0, currentFrame - 1));
  };

  const handleNextFrame = () => {
    onSeek(Math.min(totalFrames - 1, currentFrame + 1));
  };

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-lg p-4 space-y-4">
      {/* Main Controls */}
      <div className="flex items-center gap-4">
        {/* Play/Pause */}
        <button
          onClick={isPlaying ? onPause : onPlay}
          className="p-2 bg-blue-600 hover:bg-blue-700 rounded-full transition"
          title={isPlaying ? "Pause" : "Play"}
        >
          {isPlaying ? (
            <Pause className="w-5 h-5" />
          ) : (
            <Play className="w-5 h-5" />
          )}
        </button>

        {/* Frame Step */}
        <button
          onClick={handlePrevFrame}
          className="p-2 bg-slate-800 hover:bg-slate-700 rounded"
          title="Previous frame"
        >
          <SkipBack className="w-4 h-4" />
        </button>

        <button
          onClick={handleNextFrame}
          className="p-2 bg-slate-800 hover:bg-slate-700 rounded"
          title="Next frame"
        >
          <SkipForward className="w-4 h-4" />
        </button>

        {/* Time Display */}
        <div className="text-sm font-mono text-slate-300">
          {timeSeconds}s / {totalSeconds}s
        </div>

        {/* Speed Control */}
        <select
          value={speed}
          onChange={handleSpeedChange}
          className="px-2 py-1 bg-slate-800 border border-slate-700 rounded text-xs"
          title="Playback speed"
        >
          <option value={0.5}>0.5x</option>
          <option value={1}>1x</option>
          <option value={1.5}>1.5x</option>
          <option value={2}>2x</option>
          <option value={4}>4x</option>
        </select>
      </div>

      {/* Progress Bar */}
      <div className="space-y-1">
        <input
          type="range"
          min="0"
          max={totalFrames - 1}
          value={currentFrame}
          onChange={handleProgressChange}
          className="w-full h-2 bg-slate-800 rounded-full appearance-none cursor-pointer"
          style={{
            background: `linear-gradient(to right, #3b82f6 0%, #3b82f6 ${
              (currentFrame / totalFrames) * 100
            }%, #1e293b ${(currentFrame / totalFrames) * 100}%, #1e293b 100%)`,
          }}
        />
        <div className="flex justify-between text-xs text-slate-500">
          <span>0%</span>
          <span>{((currentFrame / totalFrames) * 100).toFixed(0)}%</span>
          <span>100%</span>
        </div>
      </div>

      {/* Phase Filter */}
      <div className="space-y-2">
        <label className="text-xs font-semibold text-slate-400">Filter by Phase</label>
        <div className="flex gap-2">
          <button
            onClick={() => handlePhaseChange("all")}
            className={`px-3 py-1 text-xs rounded transition ${
              selectedPhase === "all"
                ? "bg-blue-600 text-white"
                : "bg-slate-800 text-slate-300 hover:bg-slate-700"
            }`}
          >
            All
          </button>
          {phases.map((phase) => (
            <button
              key={phase.name}
              onClick={() => handlePhaseChange(phase.name)}
              className={`px-3 py-1 text-xs rounded transition ${
                selectedPhase === phase.name
                  ? "bg-blue-600 text-white"
                  : "bg-slate-800 text-slate-300 hover:bg-slate-700"
              }`}
            >
              {phase.label}
            </button>
          ))}
        </div>
      </div>

      {/* Info */}
      <div className="text-xs text-slate-500 space-y-1">
        <div>Frame: {currentFrame} / {totalFrames}</div>
        <div>Speed: {speed}x</div>
      </div>
    </div>
  );
}

/**
 * Compact playback bar (inline variant)
 */
export function PlaybackBar({
  totalFrames,
  currentFrame,
  isPlaying,
  onSeek,
}: {
  totalFrames: number;
  currentFrame: number;
  isPlaying: boolean;
  onSeek: (frame: number) => void;
}) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onSeek(parseInt(e.target.value));
  };

  const percentage = (currentFrame / totalFrames) * 100;

  return (
    <div className="flex items-center gap-2">
      <input
        type="range"
        min="0"
        max={totalFrames - 1}
        value={currentFrame}
        onChange={handleChange}
        className="flex-1 h-1 bg-slate-800 rounded-full appearance-none cursor-pointer"
        style={{
          background: `linear-gradient(to right, #3b82f6 0%, #3b82f6 ${percentage}%, #1e293b ${percentage}%, #1e293b 100%)`,
        }}
      />
      <span className="text-xs font-mono text-slate-400 min-w-12">
        {percentage.toFixed(0)}%
      </span>
    </div>
  );
}
