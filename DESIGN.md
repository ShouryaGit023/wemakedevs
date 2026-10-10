# Design System: Municipal Civic Resilience
**Project:** ClimateShield AMC (Ahmedabad Municipal Corporation)  
**Framework:** Climate Risk Decision Support System & Command Operations Desk  
**Generated via:** Stitch MCP Design Inspection  

---

## 1. Executive Summary & Brand Architecture

The **Municipal Civic Resilience** design system establishes an authoritative, institutional, civic-grade interface engineered for high-stakes municipal climate risk monitoring, emergency response mobilization, and intervention outcome verification.

### Target Audience & Operational Tone
- **Audience:** City administrators, municipal health officers (CMHO), disaster response coordinators, GIS cartographers, and municipal commissioners.
- **Visual Aesthetic:** Blends **Corporate / Modern Civic Precision** with **Tactile / Structural Minimalism**.
- **Operational Clarity:** High-contrast data density, unambiguous hazard level distinctions, and monospace telemetry streams designed to eliminate cognitive fatigue in high-stress command environments.
- **Color Philosophy:** Anchored in deep forest greens (`#144534`) to convey governmental stability and calm stewardship, while strictly isolating hazard alert colors (crimson, amber, emerald, hydrological cyan) for instant cognitive triage.

---

## 2. Screens Overview

Stitch MCP identified **3 production-grade desktop command screens** in project `ClimateShield Ahmedabad Dashboard` (ID: `382702947700919894`):

### Screen 1: Ahmedabad Climate Vulnerability & Incident Overview
- **Screen ID:** `0bece176b4b6412f9495c0d038612f5b`
- **Resolution:** 2560 × 2048 (Desktop Command Display)
- **Role:** High-level executive situational awareness and spatial hazard distribution.
- **Core Layout & Modules:**
  1. **Persistent Sidebar Navigation:** Fixed 260px (w-64) sidebar with AMC institutional branding, 6 core tabs, emergency "Issue Advisory" button, and live telemetry sensor health box (`48/48 Wards reporting`).
  2. **Top App Bar:** Jurisdiction selector dropdown (`Ahmedabad - All 48 Wards / 7 Zones`), live IMD & AMC sensor stream sync indicator, real-time heat & Sabarmati river pill, alert notifications counter, and municipal commissioner profile.
  3. **Executive KPI Strip:** 5 high-density cards tracking *High-Risk Wards*, *Heat Stress Index*, *Waterlogging Stress*, *Dual-Hazard Compound Wards*, and *Active Interventions*.
  4. **Central Tactical Bento (7:5 Split):**
     - **Left (7 Columns):** Interactive vector SVG ward map of Ahmedabad with 48 ward polygons, Sabarmati river channel, composite risk color shading, floating Danilimda ward inspection card, top-right HUD zoom/pan controls, and top-left Composite Risk Index legend.
     - **Right (5 Columns):** Top 5 Highest-Risk Priority Wards ranking table with composite risk scores, primary risk factors, and individual "Inspect" actions.

### Screen 2: Action Centre & Field Operations Tracker
- **Screen ID:** `1805b3c40f84476d87b82c73ded13bb4`
- **Resolution:** 2560 × 2048 (Desktop Command Display)
- **Role:** Tactical execution tracking, field team dispatching, blocker resolution, and SLA adherence.
- **Core Layout & Modules:**
  1. **Top App Bar & Search:** Instant search for wards, sensors, and alert codes; emergency dispatch shortcut button.
  2. **Operational KPI Strip:** 5 metrics with mini visual progress rails:
     - *Active Deployments:* 29 Ongoing across 14 high-risk wards (82% progress rail).
     - *Critical Blockers:* 3 Pending Resolution (gradient crimson alert card with 60% severity rail).
     - *On-Time Execution:* 91.4% (SLA target ≥ 90.0%, emerald rail).
     - *Teams Mobilized:* 18 Wings Active (Health, Engineering, Fire, Forestry).
     - *Daily Target Progress:* 68% (29/42 Ops completed in shift window).
  3. **Operational Controls Toolbar:** Filter View, CSV Export, and "Deploy New Operation" primary CTA.
  4. **Operations Matrix & Escalation Desk:** Multi-ward tabular dispatch log pairing field crew tags with live execution statuses.

