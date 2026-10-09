"""
ClimateShield - Explainable Multi-Hazard Intervention Engine for Ahmedabad
Generates, ranks, and optimizes hazard-matched interventions under resource constraints.

Mathematical & Methodological Foundations:
=========================================
1. Multi-Hazard Intervention Catalog:
   Supports Heat, Pluvial Flooding/Waterlogging, and Potable Water Shortage interventions.
   Explicitly catalogs unit cost assumptions, required staff, equipment, water, lead times,
   and expected impact uncertainty intervals.

2. Prioritization & Composite Scoring Formulation:
   Composite Priority Score S(w, a) balances five transparent, documented criteria:
     S(w, a) = 0.35 * [Delta_R(w, a) * (1 + alpha * V_w^2)]
             + 0.25 * Urgency(w, a)
             + 0.20 * CostEfficiency(w, a)
             + 0.10 * Feasibility(a)
             + 0.10 * VulnerableCoverage(w, a)
   Where:
     - Delta_R(w, a): Expected risk reduction points, subject to diminishing returns.
     - alpha in [0.0, 1.0]: Configurable equity preference slider.
     - V_w in [0.0, 1.0]: Ward baseline vulnerability index.
     - Urgency: Hazard intensity scaled with imminent danger and compound hotspot flags.
     - CostEfficiency: Risk reduction points per 10,000 INR.
     - Feasibility: Resource footprint penalty (staff and water draw).
     - VulnerableCoverage: Normalized population reached in vulnerable demographic cohorts.

3. Diminishing Returns & Anti-Double-Counting Submodular Model:
   To prevent double-counting when multiple interventions address the same hazard H in ward w:
     Delta_R_eff(w, a, k) = Delta_R_nom(a) * max(0.15, 1.0 - (Accum_Red(w, H) / max(Hazard_Score(w, H), 1.0)))
   Cumulative risk reduction for any hazard is strictly bounded by the ward's actual hazard score.

4. Efficiency vs. Equity Trade-Off Analysis:
   Evaluates allocations under pure efficiency (alpha = 0.0) vs. maximum equity (alpha = 1.0)
   to quantify the opportunity cost (risk reduction points traded off to increase protection
   for informal settlements and vulnerable residents).

5. Advisory Governance & Non-Validation Disclosure:
   All outputs carry explicit PENDING_HUMAN_APPROVAL status. Road closures are gated strictly
   at waterlogging >= 70.0. Assumed costs, simulated impacts, and unobserved proxies are
   transparently labeled.
"""

from typing import Dict, List, Any, Optional
import math
from datetime import datetime, timezone

# Reuse existing optimizer components
from backend.optimizer import (
    solve_resource_allocation,
    COST_MODEL_LABEL,
    BENEFIT_MODEL_LABEL,
    HUMAN_APPROVAL_NOTICE
)

# -------------------------------------------------------------
# DATA PROVENANCE LABELS & METHODOLOGY DOCUMENTATION
# -------------------------------------------------------------
PROVENANCE_LABELS = {
    "MEASURED_INPUT": "MEASURED_OR_FORECAST_OBSERVATION (e.g., Open-Meteo weather / rain data)",
    "ESTIMATED_IMPACT": "ESTIMATED_SIMULATED_RISK_REDUCTION (Algorithmically computed benefit points)",
    "DEMONSTRATION_ASSUMPTION": "DEMONSTRATION_ASSUMPTION (Configurable municipal cost/resource schedule)",
    "STATUS": "ADVISORY_PENDING_HUMAN_SIGN_OFF"
}

METHODOLOGY_DOCUMENTATION = {
    "scoring_formula": "Composite Priority Score S = 0.35 * (Delta_R * EquityBoost) + 0.25 * Urgency + 0.20 * CostEfficiency + 0.10 * Feasibility + 0.10 * Coverage",
    "equity_multiplier_formula": "EquityBoost = 1.0 + (alpha * V_w^2), where alpha in [0.0, 1.0] and V_w is ward vulnerability",
    "diminishing_returns_formula": "Delta_R_eff = Delta_R_base * max(0.15, 1.0 - (Accumulated_Hazard_Reduction / max(Hazard_Score, 1.0)))",
    "constraints_enforced": [
        "Monetary Budget Limit (INR)",
        "Available Staff Personnel Limit (Crew Count)",
        "Water Allocation Cap (Liters)",
        "Global Intervention Fleet / Capacity Limits",
        "Per-Ward Intervention Limits (after deducting existing deployments)",
        "Strict Road Closure Threshold (waterlogging >= 70.0)"
    ],
    "scientific_limitations": [
        "Unit costs represent municipal demonstration schedules and should be calibrated with local procurement tenders.",
        "Population figures are baseline spatial proxies; real-time census data is unobserved.",
        "Averted damage points are simulated indices rather than clinical mortality or financial loss figures."
    ]
}

