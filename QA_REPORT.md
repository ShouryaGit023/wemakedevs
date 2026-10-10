# ClimateShield AMC (Heat & Water Decision Support System) - Comprehensive QA Test Report

**Date of Audit:** October 10, 2026  
**Auditor:** Senior Full-Stack QA Engineer  
**Repository:** `Sharmaakshat369/wemakedevs`  
**System Under Test:** Municipal Multi-Hazard Heatwave, Waterlogging & Water Scarcity Closed-Loop Decision Support Platform for Ahmedabad Municipal Corporation (AMC)

---

## 1. Project Entry Point & Exact Startup Commands

### Environment Prerequisites
- **Python:** 3.11.x (with `uv` or `pip`)
- **Node.js:** v24.20.0+ LTS
- **Package Managers:** `npm` v11.19.0+ / `pip`

### Step-by-Step Startup Commands

#### Step A: Backend Setup & Launch (Terminal 1)
```powershell
# From repository root (c:\Users\shram\wemakedevs)
# 1. Install backend dependencies
python -m pip install -r requirements.txt

# 2. Launch FastAPI Uvicorn Server
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

#### Step B: Frontend Setup & Launch (Terminal 2)
```powershell
# Navigate to frontend directory
cd frontend

# 1. Install frontend dependencies
npm install

# 2. Launch Vite Development Server
npm run dev -- --host 127.0.0.1 --port 5173
```

#### Step C: Production Bundle Build (Optional / Integrated Mode)
```powershell
cd frontend
npm run build
# When built, FastAPI mounts and serves the static production bundle at http://127.0.0.1:8000/dashboard/
```

---

## 2. Environment Variables & Configuration

The application is architected to operate out-of-the-box with calibrated local baselines and open-access meteorological sources, with optional satellite/cloud credentials:

| Variable | Target Service | Default / Fallback | Purpose / Sensitivity |
| :--- | :--- | :--- | :--- |
| `VITE_API_URL` | Frontend (`services/api.js`) | `http://127.0.0.1:8000` | Backend API base URL for client fetch calls |
| `CDSAPI_URL` | Backend (`data_sources.py`) | Public Open-Meteo Fallback | ECMWF Copernicus Climate Data Store API URL |
| `CDSAPI_KEY` | Backend (`data_sources.py`) | Modeled / Cached Fallback | CDS API authentication token |
| `EARTHDATA_TOKEN` | Backend (`data_sources.py`) | Synthetic / Cache Fallback | NASA Earthdata token for NASA ECOSTRESS LST & ET |

*Note: In the absence of NASA/Copernicus API tokens, the Data Fusion Engine safely falls back to cached satellite passes and live Open-Meteo telemetry without crashing.*

---

## 3. URLs, Ports & Service Status

| Service Component | Host / Port | Status | Protocol | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **FastAPI Backend Core** | `http://127.0.0.1:8000` | **HEALTHY / OPERATIONAL** | HTTP/1.1 REST | 40+ endpoints active |
| **Vite Frontend Dev Server** | `http://127.0.0.1:5173` | **HEALTHY / OPERATIONAL** | HTTP/1.1 HMR | Reverse proxy `/api` -> `8000` |
| **Production Dashboard Mount** | `http://127.0.0.1:8000/dashboard/` | **HEALTHY / OPERATIONAL** | Static HTML/JS | Built bundle served directly from FastAPI |
| **SQLite Audit Database** | `backend/data/climateshield_baseline.db` | **HEALTHY / ACTIVE** | SQLite3 | 14 relational tables initialized |

---

## 4. Overall Testing Summary

