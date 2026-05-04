import React, { useState, useEffect, useCallback, useRef } from "react";
import { AlertCircle, Download } from "lucide-react";
import htmlToCanvas from "html2canvas";
import { FieldDiagram, FieldLayout } from "../components/FieldDiagram";
import { HeatmapOverlay, HeatmapLegend, HeatmapBin } from "../components/Heatmap";
import { PlaybackControls } from "../components/PlaybackControls";
import { useParams } from "react-router-dom";

/**
 * Match Visualization Page
 *
 * Comprehensive visualization of robot movement, trajectories, and heatmaps:
 * - Field diagram with trajectory overlays
 * - Spatial heatmap showing movement concentration
 * - Playback controls for replaying movement
 * - Phase filtering (auto/teleop/endgame)
 * - Team selection and export
 */

interface TeamTrajectory {
  team_id: number;
  alliance: "red" | "blue";
  coordinates: Array<[number, number]>;
  stats: {
    total_points: number;
    distance_traveled: number;
  };
}

interface MatchTrajectoriesResponse {
  match_id: number;
  teams: Record<number, TeamTrajectory>;
  field_width: number;
  field_height: number;
}

interface MatchHeatmapResponse {
  match_id: number;
  field_width: number;
  field_height: number;
  bins: HeatmapBin[];
  max_intensity: number;
  total_points: number;
}

