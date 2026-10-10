"""
ClimateShield - Persistent Baseline Database Engine (SQLite)
Provides persistent storage for Ward profiles, Interventions catalog,
Municipal outcome tracking (mortality, hospital admissions, 108 calls),
and Optimization audit history.
"""

import sqlite3
import os
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "climateshield_baseline.db")


def get_db_connection() -> sqlite3.Connection:
    """Returns a connection to the SQLite baseline database with row dict factory, WAL mode, and foreign keys enabled."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Initializes tables in the baseline database."""
    conn = get_db_connection()
    conn.execute("PRAGMA journal_mode = WAL;")
    cursor = conn.cursor()

    # 1. Wards Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS wards (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        slum_density REAL NOT NULL,
        outdoor_labor_ratio REAL NOT NULL,
        elderly_ratio REAL NOT NULL,
        baseline_heat_risk REAL NOT NULL,
        population INTEGER DEFAULT 100000,
        area_sq_km REAL DEFAULT 5.0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Interventions Catalog
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interventions (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        cost_inr REAL NOT NULL,
        crew_req INTEGER NOT NULL,
        water_req_l REAL NOT NULL,
        base_risk_reduction REAL NOT NULL,
        max_per_ward INTEGER NOT NULL,
        vulnerable_impact_json TEXT NOT NULL
    );
    """)

    # 3. Ground-truth Municipal Outcome Records (Data-Sharing Agreements)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS outcome_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_date TEXT NOT NULL,
        ward_id TEXT NOT NULL,
        hospital_heat_admissions INTEGER DEFAULT 0,
        mortality_count INTEGER DEFAULT 0,
        emergency_108_calls INTEGER DEFAULT 0,
        water_scarcity_complaints INTEGER DEFAULT 0,
        reported_by TEXT DEFAULT 'AMC_HEALTH_SURVEILLANCE',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (ward_id) REFERENCES wards (id)
    );
    """)

    # 4. Optimization Audit Runs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS optimization_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        budget_inr REAL NOT NULL,
        crew_members INTEGER NOT NULL,
        water_cap_l REAL NOT NULL,
        equity_slider REAL NOT NULL,
        total_cost_inr REAL NOT NULL,
        total_risk_reduction REAL NOT NULL,
        allocation_summary_json TEXT NOT NULL
    );
    """)

    # 5. Learning Loop: Historical Risk Predictions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        prediction_id TEXT PRIMARY KEY,
        ward_id TEXT NOT NULL,
        ward_name TEXT,
        timestamp TEXT NOT NULL,
        hazard_type TEXT NOT NULL,
        predicted_risk_score REAL NOT NULL,
        risk_category TEXT NOT NULL,
        data_source TEXT NOT NULL,
        provenance TEXT NOT NULL DEFAULT 'ESTIMATED',
        details_json TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (ward_id) REFERENCES wards (id)
    );
    """)

    # 6. Learning Loop: Recommended Interventions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recommendations (
        recommendation_id TEXT PRIMARY KEY,
        prediction_id TEXT NOT NULL,
        ward_id TEXT NOT NULL,
        intervention_type TEXT NOT NULL,
        priority_score REAL,
        estimated_cost_inr REAL,
        expected_impact_min REAL,
        expected_impact_expected REAL,
        expected_impact_max REAL,
        required_crew INTEGER,
        required_water_l REAL,
        assumptions_json TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'PROPOSED',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (prediction_id) REFERENCES predictions (prediction_id),
        FOREIGN KEY (ward_id) REFERENCES wards (id)
    );
    """)

    # 7. Learning Loop: Executed Field Actions (Approved and carried out actions)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS executed_actions (
        action_id TEXT PRIMARY KEY,
        recommendation_id TEXT,
        prediction_id TEXT,
        ward_id TEXT NOT NULL,
        intervention_type TEXT NOT NULL,
        approval_status TEXT NOT NULL,
        approved_by TEXT NOT NULL,
        approved_at TEXT,
        execution_status TEXT NOT NULL DEFAULT 'SCHEDULED',
        started_at TEXT,
        completed_at TEXT,
        actual_cost_inr REAL,
        actual_crew_used INTEGER,
        actual_water_used_l REAL,
        failure_reason TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (recommendation_id) REFERENCES recommendations (recommendation_id),
        FOREIGN KEY (prediction_id) REFERENCES predictions (prediction_id),
        FOREIGN KEY (ward_id) REFERENCES wards (id)
    );
    """)

    # 8. Learning Loop: Verified Municipal Outcomes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS verified_outcomes (
        outcome_id TEXT PRIMARY KEY,
        ward_id TEXT NOT NULL,
        prediction_id TEXT,
        action_id TEXT,
        measurement_date TEXT NOT NULL,
        measurement_window_hours INTEGER DEFAULT 24,
        hazard_type TEXT NOT NULL,
        hospital_heat_admissions INTEGER DEFAULT 0,
        mortality_count INTEGER DEFAULT 0,
        emergency_108_calls INTEGER DEFAULT 0,
        water_scarcity_complaints INTEGER DEFAULT 0,
        waterlogging_depth_cm REAL,
        data_source TEXT NOT NULL,
        provenance TEXT NOT NULL DEFAULT 'REAL',
        data_quality_score REAL DEFAULT 1.0,
        verification_notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (prediction_id) REFERENCES predictions (prediction_id),
        FOREIGN KEY (action_id) REFERENCES executed_actions (action_id),
        FOREIGN KEY (ward_id) REFERENCES wards (id)
    );
    """)

    # 9. Learning Loop: Impact Verifications (Before-After & Difference-in-Differences)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS impact_verifications (
        verification_id TEXT PRIMARY KEY,
        action_id TEXT NOT NULL,
        ward_id TEXT NOT NULL,
        control_ward_id TEXT,
        hazard_type TEXT NOT NULL,
        primary_metric TEXT NOT NULL,
        methodology TEXT NOT NULL,
        status TEXT NOT NULL,
        baseline_period TEXT,
        followup_period TEXT,
        baseline_value REAL,
        followup_value REAL,
        control_baseline_value REAL,
        control_followup_value REAL,
        observed_delta REAL,
        did_estimate REAL,
        expected_impact_nominal REAL,
        action_completed INTEGER NOT NULL,
        intended_outcome_observed INTEGER,
        provenance TEXT NOT NULL,
        confidence_score REAL NOT NULL,
        causal_claim_allowed INTEGER NOT NULL DEFAULT 0,
        uncertainty_json TEXT,
        explanation TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (action_id) REFERENCES executed_actions (action_id),
        FOREIGN KEY (ward_id) REFERENCES wards (id)
    );
    """)

    # 10. Learning Loop: Model Evaluations & Accuracy Tracking
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS model_evaluations (
        evaluation_id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        eval_window_days INTEGER DEFAULT 30,
        heat_metrics_json TEXT NOT NULL,
        waterlogging_metrics_json TEXT NOT NULL,
        water_shortage_metrics_json TEXT NOT NULL,
        overall_mae REAL,
        sample_count_real INTEGER NOT NULL,
        sample_count_excluded INTEGER NOT NULL,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 11. Learning Loop: Proposed Parameter Updates (Require Human Approval)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS proposed_parameter_updates (
        proposal_id TEXT PRIMARY KEY,
        evaluation_id TEXT NOT NULL,
        target_parameter_type TEXT NOT NULL,
        target_identifier TEXT NOT NULL,
        current_value REAL NOT NULL,
        proposed_value REAL NOT NULL,
        delta REAL NOT NULL,
        supporting_samples_count INTEGER NOT NULL,
        justification TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'PENDING_APPROVAL',
        reviewed_by TEXT,
        reviewed_at TEXT,
        review_notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (evaluation_id) REFERENCES model_evaluations (evaluation_id)
    );
    """)

    # 12. Learning Loop: Immutable Model Versions & Parameter Audit Trail
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS model_versions (
        version_id TEXT PRIMARY KEY,
        version_number INTEGER NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 0,
        parameters_json TEXT NOT NULL,
        approved_by TEXT NOT NULL,
        approved_at TEXT NOT NULL,
        change_summary TEXT NOT NULL,
        proposal_id TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 13. Verified Impact Assessments
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS impact_assessments (
        assessment_id TEXT PRIMARY KEY,
        intervention_id TEXT NOT NULL,
        ward_id TEXT NOT NULL,
        intervention_type TEXT NOT NULL,
        execution_status TEXT NOT NULL DEFAULT 'COMPLETED',
        verification_status TEXT NOT NULL,
        provenance_mode TEXT NOT NULL,
        is_synthetic INTEGER NOT NULL DEFAULT 0,
        baseline_period_json TEXT NOT NULL,
        follow_up_period_json TEXT NOT NULL,
        indicators_json TEXT NOT NULL,
        calculated_changes_json TEXT NOT NULL,
        data_quality_warnings_json TEXT NOT NULL,
        attribution_disclaimer TEXT NOT NULL,
        summary_json TEXT NOT NULL,
        version INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # 14. Impact Assessment Audit History
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS impact_assessment_history (
        history_id INTEGER PRIMARY KEY AUTOINCREMENT,
        assessment_id TEXT NOT NULL,
        version INTEGER NOT NULL,
        snapshot_json TEXT NOT NULL,
        archived_at TEXT NOT NULL,
        change_reason TEXT,
        FOREIGN KEY (assessment_id) REFERENCES impact_assessments (assessment_id)
    );
    """)

    # 15. Action Centre Operations Records (Persistent shared state across Web and Telegram)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS action_centre_records (
        action_id TEXT PRIMARY KEY,
        ward_id TEXT NOT NULL,
        ward_name TEXT NOT NULL,
        action_type TEXT NOT NULL,
        priority TEXT NOT NULL,
        reason TEXT NOT NULL,
        required_resources_json TEXT,
        related_hazard TEXT,
        risk_score REAL,
        status TEXT NOT NULL,
        status_history_json TEXT NOT NULL,
        has_active_blocker INTEGER DEFAULT 0,
        last_blocker_reason TEXT,
        source TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # Indices for relational query performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_ward ON predictions (ward_id, timestamp);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_recommendations_pred ON recommendations (prediction_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_actions_rec ON executed_actions (recommendation_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_actions_pred ON executed_actions (prediction_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_pred ON verified_outcomes (prediction_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_action ON verified_outcomes (action_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_ward_date ON verified_outcomes (ward_id, measurement_date);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_verifications_action ON impact_verifications (action_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_verifications_ward ON impact_verifications (ward_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_evaluations_time ON model_evaluations (timestamp);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_proposals_status ON proposed_parameter_updates (status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_versions_active ON model_versions (is_active);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_impact_assessments_ward ON impact_assessments (ward_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_impact_assessments_interv ON impact_assessments (intervention_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_impact_history_assessment ON impact_assessment_history (assessment_id);")

    conn.commit()
    conn.close()


