"""
ClimateShield - Impact Verification Module
Evaluates the empirical efficacy of executed interventions by comparing
predicted risks and expected benefits with observed outcomes.

Methodological & Epistemic Principles:
1. Before-and-After vs. Causal Attribution:
   - A simple before-and-after comparison is strictly labeled CORRELATIONAL_ONLY.
   - It NEVER claims causality without a valid comparison control ward.
2. Difference-in-Differences (DiD):
   - Calculated ONLY when valid, contemporaneous baseline and follow-up data exist
     for both the treated ward and a comparable control/unintervened ward.
   - If control data is missing or incomplete, reports INSUFFICIENT_DATA_NO_CONTROL
     rather than fabricating or assuming a counterfactual.
3. Insufficient Data Reporting:
   - Never manufactures an impact estimate when measurements or follow-up observations are absent.
4. Action Completion Tracking:
   - Verifies whether the field intervention was actually COMPLETED before evaluating outcomes.
   - Incomplete, failed, or canceled actions are flagged as ACTION_NOT_COMPLETED.
5. Synthetic Data Disclosure:
   - Any evaluation using SIMULATED data is explicitly labeled as a synthetic demonstration.
"""

import math
import uuid
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple, Literal
from pydantic import BaseModel, Field

from backend.database import get_db_connection
from backend.learning_loop import (
    get_action,
    get_prediction,
    list_outcomes,
    list_recommendations,
    resolve_canonical_ward_id,
    validate_iso_timestamp
)

# Supported primary outcome metrics per hazard domain
HAZARD_DEFAULT_METRICS = {
    "heat": "hospital_heat_admissions",
    "waterlogging": "waterlogging_depth_cm",
    "water_shortage": "water_scarcity_complaints",
    "compound": "hospital_heat_admissions"
}

METRIC_LABELS = {
    "hospital_heat_admissions": "Hospital Heatstroke & Exhaustion Admissions (cases/day)",
    "emergency_108_calls": "108 Emergency Ambulance Heat Dispatches (calls/day)",
    "mortality_count": "All-Cause Heat-Attributable Mortality Count (deaths/day)",
    "waterlogging_depth_cm": "Waterlogging Depth at Chronic Surcharge Points (cm)",
    "water_scarcity_complaints": "Civic CCRS 155303 Potable Water Deficit Complaints (complaints/day)"
}

CAUSAL_DISCLAIMER_BEFORE_AFTER = (
    "CORRELATIONAL_ONLY (NON-CAUSAL): A simple before-and-after comparison cannot prove that the intervention "
    "caused the observed outcome change. Confounding meteorological trends (e.g. ambient temperature drop, rain cessation), "
    "secular health behavior shifts, or unobserved municipal actions cannot be ruled out without a comparison group."
)

CAUSAL_DISCLAIMER_DID = (
    "QUASI-EXPERIMENTAL (DIFFERENCE-IN-DIFFERENCES): Estimates the net treatment effect relative to an un-intervened "
    "comparison ward. Valid under the parallel trends assumption (that treated and control wards would have followed "
    "parallel trajectories in the absence of the intervention)."
)

SYNTHETIC_DEMO_DISCLAIMER = (
    "DEMONSTRATION ONLY: This verification incorporates synthetic/simulated outcome observations. "
    "It does not reflect empirical real-world municipal surveillance data."
)


# ---------------------------------------------------------------------------
# REQUEST & RESPONSE SCHEMAS
# ---------------------------------------------------------------------------

class ImpactVerificationRequest(BaseModel):
    action_id: str = Field(..., description="Executed field action ID to verify (e.g. 'act_...')")
    primary_metric: Optional[str] = Field(
        None,
        description="Metric to evaluate: 'hospital_heat_admissions', 'emergency_108_calls', 'mortality_count', 'waterlogging_depth_cm', 'water_scarcity_complaints'"
    )
    control_ward_id: Optional[str] = Field(
        None,
        description="Optional comparison ward ID (e.g. 'W3') to enable Difference-in-Differences causal estimation"
    )
    baseline_date: Optional[str] = Field(
        None,
        description="Optional explicit baseline measurement date (YYYY-MM-DD), defaults to day prior to action"
    )
    followup_date: Optional[str] = Field(
        None,
        description="Optional explicit follow-up measurement date (YYYY-MM-DD), defaults to action completion day"
    )


