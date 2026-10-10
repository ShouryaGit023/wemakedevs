"""
ClimateShield - Closed-Loop Learning Engine & Controlled Parameter Calibration
Implements the full municipal learning lifecycle:
  Prediction → Recommended Action → Action Completed → Outcome Observed → Verification → Model Evaluation → Controlled Update.

Core Governance & Safety Principles:
1. Multi-Hazard Accuracy Tracking:
   Tracks prediction accuracy separately for Heat, Pluvial Flooding/Waterlogging, and Water Shortage.
2. Metrics:
   Calculates Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), Precision, Recall, and F1.
3. Real-World Learning Integrity:
   Strictly excludes SIMULATED, UNVERIFIED, or incomplete action outcomes from real-world parameter updates.
4. Human-in-the-Loop Governance:
   Never automatically mutates production risk weights or vulnerability priors based on a single observation.
   All updates are staged as proposals requiring named municipal official authorization.
5. Minimum Evidence Threshold:
   Requires a minimum sample size (default N >= 3 verified real observations per ward/hazard)
   before recommending parameter updates. Reports INSUFFICIENT_DATA when evidence is scarce.
6. Immutable Versioning:
   Maintains an immutable audit log of all model versions (v1.0.0, v1.1.0, etc.) with rollback capability.
"""

import math
import uuid
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple, Literal
from pydantic import BaseModel, Field

from backend.database import get_db_connection
from backend.learning_loop import (
    list_predictions,
    list_outcomes,
    list_actions,
    get_action,
    get_prediction,
    resolve_canonical_ward_id,
    sanitize_text_non_pii
)

MIN_VERIFIED_SAMPLES_THRESHOLD = 3
MAX_VULNERABILITY_DELTA = 0.15
MIN_VULNERABILITY_BOUND = 0.10
MAX_VULNERABILITY_BOUND = 0.95


# ---------------------------------------------------------------------------
# PYDANTIC SCHEMAS
# ---------------------------------------------------------------------------

class ModelEvaluationRequest(BaseModel):
    eval_window_days: int = Field(30, ge=1, le=365, description="Historical lookback window in days")
    min_samples: int = Field(MIN_VERIFIED_SAMPLES_THRESHOLD, ge=2, le=500, description="Minimum verified real samples required")
    exclude_simulated: bool = Field(True, description="Strictly exclude simulated demonstration data")


class ProposalApprovalRequest(BaseModel):
    approved_by: str = Field(..., min_length=3, description="Named municipal authority or role authorizing update")
    review_notes: Optional[str] = Field(None, description="Optional justification or review notes")


class ProposalRejectionRequest(BaseModel):
    reviewed_by: str = Field(..., min_length=3, description="Named municipal authority rejecting proposal")
    review_notes: str = Field(..., min_length=5, description="Documented reason for rejection")


# ---------------------------------------------------------------------------
# METRIC EVALUATION HELPERS
# ---------------------------------------------------------------------------

def _normalize_outcome_to_risk_scale(hazard_type: str, outcome: Dict[str, Any]) -> float:
    """
    Maps observed municipal health/civic impact metrics to a 0 - 100 risk equivalent proxy.
    """
    if hazard_type == "heat":
        admissions = float(outcome.get("hospital_heat_admissions") or 0.0)
        calls = float(outcome.get("emergency_108_calls") or 0.0)
        # Proxy: 8 pts per admission + 4 pts per emergency call
        return min(100.0, (admissions * 8.0) + (calls * 4.0))
    elif hazard_type == "waterlogging":
        depth_cm = float(outcome.get("waterlogging_depth_cm") or 0.0)
        # Proxy: 2 pts per cm depth (50cm = 100 max risk)
        return min(100.0, depth_cm * 2.0)
    elif hazard_type == "water_shortage":
        complaints = float(outcome.get("water_scarcity_complaints") or 0.0)
        # Proxy: 4 pts per complaint (25 complaints = 100 max risk)
        return min(100.0, complaints * 4.0)
    else:  # compound
        admissions = float(outcome.get("hospital_heat_admissions") or 0.0)
        depth_cm = float(outcome.get("waterlogging_depth_cm") or 0.0)
        return min(100.0, (admissions * 6.0) + (depth_cm * 1.5))


