# ☁️ Amazon Bedrock in ClimateShield: Architecture & Justification

> **Project**: ClimateShield — Decision Support System for Climate & Thermal Extremes  
> **Deployment Target**: Ahmedabad Municipal Corporation (AMC), Gujarat, India  
> **Service**: Amazon Bedrock Foundation Models (`anthropic.claude-3-haiku`, `anthropic.claude-3-5-sonnet`, `amazon.titan-text-express`)  

---

## 📌 Executive Summary

ClimateShield merges empirical thermodynamics (Stull 2011 Wet-Bulb Globe Temperature, ERA5-Land reanalysis, ECOSTRESS land surface temperatures) with constrained Operations Research (Integer Linear Programming via Google OR-Tools and PuLP) to produce mathematically optimal municipal resource allocations (hydration kiosks, cool roofs, water tankers, emergency shade).

However, **raw numbers and solver matrices do not save lives in real-time crisis situations**. Municipal incident commanders, field health workers, and citizens in informal settlements cannot act on raw mathematical indices like `WBGT = 33.4°C` or constraint vectors like $x_{w,k} = 1$.

**Amazon Bedrock bridges the critical gap between computational risk analytics and human operational execution.**

```
┌─────────────────────────────────┐      ┌──────────────────────────────┐
│  Physics & Geospatial Ingestion │      │  Constrained Optimization    │
│  - Open-Meteo & ERA5 Reanalysis │ ───► │  - Google OR-Tools ILP       │
│  - Stull (2011) WBGT Engine     │      │  - Budget, Crew, Water Caps  │
│  - ECOSTRESS LST Surface Temp   │      │  - Equity & Gini Constraints │
└─────────────────────────────────┘      └──────────────┬───────────────┘
                                                        │
                                                        ▼
                                         ┌──────────────────────────────┐
                                         │       AMAZON BEDROCK         │
                                         │  (Claude 3 / Amazon Titan)   │
                                         │  - Multi-Lingual GenAI Engine│
                                         │  - Evidence-Grounded Context │
                                         └──────────────┬───────────────┘
                                                        │
                      ┌─────────────────────────────────┴─────────────────────────────────┐
                      ▼                                                                   ▼
       ┌─────────────────────────────┐                                     ┌─────────────────────────────┐
       │   Municipal Action Plans    │                                     │  Public Broadcast Alerts   │
       │   - Priority Directives     │                                     │  - SMS / WhatsApp Alerts   │
       │   - Shelter Deployment      │                                     │  - English, Gujarati, Hindi│
       │   - Field Crew Directives   │                                     │  - Vulnerable Worker Focus │
       └─────────────────────────────┘                                     └─────────────────────────────┘
```

---

## 🎯 Why Amazon Bedrock? Key Architectural Justifications

### 1. Grounded Context (RAG-Style Determinism without Hallucination)
Rather than using generic, ungrounded conversational chatbots, ClimateShield utilizes Amazon Bedrock as an **inference synthesizer directly bounded by verified telemetry**:
* Bedrock receives real-time computed inputs: `Peak Effective WBGT`, `Ward Vulnerability Index (Danilimda, Behrampura, Vatva)`, `Budget Consumed`, and `Equity Balance Score`.
* Grounding system prompts prevent hallucinated interventions: the model can only formulate directives based on the **exact interventions allocated by the OR-Tools optimization engine**.

### 2. Multi-Lingual Civic Emergency Communications (English, Gujarati, Hindi)
Ahmedabad's population spans diverse linguistic demographics, including daily wage laborers, construction workers, and street vendors who primarily communicate in **Gujarati** or **Hindi**:
* Amazon Bedrock translates complex thermal risk metrics into clear, culturally relevant municipal safety instructions in Gujarati (ગુજરાતી) and Hindi (हिन्दी).
* Enables automatic generation of punchy, two-sentence SMS/WhatsApp broadcast warnings for emergency distribution cells.

### 3. Enterprise Data Privacy and Zero Data Leakage
Municipal emergency data, vulnerable settlement coordinates, and infrastructure allocation data cannot be routed through consumer-grade public AI APIs:
* **Amazon Bedrock ensures that customer data is never used to train base foundation models**.
* All telemetry and generated advisories remain completely within the municipal cloud boundary and conform to AWS IAM role policies.

