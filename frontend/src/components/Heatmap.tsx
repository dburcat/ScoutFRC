import React, { useEffect, useRef, useMemo } from "react";

/**
 * Heatmap Component
 *
 * Renders spatial heatmap data on a canvas with color gradient visualization.
 * Supports overlay on field diagram.
 */

export interface HeatmapBin {
  x_min: number;
  x_max: number;
  y_min: number;
  y_max: number;
  center_x: number;
  center_y: number;
  count: number;
  intensity: number;
}

interface HeatmapProps {
  width: number;
  height: number;
  fieldWidth: number;
  fieldHeight: number;
  bins: HeatmapBin[];
  maxIntensity?: number;
  colorScheme?: "hot" | "cool" | "viridis";
  opacity?: number;
}

/**
 * Utility: Convert field coordinates to canvas coordinates
 */
function fieldToCanvas(
  x: number,
  y: number,
  fieldWidth: number,
  fieldHeight: number,
  canvasWidth: number,
  canvasHeight: number
) {
  const xScale = (canvasWidth - 40) / fieldWidth;
  const yScale = (canvasHeight - 40) / fieldHeight;

  return {
    x: 20 + x * xScale,
    y: canvasHeight - 20 - y * yScale,
  };
}

/**
 * Utility: Convert intensity to RGB using color scheme
 */
function intensityToColor(
  intensity: number, // 0-1 normalized
  scheme: "hot" | "cool" | "viridis" = "hot"
): string {
  // Clamp between 0-1
  intensity = Math.max(0, Math.min(intensity, 1));

  let r = 0,
    g = 0,
    b = 0;

  if (scheme === "hot") {
    // Red-Yellow-White gradient
    if (intensity < 0.5) {
      // Black to Red
      r = Math.floor(intensity * 2 * 255);
      g = 0;
      b = 0;
    } else {
      // Red to Yellow to White
      r = 255;
      g = Math.floor((intensity - 0.5) * 2 * 255);
      b = Math.floor((intensity - 0.5) * 2 * 255);
    }
  } else if (scheme === "cool") {
    // Blue-Cyan-Green gradient
    if (intensity < 0.5) {
      // Blue to Cyan
      r = 0;
      g = Math.floor(intensity * 2 * 255);
      b = 255;
    } else {
      // Cyan to Green
      r = 0;
      g = 255;
      b = Math.floor((1 - (intensity - 0.5) * 2) * 255);
    }
  } else if (scheme === "viridis") {
    // Viridis perceptually uniform colormap
    // Simplified version
    if (intensity < 0.25) {
      // Dark Purple to Blue
      r = Math.floor((1 - intensity * 4) * 68);
      g = Math.floor(intensity * 4 * 1);
      b = Math.floor(84 + intensity * 4 * 100);
    } else if (intensity < 0.5) {
      // Blue to Cyan
      r = 0;
      g = Math.floor(((intensity - 0.25) * 4) * 176);
      b = Math.floor(256 - (intensity - 0.25) * 4 * 80);
    } else if (intensity < 0.75) {
      // Cyan to Yellow
      r = Math.floor(((intensity - 0.5) * 4) * 255);
      g = Math.floor(176 + (intensity - 0.5) * 4 * 71);
      b = Math.floor(32 - (intensity - 0.5) * 4 * 20);
    } else {
      // Yellow to Green
      r = Math.floor(255 - (intensity - 0.75) * 4 * 50);
      g = Math.floor(247 - (intensity - 0.75) * 4 * 50);
      b = 0;
    }
  }

  return `rgb(${r}, ${g}, ${b})`;
}

/**
 * Main Heatmap Component
 */