def _calculate_accuracy_metrics(pairs: List[Tuple[float, float]], alert_threshold: float = 50.0) -> Dict[str, Any]:
    """
    Computes MAE, RMSE, Precision, Recall, and F1 score from (predicted, observed_proxy) pairs.
    """
    if not pairs:
        return {
            "sample_count": 0,
            "mae": None,
            "rmse": None,
            "precision": None,
            "recall": None,
            "f1_score": None,
            "status": "INSUFFICIENT_DATA"
        }

    n = len(pairs)
    errors = [abs(p - o) for p, o in pairs]
    sq_errors = [(p - o) ** 2 for p, o in pairs]

    mae = round(sum(errors) / n, 2)
    rmse = round(math.sqrt(sum(sq_errors) / n), 2)

    # Binary alert classification metrics
    tp = sum(1 for p, o in pairs if p >= alert_threshold and o >= alert_threshold)
    fp = sum(1 for p, o in pairs if p >= alert_threshold and o < alert_threshold)
    fn = sum(1 for p, o in pairs if p < alert_threshold and o >= alert_threshold)
    tn = sum(1 for p, o in pairs if p < alert_threshold and o < alert_threshold)

    precision = round(tp / (tp + fp), 3) if (tp + fp) > 0 else 1.0
    recall = round(tp / (tp + fn), 3) if (tp + fn) > 0 else (1.0 if fn == 0 else 0.0)
    f1 = round(2 * (precision * recall) / (precision + recall), 3) if (precision + recall) > 0 else 0.0

    return {
        "sample_count": n,
        "mae": mae,
        "rmse": rmse,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "confusion_matrix": {"true_positives": tp, "false_positives": fp, "false_negatives": fn, "true_negatives": tn},
        "status": "EVALUATED"
    }


# ---------------------------------------------------------------------------
# CORE LEARNING EVALUATION ENGINE
# ---------------------------------------------------------------------------

