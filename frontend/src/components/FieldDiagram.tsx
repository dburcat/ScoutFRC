import React, { useMemo } from "react";
import { Maximize2, ZoomIn, ZoomOut } from "lucide-react";

/**
 * FRC Field Diagram Component
 *
 * Renders an accurate field layout for the current game season with
 * scoring zones and game elements.
 *
 * 2024 Crescendo Field:
 * - 54' × 27' field
 * - Blue speaker (left), Red speaker (right)
 * - Blue amp (bottom-left), Red amp (bottom-right)
 * - Center stage (endgame zone)
 */

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

/**
 * FieldDiagram: Main field visualization component
 */
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

  // Calculate scaling
  const xScale = (width - 40) / fieldLayout.width_ft;
  const yScale = (height - 40) / fieldLayout.height_ft;

  // Convert field coords to SVG coords
  const fieldToSvg = (x: number, y: number) => {
    return {
      x: 20 + x * xScale * zoom + pan.x,
      y: height - 20 - y * yScale * zoom - pan.y,
    };
  };

  // Handle zoom
  const handleZoom = (direction: "in" | "out") => {
    const factor = direction === "in" ? 1.2 : 0.8;
    setZoom((prev) => Math.max(0.5, Math.min(prev * factor, 3)));
  };

  // Reset view
  const handleReset = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  // Pan handling
  const handleMouseDown = (e: React.MouseEvent<SVGSVGElement>) => {
    if (e.button !== 2) return; // Right-click for pan
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

  // Render heatmap
  const heatmapLayer = useMemo(() => {
    if (heatmapBins.length === 0) return null;

    const cellSize = 1.0; // 1-foot cells
    const cells = [];

    for (const bin of heatmapBins) {
      const intensity = bin.intensity / Math.max(maxHeatmapIntensity, 1);
      const opacity = Math.min(intensity * 0.8, 0.8);
      
      // Color gradient: cool (blue) -> hot (red)
      const hue = (1 - intensity) * 240; // 240 (blue) to 0 (red)
      const color = `hsl(${hue}, 100%, 50%)`;

      const topLeft = fieldToSvg(bin.center_x - cellSize / 2, bin.center_y + cellSize / 2);
      const bottomRight = fieldToSvg(bin.center_x + cellSize / 2, bin.center_y - cellSize / 2);

      cells.push(
        <g key={`heatmap-${bin.center_x}-${bin.center_y}`} opacity={opacity}>
          <rect
            x={topLeft.x}
            y={topLeft.y}
            width={bottomRight.x - topLeft.x}
            height={bottomRight.y - topLeft.y}
            fill={color}
            stroke="none"
          />
        </g>
      );
    }

    return <g id="heatmap-layer">{cells}</g>;
  }, [heatmapBins, maxHeatmapIntensity, fieldToSvg]);

  // Render trajectories
  const trajectoryLayer = useMemo(() => {
    const lines = [];

    for (const [teamId, coords] of Object.entries(trajectories)) {
      if (selectedTeam && parseInt(teamId) !== selectedTeam) continue;

      const team = parseInt(teamId);
      const isRed = team % 2 === 0;
      const color = isRed ? "#DC143C" : "#4169E1";
      const opacity = selectedTeam === team ? 1 : 0.6;

      // Draw trajectory line
      if (coords.length > 1) {
        const pathData = coords
          .map((coord, idx) => {
            const point = fieldToSvg(coord[0], coord[1]);
            return `${idx === 0 ? "M" : "L"} ${point.x} ${point.y}`;
          })
          .join(" ");

        lines.push(
          <path
            key={`trajectory-${teamId}`}
            d={pathData}
            fill="none"
            stroke={color}
            strokeWidth="2"
            opacity={opacity}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        );

        // Draw start point
        const start = fieldToSvg(coords[0][0], coords[0][1]);
        lines.push(
          <circle
            key={`start-${teamId}`}
            cx={start.x}
            cy={start.y}
            r="4"
            fill={color}
            opacity={opacity}
          />
        );

        // Draw end point
        const end = fieldToSvg(coords[coords.length - 1][0], coords[coords.length - 1][1]);
        lines.push(
          <circle
            key={`end-${teamId}`}
            cx={end.x}
            cy={end.y}
            r="4"
            fill={color}
            stroke="white"
            strokeWidth="1"
            opacity={opacity}
          />
        );
      }
    }

    return <g id="trajectory-layer">{lines}</g>;
  }, [trajectories, selectedTeam, fieldToSvg]);

  // Render zones
  const zoneLayer = useMemo(() => {
    const zones = [];

    for (const zone of Object.values(fieldLayout.zones)) {
      const topLeft = fieldToSvg(zone.min_x, zone.max_y);
      const bottomRight = fieldToSvg(zone.max_x, zone.min_y);

      zones.push(
        <g key={`zone-${zone.name}`}>
          <rect
            x={topLeft.x}
            y={topLeft.y}
            width={bottomRight.x - topLeft.x}
            height={bottomRight.y - topLeft.y}
            fill={zone.color}
            fillOpacity="0.2"
            stroke={zone.color}
            strokeWidth="2"
            onClick={() => onZoneClick?.(zone)}
            className="cursor-pointer hover:fill-opacity-30 transition"
          />
          {showZoneLabels && (
            <text
              x={(topLeft.x + bottomRight.x) / 2}
              y={(topLeft.y + bottomRight.y) / 2}
              textAnchor="middle"
              dominantBaseline="middle"
              fontSize="12"
              fill={zone.color}
              fontWeight="bold"
              pointerEvents="none"
            >
              {zone.name}
            </text>
          )}
        </g>
      );
    }

    return <g id="zone-layer">{zones}</g>;
  }, [fieldLayout.zones, showZoneLabels, fieldToSvg, onZoneClick]);

  const svgWidth = width;
  const svgHeight = height;

  return (
    <div className="space-y-2">
      {/* SVG Canvas */}
      <svg
        ref={svgRef}
        width={svgWidth}
        height={svgHeight}
        className="border border-slate-700 bg-slate-950 cursor-grab active:cursor-grabbing"
        onMouseDown={handleMouseDown}
        onContextMenu={(e) => e.preventDefault()}
      >
        {/* Field border */}
        <rect
          x={20}
          y={20}
          width={xScale * fieldLayout.width_ft * zoom}
          height={yScale * fieldLayout.height_ft * zoom}
          fill="none"
          stroke="white"
          strokeWidth="2"
          transform={`translate(${pan.x}, ${pan.y})`}
        />

        {/* Grid (optional) */}
        <defs>
          <pattern
            id="grid"
            width={xScale * zoom}
            height={yScale * zoom}
            patternUnits="userSpaceOnUse"
            x={20 + pan.x}
            y={20 + pan.y}
          >
            <path d={`M ${xScale * zoom} 0 L 0 0 0 ${yScale * zoom}`} stroke="#404040" strokeWidth="0.5" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" fillOpacity="0.3" />

        {/* Layers */}
        <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
          {heatmapLayer}
          {zoneLayer}
          {trajectoryLayer}
        </g>
      </svg>

      {/* Controls */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => handleZoom("out")}
          className="p-2 bg-slate-800 hover:bg-slate-700 rounded"
          title="Zoom out"
        >
          <ZoomOut className="w-4 h-4" />
        </button>

        <div className="text-sm text-slate-400">
          {(zoom * 100).toFixed(0)}%
        </div>

        <button
          onClick={() => handleZoom("in")}
          className="p-2 bg-slate-800 hover:bg-slate-700 rounded"
          title="Zoom in"
        >
          <ZoomIn className="w-4 h-4" />
        </button>

        <button
          onClick={handleReset}
          className="p-2 bg-slate-800 hover:bg-slate-700 rounded ml-auto"
          title="Reset view"
        >
          <Maximize2 className="w-4 h-4" />
        </button>
      </div>

      {/* Legend */}
      <div className="text-xs text-slate-400 space-y-1">
        <div>🔵 Blue Alliance • 🔴 Red Alliance</div>
        <div>Right-click + drag to pan | Scroll wheel to zoom</div>
      </div>
    </div>
  );
}

/**
 * Standalone zone legend component
 */
export function FieldZoneLegend({ zones }: { zones: FieldZone[] }) {
  return (
    <div className="space-y-2">
      {zones.map((zone) => (
        <div key={zone.name} className="flex items-center gap-2 text-sm">
          <div
            className="w-4 h-4 rounded"
            style={{ backgroundColor: zone.color, opacity: 0.6 }}
          />
          <span className="text-slate-300">{zone.name}</span>
          {zone.scoring_points > 0 && (
            <span className="text-xs text-slate-500">({zone.scoring_points} pts)</span>
          )}
        </div>
      ))}
    </div>
  );
}