export const Heatmap = React.forwardRef<HTMLCanvasElement, HeatmapProps>(
  (
    {
      width,
      height,
      fieldWidth,
      fieldHeight,
      bins,
      maxIntensity = 100,
      colorScheme = "hot",
      opacity = 0.7,
    },
    ref
  ) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const finalRef = ref || canvasRef;

    // Render heatmap to canvas
    useEffect(() => {
      const canvas =
        typeof finalRef === "object" && finalRef !== null
          ? finalRef.current
          : null;

      if (!canvas) return;

      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      // Set canvas size
      canvas.width = width;
      canvas.height = height;

      // Clear canvas
      ctx.clearRect(0, 0, width, height);

      // Draw bins
      for (const bin of bins) {
        const topLeft = fieldToCanvas(
          bin.x_min,
          bin.y_max,
          fieldWidth,
          fieldHeight,
          width,
          height
        );
        const bottomRight = fieldToCanvas(
          bin.x_max,
          bin.y_min,
          fieldWidth,
          fieldHeight,
          width,
          height
        );

        const cellWidth = bottomRight.x - topLeft.x;
        const cellHeight = bottomRight.y - topLeft.y;

        // Normalize intensity
        const normalizedIntensity = bin.intensity / Math.max(maxIntensity, 1);

        // Get color
        const color = intensityToColor(normalizedIntensity, colorScheme);

        // Draw cell
        ctx.fillStyle = color;
        ctx.globalAlpha = opacity;
        ctx.fillRect(topLeft.x, topLeft.y, cellWidth, cellHeight);

        // Optional: draw cell border
        ctx.globalAlpha = opacity * 0.5;
        ctx.strokeStyle = color;
        ctx.lineWidth = 0.5;
        ctx.strokeRect(topLeft.x, topLeft.y, cellWidth, cellHeight);
      }

      // Reset alpha
      ctx.globalAlpha = 1;
    }, [bins, width, height, fieldWidth, fieldHeight, maxIntensity, colorScheme, opacity]);

    return (
      <canvas
        ref={finalRef}
        className="absolute top-0 left-0"
        style={{ opacity }}
      />
    );
  }
);

Heatmap.displayName = "Heatmap";

/**
 * Heatmap Legend Component
 */
export function HeatmapLegend({
  colorScheme = "hot",
  maxIntensity = 100,
}: {
  colorScheme?: "hot" | "cool" | "viridis";
  maxIntensity?: number;
}) {
  const gradientSteps = 10;

  const gradient = useMemo(() => {
    const colors = [];
    for (let i = 0; i <= gradientSteps; i++) {
      const intensity = i / gradientSteps;
      colors.push(intensityToColor(intensity, colorScheme));
    }
    return `linear-gradient(to right, ${colors.join(", ")})`;
  }, [colorScheme]);

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-4">
        <div
          className="flex-1 h-6 rounded border border-slate-600"
          style={{ background: gradient }}
        />
      </div>
      <div className="flex justify-between text-xs text-slate-400">
        <span>Low</span>
        <span>High ({maxIntensity})</span>
      </div>
    </div>
  );
}

/**
 * Composite: Field + Heatmap overlay
 */
interface HeatmapOverlayProps {
  width: number;
  height: number;
  fieldWidth: number;
  fieldHeight: number;
  bins: HeatmapBin[];
  maxIntensity?: number;
  colorScheme?: "hot" | "cool" | "viridis";
  children?: React.ReactNode; // Field diagram rendered beneath
}

export function HeatmapOverlay({
  width,
  height,
  fieldWidth,
  fieldHeight,
  bins,
  maxIntensity,
  colorScheme,
  children,
}: HeatmapOverlayProps) {
  const heatmapRef = useRef<HTMLCanvasElement>(null);

  return (
    <div className="relative" style={{ width, height }}>
      {/* Base layer: field diagram */}
      {children}

      {/* Overlay layer: heatmap */}
      <Heatmap
        ref={heatmapRef}
        width={width}
        height={height}
        fieldWidth={fieldWidth}
        fieldHeight={fieldHeight}
        bins={bins}
        maxIntensity={maxIntensity}
        colorScheme={colorScheme}
        opacity={0.6}
      />
    </div>
  );
}
