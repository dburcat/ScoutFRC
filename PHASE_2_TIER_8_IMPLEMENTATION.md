# Phase 2 Tier 8: Field Heatmaps & Movement Visualization - Implementation Guide

**Status:** Foundation Layer Complete - API/Frontend In Progress  
**Completion:** 20% (Foundation + API + Component skeleton)  
**Last Updated:** May 4, 2026

## Overview

Phase 2 Tier 8 implements **spatial visualization of robot movement** during FRC matches, including:
- Field diagram with accurate zone definitions
- Movement trajectory overlays (team-specific lines)
- Spatial heatmaps (concentration of activity)
- Playback controls (replay match movement)
- Phase filtering (auto/teleop/endgame)
- Data export (PNG snapshots)

### Why This Tier

Real-time understanding of robot positioning and movement patterns enables:
- **Scouting:** Where do teams spend most of their time?
- **Strategy:** Which zones see the most activity?
- **Coaching:** Animation-based movement replay for training
- **Analytics:** Heatmap-based zone efficiency metrics

---

## Architecture

### Data Flow

```
MovementTrack (DB)
    ↓
TrajectoryProcessor (extract by team/phase)
    ↓
HeatmapGenerator (2D binning)
    ↓
REST API (/matches/{id}/trajectories, /heatmap)
    ↓
Frontend (MatchVisualizationPage)
    ├─ FieldDiagram (SVG rendering)
    ├─ Heatmap (Canvas overlay)
    └─ PlaybackControls (animation)
```

### Key Components

#### Backend Services

**app/services/field_definitions.py**
- Field geometry registry (54' × 27' for 2024)
- Zone definitions (speaker, amp, stage)
- Color-coded areas for visualization
- Extensible to multiple seasons

**app/services/heatmap_generator.py**
- NumPy-based 2D histogram
- Configurable bin size (default: 1 ft)
- Intensity normalization
- Statistics (mean, std, bounds)

**app/services/trajectory_processor.py**
- Extract MovementTrack from database
- Organize by team and phase
- Phase detection (0-15s auto, 15-135s teleop, 135-150s endgame)
- Distance calculation
- Trajectory interpolation

#### Backend API

**app/routers/trajectories.py**
- `GET /matches/{match_id}/trajectories` → All robot paths
- `GET /matches/{match_id}/heatmap` → Spatial concentration
- `GET /matches/{match_id}/field-layout` → Zone definitions
- Phase filtering, team filtering, bin size customization

#### Frontend Components

**FieldDiagram.tsx**
- SVG-based field rendering
- Trajectory line overlay (red/blue by alliance)
- Zone highlighting with hover
- Zoom (0.5x - 3x) and pan (right-click + drag)
- Grid reference

**Heatmap.tsx**
- Canvas-based rendering (high performance)
- Color schemes: hot (red), cool (blue), viridis
- Intensity-to-color mapping
- Opacity overlay control
- Legend with intensity scale

**PlaybackControls.tsx**
- Play/pause buttons
- Frame scrubber
- Speed control (0.5x - 4x)
- Phase filter buttons
- Time display (seconds / total)

**MatchVisualizationPage.tsx**
- Main integration component
- Combines all three sub-components
- Real-time data loading
- Team selection sidebar
- Statistics display

---

## Deliverables (In Progress)

### ✅ Completed (Foundation Layer - 100%)

1. **Field Definitions** (app/services/field_definitions.py)
   - 2024 Crescendo field layout
   - 8 zones (speaker, amp, stage, source)
   - Color assignments for UI
   - Extensible to 2023, 2025, etc.

2. **Heatmap Generator** (app/services/heatmap_generator.py)
   - NumPy 2D histogram
   - Bin class with center, bounds, count, intensity
   - Normalization and statistics
   - Trajectory interpolation

3. **Trajectory Processor** (app/services/trajectory_processor.py)
   - Phase-based trajectory organization
   - Multi-team support
   - Distance calculation
   - MovementTrack extraction