### Screen 3: Impact Verification & Outcome Telemetry
- **Screen ID:** `80e0d13816de4721ae2ec771fdc0ab33`
- **Resolution:** 2560 × 2048 (Desktop Command Display)
- **Role:** Empirical post-intervention evaluation, baseline vs. follow-up telemetry comparison, statistical significance auditing, and municipal ROI.
- **Core Layout & Modules:**
  1. **Audit KPI Summary Grid:** *Total Verified (42)*, *Mean Surface Temp Drop (-6.8°C)*, *Runoff Mitigation (34.2%)*, *Evidence Confidence (94.1% Grade A)*, and *Outcome Audit (28 Exceeded / 11 Met / 3 Under)*.
  2. **Hazard & Evidence Filter Toolbar:** Hazard category pills (*All Hazards*, *Heatwave*, *Water Stress*, *Urban Flooding*), Ward selection, Evidence Tier selector, and Status filter.
  3. **Methodological Rigor Banner:** Explicit visual segregation between Tier 1 (Ground IoT thermistors), Tier 2 (Satellite radiance: Landsat-9/Sentinel-2), and Tier 3 (Hydrodynamic simulation: EPA SWMM).
  4. **Telemetry Audit Bento Grid (8:4 Split):**
     - **Left (8 Columns):** Dense intervention audit cards (e.g., *Gomtipur Ward Cool Roofs*, *Danilimda Stormwater Recharge Wells*, *Odhav Urban Canopy & Misting*) displaying baseline vs. follow-up values, percentage delta drops, and dual-tone comparison rails.
     - **Right (4 Columns):** Spotlight Deep-Dive Dossier featuring a **24-Hour Diurnal Surface Temperature Profile bar chart** comparing uncoated baseline vs. coated roofs across 7 time points with peak delta callout tag (`-11.1°C at 13:00 IST`).

---

## 3. Color Palette & Theming Tokens

### 3.1 Surface & Neutral Canvas Architecture
| Token Name | Hex Code | Description / Usage |
| :--- | :--- | :--- |
| `surface-canvas` | `#F4F6F4` | App canvas background with subtle mineral tint |
| `surface` / `background` | `#F8F9FF` | Primary default canvas background |
| `surface-bright` | `#F8F9FF` | Elevated card backings & input fields |
| `surface-container-lowest` | `#FFFFFF` | Primary card faces, modals, sidebars, top headers |
| `surface-container-low` | `#EFF4FF` | Hover states for navigation items, secondary table rows |
| `surface-container` | `#E5EEFF` | Active navigation pill backgrounds, container chips |
| `surface-container-high` | `#DCE9FF` | Active accent containers |
| `surface-container-highest` | `#D3E4FE` | Prominent highlights, badge backdrops |
| `surface-variant` | `#D3E4FE` | Subtle structural division tint |
| `surface-dim` | `#CBDBF5` | Dimmed operational backdrops |
| `inverse-surface` | `#213145` | Contrast tooltips and dark overlays |
| `inverse-on-surface` | `#EAF1FF` | Text on inverse surfaces |

### 3.2 Primary Governance & Civic Accents
| Token Name | Hex Code | Description / Usage |
| :--- | :--- | :--- |
| `primary` | `#002E20` / `#144534` | Deep Forest Green; represents municipal authority, brand identity, header titles, active states |
| `on-primary` | `#FFFFFF` | High-contrast white text on primary fills |
| `primary-container` | `#144534` | Primary button fill, brand avatar background |
| `on-primary-container` | `#81B29C` | Mint/sage contrast accents on primary containers |
| `inverse-primary` | `#A0D1BA` | Light mint for dark backgrounds |
| `primary-fixed` | `#BBEED5` | Light mint fixed chip fill |
| `primary-fixed-dim` | `#A0D1BA` | Muted mint chip fill |
| `on-primary-fixed` | `#002116` | Dark green text on fixed mint chips |
| `on-primary-fixed-variant` | `#204F3D` | Medium green text on fixed mint chips |

