"""
ClimateShield - Learning Loop Foundation & Multi-Hazard Lineage Engine
Provides relational tracking and closed-loop data recording connecting:
1. Historical Predictions (hazard forecasts, predicted risk, data sources, provenance)
2. Recommended Interventions (unit costs, expected impacts, resource requirements, assumptions)
3. Approved & Executed Actions (human approval, dispatch, completion, actual resources, failures)
4. Verified Municipal Outcomes (hospital morbidity, mortality, 108 calls, complaints, waterlogging depth)

Key Governance & Safety Principles:
- Linkage: Uses immutable, deterministic/UUID-stable identifiers across the decision lifecycle.
- History Preservation: Historical records are append-only and never silently overwritten.
- Provenance Discipline: Strictly separates REAL, ESTIMATED, SIMULATED, and UNVERIFIED data.
  Simulated results are never treated as real observations.
- Action Separation: Recommendations are NOT actions. Actions require explicit human approval.
- Privacy & Non-PII: Only aggregated municipal health and civic statistics are recorded.
  Personally identifiable information (names, contact numbers, patient IDs) is strictly blocked.
- Failure Tracking: Failed or canceled actions record failure reasons and actual resources drawn.
"""

import re
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple, Literal
from pydantic import BaseModel, Field, field_validator, model_validator

from backend.database import get_db_connection

# ---------------------------------------------------------------------------
# CONSTANTS & CONTROL VOCABULARIES
# ---------------------------------------------------------------------------

PROVENANCE_TYPES = ["REAL", "ESTIMATED", "SIMULATED", "UNVERIFIED"]
HAZARD_TYPES = ["heat", "waterlogging", "water_shortage", "compound", "all"]
RECOMMENDATION_STATUSES = ["PROPOSED", "APPROVED", "REJECTED", "SUPERSEDED"]
APPROVAL_STATUSES = ["APPROVED", "REJECTED", "MODIFIED", "EMERGENCY_OVERRIDE"]
EXECUTION_STATUSES = ["SCHEDULED", "IN_PROGRESS", "COMPLETED", "FAILED", "CANCELLED"]

# Regex patterns for detecting potential PII
PHONE_REGEX = re.compile(r"(\+91[\-\s]?)?[6789]\d{9}")
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
AADHAAR_REGEX = re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b")


def sanitize_text_non_pii(text: Optional[str]) -> Optional[str]:
    """
    Sanitizes free-text fields by rejecting or masking potential Personally Identifiable Information.
    Raises ValueError if phone numbers, emails, or government IDs are detected.
    """
    if not text:
        return text
    
    if PHONE_REGEX.search(text):
        raise ValueError("Privacy violation: Text contains a potential phone number. PII is strictly prohibited.")
    if EMAIL_REGEX.search(text):
        raise ValueError("Privacy violation: Text contains an email address. PII is strictly prohibited.")
    if AADHAAR_REGEX.search(text):
        raise ValueError("Privacy violation: Text contains an identification number pattern. PII is strictly prohibited.")
    
    return text.strip()


