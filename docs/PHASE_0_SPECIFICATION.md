# ClimateShield — Phase 0: Foundations & Setup (Weeks 0–4)
**Project**: ClimateShield Heat Decision Support System  
**Pilot Partner**: Ahmedabad Municipal Corporation (AMC)  
**Location**: Ahmedabad, Gujarat, India (Coordinates: `23.0225° N, 72.5714° E`)  
**Status**: COMPLETED & FORMALIZED  

---

## 🏛️ Task 1: Lock in Pilot City & Named Municipal Counterparts

### 1. Selected Pilot City
- **City**: Ahmedabad, Gujarat, India
- **Rationale**: Ahmedabad pioneered South Asia’s first municipal Heat Action Plan (HAP) in 2013 after the catastrophic May 2010 heatwave (which caused >1,300 excess deaths). It has an established administrative appetite for heat interventions, existing ward boundaries, and weather vulnerability profiles.

### 2. Named Municipal Counterparts & Governance Cell
| Stakeholder Entity | Key Counterpart Role | Designated Nodal Unit | Primary Responsibilities |
| :--- | :--- | :--- | :--- |
| **Ahmedabad Municipal Corporation (AMC)** | Chief Municipal Health Officer & Nodal Officer | Health Department, AMC Headquarters, Danapith | Overall operational authorization, inter-departmental coordination, heat alert broadcast. |
| **AMC Disaster Management Cell** | Disaster Management Specialist | Central Emergency Control Room, Paldi | Resource dispatch authorization, emergency water tanker coordination, shelter mobilization. |
| **GVK EMRI 108 Emergency Services** | Head of State Operations | 108 Emergency Response Center, Naroda | 108 heat illness ambulance dispatches, heat exhaustion case logs. |
| **Sardar Vallabhbhai Patel (SVP) / Civil Hospital** | Medical Superintendents | Emergency & Casualty Departments | Daily heat stroke admissions, severe dehydration clinical surveillance. |

---

## 📋 Task 2: City Decision-Making Workflows, SOPs & Timing

### 1. Ahmedabad Heat Action Plan (HAP) Alert Tiers & Operational SOPs
Ahmedabad operates under standardized color-coded heat thresholds, which ClimateShield binds to Wet-Bulb Globe Temperature (WBGT) and dry-bulb forecasts:

| Alert Tier | Dry Bulb (°C) | WBGT (°C) | Alert Level | Municipal SOP Mandatory Actions |
| :--- | :--- | :--- | :--- | :--- |
| **Green** | $<40.0^\circ\text{C}$ | $<26.0^\circ\text{C}$ | Normal | Routine public health advisories; baseline water tanker readiness. |
| **Yellow** | $40.0 - 42.9^\circ\text{C}$ | $26.0 - 28.9^\circ\text{C}$ | Moderate | Advisory to outdoor laborers; targeted SMS warnings to construction sites; verify drinking water booths (Chhabils/Parabs). |
| **Orange** | $43.0 - 44.9^\circ\text{C}$ | $29.0 - 30.9^\circ\text{C}$ | High | Mandate 12:00–16:00 rest pauses for construction/outdoor laborers; open municipal gardens/transit hubs as cooling spaces; expand ORS distribution at Urban Health Centres (UHCs). |
| **Red** | $\ge 45.0^\circ\text{C}$ | $\ge 31.0^\circ\text{C}$ | Extreme / Critical | **Emergency Action Triggered**: Mobilize mobile water tankers to informal settlements (slums); deploy pop-up shade canopies at high-density bus stands (AMTS/BRTS); activate cool roof programs; hospital triage wards reserved for heatstroke. |

### 2. Operational Decision-Making Timeline (Lead Time Architecture)
```
T - 48 Hours: Open-Meteo High-Resolution Ingestion
  ├── Run WBGT physical modeling across 10 Ahmedabad pilot wards.
  └── Flag ward-level microclimate hotspots.

T - 24 Hours: Automated Optimization Dispatch Generation
  ├── Municipal operators set resource bounds (Budget INR, Crew, Water Cap, Equity Slider).
  ├── ILP solver allocates interventions per ward under <200ms latency.
  └── Decision dashboard presents optimal allocation to AMC Health Nodal Officer.

T - 12 Hours: Municipal Sign-off & Inter-Departmental Routing
  ├── AMC Control Room confirms tanker dispatches to Engineering/Water department.
  └── UHC medical officers receive hydration & cooling kits.

T - 0 to T + 6 Hours: Ground Execution & Verification
  ├── Real-time deployment of interventions during peak solar irradiance (12:00 – 16:00).
  └── Feedback loop ingests emergency 108 calls & hospital admissions.
```

---

## 🔒 Task 3: Data-Sharing Agreements & Outcome Ingestion Schemas

To comply with public health privacy and municipal data security standards, ClimateShield establishes structured data schemas with daily aggregation:

### 1. Ingested Data Streams
1. **Hospital Morbidity Records**:
   - `ward_id`: Spatial reference
   - `admissions_heat_exhaustion`: Count of outpatient/inpatient admissions
   - `admissions_heat_stroke`: Severe ICU/emergency room admissions
2. **All-Cause & Heat-Attributable Mortality**:
   - `daily_mortality_count`: Recorded by AMC Registrar of Births and Deaths
   - `excess_mortality_estimate`: Difference against the 5-year seasonal baseline
3. **Emergency Dispatch (108 EMRI)**:
   - `heat_emergency_calls`: Daily emergency dispatch trips for unconsciousness/fainting
4. **Water Scarcity & Civic Complaints**:
   - `water_tanker_requests`: Civic helpline (CCRS 155303) requests from informal settlements

---

## 📊 Task 4: Agreed Success Metrics & Baseline Database

### 1. Quantitative Success Metrics (KPIs)
| KPI Category | Target Metric | Target Benchmark |
| :--- | :--- | :--- |
| **Health Impact** | Reduction in heat-related morbidity & hospital visits in covered wards | $\ge 25\%$ reduction during Orange/Red alerts |
| **Equity Guarantee** | Resource allocation to top 3 vulnerable wards (Danilimda, Behrampura, Vatva) | $\ge 60\%$ of total budget allocated when Equity Slider $\ge 0.5$ |
| **Resource Efficiency** | Budget, crew, and water utilization efficiency | $> 90\%$ effective utilization without exceeding caps |
| **Algorithmic Latency** | Decision support solver run-time | $< 200\text{ ms}$ for real-time interactive adjustments |

### 2. Baseline Database Structure (SQLite / PostGIS-compatible)
A persistent baseline SQLite database (`backend/data/climateshield_baseline.db`) stores:
- **`wards`**: 10 pilot wards with demographics, slum density, outdoor labor ratio, elderly ratio, and baseline risk.
- **`interventions`**: Standardized catalog of heat mitigation measures with costs, crew, and water specs.
- **`outcome_records`**: Daily ground-truth records for morbidity, mortality, and civic requests.
- **`optimization_runs`**: Historical record of every optimization decision run for auditability and compliance.