### 3.3 Secondary & Environmental Accents
| Token Name | Hex Code | Description / Usage |
| :--- | :--- | :--- |
| `secondary` | `#406840` / `#588157` | Sage Moss; sub-navigation anchors, baseline environmental layers |
| `on-secondary` | `#FFFFFF` | Text on secondary fills |
| `secondary-container` | `#BEECB9` / `#F0F5F1` | Secondary action buttons, subtle tags |
| `on-secondary-container` | `#446C44` | Text on secondary container fills |
| `secondary-fixed` | `#C1EEBC` | Soft green accent chip |
| `secondary-fixed-dim` | `#A5D2A2` | Muted soft green accent |
| `on-secondary-fixed` | `#002106` | Deep green text on secondary chips |

### 3.4 Tertiary & Hydrological Accents (Water, Drainage, Rivers)
| Token Name | Hex Code | Description / Usage |
| :--- | :--- | :--- |
| `tertiary` | `#002943` | Deep navy; hydrological governance |
| `tertiary-container` | `#004064` / `#0284C7` | Sabarmati river channel, waterlogging telemetry, runoff data |
| `on-tertiary` | `#FFFFFF` | Text on tertiary fills |
| `on-tertiary-container` | `#50AEF4` | Light cyan text on deep blue containers |
| `tertiary-fixed` | `#CCE5FF` | Soft sky blue chip |
| `tertiary-fixed-dim` | `#93CCFF` | Sky blue indicator |
| `on-tertiary-fixed` | `#001D31` | Deep blue text on sky blue chips |

### 3.5 Hazard Alert & Operational Status Hierarchy
Hazard states are strictly decoupled from brand colors to guarantee instant cognitive parsing:
| Hazard Level | Text / Accent Hex | Background Hex | Border Hex | Standard Usage |
| :--- | :--- | :--- | :--- | :--- |
| **Normal / Low Risk** | `#059669` / `#065F46` | `#ECFDF5` | `#A7F3D0` | Risk < 40%, nominal heat index, operational sensors, target met |
| **Moderate / Advisory** | `#D97706` / `#92400E` | `#FFFBEB` | `#FDE68A` | Risk 40–59%, level-2 heat alert, rising canal levels |
| **High Risk** | `#EA580C` / `#9A3412` | `#FFEDD5` | `#FDBA74` | Risk 60–79%, extreme LST hotspots, elevated flood risk |
| **Critical / High Hazard** | `#DC2626` / `#991B1B` | `#FEF2F2` | `#FECACA` | Risk ≥ 80%, critical blockers, flash inundation, wet-bulb danger |
| **Hydrological / Water** | `#0284C7` / `#075985` | `#F0F9FF` | `#BAE6FD` | River water level, stormwater recharge, drainage overflow |

### 3.6 Text & Outline Borders
| Token Name | Hex Code | Description / Usage |
| :--- | :--- | :--- |
| `on-surface` | `#0B1C30` | Primary body and heading text (rich slate/navy black) |
| `on-surface-variant` | `#414944` | Secondary explanatory copy, subtitle text |
| `outline` | `#717974` | Icons, muted metadata, timestamp labels, table headers |
| `outline-variant` | `#C0C9C2` / `#E2E8F0` | Default perimeter divider and border line |
| `outline-focus` | `#144534` | Focus ring outline for interactive form fields |

---

## 4. Typography & Font System

The type system prioritizes unambiguous distinction across dense data sets, coordinates, and emergency telemetry.

### Font Families
- **Primary UI & Editorial:** `Inter` (`wght@400;500;600;700;800`) — used for headings, labels, button labels, and general body text.
- **Telemetry & Technical Mono:** `JetBrains Mono` (`wght@400;500;600;700`) — used for sensor readouts, ward codes (e.g., `AMC-E-04`), GPS coordinates, timestamps, percentages, and tabular numerals.
- **Iconography:** `Material Symbols Outlined` (`100..700, 0..1 FILL`) — unified 18–24px system icons.

