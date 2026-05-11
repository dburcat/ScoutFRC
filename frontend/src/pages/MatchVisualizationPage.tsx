import React, { useState, useEffect, useCallback, useMemo } from "react";
import { AlertCircle, Download } from "lucide-react";
import { FieldDiagram, FieldLayout } from "../components/FieldDiagram";
import { HeatmapLegend, HeatmapBin } from "../components/Heatmap";
import { PlaybackControls } from "../components/PlaybackControls";
import { useParams } from "react-router-dom";

/**
 * Match Visualization Page
 *
 * FIX 1: Removed HeatmapOverlay (canvas layer) — heatmap is now rendered
 *         inside FieldDiagram as SVG rects via the heatmapBins prop.
 *         The canvas was positioned absolute inside a non-relative container,
 *         causing it to float at the top of the viewport.
 *
 * FIX 2: Playback scrubbing now slices trajectories correctly.
 *         Previously: slice(0, Math.ceil(len * frame / (150*FPS))) meant at
 *         frame=0 you'd see 0 points and at frame=4500 (2.5 min of playback)
 *         you'd see all. Now totalFrames = max coordinate count so scrubbing
 *         maps 1:1 to trajectory indices.
 *
 * FIX 3: getFilteredTrajectories is a pure useMemo (no useCallback) that
 *         correctly depends on trajectories + currentFrame.
 */