| Test Domain | Executed | Passed | Failed | Blocked | Pass Rate |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Backend Unit & Regression (Pytest)** | 272 | 272 | 0 | 0 | **100.0%** |
| **Backend Integration & REST Endpoints** | 42 | 42 | 0 | 0 | **100.0%** |
| **Mathematical Engines (Heat, Water, ILP)** | 14 | 14 | 0 | 0 | **100.0%** |
| **Closed-Loop Calibration & Learning Engine** | 10 | 10 | 0 | 0 | **100.0%** |
| **Frontend Production Build (Vite)** | 1 | 1 | 0 | 0 | **100.0%** |
| **Frontend Network Proxy & API Integration** | 3 | 3 | 0 | 0 | **100.0%** |
| **End-to-End Multi-Step Lifecycle** | 11 | 11 | 0 | 0 | **100.0%** |
| **Headless Browser Automation (Playwright)** | 8 | 0 | 0 | 8 | *Blocked (CDN 404)* |
| **TOTAL VERIFIED CHECKS** | **361** | **353** | **0** | **8** | **97.8% (100% of unblocked)** |

---

## 5. Bugs Found, Root Cause Analysis & Resolutions

During initial testing, multiple critical merge conflict markers and structural regressions were discovered resulting from an uncoordinated Git merge pushed to `origin/main` (PR #7 / commit `7fd2612`). All issues were systematically resolved and verified.

### Bug 1: Git Conflict Markers in Backend Database Schema
- **Severity:** Critical (P0 - Service Inoperable)
- **File:** `backend/database.py` (lines 93 & 286)
- **Root Cause:** Merge conflict between Sanidhya's Learning Loop tables (`predictions`, `recommendations`, `executed_actions`, `verified_outcomes`, `impact_verifications`, `model_evaluations`, `proposed_parameter_updates`, `model_versions`) and Samir's Impact Assessment tables (`impact_assessments`, `impact_assessment_history`).
- **Fix Applied:** Reconciled `init_db()` to create all 14 database tables and relational indices, ensuring backwards compatibility for both engines.
- **Verification:** SQLite database initialized cleanly without syntax errors; all 14 tables verified.

### Bug 2: Syntax Error & Unclosed Imports in FastAPI Server
- **Severity:** Critical (P0 - Service Inoperable)
- **File:** `backend/main.py` (lines 52, 187, 1134, 1519, 2092)
- **Root Cause:** Stray `<<<<<<< HEAD`, `=======`, and `>>>>>>>` markers left in imports, root router documentation list, Learning Loop router, and at the end of the file. In addition, an unclosed parenthesis in `from backend.data_sources import (` was causing Python syntax compilation failure.
- **Fix Applied:** Cleaned all conflict markers, closed import statements, merged routes list in `read_root()`, and registered all endpoints from both features.
- **Verification:** `python -m uvicorn backend.main:app` boots cleanly with zero syntax errors.

### Bug 3: Duplicate Docstrings and Stray Markers in Impact Verification Engine
- **Severity:** High (P1 - Test Failures)
- **Files:** `backend/impact_verification.py` and `backend/test_impact_verification.py`
- **Root Cause:** Merge markers `<<<<<<< HEAD`, `=======`, and `>>>>>>>` were embedded inside module docstrings, breaking Python parsing.
- **Fix Applied:** Removed stray tokens and converted comments to properly formatted docstrings.
- **Verification:** 100% of unit and integration tests in `test_impact_verification.py` pass.

### Bug 4: Merge Conflicts in Frontend Core (`package.json`, `index.html`, `vite.config.js`, `index.css`, `App.jsx`)
- **Severity:** Critical (P0 - Frontend Failed to Build)
- **Files:** `frontend/package.json`, `frontend/vite.config.js`, `frontend/index.html`, `frontend/src/index.css`, `frontend/src/App.jsx`
- **Root Cause:** Conflict markers committed directly into package manifest, Vite config, HTML entry point, and CSS tokens. In `App.jsx`, the municipal command desk pages (`OverviewPage`, `ActionCentrePage`, `ImpactVerificationPage`, `WardExplorerPage`, `InterventionPlannerPage`, `SystemStatusPage`) were disconnected.
- **Fix Applied:**
  1. Resolved `package.json` to include `tailwindcss`, `postcss`, `autoprefixer`, and `oxlint`.
  2. Preserved Vite server reverse-proxy configuration (`/api` -> `http://127.0.0.1:8000`).
  3. Integrated all Google Fonts (`Inter`, `Outfit`, `JetBrains Mono`) and `Material Symbols Outlined` in `index.html`.
  4. Merged Tailwind directives with glassmorphic Learning Loop design tokens in `index.css`.
  5. Built a unified `App.jsx` with full tab navigation including the newly integrated **Learning & Governance** tab alongside the six municipal operations pages.
- **Verification:** `npm run build` compiled 1,934 modules with zero errors in 3.43s.

### Bug 5: Backend 404 on `/dashboard/` Route During Development
- **Severity:** Medium (P2)
- **File:** `backend/main.py` (lines 140-146)
- **Root Cause:** When `frontend/dist` did not exist, `app.mount("/dashboard", ...)` was skipped entirely, causing `GET /dashboard/` to return HTTP 404 and failing E2E review tests.
- **Fix Applied:** Added a graceful fallback HTML route on `/dashboard` and `/dashboard/` when the production bundle is not yet compiled, directing users to the active Vite dev server. Once built, the static production bundle is served.
- **Verification:** `test_10_existing_heat_water_risk_and_optimizer_endpoints_still_work` passed.

### Bug 6: Playwright Browser Automation Driver CDN 404
- **Severity:** High (External Tooling Blocker)
- **Root Cause:** Playwright Azure Edge CDN (`https://playwright.azureedge.net/builds/driver/playwright-1.57.0-win32_x64.zip`) returned HTTP 404 Not Found during headless driver provisioning.
- **Resolution:** As per system protocol, the environment blocker is documented; full frontend-to-backend integration was validated via automated HTTP integration harnesses, Vite proxy validation, and production build checks.

---

## 6. API Endpoints Tested & Verification Matrix

All endpoints tested against live running instance at `http://127.0.0.1:8000`:

| Endpoint | Method | Expected Input | Status | Response Validation |
| :--- | :---: | :--- | :---: | :--- |
| `/` | `GET` | None | **200 OK** | System status, target city, complete endpoint inventory |
| `/api/weather/wbgt` | `GET` | `lat=23.0225, lon=72.5714` | **200 OK** | Live Open-Meteo WBGT, 24h hourly forecast, ward thermal risk |
| `/api/wards` | `GET` | None | **200 OK** | All 48 Ahmedabad wards with socio-demographic indicators |
| `/api/wards/geojson` | `GET` | None | **200 OK** | GeoJSON boundaries for Ahmedabad administrative wards |
| `/api/risk/monte-carlo` | `GET` | None | **200 OK** | Multi-iteration heat risk distributions across priority wards |
| `/api/water/wards` | `GET` | None | **200 OK** | Complete waterlogging & water scarcity indices for 48 wards |
| `/api/water/scenarios` | `GET` | None | **200 OK** | Monsoonal deluge, summer drought, and chronic deficit scenarios |
| `/api/climate/combined-risk` | `GET` | `weight_heat=0.5, weight_water=0.5` | **200 OK** | Multi-hazard compound score with synergy bonus & ranking |
| `/api/optimize` | `POST` | Budget, Crew, Water cap, Equity | **200 OK** | PuLP / CBC optimal knapsack allocation & equity ratio |
| `/api/interventions/catalog` | `GET` | None | **200 OK** | Catalog of 10 cooling, hydration, drainage, and tanker assets |
| `/api/action-centre/dashboard` | `GET` | None | **200 OK** | Operational metrics, prioritized actions, ward-wise summary |
| `/api/action-centre/actions` | `GET` | None | **200 OK** | Action queue with lifecycle statuses (PROPOSED, SCHEDULED, etc.) |
| `/api/impact/summary` | `GET` | None | **200 OK** | Empirical outcome assessment aggregations by ward & type |
| `/api/impact/verify` | `POST` | `action_id` | **200 OK** | Before-after delta, Difference-in-Differences, causal check |
| `/api/learning/predictions` | `POST` | Ward, hazard, predicted score | **201 Created** | Appends prediction record with cryptographic UUID |
| `/api/learning/actions` | `POST` | Prediction ID, intervention type | **201 Created** | Creates auditable field intervention action |
| `/api/learning/actions/{id}` | `PATCH` | Execution status & actual resources | **200 OK** | Transitions status to `COMPLETED` |
| `/api/learning/outcomes` | `POST` | Ward, admissions, 108 calls | **201 Created** | Ingests verified ground-truth outcome |
| `/api/learning/evaluate` | `POST` | Evaluation window (days) | **200 OK** | Calibrates model MAE and generates parameter proposals |
| `/api/learning/active-parameters`| `GET` | None | **200 OK** | Returns active immutable model version parameters |
| `/api/learning/versions` | `GET` | None | **200 OK** | Audit trail of historical versions (`v1.0.0`, etc.) |

### Validation & Error Handling Tests
- **Invalid Optimizer Budget (`-100 INR`):** Returned **422 Unprocessable Entity** with validation message `Input should be greater than or equal to 10000`.
- **Non-Existent Prediction (`GET /api/learning/predictions/nonexistent_123`):** Returned **404 Not Found** with message `Prediction 'nonexistent_123' not found.`
- **Missing Required Body Fields:** Returned **422 Unprocessable Entity** with explicit field error paths.
- **Verification on Non-Existent Action:** Returned **404 Not Found** with message `Action ID 'missing_action' not found.`

---

## 7. Engine Verification Analysis

### 1. Heat Engine (WBGT & Thermal Exposure)
- **Physics Calculation:** Calculates Wet Bulb Globe Temperature (WBGT) using ambient dry-bulb temperature, relative humidity, and direct solar irradiance from Open-Meteo.
- **Ward-Level Scaling:** Cross-references WBGT against ward-specific slum density, outdoor labor ratio, and elderly population to generate heat vulnerability indices.
- **Verification:** Verified live calculations: 35.7°C ambient temperature with 746.9 W/m² solar irradiance yielded 28.7°C WBGT ("MODERATE" hazard level).

### 2. Water Engine (Waterlogging & Potable Deficit)
- **Simulation Capabilities:** Models dual hydraulic hazards: chronic storm waterlogging depth (cm) during monsoonal cloudbursts, and civic drinking water supply deficits (hours of supply, CCRS complaints).
- **Spatial Coverage:** Comprehensive data models across all 48 Ahmedabad municipal wards.
- **Verification:** Verified all 48 wards successfully return calibrated hydraulic vulnerability metrics.

### 3. Intervention Engine & ILP Knapsack Optimizer
- **Formulation:** Solves a multi-constraint 0-1 / Integer Linear Programming problem balancing:
  $$\max \sum_{w, i} \text{RiskReduction}_{w,i} \cdot x_{w,i} + \lambda_{\text{equity}} \cdot \text{VulnerableCoverage}_{w,i}$$
  subject to Budget (INR), Deployment Crew Count, and Tanker Water Capacity (L).
- **Verification:** Tested with INR 400,000 budget, 35 crew, and 25,000 L water cap. The solver achieved optimal solution allocating INR 211,000 with 34 crew members and 10,800 L water, achieving a 578.09 composite risk reduction.

### 4. Impact Verification & Causal Guardrails
- **Attribution Guardrail:** Strictly tags simple before-and-after evaluations as `CORRELATIONAL_ONLY (NON-CAUSAL)`.
- **Difference-in-Differences (DiD):** Requires concurrent control ward observations; if control data is absent, safely reports `INSUFFICIENT_DATA_NO_CONTROL` rather than fabricating counterfactuals.
- **Action Completion Tracking:** Fails evaluation with `ACTION_NOT_COMPLETED` if the intervention was canceled or incomplete.

### 5. Learning Loop & Model Governance
- **Zero Silent Retraining:** Machine learning and statistical parameter adjustments cannot auto-apply. They generate structured proposals requiring explicit human approval.
- **Immutable Version History:** Approved parameter updates increment immutable version records (`v1.0.0`, `v1.1.0`) with audit trails and single-click rollback capability.

---

## 8. Frontend Architecture & Page Verification

The frontend application (`frontend/src`) features seven interconnected modules:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        TopAppBar (Global Telemetry)                   │
├───────────────┬────────────────────────────────────────────────────────┤
│    Sidebar    │                   Main Content Canvas                  │
│               ├────────────────────────────────────────────────────────┤
│ • Overview    │ [OverviewPage]                                         │
│ • Ward Explor │   - KPI Summary Cards                                  │
│ • Planner     │   - Ahmedabad Vector Map (Interactive Ward Polygons)   │
│ • Action Ctr  │   - Top Risk Wards Table with Quick Inspect            │
│ • Impact Ver  ├────────────────────────────────────────────────────────┤
│ • Learning Lp │ [InterventionPlannerPage]                              │
│ • Data Status │   - Sliders for Budget, Crew, Water, Equity            │
│               │   - Real-time ILP Solver Response Visualizations       │
│               ├────────────────────────────────────────────────────────┤
│               │ [ActionCentrePage]                                     │
│               │   - Prioritized Action Cards & Deployment Workflow     │
│               ├────────────────────────────────────────────────────────┤
│               │ [ImpactVerificationPage]                               │
│               │   - Before/After & DiD Visualizations                  │
│               ├────────────────────────────────────────────────────────┤
│               │ [LearningLoopDashboard]                                │
│               │   - Dark Glassmorphic Calibration Console              │
│               │   - Parameter Proposal Approval & Version Rollback     │
└───────────────┴────────────────────────────────────────────────────────┘
```

- **Interactive Modals:**
  - `WardInspectionModal.jsx`: Ward vulnerability breakdown, demographic split, and microclimate profile.
  - `IssueAdvisoryModal.jsx`: Emergency municipal heat/water advisory broadcast form.
  - `ImpactVerificationModal.jsx`: Manual or automated outcome assessment verification dialog.

---

## 9. Incomplete Integrations, Mock Data & Production Considerations

1. **Copernicus CDS & NASA Earthdata API Authentication:**
   - In `backend/data_sources.py`, external satellite pipelines use fallback simulation and local caching when `CDSAPI_KEY` or `EARTHDATA_TOKEN` are unconfigured. For production deployment, valid API credentials should be placed in environment variables.
2. **GeoJSON Geometry Fallback:**
   - In `frontend/src/data/mockData.js`, simplified ward boundary polygons are provided for the SVG vector map if `backend/data/Ahmedabad_Wards.geojson` is inaccessible. The system functions smoothly with both real and fallback geometries.
3. **Hospital Surveillance API:**
   - Outcome records (`outcome_records` table) currently simulate data ingestion from the AMC Health Surveillance portal. In production, this can be connected directly to the AMC HMIS (Health Management Information System) webhook.

---

## 10. Prioritized Next Steps

| Priority | Item | Recommended Action |
| :---: | :--- | :--- |
| **High** | **Automated Playwright Driver Provisioning** | Cache the Playwright driver binary locally in CI/CD pipeline to avoid reliance on external Azure edge download links during automated test runs. |
| **Medium** | **NASA Earthdata Credentials Setup** | Configure `EARTHDATA_TOKEN` in production `.env` to enable live daily ECOSTRESS 70m thermal infrared satellite ingestion. |
| **Medium** | **Persistent SQLite Backup** | Configure an automated backup cron for `climateshield_baseline.db` to prevent accidental loss of model parameter audit versions. |
| **Low** | **Pydantic V2 Field Warnings** | Update legacy `example="..."` kwargs in `backend/schemas.py` to `json_schema_extra={"example": "..."}` to eliminate Pydantic deprecation warnings. |

---

## 11. Developer Reproduction & Verification Guide

To verify that the complete system functions identically on any machine:

```powershell
# 1. Run all 272 automated backend tests
python -m pytest backend/ -v

# 2. Build the production React frontend bundle
cd frontend
npm run build
cd ..

# 3. Launch the complete system
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
# In second terminal:
cd frontend; npm run dev -- --host 127.0.0.1 --port 5173

# 4. Open browser to http://127.0.0.1:5173
```