### Typography Scale
| Token | Font Family | Size | Line Height | Weight | Tracking | Usage |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `display-lg` | Inter | 36px | 44px | 700 (Bold) | -0.025em | Primary KPI hero values (`14`, `42`, `-6.8°C`) |
| `headline-lg` | Inter | 30px | 38px | 600 (SemiBold) | -0.02em | Main page titles on desktop |
| `headline-lg-mobile` | Inter | 24px | 32px | 600 (SemiBold) | -0.015em | Main page titles on mobile viewports |
| `headline-md` | Inter | 22px | 28px | 600 (SemiBold) | -0.015em | Section titles, prominent card values |
| `headline-sm` | Inter | 18px | 24px | 600 (SemiBold) | -0.01em | Card headers, modal headings, sidebar title |
| `title-md` | Inter | 16px | 22px | 600 (SemiBold) | -0.005em | Top bar title, intervention card titles |
| `title-sm` | Inter | 14px | 20px | 600 (SemiBold) | 0.00em | Button labels, table column headers, tab labels |
| `body-lg` | Inter | 16px | 24px | 400 (Regular) | 0.00em | Intro paragraphs, descriptive lead text |
| `body-md` | Inter | 14px | 20px | 400 (Regular) | 0.00em | Default body copy, navigation inactive links |
| `body-sm` | Inter | 12px | 16px | 400 (Regular) | +0.01em | Secondary card details, helper notes |
| `label-md` | JetBrains Mono | 13px | 18px | 500 (Medium) | +0.02em | Secondary buttons, ward code pills |
| `label-sm` | JetBrains Mono | 11px | 14px | 500 (Medium) | +0.04em | Numeric table values, sensor telemetry tags |
| `label-xs` | JetBrains Mono | 10px | 12px | 600 (SemiBold) | +0.06em | Status pips, breadcrumbs, uppercase badge tags |

---

## 5. Spacing, Borders, Shadows & Corner Radii

### 5.1 Spacing Scale
- `space-xs`: `0.25rem` (4px) — micro-gaps between badge pips and text
- `space-sm`: `0.5rem` (8px) — gap between icon and text, compact cell padding
- `space-md`: `0.75rem` (12px) — inner card padding, input padding
- `space-lg`: `1.25rem` (20px) — header gaps, card group margins
- `space-xl`: `2.0rem` (32px) — major layout section margins
- `gutter`: `1.0rem` (16px) — tablet grid column gutters
- `gutter-mobile`: `0.75rem` (12px) — handheld column gutters
- `gutter-desktop`: `1.5rem` (24px) — command-center desktop gutters
- `margin-mobile`: `0.75rem` (12px) — mobile page outer margins
- `margin-desktop`: `2.0rem` (32px) — desktop page outer margins

### 5.2 Corner Radii
- `rounded-sm` / `0.25rem` (4px): Small tag pills, mini progress rails, inline code pills.
- `rounded-lg` / `DEFAULT` / `0.5rem` (8px): Primary buttons, form inputs, dropdowns, table row hover boundaries.
- `rounded-xl` / `0.75rem` (12px): Standard cards, telemetry modules, bento grid containers, filter toolbars.
- `rounded-2xl` / `1.0rem` (16px): Large audit cards, hero analytics modules, map container frames.
- `rounded-full` / `9999px`: Status badges, avatar images, live pulse pips, toggle switches.

### 5.3 Elevation & Shadows
- **Level 0 (Canvas Base):** `background: #F4F6F4`, no border, no shadow.
- **Level 1 (Stationary Panels & Standard Cards):**
  - Background: `#FFFFFF`
  - Border: `1px solid #E2E8F0`
  - Shadow: `0 1px 3px 0 rgba(20, 69, 52, 0.04), 0 1px 2px -1px rgba(20, 69, 52, 0.02)`