### 🔄 In Progress (API & Components)

4. **API Router** (app/routers/trajectories.py) - CREATED
   - 3 endpoints implemented
   - Schema definitions (Pydantic)
   - Phase filtering
   - Team filtering

5. **Frontend Components** - CREATED
   - FieldDiagram.tsx (SVG rendering, zoom/pan)
   - Heatmap.tsx (Canvas overlay, color schemes)
   - PlaybackControls.tsx (Animation controls)
   - MatchVisualizationPage.tsx (Integration)

### ❌ Remaining

6. **Integration Tests** (partially done)
   - E2E visualization tests
   - Performance benchmarks

7. **Documentation**
   - Usage guide
   - Troubleshooting

---

## API Endpoints

### GET /matches/{match_id}/trajectories

**Parameters:**
- `phase` (string): "auto", "teleop", "endgame", or "all" (default: "all")

**Response:**
```json
{
  "match_id": 42,
  "teams": {
    "1690": {
      "team_id": 1690,
      "alliance": "blue",
      "coordinates": [[x1, y1], [x2, y2], ...],
      "stats": {
        "total_points": 150,
        "distance_traveled": 420.5
      }
    }
  },
  "field_width": 54,
  "field_height": 27
}
```

### GET /matches/{match_id}/heatmap

**Parameters:**
- `phase` (string): "auto", "teleop", "endgame", or "all"
- `team_id` (integer, optional): Filter to single team
- `bin_size` (float): Grid cell size in feet (default: 1.0)

**Response:**
```json
{
  "match_id": 42,
  "field_width": 54,
  "field_height": 27,
  "bins": [
    {
      "x_min": 20,
      "x_max": 21,
      "y_min": 10,
      "y_max": 11,
      "center_x": 20.5,
      "center_y": 10.5,
      "count": 45,
      "intensity": 75
    }
  ],
  "max_intensity": 100,
  "total_points": 1500
}
```

### GET /matches/{match_id}/field-layout

**Response:**
```json
{
  "year": 2024,
  "width_ft": 54,
  "height_ft": 27,
  "zones": {
    "blue_speaker": {
      "name": "Blue Speaker",
      "min_x": 0,
      "max_x": 8,
      "min_y": 4,
      "max_y": 8.5,
      "scoring_points": 2,
      "color": "#4169E1"
    }
  }
}
```

---

## Frontend Usage

### Import Components

```typescript
import { FieldDiagram, FieldLayout } from '@/components/FieldDiagram';
import { HeatmapOverlay, HeatmapLegend } from '@/components/Heatmap';
import { PlaybackControls } from '@/components/PlaybackControls';
import { MatchVisualizationPage } from '@/pages/MatchVisualizationPage';
```

### Render Visualization

```typescript
<MatchVisualizationPage />
```

### Custom Layout

```typescript
<div className="space-y-4">
  <FieldDiagram
    width={800}
    height={400}
    fieldLayout={fieldLayout}
    trajectories={trajectories}
    heatmapBins={heatmapBins}
    selectedTeam={1690}
    showZoneLabels={true}
  />
  
  <PlaybackControls
    totalFrames={150 * 30}
    currentFrame={currentFrame}
    isPlaying={isPlaying}
    speed={1.0}
    onPlay={() => setIsPlaying(true)}
    onPause={() => setIsPlaying(false)}
    onSeek={setCurrentFrame}
    onSpeedChange={setPlaybackSpeed}
  />
</div>
```

---

## Performance Considerations

### Heatmap Rendering

- **Canvas vs SVG:** Canvas for heatmap overlay (60fps dense data)
- **Bin Size:** 1-foot cells recommended (54×27 field = ~1458 max bins)
- **Intensity Mapping:** Normalized to 0-100 for color interpolation

### Trajectory Rendering

- **Line Simplification:** Optional decimation for very long paths
- **SVG Optimization:** Use `stroke-linecap="round"` for smoother lines
- **Memory:** Pre-compute phase segments to avoid runtime filtering

