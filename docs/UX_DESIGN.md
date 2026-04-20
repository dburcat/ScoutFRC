# ScouterFRC — UX Design Documentation

> **Version:** 1.0  
> **Status:** Reference Document  
> **Scope:** Complete UX/UI design reference including wireframes, prototypes, component specifications, and design patterns for ScouterFRC

---

## Table of Contents

1. [Design System](#1-design-system)
2. [Design Principles](#2-design-principles)
3. [User Roles & Personas](#3-user-roles--personas)
4. [Layout & Navigation](#4-layout--navigation)
5. [Page-by-Page Wireframes](#5-page-by-page-wireframes)
6. [Component Specifications](#6-component-specifications)
7. [User Flows & Interactions](#7-user-flows--interactions)
8. [Forms & Input Validation](#8-forms--input-validation)
9. [Data Visualization & Charts](#9-data-visualization--charts)
10. [Mobile & Responsive Design](#10-mobile--responsive-design)
11. [Accessibility Guidelines](#11-accessibility-guidelines)
12. [Design Patterns & Best Practices](#12-design-patterns--best-practices)
13. [Dark Mode](#13-dark-mode)
14. [Real-Time Updates (Phase 2)](#14-real-time-updates-phase-2)
15. [Phase 2 UX Additions](#15-phase-2-ux-additions)
16. [Phase 3 UX Additions](#16-phase-3-ux-additions)
17. [Performance & Loading Strategy](#17-performance--loading-strategy)
18. [Micro-interactions](#18-micro-interactions)
19. [Error Handling UX](#19-error-handling-ux)
20. [Onboarding & Help](#20-onboarding--help)

---

## 1. Design System

### 1.1 Color Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `--color-primary-50` | `#EFF6FF` | Light background tints |
| `--color-primary-100` | `#DBEAFE` | Hover backgrounds |
| `--color-primary-500` | `#3B82F6` | Primary actions, links |
| `--color-primary-600` | `#2563EB` | Primary hover state |
| `--color-primary-700` | `#1D4ED8` | Primary active/pressed |
| `--color-secondary-500` | `#8B5CF6` | Secondary actions, badges |
| `--color-secondary-600` | `#7C3AED` | Secondary hover |
| `--color-success-50` | `#F0FDF4` | Success backgrounds |
| `--color-success-500` | `#22C55E` | Success states, positive stats |
| `--color-success-700` | `#15803D` | Success text |
| `--color-error-50` | `#FEF2F2` | Error backgrounds |
| `--color-error-500` | `#EF4444` | Error states, destructive actions |
| `--color-error-700` | `#B91C1C` | Error text |
| `--color-warning-50` | `#FFFBEB` | Warning backgrounds |
| `--color-warning-500` | `#F59E0B` | Warning states, alerts |
| `--color-warning-700` | `#B45309` | Warning text |
| `--color-neutral-0` | `#FFFFFF` | Page backgrounds, card surfaces |
| `--color-neutral-50` | `#F9FAFB` | Subtle backgrounds |
| `--color-neutral-100` | `#F3F4F6` | Borders, dividers |
| `--color-neutral-200` | `#E5E7EB` | Disabled backgrounds |
| `--color-neutral-400` | `#9CA3AF` | Placeholder text, disabled text |
| `--color-neutral-600` | `#4B5563` | Secondary text |
| `--color-neutral-800` | `#1F2937` | Primary text |
| `--color-neutral-900` | `#111827` | Headings |
| `--color-red-alliance` | `#DC2626` | Red alliance highlighting |
| `--color-blue-alliance` | `#2563EB` | Blue alliance highlighting |

### 1.2 Typography

| Token | Family | Size | Weight | Line Height | Usage |
|-------|--------|------|--------|-------------|-------|
| `--font-display` | Inter, sans-serif | 30px / 1.875rem | 700 | 1.2 | Page titles |
| `--font-h1` | Inter, sans-serif | 24px / 1.5rem | 700 | 1.25 | Section headings |
| `--font-h2` | Inter, sans-serif | 20px / 1.25rem | 600 | 1.3 | Sub-section headings |
| `--font-h3` | Inter, sans-serif | 16px / 1rem | 600 | 1.4 | Card titles, labels |
| `--font-body-lg` | Inter, sans-serif | 16px / 1rem | 400 | 1.6 | Primary body text |
| `--font-body-md` | Inter, sans-serif | 14px / 0.875rem | 400 | 1.6 | Secondary body text |
| `--font-body-sm` | Inter, sans-serif | 12px / 0.75rem | 400 | 1.5 | Captions, footnotes |
| `--font-label` | Inter, sans-serif | 12px / 0.75rem | 500 | 1.4 | Form labels, badges |
| `--font-mono` | JetBrains Mono, monospace | 13px / 0.8125rem | 400 | 1.5 | Code, IDs |

**Font Loading Strategy:** Use `font-display: swap` and preload Inter from Google Fonts CDN for fast initial rendering.

### 1.3 Spacing System (8px Grid)

| Token | Value | Usage |
|-------|-------|-------|
| `--space-1` | 4px | Micro-spacing (icon padding) |
| `--space-2` | 8px | Base unit — tight spacing |
| `--space-3` | 12px | Small gaps |
| `--space-4` | 16px | Standard component padding |
| `--space-5` | 20px | Medium gaps |
| `--space-6` | 24px | Card padding |
| `--space-8` | 32px | Section gaps |
| `--space-10` | 40px | Large section gaps |
| `--space-12` | 48px | Page section gaps |
| `--space-16` | 64px | Hero/banner spacing |
| `--space-20` | 80px | Large page sections |

### 1.4 Shadows & Elevation

| Token | CSS Value | Usage |
|-------|-----------|-------|
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.05)` | Subtle card lift |
| `--shadow-md` | `0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06)` | Cards, dropdowns |
| `--shadow-lg` | `0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05)` | Modals, popovers |
| `--shadow-xl` | `0 20px 25px -5px rgba(0,0,0,0.1), 0 10px 10px -5px rgba(0,0,0,0.04)` | Drawers, sidebars |
| `--shadow-focus` | `0 0 0 3px rgba(59,130,246,0.4)` | Focus ring (accessibility) |

### 1.5 Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | 4px | Buttons, chips, badges |
| `--radius-md` | 8px | Cards, inputs, dropdowns |
| `--radius-lg` | 12px | Modals, panels |
| `--radius-xl` | 16px | Large cards, hero sections |
| `--radius-full` | 9999px | Pills, avatars, toggles |

### 1.6 Icons & Iconography

- **Icon Library:** Heroicons v2 (MIT license) — consistent stroke-based icons
- **Icon Sizes:** 16px (inline), 20px (standard), 24px (prominent), 32px (feature icons)
- **Alliance Icons:** Custom red/blue robot icons at 32×32px
- **FRC Game Icons:** Custom field element icons per season
- **Animated Icons:** Lottie files for loading, success, error animations

```
Standard icon usage:
  Navigation: 20px stroke icons
  Buttons: 16px stroke icons (left-aligned with label)
  Status badges: 12px filled icons
  Empty state illustrations: 64–80px custom SVG
```

---

## 2. Design Principles

### 2.1 User-Centered Design

Every screen and interaction is designed around the primary user's goals during a match day:
- **Scouts** need fast, forgiving data entry forms with one-thumb operation.
- **Coaches** need at-a-glance analytics without cognitive overload.
- **Admins** need clear configuration paths with confirmation steps.

Design decisions are validated against these goals before implementation.

### 2.2 Simplicity & Clarity

- Maximum **3 actions** visible on any card or list row.
- **Progressive disclosure**: advanced options hidden in expandable sections or drawers.
- Labels are always visible (no icon-only controls without tooltip fallback).
- Hierarchy is communicated through size and weight, not color alone.

### 2.3 Accessibility (WCAG 2.1 AA)

- Minimum **4.5:1** contrast ratio for normal text; **3:1** for large text and UI components.
- All interactive elements are keyboard-navigable with a visible focus ring.
- All images and icons have descriptive `aria-label` or `alt` text.
- Form fields include associated `<label>` elements and error descriptions.
- Color is never the sole means of conveying information.

### 2.4 Performance-First

- Time to interactive (TTI) target: **< 2 seconds** on a 4G connection.
- Above-the-fold content renders without JavaScript (SSR or static shell).
- Images are lazy-loaded with `loading="lazy"` and served as WebP.
- Charts render skeletons until data is available.

### 2.5 Mobile-First Approach

- Base CSS targets 320px viewport; larger breakpoints add complexity.
- Touch targets minimum **44×44px** (Apple HIG / Material Design guidelines).
- Form inputs avoid tiny controls; use sliders, toggles, and steppers where appropriate.
- No hover-only interactions.

### 2.6 Consistency Across Pages

- Single shared `<Layout>` component wraps every page.
- A unified design token system (CSS custom properties) ensures visual consistency.
- All data tables, cards, and lists use shared base components.
- Toast notifications always appear bottom-right on desktop, bottom-center on mobile.

---

## 3. User Roles & Personas

### 3.1 Scout

| Attribute | Detail |
|-----------|--------|
| **Age range** | 14–22 years |
| **Device** | Primarily smartphone (iOS/Android), occasionally tablet |
| **Context** | Noisy match pit / stands; time pressure between matches |
| **Goals** | Log team observations quickly; review own history; flag unusual behaviors |
| **Pain Points** | Form too long to fill in 2 minutes; bad cell signal; accidental form reset |
| **Primary Use Cases** | Submit scouting form, view scouting history, look up team stats |

### 3.2 Coach

| Attribute | Detail |
|-----------|--------|
| **Age range** | 25–55 years |
| **Device** | Laptop or tablet; occasionally smartphone |
| **Context** | Alliance selection, pre-match strategy meetings, pit area |
| **Goals** | Identify top-performing teams; compare alliance candidates; build optimal alliance |
| **Pain Points** | Data hidden behind too many clicks; can't compare teams side-by-side; charts too small on tablet |
| **Primary Use Cases** | Analytics dashboard, alliance builder, team comparison, match details |

### 3.3 Team Admin

| Attribute | Detail |
|-----------|--------|
| **Age range** | 25–50 years |
| **Device** | Laptop (desktop-first) |
| **Context** | Pre-event setup, managing scout accounts, exporting data |
| **Goals** | Set up events, manage scouting assignments, download reports |
| **Pain Points** | Can't bulk-import teams; unclear permission hierarchy; no audit log |
| **Primary Use Cases** | User management, event creation/sync, settings, export |

### 3.4 System Admin

| Attribute | Detail |
|-----------|--------|
| **Age range** | 18–40 years (technical) |
| **Device** | Desktop |
| **Context** | Server administration, TBA sync management, CV pipeline monitoring |
| **Goals** | Monitor system health, manage all organizations, configure integrations |
| **Pain Points** | No dashboard for pipeline status; manual DB operations required |
| **Primary Use Cases** | Organization management, system settings, pipeline monitoring, audit logs |

---

## 4. Layout & Navigation

### 4.1 Main Layout Structure

```
┌─────────────────────────────────────────────────────────┐
│  HEADER (64px fixed)                                    │
│  [☰ Logo]  [Events] [Teams] [Matches] [Scouting] [≡]  │
├──────────┬──────────────────────────────────────────────┤
│ SIDEBAR  │  MAIN CONTENT                                │
│ (240px)  │                                              │
│          │  ┌────────────────────────────────────────┐  │
│ • Events │  │  BREADCRUMB                            │  │
│ • Teams  │  ├────────────────────────────────────────┤  │
│ • Match  │  │                                        │  │
│ • Scout  │  │  PAGE CONTENT AREA                     │  │
│ • Ally   │  │                                        │  │
│ • Analyt │  │                                        │  │
│ ─────── │  │                                        │  │
│ Settings │  │                                        │  │
│ Profile  │  └────────────────────────────────────────┘  │
└──────────┴──────────────────────────────────────────────┘
│  FOOTER (48px) — Version | Docs | Status | © ScouterFRC │
└─────────────────────────────────────────────────────────┘
```

### 4.2 Navigation Hierarchy

```
ScouterFRC
├── Events
│   ├── Event Details
│   │   ├── Teams
│   │   ├── Matches
│   │   └── Analytics
│   └── Create Event (Admin)
├── Teams
│   └── Team Profile
├── Matches
│   └── Match Details
├── Scouting
│   ├── New Observation
│   └── History
├── Alliance Builder
│   └── Saved Alliances
├── Analytics
│   ├── Rankings
│   ├── Trends
│   └── Comparison
└── Admin (Team Admin / System Admin only)
    ├── Users
    ├── Organizations (Phase 3)
    └── Settings
```

### 4.3 Responsive Breakpoints

| Breakpoint | Width | Layout Change |
|------------|-------|---------------|
| `xs` | 320px | Single column; hamburger menu; stacked cards |
| `sm` | 640px | Single column; slightly wider content |
| `md` | 768px | Tablet: collapsible sidebar; 2-col cards |
| `lg` | 1024px | Desktop: persistent sidebar (240px); 3-col grids |
| `xl` | 1280px | Wide desktop: sidebar (256px); 4-col grids |
| `2xl` | 1440px | Ultra-wide: max content width 1280px centered |

### 4.4 Breadcrumb Navigation

```
Home > Events > 2025 New England District > Teams > Team 1234
```

- Rendered as `<nav aria-label="Breadcrumb">` with `<ol>` semantics.
- Current page is non-linked and has `aria-current="page"`.
- On mobile (< 768px): show only last 2 segments with `…` truncation.

### 4.5 Footer Structure

```
┌─────────────────────────────────────────────────────────┐
│  ScouterFRC v1.0   Docs   GitHub   Status   © 2025     │
└─────────────────────────────────────────────────────────┘
```

- Minimal footer: version number, documentation link, GitHub link, system status page.
- Not shown on mobile scouting forms to maximize screen real estate.

---

## 5. Page-by-Page Wireframes

### 5.1 Authentication Pages

#### 5.1.1 Login Page

**Route:** `/login`

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│              🤖  ScouterFRC                             │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │                                                   │  │
│  │  Welcome back                                     │  │
│  │  Sign in to your account                          │  │
│  │                                                   │  │
│  │  Username or Email                                │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  scout@team1234.org                        │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │                                                   │  │
│  │  Password                                         │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  ••••••••••••                          👁   │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │                                                   │  │
│  │  [ ] Remember me          Forgot password? →      │  │
│  │                                                   │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │              Sign In                        │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │                                                   │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**States:**
- `default` — blank form
- `loading` — "Sign In" button shows spinner, inputs disabled
- `error` — red alert banner "Invalid credentials. Please try again."
- `success` — redirect to `/` (no visible state)

**Mobile variation:** Full-width card, no surrounding whitespace.

---

#### 5.1.2 Password Reset Page

**Route:** `/reset-password`

```
┌─────────────────────────────────────────────────────────┐
│              🤖  ScouterFRC                             │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Reset your password                              │  │
│  │  Enter your email address and we'll send a link   │  │
│  │                                                   │  │
│  │  Email                                            │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │  scout@team1234.org                        │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │                                                   │  │
│  │  ┌─────────────────────────────────────────────┐  │  │
│  │  │           Send Reset Link                   │  │  │
│  │  └─────────────────────────────────────────────┘  │  │
│  │                                                   │  │
│  │  ← Back to Sign In                               │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Success state:**
```
│  ✅ Email sent!                                         │
│  Check your inbox for a password reset link.           │
│  The link expires in 30 minutes.                       │
```

---

### 5.2 Event Dashboard / Landing Page

**Route:** `/`  **Role:** All authenticated users

```
Desktop (≥ 1024px)
┌─────────────────────────────────────────────────────────────────────┐
│ HEADER: [≡ ScouterFRC]  Events Teams Matches Scouting Alliance  [👤]│
├──────────┬──────────────────────────────────────────────────────────┤
│ SIDEBAR  │  Events                                     [+ New Event]│
│          │  ─────────────────────────────────────────────────────── │
│ ● Events │  [🔍 Search events...]  [Season ▼]  [Location ▼]         │
│   Teams  │                                                          │
│   Match  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│   Scout  │  │ 2025 NE Dist │  │ 2025 CT Dist │  │ 2025 MA Dist │  │
│   Ally   │  │ Bridgeport   │  │ Hartford, CT │  │ Quincy, MA   │  │
│   Analyt │  │ Mar 14–15    │  │ Mar 21–22    │  │ Apr 4–5      │  │
│          │  │ 48 teams     │  │ 36 teams     │  │ 52 teams     │  │
│          │  │ 96 matches   │  │ 72 matches   │  │ 104 matches  │  │
│          │  │ [View →]     │  │ [View →]     │  │ [View →]     │  │
│          │  └──────────────┘  └──────────────┘  └──────────────┘  │
│          │                                                          │
│          │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│          │  │ 2025 NE Chmp │  │ 2025 NewEng  │  │ 2024 Archive │  │
│          │  │ ...          │  │ ...          │  │ ...          │  │
│          │  └──────────────┘  └──────────────┘  └──────────────┘  │
│          │                                                          │
│          │  ← 1  2  3 →  Showing 1–6 of 18 events                 │
└──────────┴──────────────────────────────────────────────────────────┘
```

```
Mobile (< 768px)
┌──────────────────────────┐
│ [☰] ScouterFRC      [👤] │
├──────────────────────────┤
│  Events          [+ Add] │
│  ─────────────────────── │
│  [🔍 Search events...]   │
│  [Season ▼] [Location ▼] │
│                          │
│  ┌──────────────────────┐│
│  │ 2025 NE District     ││
│  │ Bridgeport, CT       ││
│  │ Mar 14–15 · 48 teams ││
│  │ [View →]             ││
│  └──────────────────────┘│
│  ┌──────────────────────┐│
│  │ 2025 CT District     ││
│  │ Hartford, CT         ││
│  │ Mar 21–22 · 36 teams ││
│  │ [View →]             ││
│  └──────────────────────┘│
│  ← 1  2  3 →             │
└──────────────────────────┘
```

**States:**
- `empty` — "No events found. Sync from TBA or create an event." with CTA button.
- `loading` — 3 skeleton event cards.
- `error` — inline error banner with retry button.

---

### 5.3 Event Details Page

**Route:** `/events/:id`

```
┌─────────────────────────────────────────────────────────────────────┐
│ HEADER + SIDEBAR                                                    │
├─────────────────────────────────────────────────────────────────────┤
│  Breadcrumb: Home > Events > 2025 NE District                       │
│                                                                     │
│  2025 New England District Championship                             │
│  📍 Bridgeport, CT    📅 March 14–15, 2025    👥 48 teams           │
│                                        [🔄 Sync TBA]  [⚙ Edit]     │
│                                                                     │
│  ┌──────────┬────────────┬────────────┬────────────┐               │
│  │ Overview │   Teams    │  Matches   │ Analytics  │               │
│  └──────────┴────────────┴────────────┴────────────┘               │
│                                                                     │
│  ── Overview Tab ──────────────────────────────────────────────    │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ 48 Teams │  │ 96 Quals │  │ Avg Score│  │ My Scouts│           │
│  │          │  │ 16 Elim  │  │  72.4 pt │  │  12 obs  │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
│                                                                     │
│  Recent Matches                                          [View All]│
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Qual 42  Mar 14, 2:15 PM   🔴 48+52+61=161  🔵 58+44+55=157 │  │
│  │ Qual 41  Mar 14, 2:00 PM   🔴 71+45+38=154  🔵 62+68+42=172 │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 5.4 Team List View

**Route:** `/events/:id/teams`

```
┌─────────────────────────────────────────────────────────────────────┐
│  Breadcrumb: Home > Events > 2025 NE District > Teams               │
│                                                                     │
│  Teams at 2025 NE District (48)                                     │
│  [🔍 Search by number or name...]  [Sort: Avg Score ▼]              │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │ #1234 · RoboCats │  │ #5678 · IronEagl │  │ #9012 · TechFire │  │
│  │ Elm High · MA    │  │ Oak High · CT    │  │ Pine HS · NH     │  │
│  │ Avg: 87.2 pts    │  │ Avg: 82.1 pts    │  │ Avg: 79.6 pts    │  │
│  │ W 6 / L 2        │  │ W 5 / L 3        │  │ W 5 / L 3        │  │
│  │ [View Profile →] │  │ [View Profile →] │  │ [View Profile →] │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
│  ... (grid continues)                                               │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 5.5 Team Profile Page

**Route:** `/teams/:id`

```
┌─────────────────────────────────────────────────────────────────────┐
│  Breadcrumb: Home > Teams > #1234 RoboCats                          │
│                                                                     │
│  🤖 Team 1234 — RoboCats                           [+ Scout] [📊]  │
│  Elm Street High School · Springfield, MA · Rookie: 2018            │
│                                                                     │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐      │
│  │ Matches: 8 │ │ Wins: 6    │ │ Avg: 87.2  │ │ Best: 121  │      │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘      │
│                                                                     │
│  ── Score History ─────────────────────────────────────────────    │
│  [Line chart: match scores over time]                               │
│                                                                     │
│  ── Match History ─────────────────────────────────────────────    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Qual 1  Red Alliance  Score: 121  WIN  ↗ [View Match]       │   │
│  │ Qual 5  Blue Alliance Score: 88   WIN  → [View Match]       │   │
│  │ Qual 9  Red Alliance  Score: 72   LOSS ↘ [View Match]       │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ── Scouting Notes ────────────────────────────────────────────    │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Scout: Alex B. · Qual 5 · ⭐⭐⭐⭐⭐                         │   │
│  │ "Fast autonomous, consistent speaker shots in teleop"       │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 5.6 Match List View

**Route:** `/events/:id/matches`

```
┌─────────────────────────────────────────────────────────────────────┐
│  Breadcrumb: Home > Events > 2025 NE District > Matches             │
│                                                                     │
│  Matches at 2025 NE District (96)                                   │
│  [Type: All ▼]  [Status: All ▼]  [🔍 Search match number...]        │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Qual 1  · Fri 9:00 AM  🔴 1234, 5678, 9012  🔵 2345, 6789, 0123 │
│  │          Score: 🔴 142  vs  🔵 138   ✅ Completed [View →]       │
│  ├──────────────────────────────────────────────────────────────┤  │
│  │ Qual 2  · Fri 9:15 AM  🔴 ...           🔵 ...                   │
│  │          Score: 🔴 —   vs  🔵 —    ⏳ Scheduled  [View →]        │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ← 1  2  3  4  5 →   Showing 1–20 of 96 matches                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 5.7 Match Details Page

**Route:** `/matches/:id`

```
┌─────────────────────────────────────────────────────────────────────┐
│  Breadcrumb: Home > Events > 2025 NE District > Matches > Qual 1    │
│                                                                     │
│  Qualification Match 1  ·  Fri Mar 14 · 9:00 AM                    │
│                                                                     │
│  ┌─────────────────────────┐   ┌─────────────────────────┐        │
│  │    🔴 RED ALLIANCE      │   │    🔵 BLUE ALLIANCE     │        │
│  │    ─────────────────    │   │    ──────────────────   │        │
│  │  [#1234 RoboCats]       │   │  [#2345 SpeedBot]       │        │
│  │  [#5678 IronEagl]       │   │  [#6789 CircuitBrk]     │        │
│  │  [#9012 TechFire]       │   │  [#0123 FusionTeam]     │        │
│  │                         │   │                         │        │
│  │  FINAL SCORE            │   │  FINAL SCORE            │        │
│  │       142 🏆            │   │       138               │        │
│  └─────────────────────────┘   └─────────────────────────┘        │
│                                                                     │
│  Score Breakdown                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │            │ Auto  │ Teleop │ Endgame │ Penalty │ Total      │  │
│  │ 🔴 Red     │  28   │   82   │   18    │   14    │  142       │  │
│  │ 🔵 Blue    │  24   │   78   │   22    │   14    │  138       │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 5.8 Scouting Form Page

**Route:** `/scouting/new`

```
┌─────────────────────────────────────────────────────────────────────┐
│  Scout Observation                              💾 Draft saved 2s ago│
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  Team *          Match *          Scout           Timestamp         │
│  [#1234 ▼]       [Qual 1 ▼]       Alex B.         Mar 14, 9:02 AM  │
│                                                                     │
│  ── Autonomous ─────────────────────────────────────────────────   │
│  Left Start Line?   [● Yes  ○ No]                                   │
│  Pieces Scored      [─────●──────]  3                               │
│  Mobility Bonus     [● Yes  ○ No]                                   │
│                                                                     │
│  ── Teleop ─────────────────────────────────────────────────────   │
│  Avg Cycles / Min   [─────●──────]  4                               │
│  Primary Zone       [Speaker ▼]                                     │
│  Defense Played     [● Yes  ○ No]                                   │
│                                                                     │
│  ── Endgame ────────────────────────────────────────────────────   │
│  Endgame Action     [Climb ▼]                                       │
│  Climb Successful   [● Yes  ○ No]                                   │
│                                                                     │
│  Overall Rating     ⭐ ⭐ ⭐ ⭐ ☆  (4/5)                            │
│                                                                     │
│  Notes                                                              │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ Fast autonomous routine, missed one shot in teleop but...     │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  [Clear]                               [Save Draft]  [Submit ✓]    │
└─────────────────────────────────────────────────────────────────────┘
```

**States:**
- `auto-save` — "Draft saved 2s ago" badge top-right
- `submitting` — Submit button shows spinner, all fields disabled
- `success` — Green toast "Observation submitted for Team 1234 / Qual 1"
- `error` — Red toast "Submission failed. Draft preserved. Retry?"

---

### 5.9 Scouting History Page

**Route:** `/scouting/history`

```
┌─────────────────────────────────────────────────────────────────────┐
│  My Scouting History  (12 observations)                             │
│  [Team ▼]  [Match ▼]  [Date Range ▼]            [Export CSV]        │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ #1234 RoboCats   Qual 1   Mar 14, 9:02 AM  ⭐⭐⭐⭐⭐         │  │
│  │ "Fast autonomous routine..."               [View] [Edit] [🗑]│  │
│  ├──────────────────────────────────────────────────────────────┤  │
│  │ #5678 IronEagles Qual 3   Mar 14, 9:30 AM  ⭐⭐⭐☆☆         │  │
│  │ "Defensive robot, good blocker..."         [View] [Edit] [🗑]│  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 5.10 Multi-Scout Consensus View

**Route:** `/teams/:id/consensus`

```
┌─────────────────────────────────────────────────────────────────────┐
│  Team 1234 — Scouting Consensus (3 scouts)                          │
│                                                                     │
│  Avg Rating:  ⭐⭐⭐⭐½  (4.3/5)                                    │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ Metric               Scout A   Scout B   Scout C   Average    │ │
│  │ Cycles/Min           4.0       3.5       4.5       4.0        │ │
│  │ Climb Success        Yes       Yes       No        67%        │ │
│  │ Defense              No        Yes       No        33%        │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  Notes Aggregated                                                   │
│  Scout A: "Fast auto, reliable speaker shots"                       │
│  Scout B: "Strong in teleop, tried defense briefly"                 │
│  Scout C: "Failed climb in Qual 5, otherwise consistent"            │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 5.11 Alliance Builder Page

**Route:** `/alliances`

```
┌─────────────────────────────────────────────────────────────────────┐
│  Alliance Builder                           [💾 Save] [📊 Compare]  │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  ┌──────────────────────┐  ┌───────────────────────────────────┐   │
│  │ Team Search          │  │      🔴 RED ALLIANCE              │   │
│  │ [🔍 #1234 or name]   │  │  ┌───────────┐ Drag teams here   │   │
│  │                      │  │  │  #1234    │                   │   │
│  │ Results:             │  │  │ RoboCats  │  ┌───────────┐    │   │
│  │ ┌──────────────────┐ │  │  │ Avg: 87.2 │  │  #5678    │    │   │
│  │ │ #1234 RoboCats   │ │  │  └───────────┘  │ IronEagl  │    │   │
│  │ │ Avg 87.2  W6/L2  │ │  │                 │ Avg: 82.1 │    │   │
│  │ │ [+ Add to Red]   │ │  │                 └───────────┘    │   │
│  │ │ [+ Add to Blue]  │ │  │  [ Drop robot 3 here... ]        │   │
│  │ └──────────────────┘ │  │                                   │   │
│  │ ┌──────────────────┐ │  │  Projected Red Score:  81.5 pts   │   │
│  │ │ #5678 IronEagles │ │  └───────────────────────────────────┘   │
│  │ │ ...              │ │                                           │
│  │ └──────────────────┘ │  ┌───────────────────────────────────┐   │
│  └──────────────────────┘  │      🔵 BLUE ALLIANCE             │   │
│                            │  [ Drop robots here... ]          │   │
│  Saved Alliances           │  Projected Blue Score:  — pts     │   │
│  ┌──────────────────────┐  └───────────────────────────────────┘   │
│  │ Finals Draft A       │                                           │
│  │ Red: 1234,5678,9012  │  Win Probability:  🔴 52%  🔵 48%        │
│  │ Blue: 2345,6789,0123 │                                           │
│  │ [Load] [Delete]      │  [Export CSV]  [Export PDF]              │
│  └──────────────────────┘                                           │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 5.12 Analytics Dashboard

**Route:** `/analytics`

```
┌─────────────────────────────────────────────────────────────────────┐
│  Analytics                    [Event: 2025 NE District ▼]           │
│                                                                     │
│  ┌──────────┬────────────┬──────────────┬────────────┐             │
│  │ Rankings │  Win/Loss  │    Trends    │Comparison  │             │
│  └──────────┴────────────┴──────────────┴────────────┘             │
│                                                                     │
│  ── Rankings Tab ──────────────────────────────────────────────    │
│                                                                     │
│  Top Teams by Average Score                                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ #1234 ████████████████████████████████ 87.2                  │  │
│  │ #5678 ██████████████████████████████   82.1                  │  │
│  │ #9012 █████████████████████████████    79.6                  │  │
│  │ #2345 ████████████████████████████     76.3                  │  │
│  │ ...                                                          │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │ Avg Score    │  │ Top Score    │  │ W/L Leader   │             │
│  │    72.4 pts  │  │   121 pts    │  │   #1234      │             │
│  │   across 96  │  │  #1234 Q1   │  │   W6/L2      │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 5.13 Team Comparison Page

**Route:** `/analytics/compare`

```
┌─────────────────────────────────────────────────────────────────────┐
│  Team Comparison                                                    │
│  [+ Add Team]  (max 3)                                              │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │ Team 1234    │  │ Team 5678    │  │ Team 9012    │             │
│  │ RoboCats     │  │ IronEagles   │  │ TechFire     │             │
│  │ Avg: 87.2    │  │ Avg: 82.1    │  │ Avg: 79.6    │             │
│  │ W6/L2        │  │ W5/L3        │  │ W5/L3        │             │
│  │          [✕] │  │          [✕] │  │          [✕] │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
│                                                                     │
│  [Grouped bar chart: Auto / Teleop / Endgame scores by team]        │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Metric         │ 1234   │ 5678   │ 9012                      │  │
│  │ Auto Points    │ 28.4   │ 21.2   │ 19.7                      │  │
│  │ Teleop Points  │ 48.6   │ 51.3   │ 47.2                      │  │
│  │ Endgame Points │ 10.2   │  9.6   │ 12.7                      │  │
│  │ Avg Score      │ 87.2   │ 82.1   │ 79.6                      │  │
│  │ Win Rate       │ 75%    │ 63%    │ 63%                       │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 5.14 Admin — User Management Page

**Route:** `/admin/users`  **Role:** Team Admin / System Admin

```
┌─────────────────────────────────────────────────────────────────────┐
│  User Management                                    [+ Invite User] │
│  ─────────────────────────────────────────────────────────────────  │
│  [🔍 Search users...]  [Role: All ▼]                                │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Name           Email              Role       Last Login     │  │
│  │  Alex Baker     alex@team1234.org  Scout      Mar 14, 9:10AM │  │
│  │  Jamie Lee      jamie@team1234.org Coach      Mar 13, 6:22PM │  │
│  │  Morgan Patel   morgan@t1234.org   Team Admin Mar 10, 8:00AM │  │
│  │                                           [Edit] [Deactivate]│  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  Pending Invitations                                                │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  sam@team1234.org    Scout    Sent Mar 12    [Resend] [Cancel]│  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

### 5.15 Settings Page

**Route:** `/settings`

```
┌─────────────────────────────────────────────────────────────────────┐
│  Settings                                                           │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  ┌──────────────────────────┐  ┌─────────────────────────────────┐ │
│  │ PROFILE                  │  │ Account Settings                │ │
│  │ Name:  Alex Baker        │  │ Default Event: [2025 NE Dist ▼] │ │
│  │ Email: alex@team.org     │  │ Time Zone:     [US/Eastern ▼]   │ │
│  │ Role:  Scout             │  │ Dark Mode:     [● Off  ○ On]    │ │
│  │ [Edit Profile]           │  │ Notifications: [✓] Email        │ │
│  └──────────────────────────┘  │                [✓] In-app      │ │
│                                │ [Save Settings]                 │ │
│  ┌──────────────────────────┐  └─────────────────────────────────┘ │
│  │ SECURITY                 │                                       │
│  │ [Change Password]        │  ┌─────────────────────────────────┐ │
│  │ [Revoke All Sessions]    │  │ TBA Integration (Admin)         │ │
│  └──────────────────────────┘  │ API Key: ••••••••••••     [Edit]│ │
│                                │ Last Sync: Mar 14, 8:55 AM      │ │
│                                │ [Manual Sync Now]               │ │
│                                └─────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. Component Specifications

### 6.1 EventCard

**Description:** Displays a summary of one FRC event in a card format. Used in the event dashboard grid.

**States:**

| State | Visual |
|-------|--------|
| `default` | White card, shadow-md, event name/location/date/counts |
| `hover` | Shadow-lg elevation, subtle border color shift to primary-100 |
| `loading` | Skeleton: title bar, two lines of meta, one action button |
| `selected` | Primary-500 left border (4px), primary-50 background |

**Props:**

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `event` | `Event` | ✓ | Event data object |
| `onSelect` | `(id: string) => void` | ✓ | Click handler |
| `selected` | `boolean` | — | Highlight when selected |

**Accessibility:** `role="article"`, `aria-label="Event: {name}, {location}"`, keyboard-focusable with Enter/Space.

**Code Example:**

```tsx
// components/EventCard.tsx
import { Event } from '@/types';

interface EventCardProps {
  event: Event;
  onSelect: (id: string) => void;
  selected?: boolean;
}

export function EventCard({ event, onSelect, selected = false }: EventCardProps) {
  return (
    <article
      className={`rounded-lg border p-6 shadow-md cursor-pointer transition-all
        hover:shadow-lg focus-visible:ring-2 focus-visible:ring-primary-500
        ${selected ? 'border-l-4 border-l-primary-500 bg-primary-50' : 'bg-white border-neutral-100'}`}
      onClick={() => onSelect(event.id)}
      onKeyDown={(e) => e.key === 'Enter' && onSelect(event.id)}
      tabIndex={0}
      aria-label={`Event: ${event.name}, ${event.location}`}
      aria-selected={selected}
      role="article"
    >
      <h3 className="font-semibold text-neutral-900">{event.name}</h3>
      <p className="text-sm text-neutral-600 mt-1">
        📍 {event.location} · 📅 {event.startDate}–{event.endDate}
      </p>
      <div className="flex gap-4 mt-3 text-sm text-neutral-500">
        <span>👥 {event.teamCount} teams</span>
        <span>🎮 {event.matchCount} matches</span>
      </div>
    </article>
  );
}
```

---

### 6.2 TeamCard

**Description:** Displays team number, name, school, and key stats. Used in team list grids.

**States:** default, hover, loading (skeleton), selected, compact (for alliance slots)

**Props:**

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `team` | `Team` | ✓ | Team data |
| `stats` | `TeamStats` | — | Win/loss, avg score |
| `compact` | `boolean` | — | Smaller size for alliance builder |
| `draggable` | `boolean` | — | Enable drag-and-drop |
| `onSelect` | `(id: string) => void` | ✓ | Click handler |

**Accessibility:** `role="listitem"`, keyboard drag support with Space/Arrow keys.

**Code Example:**

```tsx
// components/TeamCard.tsx
interface TeamCardProps {
  team: Team;
  stats?: TeamStats;
  compact?: boolean;
  onSelect: (id: string) => void;
}

export function TeamCard({ team, stats, compact = false, onSelect }: TeamCardProps) {
  return (
    <div
      className={`rounded-lg bg-white border border-neutral-100 shadow-sm cursor-pointer
        hover:shadow-md transition-shadow
        ${compact ? 'p-3' : 'p-5'}`}
      onClick={() => onSelect(team.id)}
      tabIndex={0}
      role="listitem"
      aria-label={`Team ${team.number}: ${team.name}`}
    >
      <div className="flex items-center gap-2">
        <span className="font-mono text-lg font-bold text-primary-600">#{team.number}</span>
        <span className="font-semibold text-neutral-800 truncate">{team.name}</span>
      </div>
      {!compact && (
        <>
          <p className="text-sm text-neutral-500 mt-1">{team.school} · {team.city}, {team.state}</p>
          {stats && (
            <div className="flex gap-3 mt-3 text-sm">
              <span className="text-success-700">W {stats.wins}</span>
              <span className="text-error-700">L {stats.losses}</span>
              <span className="text-neutral-600">Avg {stats.avgScore.toFixed(1)}</span>
            </div>
          )}
        </>
      )}
    </div>
  );
}
```

---

### 6.3 MatchCard

**Description:** Compact match summary row showing both alliances and scores.

**States:** default, hover, `scheduled` (no scores), `completed` (shows winner highlight), loading

**Props:**

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `match` | `Match` | ✓ | Match data including alliances |
| `onSelect` | `(id: string) => void` | ✓ | Click handler |

**Code Example:**

```tsx
// components/MatchCard.tsx
export function MatchCard({ match, onSelect }: MatchCardProps) {
  const redWon = match.redScore > match.blueScore;
  return (
    <div
      className="flex items-center justify-between p-4 border-b border-neutral-100
        hover:bg-neutral-50 cursor-pointer"
      onClick={() => onSelect(match.id)}
      tabIndex={0}
      role="listitem"
      aria-label={`${match.type} ${match.number}: Red ${match.redScore ?? '—'} vs Blue ${match.blueScore ?? '—'}`}
    >
      <span className="font-medium text-neutral-700 w-20">
        {match.type} {match.number}
      </span>
      <div className="flex items-center gap-2 text-sm">
        <span className={`font-bold ${redWon ? 'text-red-alliance' : 'text-neutral-500'}`}>
          🔴 {match.redScore ?? '—'}
        </span>
        <span className="text-neutral-400">vs</span>
        <span className={`font-bold ${!redWon && match.blueScore ? 'text-blue-alliance' : 'text-neutral-500'}`}>
          🔵 {match.blueScore ?? '—'}
        </span>
      </div>
      <span className={`text-xs px-2 py-1 rounded-full
        ${match.status === 'completed' ? 'bg-success-50 text-success-700' : 'bg-warning-50 text-warning-700'}`}>
        {match.status === 'completed' ? '✅ Done' : '⏳ Scheduled'}
      </span>
    </div>
  );
}
```

---

### 6.4 AllianceTeamCard (RobotCard)

**Description:** Compact team card used inside alliance builder slots. Supports drag-and-drop.

**States:** default, dragging, drag-over (drop target), empty (placeholder)

**Code Example:**

```tsx
// components/AllianceTeamCard.tsx
export function AllianceTeamCard({ team, alliance, onRemove }: AllianceTeamCardProps) {
  return (
    <div
      draggable
      className={`p-3 rounded-lg border-2 flex justify-between items-center
        ${alliance === 'red'
          ? 'border-red-alliance bg-red-50'
          : 'border-blue-alliance bg-blue-50'}`}
      aria-label={`${alliance} alliance: Team ${team.number} ${team.name}`}
    >
      <div>
        <span className="font-bold font-mono">#{team.number}</span>
        <span className="ml-2 text-sm">{team.name}</span>
      </div>
      <button
        onClick={() => onRemove(team.id)}
        aria-label={`Remove Team ${team.number} from alliance`}
        className="text-neutral-400 hover:text-error-500 p-1 rounded"
      >
        ✕
      </button>
    </div>
  );
}
```

---

### 6.5 StatBox (KPI Display)

**Description:** Single-metric display box with label and value. Used in dashboard summaries.

**Variants:** default, positive (green), negative (red), neutral (gray), large

**Code Example:**

```tsx
// components/StatBox.tsx
interface StatBoxProps {
  label: string;
  value: string | number;
  trend?: 'up' | 'down' | 'neutral';
  variant?: 'default' | 'positive' | 'negative';
}

export function StatBox({ label, value, trend, variant = 'default' }: StatBoxProps) {
  const colors = {
    default: 'bg-white border-neutral-100 text-neutral-900',
    positive: 'bg-success-50 border-success-200 text-success-700',
    negative: 'bg-error-50 border-error-200 text-error-700',
  };
  return (
    <div className={`rounded-lg border p-4 shadow-sm ${colors[variant]}`}
      role="figure" aria-label={`${label}: ${value}`}>
      <p className="text-sm font-medium text-neutral-500">{label}</p>
      <p className="text-2xl font-bold mt-1">{value}</p>
      {trend && (
        <p className="text-xs mt-1">
          {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'}
        </p>
      )}
    </div>
  );
}
```

---

### 6.6 Buttons

| Variant | Use Case | Tailwind Classes |
|---------|----------|-----------------|
| `primary` | Main CTA | `bg-primary-600 text-white hover:bg-primary-700 rounded-md px-4 py-2` |
| `secondary` | Secondary action | `bg-white text-primary-600 border border-primary-300 hover:bg-primary-50` |
| `danger` | Destructive action | `bg-error-600 text-white hover:bg-error-700` |
| `ghost` | Low-emphasis | `text-neutral-600 hover:bg-neutral-100` |
| `icon` | Icon-only | `p-2 rounded-full text-neutral-500 hover:bg-neutral-100` |

**States:** default, hover, focus (ring), active, disabled (opacity-50, cursor-not-allowed), loading (spinner)

**Accessibility:** All buttons have `type` attribute. Loading state adds `aria-busy="true"`. Disabled adds `aria-disabled="true"` (not HTML `disabled` to preserve keyboard focus for context).

---

### 6.7 Form Fields

**Text Input:**
```tsx
// Label always visible, error below field, helper text in neutral-500
<div className="flex flex-col gap-1">
  <label htmlFor="teamNumber" className="text-sm font-medium text-neutral-700">
    Team Number *
  </label>
  <input
    id="teamNumber"
    type="number"
    aria-describedby="teamNumber-error"
    aria-invalid={!!error}
    className="border border-neutral-300 rounded-md px-3 py-2 text-sm
      focus:outline-none focus:ring-2 focus:ring-primary-500
      aria-invalid:border-error-500"
  />
  {error && (
    <p id="teamNumber-error" className="text-xs text-error-600" role="alert">
      {error}
    </p>
  )}
</div>
```

**Select / Dropdown, Checkbox, Slider, Star Rating** follow the same pattern: visible label, associated id, error below.

---

### 6.8 Modals & Dialogs

**Pattern:**
- Triggered by user action (never on page load without reason).
- Background overlay `bg-black/50`.
- Focus trapped inside modal (`focus-trap-react`).
- Closed by Escape key or clicking overlay.
- First focusable element receives focus on open.
- `role="dialog"`, `aria-modal="true"`, `aria-labelledby` pointing to title.

```
┌───────────────────────────────────────────┐
│  Modal Title                          [✕] │
│  ─────────────────────────────────────    │
│  Modal body content / confirmation text   │
│                                           │
│              [Cancel]  [Confirm Action]   │
└───────────────────────────────────────────┘
```

---

### 6.9 Toast Notifications

- Position: bottom-right desktop, bottom-center mobile.
- Auto-dismiss after 5 seconds; pause on hover.
- Maximum 3 toasts stacked; oldest dismissed first.
- Types: `success` (green), `error` (red), `warning` (amber), `info` (blue).
- Each toast has a close `[✕]` button with `aria-label="Dismiss notification"`.

---

### 6.10 Loading States

| Pattern | Usage |
|---------|-------|
| Skeleton loader | Card grids, table rows, chart area |
| Spinner inline | Button loading state |
| Progress bar | File upload, TBA sync |
| Full-page overlay | Critical blocking operations (rare) |

Skeleton example:
```tsx
// components/SkeletonCard.tsx
export function SkeletonCard() {
  return (
    <div className="animate-pulse rounded-lg border border-neutral-100 p-6 bg-white" aria-hidden="true">
      <div className="h-5 bg-neutral-200 rounded w-3/4 mb-3" />
      <div className="h-4 bg-neutral-100 rounded w-1/2 mb-2" />
      <div className="h-4 bg-neutral-100 rounded w-2/3" />
    </div>
  );
}
```

---

### 6.11 Empty States

Every empty state includes:
1. Illustration (64–80px SVG icon)
2. Heading ("No events found")
3. Sub-text (why it's empty + what to do)
4. Primary CTA button (if action available)

```
        🗂️
   No events found

  Sync from The Blue Alliance
  or create an event manually.

   [Sync TBA Events]  [+ New Event]
```

---

### 6.12 Error States

```
        ⚠️
   Failed to load teams

  There was a network error.
  Check your connection and try again.

        [Retry]
```

Component: `<ErrorState error={error} onRetry={refetch} />`  
Accessible: `role="alert"`, `aria-live="assertive"`.

---

## 7. User Flows & Interactions

### 7.1 Authentication Flow

```
[Visit App]
    │
    ▼
[Check Auth Token]
    │
    ├─ Valid ──► [Dashboard /]
    │
    └─ Invalid / Missing
           │
           ▼
       [Login Page]
           │
           ├─ Submit credentials ──► [API POST /auth/login]
           │                               │
           │                        ├─ Success ──► [Store JWT] ──► [Dashboard /]
           │                        │
           │                        └─ Error ──► [Show error banner]
           │
           └─ Forgot password ──► [Reset Password Page]
                                       │
                                       └─ Submit email ──► [API POST /auth/reset]
                                                               │
                                                               └─ [Email sent confirmation]
```

---

### 7.2 Event Exploration Flow

```
[Dashboard /]
    │
    ├─ Browse event cards ──► [EventCard click]
    │                               │
    │                               ▼
    │                        [Event Details /events/:id]
    │                               │
    │                        ┌──────┴───────┐
    │                        │              │
    │                    [Teams tab]   [Matches tab]
    │                        │              │
    │                   [TeamCard]     [MatchCard]
    │                        │              │
    │               [Team Profile      [Match Details
    │               /teams/:id]        /matches/:id]
    │
    └─ Search / filter events ──► [Filtered event list]
```

---

### 7.3 Scouting Submission Flow

```
[Scout lands on /scouting/new]
    │
    ▼
[Form loads with auto-filled Scout + Timestamp]
    │
    ▼
[Select Team (autocomplete)]
    │
    ▼
[Select Match (dropdown)]
    │
    ▼
[Fill fields: auto/teleop/endgame sections]
    │
    ├─ Every 30s ──► [Auto-save draft to localStorage]
    │
    ▼
[Rate overall (stars)]
    │
    ▼
[Add notes (optional)]
    │
    ▼
[Submit]
    │
    ├─ Validation error ──► [Inline field errors, scroll to first error]
    │
    ├─ Network error ──► [Toast: "Submission failed. Draft preserved."]
    │                         └─ [Retry button in toast]
    │
    └─ Success ──► [Toast: "Observation submitted"]
                       └─ [Form resets, ready for next team]
```

---

### 7.4 Alliance Building Flow

```
[Navigate to /alliances]
    │
    ▼
[Search team by number or name]
    │
    ▼
[Results appear in left panel]
    │
    ├─ Drag team to Red/Blue slot  OR  click [+ Add to Red/Blue]
    │
    ▼
[Alliance slot fills; projected score updates in real-time]
    │
    ├─ Fill all 6 slots (3 red + 3 blue)
    │
    ▼
[Win probability displayed]
    │
    ├─ [Save Alliance] ──► [Named & stored; appears in Saved Alliances]
    │
    ├─ [Compare] ──► [Alliance Comparison view]
    │
    └─ [Export CSV/PDF]
```

---

### 7.5 Analytics Viewing Flow

```
[Navigate to /analytics]
    │
    ▼
[Select Event from dropdown]
    │
    ▼
[Rankings tab loads (default)]
    │
    ├─ Switch tab ──► [Win/Loss / Trends / Comparison]
    │
    ├─ Hover chart bar ──► [Tooltip with team name + score]
    │
    ├─ Click legend item ──► [Toggle series visibility]
    │
    ├─ Navigate to Comparison tab
    │       │
    │       └─ [+ Add Team] ──► [Search modal] ──► [Team added to chart]
    │
    └─ [Export PNG] / [Export CSV]
```

---

### 7.6 Admin Configuration Flow

```
[System Admin → /admin]
    │
    ├─ [Users] ──► [User list]
    │                   │
    │                   ├─ [+ Invite User] ──► [Email invite form] ──► [Email sent]
    │                   │
    │                   └─ [Edit user role] ──► [Role dropdown] ──► [Save]
    │
    ├─ [Settings] ──► [TBA API key, default event, etc.]
    │
    └─ [Organizations] (Phase 3) ──► [Multi-org management]
```

---

## 8. Forms & Input Validation

### 8.1 Scouting Observation Form

| Field | Type | Required | Validation | Error Message |
|-------|------|----------|------------|---------------|
| `team_number` | Autocomplete select | ✓ | Must be valid team at event | "Team not found at this event" |
| `match_id` | Dropdown | ✓ | Must be valid match | "Please select a match" |
| `auto_left_line` | Toggle | — | Boolean | — |
| `auto_pieces_scored` | Slider (0–5) | — | 0–5 integer | — |
| `teleop_cycles_per_min` | Slider (0–10) | — | 0–10 float (1 decimal) | — |
| `teleop_primary_zone` | Dropdown | — | Must be from enum | — |
| `endgame_action` | Dropdown | ✓ | Must be from enum | "Please select an endgame action" |
| `overall_rating` | Star (1–5) | ✓ | 1–5 integer | "Please provide a rating" |
| `notes` | Textarea | — | Max 1000 chars | "Notes exceed 1000 characters" |

**Auto-save behavior:** Draft saved to `localStorage` every 30 seconds and on every field blur. Draft restored on page load. Draft cleared on successful submission.

**Success message:** Toast "Observation submitted for Team {number} / {match_type} {match_number}"

---

### 8.2 Event Creation Form

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `tba_event_key` | Text | — | Pattern: `[0-9]{4}[a-z]+` |
| `name` | Text | ✓ | 3–100 chars |
| `location` | Text | ✓ | 3–100 chars |
| `start_date` | Date | ✓ | Must be before end_date |
| `end_date` | Date | ✓ | Must be after start_date |
| `season_year` | Number | ✓ | 2000–2050 |

**TBA Sync button:** When `tba_event_key` is filled, a "Sync from TBA" button appears that auto-fills remaining fields.

---

### 8.3 User Profile Form

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| `username` | Text | ✓ | 3–30 chars, alphanumeric + underscore |
| `email` | Email | ✓ | Valid email format |
| `password` | Password | — | Min 8 chars, 1 uppercase, 1 number |
| `confirm_password` | Password | — | Must match password |
| `team_id` | Select | — | Valid team in system |

---

## 9. Data Visualization & Charts

### 9.1 Team Rankings Chart (Horizontal Bar)

```
Team Rankings — Average Score (Event: 2025 NE District)

#1234  ████████████████████████████████ 87.2
#5678  ██████████████████████████████   82.1
#9012  █████████████████████████████    79.6
#2345  ████████████████████████████     76.3
#6789  ███████████████████████████      73.8
         0        20       40       60       80      100
```

**Data structure:**
```ts
interface RankingsData {
  teamNumber: number;
  teamName: string;
  avgScore: number;
  matchCount: number;
}
```

**Interactions:** Hover bar → tooltip showing team name, avg score, W/L record. Click bar → navigate to Team Profile.  
**Color coding:** Top 3 highlighted in primary-500; remainder in neutral-300.  
**Mobile:** Truncate to top 10; horizontal scroll.

---

### 9.2 Win/Loss Distribution (Pie Chart)

```
         ████ Wins (75%)
         ░░░░ Losses (25%)
              ┌──────────┐
              │ ████████ │
              │ ████░░░░ │
              │ ████░░░░ │
              └──────────┘
```

**Data structure:** `{ wins: number; losses: number; ties: number }`  
**Interactions:** Hover slice → tooltip with exact count and percentage.  
**Color coding:** wins=success-500, losses=error-500, ties=neutral-400.

---

### 9.3 Score Trends (Line Chart)

**Y-axis:** Score (0–150), **X-axis:** Match number (chronological)  
**Multiple series:** One line per selected team (up to 3).  
**Interactions:** Hover → crosshair + per-series tooltip. Click point → Match Details.  
**Mobile:** Pinch-to-zoom; single-series default.

---

### 9.4 Score Distribution (Histogram)

**X-axis:** Score bins (0–20, 20–40, …, 120–140), **Y-axis:** Frequency  
**Data:** All matches at selected event.  
**Interactions:** Hover bin → count + percentage.  
**Accessibility:** `role="img"` with `aria-label` describing distribution summary.

---

### 9.5 Head-to-Head Comparison (Grouped Bar Chart)

**Groups:** Auto / Teleop / Endgame  
**Bars per group:** One per team (max 3 teams, distinguished by color).  
**Color coding:** Team 1=primary-500, Team 2=secondary-500, Team 3=warning-500.  
**Interactions:** Hover bar → tooltip. Click legend → toggle team visibility.

---

### 9.6 Chart Library & Configuration

All charts use **Recharts** (React-native, responsive container).

```tsx
// Shared chart wrapper
<ResponsiveContainer width="100%" height={300}>
  <BarChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
    <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
    <XAxis dataKey="teamNumber" tick={{ fontSize: 12 }} />
    <YAxis tick={{ fontSize: 12 }} />
    <Tooltip content={<CustomTooltip />} />
    <Legend />
    <Bar dataKey="avgScore" fill="#3B82F6" radius={[4, 4, 0, 0]} />
  </BarChart>
</ResponsiveContainer>
```

---

## 10. Mobile & Responsive Design

### 10.1 Mobile-First Approach

CSS is written for 320px (minimum supported width) first. Larger breakpoints use Tailwind's `sm:`, `md:`, `lg:`, `xl:` prefixes to progressively enhance layouts.

### 10.2 Breakpoint Behavior Summary

| Width | Navigation | Cards | Charts | Tables |
|-------|-----------|-------|--------|--------|
| 320px | Hamburger drawer | 1 column | Full width, 200px tall | Horizontal scroll |
| 640px | Hamburger drawer | 1–2 columns | Full width, 250px tall | Horizontal scroll |
| 768px | Collapsible sidebar | 2 columns | Full width, 280px tall | Full visible |
| 1024px | Persistent sidebar | 3 columns | Fixed width, 300px | Full visible |
| 1280px | Persistent sidebar | 4 columns | Fixed width, 320px | Full visible |

### 10.3 Touch-Friendly Design

- Minimum touch target: **44×44px** for all interactive elements.
- Scouting form uses sliders instead of number inputs (easier thumb operation).
- Alliance builder supports both drag-and-drop (desktop) and tap-to-add (mobile).
- Bottom navigation bar on mobile (replaces sidebar):

```
Mobile Bottom Nav (< 768px)
┌───────────────────────────────────────────┐
│  🏠 Events  🤖 Teams  📋 Scout  📊 Stats  │
└───────────────────────────────────────────┘
```

### 10.4 Mobile Navigation (Hamburger Menu)

```
┌──────────────────────────┐
│ [✕]  ScouterFRC          │
│ ────────────────────── │
│ 🏠 Events                │
│ 👥 Teams                 │
│ 🎮 Matches               │
│ 📋 Scouting              │
│ 🤝 Alliance Builder      │
│ 📊 Analytics             │
│ ──────────────────────── │
│ ⚙️ Settings               │
│ 👤 Profile (Alex B.)     │
│ 🚪 Sign Out              │
└──────────────────────────┘
```

### 10.5 Mobile Form Optimization

- Labels above fields (never inline/floating for clarity on small screens).
- Large tap targets for checkboxes and radio buttons (min 44px).
- Keyboard type hints: `inputMode="numeric"` for numbers, `type="email"` for email.
- Scroll to first validation error automatically.
- Auto-save prevents data loss when switching apps.

---

## 11. Accessibility Guidelines

### 11.1 WCAG 2.1 AA Compliance Checklist

| Criterion | Implementation |
|-----------|---------------|
| 1.1.1 Non-text Content | All images, icons, and charts have `alt` / `aria-label` |
| 1.3.1 Info and Relationships | Semantic HTML: `<nav>`, `<main>`, `<article>`, `<section>`, `<header>` |
| 1.4.3 Contrast (Minimum) | All text ≥ 4.5:1 contrast; large text ≥ 3:1 |
| 1.4.4 Resize Text | Layout holds at 200% browser zoom without horizontal scroll |
| 2.1.1 Keyboard | All functionality accessible via keyboard |
| 2.4.2 Page Titled | Every page has a descriptive `<title>` |
| 2.4.3 Focus Order | Focus follows logical reading order |
| 2.4.7 Focus Visible | Visible focus ring on all interactive elements |
| 3.1.1 Language of Page | `<html lang="en">` |
| 3.2.1 On Focus | No context changes on focus |
| 3.3.1 Error Identification | Errors identified in text, not color alone |
| 3.3.2 Labels or Instructions | All form fields have visible labels |
| 4.1.2 Name, Role, Value | All custom components use ARIA roles/states |
| 4.1.3 Status Messages | Toast/alert messages use `role="status"` or `role="alert"` |

### 11.2 Color Contrast Ratios

| Combination | Ratio | Pass? |
|-------------|-------|-------|
| neutral-800 on white | 12.6:1 | ✅ AAA |
| neutral-600 on white | 7.2:1 | ✅ AA |
| neutral-400 on white | 3.1:1 | ⚠️ (large text only) |
| primary-600 on white | 5.9:1 | ✅ AA |
| error-600 on white | 5.8:1 | ✅ AA |
| white on primary-600 | 5.9:1 | ✅ AA |
| white on error-600 | 5.8:1 | ✅ AA |

### 11.3 Keyboard Navigation Paths

```
Tab order for Event Dashboard:
1. Skip to main content link (visible on focus)
2. Header: Logo → Events nav → Teams → Matches → Scouting → Alliance → Analytics → User menu
3. Main: Search input → Filter dropdowns → Event cards (each card: focus, Enter=select) → Pagination
4. Sidebar: Navigation links (active link has aria-current="page")
```

### 11.4 ARIA Usage

```tsx
// Page landmarks
<header role="banner">
<nav aria-label="Main navigation">
<main aria-label="Page content">
<aside aria-label="Sidebar navigation">
<footer role="contentinfo">

// Live regions
<div aria-live="polite" aria-atomic="true"> // for toast notifications
<div role="alert" aria-live="assertive">   // for errors

// Forms
<fieldset>
  <legend>Autonomous Performance</legend>
  ...
</fieldset>

// Loading
<div aria-busy="true" aria-label="Loading events...">
  <SkeletonCard />
</div>
```

---

## 12. Design Patterns & Best Practices

### 12.1 Empty States

Every list and data-heavy page must have a designed empty state.

| Context | Illustration | Heading | Sub-text | CTA |
|---------|-------------|---------|----------|-----|
| No events | 📅 calendar | "No events yet" | "Sync from TBA or create an event" | [Sync TBA] |
| No teams | 🤖 robot | "No teams found" | "Try adjusting your search filters" | [Clear filters] |
| No scouting | 📋 clipboard | "No observations yet" | "Scout your first team to get started" | [New Observation] |
| No matches | 🎮 gamepad | "No matches scheduled" | "Matches will appear when the event is synced" | [Sync TBA] |

### 12.2 Loading States

- **Skeleton loaders** (not spinners) for content-rich areas (card grids, tables).
- **Inline spinner** for button loading states and small updates.
- **Progress bar** for long operations (TBA sync, CSV export).
- Loading state preserves exact layout dimensions to prevent layout shift (CLS).

### 12.3 Error States

| Error Type | Display | Recovery |
|-----------|---------|---------|
| Network error | Inline error panel with retry | [Retry] button |
| Form validation | Field-level inline messages | Fix field, re-submit |
| 404 Not Found | Full-page 404 with navigation | [Go Home] |
| 500 Server Error | Full-page 500 with message | [Retry] / [Go Home] |
| Auth expired | Toast + redirect to login | Auto-redirect |

### 12.4 Success States

- **Toast notification** for non-blocking successes (form submitted, sync complete).
- **Inline confirmation** for in-place edits (field saved indicator).
- **Page transition** for multi-step flows (redirected to result).

### 12.5 Confirmation Dialogs

Used for **destructive or irreversible** actions only:
- Delete user, delete event, clear scouting data.
- Pattern: Modal with clear action description, "Cancel" (secondary) and "Delete" (danger) buttons.
- Keyboard: Enter confirms, Escape cancels.

```
┌───────────────────────────────────────┐
│  Delete Observation                   │
│  ─────────────────────────────────    │
│  Are you sure you want to delete      │
│  this observation? This cannot        │
│  be undone.                           │
│                                       │
│             [Cancel]  [Delete ⚠️]     │
└───────────────────────────────────────┘
```

### 12.6 Search & Filter Patterns

- Search field is always the first control, with `aria-label="Search {context}"`.
- Filters are secondary (dropdowns or collapsible panel on mobile).
- Active filters shown as dismissible chips below the search bar.
- "Clear all filters" link visible when any filter is active.
- Results count updates in real-time as filters change.

### 12.7 Pagination vs Infinite Scroll

| Context | Pattern | Reason |
|---------|---------|--------|
| Event list | Pagination (10/page) | Bookmarkable URLs |
| Team list | Pagination (12/page) | Large lists, stable URLs |
| Match list | Pagination (20/page) | Stable, filterable |
| Scouting history | Pagination (20/page) | Auditable |
| Alliance comparison | N/A (all visible) | Small dataset |

---

## 13. Dark Mode

### 13.1 Dark Mode Color Scheme

| Light Token | Dark Value | Usage |
|-------------|-----------|-------|
| `bg-white` | `#1E2433` | Card backgrounds |
| `bg-neutral-50` | `#161B27` | Page backgrounds |
| `text-neutral-900` | `#F9FAFB` | Primary text |
| `text-neutral-600` | `#D1D5DB` | Secondary text |
| `border-neutral-100` | `#374151` | Borders |
| `primary-500` | `#60A5FA` | Primary actions (lighter for dark bg) |
| `success-500` | `#4ADE80` | Success states |
| `error-500` | `#F87171` | Error states |

### 13.2 Dark Mode Toggle

```tsx
// Settings page toggle
<div className="flex items-center justify-between">
  <label htmlFor="darkMode" className="text-sm font-medium">Dark Mode</label>
  <button
    id="darkMode"
    role="switch"
    aria-checked={isDark}
    onClick={toggleDark}
    className={`relative inline-flex h-6 w-11 rounded-full transition-colors
      ${isDark ? 'bg-primary-600' : 'bg-neutral-300'}`}
    aria-label="Toggle dark mode"
  >
    <span className={`inline-block h-5 w-5 rounded-full bg-white shadow transition-transform
      ${isDark ? 'translate-x-5' : 'translate-x-0.5'}`} />
  </button>
</div>
```

### 13.3 Persistence Strategy

- Store preference in `localStorage` key `scouterfrc-theme`.
- On app load, read from localStorage; fall back to `prefers-color-scheme` media query.
- Apply `class="dark"` on `<html>` element; Tailwind's `darkMode: 'class'` handles the rest.

---

## 14. Real-Time Updates (Phase 2)

### 14.1 Live Update Indicators

```
┌────────────────────────────────┐
│  Match 42                 🟢 LIVE │
│  🔴 142  vs  🔵 138              │
│  ─────────────────────────────   │
│  Last updated: 2s ago     ↻       │
└────────────────────────────────┘
```

- Green dot with "LIVE" badge when WebSocket is connected and match is active.
- "Last updated: {N}s ago" timestamp auto-refreshes every second.
- Manual refresh icon for users who prefer not to use auto-refresh.

### 14.2 WebSocket Connection Status

| State | Indicator | Location |
|-------|-----------|---------|
| Connected | 🟢 "Live" | Header (right of logo) |
| Connecting | 🟡 "Connecting…" | Header |
| Disconnected | 🔴 "Offline — retrying" | Header + banner |
| Error | ⚠️ "Connection error" | Banner below header |

### 14.3 Connection Loss Handling UI

```
┌─────────────────────────────────────────────────────────────────────┐
│ ⚠️  Live connection lost. Showing last known data.  [Reconnect]    │
└─────────────────────────────────────────────────────────────────────┘
```

Banner is `role="alert"` and `aria-live="assertive"`. Auto-reconnect attempts with exponential backoff (1s, 2s, 4s, 8s, max 30s).

---

## 15. Phase 2 UX Additions

### 15.1 Field Heatmap Visualization

```
┌────────────────────────────────────────────────────────────┐
│  Team 1234 — Field Presence Heatmap  [Qual 1]  [Export]   │
│  ──────────────────────────────────────────────────────    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  🟥🟥🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟥🟥  (field top)    │  │
│  │  ░░░░░▒▒▒▒▓▓▓▓▓▓▓▓▒▒▒▒░░░░░░░░░░░░  (heat overlay) │  │
│  │  ░░░░░░░░░░▒▒▒▒▒▒░░░░░░░░░░░░░░░░░░                 │  │
│  │  (field bottom)                                      │  │
│  └──────────────────────────────────────────────────────┘  │
│  Legend: Cold (blue) → Hot (red)   Phase: [All ▼]          │
└────────────────────────────────────────────────────────────┘
```

- Rendered with D3.js + canvas overlay on Konva.js field background.
- Phase selector: Auto / Teleop / Endgame / All.
- Opacity slider: adjust heatmap intensity.
- Export as PNG.

### 15.2 Robot Trajectory Playback

```
┌────────────────────────────────────────────────────────────┐
│  Trajectory Playback — Qual 1                              │
│  ──────────────────────────────────────────────────────    │
│  [Field with animated robot paths]                         │
│  ────────────────────────────────────────────────────      │
│  ◀◀  ▶  ▶▶     [===========●════]  1:24 / 2:30           │
│  Speed: [0.5x ▼]  Teams: [✓1234 ✓5678 ✓9012]              │
└────────────────────────────────────────────────────────────┘
```

### 15.3 Mobile PWA UX

- Install prompt shown after 2nd visit: "Add ScouterFRC to Home Screen".
- Offline banner: "You're offline. Data will sync when reconnected."
- Sync status icon in header: 🔄 syncing / ✅ synced / ⚠️ sync failed.
- Scouting form works fully offline; submissions queued in IndexedDB.

---

## 16. Phase 3 UX Additions

> ⚠️ Phase 3 is speculative planning. Implementation timeline is not defined.

### 16.1 AI Coach Recommendations Panel

```
┌─────────────────────────────────────────────────────────────────────┐
│  🤖 AI Coach Recommendations         Alliance Selection Rd 1        │
│  ─────────────────────────────────────────────────────────────────  │
│  📊 Recommended Alliance:                                           │
│  1st Pick: #1234 RoboCats (87.2 avg, strong auto)                   │
│  2nd Pick: #5678 IronEagles (82.1 avg, endgame specialist)          │
│  Projected Score: 94.7 pts (win probability: 73%)                   │
│                                                                     │
│  ⚠️ Avoid: #0123 FusionTeam (failed climb 60% of matches)           │
│                                                                     │
│  [Explain Reasoning]  [Apply to Alliance Builder]                   │
└─────────────────────────────────────────────────────────────────────┘
```

### 16.2 Multi-Organization Switcher

```
Header: [≡ ScouterFRC]  [🏫 Team 1234 ▼]  ...

Dropdown:
┌─────────────────────────────────┐
│  🏫 Team 1234 — RoboCats  ✓    │
│  🏫 Team 5678 — IronEagles     │
│  🏢 NE District Coalition      │
│  ─────────────────────────────  │
│  [+ Join/Create Organization]   │
└─────────────────────────────────┘
```

### 16.3 Community Features

- Strategy forum integrated in sidebar (Phase 3 Tier 5+).
- Shared scouting data with opt-in inter-team visibility.
- Team strategy library with match video links.

---

## 17. Performance & Loading Strategy

### 17.1 Above-the-Fold Content

The event dashboard renders a loading shell (header + sidebar + skeleton cards) within **< 1 second** on a 4G connection:

1. Static HTML shell (header, nav structure) — served immediately.
2. Skeleton card grid — rendered by React before data arrives.
3. Event data — fetched via React Query, replaces skeletons when ready.

### 17.2 Lazy Loading Strategy

```tsx
// Route-based code splitting
const AllianceBuilder = lazy(() => import('@/pages/AllianceBuilder'));
const Analytics = lazy(() => import('@/pages/Analytics'));
const AdminPanel = lazy(() => import('@/pages/Admin'));

// Component-level lazy loading
const HeavyChart = lazy(() => import('@/components/charts/TrajectoryChart'));
```

| Resource | Strategy |
|----------|---------|
| Route bundles | React.lazy + Suspense |
| Charts | Lazy-loaded on first render |
| Images | `loading="lazy"` + WebP format |
| Icons | SVG sprites (single HTTP request) |
| Fonts | Preload + font-display: swap |

### 17.3 Skeleton Loaders for Content

Skeleton dimensions match exact final content dimensions to prevent Cumulative Layout Shift (CLS < 0.1).

```tsx
// Skeleton replaces EventCard during load
{isLoading
  ? Array(6).fill(0).map((_, i) => <SkeletonCard key={i} />)
  : events.map(e => <EventCard key={e.id} event={e} />)
}
```

### 17.4 Estimated Load Times

| Page | First Load | Subsequent (cached) |
|------|-----------|---------------------|
| Login | < 1s | < 0.3s |
| Dashboard | < 2s | < 0.5s |
| Event Details | < 1.5s | < 0.4s |
| Analytics (charts) | < 2.5s | < 0.8s |
| Alliance Builder | < 2s | < 0.6s |

---

## 18. Micro-interactions

### 18.1 Button Hover Effects

```css
/* Smooth color transition, no layout shift */
.btn-primary {
  transition: background-color 150ms ease, box-shadow 150ms ease;
}
.btn-primary:hover {
  background-color: var(--color-primary-700);
  box-shadow: var(--shadow-md);
}
```

### 18.2 Smooth Page Transitions

```tsx
// Fade in on route change
<AnimatePresence>
  <motion.div
    key={location.pathname}
    initial={{ opacity: 0, y: 8 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0 }}
    transition={{ duration: 0.15 }}
  >
    <Outlet />
  </motion.div>
</AnimatePresence>
```

### 18.3 Loading Animations

- **Skeleton pulse:** `animate-pulse` Tailwind utility (fade in/out, 1.5s).
- **Spinner:** 360° CSS rotation, 0.8s linear infinite.
- **Progress bar:** Smooth width transition at 60fps.

### 18.4 Alliance Builder Drag-and-Drop Feedback

- Card lifts with `transform: scale(1.05)` + shadow-lg while dragging.
- Drop zone glows with primary-100 background and dashed primary-400 border when drag-over.
- Snap animation (`spring` easing) when card drops into slot.
- Shake animation if dropped in invalid slot.

### 18.5 Form Success Animation

After successful scouting submission:
1. Submit button turns green with checkmark (200ms).
2. Form fades out (150ms).
3. "Observation submitted" toast slides up from bottom (200ms).
4. Form resets and fades back in (150ms).

### 18.6 Error Shake Animation

```css
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  20%       { transform: translateX(-8px); }
  40%       { transform: translateX(8px); }
  60%       { transform: translateX(-4px); }
  80%       { transform: translateX(4px); }
}
.error-shake { animation: shake 400ms ease; }
```

Applied to form container on validation failure.

---

## 19. Error Handling UX

### 19.1 Error Hierarchy

| Level | Example | Display Pattern |
|-------|---------|----------------|
| Field validation | "Team number required" | Inline below field |
| Form-level | "Please fix 3 errors" | Banner above form |
| Network error | "Failed to load events" | Inline error panel with retry |
| Auth error | "Session expired" | Toast + redirect |
| 404 Not Found | Unknown route | Full-page 404 |
| 500 Server Error | API crash | Full-page 500 with support link |
| Offline | No network | Top banner |

### 19.2 Error Messages

All error messages follow the pattern:  
**What happened** + **Why** (if known) + **What to do next**

| Scenario | Message |
|----------|---------|
| Network timeout | "Couldn't connect to the server. Check your internet connection and try again." |
| Invalid login | "Incorrect username or password. Please try again." (never specify which is wrong) |
| TBA sync failed | "TBA sync failed. The Blue Alliance API may be temporarily unavailable." |
| Form invalid | "Please fix the highlighted fields before submitting." |
| Session expired | "Your session has expired. Please sign in again." |
| Missing permissions | "You don't have permission to view this page." |

### 19.3 Full-Page Error States

**404:**
```
         🤖
    Page not found

  The page you're looking for
  doesn't exist or has been moved.

  [Go to Dashboard]  [Go Back]
```

**500:**
```
         ⚙️
    Something went wrong

  We encountered an unexpected error.
  Our team has been notified.

  [Retry]  [Go to Dashboard]
```

### 19.4 Offline State

```
┌─────────────────────────────────────────────────────────────────────┐
│ 📡  You're offline. Showing cached data. Scouting forms still work. │
└─────────────────────────────────────────────────────────────────────┘
```

- Cached data is shown with a "Cached" badge.
- Scouting forms queue submissions in IndexedDB (Phase 2 PWA feature).
- When reconnected: "Back online. Syncing queued data…" banner.

---

## 20. Onboarding & Help

### 20.1 First-Time User Experience

On first login, new users see a welcome modal:

```
┌─────────────────────────────────────────────────────────────────────┐
│  👋 Welcome to ScouterFRC!                                          │
│  ─────────────────────────────────────────────────────────────────  │
│  Let's help you get started:                                        │
│                                                                     │
│  1. Browse events and teams from The Blue Alliance                  │
│  2. Submit scouting observations during matches                     │
│  3. Use the Alliance Builder to plan your picks                     │
│  4. Analyze team performance in the Analytics dashboard             │
│                                                                     │
│  [Skip Tour]                             [Start Quick Tour →]       │
└─────────────────────────────────────────────────────────────────────┘
```

### 20.2 Guided Tour Steps

Using a lightweight tooltip-based tour (e.g., Shepherd.js):

1. **Events** — "Here you'll find all FRC events. Click one to explore."
2. **Teams** — "Browse teams attending the event and view their stats."
3. **Scouting** — "Submit your observations here. Forms auto-save as you type."
4. **Alliance Builder** — "Drag teams to build and compare alliances."
5. **Analytics** — "Charts and rankings to inform your strategy."

Each step: tooltip with title, description, [Previous] [Next] [Skip].

### 20.3 Help Tooltips

Context-sensitive `?` icons throughout the UI:

```tsx
<label className="flex items-center gap-1">
  Win Probability
  <HelpTooltip content="Calculated from the combined average scores of both alliances using historical data." />
</label>
```

Tooltip delays 300ms before appearing; accessible via keyboard focus.

### 20.4 Feature Discovery

- **New badge:** `NEW` chip on recently added nav items (shown for 14 days after release).
- **Inline callout:** First time a user visits Alliance Builder, a highlighted tip explains drag-and-drop.
- **Empty state CTAs** guide users to the most relevant next action.

### 20.5 In-App Help

- `?` icon in header links to documentation.
- Keyboard shortcut `Shift+?` opens keyboard shortcut cheatsheet modal.
- Footer links to GitHub issues for bug reports.

---

*ScouterFRC UX Design Documentation — Version 1.0*  
*Last Updated: 2025*  
*Maintained by: ScouterFRC Team*