- **Level 2 (Active Cards, Hover Panels, Map Overlays):**
  - Background: `#FFFFFF`
  - Border: `1px solid #CBD5E1`
  - Shadow: `0 4px 6px -1px rgba(20, 69, 52, 0.07), 0 2px 4px -2px rgba(20, 69, 52, 0.05)`
- **Level 3 (Modals, Ward Switcher Popups, Critical Dispatch Dialogs):**
  - Background: `#FFFFFF`
  - Border: `1px solid #94A3B8`
  - Shadow: `0 10px 15px -3px rgba(15, 23, 42, 0.10), 0 4px 6px -4px rgba(15, 23, 42, 0.06)`

*Note:* Shadows incorporate subtle forest green tints (`rgba(20, 69, 52, ...)`) to naturally unify cards with the civic palette.

---

## 6. Navigation & Layout Patterns

### 6.1 Application Shell Architecture
```
+--------------------------------------------------------------------------------------------------+
| Top Bar (h-14, sticky z-40) [Brand | Jurisdiction Selector | Stream Freshness | Weather Pill | Profile] |
+------------------+-------------------------------------------------------------------------------+
| Sidebar (w-64)   | Scrollable Main Operations Canvas (flex-1 overflow-y-auto)                    |
| - Brand Crest    | +---------------------------------------------------------------------------+ |
| - Context Desk   | | Breadcrumbs & Title Section + Page Action Buttons (Export, Deploy, Audit)  | |
| - Issue Advisory | +---------------------------------------------------------------------------+ |
| - 6 Main Tabs    | | 5 Executive KPI Summary Cards (grid cols-1 sm:cols-2 lg:cols-5)           | |
| - Telemetry Box  | +---------------------------------------------------------------------------+ |
| - Support Links  | | Bento Grid / Tactical Split (e.g., 7:5 Map + Table or 8:4 Audit + Dossier)| |
+------------------+-------------------------------------------------------------------------------+
```

### 6.2 Sidebar Navigation Specification
- **Width:** `260px` (`w-64`), full height, sticky/fixed, border-right `1px solid #C0C9C2`.
- **Background:** `surface-container-lowest` (`#FFFFFF`).
- **Brand Block:** Shield icon in `primary-container` (`#144534`), "ClimateShield" title (`font-headline-sm text-primary`), and "AMC" secondary badge (`bg-secondary-container text-on-secondary-container`).
- **Desk Identifier:** "Command Operations Desk" (`label-xs text-outline uppercase tracking-wider`).
- **Tab Structure (6 Core Pages):**
  1. `Overview` (`dashboard`)
  2. `Ward Explorer` (`map`)
  3. `Intervention Planner` (`crisis_alert`)
  4. `Action Centre` (`local_police`)
  5. `Impact Verification` (`verified`)
  6. `Data & System Status` (`database`)
- **Active Tab Style:** `bg-surface-container text-primary font-title-sm border-l-4 border-primary shadow-sm`.
- **Inactive Tab Style:** `text-on-surface-variant font-body-md hover:bg-surface-container-low transition-colors`.
- **Emergency CTA:** Full-width "Issue Advisory" button with warning icon (`bg-error` or `bg-primary-container`).
- **Footer Diagnostics:** Live sensor telemetry box with animated pulsing green dot (`48/48 Wards reporting (100%)`).

### 6.3 Top Header App Bar
- **Height:** `56px` (`h-14`), sticky top, border-bottom `1px solid #C0C9C2`, background `#FFFFFF`.
- **Left Region:** Jurisdiction switcher button (`location_city` icon + dropdown caret: "Ahmedabad - All 48 Wards / 7 Zones") and live sensor freshness badge (`IMD & AMC Sensor Stream: Live (Synced 8m ago)`).
- **Center Region:** Live search bar with `search` icon and `⌘K` keyboard shortcut pill.
- **Right Region:**
  - Weather quick pill (`43.8°C Extreme Heat Alert | Sabarmati River: Normal`).
  - Action icons: Notifications (with red numeric badge), Refresh, Help.
  - Officer Profile: Avatar image (`w-8 h-8 rounded-full border border-outline-variant`), officer name (`K. Patel, IAS` / `M. Thennarasan, IAS`), designation (`Dy. Municipal Commissioner` / `Comm. Officer`), and expand caret.