def seed_baseline_data() -> None:
    """Seeds baseline wards, interventions catalog, and sample historical outcomes."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Seed all 48 Wards from GeoJSON if available, with core 10 having calibrated vulnerability
    cursor.execute("SELECT COUNT(*) as count FROM wards;")
    count = cursor.fetchone()["count"]
    if count < 48:
        # Seed core priority wards
        ahmedabad_wards = [
            ("W1", "Danilimda", 0.85, 0.75, 0.20, 0.92, 125000, 6.2),
            ("W2", "Behrampura", 0.80, 0.70, 0.18, 0.88, 110000, 5.4),
            ("W3", "Asarwa", 0.65, 0.60, 0.25, 0.78, 95000, 4.8),
            ("W4", "Bapunagar", 0.75, 0.65, 0.22, 0.84, 130000, 5.9),
            ("W5", "Khadia (Old City)", 0.40, 0.45, 0.35, 0.72, 85000, 3.2),
            ("W6", "Amraiwadi", 0.70, 0.68, 0.19, 0.81, 105000, 5.1),
            ("W7", "Vatva", 0.78, 0.72, 0.17, 0.86, 140000, 7.8),
            ("W8", "Sabarmati", 0.35, 0.35, 0.28, 0.55, 90000, 6.5),
            ("W9", "Maninagar", 0.30, 0.30, 0.30, 0.50, 115000, 5.0),
            ("W10", "Naroda", 0.60, 0.58, 0.21, 0.70, 100000, 6.8)
        ]
        cursor.executemany("""
        INSERT OR IGNORE INTO wards (id, name, slum_density, outdoor_labor_ratio, elderly_ratio, baseline_heat_risk, population, area_sq_km)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, ahmedabad_wards)

        # Seed remaining wards up to W48 from GeoJSON if present
        geojson_path = os.path.join(os.path.dirname(__file__), "data", "Ahmedabad_Wards.geojson")
        if os.path.exists(geojson_path):
            try:
                with open(geojson_path, "r", encoding="utf-8") as f:
                    geo = json.load(f)
                features = geo.get("features", [])
                for idx, feat in enumerate(features):
                    w_id = f"W{idx + 1}"
                    props = feat.get("properties", {})
                    name = props.get("Name", props.get("NAME", f"Ward {idx + 1}"))
                    cursor.execute("""
                    INSERT OR IGNORE INTO wards (id, name, slum_density, outdoor_labor_ratio, elderly_ratio, baseline_heat_risk, population, area_sq_km)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """, (w_id, name, 0.50, 0.50, 0.20, 0.60, 100000, 5.0))
            except Exception:
                pass

    # Check if interventions catalog already seeded
    cursor.execute("SELECT COUNT(*) as count FROM interventions;")
    if cursor.fetchone()["count"] == 0:
        interventions = [
            ("cooling_center", "Cooling Center Shelter", 50000, 4, 500, 85.0, 2, json.dumps({"slum_dwellers": 40, "outdoor_laborers": 20, "elderly_infants": 40})),
            ("hydration_kiosk", "Emergency Hydration Kiosk", 15000, 2, 1200, 45.0, 4, json.dumps({"slum_dwellers": 30, "outdoor_laborers": 60, "elderly_infants": 10})),
            ("shade_canopy", "Pop-up Bus Stop Shade Canopy", 25000, 3, 0, 35.0, 3, json.dumps({"slum_dwellers": 20, "outdoor_laborers": 70, "elderly_infants": 10})),
            ("cool_roof_coating", "Slum Cool Roof Painting", 35000, 5, 100, 65.0, 3, json.dumps({"slum_dwellers": 80, "outdoor_laborers": 0, "elderly_infants": 20})),
            ("water_tanker_dispatch", "Mobile Water Tanker Dispatch", 10000, 2, 5000, 50.0, 2, json.dumps({"slum_dwellers": 50, "outdoor_laborers": 30, "elderly_infants": 20}))
        ]
        cursor.executemany("""
        INSERT INTO interventions (id, name, cost_inr, crew_req, water_req_l, base_risk_reduction, max_per_ward, vulnerable_impact_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, interventions)

    # Check if sample historical outcome records seeded
    cursor.execute("SELECT COUNT(*) as count FROM outcome_records;")
    if cursor.fetchone()["count"] == 0:
        sample_outcomes = [
            ("2026-05-15", "W1", 14, 2, 8, 22, "AMC_HEALTH_SURVEILLANCE"),
            ("2026-05-15", "W2", 12, 1, 6, 18, "AMC_HEALTH_SURVEILLANCE"),
            ("2026-05-15", "W4", 10, 1, 5, 15, "AMC_HEALTH_SURVEILLANCE"),
            ("2026-05-15", "W7", 11, 2, 7, 20, "AMC_HEALTH_SURVEILLANCE"),
            ("2026-05-15", "W9", 2, 0, 1, 3, "AMC_HEALTH_SURVEILLANCE")
        ]
        cursor.executemany("""
        INSERT INTO outcome_records (record_date, ward_id, hospital_heat_admissions, mortality_count, emergency_108_calls, water_scarcity_complaints, reported_by)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """, sample_outcomes)

    # Check if initial baseline model version v1.0.0 is seeded
    cursor.execute("SELECT COUNT(*) as count FROM model_versions;")
    if cursor.fetchone()["count"] == 0:
        default_params = {
            "ward_vulnerability_offsets": {},
            "intervention_efficacy_multipliers": {
                "cooling_center": 1.0,
                "hydration_kiosk": 1.0,
                "shade_canopy": 1.0,
                "cool_roof_coating": 1.0,
                "heat_alert_outreach": 1.0,
                "drainage_inspection_clean": 1.0,
                "flood_barricade_warning": 1.0,
                "mobile_pumping": 1.0,
                "water_tanker_dispatch": 1.0,
                "piped_supply_priority": 1.0
            },
            "hazard_weights": {"heat": 0.50, "water": 0.50}
        }
        cursor.execute("""
        INSERT INTO model_versions (version_id, version_number, is_active, parameters_json, approved_by, approved_at, change_summary)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """, ("v1.0.0", 1, 1, json.dumps(default_params), "SYSTEM_INITIALIZATION", datetime.now(timezone.utc).isoformat(), "Initial baseline model version with uncalibrated prior parameters."))

    conn.commit()
    conn.close()


def get_all_wards() -> List[Dict[str, Any]]:
    """Returns all ward records as dictionaries."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM wards ORDER BY baseline_heat_risk DESC;")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_all_interventions() -> List[Dict[str, Any]]:
    """Returns the interventions catalog."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM interventions;")
    rows = []
    for r in cursor.fetchall():
        item = dict(r)
        item["vulnerable_impact"] = json.loads(item["vulnerable_impact_json"])
        del item["vulnerable_impact_json"]
        rows.append(item)
    conn.close()
    return rows


def insert_outcome_record(
    record_date: str,
    ward_id: str,
    hospital_admissions: int,
    mortality_count: int,
    emergency_108_calls: int,
    water_complaints: int,
    reported_by: str = "AMC_HEALTH_SURVEILLANCE"
) -> int:
    """Inserts a new ground-truth municipal outcome record."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO outcome_records (record_date, ward_id, hospital_heat_admissions, mortality_count, emergency_108_calls, water_scarcity_complaints, reported_by)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, (record_date, ward_id, hospital_admissions, mortality_count, emergency_108_calls, water_complaints, reported_by))
    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return record_id