# -------------------------------------------------------------
# SUPPORTED MULTI-HAZARD INTERVENTIONS CATALOG
# -------------------------------------------------------------
INTERVENTIONS_CATALOG: Dict[str, Dict[str, Any]] = {
    # ------------------ HEAT INTERVENTIONS ------------------
    "cooling_center": {
        "id": "cooling_center",
        "name": "Cooling-Centre Deployment / Activation",
        "intervention_type": "PHYSICAL_REFUGE_AND_COOLING",
        "related_hazard": "heat",
        "category": "heat",
        "unit_cost_inr": 50000.0,
        "cost_assumptions": "Assumed municipal air-conditioned facility activation, daily power, and nurse staffing (₹50,000/day).",
        "crew_required": 4,
        "equipment_required": ["Air Conditioning Chillers", "Clinical Heatstroke Triage Cots", "ORS Hydration Supplies", "Backup Diesel Genset"],
        "water_required_l": 500.0,
        "base_risk_reduction": 85.0,
        "max_per_ward": 2,
        "global_capacity_limit": 15,
        "trigger_threshold": 45.0,
        "lead_time": "2-4 hours",
        "urgency_baseline": "HIGH",
        "people_reached_factor": 0.045,  # Reaches approx 4.5% of ward vulnerable population per center
        "impact_range_factors": {"min": 0.80, "expected": 1.0, "max": 1.25},
        "vulnerable_weights": {"slum_dwellers": 0.40, "outdoor_laborers": 0.20, "elderly_infants": 0.40},
        "reason_template": "Critical heat stress. Activates air-conditioned public refuge with rehydration, shade, and clinical triage for elderly and slum residents.",
        "feasibility": "HIGH",
        "confidence_level": "HIGH",
        "confidence_score_pct": 85,
        "uncertainty_note": "Impact varies with resident proximity and willingness to evacuate uncooled tin-roof homes."
    },
    "drinking_water_point": {
        "id": "drinking_water_point",
        "name": "Drinking-Water Point / Hydration Kiosk Deployment",
        "intervention_type": "HYDRATION_DISTRIBUTION",
        "related_hazard": "heat",
        "category": "heat",
        "unit_cost_inr": 15000.0,
        "cost_assumptions": "Assumed municipal deployment cost for chilled dispensing station and ORS distribution (₹15,000/kiosk/day).",
        "crew_required": 2,
        "equipment_required": ["Chilled 1,000L Dispenser Cart", "WHO-Standard ORS Electrolyte Packets", "Biodegradable Paper Cups"],
        "water_required_l": 1200.0,
        "base_risk_reduction": 45.0,
        "max_per_ward": 4,
        "global_capacity_limit": 40,
        "trigger_threshold": 35.0,
        "lead_time": "30-60 mins",
        "urgency_baseline": "IMMEDIATE",
        "people_reached_factor": 0.035,
        "impact_range_factors": {"min": 0.85, "expected": 1.0, "max": 1.15},
        "vulnerable_weights": {"slum_dwellers": 0.30, "outdoor_laborers": 0.60, "elderly_infants": 0.10},
        "reason_template": "High outdoor heat exposure. Deploys chilled potable water kiosks and ORS rehydration packs along high-density informal laborer corridors.",
        "feasibility": "VERY_HIGH",
        "confidence_level": "HIGH",
        "confidence_score_pct": 90,
        "uncertainty_note": "Highly effective for active street laborers; relies on regular water tanker replenishment."
    },
    "shade_tree_deployment": {
        "id": "shade_tree_deployment",
        "name": "Pop-up Shade Canopies & Rapid Tree Shelter Deployment",
        "intervention_type": "PASSIVE_COOLING_AND_SHADE",
        "related_hazard": "heat",
        "category": "heat",
        "unit_cost_inr": 25000.0,
        "cost_assumptions": "Assumed procurement, anchoring, and maintenance of high-UV modular shade structures (₹25,000/site).",
        "crew_required": 3,
        "equipment_required": ["High-Albedo UV-Reflective Canopies", "Weighted Anchoring Blocks", "Misting Micro-Nozzles"],
        "water_required_l": 0.0,
        "base_risk_reduction": 35.0,
        "max_per_ward": 3,
        "global_capacity_limit": 25,
        "trigger_threshold": 35.0,
        "lead_time": "1-2 hours",
        "urgency_baseline": "MODERATE",
        "people_reached_factor": 0.025,
        "impact_range_factors": {"min": 0.75, "expected": 1.0, "max": 1.20},
        "vulnerable_weights": {"slum_dwellers": 0.20, "outdoor_laborers": 0.70, "elderly_infants": 0.10},
        "reason_template": "Intense solar radiation. Erects high-UV reflective modular shade canopies and potted green buffers at crowded bus terminals and labor nakas.",
        "feasibility": "VERY_HIGH",
        "confidence_level": "HIGH",
        "confidence_score_pct": 85,
        "uncertainty_note": "Reduces direct radiant temperature by 4-7°C; does not lower ambient air temperature without misting."
    },
    "heat_alerts_outreach": {
        "id": "heat_alerts_outreach",
        "name": "Community Heat Alerts & Outreach Campaign",
        "intervention_type": "PUBLIC_COMMUNICATION_AND_TRIAGE",
        "related_hazard": "heat",
        "category": "heat",
        "unit_cost_inr": 18000.0,
        "cost_assumptions": "Assumed operational outreach van fuel, loudspeaker equipment, and community health volunteer stipend (₹18,000/van/day).",
        "crew_required": 3,
        "equipment_required": ["Mobile Loudspeaker Vehicle", "First-Aid Instant Cold Packs", "Multilingual Vernacular Infographics", "Digital Thermometers"],
        "water_required_l": 200.0,
        "base_risk_reduction": 40.0,
        "max_per_ward": 2,
        "global_capacity_limit": 20,
        "trigger_threshold": 35.0,
        "lead_time": "30-60 mins",
        "urgency_baseline": "IMMEDIATE",
        "people_reached_factor": 0.080,
        "impact_range_factors": {"min": 0.70, "expected": 1.0, "max": 1.30},
        "vulnerable_weights": {"slum_dwellers": 0.50, "outdoor_laborers": 0.30, "elderly_infants": 0.20},
        "reason_template": "Thermal vulnerability in informal housing. Mobile loudspeaker vans and health teams distribute heat-stroke warnings and ice packs.",
        "feasibility": "HIGH",
        "confidence_level": "MODERATE",
        "confidence_score_pct": 75,
        "uncertainty_note": "Outreach reaches broad audiences but depends on resident behavioral adherence to heat safety advisories."
    },

    # ------------------ WATERLOGGING & FLOOD INTERVENTIONS ------------------
    "drainage_inspection_cleaning": {
        "id": "drainage_inspection_cleaning",
        "name": "Storm Drainage Inspection & Culvert Desilting",
        "intervention_type": "INFRASTRUCTURE_MAINTENANCE",
        "related_hazard": "flood/waterlogging",
        "category": "waterlogging",
        "unit_cost_inr": 30000.0,
        "cost_assumptions": "Assumed municipal suction jetting truck hire, culvert cleaning crew, and silt disposal (₹30,000/crew/shift).",
        "crew_required": 4,
        "equipment_required": ["High-Pressure Vacuum Jetting Truck", "Submersible Solids Trash Pump", "Hydraulic Silt Dredging Shovels"],
        "water_required_l": 0.0,
        "base_risk_reduction": 70.0,
        "max_per_ward": 3,
        "global_capacity_limit": 25,
        "trigger_threshold": 40.0,
        "lead_time": "1-3 hours",
        "urgency_baseline": "HIGH",
        "people_reached_factor": 0.060,
        "impact_range_factors": {"min": 0.75, "expected": 1.0, "max": 1.25},
        "vulnerable_weights": {"slum_dwellers": 0.50, "outdoor_laborers": 0.30, "elderly_infants": 0.20},
        "reason_template": "High pluvial waterlogging hazard. Rapid desilting crew clears choked stormwater culverts to restore discharge capacity and prevent underpass submergence.",
        "feasibility": "HIGH",
        "confidence_level": "HIGH",
        "confidence_score_pct": 85,
        "uncertainty_note": "Highly effective when executed ahead of peak rainfall; downstream interceptor bottlenecks can limit benefit."
    },
    "flood_warnings_communication": {
        "id": "flood_warnings_communication",
        "name": "Flood Warning Barricades & Multi-Channel Risk Communication",
        "intervention_type": "EARLY_WARNING_AND_TRAFFIC_ALERT",
        "related_hazard": "flood/waterlogging",
        "category": "waterlogging",
        "unit_cost_inr": 20000.0,
        "cost_assumptions": "Assumed automated water-level sensor warning sign, flashing barricades, and bulk geofenced SMS broadcast (₹20,000/site).",
        "crew_required": 2,
        "equipment_required": ["Reflective LED Hazard Flashers", "Ultrasonic Water-Level Visual Gauge", "Geofenced SMS Emergency Broadcast Gateway"],
        "water_required_l": 0.0,
        "base_risk_reduction": 55.0,
        "max_per_ward": 2,
        "global_capacity_limit": 30,
        "trigger_threshold": 45.0,
        "lead_time": "15-30 mins",
        "urgency_baseline": "IMMEDIATE",
        "people_reached_factor": 0.075,
        "impact_range_factors": {"min": 0.80, "expected": 1.0, "max": 1.20},
        "vulnerable_weights": {"slum_dwellers": 0.30, "outdoor_laborers": 0.50, "elderly_infants": 0.20},
        "reason_template": "Flash pooling danger. Deploys audible alert sirens, automated rising-water flashers, and localized SMS alerts to commuters.",
        "feasibility": "VERY_HIGH",
        "confidence_level": "HIGH",
        "confidence_score_pct": 88,
        "uncertainty_note": "Significantly curbs accidental vehicle submergence; requires prompt coordination with traffic control."
    },
    "road_closure_recommendation": {
        "id": "road_closure_recommendation",
        "name": "Emergency Inundation Road-Closure Recommendation",
        "intervention_type": "TRAFFIC_RESTRICTION",
        "related_hazard": "flood/waterlogging",
        "category": "waterlogging",
        "unit_cost_inr": 12000.0,
        "cost_assumptions": "Assumed traffic diversion barriers, warning signboards, and joint police marshal posting (₹12,000/closure/point).",
        "crew_required": 4,
        "equipment_required": ["Heavy-Duty Steel Barricades", "Variable Message Directional Signs", "Safety Flares and Traffic Cones"],
        "water_required_l": 0.0,
        "base_risk_reduction": 80.0,
        "max_per_ward": 1,
        "global_capacity_limit": 8,
        "trigger_threshold": 70.0,  # Strictly gated at waterlogging >= 70.0
        "lead_time": "15-30 mins",
        "urgency_baseline": "IMMEDIATE",
        "people_reached_factor": 0.050,
        "impact_range_factors": {"min": 0.85, "expected": 1.0, "max": 1.15},
        "vulnerable_weights": {"slum_dwellers": 0.30, "outdoor_laborers": 0.40, "elderly_infants": 0.30},
        "reason_template": "CRITICAL SUBMERGENCE DANGER! Pluvial inundation exceeds safe vehicle thresholds (>0.5m). Strictly advisory recommendation for joint Traffic Police sign-off.",
        "feasibility": "MODERATE",
        "confidence_level": "HIGH",
        "confidence_score_pct": 92,
        "uncertainty_note": "Prevents catastrophic drowning/stalling; causes traffic rerouting congestion on secondary roads."
    },

    # ------------------ WATER SHORTAGE INTERVENTIONS ------------------
    "water_tanker_allocation": {
        "id": "water_tanker_allocation",
        "name": "Emergency Potable Water-Tanker Allocation",
        "intervention_type": "EMERGENCY_SUPPLY_TRANSPORT",
        "related_hazard": "water_shortage",
        "category": "water_shortage",
        "unit_cost_inr": 12000.0,
        "cost_assumptions": "Assumed municipal 5,000L certified potable tanker trip, fuel, driver, and water filling cost (₹12,000/trip).",
        "crew_required": 2,
        "equipment_required": ["5,000L Food-Grade Stainless Tanker", "Food-Safe Delivery Hoses", "Chlorine Residual Test Kit"],
        "water_required_l": 5000.0,
        "base_risk_reduction": 60.0,
        "max_per_ward": 3,
        "global_capacity_limit": 20,
        "trigger_threshold": 35.0,
        "lead_time": "1-2 hours",
        "urgency_baseline": "HIGH",
        "people_reached_factor": 0.030,
        "impact_range_factors": {"min": 0.80, "expected": 1.0, "max": 1.20},
        "vulnerable_weights": {"slum_dwellers": 0.60, "outdoor_laborers": 0.20, "elderly_infants": 0.20},
        "reason_template": "Acute drinking water deficit. Dispatches certified 5,000L municipal potable tankers directly to water-stressed informal settlement clusters.",
        "feasibility": "HIGH",
        "confidence_level": "HIGH",
        "confidence_score_pct": 88,
        "uncertainty_note": "Directly delivers lifeline water; requires distribution queue marshaling to prevent crowding."
    },
    "drinking_water_distribution": {
        "id": "drinking_water_distribution",
        "name": "Communal Static Storage & Potable Water Distribution Tank",
        "intervention_type": "STATIC_BUFFER_STORAGE",
        "related_hazard": "water_shortage",
        "category": "water_shortage",
        "unit_cost_inr": 32000.0,
        "cost_assumptions": "Assumed 5,000L food-grade bladder tank hardware procurement, installation, and chlorine dosing (₹32,000/site).",
        "crew_required": 4,
        "equipment_required": ["5,000L Collapsible TPU Bladder Tank", "Multi-Tap Distribution Manifold", "Solar Water Pump"],
        "water_required_l": 5000.0,
        "base_risk_reduction": 70.0,
        "max_per_ward": 2,
        "global_capacity_limit": 12,
        "trigger_threshold": 45.0,
        "lead_time": "3-5 hours",
        "urgency_baseline": "HIGH",
        "people_reached_factor": 0.040,
        "impact_range_factors": {"min": 0.80, "expected": 1.0, "max": 1.25},
        "vulnerable_weights": {"slum_dwellers": 0.70, "outdoor_laborers": 0.10, "elderly_infants": 0.20},
        "reason_template": "Zero-buffer community zone. Installs rapid-deployment static food-grade community bladder tanks to ensure reliable 24/7 lifeline access.",
        "feasibility": "HIGH",
        "confidence_level": "MODERATE",
        "confidence_score_pct": 82,
        "uncertainty_note": "Provides continuous buffer storage; requires ongoing daily tanker refills."
    },
    "vulnerable_community_prioritization": {
        "id": "vulnerable_community_prioritization",
        "name": "Smart Valve Flow Prioritization for Vulnerable Sectors",
        "intervention_type": "NETWORK_HYDRAULIC_REDISTRIBUTION",
        "related_hazard": "water_shortage",
        "category": "water_shortage",
        "unit_cost_inr": 22000.0,
        "cost_assumptions": "Assumed hydraulic crew field shift, motorized telemetry valve adjustments, and terminal pressure monitoring (₹22,000/zone).",
        "crew_required": 3,
        "equipment_required": ["SCADA Network Pressure Recorders", "Hydraulic Flow Throttling Actuators", "Pipe Acoustic Leak Detectors"],
        "water_required_l": 0.0,
        "base_risk_reduction": 65.0,
        "max_per_ward": 2,
        "global_capacity_limit": 15,
        "trigger_threshold": 40.0,
        "lead_time": "1-2 hours",
        "urgency_baseline": "HIGH",
        "people_reached_factor": 0.070,
        "impact_range_factors": {"min": 0.75, "expected": 1.0, "max": 1.20},
        "vulnerable_weights": {"slum_dwellers": 0.50, "outdoor_laborers": 0.20, "elderly_infants": 0.30},
        "reason_template": "Severe terminal line pressure drop. Throttles non-essential commercial feeder lines and boosts pressure to maintain CPHEEO lifeline supply.",
        "feasibility": "HIGH",
        "confidence_level": "HIGH",
        "confidence_score_pct": 86,
        "uncertainty_note": "Rebalances municipal piped flow without consuming additional water; depends on feeder pipe integrity."
    }
}