---

## 7. Reusable Component Specifications

### 7.1 Buttons
- **Primary Action:**
  - Classes: `h-10 px-4 bg-primary-container text-white rounded-lg font-title-sm flex items-center gap-2 shadow-sm hover:bg-[#1B5742] active:scale-[0.98] transition-all`
  - Usage: Primary submits, "Deploy New Operation", "Issue Ward Advisory".
- **Secondary / Municipal Action:**
  - Classes: `h-10 px-3.5 bg-surface-container-lowest border border-outline-variant text-primary rounded-lg font-title-sm hover:bg-[#F8FAF8] shadow-sm transition-all`
  - Usage: "Export Ward Situation Report (PDF)", "Filter View".
- **Destructive / Emergency Dispatch:**
  - Classes: `h-10 px-4 bg-error text-white rounded-lg font-title-sm flex items-center gap-2 hover:bg-[#991B1B] active:scale-[0.98] shadow-sm transition-all`
  - Usage: Emergency sirens, urgent city-wide broadcasts.
- **Compact Ghost / Table Action:**
  - Classes: `px-2.5 py-1 bg-[#F0F5F1] hover:bg-[#E1EDE3] text-primary font-label-xs font-bold rounded border border-outline-variant transition-colors`
  - Usage: "Inspect", "Inspect Time-Series", "Open Dossier".

### 7.2 Status Badges & Chips
Composed of an 8px circular status indicator pip, `label-xs` monospace text, and a matched border/background:
- **Low Risk / Normal:** `bg-[#ECFDF5] border border-[#A7F3D0] text-[#065F46]` with pip `#059669`.
- **Moderate / Advisory:** `bg-[#FFFBEB] border border-[#FDE68A] text-[#92400E]` with pip `#D97706`.
- **High Risk:** `bg-[#FFEDD5] border border-[#FDBA74] text-[#9A3412]` with pip `#EA580C`.
- **Critical / High Hazard:** `bg-[#FEF2F2] border border-[#FECACA] text-[#991B1B]` with pip `#DC2626`.
- **Hydrological / River:** `bg-[#F0F9FF] border border-[#BAE6FD] text-[#075985]` with pip `#0284C7`.

### 7.3 KPI Metric Cards
Standardized 5-card responsive grid:
- **Card Container:** `bg-surface-container-lowest p-4 rounded-xl border border-outline-variant shadow-sm flex flex-col justify-between`.
- **Top Bar:** Label (`label-xs text-outline uppercase tracking-wider`) + functional icon (`18px`).
- **Value Row:** Display value (`font-display-lg font-bold leading-none`) + benchmark denominator (`body-md text-outline`).
- **Footer / Progress Rail:** Comparative subtitle (`body-sm`) + delta percentage badge (`label-xs px-1.5 py-0.5 rounded`) or mini colored progress rail (`h-1 bg-surface-container rounded-full overflow-hidden`).

### 7.4 Data Tables & Priority Ranking Grids
- **Header Structure:** `h-8 bg-[#F8FAF8] border-b border-outline-variant text-[10px] uppercase font-label-xs text-outline`.
- **Row Density:** 40px compact row height, `hover:bg-[#F8FAF8] transition-colors`.
- **Dividers:** `divide-y divide-outline-variant`.
- **Numeric Alignment:** Strictly right-aligned with monospace font features enabled.
- **Action Column:** Centered compact buttons (`Inspect`).

### 7.5 Form Inputs & Filter Controls
- **Height & Radius:** `h-9` or `h-10`, `rounded-lg`, `border border-outline-variant`.
- **Background:** `surface-container-lowest` (`#FFFFFF`) or `surface-bright` (`#F8F9FF`).
- **Typography:** `body-sm text-on-surface placeholder-outline`.
- **Focus State:** `border-primary ring-1 ring-primary focus:outline-none`.
- **Select Dropdowns:** Custom right arrow chevron (`arrow_drop_down`), neat internal padding.