interface TeamTrajectory {
  team_id: number;
  alliance: "red" | "blue";
  coordinates: Array<[number, number]>;
  stats: {
    total_points: number;
    distance_traveled: number;
  };
  station?: {
    slot: number;
    label: string;
    median_x: number;
    median_y: number;
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

const FPS = 10; // visualization frames per second (matches backend FRAME_SAMPLE_FPS)
const MATCH_DURATION_S = 150;

export function MatchVisualizationPage() {
  const { matchId } = useParams<{ matchId: string }>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [trajectories, setTrajectories] = useState<MatchTrajectoriesResponse | null>(null);
  const [heatmapData, setHeatmapData] = useState<MatchHeatmapResponse | null>(null);
  const [fieldLayout, setFieldLayout] = useState<FieldLayout | null>(null);

  const [selectedTeam, setSelectedTeam] = useState<number | null>(null);
  const [currentPhase, setCurrentPhase] = useState<string>("all");
  const [colorScheme, setColorScheme] = useState<"hot" | "cool" | "viridis">("hot");

  // FIX: totalFrames is the max number of coordinate points across all teams,
  // so the scrubber maps 1:1 to actual data rather than an arbitrary 4500 count.
  const totalFrames = useMemo(() => {
    if (!trajectories) return MATCH_DURATION_S * FPS;
    const counts = Object.values(trajectories.teams).map((t) => t.coordinates.length);
    return Math.max(...counts, 1);
  }, [trajectories]);

  const [currentFrame, setCurrentFrame] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);

  // Load data whenever matchId or phase changes
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        setError(null);
        setIsPlaying(false);
        setCurrentFrame(0);

        const base = import.meta.env.VITE_API_URL || "http://localhost:8000";
        const headers = { Authorization: `Bearer ${localStorage.getItem("token")}` };

        const [trajRes, heatmapRes, fieldRes] = await Promise.all([
          fetch(`${base}/matches/${matchId}/trajectories?phase=${currentPhase}`, { headers }),
          fetch(`${base}/matches/${matchId}/heatmap?phase=${currentPhase}`, { headers }),
          fetch(`${base}/matches/${matchId}/field-layout`, { headers }),
        ]);

        if (!trajRes.ok) throw new Error(`Trajectories: ${trajRes.statusText}`);
        if (!heatmapRes.ok) throw new Error(`Heatmap: ${heatmapRes.statusText}`);
        if (!fieldRes.ok) throw new Error(`Field layout: ${fieldRes.statusText}`);

        const [trajData, heatData, fieldData] = await Promise.all([
          trajRes.json(),
          heatmapRes.json(),
          fieldRes.json(),
        ]);

        setTrajectories(trajData);
        setHeatmapData(heatData);
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
        const next = prev + 1;
        if (next >= totalFrames) {
          setIsPlaying(false);
          return totalFrames - 1;
        }
        return next;
      });
    }, 1000 / (FPS * playbackSpeed));
    return () => clearInterval(interval);
  }, [isPlaying, playbackSpeed, trajectories, totalFrames]);

  // FIX: Slice trajectories to currentFrame index — direct 1:1 mapping.
  // Previously this divided by (150*FPS=4500) making frame=0 show nothing.
  const filteredTrajectories = useMemo<Record<number, Array<[number, number]>>>(() => {
    if (!trajectories) return {};
    const result: Record<number, Array<[number, number]>> = {};
    for (const [teamIdStr, traj] of Object.entries(trajectories.teams)) {
      const teamId = parseInt(teamIdStr);
      // Show coords up to currentFrame; when at max show all
      const sliceTo = currentFrame >= totalFrames - 1
        ? traj.coordinates.length
        : Math.ceil((traj.coordinates.length * (currentFrame + 1)) / totalFrames);
      result[teamId] = traj.coordinates.slice(0, Math.max(1, sliceTo));
    }
    return result;
  }, [trajectories, currentFrame, totalFrames]);

  const handleExportHeatmap = useCallback(async () => {
    try {
      const element = document.getElementById("visualization-container");
      if (!element) throw new Error("Container not found");
      // Dynamically import html2canvas to avoid making it a hard dep
      const { default: html2canvas } = await import("html2canvas");
      const canvas = await html2canvas(element, { backgroundColor: "#0f172a", scale: 2, logging: false });
      canvas.toBlob((blob) => {
        if (!blob) return;
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `match_${matchId}_heatmap_${new Date().toISOString().split("T")[0]}.png`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      });
    } catch (err) {
      console.error("Export failed:", err);
      alert("Failed to export PNG");
    }
  }, [matchId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-950">
        <div className="text-slate-300 flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          Loading match visualization…
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-950">
        <div className="flex items-center gap-3 bg-red-900/20 border border-red-700 rounded-lg p-4 text-red-300">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <div>
            <div className="font-semibold">Failed to load visualization</div>
            <div className="text-sm mt-1">{error}</div>
          </div>
        </div>
      </div>
    );
  }

  if (!trajectories || !fieldLayout || !heatmapData) return null;

  const teams = Object.values(trajectories.teams);
  
  // Calculate total movement points from trajectory data
  // (more reliable than heatmap response which may lag or have filtering issues)
  const totalMovementPoints = Object.values(trajectories.teams).reduce(
    (sum, traj) => sum + (traj.stats?.total_points || traj.coordinates?.length || 0),
    0
  );

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 space-y-6">
      {/* Header */}
      <div className="space-y-1">
        <h1 className="text-3xl font-bold">Match {matchId} Visualization</h1>
        <p className="text-slate-400">
          {teams.length} teams tracked · {totalMovementPoints} movement points
          {totalMovementPoints === 0 && (
            <span className="ml-2 text-yellow-400 text-sm">
              ⚠ No tracking data — run the video CV pipeline first
            </span>
          )}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main visualization */}
        <div className="lg:col-span-3 space-y-4">
          <div className="bg-slate-900 border border-slate-700 rounded-lg p-4">
            {/*
              FIX: heatmap is passed as SVG bins directly into FieldDiagram
              instead of a canvas overlay. The old HeatmapOverlay used a
              <canvas position:absolute> inside a non-relative div, causing it
              to render at the top of the page instead of over the field.
            */}
            <div id="visualization-container">
              <FieldDiagram
                width={800}
                height={400}
                fieldLayout={fieldLayout}
                trajectories={filteredTrajectories}
                heatmapBins={heatmapData.bins.map((b) => ({
                  center_x: b.center_x,
                  center_y: b.center_y,
                  intensity: b.intensity,
                }))}
                maxHeatmapIntensity={heatmapData.max_intensity}
                selectedTeam={selectedTeam}
                showZoneLabels={true}
              />
            </div>

            <div className="mt-4 space-y-3">
              <PlaybackControls
                totalFrames={totalFrames}
                currentFrame={currentFrame}
                isPlaying={isPlaying}
                speed={playbackSpeed}
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
                onSeek={setCurrentFrame}
                onSpeedChange={setPlaybackSpeed}
                onPhaseChange={(p) => { setCurrentPhase(p); }}
                fps={FPS}
              />

              <div className="flex gap-2 flex-wrap items-center">
                <label className="text-xs text-slate-400">Heatmap scheme:</label>
                <select
                  value={colorScheme}
                  onChange={(e) => setColorScheme(e.target.value as "hot" | "cool" | "viridis")}
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

          <div className="bg-slate-900 border border-slate-700 rounded-lg p-4">
            <h3 className="text-sm font-semibold mb-3">Heat Intensity</h3>
            <HeatmapLegend colorScheme={colorScheme} maxIntensity={heatmapData.max_intensity} />
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          <div className="bg-slate-900 border border-slate-700 rounded-lg p-4">
            <h3 className="text-sm font-semibold mb-3">Teams</h3>
            <div className="space-y-1 max-h-96 overflow-y-auto">
              <button
                onClick={() => setSelectedTeam(null)}
                className={`w-full text-left px-2 py-1 rounded text-sm transition ${
                  selectedTeam === null ? "bg-blue-600 text-white" : "hover:bg-slate-800"
                }`}
              >
                All Teams
              </button>

              {teams.map((team) => {
                // Generate display label: use station info for unidentified robots
                const label = team.station
                  ? `${team.station.label}`
                  : `Team ${team.team_id}`;
                
                return (
                  <button
                    key={team.team_id}
                    onClick={() => setSelectedTeam(team.team_id)}
                    className={`w-full text-left px-2 py-1.5 rounded text-sm transition ${
                      selectedTeam === team.team_id
                        ? "bg-blue-600 text-white"
                        : team.alliance === "red"
                          ? "hover:bg-red-900/30 text-red-300"
                          : "hover:bg-blue-900/30 text-blue-300"
                    }`}
                  >
                    <div className="font-semibold">{label}</div>
                    <div className="text-xs opacity-70">{team.stats.total_points} track points</div>
                    <div className="text-xs opacity-70">{team.stats.distance_traveled.toFixed(1)} ft</div>
                  </button>
                );
              })}

              {teams.length === 0 && (
                <p className="text-xs text-slate-500 p-2">
                  No team data — video hasn't been processed yet.
                </p>
              )}
            </div>
          </div>

          {selectedTeam !== null && trajectories.teams[selectedTeam] && (
            <div className="bg-slate-900 border border-slate-700 rounded-lg p-4">
              {(() => {
                const team = trajectories.teams[selectedTeam];
                const label = team.station ? `${team.station.label}` : `Team ${selectedTeam}`;
                return <h3 className="text-sm font-semibold mb-3">{label} Stats</h3>;
              })()}
              <div className="space-y-2 text-sm">
                <div>
                  <div className="text-slate-400">Track Points</div>
                  <div className="font-semibold">{trajectories.teams[selectedTeam].stats.total_points}</div>
                </div>
                <div>
                  <div className="text-slate-400">Distance Traveled</div>
                  <div className="font-semibold">
                    {trajectories.teams[selectedTeam].stats.distance_traveled.toFixed(1)} ft
                  </div>
                </div>
                <div>
                  <div className="text-slate-400">Alliance</div>
                  <div className={`font-semibold capitalize ${
                    trajectories.teams[selectedTeam].alliance === "red" ? "text-red-400" : "text-blue-400"
                  }`}>
                    {trajectories.teams[selectedTeam].alliance}
                  </div>
                </div>
                <div>
                  <div className="text-slate-400">Showing</div>
                  <div className="font-semibold">
                    {filteredTrajectories[selectedTeam]?.length ?? 0} / {trajectories.teams[selectedTeam].coordinates.length} pts
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