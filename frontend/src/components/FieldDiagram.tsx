import React, { useMemo, useCallback } from "react";
import { Maximize2, ZoomIn, ZoomOut } from "lucide-react";

export interface FieldZone {
  name: string;
  min_x: number;
  max_x: number;
  min_y: number;
  max_y: number;
  scoring_points: number;
  color: string;
}

export interface FieldLayout {
  year: number;
  width_ft: number;
  height_ft: number;
  zones: Record<string, FieldZone>;
}

interface FieldDiagramProps {
  width?: number;
  height?: number;
  fieldLayout: FieldLayout;
  trajectories?: Record<number, Array<[number, number]>>;
  heatmapBins?: Array<{
    center_x: number;
    center_y: number;
    intensity: number;
  }>;
  selectedTeam?: number | null;
  onZoneClick?: (zone: FieldZone) => void;
  showZoneLabels?: boolean;
  maxHeatmapIntensity?: number;
}

export function FieldDiagram({
  width = 800,
  height = 400,
  fieldLayout,
  trajectories = {},
  heatmapBins = [],
  selectedTeam = null,
  onZoneClick,
  showZoneLabels = true,
  maxHeatmapIntensity = 100,
}: FieldDiagramProps) {
  const [zoom, setZoom] = React.useState(1);
  const [pan, setPan] = React.useState({ x: 0, y: 0 });
  const svgRef = React.useRef<SVGSVGElement>(null);

  // Base scaling — zoom/pan live on the <g> transform, not here
  const xScale = (width - 40) / fieldLayout.width_ft;
  const yScale = (height - 40) / fieldLayout.height_ft;

  // Convert field coords → base SVG coords (NO zoom/pan baked in)
  // FIX: was previously baking zoom+pan in here AND the <g> also applied them,
  // causing a double-transform that pushed everything off-screen.
  const fieldToSvg = useCallback(
    (x: number, y: number) => ({
      x: 20 + x * xScale,
      y: height - 20 - y * yScale,
    }),
    [xScale, yScale, height]
  );

  const handleZoom = (direction: "in" | "out") => {
    const factor = direction === "in" ? 1.2 : 0.8;
    setZoom((prev) => Math.max(0.5, Math.min(prev * factor, 3)));
  };

  const handleReset = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  const handleMouseDown = (e: React.MouseEvent<SVGSVGElement>) => {
    if (e.button !== 2) return;
    const startX = e.clientX;
    const startY = e.clientY;
    const startPan = { ...pan };

    const handleMouseMove = (moveEvent: MouseEvent) => {
      setPan({
        x: startPan.x + moveEvent.clientX - startX,
        y: startPan.y + moveEvent.clientY - startY,
      });
    };
    const handleMouseUp = () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);
    e.preventDefault();
  };

  // Heatmap bins rendered as SVG rects (no separate canvas positioning issues)
  const heatmapLayer = useMemo(() => {
    if (heatmapBins.length === 0) return null;
    const cellSize = 1.0;
    return (
      <g id="heatmap-layer">
        {heatmapBins.map((bin) => {
          const intensity = bin.intensity / Math.max(maxHeatmapIntensity, 1);
          const opacity = Math.min(intensity * 0.85, 0.85);
          const hue = (1 - intensity) * 240;
          const tl = fieldToSvg(bin.center_x - cellSize / 2, bin.center_y + cellSize / 2);
          const br = fieldToSvg(bin.center_x + cellSize / 2, bin.center_y - cellSize / 2);
          return (
            <rect
              key={`h-${bin.center_x}-${bin.center_y}`}
              x={tl.x}
              y={tl.y}
              width={Math.abs(br.x - tl.x)}
              height={Math.abs(br.y - tl.y)}
              fill={`hsl(${hue},100%,50%)`}
              opacity={opacity}
            />
          );
        })}
      </g>
    );
  }, [heatmapBins, maxHeatmapIntensity, fieldToSvg]);

  // Trajectory paths
  // FIX: trajectories may be empty or have no coords — guard against those
  const trajectoryLayer = useMemo(() => {
    const items: React.ReactNode[] = [];

    for (const [teamId, coords] of Object.entries(trajectories)) {
      if (selectedTeam !== null && parseInt(teamId) !== selectedTeam) continue;
      if (!coords || coords.length === 0) continue;

      const isRed = parseInt(teamId) % 2 === 0;
      const color = isRed ? "#ef4444" : "#3b82f6";
      const opacity = selectedTeam === null || selectedTeam === parseInt(teamId) ? 1 : 0.35;

      if (coords.length > 1) {
        const d = coords
          .map((c, i) => {
            const p = fieldToSvg(c[0], c[1]);
            return `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`;
          })
          .join(" ");
        items.push(
          <path
            key={`traj-${teamId}`}
            d={d}
            fill="none"
            stroke={color}
            strokeWidth="2.5"
            opacity={opacity}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        );
      }

      // Start marker
      const s = fieldToSvg(coords[0][0], coords[0][1]);
      items.push(
        <circle key={`s-${teamId}`} cx={s.x} cy={s.y} r={5} fill="white" stroke={color} strokeWidth="2" opacity={opacity} />
      );

      // Current position marker
      const e = fieldToSvg(coords[coords.length - 1][0], coords[coords.length - 1][1]);
      items.push(
        <circle key={`e-${teamId}`} cx={e.x} cy={e.y} r={7} fill={color} stroke="white" strokeWidth="1.5" opacity={opacity} />
      );

      // Team label
      items.push(
        <text
          key={`lbl-${teamId}`}
          x={e.x + 10}
          y={e.y - 10}
          fontSize="12"
          fill={color}
          fontWeight="bold"
          stroke="black"
          strokeWidth="3"
          paintOrder="stroke"
          opacity={opacity}
        >
          {teamId}
        </text>
      );
    }

    return <g id="trajectory-layer">{items}</g>;
  }, [trajectories, selectedTeam, fieldToSvg]);

  // Zone rects
  const zoneLayer = useMemo(() => (
    <g id="zone-layer">
      {Object.values(fieldLayout.zones).map((zone) => {
        const tl = fieldToSvg(zone.min_x, zone.max_y);
        const br = fieldToSvg(zone.max_x, zone.min_y);
        const w = Math.abs(br.x - tl.x);
        const h = Math.abs(br.y - tl.y);
        return (
          <g key={`zone-${zone.name}`}>
            <rect
              x={tl.x} y={tl.y} width={w} height={h}
              fill={zone.color} fillOpacity="0.15"
              stroke={zone.color} strokeWidth="1.5"
              onClick={() => onZoneClick?.(zone)}
              className="cursor-pointer"
            />
            {showZoneLabels && (
              <text
                x={tl.x + w / 2} y={tl.y + h / 2}
                textAnchor="middle" dominantBaseline="middle"
                fontSize="11" fill={zone.color} fontWeight="bold"
                stroke="black" strokeWidth="2.5" paintOrder="stroke"
                pointerEvents="none"
              >
                {zone.name}
              </text>
            )}
          </g>
        );
      })}
    </g>
  ), [fieldLayout.zones, showZoneLabels, fieldToSvg, onZoneClick]);

  return (
    <div className="space-y-2">
      <svg
        ref={svgRef}
        width={width}
        height={height}
        className="border border-slate-700 bg-slate-950 cursor-grab active:cursor-grabbing"
        onMouseDown={handleMouseDown}
        onContextMenu={(e) => e.preventDefault()}
      >
        {/* Background grid */}
        <defs>
          <pattern id="grid" width={xScale} height={yScale} patternUnits="userSpaceOnUse" x={20} y={20}>
            <path d={`M ${xScale} 0 L 0 0 0 ${yScale}`} stroke="#2a2a3a" strokeWidth="0.5" fill="none" />
          </pattern>
        </defs>
        <rect x={20} y={20} width={width - 40} height={height - 40} fill="url(#grid)" />

        {/*
          FIX: Single <g> handles ALL zoom+pan. fieldToSvg only converts to
          base SVG space — it no longer bakes in pan/zoom itself.
          Previously fieldToSvg included pan/zoom AND this <g> re-applied them,
          placing everything 2x off-screen.
        */}
        <g transform={`translate(${pan.x},${pan.y}) scale(${zoom})`} style={{ transformOrigin: `${20}px ${height - 20}px` }}>
          <rect
            x={20} y={20}
            width={xScale * fieldLayout.width_ft}
            height={yScale * fieldLayout.height_ft}
            fill="none" stroke="white" strokeWidth="2"
          />
          {heatmapLayer}
          {zoneLayer}
          {trajectoryLayer}
        </g>
      </svg>

      <div className="flex items-center gap-2">
        <button onClick={() => handleZoom("out")} className="p-2 bg-slate-800 hover:bg-slate-700 rounded" title="Zoom out">
          <ZoomOut className="w-4 h-4" />
        </button>
        <div className="text-sm text-slate-400">{(zoom * 100).toFixed(0)}%</div>
        <button onClick={() => handleZoom("in")} className="p-2 bg-slate-800 hover:bg-slate-700 rounded" title="Zoom in">
          <ZoomIn className="w-4 h-4" />
        </button>
        <button onClick={handleReset} className="p-2 bg-slate-800 hover:bg-slate-700 rounded ml-auto" title="Reset view">
          <Maximize2 className="w-4 h-4" />
        </button>
      </div>

      <div className="text-xs text-slate-400">
        ⚪ Start &nbsp;●&nbsp; Current position &nbsp;·&nbsp; Right-click drag to pan
      </div>
    </div>
  );
}

export function FieldZoneLegend({ zones }: { zones: FieldZone[] }) {
  return (
    <div className="space-y-2">
      {zones.map((zone) => (
        <div key={zone.name} className="flex items-center gap-2 text-sm">
          <div className="w-4 h-4 rounded" style={{ backgroundColor: zone.color, opacity: 0.6 }} />
          <span className="text-slate-300">{zone.name}</span>
          {zone.scoring_points > 0 && (
            <span className="text-xs text-slate-500">({zone.scoring_points} pts)</span>
          )}
        </div>
      ))}
    </div>
  );
}