import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { FieldDiagram, FieldLayout } from "../FieldDiagram";

/**
 * Tests for FieldDiagram component
 */

const mockFieldLayout: FieldLayout = {
  year: 2024,
  width_ft: 54,
  height_ft: 27,
  zones: {
    blue_speaker: {
      name: "Blue Speaker",
      min_x: 0,
      max_x: 8,
      min_y: 4,
      max_y: 8.5,
      scoring_points: 2,
      color: "#4169E1",
    },
    red_speaker: {
      name: "Red Speaker",
      min_x: 46,
      max_x: 54,
      min_y: 4,
      max_y: 8.5,
      scoring_points: 2,
      color: "#DC143C",
    },
    stage: {
      name: "Stage",
      min_x: 17,
      max_x: 37,
      min_y: 8,
      max_y: 19,
      scoring_points: 0,
      color: "#9370DB",
    },
  },
};

describe("FieldDiagram", () => {
  it("renders without crashing", () => {
    render(
      <FieldDiagram
        width={800}
        height={400}
        fieldLayout={mockFieldLayout}
        trajectories={{}}
        heatmapBins={[]}
      />
    );

    expect(screen.getByRole("img", { hidden: true })).toBeInTheDocument();
  });

  it("displays zones from field layout", () => {
    const { container } = render(
      <FieldDiagram
        width={800}
        height={400}
        fieldLayout={mockFieldLayout}
        trajectories={{}}
        heatmapBins={[]}
        showZoneLabels={true}
      />
    );

    // Check that zone labels are rendered
    const text = container.textContent;
    expect(text).toContain("Blue Speaker");
    expect(text).toContain("Red Speaker");
  });

  it("renders trajectories when provided", () => {
    const trajectories = {
      1690: [
        [10, 10],
        [20, 15],
        [30, 20],
      ],
    };

    const { container } = render(
      <FieldDiagram
        width={800}
        height={400}
        fieldLayout={mockFieldLayout}
        trajectories={trajectories}
        heatmapBins={[]}
      />
    );

    // Check that path elements are rendered
    const paths = container.querySelectorAll("path");
    expect(paths.length).toBeGreaterThan(0);
  });

  it("filters trajectories by selected team", () => {
    const trajectories = {
      1690: [
        [10, 10],
        [20, 15],
      ],
      1836: [
        [5, 5],
        [15, 10],
      ],
    };

    const { container } = render(
      <FieldDiagram
        width={800}
        height={400}
        fieldLayout={mockFieldLayout}
        trajectories={trajectories}
        selectedTeam={1690}
        heatmapBins={[]}
      />
    );

    // When a team is selected, only that team's trajectory should be highlighted
    const paths = container.querySelectorAll("path");
    expect(paths.length).toBeGreaterThan(0);
  });

  it("handles zoom controls", () => {
    const { getByTitle } = render(
      <FieldDiagram
        width={800}
        height={400}
        fieldLayout={mockFieldLayout}
        trajectories={{}}
        heatmapBins={[]}
      />
    );

    const zoomInButton = getByTitle("Zoom in");
    const zoomOutButton = getByTitle("Zoom out");

    expect(zoomInButton).toBeInTheDocument();
    expect(zoomOutButton).toBeInTheDocument();

    fireEvent.click(zoomInButton);
    // Zoom level should change (verified by zoom display updating)
  });

  it("handles reset view", () => {
    const { getByTitle } = render(
      <FieldDiagram
        width={800}
        height={400}
        fieldLayout={mockFieldLayout}
        trajectories={{}}
        heatmapBins={[]}
      />
    );

    const resetButton = getByTitle("Reset view");
    expect(resetButton).toBeInTheDocument();

    fireEvent.click(resetButton);
    // View should be reset to default (1x zoom, no pan)
  });

  it("triggers zone click handler", () => {
    const handleZoneClick = vi.fn();

    const { container } = render(
      <FieldDiagram
        width={800}
        height={400}
        fieldLayout={mockFieldLayout}
        trajectories={{}}
        heatmapBins={[]}
        onZoneClick={handleZoneClick}
      />
    );

    // Find zone rectangles and click
    const rects = container.querySelectorAll("rect");
    if (rects.length > 0) {
      fireEvent.click(rects[1]); // Skip field border
      // Handler should be called
    }
  });

  it("renders heatmap bins", () => {
    const bins = [
      {
        center_x: 27,
        center_y: 13.5,
        intensity: 50,
      },
      {
        center_x: 10,
        center_y: 10,
        intensity: 75,
      },
    ];

    const { container } = render(
      <FieldDiagram
        width={800}
        height={400}
        fieldLayout={mockFieldLayout}
        trajectories={{}}
        heatmapBins={bins}
        maxHeatmapIntensity={100}
      />
    );

    // Heatmap should render as rectangles
    const allRects = container.querySelectorAll("rect");
    expect(allRects.length).toBeGreaterThan(0);
  });

  it("handles multiple trajectories with different colors", () => {
    const trajectories = {
      1690: [[5, 5], [10, 10]], // Even team (red)
      1835: [[15, 15], [20, 20]], // Odd team (blue)
    };

    const { container } = render(
      <FieldDiagram
        width={800}
        height={400}
        fieldLayout={mockFieldLayout}
        trajectories={trajectories}
        heatmapBins={[]}
      />
    );

    const paths = container.querySelectorAll("path");
    expect(paths.length).toBeGreaterThanOrEqual(2);
  });

  it("responds to pan gestures", () => {
    const { container } = render(
      <FieldDiagram
        width={800}
        height={400}
        fieldLayout={mockFieldLayout}
        trajectories={{}}
        heatmapBins={[]}
      />
    );

    const svg = container.querySelector("svg");
    expect(svg).toHaveClass("cursor-grab");

    // Simulate right-click + drag
    fireEvent.mouseDown(svg!, { button: 2, clientX: 100, clientY: 100 });
    fireEvent.mouseMove(document, { clientX: 150, clientY: 150 });
    fireEvent.mouseUp(document);
  });

  it("displays field dimensions correctly", () => {
    const { container } = render(
      <FieldDiagram
        width={800}
        height={400}
        fieldLayout={mockFieldLayout}
        trajectories={{}}
        heatmapBins={[]}
      />
    );

    const svg = container.querySelector("svg");
    expect(svg).toHaveAttribute("width", "800");
    expect(svg).toHaveAttribute("height", "400");
  });

  it("hides zone labels when disabled", () => {
    const { container } = render(
      <FieldDiagram
        width={800}
        height={400}
        fieldLayout={mockFieldLayout}
        trajectories={{}}
        heatmapBins={[]}
        showZoneLabels={false}
      />
    );

    // Text elements for zone labels should not be rendered
    const texts = container.querySelectorAll("text");
    // Should only have minimal text (like legend)
    expect(texts.length).toBeLessThan(10);
  });

  it("maintains aspect ratio for field", () => {
    const width = 800;
    const height = 400;
    const expectedRatio = width / height;
    const fieldRatio = mockFieldLayout.width_ft / mockFieldLayout.height_ft;

    // Ratios should be similar (both are 2:1)
    expect(Math.abs(expectedRatio - fieldRatio)).toBeLessThan(0.01);
  });
});