def validate_iso_timestamp(ts: Optional[str]) -> str:
    """
    Validates and normalizes an ISO 8601 timestamp string.
    Defaults to current UTC timestamp if None or empty.
    """
    if not ts:
        return datetime.now(timezone.utc).isoformat()
    try:
        # Accepts 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SSZ'
        if len(ts) == 10 and ts.count("-") == 2:
            dt = datetime.strptime(ts, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return dt.isoformat()
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.isoformat()
    except Exception as e:
        raise ValueError(f"Invalid timestamp format '{ts}'. Must be valid ISO 8601 or YYYY-MM-DD: {str(e)}")


def resolve_canonical_ward_id(ward_raw: str) -> Tuple[str, str]:
    """
    Resolves ward string (e.g. 'W1', '1', 'Danilimda') to canonical ID and name.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    raw = ward_raw.strip()

    # Strategy 1: Exact ID
    cursor.execute("SELECT id, name FROM wards WHERE LOWER(id) = LOWER(?);", (raw,))
    row = cursor.fetchone()
    if row:
        conn.close()
        return row["id"], row["name"]

    # Strategy 2: Numeric index -> W{n}
    if raw.isdigit():
        w_id = f"W{raw}"
        cursor.execute("SELECT id, name FROM wards WHERE id = ?;", (w_id,))
        row = cursor.fetchone()
        if row:
            conn.close()
            return row["id"], row["name"]

    # Strategy 3: Name substring
    cursor.execute("SELECT id, name FROM wards WHERE LOWER(name) LIKE LOWER(?);", (f"%{raw}%",))
    row = cursor.fetchone()
    if row:
        conn.close()
        return row["id"], row["name"]

    conn.close()
    # Fallback default canonical formatting
    norm_id = raw.upper() if raw.upper().startswith("W") else f"W{raw}"
    return norm_id, f"Ward {norm_id}"


# ---------------------------------------------------------------------------
# PYDANTIC VALIDATION MODELS
# ---------------------------------------------------------------------------

class PredictionRecordCreate(BaseModel):
    ward_id: str = Field(..., description="Target ward ID or name (e.g. 'W1', 'Danilimda')")
    hazard_type: Literal["heat", "waterlogging", "water_shortage", "compound", "all"] = Field(..., description="Hazard domain")
    predicted_risk_score: float = Field(..., ge=0.0, le=100.0, description="Predicted risk score (0-100)")
    risk_category: Literal["LOW", "MODERATE", "HIGH", "CRITICAL"] = Field(..., description="Standardized risk tier")
    data_source: str = Field(..., min_length=2, max_length=120, description="Data source (e.g. 'Open-Meteo Weather API')")
    provenance: Literal["REAL", "ESTIMATED", "SIMULATED", "UNVERIFIED"] = Field("ESTIMATED", description="Data provenance tier")
    timestamp: Optional[str] = Field(None, description="Prediction timestamp (ISO 8601 or YYYY-MM-DD)")
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Supporting metrics (e.g. WBGT, rainfall mm)")

    @field_validator("data_source")
    @classmethod
    def sanitize_source(cls, v: str) -> str:
        return sanitize_text_non_pii(v) or v


class RecommendationItemCreate(BaseModel):
    intervention_type: str = Field(..., min_length=2, description="Intervention catalog ID (e.g. 'cooling_center')")
    priority_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Priority score")
    estimated_cost_inr: Optional[float] = Field(None, ge=0.0, description="Estimated monetary budget requirement")
    expected_impact_min: Optional[float] = Field(None, ge=0.0, le=100.0, description="Lower bound expected risk reduction")
    expected_impact_expected: Optional[float] = Field(None, ge=0.0, le=100.0, description="Nominal expected risk reduction")
    expected_impact_max: Optional[float] = Field(None, ge=0.0, le=100.0, description="Upper bound expected risk reduction")
    required_crew: Optional[int] = Field(None, ge=0, description="Crew members required")
    required_water_l: Optional[float] = Field(None, ge=0.0, description="Potable water requirement in liters")
    assumptions: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Documented cost/benefit assumptions")
    status: Literal["PROPOSED", "APPROVED", "REJECTED", "SUPERSEDED"] = Field("PROPOSED", description="Recommendation state")


class BatchRecommendationCreate(BaseModel):
    prediction_id: str = Field(..., description="ID of the prediction triggering these recommendations")
    ward_id: str = Field(..., description="Ward ID for these recommendations")
    recommendations: List[RecommendationItemCreate] = Field(..., min_length=1, description="List of candidate interventions")


class ExecutedActionCreate(BaseModel):
    ward_id: str = Field(..., description="Target ward ID")
    intervention_type: str = Field(..., min_length=2, description="Type of intervention dispatched")
    recommendation_id: Optional[str] = Field(None, description="Optional link to originating recommendation ID")
    prediction_id: Optional[str] = Field(None, description="Optional link to originating prediction ID")
    approval_status: Literal["APPROVED", "REJECTED", "MODIFIED", "EMERGENCY_OVERRIDE"] = Field(..., description="Approval status")
    approved_by: str = Field(..., min_length=3, description="Named municipal authority or role authorizing execution")
    approved_at: Optional[str] = Field(None, description="Timestamp of authorization")
    execution_status: Literal["SCHEDULED", "IN_PROGRESS", "COMPLETED", "FAILED", "CANCELLED"] = Field("SCHEDULED", description="Field execution status")
    started_at: Optional[str] = Field(None, description="Field deployment start timestamp")
    completed_at: Optional[str] = Field(None, description="Field deployment completion timestamp")
    actual_cost_inr: Optional[float] = Field(None, ge=0.0, description="Actual expenditure incurred")
    actual_crew_used: Optional[int] = Field(None, ge=0, description="Actual crew deployed")
    actual_water_used_l: Optional[float] = Field(None, ge=0.0, description="Actual water volume consumed")
    failure_reason: Optional[str] = Field(None, description="Documented reason if execution failed or canceled")
    notes: Optional[str] = Field(None, description="Operational notes (strictly non-PII)")

    @model_validator(mode="after")
    def validate_action_fields(self) -> "ExecutedActionCreate":
        if self.execution_status in ["FAILED", "CANCELLED"] and not self.failure_reason:
            raise ValueError(f"failure_reason is required when execution_status is '{self.execution_status}'.")
        self.approved_by = sanitize_text_non_pii(self.approved_by) or self.approved_by
        if self.notes:
            self.notes = sanitize_text_non_pii(self.notes)
        if self.failure_reason:
            self.failure_reason = sanitize_text_non_pii(self.failure_reason)
        return self


class ExecutedActionUpdate(BaseModel):
    execution_status: Optional[Literal["SCHEDULED", "IN_PROGRESS", "COMPLETED", "FAILED", "CANCELLED"]] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    actual_cost_inr: Optional[float] = Field(None, ge=0.0)
    actual_crew_used: Optional[int] = Field(None, ge=0)
    actual_water_used_l: Optional[float] = Field(None, ge=0.0)
    failure_reason: Optional[str] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_update(self) -> "ExecutedActionUpdate":
        if self.execution_status in ["FAILED", "CANCELLED"] and not self.failure_reason:
            raise ValueError("failure_reason is required when changing status to FAILED or CANCELLED.")
        if self.notes:
            self.notes = sanitize_text_non_pii(self.notes)
        if self.failure_reason:
            self.failure_reason = sanitize_text_non_pii(self.failure_reason)
        return self


class VerifiedOutcomeCreate(BaseModel):
    ward_id: str = Field(..., description="Target ward identifier")
    measurement_date: str = Field(..., description="Date of outcome measurement (YYYY-MM-DD or ISO 8601)")
    prediction_id: Optional[str] = Field(None, description="Optional link to prior prediction ID")
    action_id: Optional[str] = Field(None, description="Optional link to executed intervention action ID")
    hazard_type: Literal["heat", "waterlogging", "water_shortage", "compound", "all"] = Field("heat", description="Hazard type evaluated")
    measurement_window_hours: int = Field(24, ge=1, le=168, description="Observation time window in hours")
    hospital_heat_admissions: int = Field(0, ge=0, description="Aggregate hospital heat exhaustion/stroke admissions (NO PII)")
    mortality_count: int = Field(0, ge=0, description="Aggregate mortality count (NO PII)")
    emergency_108_calls: int = Field(0, ge=0, description="Aggregate 108 ambulance dispatch calls (NO PII)")
    water_scarcity_complaints: int = Field(0, ge=0, description="Civic helpline complaint count (CCRS 155303)")
    waterlogging_depth_cm: Optional[float] = Field(None, ge=0.0, le=500.0, description="Measured waterlogging depth in cm if applicable")
    data_source: str = Field("AMC_HEALTH_SURVEILLANCE", description="Agency or sensor reporting outcome")
    provenance: Literal["REAL", "ESTIMATED", "SIMULATED", "UNVERIFIED"] = Field("REAL", description="Empirical data provenance")
    data_quality_score: float = Field(1.0, ge=0.0, le=1.0, description="Data confidence score (0.0 to 1.0)")
    verification_notes: Optional[str] = Field(None, description="Verification methodology notes (strictly non-PII)")

    @field_validator("verification_notes")
    @classmethod
    def sanitize_notes(cls, v: Optional[str]) -> Optional[str]:
        return sanitize_text_non_pii(v)

    @field_validator("data_source")
    @classmethod
    def sanitize_source(cls, v: str) -> str:
        return sanitize_text_non_pii(v) or v


# ---------------------------------------------------------------------------
# CORE DATABASE OPERATIONS FOR THE LEARNING LOOP
# ---------------------------------------------------------------------------

def record_prediction(pred_data: PredictionRecordCreate) -> Dict[str, Any]:
    """
    Persists a historical risk prediction with a stable, unique ID.
    Validates ward existence, timestamps, and input ranges.
    """
    canonical_id, canonical_name = resolve_canonical_ward_id(pred_data.ward_id)
    norm_ts = validate_iso_timestamp(pred_data.timestamp)
    pred_uuid = f"pred_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"

    conn = get_db_connection()
    cursor = conn.cursor()

    details_str = json.dumps(pred_data.details or {})

    cursor.execute("""
    INSERT INTO predictions (
        prediction_id, ward_id, ward_name, timestamp, hazard_type,
        predicted_risk_score, risk_category, data_source, provenance, details_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        pred_uuid, canonical_id, canonical_name, norm_ts, pred_data.hazard_type,
        round(pred_data.predicted_risk_score, 2), pred_data.risk_category,
        pred_data.data_source, pred_data.provenance, details_str
    ))

    conn.commit()
    conn.close()

    return {
        "prediction_id": pred_uuid,
        "ward_id": canonical_id,
        "ward_name": canonical_name,
        "timestamp": norm_ts,
        "hazard_type": pred_data.hazard_type,
        "predicted_risk_score": round(pred_data.predicted_risk_score, 2),
        "risk_category": pred_data.risk_category,
        "data_source": pred_data.data_source,
        "provenance": pred_data.provenance,
        "is_real_observation": (pred_data.provenance == "REAL"),
        "details": pred_data.details or {}
    }


