# ClimateShield: 30-Hour Hackathon Execution Checklist & Architecture Plan
**Target City**: Ahmedabad, Gujarat, India (Coordinates: 23.0225° N, 72.5714° E)  
**Tech Stack**: FastAPI Backend | React + Tailwind CSS Frontend | Google OR-Tools / PuLP Optimization Engine  
**Team Structure**: 4 Developers  

---

## 👥 Team Roles & Responsibilities

| Role | Developer Focus | Key Deliverables |
| :--- | :--- | :--- |
| **Dev 1: Frontend & Maps Lead** | React, Tailwind CSS, Leaflet/Mapbox | Ward choropleth heat map, Equity slider UI controls, Intervention dashboard |
| **Dev 2: Backend Infrastructure** | FastAPI, CORS, Request Validation, Integration | REST endpoints, SQLite/In-memory cache, WebSocket/live updates |
| **Dev 3: Data & WBGT Pipeline** | Open-Meteo API, Microclimate Physics | Wet-Bulb Globe Temp (WBGT) engine, Ward vulnerability scoring for Ahmedabad |
| **Dev 4: Optimization Engine** | Google OR-Tools, ILP Knapsack Formulation | Multi-constraint solver (Budget, Crew, Water Cap, Equity Slider) |

---

## ⏱️ 30-Hour Task-by-Task Timeline Checklist

### Phase 1: Setup & Architecture Alignment (Hours 0 – 4)
- [x] **Dev 1**: Initialize React app with Tailwind CSS (`npx create-vite-app` or Vite React boilerplate). Set up global layout, theme colors (Dark mode/Glassmorphism for heat hazard visuals).
- [x] **Dev 2**: Set up FastAPI repository structure, CORS policy, virtual environment, and dependency configuration (`backend/main.py`).
- [x] **Dev 3**: Create `backend/wbgt_pipeline.py` with Open-Meteo API integration for Ahmedabad coordinates (`23.0225, 72.5714`).
- [x] **Dev 4**: Build `backend/optimizer.py` starter script with Google OR-Tools integer knapsack solver formulation.

---

### Phase 2: Core Data Engine & Optimization Logic (Hours 4 – 12)
- [ ] **Dev 3**:
  - Implement empirical Stull (2011) Natural Wet-Bulb & Outdoor Globe Temperature calculation.
  - Implement heat hazard classification tiers (`SAFE`, `MODERATE`, `HIGH`, `EXTREME`, `CRITICAL`).
  - Map Ahmedabad Wards (Danilimda, Behrampura, Asarwa, Bapunagar, Khadia, Amraiwadi, Vatva, Sabarmati, Maninagar, Naroda) to baseline vulnerability indices.
- [ ] **Dev 4**:
  - Implement multi-constraint ILP solver:
    - $\text{Maximize } \sum \text{Risk Reduction}_{w, k} \cdot x_{w, k}$
    - Constraint 1: Total Budget Cap ($\le B$)
    - Constraint 2: Deployment Crew Cap ($\le C$)
    - Constraint 3: Water Cap ($\le W$)
    - Constraint 4: Equity Slider ($\alpha \in [0.0, 1.0]$) enforcing minimum coverage for Slum Dwellers, Outdoor Laborers, and Elderly/Infants.
- [ ] **Dev 2**: Connect WBGT pipeline and Optimization engine to FastAPI API router (`GET /api/weather/wbgt`, `POST /api/optimize`).
- [ ] **Dev 1**: Build interactive Equity Slider control panel and Budget/Crew/Water input forms in React with Tailwind CSS.

---

### Phase 3: Interactive Visualizations & Mapping (Hours 12 – 20)
- [ ] **Dev 1**: Integrate Leaflet / React-Leaflet or Mapbox with GeoJSON for Ahmedabad Ward boundaries. Color wards dynamically based on WBGT risk level.
- [ ] **Dev 2**: Implement caching layer (FastAPI background tasks or in-memory dictionary) to store hourly Open-Meteo responses to avoid API rate limits.
- [ ] **Dev 3**: Create mock extreme heat wave scenario toggle (e.g., simulating 44°C ambient temp + high relative humidity) for live stress-testing.
- [ ] **Dev 4**: Add Resource Utilization gauges (Budget % used, Crew % assigned, Water % drawn) and Gini Equity balance score calculation.

---

### Phase 4: Integration, Closed-Loop Feedback & UI Polish (Hours 20 – 26)
- [ ] **Team Joint Task**: Connect React frontend to FastAPI backend endpoints.
- [ ] **Dev 1**: Render allocated intervention icons (Cooling Centers, Hydration Kiosks, Shade Canopies, Cool Roofs, Water Tankers) directly on ward map cards.
- [ ] **Dev 2**: Add export feature (`GET /api/export-plan`) allowing decision-makers to download PDF/CSV operational dispatch sheets.
- [ ] **Dev 3**: Add sensitivity analysis metrics showing how changing the Equity Slider impacts total risk reduction vs. vulnerable group protection.
- [ ] **Dev 4**: Verify optimization performance (<200ms solver latency) and validate fallback heuristic.

---

### Phase 5: Demo Prep, Pitch & Final Polish (Hours 26 – 30)
- [ ] **Dev 1 & 2**: UI final polish: Micro-animations, responsive layout adjustments, error boundary toasts.
- [ ] **Dev 3 & 4**: Prepare 3 key demo scenarios:
  1. *Baseline Heatwave*: 36°C WBGT with default budget.
  2. *Severe Resource Scarcity*: Low water cap scenario showing intelligent prioritization.
  3. *Equity Slider Shift*: Demonstrating how sliding equity from 0% to 100% shifts interventions toward informal settlements (Danilimda, Behrampura).
- [ ] **All**: Record 2-minute demo video and build pitch deck slides.