class DuplicateAssessmentError(ValueError):
    """Raised when attempting to insert an assessment that already exists without explicit update."""
    pass


def _row_to_assessment_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Helper to convert a database row to an assessment dictionary with parsed JSON fields."""
    d = dict(row)
    d["is_synthetic"] = bool(d.get("is_synthetic", 0))
    for json_field, target_key in [
        ("baseline_period_json", "baseline_period"),
        ("follow_up_period_json", "follow_up_period"),
        ("indicators_json", "indicators"),
        ("calculated_changes_json", "calculated_changes"),
        ("data_quality_warnings_json", "data_quality_warnings"),
        ("summary_json", "summary"),
    ]:
        if json_field in d and d[json_field] is not None:
            try:
                d[target_key] = json.loads(d[json_field])
            except Exception:
                d[target_key] = {}
            del d[json_field]
    return d


def save_impact_assessment_record(
    record: Dict[str, Any],
    allow_update: bool = False,
    change_reason: Optional[str] = None
) -> Dict[str, Any]:
    """
    Saves an impact assessment to the baseline database.
    - Prevents accidental duplicates by checking assessment_id.
    - If assessment_id already exists and incoming payload is identical, returns existing record idempotently.
    - If assessment_id already exists and allow_update is False, raises DuplicateAssessmentError.
    - If allow_update is True, archives current version to impact_assessment_history and increments version.
    """
    assessment_id = record.get("assessment_id")
    if not assessment_id:
        raise ValueError("Cannot save assessment: 'assessment_id' is required.")

    now_iso = datetime.now(timezone.utc).isoformat()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if record already exists
    cursor.execute("SELECT * FROM impact_assessments WHERE assessment_id = ?;", (assessment_id,))
    existing_row = cursor.fetchone()

    # Prepare serialized JSON fields
    indicators_val = record.get("indicators", record.get("results_by_indicator", {}))
    calculated_changes_val = record.get("calculated_changes", {})
    if not calculated_changes_val and isinstance(indicators_val, dict):
        calculated_changes_val = {
            k: {
                "difference": v.get("difference"),
                "percentage_change": v.get("percentage_change"),
                "unit": v.get("unit"),
                "is_improvement": v.get("is_improvement")
            }
            for k, v in indicators_val.items() if isinstance(v, dict)
        }

    baseline_period_json = json.dumps(record.get("baseline_period", {}), sort_keys=True)
    follow_up_period_json = json.dumps(record.get("follow_up_period", {}), sort_keys=True)
    indicators_json = json.dumps(indicators_val, sort_keys=True)
    calculated_changes_json = json.dumps(calculated_changes_val, sort_keys=True)
    data_quality_warnings_json = json.dumps(record.get("data_quality_warnings", []), sort_keys=True)
    summary_json = json.dumps(record.get("summary", {}), sort_keys=True)
    attribution_disclaimer = record.get("attribution_disclaimer", "")
    provenance_mode = record.get("provenance_mode", "MEASURED")
    is_synthetic = 1 if record.get("is_synthetic", False) else 0
    execution_status = record.get("execution_status", "COMPLETED")
    verification_status = record.get("verification_status", "VERIFIED")
    intervention_id = record.get("intervention_id", "")
    ward_id = record.get("ward_id", "")
    intervention_type = record.get("intervention_type", "")

    if existing_row:
        existing_dict = _row_to_assessment_dict(existing_row)

        # Idempotency check: compare core payload
        is_identical = (
            existing_row["intervention_id"] == intervention_id and
            existing_row["ward_id"] == ward_id and
            existing_row["intervention_type"] == intervention_type and
            existing_row["indicators_json"] == indicators_json and
            existing_row["calculated_changes_json"] == calculated_changes_json and
            existing_row["execution_status"] == execution_status
        )

        if is_identical:
            conn.close()
            existing_dict["save_status"] = "IDEMPOTENT_UNCHANGED"
            return existing_dict

        if not allow_update:
            conn.close()
            raise DuplicateAssessmentError(
                f"Assessment ID '{assessment_id}' already exists in database. "
                "Silently overwriting historical records is forbidden. "
                "To update or re-evaluate, specify allow_update=True."
            )

        # Archive existing version to audit history
        current_version = existing_row["version"]
        snapshot_json = json.dumps(dict(existing_row))
        cursor.execute("""
        INSERT INTO impact_assessment_history (assessment_id, version, snapshot_json, archived_at, change_reason)
        VALUES (?, ?, ?, ?, ?);
        """, (assessment_id, current_version, snapshot_json, now_iso, change_reason or "Updated via save_impact_assessment_record"))

        # Update current record with incremented version
        new_version = current_version + 1
        cursor.execute("""
        UPDATE impact_assessments
        SET intervention_id = ?,
            ward_id = ?,
            intervention_type = ?,
            execution_status = ?,
            verification_status = ?,
            provenance_mode = ?,
            is_synthetic = ?,
            baseline_period_json = ?,
            follow_up_period_json = ?,
            indicators_json = ?,
            calculated_changes_json = ?,
            data_quality_warnings_json = ?,
            attribution_disclaimer = ?,
            summary_json = ?,
            version = ?,
            updated_at = ?
        WHERE assessment_id = ?;
        """, (
            intervention_id, ward_id, intervention_type, execution_status, verification_status,
            provenance_mode, is_synthetic, baseline_period_json, follow_up_period_json,
            indicators_json, calculated_changes_json, data_quality_warnings_json,
            attribution_disclaimer, summary_json, new_version, now_iso, assessment_id
        ))
        conn.commit()
        cursor.execute("SELECT * FROM impact_assessments WHERE assessment_id = ?;", (assessment_id,))
        updated_row = cursor.fetchone()
        conn.close()
        res = _row_to_assessment_dict(updated_row)
        res["save_status"] = "UPDATED_AND_ARCHIVED"
        return res

    # Insert new record
    created_at = record.get("created_at") or now_iso
    updated_at = now_iso
    cursor.execute("""
    INSERT INTO impact_assessments (
        assessment_id, intervention_id, ward_id, intervention_type, execution_status,
        verification_status, provenance_mode, is_synthetic, baseline_period_json,
        follow_up_period_json, indicators_json, calculated_changes_json,
        data_quality_warnings_json, attribution_disclaimer, summary_json,
        version, created_at, updated_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?);
    """, (
        assessment_id, intervention_id, ward_id, intervention_type, execution_status,
        verification_status, provenance_mode, is_synthetic, baseline_period_json,
        follow_up_period_json, indicators_json, calculated_changes_json,
        data_quality_warnings_json, attribution_disclaimer, summary_json,
        created_at, updated_at
    ))
    conn.commit()
    cursor.execute("SELECT * FROM impact_assessments WHERE assessment_id = ?;", (assessment_id,))
    new_row = cursor.fetchone()
    conn.close()
    res = _row_to_assessment_dict(new_row)
    res["save_status"] = "CREATED"
    return res


def get_impact_assessment_by_id(assessment_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves an impact assessment record by its unique ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM impact_assessments WHERE assessment_id = ?;", (assessment_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return _row_to_assessment_dict(row)


def get_all_impact_assessments(
    ward_id: Optional[str] = None,
    intervention_id: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Retrieves impact assessments with optional filtering by ward or intervention."""
    conn = get_db_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM impact_assessments WHERE 1=1"
    params: List[Any] = []

    if ward_id:
        query += " AND ward_id = ?"
        params.append(ward_id.strip().upper())
    if intervention_id:
        query += " AND intervention_id = ?"
        params.append(intervention_id.strip())

    query += " ORDER BY updated_at DESC LIMIT ?;"
    params.append(limit)

    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    conn.close()
    return [_row_to_assessment_dict(r) for r in rows]


def get_impact_assessment_history(assessment_id: str) -> List[Dict[str, Any]]:
    """Retrieves the complete audit history of all previous versions for an assessment ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT history_id, assessment_id, version, snapshot_json, archived_at, change_reason
    FROM impact_assessment_history
    WHERE assessment_id = ?
    ORDER BY version ASC;
    """, (assessment_id,))
    rows = cursor.fetchall()
    conn.close()

    history: List[Dict[str, Any]] = []
    for r in rows:
        item = dict(r)
        try:
            item["snapshot"] = json.loads(item["snapshot_json"])
        except Exception:
            item["snapshot"] = {}
        del item["snapshot_json"]
        history.append(item)
    return history


# Auto-initialize and seed when module loaded
init_db()
seed_baseline_data()