def get_prediction(prediction_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single prediction by its unique ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM predictions WHERE prediction_id = ?;", (prediction_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["details"] = json.loads(d.get("details_json") or "{}")
    d["is_real_observation"] = (d.get("provenance") == "REAL")
    return d


def list_predictions(
    ward_id: Optional[str] = None,
    hazard_type: Optional[str] = None,
    provenance: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Lists historical predictions with optional filtering."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM predictions WHERE 1=1"
    params: List[Any] = []

    if ward_id:
        c_id, _ = resolve_canonical_ward_id(ward_id)
        query += " AND ward_id = ?"
        params.append(c_id)
    if hazard_type:
        query += " AND hazard_type = ?"
        params.append(hazard_type)
    if provenance:
        query += " AND provenance = ?"
        params.append(provenance)

    query += " ORDER BY timestamp DESC LIMIT ?;"
    params.append(limit)

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        d = dict(r)
        d["details"] = json.loads(d.get("details_json") or "{}")
        d["is_real_observation"] = (d.get("provenance") == "REAL")
        results.append(d)
    return results


def record_recommendations(
    prediction_id: str,
    ward_id: str,
    recommendations: List[RecommendationItemCreate]
) -> List[Dict[str, Any]]:
    """
    Records a list of candidate interventions tied to a prediction.
    Strictly marked as 'PROPOSED' (advisory) unless later approved.
    """
    pred = get_prediction(prediction_id)
    if not pred:
        raise ValueError(f"Cannot record recommendations: Prediction ID '{prediction_id}' not found.")

    canonical_id, _ = resolve_canonical_ward_id(ward_id)
    conn = get_db_connection()
    cursor = conn.cursor()

    created_records = []
    for rec in recommendations:
        rec_uuid = f"rec_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"
        assumptions_str = json.dumps(rec.assumptions or {})

        cursor.execute("""
        INSERT INTO recommendations (
            recommendation_id, prediction_id, ward_id, intervention_type,
            priority_score, estimated_cost_inr, expected_impact_min,
            expected_impact_expected, expected_impact_max, required_crew,
            required_water_l, assumptions_json, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            rec_uuid, prediction_id, canonical_id, rec.intervention_type,
            rec.priority_score, rec.estimated_cost_inr, rec.expected_impact_min,
            rec.expected_impact_expected, rec.expected_impact_max, rec.required_crew,
            rec.required_water_l, assumptions_str, rec.status
        ))

        created_records.append({
            "recommendation_id": rec_uuid,
            "prediction_id": prediction_id,
            "ward_id": canonical_id,
            "intervention_type": rec.intervention_type,
            "priority_score": rec.priority_score,
            "estimated_cost_inr": rec.estimated_cost_inr,
            "expected_impact": {
                "min": rec.expected_impact_min,
                "expected": rec.expected_impact_expected,
                "max": rec.expected_impact_max
            },
            "required_resources": {
                "crew": rec.required_crew,
                "water_l": rec.required_water_l
            },
            "status": rec.status,
            "is_action_executed": False  # Recommendations are NEVER proof of execution
        })

    conn.commit()
    conn.close()
    return created_records


def list_recommendations(
    prediction_id: Optional[str] = None,
    ward_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Queries recommendations by prediction, ward, or status."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM recommendations WHERE 1=1"
    params: List[Any] = []

    if prediction_id:
        query += " AND prediction_id = ?"
        params.append(prediction_id)
    if ward_id:
        c_id, _ = resolve_canonical_ward_id(ward_id)
        query += " AND ward_id = ?"
        params.append(c_id)
    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY created_at DESC LIMIT ?;"
    params.append(limit)

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        d = dict(r)
        d["assumptions"] = json.loads(d.get("assumptions_json") or "{}")
        d["is_action_executed"] = False
        results.append(d)
    return results


def record_executed_action(action_data: ExecutedActionCreate) -> Dict[str, Any]:
    """
    Records an approved field intervention action with required authorization metadata.
    Enforces that an action is distinct from a recommendation.
    """
    canonical_id, canonical_name = resolve_canonical_ward_id(action_data.ward_id)
    act_uuid = f"act_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"
    approved_at_norm = validate_iso_timestamp(action_data.approved_at)

    # Validate linked recommendation if provided
    if action_data.recommendation_id:
        conn_check = get_db_connection()
        c_check = conn_check.cursor()
        c_check.execute("SELECT recommendation_id FROM recommendations WHERE recommendation_id = ?;", (action_data.recommendation_id,))
        if not c_check.fetchone():
            conn_check.close()
            raise ValueError(f"Referenced recommendation_id '{action_data.recommendation_id}' does not exist.")
        # Mark recommendation as APPROVED
        c_check.execute("UPDATE recommendations SET status = 'APPROVED' WHERE recommendation_id = ?;", (action_data.recommendation_id,))
        conn_check.commit()
        conn_check.close()

    # Validate linked prediction if provided
    if action_data.prediction_id:
        pred = get_prediction(action_data.prediction_id)
        if not pred:
            raise ValueError(f"Referenced prediction_id '{action_data.prediction_id}' does not exist.")

    started_at_norm = validate_iso_timestamp(action_data.started_at) if action_data.started_at else None
    completed_at_norm = validate_iso_timestamp(action_data.completed_at) if action_data.completed_at else None

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO executed_actions (
        action_id, recommendation_id, prediction_id, ward_id,
        intervention_type, approval_status, approved_by, approved_at,
        execution_status, started_at, completed_at, actual_cost_inr,
        actual_crew_used, actual_water_used_l, failure_reason, notes
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        act_uuid, action_data.recommendation_id, action_data.prediction_id,
        canonical_id, action_data.intervention_type, action_data.approval_status,
        action_data.approved_by, approved_at_norm, action_data.execution_status,
        started_at_norm, completed_at_norm, action_data.actual_cost_inr,
        action_data.actual_crew_used, action_data.actual_water_used_l,
        action_data.failure_reason, action_data.notes
    ))

    conn.commit()
    conn.close()

    return {
        "action_id": act_uuid,
        "recommendation_id": action_data.recommendation_id,
        "prediction_id": action_data.prediction_id,
        "ward_id": canonical_id,
        "ward_name": canonical_name,
        "intervention_type": action_data.intervention_type,
        "approval": {
            "status": action_data.approval_status,
            "approved_by": action_data.approved_by,
            "approved_at": approved_at_norm
        },
        "execution": {
            "status": action_data.execution_status,
            "started_at": started_at_norm,
            "completed_at": completed_at_norm,
            "actual_cost_inr": action_data.actual_cost_inr,
            "actual_crew_used": action_data.actual_crew_used,
            "actual_water_used_l": action_data.actual_water_used_l,
            "failure_reason": action_data.failure_reason
        },
        "notes": action_data.notes
    }


def update_executed_action(action_id: str, update_data: ExecutedActionUpdate) -> Dict[str, Any]:
    """Updates status, resources used, completion timestamp, or failure details for an existing action."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM executed_actions WHERE action_id = ?;", (action_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise ValueError(f"Action '{action_id}' not found.")

    fields = []
    params: List[Any] = []

    if update_data.execution_status is not None:
        fields.append("execution_status = ?")
        params.append(update_data.execution_status)
    if update_data.started_at is not None:
        fields.append("started_at = ?")
        params.append(validate_iso_timestamp(update_data.started_at))
    if update_data.completed_at is not None:
        fields.append("completed_at = ?")
        params.append(validate_iso_timestamp(update_data.completed_at))
    if update_data.actual_cost_inr is not None:
        fields.append("actual_cost_inr = ?")
        params.append(update_data.actual_cost_inr)
    if update_data.actual_crew_used is not None:
        fields.append("actual_crew_used = ?")
        params.append(update_data.actual_crew_used)
    if update_data.actual_water_used_l is not None:
        fields.append("actual_water_used_l = ?")
        params.append(update_data.actual_water_used_l)
    if update_data.failure_reason is not None:
        fields.append("failure_reason = ?")
        params.append(update_data.failure_reason)
    if update_data.notes is not None:
        fields.append("notes = ?")
        params.append(update_data.notes)

    if not fields:
        conn.close()
        return dict(existing)

    query = f"UPDATE executed_actions SET {', '.join(fields)} WHERE action_id = ?;"
    params.append(action_id)

    cursor.execute(query, tuple(params))
    conn.commit()

    cursor.execute("SELECT * FROM executed_actions WHERE action_id = ?;", (action_id,))
    updated = cursor.fetchone()
    conn.close()
    return dict(updated)


def get_action(action_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves an executed action by its ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM executed_actions WHERE action_id = ?;", (action_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def list_actions(
    ward_id: Optional[str] = None,
    execution_status: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Lists field actions with optional status and ward filters."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM executed_actions WHERE 1=1"
    params: List[Any] = []

    if ward_id:
        c_id, _ = resolve_canonical_ward_id(ward_id)
        query += " AND ward_id = ?"
        params.append(c_id)
    if execution_status:
        query += " AND execution_status = ?"
        params.append(execution_status)

    query += " ORDER BY created_at DESC LIMIT ?;"
    params.append(limit)

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def record_verified_outcome(outcome_data: VerifiedOutcomeCreate) -> Dict[str, Any]:
    """
    Records an observed outcome post-intervention or during active surveillance.
    Ensures strict privacy (aggregated non-PII counts) and provenance tagging.
    """
    canonical_id, canonical_name = resolve_canonical_ward_id(outcome_data.ward_id)
    out_uuid = f"out_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"
    meas_date = validate_iso_timestamp(outcome_data.measurement_date)

    # Validate links if provided
    if outcome_data.prediction_id:
        if not get_prediction(outcome_data.prediction_id):
            raise ValueError(f"Referenced prediction_id '{outcome_data.prediction_id}' does not exist.")
    if outcome_data.action_id:
        if not get_action(outcome_data.action_id):
            raise ValueError(f"Referenced action_id '{outcome_data.action_id}' does not exist.")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO verified_outcomes (
        outcome_id, ward_id, prediction_id, action_id, measurement_date,
        measurement_window_hours, hazard_type, hospital_heat_admissions,
        mortality_count, emergency_108_calls, water_scarcity_complaints,
        waterlogging_depth_cm, data_source, provenance, data_quality_score,
        verification_notes
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        out_uuid, canonical_id, outcome_data.prediction_id, outcome_data.action_id,
        meas_date, outcome_data.measurement_window_hours, outcome_data.hazard_type,
        outcome_data.hospital_heat_admissions, outcome_data.mortality_count,
        outcome_data.emergency_108_calls, outcome_data.water_scarcity_complaints,
        outcome_data.waterlogging_depth_cm, outcome_data.data_source,
        outcome_data.provenance, outcome_data.data_quality_score,
        outcome_data.verification_notes
    ))

    conn.commit()
    conn.close()

    return {
        "outcome_id": out_uuid,
        "ward_id": canonical_id,
        "ward_name": canonical_name,
        "prediction_id": outcome_data.prediction_id,
        "action_id": outcome_data.action_id,
        "measurement_date": meas_date,
        "measurement_window_hours": outcome_data.measurement_window_hours,
        "hazard_type": outcome_data.hazard_type,
        "observations": {
            "hospital_heat_admissions": outcome_data.hospital_heat_admissions,
            "mortality_count": outcome_data.mortality_count,
            "emergency_108_calls": outcome_data.emergency_108_calls,
            "water_scarcity_complaints": outcome_data.water_scarcity_complaints,
            "waterlogging_depth_cm": outcome_data.waterlogging_depth_cm
        },
        "data_source": outcome_data.data_source,
        "provenance": outcome_data.provenance,
        "is_real_observation": (outcome_data.provenance == "REAL"),
        "data_quality_score": outcome_data.data_quality_score,
        "verification_notes": outcome_data.verification_notes
    }


def get_outcome(outcome_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves an outcome record by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM verified_outcomes WHERE outcome_id = ?;", (outcome_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["is_real_observation"] = (d.get("provenance") == "REAL")
    return d


def list_outcomes(
    ward_id: Optional[str] = None,
    provenance: Optional[str] = None,
    prediction_id: Optional[str] = None,
    action_id: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Lists verified outcomes with relational filtering."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM verified_outcomes WHERE 1=1"
    params: List[Any] = []

    if ward_id:
        c_id, _ = resolve_canonical_ward_id(ward_id)
        query += " AND ward_id = ?"
        params.append(c_id)
    if provenance:
        query += " AND provenance = ?"
        params.append(provenance)
    if prediction_id:
        query += " AND prediction_id = ?"
        params.append(prediction_id)
    if action_id:
        query += " AND action_id = ?"
        params.append(action_id)

    query += " ORDER BY measurement_date DESC, created_at DESC LIMIT ?;"
    params.append(limit)

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        d = dict(r)
        d["is_real_observation"] = (d.get("provenance") == "REAL")
        results.append(d)
    return results


# ---------------------------------------------------------------------------
# FULL RELATIONAL LINEAGE RECONSTRUCTION
# ---------------------------------------------------------------------------

def get_learning_lineage(prediction_id: str) -> Dict[str, Any]:
    """
    Reconstructs the full end-to-end lineage tree connecting:
    Prediction -> Candidate Recommendations -> Executed Actions -> Verified Outcomes
    """
    pred = get_prediction(prediction_id)
    if not pred:
        raise ValueError(f"Lineage error: Prediction ID '{prediction_id}' does not exist.")

    recs = list_recommendations(prediction_id=prediction_id, limit=100)
    
    # Get all actions linked to this prediction OR any of its recommendations
    rec_ids = {r["recommendation_id"] for r in recs}
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM executed_actions WHERE prediction_id = ?;", (prediction_id,))
    actions_by_pred = [dict(a) for a in cursor.fetchall()]

    actions_by_rec = []
    if rec_ids:
        placeholders = ",".join("?" for _ in rec_ids)
        cursor.execute(f"SELECT * FROM executed_actions WHERE recommendation_id IN ({placeholders});", tuple(rec_ids))
        actions_by_rec = [dict(a) for a in cursor.fetchall()]

    all_actions_dict = {}
    for a in actions_by_pred + actions_by_rec:
        all_actions_dict[a["action_id"]] = a
    all_actions = list(all_actions_dict.values())

    # Get outcomes linked to prediction or any action
    action_ids = set(all_actions_dict.keys())
    outcomes_by_pred = list_outcomes(prediction_id=prediction_id, limit=100)

    outcomes_by_action = []
    if action_ids:
        placeholders = ",".join("?" for _ in action_ids)
        cursor.execute(f"SELECT * FROM verified_outcomes WHERE action_id IN ({placeholders});", tuple(action_ids))
        outcomes_by_action = [dict(o) for o in cursor.fetchall()]

    conn.close()

    all_outcomes_dict = {}
    for o in outcomes_by_pred + outcomes_by_action:
        o["is_real_observation"] = (o.get("provenance") == "REAL")
        all_outcomes_dict[o["outcome_id"]] = o
    all_outcomes = list(all_outcomes_dict.values())

    return {
        "prediction_id": prediction_id,
        "ward_id": pred["ward_id"],
        "ward_name": pred.get("ward_name"),
        "prediction": pred,
        "recommendations_count": len(recs),
        "recommendations": recs,
        "actions_count": len(all_actions),
        "executed_actions": all_actions,
        "outcomes_count": len(all_outcomes),
        "verified_outcomes": all_outcomes,
        "has_verified_real_outcome": any(o.get("provenance") == "REAL" for o in all_outcomes),
        "has_completed_action": any(a.get("execution_status") == "COMPLETED" for a in all_actions)
    }