### 7.6 Tactical Map & Telemetry Visualizations
- **GIS Canvas:** Tactical background grid pattern (`#DCE5DC` stroke on `#EFF4EA` fill) simulating digital operations desk.
- **Ward Polygons:** Interactive SVG polygons color-coded by composite hazard risk, pulsing SVG circles on critical wards (`Gomtipur`, `Danilimda`).
- **Floating Hover Inspection Card:** Fixed bottom-left card (`w-80 bg-white border border-outline rounded-lg p-3 shadow-lg z-30`) showing real-time ward population, heat vulnerability, water deficit, and active cooling centers.
- **24-Hour Diurnal Temperature Profile Chart:**
  - Dual-bar vertical sparkline chart comparing Uncoated Baseline (red-orange) vs. High-Albedo Coated (emerald).
  - Peak delta callout badge at 13:00 IST (`-11.1°C`).
  - Legend indicator and data provenance breakdown.

---

## 8. Desktop and Mobile Layout Rules

### 8.1 Grid Breakpoints
| Viewport | Range | Columns | Gutter | Margin | Layout Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Command Desktop** | `≥ 1280px` | 12 cols | 24px (`gutter-desktop`) | 32px (`margin-desktop`) | Persistent 260px sidebar, full split-screen bento grids, 5-col KPI strips |
| **Field Tablet** | `768px – 1279px`| 8 cols | 16px (`gutter`) | 16px (`margin`) | 2-col KPI grid, stacked bento views, collapsible sidebar |
| **Handheld Mobile** | `< 768px` | 4 cols | 12px (`gutter-mobile`) | 12px (`margin-mobile`) | Single-column stacked layout, drawer sidebar, horizontal scrolling tables |

### 8.2 Responsive Reflow Rules
1. **Sidebar Reflow:** On viewports `< 1024px`, the 260px persistent sidebar collapses into an off-canvas drawer triggered by a top hamburger button.
2. **Top App Bar Reflow:** On viewports `< 768px`, search and jurisdiction selector condense into modal search drawers; the weather pill collapses into an icon alert.
3. **5-KPI Strip Reflow:**
   - Desktop (`≥ 1024px`): 5 columns (`lg:grid-cols-5`).
   - Tablet (`640px – 1023px`): 2 columns (`sm:grid-cols-2`).
   - Mobile (`< 640px`): 1 column stacked (`grid-cols-1`).
4. **Bento Grid Reflow:**
   - Overview Screen: 7:5 map/table split stacks vertically on mobile/tablet.
   - Impact Verification Screen: 8:4 audit/spotlight split stacks vertically with the deep-dive dossier below the intervention cards.
5. **Touch Targets:** Buttons on mobile expand to a minimum touch target of `44px` with minimum `12px` padding.
6. **Data Tables:** Enclosed in `overflow-x-auto` wrappers to preserve row data readability on narrow screens without truncation.

---

## 9. Developer Guidelines & Implementation Checklist

When implementing frontend components conforming to this design system:
- [ ] **Do NOT introduce arbitrary Tailwind color names** (e.g., standard `blue-500` or `green-500`). Use the defined semantic tokens: `primary`, `secondary`, `tertiary`, `error`, `surface-container`, etc.
- [ ] **Enforce Font Segregation:** Use `Inter` for all editorial and structural titles. Use `JetBrains Mono` for all Ward IDs, sensor codes, temperatures, timestamps, and numeric metrics.
- [ ] **Ensure Tabular Number Alignment:** Apply `font-feature-settings: "tnum" 1, "zero" 1;` on all numeric data tables.
- [ ] **Maintain Hazard Alert Decoupling:** Never use `primary` green for low-hazard statuses. Use semantic hazard emerald (`#059669`), amber (`#D97706`), or crimson (`#DC2626`).
- [ ] **Include Subtle Tinted Shadows:** Level 1 and Level 2 shadows should use `rgba(20, 69, 52, 0.04)` to harmoniously integrate cards into the civic theme.