export function MatchVisualizationPage() {
  const { matchId } = useParams<{ matchId: string }>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Data
  const [trajectories, setTrajectories] = useState<MatchTrajectoriesResponse | null>(null);
  const [heatmapData, setHeatmapData] = useState<MatchHeatmapResponse | null>(null);
  const [fieldLayout, setFieldLayout] = useState<FieldLayout | null>(null);

  // UI State
  const [selectedTeam, setSelectedTeam] = useState<number | null>(null);
  const [currentPhase, setCurrentPhase] = useState<string>("all");
  const [colorScheme, setColorScheme] = useState<"hot" | "cool" | "viridis">("hot");

  // Playback State
  const [currentFrame, setCurrentFrame] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const FPS = 30;

  // Load data
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);

        const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";

        // Load trajectories
        const trajRes = await fetch(
          `${baseUrl}/matches/${matchId}/trajectories?phase=${currentPhase}`,
          {
            headers: {
              Authorization: `Bearer ${localStorage.getItem("token")}`,
            },
          }
        );

        if (!trajRes.ok) throw new Error("Failed to load trajectories");
        const trajData = await trajRes.json();
        setTrajectories(trajData);

        // Load heatmap
        const heatmapRes = await fetch(
          `${baseUrl}/matches/${matchId}/heatmap?phase=${currentPhase}`,
          {
            headers: {
              Authorization: `Bearer ${localStorage.getItem("token")}`,
            },
          }
        );

        if (!heatmapRes.ok) throw new Error("Failed to load heatmap");
        const heatmapResData = await heatmapRes.json();
        setHeatmapData(heatmapResData);

        // Load field layout
        const fieldRes = await fetch(
          `${baseUrl}/matches/${matchId}/field-layout`,
          {
            headers: {
              Authorization: `Bearer ${localStorage.getItem("token")}`,
            },
          }
        );

        if (!fieldRes.ok) throw new Error("Failed to load field layout");
        const fieldData = await fieldRes.json();
        setFieldLayout(fieldData);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [matchId, currentPhase]);

  // Playback loop
  useEffect(() => {
    if (!isPlaying || !trajectories) return;

    const interval = setInterval(() => {
      setCurrentFrame((prev) => {
        const maxFrames = 150 * FPS; // Match duration * FPS
        const next = prev + playbackSpeed;
        if (next >= maxFrames) {
          setIsPlaying(false);
          return 0;
        }
        return next;
      });
    }, 1000 / (FPS * playbackSpeed));

    return () => clearInterval(interval);
  }, [isPlaying, playbackSpeed, trajectories]);

  // Filter trajectories by current playback time
  const getFilteredTrajectories = useCallback(() => {
    if (!trajectories) return {};

    const timeMs = (currentFrame / FPS) * 1000;
    const filtered: Record<number, Array<[number, number]>> = {};

    for (const [teamId, traj] of Object.entries(trajectories.teams)) {
      const team = parseInt(teamId);

      // For now, show all points up to current time
      // In a real implementation, would interpolate based on timestamps
      filtered[team] = traj.coordinates.slice(
        0,
        Math.ceil((traj.coordinates.length * currentFrame) / (150 * FPS))
      );
    }

    return filtered;
  }, [trajectories, currentFrame]);

  // Export heatmap as image
  const handleExportHeatmap = useCallback(async () => {
    try {
      // Get the visualization container
      const element = document.getElementById("visualization-container");
      if (!element) {
        throw new Error("Visualization container not found");
      }

      // Capture the visualization as canvas
      const canvas = await htmlToCanvas(element, {
        backgroundColor: "#1a1a2e",
        scale: 2,
        logging: false,
      });

      // Convert canvas to blob and download
      canvas.toBlob((blob) => {
        if (!blob) return;

        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        
        // Create filename with match ID and timestamp
        const timestamp = new Date().toISOString().split("T")[0];
        const filename = `match_${matchId}_heatmap_${timestamp}.png`;
        link.download = filename;

        // Trigger download
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        // Cleanup
        URL.revokeObjectURL(url);
      });
    } catch (err) {
      console.error("Failed to export heatmap:", err);
      alert("Failed to export heatmap as PNG");
    }
  }, [matchId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-950">
        <div className="text-slate-300">Loading match visualization...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-950">
        <div className="flex items-center gap-3 bg-red-900/20 border border-red-700 rounded-lg p-4 text-red-300">
          <AlertCircle className="w-5 h-5" />
          <div>
            <div className="font-semibold">Error</div>
            <div className="text-sm">{error}</div>
          </div>
        </div>
      </div>
    );
  }

  if (!trajectories || !fieldLayout || !heatmapData) {
    return null;
  }

  const teams = Object.values(trajectories.teams);
  const filteredTrajectories = getFilteredTrajectories();

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">Match {matchId} Visualization</h1>
        <p className="text-slate-400">
          {teams.length} teams tracked • {heatmapData.total_points} data points
        </p>
      </div>

      {/* Main Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main Visualization (3 cols) */}
        <div className="lg:col-span-3 space-y-4">
          {/* Field + Heatmap */}
          <div className="bg-slate-900 border border-slate-700 rounded-lg p-4">
            <div id="visualization-container" className="bg-slate-950 rounded">
              {fieldLayout && heatmapData && (
                <HeatmapOverlay
                  width={800}
                  height={400}
                  fieldWidth={fieldLayout.width_ft}
                  fieldHeight={fieldLayout.height_ft}
                  bins={heatmapData.bins}
                  maxIntensity={heatmapData.max_intensity}
                  colorScheme={colorScheme}
                >
                  <FieldDiagram
                    width={800}
                    height={400}
                    fieldLayout={fieldLayout}
                    trajectories={filteredTrajectories}
                    selectedTeam={selectedTeam}
                    showZoneLabels={true}
                  />
                </HeatmapOverlay>
              )}
            </div>

            {/* Controls Under Visualization */}
            <div className="mt-4 space-y-3">
              <PlaybackControls
                totalFrames={150 * FPS}
                currentFrame={currentFrame}
                isPlaying={isPlaying}
                speed={playbackSpeed}
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
                onSeek={setCurrentFrame}
                onSpeedChange={setPlaybackSpeed}
                onPhaseChange={setCurrentPhase}
                fps={FPS}
              />

              {/* Options */}
              <div className="flex gap-2 flex-wrap">
                <select
                  value={colorScheme}
                  onChange={(e) =>
                    setColorScheme(e.target.value as "hot" | "cool" | "viridis")
                  }
                  className="px-3 py-1 bg-slate-800 border border-slate-700 rounded text-xs"
                >
                  <option value="hot">Hot</option>
                  <option value="cool">Cool</option>
                  <option value="viridis">Viridis</option>
                </select>

                <button
                  onClick={handleExportHeatmap}
                  className="px-3 py-1 bg-slate-800 hover:bg-slate-700 rounded text-xs flex items-center gap-2"
                >
                  <Download className="w-3 h-3" />
                  Export PNG
                </button>
              </div>
            </div>
          </div>

          {/* Heatmap Legend */}
          <div className="bg-slate-900 border border-slate-700 rounded-lg p-4">
            <h3 className="text-sm font-semibold mb-3">Heat Intensity</h3>
            <HeatmapLegend
              colorScheme={colorScheme}
              maxIntensity={heatmapData.max_intensity}
            />
          </div>
        </div>

        {/* Sidebar (1 col) */}
        <div className="space-y-4">
          {/* Team List */}
          <div className="bg-slate-900 border border-slate-700 rounded-lg p-4">
            <h3 className="text-sm font-semibold mb-3">Teams</h3>
            <div className="space-y-1 max-h-96 overflow-y-auto">
              <button
                onClick={() => setSelectedTeam(null)}
                className={`w-full text-left px-2 py-1 rounded text-sm transition ${
                  selectedTeam === null
                    ? "bg-blue-600 text-white"
                    : "hover:bg-slate-800"
                }`}
              >
                All Teams
              </button>

              {teams.map((team) => (
                <button
                  key={team.team_id}
                  onClick={() => setSelectedTeam(team.team_id)}
                  className={`w-full text-left px-2 py-1 rounded text-sm transition ${
                    selectedTeam === team.team_id
                      ? "bg-blue-600 text-white"
                      : team.alliance === "red"
                        ? "hover:bg-red-900/30 text-red-300"
                        : "hover:bg-blue-900/30 text-blue-300"
                  }`}
                >
                  <div className="font-semibold">Team {team.team_id}</div>
                  <div className="text-xs opacity-70">
                    {team.stats.total_points} points
                  </div>
                  <div className="text-xs opacity-70">
                    {team.stats.distance_traveled.toFixed(1)} ft
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Statistics */}
          {selectedTeam && trajectories.teams[selectedTeam] && (
            <div className="bg-slate-900 border border-slate-700 rounded-lg p-4">
              <h3 className="text-sm font-semibold mb-3">
                Team {selectedTeam} Stats
              </h3>
              <div className="space-y-2 text-sm">
                <div>
                  <div className="text-slate-400">Total Points</div>
                  <div className="font-semibold">
                    {trajectories.teams[selectedTeam].stats.total_points}
                  </div>
                </div>
                <div>
                  <div className="text-slate-400">Distance Traveled</div>
                  <div className="font-semibold">
                    {trajectories.teams[selectedTeam].stats.distance_traveled.toFixed(1)}{" "}
                    ft
                  </div>
                </div>
                <div>
                  <div className="text-slate-400">Alliance</div>
                  <div className="font-semibold capitalize">
                    {trajectories.teams[selectedTeam].alliance}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