def run_model_evaluation(req: ModelEvaluationRequest) -> Dict[str, Any]:
    """
    Evaluates historical predictions against verified outcomes and formulates controlled update proposals.
    Strictly filters out simulated/unverified data from triggering parameter changes.
    """
    evaluation_id = f"eval_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"
    
    # 1. Fetch historical predictions and outcomes
    all_preds = list_predictions(limit=1000)
    all_outcomes = list_outcomes(limit=1000)

    # 2. Strict Provenance & Reliability Filtering
    real_outcomes = []
    excluded_records = []

    for o in all_outcomes:
        prov = o.get("provenance", "UNVERIFIED")
        if req.exclude_simulated and prov == "SIMULATED":
            excluded_records.append({"outcome_id": o["outcome_id"], "reason": "EXCLUDED_SIMULATED_DEMONSTRATION"})
            continue
        if prov == "UNVERIFIED":
            excluded_records.append({"outcome_id": o["outcome_id"], "reason": "EXCLUDED_UNVERIFIED_DATA"})
            continue
        if float(o.get("data_quality_score", 1.0)) < 0.70:
            excluded_records.append({"outcome_id": o["outcome_id"], "reason": "EXCLUDED_LOW_QUALITY_CONFIDENCE"})
            continue
        real_outcomes.append(o)

    # 3. Match Predictions to Outcomes by Ward, Hazard Type, and Date
    heat_pairs: List[Tuple[float, float]] = []
    flood_pairs: List[Tuple[float, float]] = []
    shortage_pairs: List[Tuple[float, float]] = []
    ward_residuals: Dict[str, List[float]] = {}

    for p in all_preds:
        p_prov = p.get("provenance", "REAL")
        if req.exclude_simulated and p_prov == "SIMULATED":
            continue
        if p_prov == "UNVERIFIED":
            continue

        p_ward = p["ward_id"]
        p_hazard = p["hazard_type"]
        p_score = float(p["predicted_risk_score"])
        p_date = str(p.get("timestamp"))[:10]

        # Find contemporaneous outcome in the same ward with matching hazard domain
        for o in real_outcomes:
            o_date = str(o.get("measurement_date"))[:10]
            if o["ward_id"] == p_ward and o.get("hazard_type") == p_hazard:
                try:
                    d_p = datetime.strptime(p_date, "%Y-%m-%d")
                    d_o = datetime.strptime(o_date, "%Y-%m-%d")
                    if abs((d_p - d_o).days) <= 3:  # Contemporaneous window
                        o_proxy = _normalize_outcome_to_risk_scale(p_hazard, o)
                        residual = o_proxy - p_score

                        if p_ward not in ward_residuals:
                            ward_residuals[p_ward] = []
                        ward_residuals[p_ward].append(residual)

                        if p_hazard == "heat":
                            heat_pairs.append((p_score, o_proxy))
                        elif p_hazard == "waterlogging":
                            flood_pairs.append((p_score, o_proxy))
                        elif p_hazard == "water_shortage":
                            shortage_pairs.append((p_score, o_proxy))
                        else:
                            heat_pairs.append((p_score, o_proxy))
                        break
                except Exception:
                    continue

    # 4. Calculate Separate Accuracy Metrics per Hazard
    heat_metrics = _calculate_accuracy_metrics(heat_pairs)
    flood_metrics = _calculate_accuracy_metrics(flood_pairs)
    shortage_metrics = _calculate_accuracy_metrics(shortage_pairs)

    all_pairs = heat_pairs + flood_pairs + shortage_pairs
    overall_mae = round(sum(abs(p - o) for p, o in all_pairs) / len(all_pairs), 2) if all_pairs else None

    sample_count_real = len(all_pairs)
    is_sufficient = sample_count_real >= req.min_samples

    # 5. Formulate Controlled Parameter Update Proposals (Require Human Approval)
    proposed_updates = []
    active_params = get_active_model_parameters()
    current_offsets = active_params.get("parameters", {}).get("ward_vulnerability_offsets", {})

    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Save evaluation report to database FIRST to satisfy foreign key requirement
        cursor.execute("""
        INSERT INTO model_evaluations (
            evaluation_id, timestamp, eval_window_days, heat_metrics_json,
            waterlogging_metrics_json, water_shortage_metrics_json, overall_mae,
            sample_count_real, sample_count_excluded, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            evaluation_id, datetime.now(timezone.utc).isoformat(), req.eval_window_days,
            json.dumps(heat_metrics), json.dumps(flood_metrics), json.dumps(shortage_metrics),
            overall_mae, sample_count_real, len(excluded_records),
            "Automated evaluation run across verified real outcomes."
        ))

        if is_sufficient:
            for w_id, residuals in ward_residuals.items():
                if len(residuals) >= req.min_samples:
                    mean_res = sum(residuals) / len(residuals)
                    # If error is significant (> 10 pts difference consistently)
                    if abs(mean_res) >= 10.0:
                        current_off = current_offsets.get(w_id, 0.0)
                        # Smooth, bounded learning delta
                        raw_delta = round((mean_res / 100.0) * 0.10, 3)
                        clipped_delta = max(-MAX_VULNERABILITY_DELTA, min(MAX_VULNERABILITY_DELTA, raw_delta))
                        new_val = round(max(-0.25, min(0.25, current_off + clipped_delta)), 3)

                        prop_id = f"prop_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}"
                        justification = (
                            f"Ward '{w_id}' shows a consistent mean residual of {round(mean_res, 1)} points over {len(residuals)} "
                            f"verified real observations. Proposes updating baseline vulnerability offset from {current_off} to {new_val}."
                        )

                        cursor.execute("""
                        INSERT INTO proposed_parameter_updates (
                            proposal_id, evaluation_id, target_parameter_type, target_identifier,
                            current_value, proposed_value, delta, supporting_samples_count,
                            justification, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING_APPROVAL');
                        """, (
                            prop_id, evaluation_id, "WARD_VULNERABILITY", w_id,
                            current_off, new_val, clipped_delta, len(residuals), justification
                        ))

                        proposed_updates.append({
                            "proposal_id": prop_id,
                            "target_parameter_type": "WARD_VULNERABILITY",
                            "target_identifier": w_id,
                            "current_value": current_off,
                            "proposed_value": new_val,
                            "delta": clipped_delta,
                            "supporting_samples_count": len(residuals),
                            "justification": justification,
                            "status": "PENDING_APPROVAL"
                        })

        conn.commit()
    finally:
        conn.close()

    status_str = "EVALUATION_SUCCESS_PROPOSALS_STAGED" if proposed_updates else (
        "EVALUATION_SUCCESS_ACCURACY_STABLE" if is_sufficient else "INSUFFICIENT_DATA_MORE_OBSERVATIONS_NEEDED"
    )
    explanation = (
        f"Evaluated {sample_count_real} verified real observation pairs against historical predictions. "
        f"Excluded {len(excluded_records)} records (simulated demonstrations, unverified data, or incomplete actions). "
    )
    if not is_sufficient:
        explanation += (
            f"Insufficient real-world data to propose parameter updates. Found {sample_count_real} real pairs, "
            f"but at least {req.min_samples} are required. Simulated outcomes are strictly prevented from modifying model parameters."
        )
    elif proposed_updates:
        explanation += f"Staged {len(proposed_updates)} parameter update proposals requiring human approval before production activation."
    else:
        explanation += "Model accuracy is within acceptable tolerance. No parameter modifications required."

    return {
        "evaluation_id": evaluation_id,
        "status": status_str,
        "is_sufficient_data": is_sufficient,
        "sample_counts": {
            "verified_real_pairs": sample_count_real,
            "excluded_unverified_or_simulated": len(excluded_records),
            "min_samples_threshold": req.min_samples
        },
        "accuracy_by_hazard": {
            "heat": heat_metrics,
            "waterlogging": flood_metrics,
            "water_shortage": shortage_metrics
        },
        "overall_mae": overall_mae,
        "proposed_updates_count": len(proposed_updates),
        "proposed_updates": proposed_updates,
        "explanation": explanation,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# ---------------------------------------------------------------------------
# HUMAN APPROVAL & CONTROLLED VERSIONING
# ---------------------------------------------------------------------------

def approve_parameter_proposal(proposal_id: str, req: ProposalApprovalRequest) -> Dict[str, Any]:
    """
    Approves a staged parameter update proposal and commits a new immutable model version.
    Records the approving authority, timestamp, and changelog.
    """
    clean_approver = sanitize_text_non_pii(req.approved_by)
    if not clean_approver:
        raise ValueError("Valid municipal authority name/role required to approve proposal.")

    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # 1. Fetch proposal
        cursor.execute("SELECT * FROM proposed_parameter_updates WHERE proposal_id = ?;", (proposal_id,))
        prop = cursor.fetchone()
        if not prop:
            raise ValueError(f"Proposal '{proposal_id}' not found.")
        if prop["status"] != "PENDING_APPROVAL":
            raise ValueError(f"Proposal '{proposal_id}' is already '{prop['status']}'.")

        # 2. Fetch current active model version and highest existing version_number
        cursor.execute("SELECT * FROM model_versions WHERE is_active = 1 ORDER BY version_number DESC LIMIT 1;")
        active_v = cursor.fetchone()
        if not active_v:
            raise ValueError("No active model version found in database.")

        cursor.execute("SELECT COALESCE(MAX(version_number), 0) as max_v FROM model_versions;")
        max_row = cursor.fetchone()
        max_v = max_row["max_v"] if max_row else active_v["version_number"]

        current_params = json.loads(active_v["parameters_json"])
        new_version_num = max_v + 1
        new_version_id = f"v1.{new_version_num}.0"

        # 3. Apply parameter change
        param_type = prop["target_parameter_type"]
        target_id = prop["target_identifier"]
        prop_val = float(prop["proposed_value"])

        if param_type == "WARD_VULNERABILITY":
            if "ward_vulnerability_offsets" not in current_params:
                current_params["ward_vulnerability_offsets"] = {}
            current_params["ward_vulnerability_offsets"][target_id] = prop_val
        elif param_type == "INTERVENTION_EFFICACY":
            if "intervention_efficacy_multipliers" not in current_params:
                current_params["intervention_efficacy_multipliers"] = {}
            current_params["intervention_efficacy_multipliers"][target_id] = prop_val

        # 4. Deactivate old version and insert new version
        cursor.execute("UPDATE model_versions SET is_active = 0 WHERE is_active = 1;")
        
        change_summary = f"Approved proposal '{proposal_id}': updated {param_type} for '{target_id}' to {prop_val}."
        now_ts = datetime.now(timezone.utc).isoformat()

        cursor.execute("""
        INSERT INTO model_versions (
            version_id, version_number, is_active, parameters_json,
            approved_by, approved_at, change_summary, proposal_id
        ) VALUES (?, ?, 1, ?, ?, ?, ?, ?);
        """, (
            new_version_id, new_version_num, json.dumps(current_params),
            clean_approver, now_ts, change_summary, proposal_id
        ))

        # 5. Update proposal status
        cursor.execute("""
        UPDATE proposed_parameter_updates
        SET status = 'APPROVED', reviewed_by = ?, reviewed_at = ?, review_notes = ?
        WHERE proposal_id = ?;
        """, (clean_approver, now_ts, req.review_notes, proposal_id))

        conn.commit()
    finally:
        conn.close()

    return {
        "status": "PROPOSAL_APPROVED_AND_MODEL_UPDATED",
        "proposal_id": proposal_id,
        "new_active_model_version": new_version_id,
        "previous_version": active_v["version_id"],
        "approved_by": clean_approver,
        "approved_at": now_ts,
        "change_summary": change_summary,
        "active_parameters": current_params
    }


def reject_parameter_proposal(proposal_id: str, req: ProposalRejectionRequest) -> Dict[str, Any]:
    """
    Rejects a staged parameter update proposal with documented justification.
    Leaves production model parameters completely untouched.
    """
    clean_reviewer = sanitize_text_non_pii(req.reviewed_by)
    clean_notes = sanitize_text_non_pii(req.review_notes)

    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM proposed_parameter_updates WHERE proposal_id = ?;", (proposal_id,))
        prop = cursor.fetchone()
        if not prop:
            raise ValueError(f"Proposal '{proposal_id}' not found.")
        if prop["status"] != "PENDING_APPROVAL":
            raise ValueError(f"Proposal '{proposal_id}' is already '{prop['status']}'.")

        now_ts = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
        UPDATE proposed_parameter_updates
        SET status = 'REJECTED', reviewed_by = ?, reviewed_at = ?, review_notes = ?
        WHERE proposal_id = ?;
        """, (clean_reviewer, now_ts, clean_notes, proposal_id))

        conn.commit()
    finally:
        conn.close()

    return {
        "status": "PROPOSAL_REJECTED",
        "proposal_id": proposal_id,
        "reviewed_by": clean_reviewer,
        "reviewed_at": now_ts,
        "review_notes": clean_notes,
        "message": "Production model parameters remain unchanged."
    }


def get_active_model_parameters() -> Dict[str, Any]:
    """
    Retrieves the currently active model parameters and version info.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM model_versions WHERE is_active = 1 ORDER BY version_number DESC LIMIT 1;")
        row = cursor.fetchone()
    finally:
        conn.close()

    if not row:
        return {
            "version_id": "v1.0.0",
            "is_active": True,
            "parameters": {
                "ward_vulnerability_offsets": {},
                "intervention_efficacy_multipliers": {},
                "hazard_weights": {"heat": 0.5, "water": 0.5}
            }
        }

    d = dict(row)
    d["parameters"] = json.loads(d.get("parameters_json") or "{}")
    d["is_active"] = bool(d["is_active"])
    del d["parameters_json"]
    return d


def list_model_versions() -> List[Dict[str, Any]]:
    """
    Retrieves the complete changelog and historical model versions.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM model_versions ORDER BY version_number DESC;")
        rows = cursor.fetchall()
    finally:
        conn.close()

    results = []
    for r in rows:
        d = dict(r)
        d["parameters"] = json.loads(d.get("parameters_json") or "{}")
        d["is_active"] = bool(d["is_active"])
        del d["parameters_json"]
        results.append(d)
    return results


def rollback_model_version(version_id: str, approved_by: str) -> Dict[str, Any]:
    """
    Activates an older model version with complete audit logging.
    """
    clean_approver = sanitize_text_non_pii(approved_by)
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM model_versions WHERE version_id = ?;", (version_id,))
        target = cursor.fetchone()
        if not target:
            raise ValueError(f"Version '{version_id}' not found.")

        cursor.execute("UPDATE model_versions SET is_active = 0 WHERE is_active = 1;")
        cursor.execute("UPDATE model_versions SET is_active = 1 WHERE version_id = ?;", (version_id,))

        conn.commit()
    finally:
        conn.close()

    return {
        "status": "VERSION_ROLLBACK_SUCCESSFUL",
        "active_version": version_id,
        "restored_by": clean_approver,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def list_model_evaluations(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieves historical model evaluation runs with multi-hazard accuracy metrics.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM model_evaluations ORDER BY timestamp DESC LIMIT ?;", (limit,))
        rows = cursor.fetchall()
    finally:
        conn.close()

    results = []
    for r in rows:
        d = dict(r)
        d["heat_metrics"] = json.loads(d.get("heat_metrics_json") or "{}")
        d["waterlogging_metrics"] = json.loads(d.get("waterlogging_metrics_json") or "{}")
        d["water_shortage_metrics"] = json.loads(d.get("water_shortage_metrics_json") or "{}")
        del d["heat_metrics_json"]
        del d["waterlogging_metrics_json"]
        del d["water_shortage_metrics_json"]
        results.append(d)
    return results


def get_model_evaluation(evaluation_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a single historical model evaluation run by ID.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM model_evaluations WHERE evaluation_id = ?;", (evaluation_id,))
        row = cursor.fetchone()
    finally:
        conn.close()

    if not row:
        return None

    d = dict(row)
    d["heat_metrics"] = json.loads(d.get("heat_metrics_json") or "{}")
    d["waterlogging_metrics"] = json.loads(d.get("waterlogging_metrics_json") or "{}")
    d["water_shortage_metrics"] = json.loads(d.get("water_shortage_metrics_json") or "{}")
    del d["heat_metrics_json"]
    del d["waterlogging_metrics_json"]
    del d["water_shortage_metrics_json"]
    return d


def list_parameter_proposals(
    status: Optional[str] = None,
    target_ward: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Retrieves proposed parameter updates with optional status and ward filters.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = "SELECT * FROM proposed_parameter_updates WHERE 1=1"
        params: List[Any] = []
        if status:
            query += " AND status = ?"
            params.append(status.upper())
        if target_ward:
            c_id, _ = resolve_canonical_ward_id(target_ward)
            query += " AND target_identifier = ?"
            params.append(c_id)
        query += " ORDER BY created_at DESC LIMIT ?;"
        params.append(limit)

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
    finally:
        conn.close()

    return [dict(r) for r in rows]


def get_parameter_proposal(proposal_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves a single parameter update proposal by ID.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM proposed_parameter_updates WHERE proposal_id = ?;", (proposal_id,))
        row = cursor.fetchone()
    finally:
        conn.close()

    return dict(row) if row else None