### 4. Enterprise-Grade High Availability with Graceful Degradation
Emergency response systems must never experience single-point failures:
* In `backend/bedrock_service.py`, ClimateShield implements a resilient dual-layer architecture:
  1. **Primary Layer**: Live invocation of Amazon Bedrock (`anthropic.claude-3-haiku`, `anthropic.claude-3-5-sonnet`, or `amazon.titan-text-express`) via `boto3`.
  2. **Deterministic Fallback Layer**: If AWS credentials are temporarily unconfigured, during network downtime, or offline simulations, a deterministic municipal rule engine instantly supplies verified action summaries in all three languages with zero latency and zero service interruptions.

---

## 🛠️ Implementation Details

### API Endpoints

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/bedrock/advisory` | `POST` | Synthesizes WBGT risk and optimization allocations into structured municipal action plans and public warnings. |
| `/api/bedrock/status` | `GET` | Reports Bedrock connectivity, active model family, target AWS region, and supported languages. |

### Sample Request (`POST /api/bedrock/advisory`)

```json
{
  "city_name": "Ahmedabad",
  "max_hazard_level": "CRITICAL",
  "peak_wbgt": 33.4,
  "ward_summaries": [
    { "ward_id": "W1", "name": "Danilimda", "effective_wbgt": 33.4, "risk_category": "CRITICAL" },
    { "ward_id": "W2", "name": "Behrampura", "effective_wbgt": 32.8, "risk_category": "EXTREME" }
  ],
  "allocated_interventions": [
    { "intervention_type": "Hydration Kiosk", "quantity": 12 },
    { "intervention_type": "Cool Roof Application", "quantity": 30 },
    { "intervention_type": "Emergency Water Tanker", "quantity": 5 }
  ],
  "budget_used": 500000.0,
  "equity_score": 0.92,
  "target_audience": "MUNICIPAL_OFFICERS",
  "language": "gu"
}
```

### Sample Bedrock Output (Gujarati Response)

```json
{
  "status": "SUCCESS",
  "provider": "Amazon Bedrock",
  "model_id": "anthropic.claude-3-haiku-20240307-v1:0",
  "language": "gu",
  "hazard_level": "CRITICAL",
  "peak_wbgt": 33.4,
  "executive_summary": "અમદાવાદ મહાનગર પાલિકા (AMC) હીટ એલર્ટ: CRITICAL જોખમ. પીક WBGT 33.4°C નોંધાયેલ છે...",
  "priority_directives": [
    "Danilimda અને Behrampura ના સ્લમ વિસ્તારોમાં તાત્કાલિક પીવાના પાણીના ટેન્કર અને ORS કિઓસ્ક તૈનાત કરો.",
    "બપોરે ૧૨ થી ૪ વાગ્યા સુધી બાંધકામ અને મજૂરી કામ સ્થગિત રાખવા માટે આદેશ જાહેર કરો.",
    "તમામ અર્બન હેલ્થ સેન્ટર (UHC) ખાતે કૂલિંગ સેન્ટરો કાર્યરત કરો."
  ],
  "citizen_broadcast_alert": "સાવચેત રહો: શહેરમાં અતિશય ગરમીનું મોજું (33.4°C WBGT). બપોરે બહાર જવાનું ટાળો અને પૂરતું પાણી પીઓ."
}
```

---

## ⚙️ Configuration & Environment Variables

To connect live Amazon Bedrock credentials, set the following environment variables:

```bash
# AWS Credentials
export AWS_ACCESS_KEY_ID="your-aws-access-key"
export AWS_SECRET_ACCESS_KEY="your-aws-secret-key"
export AWS_DEFAULT_REGION="us-east-1"

# Target Bedrock Model (Defaults to Claude 3 Haiku)
export AWS_BEDROCK_MODEL_ID="anthropic.claude-3-haiku-20240307-v1:0"
# Alternative options:
# export AWS_BEDROCK_MODEL_ID="anthropic.claude-3-5-sonnet-20240620-v1:0"
# export AWS_BEDROCK_MODEL_ID="amazon.titan-text-express-v1"
```

---

## 🏆 Hackathon Value Proposition

1. **End-to-End AWS Integration**: Demonstrates tangible usage of AWS GenAI primitives (`boto3`, Bedrock Runtime, Claude/Titan).
2. **Civic & Social Impact**: Solves the real-world communication barrier in municipal heat action plans for vulnerable urban populations.
3. **Fail-Safe Reliability**: Even during live stage judging with zero AWS credits or network glitches, the platform continues to run seamlessly via the offline deterministic fallback engine.
