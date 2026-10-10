# ClimateShield AMC — Heat & Water Decision Support System

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%200.100+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/Frontend-React%2019%20+%20Vite-61DAFB.svg?logo=react)](https://react.dev)
[![TailwindCSS](https://img.shields.io/badge/Styling-Tailwind%20CSS-38B2AC.svg?logo=tailwind-css)](https://tailwindcss.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python)](https://python.org)
[![Tests](https://img.shields.io/badge/Tests-272%20Passed%20(100%25)-success.svg)](https://pytest.org)

**ClimateShield AMC** is a municipal multi-hazard climate decision support and operational dispatch platform built for the **Ahmedabad Municipal Corporation (AMC)**. It combines physics-based thermal forecasts, hydraulic simulations, integer linear programming (ILP) optimization, and an empirical closed-loop learning engine to manage extreme heatwaves, urban waterlogging, and potable water deficits across all 48 municipal wards.

---

## Table of Contents

- [Key Capabilities](#key-capabilities)
- [System Architecture](#system-architecture)
- [Core Mathematical & Analytical Engines](#core-mathematical--analytical-engines)
- [Quick Start & Setup](#quick-start--setup)
- [Dashboard Navigation & User Guide](#dashboard-navigation--user-guide)
- [The Issue Advisory Workflow](#the-issue-advisory-workflow)
- [API Reference](#api-reference)
- [Testing & Quality Assurance](#testing--quality-assurance)
- [License & Acknowledgments](#license--acknowledgments)

---

## Key Capabilities

1. **Multi-Hazard Environmental Modeling:** Simultaneous evaluation of extreme heat (WBGT), monsoon waterlogging (surcharge depth), and summer potable water deficits.
2. **Deterministic ILP Knapsack Optimizer:** Optimizes resource allocation (budgets, deployment crews, mobile water tankers) subject to municipal constraints and equity priorities.
3. **Operational Action Centre:** Tracks real-time field deployments with strict human-in-the-loop approval workflows (`proposed` &rarr; `approved` &rarr; `in_progress` &rarr; `completed`).
4. **Empirical Impact Verification:** Validates field outcomes using Before-and-After and Difference-in-Differences (DiD) methodologies with causal guardrails.
5. **Closed-Loop Model Governance:** Continuously audits forecast accuracy against ground-truth surveillance data, generating transparent parameter update proposals with single-click rollbacks.

---

## System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Vite + React 19 Frontend (Port 5173)                 │
│  Overview • Ward Explorer • Planner • Action Centre • Impact • Learning │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │ Reverse Proxy (/api/*)
┌────────────────────────────────────▼───────────────────────────────────┐
│                     FastAPI Backend Engine (Port 8000)                 │
├─────────────────┬──────────────────┬─────────────────┬─────────────────┤
│   Heat Engine   │   Water Engine   │  Combined Risk  │  ILP Optimizer  │
│  (Open-Meteo &  │ (Waterlogging &  │ (Compound Risk  │ (PuLP / CBC     │
│   WBGT Physics) │  Deficit Models) │     Synergy)    │  Solver)        │
├─────────────────┴──────────────────┴─────────────────┴─────────────────┤
│            Action Centre Store & Operational State Machine             │
├────────────────────────────────────────────────────────────────────────┤
│           Impact Verification & Learning Loop Calibration Engine       │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
┌────────────────────────────────────▼───────────────────────────────────┐
│        SQLite Audit & Governance Store (climateshield_baseline.db)      │
│     14 Relational Tables: Predictions, Actions, Outcomes, Versions     │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Core Mathematical & Analytical Engines

### 1. Heat Engine (WBGT & Thermal Index)
- Computes **Wet Bulb Globe Temperature (WBGT)** using ambient dry-bulb temperature, relative humidity, and solar radiation from Open-Meteo.
- Combines physical heat exposure with ward-level demographic vulnerability (slum density, outdoor labor ratios, elderly population).

### 2. Water Engine (Dual Hazard Hydraulic Model)
- Evaluates storm waterlogging depth (cm) during monsoonal cloudbursts.
- Measures potable water supply stress (supply hours deficit, civic CCRS complaints).

### 3. Combined Risk Engine (Compound Synergy)
- Merges heat and water stress into a single normalized index (0–100).
- Applies a **Compound Synergy Multiplier** when a ward faces concurrent thermal and hydraulic extremes.

### 4. Intervention Optimizer (Integer Linear Programming)
- Solves a multi-constraint knapsack optimization problem using **PuLP / CBC**:
  $$\max \sum_{w, i} \text{RiskReduction}_{w,i} \cdot x_{w,i} + \lambda_{\text{equity}} \cdot \text{VulnerabilityWeight}_{w,i}$$
  *Subject to:* Total Budget (INR), Personnel Crew Cap, and Daily Water Tanker Volume (L).

### 5. Empirical Impact Verification & Learning Loop
- Computes empirical deltas and Difference-in-Differences against unintervened control wards.
- Enforces strict **Causal Guardrails** (correlational labels for simple before/after; prevents counterfactual fabrication).
- Human sign-off required for parameter updates; maintains immutable version history (`v1.0.0`, `v1.1.0`) with rollback.

---

## Quick Start & Setup

### Prerequisites
- **Python:** 3.11 or higher
- **Node.js:** v20+ LTS (Node.js 24 LTS recommended)
- **Package Managers:** `pip` and `npm`

### 1. Backend Setup & Startup (Terminal 1)

```powershell
# From project root (c:\Users\shram\wemakedevs)
# Install Python dependencies
python -m pip install -r requirements.txt

# Start the FastAPI Uvicorn Server
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
*Backend is now running at `http://127.0.0.1:8000` (Swagger UI at `/docs`).*

### 2. Frontend Setup & Startup (Terminal 2)

```powershell
# From project root, navigate to the frontend folder
cd frontend

# Install Node dependencies
npm install

# Start the Vite development server
npm run dev -- --host 127.0.0.1 --port 5173
```
*Frontend application is now live at `http://127.0.0.1:5173`.*

### 3. Integrated Production Mode (Optional)

```powershell
cd frontend
npm run build
```
Once built, the FastAPI backend will automatically serve the production dashboard directly at:  
`http://127.0.0.1:8000/dashboard/`

---

## Dashboard Navigation & User Guide

The dashboard is organized into seven operational modules accessible from the sidebar:

### 1. Overview (`OverviewPage.jsx`)
- **KPI Summary Cards:** Citywide critical risk wards, live ambient & WBGT thermal index, waterlogging exposure, and active municipal dispatches.
- **Ahmedabad Vector Map:** Interactive SVG map of all 48 wards colored by composite risk level (Green, Yellow, Orange, Red). Hover for quick stats; click to inspect.
- **Top At-Risk Wards Table:** Ranked list of the most vulnerable wards. Click **"Inspect"** on any row to open the full ward demographic breakdown.
- **Export Situation Brief:** Downloads a timestamped text situation report for municipal briefings.

### 2. Ward Explorer (`WardExplorerPage.jsx`)
- **Ward Search & Filter:** Search any of the 48 wards by name or filter by municipal zone (East, South, North, Central, West).
- **Vulnerability Breakdown:** View radar and bar profiles comparing heat index vs. pluvial flood surcharge.
- **Inspect Microclimate:** Opens detailed socio-demographic and sensor telemetry modals.

### 3. Intervention Planner (`InterventionPlannerPage.jsx`)
- **Resource Constraints Sliders:** Adjust Total Budget (INR 10,000–1,000,000), Personnel Crew, Water Cap (L), and the Equity Slider.
- **Integer Linear Programming Results:** Shows optimal intervention distribution (Cooling Shelters, Hydration Kiosks, Cool Roof Coating, Mobile Tankers, Drainage Clearing).
- **"Dispatch Plan to Ops Queue":** Automatically transfers all recommended interventions into the Action Centre.

### 4. Action Centre (`ActionCentrePage.jsx`)
- **Incident Response Queue:** Prioritized operational cards with human-in-the-loop lifecycle states.
- **Status Transitions:** Move actions through `Proposed` &rarr; `Approved` &rarr; `In Progress` &rarr; `Completed`.
- **Auto-Generate from Risk:** Generates heat alert interventions directly from current high-risk ward forecasts.

### 5. Impact Verification (`ImpactVerificationPage.jsx`)
- **Empirical M&E Dossier:** Compares baseline conditions with follow-up telemetry to verify real-world risk reduction.
- **Difference-in-Differences:** Identifies true intervention impact vs. synoptic weather changes.
- **Download Dossier:** Exports verification records as structured JSON files.

### 6. Learning & Governance (`LearningLoopDashboard.jsx`)
- **Dark Glassmorphic Command Center:** Inspect model predictions, field actions, and ground-truth outcomes.
- **Accuracy Audits:** Evaluates Mean Absolute Error (MAE) across hazard domains.
- **Human Parameter Sign-Off:** Review, approve, or reject proposed calibration changes and execute version rollbacks.

### 7. Data & System Status (`SystemStatusPage.jsx`)
- **Real-Time Health Monitoring:** Pings all 8 sub-services with live latency tracking in milliseconds.
- **Telemetry Indicators:** Verifies Open-Meteo, ERA5 reanalysis, and ECOSTRESS satellite status.

---

## The Issue Advisory Workflow

One of the platform's core emergency capabilities is the **Municipal Climate Advisory**:

1. **Trigger:** Click the red **"Issue Advisory"** button in the sidebar or top banner.
2. **Configure:** 
   - Choose the **HAP Alert Tier:** Green (<40°C), Yellow (40–43°C), Orange (43–45°C), or Red (≥45°C Extreme).
   - Select target municipal zones (e.g., East Zone, South Zone).
   - Toggle notification channels (Public SMS, Water Tankers, Hospital Pre-alert, PA Systems).
3. **Authorize:** Click **"Authorize Tier [X] Broadcast"**.
4. **Backend Processing:** Sends a `POST /api/action-centre/create` request. The backend creates an auditable `ActionRecord` with required crew and water tanker allocations.
5. **Where Results Appear:** The modal confirms dispatch with a green indicator and closes. The dispatched advisory is placed into the **Action Centre** queue under **"Prioritized Operational Actions"**, where incident commanders can approve, mobilize, or complete the dispatch.

---

## API Reference

The FastAPI server provides over 40 REST endpoints. Key endpoints include:

| Method | Endpoint | Description |
| :---: | :--- | :--- |
| `GET` | `/` | Root health status & endpoint directory |
| `GET` | `/api/weather/wbgt` | Live Open-Meteo WBGT and thermal hazard levels |
| `GET` | `/api/wards` | Socio-demographic census indicators for all 48 wards |
| `GET` | `/api/water/wards` | Waterlogging and supply deficit vulnerability metrics |
| `GET` | `/api/climate/combined-risk` | Multi-hazard compound risk scores and ward rankings |
| `POST` | `/api/optimize` | ILP knapsack resource allocation solver |
| `GET` | `/api/action-centre/dashboard` | Active operations metrics and prioritized actions |
| `POST` | `/api/action-centre/create` | Manually dispatch or record an operational action |
| `PUT` | `/api/action-centre/actions/{id}/status` | Transition action state (`approved`, `in_progress`, etc.) |
| `POST` | `/api/impact/verify` | Run empirical Before/After or DiD verification |
| `POST` | `/api/learning/predictions` | Record a historical risk prediction in audit trail |
| `POST` | `/api/learning/evaluate` | Run closed-loop model evaluation and generate proposals |
| `GET` | `/api/learning/active-parameters` | Fetch current active model calibration parameters |
| `GET` | `/api/learning/versions` | Retrieve immutable version audit log and rollback history |

---

## Testing & Quality Assurance

The codebase includes an automated test suite verifying all engines, schemas, and workflows:

```powershell
# Run the complete test suite (272 tests)
python -m pytest backend/ -v
```

**Test Verification Summary:**
- **Automated Tests:** **272 / 272 Passed (100% Pass Rate)**
- **Mathematical Engines:** Verified with live inputs (Heat WBGT, Waterlogging, ILP Knapsack).
- **Database Schema:** 14 relational tables verified in SQLite.
- **Frontend Production Build:** Compiles 1,934 modules with zero syntax errors via `npm run build`.

---

## License & Acknowledgments

- **Target City:** Ahmedabad Municipal Corporation (AMC), Gujarat, India.
- **Data Integrations:** Open-Meteo Weather Grid, ECMWF ERA5-Land Reanalysis, NASA ECOSTRESS LST.
- **Frameworks:** FastAPI, Pytest, PuLP, React 19, Vite, Tailwind CSS, Lucide Icons.