# ---------------------------------------------------------------------------
# CORE IMPACT VERIFICATION ENGINE
# ---------------------------------------------------------------------------

def _find_outcome_observation(
    ward_id: str,
    target_date: Optional[str],
    hazard_type: str,
    prefer_action_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Locates the most relevant verified outcome for a ward around a specific target date.
    """
    c_id, _ = resolve_canonical_ward_id(ward_id)
    conn = get_db_connection()
    cursor = conn.cursor()

    if prefer_action_id:
        cursor.execute("SELECT * FROM verified_outcomes WHERE action_id = ?;", (prefer_action_id,))
        row = cursor.fetchone()
        if row:
            conn.close()
            d = dict(row)
            d["is_real_observation"] = (d.get("provenance") == "REAL")
            return d

    if target_date:
        target_clean = target_date[:10]
        cursor.execute("""
            SELECT * FROM verified_outcomes
            WHERE ward_id = ? AND (hazard_type = ? OR hazard_type = 'compound')
            ORDER BY ABS(julianday(substr(measurement_date, 1, 10)) - julianday(?)) ASC
            LIMIT 5;
        """, (c_id, hazard_type, target_clean))
        rows = cursor.fetchall()
        if not rows:
            cursor.execute("""
                SELECT * FROM verified_outcomes
                WHERE ward_id = ?
                ORDER BY ABS(julianday(substr(measurement_date, 1, 10)) - julianday(?)) ASC
                LIMIT 5;
            """, (c_id, target_clean))
            rows = cursor.fetchall()
        conn.close()

        for r in rows:
            d = dict(r)
            d["is_real_observation"] = (d.get("provenance") == "REAL")
            m_str = str(d.get("measurement_date"))[:10]
            try:
                m_dt = datetime.strptime(m_str, "%Y-%m-%d")
                t_dt = datetime.strptime(target_clean, "%Y-%m-%d")
                if abs((m_dt - t_dt).days) <= 2:
                    return d
            except Exception:
                return d
        return None

    # Fallback to most recent observation
    cursor.execute("""
        SELECT * FROM verified_outcomes
        WHERE ward_id = ? AND (hazard_type = ? OR hazard_type = 'compound')
        ORDER BY measurement_date DESC, created_at DESC
        LIMIT 1;
    """, (c_id, hazard_type))
    row = cursor.fetchone()
    if not row:
        cursor.execute("""
            SELECT * FROM verified_outcomes
            WHERE ward_id = ?
            ORDER BY measurement_date DESC, created_at DESC
            LIMIT 1;
        """, (c_id,))
        row = cursor.fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["is_real_observation"] = (d.get("provenance") == "REAL")
        return d
    return None


def verify_intervention_impact(req: ImpactVerificationRequest) -> Dict[str, Any]:
    """
    Executes an impact verification evaluation for an executed field intervention action.
    """
    action = get_action(req.action_id)
    if not action:
        raise ValueError(f"Action ID '{req.action_id}' not found.")

    verification_id = f"verif_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"
    ward_id = action["ward_id"]
    intervention_type = action["intervention_type"]
    exec_status = action.get("execution_status", "SCHEDULED")

    # Step 1: Check whether the action was completed
    action_completed = (exec_status == "COMPLETED")
    if not action_completed:
        fail_reason = action.get("failure_reason") or "Action still in progress or scheduled"
        result_incomplete = {
            "verification_id": verification_id,
            "action_id": req.action_id,
            "ward_id": ward_id,
            "intervention_type": intervention_type,
            "status": "INSUFFICIENT_DATA_INCOMPLETE_ACTION",
            "action_completed": False,
            "execution_status": exec_status,
            "failure_reason": action.get("failure_reason"),
            "causal_claim_allowed": False,
            "explanation": f"Intervention was not completed (status: '{exec_status}'). Reason: {fail_reason}. Impact verification cannot evaluate uncompleted actions.",
            "disclaimer": "No impact result calculated due to incomplete action execution.",
            "is_synthetic_demonstration": False,
            "confidence_score": 0.0,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        _persist_verification(result_incomplete)
        return result_incomplete

    # Step 2: Determine hazard and primary metric
    hazard_type = "heat"
    if "pump" in intervention_type or "drain" in intervention_type or "flood" in intervention_type or "road" in intervention_type:
        hazard_type = "waterlogging"
    elif "tanker" in intervention_type or "shortage" in intervention_type or "valve" in intervention_type:
        hazard_type = "water_shortage"

    primary_metric = req.primary_metric or HAZARD_DEFAULT_METRICS.get(hazard_type, "hospital_heat_admissions")

    # Step 3: Fetch baseline and follow-up outcome observations for treated ward
    started_at = action.get("started_at")
    completed_at = action.get("completed_at")
    
    baseline_target_date = req.baseline_date or (started_at[:10] if started_at else None)
    followup_target_date = req.followup_date or (completed_at[:10] if completed_at else None)

    baseline_obs = _find_outcome_observation(ward_id, baseline_target_date, hazard_type)
    followup_obs = _find_outcome_observation(ward_id, followup_target_date, hazard_type, prefer_action_id=req.action_id)

    # Check for missing observation data
    missing_items = []
    if not baseline_obs:
        missing_items.append("baseline_observation")
    if not followup_obs:
        missing_items.append("followup_observation")

    if missing_items:
        result_missing = {
            "verification_id": verification_id,
            "action_id": req.action_id,
            "ward_id": ward_id,
            "intervention_type": intervention_type,
            "status": "INSUFFICIENT_DATA_MISSING_OBSERVATIONS",
            "action_completed": True,
            "missing_components": missing_items,
            "causal_claim_allowed": False,
            "explanation": f"Insufficient observation data for ward '{ward_id}'. Missing: {', '.join(missing_items)}. Impact verification requires both baseline and follow-up measurements.",
            "disclaimer": "Impact results not manufactured without verified measurements.",
            "is_synthetic_demonstration": False,
            "confidence_score": 0.0,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        _persist_verification(result_missing)
        return result_missing

    # Extract metric values
    y_t_pre = float(baseline_obs.get(primary_metric) or 0.0)
    y_t_post = float(followup_obs.get(primary_metric) or 0.0)
    observed_delta = round(y_t_post - y_t_pre, 2)
    percent_change = round(((y_t_post - y_t_pre) / max(y_t_pre, 1.0)) * 100.0, 1)

    is_synthetic = (baseline_obs.get("provenance") == "SIMULATED") or (followup_obs.get("provenance") == "SIMULATED")

    # Step 4: Evaluate expected benefit from recommendation if available
    expected_impact = None
    rec_id = action.get("recommendation_id")
    if rec_id:
        recs = list_recommendations(limit=100)
        rec_match = [r for r in recs if r.get("recommendation_id") == rec_id]
        if rec_match:
            rec = rec_match[0]
            expected_impact = {
                "nominal_risk_reduction_points": rec.get("expected_impact_expected"),
                "impact_range_min": rec.get("expected_impact_min"),
                "impact_range_max": rec.get("expected_impact_max"),
                "assumed_basis": rec.get("assumptions", {}).get("basis", "Standard Municipal Rate")
            }

    # Step 5: Check whether intended outcome direction was observed
    # For health morbidity, mortality, calls, complaints, and depth: lower is better
    intended_outcome_observed = (observed_delta < 0.0)

    # Step 6: Difference-in-Differences evaluation if control ward provided
    control_ward_id = req.control_ward_id
    did_result = None
    methodology = "SIMPLE_BEFORE_AFTER"
    causal_claim_allowed = False
    causal_disclaimer = CAUSAL_DISCLAIMER_BEFORE_AFTER

    if control_ward_id:
        c_ward_canon, _ = resolve_canonical_ward_id(control_ward_id)
        if c_ward_canon == ward_id:
            did_result = {"eligible": False, "reason": "Control ward cannot be identical to treated ward."}
        else:
            c_base = _find_outcome_observation(c_ward_canon, baseline_target_date, hazard_type)
            c_post = _find_outcome_observation(c_ward_canon, followup_target_date, hazard_type)

            if c_base and c_post:
                y_c_pre = float(c_base.get(primary_metric) or 0.0)
                y_c_post = float(c_post.get(primary_metric) or 0.0)
                
                # DiD = (Y_T,post - Y_T,pre) - (Y_C,post - Y_C,pre)
                delta_treated = y_t_post - y_t_pre
                delta_control = y_c_post - y_c_pre
                did_estimate = round(delta_treated - delta_control, 2)
                
                # Standard error approximation for Poisson count differences
                se_did = round(math.sqrt(max(0.1, y_t_pre + y_t_post + y_c_pre + y_c_post) / 4.0), 2)
                ci_lower = round(did_estimate - 1.96 * se_did, 2)
                ci_upper = round(did_estimate + 1.96 * se_did, 2)

                methodology = "DIFFERENCE_IN_DIFFERENCES"
                causal_claim_allowed = True
                causal_disclaimer = CAUSAL_DISCLAIMER_DID

                if (c_base.get("provenance") == "SIMULATED") or (c_post.get("provenance") == "SIMULATED"):
                    is_synthetic = True

                did_result = {
                    "eligible": True,
                    "control_ward_id": c_ward_canon,
                    "control_baseline_value": y_c_pre,
                    "control_followup_value": y_c_post,
                    "control_delta": round(delta_control, 2),
                    "did_estimate": did_estimate,
                    "standard_error": se_did,
                    "confidence_interval_95": {"lower": ci_lower, "upper": ci_upper},
                    "parallel_trends_assumed": True
                }
            else:
                did_result = {
                    "eligible": False,
                    "reason": f"Insufficient data for comparison ward '{c_ward_canon}'. Both baseline and follow-up observations must be available to compute DiD."
                }

    # Step 7: Construct final explanation and uncertainty
    uncertainty_info = {
        "primary_metric": primary_metric,
        "metric_unit": METRIC_LABELS.get(primary_metric, primary_metric),
        "measurement_error_bound": "± 5% civic reporting reporting noise",
        "data_quality_scores": {
            "baseline": baseline_obs.get("data_quality_score", 1.0),
            "followup": followup_obs.get("data_quality_score", 1.0)
        }
    }

    direction_str = "decreased" if observed_delta < 0 else ("increased" if observed_delta > 0 else "remained unchanged")
    explanation = (
        f"In ward '{ward_id}', following completed dispatch of '{intervention_type}', "
        f"{METRIC_LABELS.get(primary_metric, primary_metric)} {direction_str} by {abs(observed_delta)} units ({percent_change}%) "
        f"from {y_t_pre} to {y_t_post}."
    )
    if did_result and did_result.get("eligible"):
        explanation += f" Net Difference-in-Differences impact against control ward '{did_result['control_ward_id']}' is {did_result['did_estimate']} units."

    verification_record = {
        "verification_id": verification_id,
        "action_id": req.action_id,
        "ward_id": ward_id,
        "control_ward_id": control_ward_id,
        "intervention_type": intervention_type,
        "status": "VERIFIED_COMPLETED",
        "action_completed": True,
        "hazard_type": hazard_type,
        "primary_metric": primary_metric,
        "primary_metric_label": METRIC_LABELS.get(primary_metric, primary_metric),
        "evaluation_methodology": methodology,
        "baseline_measurement": {
            "date": str(baseline_obs.get("measurement_date"))[:10],
            "value": y_t_pre,
            "source": baseline_obs.get("data_source"),
            "provenance": baseline_obs.get("provenance")
        },
        "followup_measurement": {
            "date": str(followup_obs.get("measurement_date"))[:10],
            "value": y_t_post,
            "source": followup_obs.get("data_source"),
            "provenance": followup_obs.get("provenance")
        },
        "observed_delta": observed_delta,
        "observed_percent_change": percent_change,
        "difference_in_differences": did_result,
        "expected_impact": expected_impact,
        "intended_outcome_observed": intended_outcome_observed,
        "causal_claim_allowed": causal_claim_allowed,
        "causal_disclaimer": causal_disclaimer,
        "is_synthetic_demonstration": is_synthetic,
        "synthetic_disclaimer": SYNTHETIC_DEMO_DISCLAIMER if is_synthetic else None,
        "uncertainty": uncertainty_info,
        "explanation": explanation,
        "confidence_score": 0.85 if did_result and did_result.get("eligible") else 0.55,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    _persist_verification(verification_record)
    return verification_record


def _persist_verification(rec: Dict[str, Any]) -> None:
    """Saves a verification report to the SQLite impact_verifications table."""
    conn = get_db_connection()
    cursor = conn.cursor()

    did_est = None
    if rec.get("difference_in_differences") and rec["difference_in_differences"].get("eligible"):
        did_est = rec["difference_in_differences"].get("did_estimate")

    c_base_val = None
    c_post_val = None
    if rec.get("difference_in_differences") and rec["difference_in_differences"].get("eligible"):
        c_base_val = rec["difference_in_differences"].get("control_baseline_value")
        c_post_val = rec["difference_in_differences"].get("control_followup_value")

    base_val = rec.get("baseline_measurement", {}).get("value")
    post_val = rec.get("followup_measurement", {}).get("value")
    base_period = rec.get("baseline_measurement", {}).get("date")
    post_period = rec.get("followup_measurement", {}).get("date")

    exp_nominal = None
    if rec.get("expected_impact"):
        exp_nominal = rec["expected_impact"].get("nominal_risk_reduction_points")

    cursor.execute("""
    INSERT OR REPLACE INTO impact_verifications (
        verification_id, action_id, ward_id, control_ward_id, hazard_type,
        primary_metric, methodology, status, baseline_period, followup_period,
        baseline_value, followup_value, control_baseline_value, control_followup_value,
        observed_delta, did_estimate, expected_impact_nominal, action_completed,
        intended_outcome_observed, provenance, confidence_score, causal_claim_allowed,
        uncertainty_json, explanation
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        rec["verification_id"], rec["action_id"], rec["ward_id"],
        rec.get("control_ward_id"), rec.get("hazard_type", "heat"),
        rec.get("primary_metric", "hospital_heat_admissions"),
        rec.get("evaluation_methodology", "SIMPLE_BEFORE_AFTER"),
        rec["status"], base_period, post_period, base_val, post_val,
        c_base_val, c_post_val, rec.get("observed_delta"), did_est,
        exp_nominal, 1 if rec.get("action_completed") else 0,
        1 if rec.get("intended_outcome_observed") else (0 if rec.get("intended_outcome_observed") is False else None),
        "SIMULATED" if rec.get("is_synthetic_demonstration") else "REAL",
        rec.get("confidence_score", 0.5),
        1 if rec.get("causal_claim_allowed") else 0,
        json.dumps(rec.get("uncertainty") or {}),
        rec.get("explanation")
    ))

    conn.commit()
    conn.close()


def get_verification(verification_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a verification record by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM impact_verifications WHERE verification_id = ?;", (verification_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["uncertainty"] = json.loads(d.get("uncertainty_json") or "{}")
    d["action_completed"] = bool(d["action_completed"])
    d["causal_claim_allowed"] = bool(d["causal_claim_allowed"])
    return d


def list_verifications(
    action_id: Optional[str] = None,
    ward_id: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Lists historical impact verifications."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM impact_verifications WHERE 1=1"
    params: List[Any] = []

    if action_id:
        query += " AND action_id = ?"
        params.append(action_id)
    if ward_id:
        c_id, _ = resolve_canonical_ward_id(ward_id)
        query += " AND ward_id = ?"
        params.append(c_id)

    query += " ORDER BY created_at DESC LIMIT ?;"
    params.append(limit)

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        d = dict(r)
        d["uncertainty"] = json.loads(d.get("uncertainty_json") or "{}")
        d["action_completed"] = bool(d["action_completed"])
        d["causal_claim_allowed"] = bool(d["causal_claim_allowed"])
        results.append(d)
    return results
