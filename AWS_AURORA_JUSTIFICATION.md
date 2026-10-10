# 🐬 Amazon Aurora Datasets in ClimateShield: Architecture & Justification

> **Project**: ClimateShield — Decision Support System for Climate & Thermal Extremes  
> **Deployment Target**: Ahmedabad Municipal Corporation (AMC), Gujarat, India  
> **AWS Service**: Amazon Aurora (PostgreSQL-Compatible & Aurora Serverless v2)  

---

## 📌 Executive Summary

ClimateShield processes municipal-scale geospatial layers, microclimate telemetry, empirical epidemiology records, and optimization run audits. While local development uses embedded SQLite, municipal disaster management requires a **high-throughput, auto-scaling, fault-tolerant relational cloud database**.

**Amazon Aurora** serves as the system of record for ClimateShield's core datasets:
1. **Ward Baseline Geographies & Demographics** (slum densities, outdoor labor ratios, vulnerable demographics across 48 AMC wards).
2. **Municipal Ground-Truth Outcome Records** (GVK EMRI 108 emergency calls, hospital heat admissions, heat mortality registers).
3. **Intervention Catalogs & Parametric Constraints** (hydration kiosks, cool roofs, water tankers, shade canopies, unit costs, crew requirements).
4. **Optimization Audit Logs** (historical mathematical solver runs, budget allocations, equity trade-offs).
5. **Empirical Impact Verifications** (pre/post intervention microclimate measurements and difference-in-differences evaluations).

```
┌───────────────────────────────────────────────────────────┐
│                 CLIMATESHIELD INGESTION                   │
│   (Open-Meteo, ERA5-Land Reanalysis, ECOSTRESS LST)       │
└─────────────────────────────┬─────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────┐
│              AMAZON AURORA CLOUD REPOSITORY               │
│               (PostgreSQL / Serverless v2)                │
│                                                           │
│  ┌───────────────────────┐     ┌───────────────────────┐  │
│  │     wards table       │     │  interventions table  │  │
│  │ (Demographics & Area) │     │ (Costs, Crew, Water)  │  │
│  └───────────────────────┘     └───────────────────────┘  │
│  ┌───────────────────────┐     ┌───────────────────────┐  │
│  │ outcome_records table │     │ optimization_runs     │  │
│  │ (108 calls, Hospital) │     │ (Solver Audit Log)    │  │
│  └───────────────────────┘     └───────────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │          impact_assessments (JSONB Payloads)        │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────┬─────────────────────────────┘
                              │
        ┌─────────────────────┴─────────────────────┐
        ▼                                           ▼
┌──────────────────────────────┐    ┌──────────────────────────────┐
│     OR-Tools Optimization    │    │      Amazon Bedrock LLM      │
│     Engine (ILP Solver)      │    │  (Action Plans & Advisories) │
└──────────────────────────────┘    └──────────────────────────────┘
```

---

## 🎯 Why Amazon Aurora? Key Architectural Justifications

### 1. High-Concurrency Read Scalability for Emergency Crisis Dashboards
During acute heatwave declarations, dozens of civic officials (municipal commissioners, zone health officers, water distribution superintendents) access the dashboard simultaneously.
* Aurora provides up to **15 read replicas** with sub-10ms replica lag across multiple Availability Zones.
* Separates write-heavy sensor ingestion from read-intensive choropleth map queries.

### 2. Native Semi-Structured Geospatial & JSONB Telemetry
* ClimateShield stores rich sensor payloads, confidence intervals, and spatial coordinates.
* Aurora PostgreSQL natively supports **`JSONB`** for nested impact assessment indicators and **`PostGIS`** extensions for ward boundary spatial queries without relational schema bloat.

### 3. Serverless v2 Elasticity & Cost Efficiency
* Extreme heat events in Ahmedabad are highly seasonal (concentrated in March–June peak pre-monsoon heatwave spikes).
* **Aurora Serverless v2** automatically scales database compute up to hundreds of ACUs (Aurora Capacity Units) in fractions of a second during emergency heat alerts, and scales down to minimal capacity during normal weather conditions, preventing idle municipal cloud costs.

