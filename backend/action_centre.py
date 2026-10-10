"""
ClimateShield - Action Centre Module
=====================================
Operational command-and-control module that surfaces high-risk Ahmedabad wards,
displays heat and water risks with contributing factors, presents recommended
actions (heat alerts, cooling centres, drinking-water points, drainage cleaning,
water allocation), tracks action status, and reports data freshness & quality.

Safety Rules:
- Does NOT recalculate risk scores; reads from existing Combined Risk Engine
  and Intervention Engine outputs.
- Does NOT modify the Heat Engine, Water Engine, Combined Risk Engine,
  Optimizer, or Data Sources/Data Fusion modules.
- Actions are ADVISORY recommendations pending human sign-off.
- Missing data is marked explicitly, never fabricated.
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import uuid
import threading

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_STATUSES = ["proposed", "approved", "in_progress", "completed", "cancelled"]

VALID_STATUS_TRANSITIONS = {
    "proposed": {"approved", "cancelled"},
    "approved": {"in_progress", "cancelled"},
    "in_progress": {"completed", "cancelled"},
    "completed": set(),      # terminal
    "cancelled": set(),      # terminal
}

ACTION_TYPES = [
    "heat_alert",
    "cooling_centre",
    "drinking_water_point",
    "shade_canopy",
    "heat_awareness_outreach",
    "cool_roof_coating",
    "drainage_cleaning",
    "flood_barricade",
    "mobile_pump",
    "road_closure",
    "water_tanker_dispatch",
    "smart_valve_prioritization",
    "communal_bladder_tank",
    "water_conservation_advisory",
    "water_allocation_review",
    "other",
]

HUMAN_APPROVAL_NOTICE = (
    "DECISION SUPPORT ADVISORY: All recommended actions require human review "
    "and authorization by the Municipal Commissioner, Incident Commander, or "
    "designated Disaster Management Authority before dispatch."
)


# ---------------------------------------------------------------------------
# In-memory thread-safe action store
# ---------------------------------------------------------------------------

class ActionStore:
    """Thread-safe persistent store for action records synchronized with SQLite database."""

    def __init__(self):
        self._lock = threading.Lock()
        self._actions: Dict[str, Dict[str, Any]] = {}
        self._load_from_db()

    def _load_from_db(self):
        """Loads all existing actions from the SQLite database on startup."""
        try:
            from backend.database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM action_centre_records ORDER BY created_at ASC;")
            rows = cursor.fetchall()
            conn.close()
            for r in rows:
                item = dict(r)
                try:
                    item["required_resources"] = json.loads(item.get("required_resources_json") or "{}")
                except Exception:
                    item["required_resources"] = {}
                try:
                    item["status_history"] = json.loads(item.get("status_history_json") or "[]")
                except Exception:
                    item["status_history"] = []
                item["has_active_blocker"] = bool(item.get("has_active_blocker", 0))
                self._actions[item["action_id"]] = item
        except Exception:
            pass

    def _save_record_to_db(self, record: Dict[str, Any]):
        """Persists or updates an action record in the SQLite database."""
        try:
            from backend.database import get_db_connection
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO action_centre_records (
                action_id, ward_id, ward_name, action_type, priority, reason,
                required_resources_json, related_hazard, risk_score, status,
                status_history_json, has_active_blocker, last_blocker_reason,
                source, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(action_id) DO UPDATE SET
                status = excluded.status,
                status_history_json = excluded.status_history_json,
                has_active_blocker = excluded.has_active_blocker,
                last_blocker_reason = excluded.last_blocker_reason,
                updated_at = excluded.updated_at;
            """, (
                record["action_id"],
                record["ward_id"],
                record["ward_name"],
                record["action_type"],
                record["priority"],
                record["reason"],
                json.dumps(record.get("required_resources", {})),
                record.get("related_hazard"),
                record.get("risk_score"),
                record["status"],
                json.dumps(record.get("status_history", [])),
                1 if record.get("has_active_blocker") else 0,
                record.get("last_blocker_reason"),
                record.get("source", "system"),
                record["created_at"],
                record["updated_at"]
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass

    # -- write ---------------------------------------------------------------

    def create_action(
        self,
        ward_id: str,
        ward_name: str,
        action_type: str,
        priority: str,
        reason: str,
        required_resources: Optional[Dict[str, Any]] = None,
        related_hazard: Optional[str] = None,
        risk_score: Optional[float] = None,
        source: str = "system",
    ) -> Dict[str, Any]:
        """Creates a new action record with status 'proposed' and persists it."""
        if action_type not in ACTION_TYPES:
            raise ValueError(
                f"Invalid action_type '{action_type}'. "
                f"Must be one of: {ACTION_TYPES}"
            )

        action_id = f"ACT-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc).isoformat()

        record = {
            "action_id": action_id,
            "ward_id": ward_id,
            "ward_name": ward_name,
            "action_type": action_type,
            "priority": priority,
            "reason": reason,
            "required_resources": required_resources or {},
            "related_hazard": related_hazard,
            "risk_score": risk_score,
            "status": "proposed",
            "status_history": [
                {"status": "proposed", "timestamp": now, "changed_by": source}
            ],
            "has_active_blocker": False,
            "last_blocker_reason": None,
            "created_at": now,
            "updated_at": now,
            "source": source,
        }

        with self._lock:
            self._actions[action_id] = record
            self._save_record_to_db(record)

        return record

    def update_status(
        self,
        action_id: str,
        new_status: str,
        changed_by: str = "operator",
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Transitions an action to a new status with validation and persists changes."""
        if new_status not in VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{new_status}'. Must be one of: {VALID_STATUSES}"
            )

        with self._lock:
            if action_id not in self._actions:
                self._load_from_db()

            if action_id not in self._actions:
                raise KeyError(f"Action '{action_id}' not found")

            action = self._actions[action_id]
            current_status = action["status"]

            allowed = VALID_STATUS_TRANSITIONS.get(current_status, set())
            if new_status not in allowed:
                raise ValueError(
                    f"Cannot transition from '{current_status}' to '{new_status}'. "
                    f"Allowed transitions: {sorted(allowed) if allowed else 'none (terminal state)'}"
                )

            now = datetime.now(timezone.utc).isoformat()
            entry = {
                "status": new_status,
                "timestamp": now,
                "changed_by": changed_by,
            }
            if notes:
                entry["notes"] = notes

            action["status"] = new_status
            action["updated_at"] = now
            action.setdefault("status_history", []).append(entry)
            self._save_record_to_db(action)

            return dict(action)

    # -- read ----------------------------------------------------------------

    def get_action(self, action_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            self._load_from_db()
            action = self._actions.get(action_id)
            return dict(action) if action else None

    def list_actions(
        self,
        ward_id: Optional[str] = None,
        action_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Lists actions with optional filters and automatic database sync."""
        with self._lock:
            self._load_from_db()
            results = list(self._actions.values())

        if ward_id:
            wid = ward_id.strip().lower()
            results = [
                a for a in results
                if wid in a["ward_id"].lower() or wid in a["ward_name"].lower()
            ]
        if action_type:
            at = action_type.strip().lower()
            results = [a for a in results if a["action_type"].lower() == at]
        if status:
            st = status.strip().lower()
            results = [a for a in results if a["status"].lower() == st]

        return [dict(a) for a in results]

    def count_by_status(self) -> Dict[str, int]:
        with self._lock:
            self._load_from_db()
            counts = {s: 0 for s in VALID_STATUSES}
            for a in self._actions.values():
                counts[a["status"]] = counts.get(a["status"], 0) + 1
            return counts

    def clear(self):
        """Clears all actions (useful for testing)."""
        with self._lock:
            self._actions.clear()
            try:
                from backend.database import get_db_connection
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM action_centre_records;")
                conn.commit()
                conn.close()
            except Exception:
                pass


# Module-level singleton
_action_store = ActionStore()


def get_action_store() -> ActionStore:
    """Returns the module-level action store singleton."""
    return _action_store


# ---------------------------------------------------------------------------
# Action generation from existing engine outputs
# ---------------------------------------------------------------------------

# Maps intervention IDs from the optimizer / intervention engine to action types
_INTERVENTION_TO_ACTION_TYPE = {
    "cooling_center": "cooling_centre",
    "hydration_kiosk": "drinking_water_point",
    "shade_canopy": "shade_canopy",
    "heat_awareness_outreach": "heat_awareness_outreach",
    "cool_roof_coating": "cool_roof_coating",
    "drainage_inspection_cleaning": "drainage_cleaning",
    "flood_warning_barricade": "flood_barricade",
    "mobile_pump_deployment": "mobile_pump",
    "mobile_dewatering_pump": "mobile_pump",
    "emergency_road_closure": "road_closure",
    "tanker_dispatch": "water_tanker_dispatch",
    "water_tanker_dispatch": "water_tanker_dispatch",
    "smart_valve_supply": "smart_valve_prioritization",
    "supply_prioritization_rationing": "smart_valve_prioritization",
    "communal_bladder_tank": "communal_bladder_tank",
    "communal_storage_tank": "communal_bladder_tank",
}

_HAZARD_PRIORITY_MAP = {
    "CRITICAL": "critical",
    "HIGH": "high",
    "ELEVATED": "medium",
    "MODERATE": "medium",
    "LOW": "low",
}


def _extract_priority_from_score(score: Optional[float]) -> str:
    """Maps a 0–100 risk score to a priority label."""
    if score is None:
        return "medium"
    if score >= 75.0:
        return "critical"
    if score >= 50.0:
        return "high"
    if score >= 25.0:
        return "medium"
    return "low"


def generate_actions_from_climate_risk(
    climate_risk_data: Dict[str, Any],
    store: Optional[ActionStore] = None,
) -> Dict[str, Any]:
    """
    Reads existing Combined Climate Risk Engine output and generates
    proposed heat-alert actions for high-risk wards.

    Does NOT recalculate risk; only reads 'ranked_wards' from existing output.
    """
    store = store or get_action_store()
    ranked_wards = climate_risk_data.get("ranked_wards", [])
    created_actions = []

    for ward in ranked_wards:
        combined_score = ward.get("combined_risk_score", 0.0)
        heat_score = ward.get("heat_risk_score", 0.0)
        water_score = ward.get("water_risk_score", 0.0)
        ward_id = ward.get("id", "")
        ward_name = ward.get("name", ward.get("official_name", ""))
        compound = ward.get("compound_hazard", {})

        # Only generate actions for wards at elevated risk or above
        if combined_score < 25.0:
            continue

        priority = _extract_priority_from_score(combined_score)

        # Heat alert for wards with significant heat risk
        if heat_score >= 30.0:
            heat_category = ward.get("heat_risk_category", "")
            reason = (
                f"Heat risk score {heat_score:.1f}/100 "
                f"({heat_category or 'elevated'}). "
                f"Combined risk {combined_score:.1f}/100 for ward {ward_name}."
            )
            if compound.get("is_compound_hotspot"):
                reason += f" {compound.get('badge', '')} — compound hazard detected."

            action = store.create_action(
                ward_id=ward_id,
                ward_name=ward_name,
                action_type="heat_alert",
                priority=priority,
                reason=reason,
                related_hazard="heat",
                risk_score=heat_score,
                source="climate_risk_engine",
            )
            created_actions.append(action)

    return {
        "status": "SUCCESS",
        "total_actions_created": len(created_actions),
        "actions": created_actions,
        "advisory": HUMAN_APPROVAL_NOTICE,
    }


def generate_actions_from_interventions(
    intervention_plan: Dict[str, Any],
    store: Optional[ActionStore] = None,
) -> Dict[str, Any]:
    """
    Reads existing Intervention Engine / Optimizer output and converts
    recommended interventions into trackable Action Centre records.

    Does NOT rerun optimization; reads the dispatch plan that was already computed.
    """
    store = store or get_action_store()
    created_actions = []

    # The intervention engine returns 'dispatch_plan' with a list of allocated items
    dispatch_items = intervention_plan.get("dispatch_plan", [])

    # Also try 'optimized_dispatch_plan' key used by the intervention engine
    if not dispatch_items:
        dispatch_items = intervention_plan.get("optimized_dispatch_plan", [])

    # Fallback: 'ranked_interventions' from the ranked endpoint
    if not dispatch_items:
        dispatch_items = intervention_plan.get("ranked_interventions", [])

    for item in dispatch_items:
        intervention_id = item.get("intervention_id", item.get("id", ""))
        action_type = _INTERVENTION_TO_ACTION_TYPE.get(intervention_id, "other")

        target_ward = item.get("target_ward", {})
        ward_id = target_ward.get("ward_id", item.get("ward_id", ""))
        ward_name = target_ward.get("ward_name", item.get("ward_name", ""))

        reason = item.get("reason", item.get("rationale", ""))
        if not reason:
            reason = item.get("reason_template", f"Recommended {intervention_id} intervention.")

        priority_score = item.get("composite_priority_score", item.get("priority_score"))
        priority = _extract_priority_from_score(
            priority_score * 100 if priority_score and priority_score <= 1.0 else priority_score
        )

        resources = {}
        if "unit_cost_inr" in item:
            resources["cost_inr"] = item["unit_cost_inr"]
        if "crew_required" in item:
            resources["crew_required"] = item["crew_required"]
        if "water_required_l" in item:
            resources["water_required_l"] = item["water_required_l"]

        related_hazard = item.get("related_hazard", item.get("category", None))
        risk_score_val = item.get("ward_combined_risk_score", item.get("risk_score"))

        action = store.create_action(
            ward_id=ward_id,
            ward_name=ward_name,
            action_type=action_type,
            priority=priority,
            reason=reason,
            required_resources=resources,
            related_hazard=related_hazard,
            risk_score=risk_score_val,
            source="intervention_engine",
        )
        created_actions.append(action)

    return {
        "status": "SUCCESS",
        "total_actions_created": len(created_actions),
        "actions": created_actions,
        "advisory": HUMAN_APPROVAL_NOTICE,
    }


# ---------------------------------------------------------------------------
# Dashboard summary builder
# ---------------------------------------------------------------------------

def evaluate_risk_data_freshness(
    climate_risk_data: Optional[Dict[str, Any]] = None,
    data_quality: Optional[Dict[str, Any]] = None,
    max_age_seconds: float = 86400.0,
) -> Dict[str, Any]:
    """
    Evaluates whether climate risk data is available, fresh, or stale.
    Safely handles missing or unparseable timestamps without crashing.
    Maintains full backward-compatible keys ('climate_risk_available',
    'climate_risk_timestamp', 'data_quality').
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    if not climate_risk_data:
        quality_val = data_quality if data_quality is not None else "unavailable — no quality metadata provided"
        return {
            "timestamp": now_iso,
            "climate_risk_available": False,
            "climate_risk_timestamp": None,
            "data_quality": quality_val,
            "staleness_status": "UNAVAILABLE",
            "is_stale": False,
            "age_seconds": None,
            "message": "Climate risk data is not provided. Operating in safe decoupled store-only mode.",
        }

    ts_str = climate_risk_data.get("timestamp")
    age_seconds = None
    is_stale = False

    if ts_str:
        try:
            clean_ts = ts_str.replace("Z", "+00:00")
            parsed_ts = datetime.fromisoformat(clean_ts)
            if parsed_ts.tzinfo is None:
                parsed_ts = parsed_ts.replace(tzinfo=timezone.utc)
            age_seconds = max(0.0, (now - parsed_ts).total_seconds())
            is_stale = age_seconds > max_age_seconds
        except Exception:
            is_stale = False

    staleness_status = "STALE" if is_stale else "FRESH"
    msg = (
        f"Risk results are stale (age: {int(age_seconds)}s > {int(max_age_seconds)}s threshold). Revalidation recommended."
        if is_stale else
        "Risk results are fresh and within operational threshold."
    )

    quality_val = (
        data_quality
        if data_quality is not None
        else climate_risk_data.get("data_quality_and_confidence", "unavailable — no quality metadata provided")
    )

    return {
        "timestamp": now_iso,
        "climate_risk_available": True,
        "climate_risk_timestamp": ts_str,
        "data_quality": quality_val,
        "staleness_status": staleness_status,
        "is_stale": is_stale,
        "age_seconds": round(age_seconds, 1) if age_seconds is not None else None,
        "message": msg,
    }


def get_prioritized_actions(
    store: Optional[ActionStore] = None,
    status: Optional[str] = None,
    ward_id: Optional[str] = None,
    action_type: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Returns actions sorted by priority, status urgency, risk score, and recency.
    Priority order: critical (0) > high (1) > medium (2) > low (3).
    Status urgency: in_progress (0) > approved (1) > proposed (2) > completed (3) > cancelled (4).
    """
    store = store or get_action_store()
    actions = store.list_actions(ward_id=ward_id, action_type=action_type, status=status)

    priority_map = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    status_urgency = {"in_progress": 0, "approved": 1, "proposed": 2, "completed": 3, "cancelled": 4}

    actions.sort(key=lambda a: (
        priority_map.get(a.get("priority", "medium").lower(), 9),
        status_urgency.get(a.get("status", "proposed").lower(), 9),
        -(a.get("risk_score") or 0.0),
        a.get("created_at") or "",
    ))

    if limit is not None and limit > 0:
        return actions[:limit]
    return actions


def get_ward_wise_action_summary(
    store: Optional[ActionStore] = None,
    climate_risk_data: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Aggregates existing Action Centre actions by ward, correlating with
    risk engine outputs when available.
    """
    store = store or get_action_store()
    all_actions = store.list_actions()

    # Index climate risk wards by id and name for matching
    risk_by_ward: Dict[str, Any] = {}
    if climate_risk_data:
        for w in climate_risk_data.get("ranked_wards", climate_risk_data.get("wards", [])):
            wid = (w.get("id") or w.get("ward_id") or "").strip().lower()
            wname = (w.get("name") or w.get("ward_name") or w.get("official_name") or "").strip().lower()
            info = {
                "combined_risk_score": w.get("combined_risk_score"),
                "risk_category": w.get("combined_risk_category") or w.get("risk_category"),
                "heat_risk_score": w.get("heat_risk_score"),
                "water_risk_score": w.get("water_risk_score"),
                "is_compound_hotspot": bool(w.get("compound_hazard", {}).get("is_compound_hotspot", False)),
            }
            if wid:
                risk_by_ward[wid] = info
            if wname:
                risk_by_ward[wname] = info

    # Group actions by ward_id
    wards_map: Dict[str, Dict[str, Any]] = {}
    for a in all_actions:
        wid = a["ward_id"]
        wname = a["ward_name"]
        if wid not in wards_map:
            matched = risk_by_ward.get(wid.lower()) or risk_by_ward.get(wname.lower()) or {}
            wards_map[wid] = {
                "ward_id": wid,
                "ward_name": wname,
                "total_actions": 0,
                "active_actions_count": 0,
                "by_status": {s: 0 for s in VALID_STATUSES},
                "highest_priority": "none",
                "risk_profile": matched if matched else "risk_profile_unavailable",
                "actions": [],
            }

        w_entry = wards_map[wid]
        w_entry["total_actions"] += 1
        st = a["status"]
        if st in w_entry["by_status"]:
            w_entry["by_status"][st] += 1
        if st in UNRESOLVED_STATUSES:
            w_entry["active_actions_count"] += 1

        w_entry["actions"].append(a)

    priority_ranks = {"critical": 0, "high": 1, "medium": 2, "low": 3, "none": 9}
    for w_entry in wards_map.values():
        prios = [a.get("priority", "low").lower() for a in w_entry["actions"]]
        if prios:
            w_entry["highest_priority"] = min(prios, key=lambda p: priority_ranks.get(p, 9))

    # Sort wards by active action count descending, then total actions
    result = list(wards_map.values())
    result.sort(key=lambda w: (
        -w["active_actions_count"],
        -w["total_actions"],
        w["ward_id"],
    ))
    return result


def build_action_centre_dashboard(
    climate_risk_data: Optional[Dict[str, Any]] = None,
    data_quality: Optional[Dict[str, Any]] = None,
    store: Optional[ActionStore] = None,
) -> Dict[str, Any]:
    """
    Builds the Action Centre dashboard summary from existing risk outputs
    and the current action store state. Handles missing or stale risk results safely.
    Provides high-risk wards, action counts, ward-wise summary, and prioritized actions.
    """
    store = store or get_action_store()
    now = datetime.now(timezone.utc).isoformat()

    # Summarize high-risk wards from existing combined risk data
    high_risk_wards = []
    if climate_risk_data:
        for ward in climate_risk_data.get("ranked_wards", []):
            combined = ward.get("combined_risk_score", 0.0)
            if combined >= 50.0:
                high_risk_wards.append({
                    "ward_id": ward.get("id", ""),
                    "ward_name": ward.get("name", ""),
                    "combined_risk_score": combined,
                    "heat_risk_score": ward.get("heat_risk_score"),
                    "water_risk_score": ward.get("water_risk_score"),
                    "risk_category": ward.get("combined_risk_category", ""),
                    "compound_hazard": ward.get("compound_hazard", {}),
                    "contributing_factors": {
                        "heat": ward.get("heat_contributing_factors", ward.get("heat_risk_category", "unavailable")),
                        "water": ward.get("water_contributing_factors", ward.get("water_risk_category", "unavailable")),
                    },
                })

    # Action status counts and lists
    status_counts = store.count_by_status()
    all_actions = store.list_actions()

    # Data freshness and staleness evaluation
    freshness = evaluate_risk_data_freshness(
        climate_risk_data=climate_risk_data,
        data_quality=data_quality,
    )

    # Ward-wise action summary and prioritized queue
    ward_summaries = get_ward_wise_action_summary(
        store=store,
        climate_risk_data=climate_risk_data,
    )
    prioritized_actions = get_prioritized_actions(store=store)

    return {
        "status": "SUCCESS",
        "dashboard_generated_at": now,
        "advisory": HUMAN_APPROVAL_NOTICE,
        "high_risk_wards": {
            "count": len(high_risk_wards),
            "wards": high_risk_wards,
        },
        "action_summary": {
            "total_actions": len(all_actions),
            "by_status": status_counts,
        },
        "ward_action_summary": {
            "total_wards_with_actions": len(ward_summaries),
            "ward_summaries": ward_summaries,
        },
        "prioritized_actions": prioritized_actions[:20],
        "recent_actions": sorted(all_actions, key=lambda a: a["created_at"], reverse=True)[:20],
        "data_freshness": freshness,
    }


# ---------------------------------------------------------------------------
# Rule-Based Recommendation Layer
# ---------------------------------------------------------------------------

UNRESOLVED_STATUSES = {"proposed", "approved", "in_progress"}
RESOLVED_STATUSES = {"completed", "cancelled"}

# Transparent, configurable default thresholds (0-100 scale)
DEFAULT_RECOMMENDATION_THRESHOLDS: Dict[str, float] = {
    # Heat hazard rules
    "heat_alert_threshold": 50.0,
    "cooling_centre_threshold": 60.0,
    "drinking_water_threshold": 45.0,
    "shade_canopy_threshold": 55.0,
    # Flood / waterlogging rules
    "drainage_cleaning_threshold": 40.0,
    "mobile_pump_threshold": 55.0,
    "flood_barricade_threshold": 65.0,
    # Drought / water stress rules
    "water_conservation_threshold": 40.0,
    "water_allocation_review_threshold": 50.0,
    "water_tanker_threshold": 55.0,
    "communal_tank_threshold": 60.0,
}

# Standard municipal resource schedule per action type (aligned with Optimizer)
ACTION_RESOURCE_ESTIMATES: Dict[str, Dict[str, Any]] = {
    "heat_alert": {"cost_inr": 5000.0, "crew_required": 1, "water_required_l": 0.0},
    "cooling_centre": {"cost_inr": 50000.0, "crew_required": 4, "water_required_l": 500.0},
    "drinking_water_point": {"cost_inr": 15000.0, "crew_required": 2, "water_required_l": 1200.0},
    "shade_canopy": {"cost_inr": 25000.0, "crew_required": 3, "water_required_l": 0.0},
    "heat_awareness_outreach": {"cost_inr": 18000.0, "crew_required": 3, "water_required_l": 200.0},
    "cool_roof_coating": {"cost_inr": 35000.0, "crew_required": 5, "water_required_l": 100.0},
    "drainage_cleaning": {"cost_inr": 30000.0, "crew_required": 4, "water_required_l": 0.0},
    "flood_barricade": {"cost_inr": 20000.0, "crew_required": 2, "water_required_l": 0.0},
    "mobile_pump": {"cost_inr": 40000.0, "crew_required": 3, "water_required_l": 0.0},
    "road_closure": {"cost_inr": 12000.0, "crew_required": 4, "water_required_l": 0.0},
    "water_tanker_dispatch": {"cost_inr": 12000.0, "crew_required": 2, "water_required_l": 5000.0},
    "smart_valve_prioritization": {"cost_inr": 22000.0, "crew_required": 3, "water_required_l": 0.0},
    "water_allocation_review": {"cost_inr": 15000.0, "crew_required": 2, "water_required_l": 0.0},
    "water_conservation_advisory": {"cost_inr": 8000.0, "crew_required": 1, "water_required_l": 0.0},
    "communal_bladder_tank": {"cost_inr": 32000.0, "crew_required": 4, "water_required_l": 5000.0},
    "other": {"cost_inr": 10000.0, "crew_required": 2, "water_required_l": 0.0},
}

RULE_DEFINITIONS: List[Dict[str, Any]] = [
    # --- HEAT HAZARD RULES ---
    {
        "rule_id": "RULE-HEAT-01-ALERT",
        "name": "Targeted Heat Wave Alert Advisory",
        "hazard_category": "heat",
        "action_type": "heat_alert",
        "threshold_key": "heat_alert_threshold",
        "indicator": "heat_score",
        "description": "Recommends targeted heat warning and advisory dissemination when heat risk exceeds threshold.",
        "template": (
            "Targeted heat advisory recommended for ward {ward_name} ({ward_id}) "
            "based on heat risk score of {score:.1f}/100 exceeding threshold of {threshold:.1f}."
            "{extra} Advisory only; no real-time public alerts have been broadcast."
        ),
    },
    {
        "rule_id": "RULE-HEAT-02-COOLING",
        "name": "Cooling-Centre Readiness Advisory",
        "hazard_category": "heat",
        "action_type": "cooling_centre",
        "threshold_key": "cooling_centre_threshold",
        "indicator": "heat_score",
        "description": "Recommends readying cooling centres and air-conditioned refuges when severe heat stress is detected.",
        "template": (
            "Cooling-centre readiness recommended for ward {ward_name} ({ward_id}) "
            "based on high heat risk score of {score:.1f}/100 exceeding threshold of {threshold:.1f}."
            "{extra} Advisory only; no physical shelters have been opened."
        ),
    },
    {
        "rule_id": "RULE-HEAT-03-HYDRATION",
        "name": "Drinking-Water Point Access Advisory",
        "hazard_category": "heat",
        "action_type": "drinking_water_point",
        "threshold_key": "drinking_water_threshold",
        "indicator": "heat_score",
        "description": "Recommends deploying emergency drinking water kiosks and ORS distribution along pedestrian corridors.",
        "template": (
            "Emergency drinking-water point access recommended for ward {ward_name} ({ward_id}) "
            "based on elevated heat risk score of {score:.1f}/100 exceeding threshold of {threshold:.1f}."
            "{extra} Advisory only; no physical hydration kiosks have been deployed."
        ),
    },
    {
        "rule_id": "RULE-HEAT-04-SHADE",
        "name": "Pedestrian Shade Canopy Advisory",
        "hazard_category": "heat",
        "action_type": "shade_canopy",
        "threshold_key": "shade_canopy_threshold",
        "indicator": "heat_score",
        "description": "Recommends deploying UV-reflective pedestrian shade canopies in crowded transit/labor corridors.",
        "template": (
            "Pedestrian shade canopy deployment recommended for ward {ward_name} ({ward_id}) "
            "based on heat risk score of {score:.1f}/100 exceeding threshold of {threshold:.1f}."
            "{extra} Advisory only; no physical structures have been erected."
        ),
    },

    # --- FLOOD / WATERLOGGING RULES ---
    {
        "rule_id": "RULE-FLOOD-01-DRAINAGE",
        "name": "Drainage Inspection & Desilting Advisory",
        "hazard_category": "flood",
        "action_type": "drainage_cleaning",
        "threshold_key": "drainage_cleaning_threshold",
        "indicator": "waterlogging_score",
        "description": "Recommends proactive culvert desilting and storm drain inspection supported by pluvial flood indicators.",
        "template": (
            "Drainage inspection and culvert desilting recommended for ward {ward_name} ({ward_id}) "
            "supported by flood-risk indicator: waterlogging score of {score:.1f}/100 exceeding threshold of {threshold:.1f}."
            "{extra} Advisory only; no physical desilting work has been performed."
        ),
    },
    {
        "rule_id": "RULE-FLOOD-02-PUMP",
        "name": "Mobile Dewatering Pump Staging Advisory",
        "hazard_category": "flood",
        "action_type": "mobile_pump",
        "threshold_key": "mobile_pump_threshold",
        "indicator": "waterlogging_score",
        "description": "Recommends staging mobile dewatering pumps in low-lying catchment areas with elevated flood risk.",
        "template": (
            "Mobile dewatering pump staging recommended for ward {ward_name} ({ward_id}) "
            "supported by pluvial flood indicator: waterlogging score of {score:.1f}/100 exceeding threshold of {threshold:.1f}."
            "{extra} Advisory only; no mobile pumps have been deployed."
        ),
    },
    {
        "rule_id": "RULE-FLOOD-03-BARRICADE",
        "name": "Underpass Flood Warning Barricade Advisory",
        "hazard_category": "flood",
        "action_type": "flood_barricade",
        "threshold_key": "flood_barricade_threshold",
        "indicator": "waterlogging_score",
        "description": "Recommends staging automated warning barricades at flood-prone underpasses supported by severe flood indicators.",
        "template": (
            "Underpass flood warning barricade staging recommended for ward {ward_name} ({ward_id}) "
            "supported by critical flood risk indicator: waterlogging score of {score:.1f}/100 exceeding threshold of {threshold:.1f}."
            "{extra} Advisory only; no barricades have been erected."
        ),
    },

    # --- DROUGHT / WATER STRESS RULES ---
    {
        "rule_id": "RULE-DROUGHT-01-CONSERVE",
        "name": "Water Conservation Advisory",
        "hazard_category": "water_stress",
        "action_type": "water_conservation_advisory",
        "threshold_key": "water_conservation_threshold",
        "indicator": "water_shortage_score",
        "description": "Recommends municipal water conservation advisories and non-essential usage reductions supported by water stress data.",
        "template": (
            "Municipal water conservation advisory recommended for ward {ward_name} ({ward_id}) "
            "supported by water stress data: shortage score of {score:.1f}/100 exceeding threshold of {threshold:.1f}."
            "{extra} Advisory only; no mandatory restrictions have been enforced."
        ),
    },
    {
        "rule_id": "RULE-DROUGHT-02-ALLOCATION",
        "name": "Water Allocation Review Advisory",
        "hazard_category": "water_stress",
        "action_type": "water_allocation_review",
        "threshold_key": "water_allocation_review_threshold",
        "indicator": "water_shortage_score",
        "description": "Recommends reviewing ward water allocation quotas and valve pressure balancing supported by supply deficit indicators.",
        "template": (
            "Reviewing ward water allocation and pressure balancing recommended for ward {ward_name} ({ward_id}) "
            "supported by water stress data: shortage score of {score:.1f}/100 exceeding threshold of {threshold:.1f}."
            "{extra} Advisory only; no valve adjustments or quota shifts have been executed."
        ),
    },
    {
        "rule_id": "RULE-DROUGHT-03-TANKER",
        "name": "Emergency Water Tanker Dispatch Advisory",
        "hazard_category": "water_stress",
        "action_type": "water_tanker_dispatch",
        "threshold_key": "water_tanker_threshold",
        "indicator": "water_shortage_score",
        "description": "Recommends staging emergency potable water tankers in vulnerable clusters supported by severe water shortage indicators.",
        "template": (
            "Emergency potable water tanker dispatch recommended for ward {ward_name} ({ward_id}) "
            "supported by acute water stress indicator: shortage score of {score:.1f}/100 exceeding threshold of {threshold:.1f}."
            "{extra} Advisory only; no tankers have been dispatched."
        ),
    },
]


def extract_indicators_from_ward(ward: Dict[str, Any]) -> Dict[str, Any]:
    """
    Safely extracts risk indicators from a ward dictionary.
    Never invents missing values; returns None if an indicator is absent.
    """
    ward_id = str(ward.get("id") or ward.get("ward_id") or "")
    ward_name = str(ward.get("name") or ward.get("ward_name") or ward.get("official_name") or ward_id)

    # 1. Heat indicators
    heat_score = ward.get("heat_risk_score")
    if heat_score is None and isinstance(ward.get("heat_risk"), dict):
        heat_score = ward["heat_risk"].get("score")
    if heat_score is not None:
        try:
            heat_score = float(heat_score)
        except (ValueError, TypeError):
            heat_score = None

    effective_wbgt = None
    if isinstance(ward.get("heat_risk"), dict):
        effective_wbgt = ward["heat_risk"].get("effective_wbgt_c")
        if effective_wbgt is not None:
            try:
                effective_wbgt = float(effective_wbgt)
            except (ValueError, TypeError):
                effective_wbgt = None

    # 2. Water risk object
    water_obj = ward.get("water_risk", {})
    if not isinstance(water_obj, dict):
        water_obj = {}

    water_score = ward.get("water_risk_score")
    if water_score is None:
        water_score = water_obj.get("score")
    if water_score is not None:
        try:
            water_score = float(water_score)
        except (ValueError, TypeError):
            water_score = None

    # 3. Waterlogging / Flood indicators
    waterlogging_score = ward.get("waterlogging_score")
    if waterlogging_score is None:
        waterlogging_score = water_obj.get("waterlogging_score")
    if waterlogging_score is None:
        cf = water_obj.get("contributing_factors", {})
        if isinstance(cf, dict) and "waterlogging" in cf:
            w_cf = cf.get("waterlogging", {})
            if isinstance(w_cf, dict):
                waterlogging_score = w_cf.get("score")
    if waterlogging_score is None:
        cf = ward.get("contributing_factors", {})
        if isinstance(cf, dict) and "waterlogging" in cf:
            w_cf = cf.get("waterlogging", {})
            if isinstance(w_cf, dict):
                waterlogging_score = w_cf.get("score")
    if waterlogging_score is not None:
        try:
            waterlogging_score = float(waterlogging_score)
        except (ValueError, TypeError):
            waterlogging_score = None

    # 4. Water shortage / Drought indicators
    water_shortage_score = ward.get("water_shortage_score")
    if water_shortage_score is None:
        water_shortage_score = water_obj.get("water_shortage_score")
    if water_shortage_score is None:
        cf = water_obj.get("contributing_factors", {})
        if isinstance(cf, dict) and "water_shortage" in cf:
            s_cf = cf.get("water_shortage", {})
            if isinstance(s_cf, dict):
                water_shortage_score = s_cf.get("score")
    if water_shortage_score is None:
        cf = ward.get("contributing_factors", {})
        if isinstance(cf, dict) and "water_shortage" in cf:
            s_cf = cf.get("water_shortage", {})
            if isinstance(s_cf, dict):
                water_shortage_score = s_cf.get("score")
    if water_shortage_score is not None:
        try:
            water_shortage_score = float(water_shortage_score)
        except (ValueError, TypeError):
            water_shortage_score = None

    # 5. Compound hazard
    compound = ward.get("compound_hazard", {})
    if not isinstance(compound, dict):
        compound = {}
    is_compound = bool(compound.get("is_compound_hotspot", False))
    compound_badge = str(compound.get("badge", ""))

    return {
        "ward_id": ward_id,
        "ward_name": ward_name,
        "heat_score": heat_score,
        "effective_wbgt": effective_wbgt,
        "water_score": water_score,
        "waterlogging_score": waterlogging_score,
        "water_shortage_score": water_shortage_score,
        "is_compound": is_compound,
        "compound_badge": compound_badge,
    }


def check_duplicate_unresolved_action(
    store: ActionStore,
    ward_id: str,
    action_type: str,
    seen_batch_keys: set,
) -> Optional[Dict[str, Any]]:
    """
    Checks if an unresolved action already exists for the given ward and action type.
    Unresolved statuses: 'proposed', 'approved', 'in_progress'.
    Terminal/resolved statuses ('completed', 'cancelled') do NOT block new recommendations.
    Also checks seen_batch_keys to prevent duplicates within the same evaluation run.
    """
    if (ward_id, action_type) in seen_batch_keys:
        return {
            "duplicate_source": "batch",
            "action_id": "BATCH_DUPLICATE",
            "status": "proposed",
            "reason": f"Duplicate recommendation for ward '{ward_id}' and action '{action_type}' in current evaluation run."
        }

    existing_actions = store.list_actions(ward_id=ward_id, action_type=action_type)
    for existing in existing_actions:
        if existing["status"] in UNRESOLVED_STATUSES:
            return {
                "duplicate_source": "store",
                "action_id": existing["action_id"],
                "status": existing["status"],
                "reason": (
                    f"Active unresolved action '{existing['action_id']}' with status '{existing['status']}' "
                    f"already exists for ward '{ward_id}' and action '{action_type}'."
                )
            }
    return None


class RuleBasedRecommendationEngine:
    """
    Explainable, rule-based recommendation engine for the Action Centre.
    Evaluates existing risk outputs and Optimizer plans, respects resource
    constraints, prevents duplicates for unresolved risks, and maintains
    strict transparency and safety guardrails.
    """

    def __init__(
        self,
        thresholds: Optional[Dict[str, float]] = None,
        resource_estimates: Optional[Dict[str, Dict[str, Any]]] = None,
        rules: Optional[List[Dict[str, Any]]] = None,
    ):
        self.thresholds = dict(DEFAULT_RECOMMENDATION_THRESHOLDS)
        if thresholds:
            self.thresholds.update(thresholds)

        self.resource_estimates = dict(ACTION_RESOURCE_ESTIMATES)
        if resource_estimates:
            self.resource_estimates.update(resource_estimates)

        self.rules = list(rules) if rules is not None else list(RULE_DEFINITIONS)

    def evaluate_ward(self, ward: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Evaluates a single ward against all active rules.
        Returns a list of candidate recommendation dictionaries.
        """
        indicators = extract_indicators_from_ward(ward)
        ward_id = indicators["ward_id"]
        ward_name = indicators["ward_name"]
        candidates = []

        for rule in self.rules:
            indicator_key = rule["indicator"]
            score = indicators.get(indicator_key)

            # Do not invent values: if the required indicator is missing, rule does not fire
            if score is None:
                continue

            threshold = self.thresholds.get(rule["threshold_key"], 50.0)
            if score < threshold:
                continue

            # Extra contextual notes
            extra_notes = []
            if indicators["effective_wbgt"] is not None:
                extra_notes.append(f"Effective outdoor WBGT is {indicators['effective_wbgt']:.1f}°C.")
            if indicators["is_compound"]:
                extra_notes.append("Compound hazard hotspot detected.")

            extra_str = (" " + " ".join(extra_notes)) if extra_notes else ""

            reason = rule["template"].format(
                ward_name=ward_name,
                ward_id=ward_id,
                score=score,
                threshold=threshold,
                extra=extra_str,
            )

            priority = _extract_priority_from_score(score)
            if indicators["is_compound"] and priority == "high":
                priority = "critical"

            resources = dict(self.resource_estimates.get(rule["action_type"], {}))

            candidates.append({
                "rule_id": rule["rule_id"],
                "rule_name": rule["name"],
                "ward_id": ward_id,
                "ward_name": ward_name,
                "action_type": rule["action_type"],
                "priority": priority,
                "reason": reason,
                "required_resources": resources,
                "related_hazard": rule["hazard_category"],
                "risk_score": score,
                "threshold_applied": threshold,
                "source": "rule_recommendation_engine",
            })

        return candidates

    def generate_recommendations(
        self,
        climate_risk_data: Optional[Dict[str, Any]] = None,
        optimizer_plan: Optional[Dict[str, Any]] = None,
        resource_constraints: Optional[Dict[str, Any]] = None,
        store: Optional[ActionStore] = None,
        create_in_store: bool = True,
        enforce_resource_constraints: bool = True,
    ) -> Dict[str, Any]:
        """
        Generates explainable recommendations based on climate risk data and/or
        optimizer outputs. Enforces duplicate prevention and resource constraints.
        """
        store = store or get_action_store()
        candidates: List[Dict[str, Any]] = []

        # 1. Ingest candidates from climate risk data wards
        if climate_risk_data:
            wards = climate_risk_data.get("ranked_wards", climate_risk_data.get("wards", []))
            for ward in wards:
                candidates.extend(self.evaluate_ward(ward))

        # 2. Ingest candidates from Optimizer plan if provided
        if optimizer_plan:
            dispatch_items = (
                optimizer_plan.get("dispatch_plan")
                or optimizer_plan.get("optimized_dispatch_plan")
                or optimizer_plan.get("ranked_interventions")
                or []
            )
            for item in dispatch_items:
                intervention_id = item.get("intervention_id", item.get("id", ""))
                action_type = _INTERVENTION_TO_ACTION_TYPE.get(intervention_id, intervention_id)
                if action_type not in ACTION_TYPES:
                    action_type = "other"

                target_ward = item.get("target_ward", {})
                w_id = target_ward.get("ward_id", item.get("ward_id", ""))
                w_name = target_ward.get("ward_name", item.get("ward_name", w_id))

                base_reason = item.get("reason") or item.get("rationale") or f"Optimizer-recommended {intervention_id} intervention."
                full_reason = f"{base_reason} Advisory only; pending human authorization."

                priority_score = item.get("composite_priority_score", item.get("priority_score", 0.5))
                if isinstance(priority_score, (int, float)) and priority_score <= 1.0:
                    priority_score_pct = priority_score * 100.0
                else:
                    priority_score_pct = float(priority_score) if priority_score is not None else 50.0

                priority = _extract_priority_from_score(priority_score_pct)

                resources = {
                    "cost_inr": float(item.get("unit_cost_inr", self.resource_estimates.get(action_type, {}).get("cost_inr", 0.0))),
                    "crew_required": int(item.get("crew_required", self.resource_estimates.get(action_type, {}).get("crew_required", 0))),
                    "water_required_l": float(item.get("water_required_l", self.resource_estimates.get(action_type, {}).get("water_required_l", 0.0))),
                }

                candidates.append({
                    "rule_id": f"OPTIMIZER-{intervention_id.upper()}",
                    "rule_name": f"Optimizer Plan: {intervention_id}",
                    "ward_id": w_id,
                    "ward_name": w_name,
                    "action_type": action_type,
                    "priority": priority,
                    "reason": full_reason,
                    "required_resources": resources,
                    "related_hazard": item.get("related_hazard", item.get("risk_type", "multi_hazard")),
                    "risk_score": priority_score_pct,
                    "threshold_applied": item.get("trigger_threshold", 0.0),
                    "source": "optimizer_recommendation",
                })

        # 3. Extract resource limits from optimizer_plan if not explicitly passed
        if resource_constraints is None and optimizer_plan is not None:
            limits = optimizer_plan.get("resource_limits", {})
            b = limits.get("budget_inr", optimizer_plan.get("total_budget_inr"))
            c = limits.get("crew_members", optimizer_plan.get("total_crew_members"))
            w = limits.get("water_liters", optimizer_plan.get("total_water_cap_l"))
            if any(x is not None for x in (b, c, w)):
                resource_constraints = {
                    "available_budget_inr": float(b) if b is not None else None,
                    "available_crew": int(c) if c is not None else None,
                    "available_water_l": float(w) if w is not None else None,
                }

        # 4. Set up resource tracking
        available_budget = None
        available_crew = None
        available_water = None
        constraints_active = False

        if resource_constraints:
            available_budget = resource_constraints.get("available_budget_inr")
            available_crew = resource_constraints.get("available_crew")
            available_water = resource_constraints.get("available_water_l")
            if any(x is not None for x in (available_budget, available_crew, available_water)):
                constraints_active = True

        rem_budget = float(available_budget) if available_budget is not None else None
        rem_crew = int(available_crew) if available_crew is not None else None
        rem_water = float(available_water) if available_water is not None else None

        spent_budget = 0.0
        spent_crew = 0
        spent_water = 0.0

        # 5. Sort candidates by priority (critical > high > medium > low), then descending risk score
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        candidates.sort(key=lambda c: (
            priority_order.get(c.get("priority", "medium"), 9),
            -(c.get("risk_score") or 0.0)
        ))

        # 6. Evaluate each candidate against duplicate prevention & resource caps
        accepted_recommendations: List[Dict[str, Any]] = []
        skipped_duplicates: List[Dict[str, Any]] = []
        skipped_resource_constrained: List[Dict[str, Any]] = []
        seen_batch_keys: set = set()

        for cand in candidates:
            w_id = cand["ward_id"]
            a_type = cand["action_type"]

            # Check duplicate against existing unresolved actions
            dup = check_duplicate_unresolved_action(store, w_id, a_type, seen_batch_keys)
            if dup:
                skipped_duplicates.append({
                    "ward_id": w_id,
                    "ward_name": cand["ward_name"],
                    "action_type": a_type,
                    "priority": cand["priority"],
                    "existing_action_id": dup["action_id"],
                    "existing_status": dup["status"],
                    "reason": dup["reason"],
                })
                continue

            # Check resource constraints if active and enforced
            cost = cand["required_resources"].get("cost_inr", 0.0)
            crew = cand["required_resources"].get("crew_required", 0)
            water = cand["required_resources"].get("water_required_l", 0.0)

            if constraints_active:
                exceeded_reasons = []
                if rem_budget is not None and cost > rem_budget:
                    exceeded_reasons.append(f"budget (required INR {cost:,.0f}, remaining INR {rem_budget:,.0f})")
                if rem_crew is not None and crew > rem_crew:
                    exceeded_reasons.append(f"crew (required {crew}, remaining {rem_crew})")
                if rem_water is not None and water > rem_water:
                    exceeded_reasons.append(f"water (required {water:,.0f}L, remaining {rem_water:,.0f}L)")

                if exceeded_reasons and enforce_resource_constraints:
                    skipped_resource_constrained.append({
                        "ward_id": w_id,
                        "ward_name": cand["ward_name"],
                        "action_type": a_type,
                        "priority": cand["priority"],
                        "required_resources": cand["required_resources"],
                        "remaining_at_evaluation": {
                            "budget_inr": rem_budget,
                            "crew": rem_crew,
                            "water_l": rem_water,
                        },
                        "reason": f"Skipped due to resource constraint: exceeds available {', '.join(exceeded_reasons)}.",
                    })
                    continue

                # Allocate resources
                if rem_budget is not None:
                    rem_budget -= cost
                    spent_budget += cost
                if rem_crew is not None:
                    rem_crew -= crew
                    spent_crew += crew
                if rem_water is not None:
                    rem_water -= water
                    spent_water += water

            # Mark key as seen in this batch
            seen_batch_keys.add((w_id, a_type))

            # Store action record with status 'proposed'
            if create_in_store:
                action_record = store.create_action(
                    ward_id=w_id,
                    ward_name=cand["ward_name"],
                    action_type=a_type,
                    priority=cand["priority"],
                    reason=cand["reason"],
                    required_resources=cand["required_resources"],
                    related_hazard=cand["related_hazard"],
                    risk_score=cand["risk_score"],
                    source=cand["source"],
                )
                action_record["rule_id"] = cand.get("rule_id")
                accepted_recommendations.append(action_record)
            else:
                simulated_record = dict(cand)
                simulated_record["status"] = "proposed"
                accepted_recommendations.append(simulated_record)

        return {
            "status": "SUCCESS",
            "advisory": HUMAN_APPROVAL_NOTICE,
            "total_recommendations": len(accepted_recommendations),
            "recommendations": accepted_recommendations,
            "skipped_duplicates_count": len(skipped_duplicates),
            "skipped_duplicates": skipped_duplicates,
            "skipped_resource_constrained_count": len(skipped_resource_constrained),
            "skipped_resource_constrained": skipped_resource_constrained,
            "resource_summary": {
                "constraints_enforced": bool(constraints_active and enforce_resource_constraints),
                "initial_resources": {
                    "budget_inr": available_budget,
                    "crew": available_crew,
                    "water_l": available_water,
                },
                "consumed_resources": {
                    "budget_inr": spent_budget,
                    "crew": spent_crew,
                    "water_l": spent_water,
                },
                "remaining_resources": {
                    "budget_inr": rem_budget if available_budget is not None else None,
                    "crew": rem_crew if available_crew is not None else None,
                    "water_l": rem_water if available_water is not None else None,
                },
            },
            "rules_summary": {
                "total_rules_defined": len(self.rules),
                "thresholds_applied": dict(self.thresholds),
                "candidates_evaluated": len(candidates),
                "recommendations_accepted": len(accepted_recommendations),
            },
        }


def generate_rule_based_recommendations(
    climate_risk_data: Optional[Dict[str, Any]] = None,
    optimizer_plan: Optional[Dict[str, Any]] = None,
    resource_constraints: Optional[Dict[str, Any]] = None,
    thresholds: Optional[Dict[str, float]] = None,
    store: Optional[ActionStore] = None,
    create_in_store: bool = True,
    enforce_resource_constraints: bool = True,
) -> Dict[str, Any]:
    """
    Public convenience function to generate rule-based recommendations
    using existing risk outputs and Optimizer plans.
    """
    engine = RuleBasedRecommendationEngine(thresholds=thresholds)
    return engine.generate_recommendations(
        climate_risk_data=climate_risk_data,
        optimizer_plan=optimizer_plan,
        resource_constraints=resource_constraints,
        store=store,
        create_in_store=create_in_store,
        enforce_resource_constraints=enforce_resource_constraints,
    )