# Alias mapping between optimizer.py and intervention_engine.py IDs
ALIASES = {
    "hydration_kiosk": "drinking_water_point",
    "shade_canopy": "shade_tree_deployment",
    "heat_awareness_outreach": "heat_alerts_outreach",
    "flood_warning_barricade": "flood_warnings_communication",
    "emergency_road_closure": "road_closure_recommendation",
    "water_tanker_dispatch": "water_tanker_allocation",
    "communal_storage_tank": "drinking_water_distribution",
    "supply_prioritization_rationing": "vulnerable_community_prioritization"
}
REVERSE_ALIASES = {v: k for k, v in ALIASES.items()}


class InterventionEngine:
    """
    Explainable Multi-Hazard Intervention Engine for Ahmedabad.
    Generates, ranks, and optimizes interventions under budget, crew, water,
    and capacity limits, with explicit anti-double-counting submodularity
    and efficiency-vs-equity trade-off analysis.
    """

    def __init__(self, catalog: Optional[Dict[str, Dict[str, Any]]] = None):
        self.catalog = catalog or INTERVENTIONS_CATALOG

    def _normalize_ward_record(self, ward: Dict[str, Any]) -> Dict[str, Any]:
        """Normalizes ward record across possible schema variations."""
        w_id = str(ward.get("id", ward.get("canonical_id", ward.get("ward_id", "W1"))))
        w_name = ward.get("name", ward.get("official_name", ward.get("ward_name", f"Ward {w_id}")))
        vuln = float(ward.get("vulnerability", ward.get("baseline_heat_risk", 0.70)))
        
        # Extract hazard scores
        heat_score = ward.get("heat_risk_score")
        if heat_score is None and isinstance(ward.get("heat_risk"), dict):
            heat_score = ward["heat_risk"].get("score")
        heat_score = float(heat_score) if heat_score is not None else 50.0

        # Handle missing water data without silently treating it as zero risk (Requirement 6)
        water_score = ward.get("water_risk_score")
        is_water_missing = False
        if water_score is None:
            if isinstance(ward.get("water_risk"), dict):
                water_score = ward["water_risk"].get("score")
            elif "water_risk" not in ward and "water_risk_score" not in ward:
                is_water_missing = True

        if water_score is None or is_water_missing:
            # Conservative non-zero hydrology prior based on vulnerability and citywide baseline
            water_score = round(35.0 + (vuln * 15.0), 1)
            water_prov = "ESTIMATED_HYDROLOGY_PRIOR (water data missing; non-zero default applied)"
        else:
            water_score = float(water_score)
            water_prov = "MEASURED_OR_SIMULATED_WATER_OBSERVATION"

        wl_score = ward.get("waterlogging_score")
        if wl_score is None and isinstance(ward.get("water_risk"), dict):
            wl_score = ward["water_risk"].get("waterlogging_score")
        if wl_score is None:
            wl_score = round(30.0 + (vuln * 15.0), 1)
        else:
            wl_score = float(wl_score)

        ws_score = ward.get("water_shortage_score")
        if ws_score is None and isinstance(ward.get("water_risk"), dict):
            ws_score = ward["water_risk"].get("water_shortage_score")
        if ws_score is None:
            ws_score = round(30.0 + (vuln * 12.0), 1)
        else:
            ws_score = float(ws_score)

        # Population
        pop = ward.get("population", ward.get("exposed_population", 100000))
        pop = int(pop) if pop is not None else 100000

        # Provenance indicator
        prov = ward.get("data_provenance", water_prov)

        return {
            "id": w_id,
            "name": w_name,
            "vulnerability": vuln,
            "population": pop,
            "heat_risk_score": heat_score,
            "water_risk_score": water_score,
            "waterlogging_score": wl_score,
            "water_shortage_score": ws_score,
            "data_provenance": prov,
            "is_compound_hotspot": bool(ward.get("is_compound_hotspot", (heat_score >= 50.0 and water_score >= 50.0)))
        }

    def generate_candidate_interventions(
        self,
        wards: List[Dict[str, Any]],
        existing_interventions: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        1. Identifies suitable interventions for each ward based on hazard thresholds.
        2. Deducts existing interventions so already-deployed resources are not duplicated.
        3. Enforces road-closure threshold (strictly waterlogging >= 70.0).
        4. Populates full 11-field candidate schema.
        """
        existing_map: Dict[str, Dict[str, int]] = {}
        if existing_interventions:
            for ex in existing_interventions:
                w_id = str(ex.get("ward_id", ex.get("id", "")))
                a_id = str(ex.get("action_id", ex.get("intervention_id", "")))
                canon_a_id = ALIASES.get(a_id, a_id)
                units = int(ex.get("units", 1))
                if w_id not in existing_map:
                    existing_map[w_id] = {}
                existing_map[w_id][canon_a_id] = existing_map[w_id].get(canon_a_id, 0) + units

        candidates: List[Dict[str, Any]] = []

        for raw_ward in wards:
            w = self._normalize_ward_record(raw_ward)
            w_id = w["id"]

            for a_id, det in self.catalog.items():
                cat = det["category"]
                thresh = det["trigger_threshold"]

                # Determine ward hazard relevant to this intervention
                if cat == "heat":
                    hazard_score = w["heat_risk_score"]
                    rel_hazard = "heat"
                elif cat == "waterlogging":
                    hazard_score = w["waterlogging_score"]
                    rel_hazard = "flood/waterlogging"
                elif cat == "water_shortage":
                    hazard_score = w["water_shortage_score"]
                    rel_hazard = "water_shortage"
                else:
                    hazard_score = max(w["heat_risk_score"], w["water_risk_score"])
                    rel_hazard = "multi_hazard"

                # Gate check: Does ward hazard meet the trigger threshold?
                if hazard_score < thresh:
                    continue

                # Hard safety gate: Road closure strictly requires waterlogging >= 70.0
                if a_id == "road_closure_recommendation" and w["waterlogging_score"] < 70.0:
                    continue

                # Check existing interventions in this ward
                already_deployed = existing_map.get(w_id, {}).get(a_id, 0)
                remaining_capacity = max(0, det["max_per_ward"] - already_deployed)

                if remaining_capacity <= 0:
                    continue

                # Impact range calculation based on hazard
                h_norm = hazard_score / 100.0
                base_red = det["base_risk_reduction"] * h_norm
                factors = det.get("impact_range_factors", {"min": 0.8, "expected": 1.0, "max": 1.2})
                exp_min = round(base_red * factors["min"], 2)
                exp_mean = round(base_red * factors["expected"], 2)
                exp_max = round(base_red * factors["max"], 2)

                # Estimated people reached based on ward population and vulnerability
                reach_factor = det.get("people_reached_factor", 0.04)
                reached_count = int(max(500, w["population"] * reach_factor * (1.0 + w["vulnerability"])))

                # Imminent urgency determination
                is_imminent = (hazard_score >= 70.0) or (w["is_compound_hotspot"] and hazard_score >= 50.0)
                urgency_tier = "IMMEDIATE" if is_imminent else det.get("urgency_baseline", "HIGH")

                candidates.append({
                    "intervention_id": a_id,
                    "action_id": a_id,
                    "intervention_type": det.get("intervention_type", "MUNICIPAL_INTERVENTION"),
                    "action_name": det["name"],
                    "ward_id": w_id,
                    "ward_name": w["name"],
                    "ward_vulnerability": w["vulnerability"],
                    "ward_population": w["population"],
                    "is_compound_hotspot": w["is_compound_hotspot"],
                    "target_ward": {
                        "ward_id": w_id,
                        "ward_name": w["name"],
                        "vulnerability": w["vulnerability"],
                        "population": w["population"],
                        "is_compound_hotspot": w["is_compound_hotspot"]
                    },
                    "related_hazard": rel_hazard,
                    "category": cat,
                    "hazard_score": hazard_score,
                    "estimated_cost": {
                        "unit_cost_inr": det["unit_cost_inr"],
                        "cost_assumptions": det.get("cost_assumptions", det.get("assumptions_note", "Standard municipal cost schedule."))
                    },
                    "unit_cost_inr": det["unit_cost_inr"],
                    "required_resources": {
                        "staff_personnel": det["crew_required"],
                        "equipment": det.get("equipment_required", []),
                        "water_liters": det["water_required_l"],
                        "max_units_deployable": remaining_capacity
                    },
                    "crew_required_per_unit": det["crew_required"],
                    "water_required_per_unit_l": det["water_required_l"],
                    "expected_impact_range": {
                        "min_risk_reduction": exp_min,
                        "expected_risk_reduction": exp_mean,
                        "max_risk_reduction": exp_max,
                        "evidence_note": det.get("uncertainty_note", "Simulated benefit.")
                    },
                    "base_risk_reduction": det["base_risk_reduction"],
                    "expected_risk_reduction_points": exp_mean,
                    "estimated_people_reached": {
                        "estimated_count": reached_count,
                        "basis": f"Ward population ({w['population']:,}) x reach factor ({reach_factor*100:.1f}%) adjusted for vulnerability ({w['vulnerability']:.2f})"
                    },
                    "lead_time_and_urgency": {
                        "lead_time": det.get("lead_time", "1-2 hours"),
                        "urgency": urgency_tier,
                        "is_imminent_danger": is_imminent
                    },
                    "max_units_deployable": remaining_capacity,
                    "already_deployed_units": already_deployed,
                    "global_capacity_limit": det.get("global_capacity_limit", 50),
                    "vulnerable_weights": det["vulnerable_weights"],
                    "reason_template": det["reason_template"],
                    "feasibility": det.get("feasibility", "HIGH"),
                    "data_quality_and_uncertainty": {
                        "confidence_level": det.get("confidence_level", "HIGH"),
                        "confidence_score_pct": det.get("confidence_score_pct", 85),
                        "data_sources": ["Open-Meteo Weather API", "Ahmedabad Ward Spatial Boundary GeoJSON"],
                        "unobserved_proxies": ["Real-time storm pipe ultrasonic flow meters unobserved in public APIs"],
                        "uncertainty_interval": f"[{exp_min} - {exp_max}] points"
                    }
                })

        return candidates

    def rank_candidate_interventions(
        self,
        candidates: List[Dict[str, Any]],
        equity_slider: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Ranks candidate interventions across five transparent criteria:
        1. Expected Risk Reduction: base reduction * (hazard / 100)
        2. Urgency: hazard score * (1.35 if hazard >= 75) * (1.20 if compound hotspot)
        3. Cost-Efficiency: risk reduction / (cost / 10000)
        4. Feasibility: staff & water footprint penalty
        5. Vulnerable Population Coverage: reached count * vulnerability * cohort weight
        """
        ranked = []
        for cand in candidates:
            tw = cand["target_ward"]
            vuln = tw["vulnerability"]
            pop = tw["population"]
            cost = cand["unit_cost_inr"]
            crew = cand["crew_required_per_unit"]
            water = cand["water_required_per_unit_l"]
            exp_risk_red = cand["expected_risk_reduction_points"]
            h_score = cand["hazard_score"]

            # 1. Urgency: Higher priority for severe (>= 75) and compound hotspots
            severity_mult = 1.35 if h_score >= 75.0 else 1.0
            compound_mult = 1.20 if tw["is_compound_hotspot"] else 1.0
            urgency_score = min(100.0, round(h_score * severity_mult * compound_mult, 1))

            # 2. Cost-Efficiency (Benefit points per 10k INR)
            cost_efficiency = round((exp_risk_red / (cost / 10000.0)), 2)

            # 3. Feasibility Score: Resource draw penalty
            feasibility_penalty = (crew * 2.0) + (water / 1000.0 * 1.5)
            feasibility_score = max(10.0, round(100.0 - feasibility_penalty, 1))

            # 4. Vulnerable Population Coverage
            people_reached = cand["estimated_people_reached"]["estimated_count"]
            coverage_score = min(100.0, round(people_reached / 200.0, 1))

            # 5. Equity Boost: Quadratic amplification for vulnerable wards
            # When equity_slider=0 (efficiency), boost=1.0. When equity_slider=1, boost=1 + vuln^2
            equity_boost = 1.0 + (equity_slider * (vuln ** 2))

            # Composite Priority Score Formulation
            composite_score = round(
                (exp_risk_red * 0.35 * equity_boost) +
                (urgency_score * 0.25) +
                (cost_efficiency * 0.20) +
                (feasibility_score * 0.10) +
                (coverage_score * 0.10),
                2
            )

            # Plain-English explainable rationale
            compound_flag_str = " [Compound Hotspot Alert]" if tw["is_compound_hotspot"] else ""
            explanation = (
                f"Recommended for {tw['ward_name']}{compound_flag_str} facing {cand['related_hazard']} "
                f"stress (Score: {h_score:.1f}/100, Urgency: {cand['lead_time_and_urgency']['urgency']}). "
                f"{cand['reason_template']} "
                f"Estimated impact: {exp_risk_red} risk reduction points reaching approximately {people_reached:,} "
                f"residents (Lead time: {cand['lead_time_and_urgency']['lead_time']})."
            )
            if cand["already_deployed_units"] > 0:
                explanation += f" ({cand['already_deployed_units']} active unit(s) already operational in this ward)."

            ranked.append({
                **cand,
                "priority_score": composite_score,
                "composite_priority_score": composite_score,
                "urgency_score": urgency_score,
                "cost_efficiency_score": cost_efficiency,
                "feasibility_score": feasibility_score,
                "reason_for_recommendation": explanation,
                "explanation": explanation
            })

        # Sort descending by priority score
        ranked.sort(key=lambda x: x["priority_score"], reverse=True)

        for idx, item in enumerate(ranked):
            item["priority_rank"] = idx + 1

        return ranked

    def _execute_knapsack_pass(
        self,
        norm_wards: List[Dict[str, Any]],
        ranked_candidates: List[Dict[str, Any]],
        budget_cap: float,
        crew_cap: int,
        water_cap: float,
        global_caps: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        Internal optimization pass incorporating diminishing marginal returns (anti-double-counting).
        """
        rem_budget = float(budget_cap)
        rem_crew = int(crew_cap)
        rem_water = float(water_cap)

        global_dispatched: Dict[str, int] = {a: 0 for a in self.catalog}
        ward_dispatched: Dict[str, Dict[str, int]] = {w["id"]: {a: 0 for a in self.catalog} for w in norm_wards}

        # Submodular tracking to avoid double-counting same hazard in same ward
        accumulated_hazard_reduction: Dict[str, Dict[str, float]] = {
            w["id"]: {"heat": 0.0, "flood/waterlogging": 0.0, "water_shortage": 0.0}
            for w in norm_wards
        }

        total_risk_red = 0.0
        hazard_spending = {"heat": 0.0, "waterlogging": 0.0, "water_shortage": 0.0}
        vulnerable_coverage = {"slum_dwellers": 0.0, "outdoor_laborers": 0.0, "elderly_infants": 0.0}

        allocated_recommendations = []
        unmet_candidates = []

        for cand in ranked_candidates:
            w_id = cand["target_ward"]["ward_id"]
            a_id = cand["intervention_id"]
            hazard_cat = cand["related_hazard"]
            h_score = cand["hazard_score"]
            cost = cand["unit_cost_inr"]
            crew = cand["crew_required_per_unit"]
            water = cand["water_required_per_unit_l"]
            max_units = cand["max_units_deployable"]

            units_to_dispatch = 0
            unit_effective_reductions = []

            while (
                units_to_dispatch < max_units and
                global_dispatched[a_id] < global_caps[a_id] and
                rem_budget >= cost and
                rem_crew >= crew and
                rem_water >= water
            ):
                # Apply diminishing marginal returns: discount based on already accumulated hazard reduction
                prior_accum = accumulated_hazard_reduction[w_id].get(hazard_cat, 0.0)
                diminishing_factor = max(0.15, 1.0 - (prior_accum / max(h_score, 1.0)))
                eff_reduction = round(cand["expected_risk_reduction_points"] * diminishing_factor, 2)

                # Cap total accumulated reduction at ward hazard score (cannot avert more risk than exists)
                if prior_accum + eff_reduction > h_score:
                    eff_reduction = max(0.0, round(h_score - prior_accum, 2))

                if eff_reduction <= 0.5:
                    # Saturation reached for this hazard in this ward; diminishing returns exhausted
                    break

                rem_budget -= cost
                rem_crew -= crew
                rem_water -= water
                units_to_dispatch += 1
                global_dispatched[a_id] += 1
                ward_dispatched[w_id][a_id] += 1

                accumulated_hazard_reduction[w_id][hazard_cat] = prior_accum + eff_reduction
                unit_effective_reductions.append(eff_reduction)

            if units_to_dispatch > 0:
                tot_cost = units_to_dispatch * cost
                tot_crew = units_to_dispatch * crew
                tot_water = units_to_dispatch * water
                tot_red = round(sum(unit_effective_reductions), 2)

                total_risk_red += tot_red
                spending_key = "waterlogging" if "waterlogging" in hazard_cat else ("water_shortage" if "shortage" in hazard_cat else "heat")
                hazard_spending[spending_key] += tot_cost

                # Vulnerable coverage
                people_reached = cand["estimated_people_reached"]["estimated_count"] * units_to_dispatch
                for cohort, weight in cand["vulnerable_weights"].items():
                    vulnerable_coverage[cohort] += people_reached * weight

                allocated_recommendations.append({
                    "priority_rank": cand["priority_rank"],
                    "intervention_id": a_id,
                    "action_id": a_id,
                    "intervention_type": cand["intervention_type"],
                    "action_name": cand["action_name"],
                    "target_ward": cand["target_ward"],
                    "ward_id": w_id,
                    "ward_name": cand["target_ward"]["ward_name"],
                    "related_hazard": cand["related_hazard"],
                    "category": cand["category"],
                    "priority_score": cand["priority_score"],
                    "units_allocated": units_to_dispatch,
                    "estimated_cost": {
                        "allocated_cost_inr": tot_cost,
                        "unit_cost_inr": cost,
                        "cost_assumptions": cand["estimated_cost"]["cost_assumptions"]
                    },
                    "estimated_cost_inr": tot_cost,
                    "required_resources": {
                        "crew_allocated": tot_crew,
                        "water_allocated_l": tot_water,
                        "equipment": cand["required_resources"]["equipment"]
                    },
                    "crew_required": tot_crew,
                    "water_required_l": tot_water,
                    "expected_impact_range": {
                        "min_risk_reduction": round(cand["expected_impact_range"]["min_risk_reduction"] * units_to_dispatch, 2),
                        "expected_risk_reduction": tot_red,
                        "max_risk_reduction": round(cand["expected_impact_range"]["max_risk_reduction"] * units_to_dispatch, 2),
                        "submodular_diminishing_discount_applied": True,
                        "evidence_note": cand["expected_impact_range"]["evidence_note"]
                    },
                    "expected_risk_reduction": tot_red,
                    "estimated_people_reached": {
                        "estimated_count": people_reached,
                        "basis": cand["estimated_people_reached"]["basis"]
                    },
                    "lead_time_and_urgency": cand["lead_time_and_urgency"],
                    "reason_for_recommendation": cand["reason_for_recommendation"],
                    "explanation": cand["reason_for_recommendation"],
                    "data_quality_and_uncertainty": cand["data_quality_and_uncertainty"],
                    "approval_status": "PENDING_HUMAN_APPROVAL",
                    "requires_human_signoff": True,
                    "approval_authority": "Municipal Commissioner / Incident Commander" if a_id != "road_closure_recommendation" else "Municipal Commissioner & Joint Traffic Police Authority",
                    "data_provenance": {
                        "cost": PROVENANCE_LABELS["DEMONSTRATION_ASSUMPTION"],
                        "benefit": PROVENANCE_LABELS["ESTIMATED_IMPACT"]
                    }
                })
            else:
                bottlenecks = []
                if rem_budget < cost:
                    bottlenecks.append("BUDGET_EXHAUSTED")
                if rem_crew < crew:
                    bottlenecks.append("CREW_EXHAUSTED")
                if rem_water < water:
                    bottlenecks.append("WATER_CAP_EXHAUSTED")
                if global_dispatched[a_id] >= global_caps[a_id]:
                    bottlenecks.append("INTERVENTION_CAPACITY_LIMIT_REACHED")
                if not bottlenecks:
                    bottlenecks.append("HAZARD_RISK_SATURATION_REACHED")

                unmet_candidates.append({
                    "ward_id": w_id,
                    "ward_name": cand["target_ward"]["ward_name"],
                    "intervention_id": a_id,
                    "action_name": cand["action_name"],
                    "related_hazard": cand["related_hazard"],
                    "bottlenecks": bottlenecks
                })

        return {
            "used_cost": budget_cap - rem_budget,
            "used_crew": crew_cap - rem_crew,
            "used_water": water_cap - rem_water,
            "rem_budget": rem_budget,
            "rem_crew": rem_crew,
            "rem_water": rem_water,
            "total_risk_red": round(total_risk_red, 2),
            "hazard_spending": hazard_spending,
            "vulnerable_coverage": {k: int(v) for k, v in vulnerable_coverage.items()},
            "global_dispatched": global_dispatched,
            "allocated_recommendations": allocated_recommendations,
            "unmet_candidates": unmet_candidates
        }

    def optimize_interventions(
        self,
        wards: List[Dict[str, Any]],
        total_budget_inr: float = 500000.0,
        total_crew_members: int = 40,
        total_water_cap_l: float = 30000.0,
        equity_slider: float = 0.5,
        intervention_capacity_limits: Optional[Dict[str, int]] = None,
        existing_interventions: Optional[List[Dict[str, Any]]] = None,
        include_tradeoff_analysis: bool = True
    ) -> Dict[str, Any]:
        """
        Executes multi-hazard optimization under resource constraints, anti-double-counting
        submodular returns, and produces an explainable trade-off analysis between pure efficiency
        and equity protection for vulnerable wards.
        """
        # Step 1: Normalize wards
        norm_wards = [self._normalize_ward_record(w) for w in wards]

        # Step 2: Generate candidate interventions
        candidates = self.generate_candidate_interventions(norm_wards, existing_interventions)

        # Step 3: Multi-criteria ranking using user-specified equity slider
        ranked_candidates = self.rank_candidate_interventions(candidates, equity_slider)

        # Step 4: Resolve global capacity limits
        caps = {a: det.get("global_capacity_limit", 50) for a, det in self.catalog.items()}
        if intervention_capacity_limits:
            caps.update(intervention_capacity_limits)

        # Step 5: Primary Optimization Pass
        primary = self._execute_knapsack_pass(
            norm_wards=norm_wards,
            ranked_candidates=ranked_candidates,
            budget_cap=total_budget_inr,
            crew_cap=total_crew_members,
            water_cap=total_water_cap_l,
            global_caps=caps
        )

        # Step 6: Efficiency vs. Equity Trade-off Analysis (Requirement 5)
        tradeoff_analysis = {}
        if include_tradeoff_analysis:
            # Efficiency benchmark (alpha = 0.0)
            eff_ranked = self.rank_candidate_interventions(candidates, equity_slider=0.0)
            eff_run = self._execute_knapsack_pass(norm_wards, eff_ranked, total_budget_inr, total_crew_members, total_water_cap_l, caps)

            # Maximum equity benchmark (alpha = 1.0)
            eq_ranked = self.rank_candidate_interventions(candidates, equity_slider=1.0)
            eq_run = self._execute_knapsack_pass(norm_wards, eq_ranked, total_budget_inr, total_crew_members, total_water_cap_l, caps)

            # Vulnerable ward coverage counts (wards with vulnerability >= 0.75)
            high_vuln_ids = {w["id"] for w in norm_wards if w["vulnerability"] >= 0.75}
            high_vuln_total = len(high_vuln_ids) or 1

            eff_vuln_wards = len({r["ward_id"] for r in eff_run["allocated_recommendations"] if r["ward_id"] in high_vuln_ids})
            cur_vuln_wards = len({r["ward_id"] for r in primary["allocated_recommendations"] if r["ward_id"] in high_vuln_ids})
            eq_vuln_wards = len({r["ward_id"] for r in eq_run["allocated_recommendations"] if r["ward_id"] in high_vuln_ids})

            opportunity_cost_pts = round(max(0.0, eff_run["total_risk_red"] - primary["total_risk_red"]), 2)

            tradeoff_analysis = {
                "equity_slider_setting": equity_slider,
                "efficiency_benchmark_risk_reduction": eff_run["total_risk_red"],
                "maximum_equity_benchmark_risk_reduction": eq_run["total_risk_red"],
                "current_solution_risk_reduction": primary["total_risk_red"],
                "opportunity_cost_risk_reduction_points": opportunity_cost_pts,
                "high_vulnerability_wards_served": {
                    "efficiency_mode": f"{eff_vuln_wards} / {high_vuln_total}",
                    "current_mode": f"{cur_vuln_wards} / {high_vuln_total}",
                    "maximum_equity_mode": f"{eq_vuln_wards} / {high_vuln_total}"
                },
                "tradeoff_explanation": (
                    f"At equity slider = {equity_slider:.2f}, the system trades off {opportunity_cost_pts} "
                    f"risk reduction points ({round(opportunity_cost_pts / max(1.0, eff_run['total_risk_red']) * 100, 1)}% of maximum theoretical efficiency) "
                    f"to allocate resources across {cur_vuln_wards} high-vulnerability informal settlement wards."
                )
            }

        # Step 7: Organize allocations by ward
        ward_allocations: Dict[str, Dict[str, Any]] = {}
        for w in norm_wards:
            w_id = w["id"]
            actions_in_ward = [r for r in primary["allocated_recommendations"] if r["ward_id"] == w_id]
            w_cost = sum(r["estimated_cost_inr"] for r in actions_in_ward)
            w_crew = sum(r["crew_required"] for r in actions_in_ward)
            w_water = sum(r["water_required_l"] for r in actions_in_ward)
            w_red = round(sum(r["expected_risk_reduction"] for r in actions_in_ward), 2)
            w_people = sum(r["estimated_people_reached"]["estimated_count"] for r in actions_in_ward)

            ward_allocations[w_id] = {
                "ward_id": w_id,
                "ward_name": w["name"],
                "vulnerability": w["vulnerability"],
                "population": w["population"],
                "hazard_summary": {
                    "heat_score": w["heat_risk_score"],
                    "waterlogging_score": w["waterlogging_score"],
                    "water_shortage_score": w["water_shortage_score"],
                    "is_compound_hotspot": w["is_compound_hotspot"]
                },
                "total_cost_inr": w_cost,
                "total_crew_allocated": w_crew,
                "total_water_allocated_l": w_water,
                "total_risk_reduction": w_red,
                "total_people_reached": w_people,
                "interventions_count": len(actions_in_ward),
                "interventions": actions_in_ward
            }

        is_infeasible = (len(primary["allocated_recommendations"]) == 0 and len(candidates) > 0)
        status_code = "CONSTRAINED_NO_ALLOCATION" if is_infeasible else ("NO_CANDIDATES_NEEDED" if len(candidates) == 0 else "OPTIMAL")

        return {
            "status": status_code,
            "is_feasible": not is_infeasible,
            "solver": "Submodular Diminishing-Returns Knapsack & Multi-Criteria Prioritization",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "infeasibility_notes": (
                "Available budget, crew, or water resources are insufficient to deploy any candidate interventions. "
                "Minimum single action requires ₹12,000 INR and 2 crew members."
            ) if is_infeasible else None,
            "methodology_and_governance": {
                "notice": HUMAN_APPROVAL_NOTICE,
                "approval_required": True,
                "labels": PROVENANCE_LABELS,
                "documentation": METHODOLOGY_DOCUMENTATION
            },
            "resource_summary": {
                "budget": {
                    "allocated_inr": primary["used_cost"],
                    "cap_inr": total_budget_inr,
                    "remaining_inr": primary["rem_budget"],
                    "utilization_pct": round(primary["used_cost"] / total_budget_inr * 100, 1) if total_budget_inr > 0 else 0.0,
                    "cost_model": COST_MODEL_LABEL
                },
                "crew": {
                    "allocated_members": primary["used_crew"],
                    "cap_members": total_crew_members,
                    "remaining_members": primary["rem_crew"],
                    "utilization_pct": round(primary["used_crew"] / total_crew_members * 100, 1) if total_crew_members > 0 else 0.0
                },
                "water": {
                    "allocated_liters": primary["used_water"],
                    "cap_liters": total_water_cap_l,
                    "remaining_liters": primary["rem_water"],
                    "utilization_pct": round(primary["used_water"] / total_water_cap_l * 100, 1) if total_water_cap_l > 0 else 0.0
                },
                "hazard_spending_breakdown_inr": primary["hazard_spending"],
                "global_intervention_capacity_utilization": {
                    a: {"dispatched": primary["global_dispatched"][a], "limit": caps[a]} for a in self.catalog
                }
            },
            "impact_summary": {
                "total_risk_reduction_achieved": primary["total_risk_red"],
                "total_interventions_dispatched": sum(primary["global_dispatched"].values()),
                "total_wards_covered": len([w for w in ward_allocations.values() if w["interventions_count"] > 0]),
                "total_people_reached": sum(r["estimated_people_reached"]["estimated_count"] for r in primary["allocated_recommendations"]),
                "vulnerable_population_coverage": primary["vulnerable_coverage"],
                "benefit_model": BENEFIT_MODEL_LABEL
            },
            "tradeoff_analysis": tradeoff_analysis,
            "ranked_recommendations": primary["allocated_recommendations"],
            "ward_allocations": ward_allocations,
            "unmet_needs_due_to_constraints": primary["unmet_candidates"][:10],
            "existing_interventions_accounted_for": len(existing_interventions) if existing_interventions else 0
        }

    def simulate_what_if_scenario(
        self,
        wards: List[Dict[str, Any]],
        simulated_budget_inr: float,
        simulated_crew_members: int,
        simulated_water_cap_l: float,
        simulated_equity_slider: float,
        simulated_capacity_limits: Optional[Dict[str, int]] = None,
        baseline_budget_inr: float = 500000.0,
        baseline_crew_members: int = 40,
        baseline_water_cap_l: float = 30000.0,
        baseline_equity_slider: float = 0.5,
        baseline_capacity_limits: Optional[Dict[str, int]] = None,
        existing_interventions: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Lightweight What-If Simulator:
        Compares a baseline resource allocation against a user-modified simulated scenario.
        Computes metric deltas, identifies wards and actions gaining or losing priority,
        displays uncertainty impact intervals, and synthesizes an explainable trade-off narrative.
        """
        norm_wards = [self._normalize_ward_record(w) for w in wards]

        # 1. Run Baseline Allocation
        baseline = self.optimize_interventions(
            wards=norm_wards,
            total_budget_inr=baseline_budget_inr,
            total_crew_members=baseline_crew_members,
            total_water_cap_l=baseline_water_cap_l,
            equity_slider=baseline_equity_slider,
            intervention_capacity_limits=baseline_capacity_limits,
            existing_interventions=existing_interventions,
            include_tradeoff_analysis=False
        )

        # 2. Run Simulated Allocation
        simulated = self.optimize_interventions(
            wards=norm_wards,
            total_budget_inr=simulated_budget_inr,
            total_crew_members=simulated_crew_members,
            total_water_cap_l=simulated_water_cap_l,
            equity_slider=simulated_equity_slider,
            intervention_capacity_limits=simulated_capacity_limits,
            existing_interventions=existing_interventions,
            include_tradeoff_analysis=False
        )

        # 3. Compute High-Level Metric Deltas
        base_res = baseline["resource_summary"]
        sim_res = simulated["resource_summary"]
        base_imp = baseline["impact_summary"]
        sim_imp = simulated["impact_summary"]

        delta_budget_allocated = round(sim_res["budget"]["allocated_inr"] - base_res["budget"]["allocated_inr"], 2)
        delta_crew_allocated = sim_res["crew"]["allocated_members"] - base_res["crew"]["allocated_members"]
        delta_water_allocated = round(sim_res["water"]["allocated_liters"] - base_res["water"]["allocated_liters"], 2)
        delta_risk_red = round(sim_imp["total_risk_reduction_achieved"] - base_imp["total_risk_reduction_achieved"], 2)
        pct_risk_red_change = round((delta_risk_red / max(1.0, base_imp["total_risk_reduction_achieved"])) * 100.0, 1)
        delta_people_reached = sim_imp["total_people_reached"] - base_imp["total_people_reached"]
        delta_wards_covered = sim_imp["total_wards_covered"] - base_imp["total_wards_covered"]

        # 4. Impact Uncertainty Ranges (Baseline vs Simulated)
        base_recs = baseline["ranked_recommendations"]
        sim_recs = simulated["ranked_recommendations"]

        base_min_impact = round(sum(r["expected_impact_range"]["min_risk_reduction"] for r in base_recs), 2)
        base_exp_impact = base_imp["total_risk_reduction_achieved"]
        base_max_impact = round(sum(r["expected_impact_range"]["max_risk_reduction"] for r in base_recs), 2)

        sim_min_impact = round(sum(r["expected_impact_range"]["min_risk_reduction"] for r in sim_recs), 2)
        sim_exp_impact = sim_imp["total_risk_reduction_achieved"]
        sim_max_impact = round(sum(r["expected_impact_range"]["max_risk_reduction"] for r in sim_recs), 2)

        uncertainty_bounds = {
            "baseline_risk_reduction": {"min": base_min_impact, "expected": base_exp_impact, "max": base_max_impact},
            "simulated_risk_reduction": {"min": sim_min_impact, "expected": sim_exp_impact, "max": sim_max_impact},
            "delta_risk_reduction_range": {
                "min_possible_delta": round(sim_min_impact - base_max_impact, 2),
                "expected_delta": delta_risk_red,
                "max_possible_delta": round(sim_max_impact - base_min_impact, 2),
                "confidence_note": "Uncertainty interval combines microclimate variability and response compliance."
            }
        }

        # 5. Ward-Level Priority & Resource Shifts
        base_wards_map = baseline["ward_allocations"]
        sim_wards_map = simulated["ward_allocations"]

        wards_gaining = []
        wards_losing = []
        wards_neutral = []

        for w_id, sim_w in sim_wards_map.items():
            base_w = base_wards_map.get(w_id, {})
            base_red = base_w.get("total_risk_reduction", 0.0)
            sim_red = sim_w.get("total_risk_reduction", 0.0)
            diff_red = round(sim_red - base_red, 2)
            diff_units = sim_w.get("interventions_count", 0) - base_w.get("interventions_count", 0)
            diff_cost = round(sim_w.get("total_cost_inr", 0.0) - base_w.get("total_cost_inr", 0.0), 2)

            ward_summary = {
                "ward_id": w_id,
                "ward_name": sim_w["ward_name"],
                "vulnerability": sim_w["vulnerability"],
                "risk_reduction_delta": diff_red,
                "interventions_delta": diff_units,
                "budget_delta_inr": diff_cost,
                "baseline_risk_reduction": base_red,
                "simulated_risk_reduction": sim_red
            }

            if diff_red > 0.5:
                wards_gaining.append(ward_summary)
            elif diff_red < -0.5:
                wards_losing.append(ward_summary)
            else:
                wards_neutral.append(ward_summary)

        wards_gaining.sort(key=lambda x: x["risk_reduction_delta"], reverse=True)
        wards_losing.sort(key=lambda x: x["risk_reduction_delta"])

        # 6. Action-Level Interventions Modified / Added / Dropped
        base_actions_dict: Dict[str, int] = {}
        for r in base_recs:
            key = f"{r['ward_id']}_{r['action_id']}"
            base_actions_dict[key] = base_actions_dict.get(key, 0) + r["units_allocated"]

        sim_actions_dict: Dict[str, int] = {}
        for r in sim_recs:
            key = f"{r['ward_id']}_{r['action_id']}"
            sim_actions_dict[key] = sim_actions_dict.get(key, 0) + r["units_allocated"]

        actions_added = []
        actions_removed = []
        actions_adjusted = []

        all_keys = set(base_actions_dict.keys()).union(set(sim_actions_dict.keys()))
        for key in all_keys:
            w_id, a_id = key.split("_", 1)
            b_cnt = base_actions_dict.get(key, 0)
            s_cnt = sim_actions_dict.get(key, 0)
            w_name = sim_wards_map.get(w_id, {}).get("ward_name", f"Ward {w_id}")
            a_name = self.catalog.get(a_id, {}).get("name", a_id)

            if b_cnt == 0 and s_cnt > 0:
                actions_added.append({
                    "ward_id": w_id, "ward_name": w_name,
                    "action_id": a_id, "action_name": a_name,
                    "units_added": s_cnt
                })
            elif b_cnt > 0 and s_cnt == 0:
                actions_removed.append({
                    "ward_id": w_id, "ward_name": w_name,
                    "action_id": a_id, "action_name": a_name,
                    "units_dropped": b_cnt
                })
            elif b_cnt != s_cnt:
                actions_adjusted.append({
                    "ward_id": w_id, "ward_name": w_name,
                    "action_id": a_id, "action_name": a_name,
                    "baseline_units": b_cnt, "simulated_units": s_cnt,
                    "net_change": s_cnt - b_cnt
                })

        # 7. Synthesize Explainable Trade-off Narrative
        narrative_points = []

        # Budget commentary
        budget_diff = simulated_budget_inr - baseline_budget_inr
        if budget_diff > 0:
            narrative_points.append(f"Budget expansion of +₹{budget_diff:,.0f} unlocked {len(actions_added)} new intervention deployment(s).")
        elif budget_diff < 0:
            narrative_points.append(f"Budget reduction of ₹{abs(budget_diff):,.0f} forced {len(actions_removed)} intervention drop(s).")

        # Crew commentary
        crew_diff = simulated_crew_members - baseline_crew_members
        if crew_diff < 0 and sim_res["crew"]["utilization_pct"] >= 95.0:
            narrative_points.append(f"Staff cap constrained to {simulated_crew_members} personnel created a field crew deployment bottleneck.")

        # Equity slider commentary
        equity_diff = simulated_equity_slider - baseline_equity_slider
        if abs(equity_diff) >= 0.1:
            if equity_diff > 0:
                narrative_points.append(
                    f"Higher equity preference ({simulated_equity_slider:.2f} vs {baseline_equity_slider:.2f}) redirected resources "
                    f"towards high-vulnerability informal settlements ({len(wards_gaining)} wards gained priority)."
                )
            else:
                narrative_points.append(
                    f"Lower equity preference ({simulated_equity_slider:.2f} vs {baseline_equity_slider:.2f}) shifted focus "
                    f"to maximum citywide efficiency (points per rupee)."
                )

        # Net impact commentary
        if delta_risk_red >= 0:
            narrative_points.append(f"Net simulated impact: +{delta_risk_red:.1f} risk reduction points (+{pct_risk_red_change:.1f}%) reaching {delta_people_reached:+,} additional residents.")
        else:
            narrative_points.append(f"Net simulated impact: {delta_risk_red:.1f} risk reduction points ({pct_risk_red_change:.1f}%) with {abs(delta_people_reached):,} fewer residents protected.")

        tradeoff_narrative = " ".join(narrative_points)

        return {
            "status": "SUCCESS",
            "simulation_mode": "WHAT_IF_COMPARATIVE_ANALYSIS",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "parameter_comparison": {
                "budget_inr": {"baseline": baseline_budget_inr, "simulated": simulated_budget_inr, "delta": budget_diff},
                "crew_members": {"baseline": baseline_crew_members, "simulated": simulated_crew_members, "delta": crew_diff},
                "water_cap_l": {"baseline": baseline_water_cap_l, "simulated": simulated_water_cap_l, "delta": simulated_water_cap_l - baseline_water_cap_l},
                "equity_slider": {"baseline": baseline_equity_slider, "simulated": simulated_equity_slider, "delta": round(equity_diff, 2)}
            },
            "metric_deltas": {
                "budget_allocated_delta_inr": delta_budget_allocated,
                "crew_allocated_delta": delta_crew_allocated,
                "water_allocated_delta_l": delta_water_allocated,
                "risk_reduction_delta_points": delta_risk_red,
                "risk_reduction_pct_change": pct_risk_red_change,
                "people_reached_delta": delta_people_reached,
                "wards_covered_delta": delta_wards_covered
            },
            "uncertainty_ranges": uncertainty_bounds,
            "tradeoff_narrative": tradeoff_narrative,
            "priority_shifts": {
                "wards_gaining_resources_count": len(wards_gaining),
                "wards_gaining_resources": wards_gaining[:5],
                "wards_losing_resources_count": len(wards_losing),
                "wards_losing_resources": wards_losing[:5],
                "wards_unchanged_count": len(wards_neutral)
            },
            "intervention_changes": {
                "actions_added": actions_added,
                "actions_removed": actions_removed,
                "actions_adjusted": actions_adjusted
            },
            "simulated_plan_summary": {
                "status": simulated["status"],
                "is_feasible": simulated["is_feasible"],
                "total_budget_allocated_inr": sim_res["budget"]["allocated_inr"],
                "total_crew_used": sim_res["crew"]["allocated_members"],
                "total_water_used_l": sim_res["water"]["allocated_liters"],
                "total_risk_reduction": sim_imp["total_risk_reduction_achieved"],
                "total_interventions_count": sim_imp["total_interventions_dispatched"],
                "total_people_reached": sim_imp["total_people_reached"],
                "unmet_needs_count": len(simulated["unmet_needs_due_to_constraints"])
            },
            "baseline_plan_summary": {
                "status": baseline["status"],
                "total_budget_allocated_inr": base_res["budget"]["allocated_inr"],
                "total_crew_used": base_res["crew"]["allocated_members"],
                "total_water_used_l": base_res["water"]["allocated_liters"],
                "total_risk_reduction": base_imp["total_risk_reduction_achieved"],
                "total_interventions_count": base_imp["total_interventions_dispatched"],
                "total_people_reached": base_imp["total_people_reached"]
            }
        }


# Convenience singleton and functional API
default_engine = InterventionEngine()


def generate_intervention_recommendations(
    wards: List[Dict[str, Any]],
    total_budget_inr: float = 500000.0,
    total_crew_members: int = 40,
    total_water_cap_l: float = 30000.0,
    equity_slider: float = 0.5,
    intervention_capacity_limits: Optional[Dict[str, int]] = None,
    existing_interventions: Optional[List[Dict[str, Any]]] = None,
    include_tradeoff_analysis: bool = True
) -> Dict[str, Any]:
    """Top-level functional API for the Intervention Engine."""
    return default_engine.optimize_interventions(
        wards=wards,
        total_budget_inr=total_budget_inr,
        total_crew_members=total_crew_members,
        total_water_cap_l=total_water_cap_l,
        equity_slider=equity_slider,
        intervention_capacity_limits=intervention_capacity_limits,
        existing_interventions=existing_interventions,
        include_tradeoff_analysis=include_tradeoff_analysis
    )


def run_what_if_simulation(
    wards: List[Dict[str, Any]],
    simulated_budget_inr: float,
    simulated_crew_members: int,
    simulated_water_cap_l: float,
    simulated_equity_slider: float,
    simulated_capacity_limits: Optional[Dict[str, int]] = None,
    baseline_budget_inr: float = 500000.0,
    baseline_crew_members: int = 40,
    baseline_water_cap_l: float = 30000.0,
    baseline_equity_slider: float = 0.5,
    baseline_capacity_limits: Optional[Dict[str, int]] = None,
    existing_interventions: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Top-level functional API for What-If scenario simulation."""
    return default_engine.simulate_what_if_scenario(
        wards=wards,
        simulated_budget_inr=simulated_budget_inr,
        simulated_crew_members=simulated_crew_members,
        simulated_water_cap_l=simulated_water_cap_l,
        simulated_equity_slider=simulated_equity_slider,
        simulated_capacity_limits=simulated_capacity_limits,
        baseline_budget_inr=baseline_budget_inr,
        baseline_crew_members=baseline_crew_members,
        baseline_water_cap_l=baseline_water_cap_l,
        baseline_equity_slider=baseline_equity_slider,
        baseline_capacity_limits=baseline_capacity_limits,
        existing_interventions=existing_interventions
    )