### Playback Animation

- **Frame Rate:** 30 fps default (configurable)
- **Interpolation:** Linear interpolation between movement points
- **Speed Control:** Multiplier (0.5x - 4x) without re-fetching data

---

## Testing

### Backend Tests

```bash
# Heatmap algorithm
pytest backend/tests/test_heatmap_generator.py -v

# Trajectory processing
pytest backend/tests/test_trajectory_processor.py -v

# API endpoints
pytest backend/tests/test_trajectories_api.py -v
```

### Frontend Tests

```bash
# Component tests
npm test frontend/src/components/FieldDiagram.test.tsx
npm test frontend/src/components/Heatmap.test.tsx
npm test frontend/src/components/PlaybackControls.test.tsx
```

---

## Configuration

### Field Definitions

Add new season to `backend/app/services/field_definitions.py`:

```python
@dataclass
class FieldLayout:
    year: int
    width_ft: float
    height_ft: float
    zones: List[Zone]

# 2025 game (placeholder)
FIELD_2025 = FieldLayout(
    year=2025,
    width_ft=54,
    height_ft=27,
    zones=[...]
)
```

### Heatmap Colors

Modify `frontend/src/components/Heatmap.tsx`:

```typescript
function intensityToColor(intensity, scheme) {
  if (scheme === "custom") {
    // Your gradient here
  }
}
```

---

## Remaining Tasks

### Immediate (Next Session)

1. **Fix HeatmapGenerator** - Add missing `to_dict()` method to FieldLayout
2. **Add Missing Import** - Ensure `get_field_layout()` is exported
3. **Test API Endpoints** - Run trajectories_api tests against real DB
4. **Frontend Routing** - Add MatchVisualizationPage to router

### Secondary

5. Performance optimization for large matches (>500 movement tracks)
6. WebSocket streaming for live trajectory updates
7. Zone-specific statistics in sidebar
8. Heatmap PNG export functionality
9. Multi-match comparison views

---

## Troubleshooting

### Heatmap Shows No Data

- Verify MovementTrack records in database
- Check `field_x` and `field_y` are not NULL
- Confirm bin_size is appropriate for data range

### Trajectories Not Updating

- Verify WebSocket connection in browser console
- Check API endpoint response for team data
- Ensure phase filter matches available data

### Performance Issues

- Reduce bin_size (larger cells) for zoomed-out view
- Use `selectedTeam` filter to show single trajectory
- Decrease canvas resolution for slower devices

---

## Related Documentation

- [PHASE_2_TIERED_DEVELOPMENT_PLAN.md](../PHASE_2_TIERED_DEVELOPMENT_PLAN.md) - Tier 8 requirements
- [COMPUTER_VISION_STRATEGY.md](../docs/COMPUTER_VISION_STRATEGY.md) - MovementTrack data source
- [DATABASE_SCHEMA.md](../docs/DATABASE_SCHEMA.md) - Schema details
- [UX_DESIGN.md](../docs/UX_DESIGN.md) - UI patterns

---

## Session Progress

| Task | Status | Files |
|------|--------|-------|
| Field Definitions | ✅ | `field_definitions.py` |
| Heatmap Algorithm | ✅ | `heatmap_generator.py` |
| Trajectory Processor | ✅ | `trajectory_processor.py` |
| Trajectories API | ✅ | `trajectories.py` router |
| FieldDiagram Component | ✅ | `FieldDiagram.tsx` |
| Heatmap Component | ✅ | `Heatmap.tsx` |
| PlaybackControls | ✅ | `PlaybackControls.tsx` |
| Visualization Page | ✅ | `MatchVisualizationPage.tsx` |
| Backend Tests | ✅ | 3 test files |
| Frontend Tests | 🔄 | 1 component test |
| Documentation | 🔄 | This file |

**Current Completion: ~20% (Foundation only)**  
**Next Milestone: API validation + component integration (40%)**