### 4. Zero Data Loss & Continuous Point-in-Time Recovery (PITR)
* Civil epidemiology records and optimization allocation audits must satisfy government legal compliance.
* Aurora replicates 6 copies of data across 3 Availability Zones with continuous backups to Amazon S3, allowing point-in-time restoration to any second within the retention period.

### 5. Resilient Dual-Mode Adapter (Zero Hackathon Demo Risk)
* Implemented in `backend/aurora_service.py`:
  * **Production Mode**: Direct PostgreSQL connection via `psycopg2` or AWS Aurora Serverless RDS Data API (`boto3 rds-data`).
  * **Fallback / Offline Mode**: High-concurrency local SQLite mirror with automatic schema validation and synchronization utilities (`/api/aurora/sync`), guaranteeing the demo always runs regardless of AWS credential state.

---

## 🛠️ API Interface

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/aurora/status` | `GET` | Reports Aurora connectivity, active adapter mode, cluster endpoint, and registered datasets. |
| `/api/aurora/schema` | `GET` | Returns PostgreSQL DDL table definitions, foreign keys, and indexes optimized for Aurora. |
| `/api/aurora/dataset` | `GET` | Exports complete baseline dataset payload (wards, interventions, outcomes) for cloud ingestion. |
| `/api/aurora/sync` | `POST` | Executes / simulates dataset synchronization between local state and Amazon Aurora. |

---

## 📋 Aurora PostgreSQL DDL Schema

```sql
CREATE TABLE IF NOT EXISTS wards (
    id VARCHAR(32) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    slum_density DOUBLE PRECISION NOT NULL,
    outdoor_labor_ratio DOUBLE PRECISION NOT NULL,
    elderly_ratio DOUBLE PRECISION NOT NULL,
    baseline_heat_risk DOUBLE PRECISION NOT NULL,
    population INTEGER DEFAULT 100000,
    area_sq_km DOUBLE PRECISION DEFAULT 5.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS interventions (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    cost_inr DOUBLE PRECISION NOT NULL,
    crew_req INTEGER NOT NULL,
    water_req_l DOUBLE PRECISION NOT NULL,
    base_risk_reduction DOUBLE PRECISION NOT NULL,
    max_per_ward INTEGER NOT NULL,
    vulnerable_impact_json JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS outcome_records (
    id SERIAL PRIMARY KEY,
    record_date DATE NOT NULL,
    ward_id VARCHAR(32) REFERENCES wards(id),
    hospital_heat_admissions INTEGER DEFAULT 0,
    mortality_count INTEGER DEFAULT 0,
    emergency_108_calls INTEGER DEFAULT 0,
    water_scarcity_complaints INTEGER DEFAULT 0,
    reported_by VARCHAR(128) DEFAULT 'AMC_HEALTH_SURVEILLANCE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_outcome_records_ward_date ON outcome_records(ward_id, record_date);
```

---

## ⚙️ Environment Variables

To bind ClimateShield to a live Amazon Aurora cluster:

```bash
# Aurora PostgreSQL Direct Endpoint
export AURORA_DB_HOST="climateshield-aurora-cluster.cluster-xyz.us-east-1.rds.amazonaws.com"
export AURORA_DB_PORT="5432"
export AURORA_DB_NAME="climateshield_db"
export AURORA_DB_USER="postgres"
export AURORA_DB_PASSWORD="your-secure-password"

# Alternatively, for Aurora Serverless Data API:
export AURORA_CLUSTER_ARN="arn:aws:rds:us-east-1:123456789012:cluster:climateshield-aurora"
export AURORA_SECRET_ARN="arn:aws:secretsmanager:us-east-1:123456789012:secret:aurora-credentials"
export AWS_DEFAULT_REGION="us-east-1"
```

---

## 🧪 Testing & Verification

Run the dedicated test suite:
```bash
python backend/test_aurora_integration.py
```
**Test Coverage**:
* Aurora connection readiness and adapter mode detection
* Aurora PostgreSQL DDL schema validation (tables, constraints, JSONB, indexes)
* Baseline dataset export integrity (wards, interventions, outcome tracking)
* Dataset sync simulation and schema parity verification
* All 4 FastAPI Aurora endpoints (`/status`, `/schema`, `/dataset`, `/sync`)
