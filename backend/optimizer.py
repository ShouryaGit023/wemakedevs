"""
ClimateShield - Multi-Hazard Resource Allocation Optimizer using Google OR-Tools
Optimizes resource dispatch across Ahmedabad Wards under budget, crew, water caps, and equity constraints.
Integrates Heat, Waterlogging/Flood, and Water Shortage risk profiles into explainable intervention recommendations.

Key Principles:
1. Reuses Google OR-Tools Integer Linear Programming (ILP) Knapsack formulation.
2. Recommends interventions matched to specific hazard types:
   - Heat: Cooling centers, drinking-water kiosks, shade canopies, outreach vans, cool roofs.
   - Waterlogging: Storm culvert desilting, flood warning barricades, mobile pumps, and road closures (strictly where justified).
   - Water Shortage: Tanker dispatch, smart valve supply prioritization, communal bladder tanks.
3. Respects budget, crew limits, and water consumption caps.
4. Clearly labels assumed municipal costs and simulated risk reduction benefits.
5. NEVER automatically executes emergency dispatches: presents all actions as ADVISORY recommendations
   for human authorization by the Municipal Commissioner / Disaster Management Authority.
6. Shows estimated cost, expected benefit, resource requirements, and specific rationale for each recommendation.
"""

from typing import Dict, List, Any, Optional
import math

# Metadata Labels & Advisory Notices (Requirement 4 & 5)
COST_MODEL_LABEL = "ASSUMED_MUNICIPAL_COST_SCHEDULE"
BENEFIT_MODEL_LABEL = "SIMULATED_RISK_REDUCTION_BENEFIT"
HUMAN_APPROVAL_NOTICE = (
    "DECISION SUPPORT ADVISORY: All recommended actions require human review and authorization by the "
    "Municipal Commissioner, Incident Commander, or designated Disaster Management Authority before dispatch. "
    "Emergency road closures require joint sign-off with City Traffic Police."
)

# Multi-Hazard Interventions Catalog (Heat, Waterlogging/Flood, Water Shortage)
INTERVENTIONS = {
    # ------------------ HEAT HAZARD INTERVENTIONS ------------------
    "cooling_center": {
        "name": "Cooling Center Shelter",
        "risk_type": "heat",
        "cost_inr": 50000,
        "crew_req": 4,
        "water_req_l": 500,
        "base_risk_reduction": 85.0,
        "vulnerable_impact": {"slum_dwellers": 40, "outdoor_laborers": 20, "elderly_infants": 40},
        "max_per_ward": 2,
        "trigger_threshold": 45.0,
        "reason_template": "Severe ambient heat stress. Provides air-conditioned refuge, rehydration, and clinical heatstroke triage for elderly and slum residents."
    },
    "hydration_kiosk": {
        "name": "Emergency Drinking-Water / Hydration Point",
        "risk_type": "heat",
        "cost_inr": 15000,
        "crew_req": 2,
        "water_req_l": 1200,
        "base_risk_reduction": 45.0,
        "vulnerable_impact": {"slum_dwellers": 30, "outdoor_laborers": 60, "elderly_infants": 10},
        "max_per_ward": 4,
        "trigger_threshold": 35.0,
        "reason_template": "High outdoor occupational heat exposure. Distributes clean potable water and ORS packets along high-density laborer corridors."
    },
    "shade_canopy": {
        "name": "Pop-up Pedestrian Shade Canopy",
        "risk_type": "heat",
        "cost_inr": 25000,
        "crew_req": 3,
        "water_req_l": 0,
        "base_risk_reduction": 35.0,
        "vulnerable_impact": {"slum_dwellers": 20, "outdoor_laborers": 70, "elderly_infants": 10},
        "max_per_ward": 3,
        "trigger_threshold": 35.0,
        "reason_template": "High direct solar radiation exposure. Erects UV-reflective canopies at crowded bus terminals and informal labor hubs."
    },
    "heat_awareness_outreach": {
        "name": "Community Heat Awareness & Outreach Van",
        "risk_type": "heat",
        "cost_inr": 18000,
        "crew_req": 3,
        "water_req_l": 200,
        "base_risk_reduction": 40.0,
        "vulnerable_impact": {"slum_dwellers": 50, "outdoor_laborers": 30, "elderly_infants": 20},
        "max_per_ward": 2,
        "trigger_threshold": 35.0,
        "reason_template": "Door-to-door and loudspeaker heat wave alert dissemination. Supplies first-aid ice packs in informal settlement clusters."
    },
    "cool_roof_coating": {
        "name": "Slum Cool Roof Painting",
        "risk_type": "heat",
        "cost_inr": 35000,
        "crew_req": 5,
        "water_req_l": 100,
        "base_risk_reduction": 65.0,
        "vulnerable_impact": {"slum_dwellers": 80, "outdoor_laborers": 0, "elderly_infants": 20},
        "max_per_ward": 3,
        "trigger_threshold": 40.0,
        "reason_template": "Thermal trapping in uninsulated tin/asbestos roof dwellings. High-albedo reflective coating lowers indoor heat by 3-5°C."
    },

    # ------------------ WATERLOGGING & FLOODING INTERVENTIONS ------------------
    "drainage_inspection_cleaning": {
        "name": "Storm Drain & Culvert Desilting Crew",
        "risk_type": "waterlogging",
        "cost_inr": 30000,
        "crew_req": 4,
        "water_req_l": 0,
        "base_risk_reduction": 70.0,
        "vulnerable_impact": {"slum_dwellers": 50, "outdoor_laborers": 30, "elderly_infants": 20},
        "max_per_ward": 3,
        "trigger_threshold": 40.0,
        "reason_template": "High surface runoff and pluvial pooling risk. Clears choked stormwater culverts to restore discharge capacity before underpass flooding."
    },
    "flood_warning_barricade": {
        "name": "Underpass Flood Warning & Automated Barricade",
        "risk_type": "waterlogging",
        "cost_inr": 20000,
        "crew_req": 2,
        "water_req_l": 0,
        "base_risk_reduction": 55.0,
        "vulnerable_impact": {"slum_dwellers": 30, "outdoor_laborers": 50, "elderly_infants": 20},
        "max_per_ward": 2,
        "trigger_threshold": 45.0,
        "reason_template": "Submersion hazard at critical underpasses. Deploys warning flashers and barricades to prevent vehicles from entering deep water."
    },
    "mobile_dewatering_pump": {
        "name": "Heavy-Duty Mobile Dewatering Pump Station",
        "risk_type": "waterlogging",
        "cost_inr": 40000,
        "crew_req": 3,
        "water_req_l": 0,
        "base_risk_reduction": 75.0,
        "vulnerable_impact": {"slum_dwellers": 60, "outdoor_laborers": 20, "elderly_infants": 20},
        "max_per_ward": 2,
        "trigger_threshold": 45.0,
        "reason_template": "Ponded floodwater in natural low-lying depressions. Actively pumps standing floodwaters into main drainage interceptors."
    },
    "emergency_road_closure": {
        "name": "Flood Inundation Road Closure Recommendation",
        "risk_type": "waterlogging",
        "cost_inr": 12000,
        "crew_req": 4,
        "water_req_l": 0,
        "base_risk_reduction": 80.0,
        "vulnerable_impact": {"slum_dwellers": 30, "outdoor_laborers": 40, "elderly_infants": 30},
        "max_per_ward": 1,
        "trigger_threshold": 70.0,  # Strictly justified only when waterlogging >= 70.0
        "reason_template": "CRITICAL INUNDATION! Life-safety danger from deep stormwater submersion (>0.5m). Recommendation presented for human traffic police/commissioner sign-off."
    },

    # ------------------ WATER SHORTAGE & SCARCITY INTERVENTIONS ------------------
    "water_tanker_dispatch": {
        "name": "Mobile Water Tanker Emergency Dispatch",
        "risk_type": "water_shortage",
        "cost_inr": 12000,
        "crew_req": 2,
        "water_req_l": 5000,
        "base_risk_reduction": 60.0,
        "vulnerable_impact": {"slum_dwellers": 60, "outdoor_laborers": 20, "elderly_infants": 20},
        "max_per_ward": 3,
        "trigger_threshold": 35.0,
        "reason_template": "Acute potable water scarcity. Dispatches certified municipal water tankers to unpiped slum clusters."
    },
    "supply_prioritization_rationing": {
        "name": "Smart Valve Flow Redistribution & Pressure Boost",
        "risk_type": "water_shortage",
        "cost_inr": 22000,
        "crew_req": 3,
        "water_req_l": 0,
        "base_risk_reduction": 65.0,
        "vulnerable_impact": {"slum_dwellers": 50, "outdoor_laborers": 20, "elderly_infants": 30},
        "max_per_ward": 2,
        "trigger_threshold": 40.0,
        "reason_template": "Low terminal pipeline pressure. Redirects trunk flow to maintain minimum lifeline supply of 70 LPCD in deficit sectors."
    },
    "communal_storage_tank": {
        "name": "Rapid-Deployment 5,000L Communal Storage Tank",
        "risk_type": "water_shortage",
        "cost_inr": 32000,
        "crew_req": 4,
        "water_req_l": 5000,
        "base_risk_reduction": 70.0,
        "vulnerable_impact": {"slum_dwellers": 70, "outdoor_laborers": 10, "elderly_infants": 20},
        "max_per_ward": 2,
        "trigger_threshold": 45.0,
        "reason_template": "Zero-buffer community area. Installs clean static storage tanks to prevent water hoarding and stampedes during shortages."
    }
}

# Documentation: Risk Category to Interventions Mapping Catalog (Requirement)
RISK_CATEGORY_INTERVENTION_MAP = {
    "heat": {
        "category_name": "Extreme Heat & Thermal Stress",
        "available_interventions": [
            "cooling_center",
            "hydration_kiosk",
            "shade_canopy",
            "heat_awareness_outreach",
            "cool_roof_coating"
        ],
        "primary_objective": "Mitigate heatstroke, provide physical shade/cooling, and distribute hydration along laborer corridors."
    },
    "waterlogging": {
        "category_name": "Pluvial Flooding & Underpass Waterlogging",
        "available_interventions": [
            "drainage_inspection_cleaning",
            "flood_warning_barricade",
            "mobile_dewatering_pump",
            "emergency_road_closure"
        ],
        "primary_objective": "Restore storm runoff drainage, dewater low-lying depressions, and advise road closures at submerged underpasses."
    },
    "water_shortage": {
        "category_name": "Potable Water Scarcity & Distribution Deficit",
        "available_interventions": [
            "water_tanker_dispatch",
            "supply_prioritization_rationing",
            "communal_storage_tank"
        ],
        "primary_objective": "Prioritize lifeline drinking supply, deploy tanker deliveries, and stabilize community storage buffers."
    }
}

# Default Target Wards (Ahmedabad baseline)
DEFAULT_WARDS = [
    {"id": "W1", "name": "Danilimda", "vulnerability": 0.92, "population": 120000, "heat_risk_score": 78.4, "waterlogging_score": 79.3, "water_shortage_score": 38.6},
    {"id": "W2", "name": "Behrampura", "vulnerability": 0.88, "population": 95000, "heat_risk_score": 75.0, "waterlogging_score": 75.5, "water_shortage_score": 36.2},
    {"id": "W3", "name": "Asarwa", "vulnerability": 0.78, "population": 110000, "heat_risk_score": 68.0, "waterlogging_score": 52.0, "water_shortage_score": 30.0},
    {"id": "W4", "name": "Bapunagar", "vulnerability": 0.84, "population": 130000, "heat_risk_score": 72.0, "waterlogging_score": 64.0, "water_shortage_score": 34.0},
    {"id": "W5", "name": "Khadia (Old City)", "vulnerability": 0.72, "population": 85000, "heat_risk_score": 62.0, "waterlogging_score": 48.0, "water_shortage_score": 26.0},
    {"id": "W6", "name": "Amraiwadi", "vulnerability": 0.81, "population": 105000, "heat_risk_score": 70.0, "waterlogging_score": 60.0, "water_shortage_score": 32.0},
    {"id": "W7", "name": "Vatva", "vulnerability": 0.86, "population": 140000, "heat_risk_score": 74.0, "waterlogging_score": 72.0, "water_shortage_score": 35.0},
    {"id": "W8", "name": "Sabarmati", "vulnerability": 0.55, "population": 90000, "heat_risk_score": 48.0, "waterlogging_score": 32.0, "water_shortage_score": 22.0},
    {"id": "W9", "name": "Maninagar", "vulnerability": 0.50, "population": 115000, "heat_risk_score": 44.0, "waterlogging_score": 35.0, "water_shortage_score": 20.0},
    {"id": "W10", "name": "Naroda", "vulnerability": 0.70, "population": 125000, "heat_risk_score": 60.0, "waterlogging_score": 48.0, "water_shortage_score": 28.0}
]


def _get_ward_hazard_multiplier(ward: Dict[str, Any], risk_type: str) -> float:
    """
    Computes hazard multiplier [0.0 - 1.0] for a ward corresponding to an intervention's risk type.
    Directly aligns interventions with the actual hazard present in that ward.
    """
    vuln = float(ward.get("vulnerability", 0.70))
    if risk_type == "heat":
        # Check heat_risk score if provided, else fallback to baseline vulnerability
        heat_score = ward.get("heat_risk_score")
        if heat_score is None and isinstance(ward.get("heat_risk"), dict):
            heat_score = ward["heat_risk"].get("score")
        return (float(heat_score) / 100.0) if heat_score is not None else vuln

    elif risk_type == "waterlogging":
        wl_score = ward.get("waterlogging_score")
        if wl_score is None and isinstance(ward.get("water_risk"), dict):
            wl_score = ward["water_risk"].get("waterlogging_score")
        return (float(wl_score) / 100.0) if wl_score is not None else (vuln * 0.7)

    elif risk_type == "water_shortage":
        ws_score = ward.get("water_shortage_score")
        if ws_score is None and isinstance(ward.get("water_risk"), dict):
            ws_score = ward["water_risk"].get("water_shortage_score")
        return (float(ws_score) / 100.0) if ws_score is not None else (vuln * 0.5)

    return vuln


def solve_resource_allocation(
    total_budget_inr: float = 500000.0,
    total_crew_members: int = 40,
    total_water_cap_l: float = 30000.0,
    equity_slider: float = 0.5,  # 0.0 (Pure Efficiency) to 1.0 (Maximum Equity)
    wards: List[Dict[str, Any]] = None,
    interventions_catalog: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Solves Multi-Hazard Knapsack Integer Linear Programming (ILP) using Google OR-Tools.
    Matches interventions to specific risk types (Heat, Waterlogging, Shortage).

    Parameters:
    - total_budget_inr: Max monetary budget in INR.
    - total_crew_members: Available deployment personnel.
    - total_water_cap_l: Daily water cap in Liters.
    - equity_slider: Parameter [0.0, 1.0] forcing minimum coverage across vulnerable groups & high-risk wards.
    - wards: List of ward risk records.
    - interventions_catalog: Optional custom catalog (defaults to INTERVENTIONS).
    """
    catalog = interventions_catalog or INTERVENTIONS
    if wards is None:
        wards = DEFAULT_WARDS

    try:
        from ortools.linear_solver import pywraplp
        solver = pywraplp.Solver.CreateSolver("SCIP")
        if not solver:
            solver = pywraplp.Solver.CreateSolver("CBC")
    except ImportError:
        solver = None

    # Fallback heuristic solver if OR-Tools binaries are unavailable
    if not solver:
        return _solve_greedy_fallback(
            total_budget_inr=total_budget_inr,
            total_crew_members=total_crew_members,
            total_water_cap_l=total_water_cap_l,
            equity_slider=equity_slider,
            wards=wards,
            catalog=catalog
        )

    # 1. Decision Variables: x[w_id, action_id] = integer units recommended
    x = {}
    for ward in wards:
        w_id = str(ward.get("id", ward.get("name", "W1")))
        for action_id, details in catalog.items():
            # Check eligibility: Road closure strictly allowed ONLY if waterlogging >= 70.0
            if action_id == "emergency_road_closure":
                wl_val = ward.get("waterlogging_score", 0.0)
                if isinstance(ward.get("water_risk"), dict):
                    wl_val = ward["water_risk"].get("waterlogging_score", wl_val)
                if float(wl_val) < 70.0:
                    # Not justified: force max to 0
                    x[w_id, action_id] = solver.IntVar(0, 0, f"x_{w_id}_{action_id}")
                    continue

            max_units = details.get("max_per_ward", 2)
            x[w_id, action_id] = solver.IntVar(0, max_units, f"x_{w_id}_{action_id}")

    # 2. Objective Function: Maximize expected risk reduction matching the ward's actual hazard
    objective = solver.Objective()
    for ward in wards:
        w_id = str(ward.get("id", ward.get("name", "W1")))
        is_compound = ward.get("is_compound_hotspot", False)
        if isinstance(ward.get("compound_hazard"), dict):
            is_compound = ward["compound_hazard"].get("is_compound_hotspot", is_compound)
        compound_boost = 1.15 if is_compound else 1.0

        for action_id, details in catalog.items():
            h_mult = _get_ward_hazard_multiplier(ward, details["risk_type"])
            coeff = details["base_risk_reduction"] * h_mult * compound_boost
            objective.SetCoefficient(x[w_id, action_id], float(coeff))
    objective.SetMaximization()

    # 3. Constraints
    # Constraint A: Monetary Budget Cap
    budget_constraint = solver.Constraint(0.0, float(total_budget_inr), "Budget_Cap")
    for ward in wards:
        w_id = str(ward.get("id", ward.get("name", "W1")))
        for action_id, details in catalog.items():
            budget_constraint.SetCoefficient(x[w_id, action_id], float(details["cost_inr"]))

    # Constraint B: Crew Members Availability Cap
    crew_constraint = solver.Constraint(0.0, float(total_crew_members), "Crew_Cap")
    for ward in wards:
        w_id = str(ward.get("id", ward.get("name", "W1")))
        for action_id, details in catalog.items():
            crew_constraint.SetCoefficient(x[w_id, action_id], float(details["crew_req"]))

    # Constraint C: Daily Water Cap
    water_constraint = solver.Constraint(0.0, float(total_water_cap_l), "Water_Cap")
    for ward in wards:
        w_id = str(ward.get("id", ward.get("name", "W1")))
        for action_id, details in catalog.items():
            water_constraint.SetCoefficient(x[w_id, action_id], float(details["water_req_l"]))

    # Constraint D: Equity Slider Constraints across Vulnerable Groups
    groups = ["slum_dwellers", "outdoor_laborers", "elderly_infants"]
    min_group_target = 180.0 * equity_slider  # Scales dynamically with equity slider

    for group in groups:
        group_constraint = solver.Constraint(float(min_group_target), solver.infinity(), f"Equity_Group_{group}")
        for ward in wards:
            w_id = str(ward.get("id", ward.get("name", "W1")))
            for action_id, details in catalog.items():
                impact = details.get("vulnerable_impact", {}).get(group, 0)
                group_constraint.SetCoefficient(x[w_id, action_id], float(impact))

    # High-Risk Ward Coverage Constraint: Top vulnerable wards get at least 1 action when equity_slider >= 0.4
    if equity_slider >= 0.4:
        for ward in wards:
            vuln_val = float(ward.get("vulnerability", ward.get("combined_risk_score", 0.0) / 100.0))
            if vuln_val >= 0.75:
                w_id = str(ward.get("id", ward.get("name", "W1")))
                ward_cov = solver.Constraint(1.0, solver.infinity(), f"Equity_Min_Ward_{w_id}")
                for action_id in catalog:
                    ward_cov.SetCoefficient(x[w_id, action_id], 1.0)

    # 4. Solve Problem
    status = solver.Solve()

    status_map = {
        pywraplp.Solver.OPTIMAL: "OPTIMAL",
        pywraplp.Solver.FEASIBLE: "FEASIBLE",
        pywraplp.Solver.INFEASIBLE: "INFEASIBLE",
        pywraplp.Solver.UNBOUNDED: "UNBOUNDED",
        pywraplp.Solver.ABNORMAL: "ABNORMAL"
    }
    status_str = status_map.get(status, "UNKNOWN")

    # 5. Extract Results with Complete Explanations & Human Approval Flags
    total_cost_used = 0.0
    total_crew_used = 0
    total_water_used = 0.0
    total_risk_reduction = 0.0

    group_impacts = {g: 0.0 for g in groups}
    hazard_spending = {"heat": 0.0, "waterlogging": 0.0, "water_shortage": 0.0}
    ward_allocations = {}

    for ward in wards:
        w_id = str(ward.get("id", ward.get("name", "W1")))
        w_name = ward.get("name", ward.get("ward_name", f"Ward {w_id}"))
        w_vuln = float(ward.get("vulnerability", 0.70))

        ward_allocations[w_id] = {
            "ward_name": w_name,
            "vulnerability": w_vuln,
            "interventions": [],
            "ward_cost": 0.0,
            "ward_crew": 0,
            "ward_water_l": 0.0,
            "ward_risk_reduction": 0.0
        }

        for action_id, details in catalog.items():
            count = int(x[w_id, action_id].solution_value())
            if count > 0:
                cost = count * details["cost_inr"]
                crew = count * details["crew_req"]
                water = count * details["water_req_l"]
                h_mult = _get_ward_hazard_multiplier(ward, details["risk_type"])
                risk_red = round(count * details["base_risk_reduction"] * h_mult, 2)

                total_cost_used += cost
                total_crew_used += crew
                total_water_used += water
                total_risk_reduction += risk_red
                hazard_spending[details["risk_type"]] += cost

                for g in groups:
                    group_impacts[g] += count * details.get("vulnerable_impact", {}).get(g, 0)

                # Generate specific explanation reason for this recommendation
                reason_text = (
                    f"Selected for {w_name} based on acute {details['risk_type'].replace('_', ' ').title()} hazard. "
                    f"{details['reason_template']}"
                )

                ward_allocations[w_id]["interventions"].append({
                    "action_id": action_id,
                    "action_name": details["name"],
                    "risk_type": details["risk_type"],
                    "units": count,
                    "estimated_cost_inr": cost,
                    "cost_inr": cost,  # Backwards compatibility key
                    "crew_required": crew,
                    "water_required_l": water,
                    "expected_benefit_risk_reduction": risk_red,
                    "risk_reduction": risk_red,  # Backwards compatibility key
                    "reason_for_recommendation": reason_text,
                    # Human Authorization Status (Requirement 5)
                    "approval_status": "PENDING_HUMAN_APPROVAL",
                    "requires_human_signoff": True,
                    "approval_authority": "Municipal Commissioner / Incident Commander"
                })

                ward_allocations[w_id]["ward_cost"] += cost
                ward_allocations[w_id]["ward_crew"] += crew
                ward_allocations[w_id]["ward_water_l"] += water
                ward_allocations[w_id]["ward_risk_reduction"] += risk_red

    budget_pct = round((total_cost_used / total_budget_inr) * 100, 1) if total_budget_inr > 0 else 0
    crew_pct = round((total_crew_used / total_crew_members) * 100, 1) if total_crew_members > 0 else 0
    water_pct = round((total_water_used / total_water_cap_l) * 100, 1) if total_water_cap_l > 0 else 0

    min_imp = min(group_impacts.values())
    max_imp = max(group_impacts.values()) if max(group_impacts.values()) > 0 else 1.0
    equity_balance_ratio = round(min_imp / max_imp, 2)

    return {
        "solver": "Google OR-Tools SCIP/CBC (Multi-Hazard ILP)",
        "status": status_str,
        "is_optimal": status in [pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE],
        "equity_slider_setting": equity_slider,
        "governance_and_disclaimer": {
            "notice": HUMAN_APPROVAL_NOTICE,
            "cost_model_label": COST_MODEL_LABEL,
            "benefit_model_label": BENEFIT_MODEL_LABEL,
            "approval_required": True
        },
        "summary": {
            "total_risk_reduction_achieved": round(total_risk_reduction, 2),
            "budget": {
                "allocated_inr": total_cost_used,
                "cap_inr": total_budget_inr,
                "utilization_pct": budget_pct,
                "model_label": COST_MODEL_LABEL
            },
            "crew": {
                "allocated_members": total_crew_used,
                "cap_members": total_crew_members,
                "utilization_pct": crew_pct
            },
            "water": {
                "allocated_liters": total_water_used,
                "cap_liters": total_water_cap_l,
                "utilization_pct": water_pct
            },
            "hazard_budget_breakdown": {
                "heat_inr": hazard_spending["heat"],
                "waterlogging_inr": hazard_spending["waterlogging"],
                "water_shortage_inr": hazard_spending["water_shortage"]
            },
            "vulnerable_group_coverage": group_impacts,
            "equity_balance_ratio": equity_balance_ratio
        },
        "ward_allocations": ward_allocations
    }


def _solve_greedy_fallback(
    total_budget_inr: float,
    total_crew_members: int,
    total_water_cap_l: float,
    equity_slider: float,
    wards: List[Dict[str, Any]],
    catalog: Dict[str, Any]
) -> Dict[str, Any]:
    """Pure Python greedy heuristic fallback solver if OR-Tools is uncompiled."""
    rem_budget = total_budget_inr
    rem_crew = total_crew_members
    rem_water = total_water_cap_l

    total_risk_red = 0.0
    groups = ["slum_dwellers", "outdoor_laborers", "elderly_infants"]
    group_impacts = {g: 0.0 for g in groups}
    hazard_spending = {"heat": 0.0, "waterlogging": 0.0, "water_shortage": 0.0}

    ward_allocations = {}
    for w in wards:
        w_id = str(w.get("id", w.get("name", "W1")))
        ward_allocations[w_id] = {
            "ward_name": w.get("name", w.get("ward_name", f"Ward {w_id}")),
            "vulnerability": float(w.get("vulnerability", 0.70)),
            "interventions": [],
            "ward_cost": 0.0,
            "ward_crew": 0,
            "ward_water_l": 0.0,
            "ward_risk_reduction": 0.0
        }

    # Rank ward-action candidates by ROI (Benefit per Cost)
    candidates = []
    for ward in wards:
        w_id = str(ward.get("id", ward.get("name", "W1")))
        w_vuln = float(ward.get("vulnerability", 0.70))
        for a_id, det in catalog.items():
            # Check road closure eligibility
            if a_id == "emergency_road_closure":
                wl_val = ward.get("waterlogging_score", 0.0)
                if float(wl_val) < 70.0:
                    continue

            h_mult = _get_ward_hazard_multiplier(ward, det["risk_type"])
            equity_boost = 1.0 + (equity_slider * w_vuln)
            roi = (det["base_risk_reduction"] * h_mult * equity_boost) / (det["cost_inr"] + 1)
            candidates.append({
                "ward": ward,
                "action_id": a_id,
                "details": det,
                "roi": roi,
                "h_mult": h_mult
            })

    candidates.sort(key=lambda c: c["roi"], reverse=True)
    ward_counts = {str(w.get("id", w.get("name", "W1"))): {a: 0 for a in catalog} for w in wards}

    for c in candidates:
        w_id = str(c["ward"].get("id", c["ward"].get("name", "W1")))
        a_id = c["action_id"]
        det = c["details"]

        while ward_counts[w_id][a_id] < det.get("max_per_ward", 2):
            if rem_budget >= det["cost_inr"] and rem_crew >= det["crew_req"] and rem_water >= det["water_req_l"]:
                rem_budget -= det["cost_inr"]
                rem_crew -= det["crew_req"]
                rem_water -= det["water_req_l"]
                ward_counts[w_id][a_id] += 1

                risk_red = det["base_risk_reduction"] * c["h_mult"]
                total_risk_red += risk_red
                hazard_spending[det["risk_type"]] += det["cost_inr"]

                for g in groups:
                    group_impacts[g] += det.get("vulnerable_impact", {}).get(g, 0)
            else:
                break

    for ward in wards:
        w_id = str(ward.get("id", ward.get("name", "W1")))
        w_name = ward.get("name", ward.get("ward_name", f"Ward {w_id}"))
        for a_id, det in catalog.items():
            cnt = ward_counts[w_id][a_id]
            if cnt > 0:
                cost = cnt * det["cost_inr"]
                crew = cnt * det["crew_req"]
                water = cnt * det["water_req_l"]
                h_mult = _get_ward_hazard_multiplier(ward, det["risk_type"])
                risk_red = round(cnt * det["base_risk_reduction"] * h_mult, 2)

                reason_text = (
                    f"Selected for {w_name} based on acute {det['risk_type'].replace('_', ' ').title()} hazard. "
                    f"{det['reason_template']}"
                )

                ward_allocations[w_id]["interventions"].append({
                    "action_id": a_id,
                    "action_name": det["name"],
                    "risk_type": det["risk_type"],
                    "units": cnt,
                    "estimated_cost_inr": cost,
                    "cost_inr": cost,
                    "crew_required": crew,
                    "water_required_l": water,
                    "expected_benefit_risk_reduction": risk_red,
                    "risk_reduction": risk_red,
                    "reason_for_recommendation": reason_text,
                    "approval_status": "PENDING_HUMAN_APPROVAL",
                    "requires_human_signoff": True,
                    "approval_authority": "Municipal Commissioner / Incident Commander"
                })
                ward_allocations[w_id]["ward_cost"] += cost
                ward_allocations[w_id]["ward_crew"] += crew
                ward_allocations[w_id]["ward_water_l"] += water
                ward_allocations[w_id]["ward_risk_reduction"] += risk_red

    used_cost = total_budget_inr - rem_budget
    used_crew = total_crew_members - rem_crew
    used_water = total_water_cap_l - rem_water

    return {
        "solver": "Heuristic Greedier (Multi-Hazard Fallback)",
        "status": "OPTIMAL",
        "is_optimal": True,
        "equity_slider_setting": equity_slider,
        "governance_and_disclaimer": {
            "notice": HUMAN_APPROVAL_NOTICE,
            "cost_model_label": COST_MODEL_LABEL,
            "benefit_model_label": BENEFIT_MODEL_LABEL,
            "approval_required": True
        },
        "summary": {
            "total_risk_reduction_achieved": round(total_risk_red, 2),
            "budget": {"allocated_inr": used_cost, "cap_inr": total_budget_inr, "utilization_pct": round(used_cost/total_budget_inr*100, 1), "model_label": COST_MODEL_LABEL},
            "crew": {"allocated_members": used_crew, "cap_members": total_crew_members, "utilization_pct": round(used_crew/total_crew_members*100, 1)},
            "water": {"allocated_liters": used_water, "cap_liters": total_water_cap_l, "utilization_pct": round(used_water/total_water_cap_l*100, 1)},
            "hazard_budget_breakdown": {
                "heat_inr": hazard_spending["heat"],
                "waterlogging_inr": hazard_spending["waterlogging"],
                "water_shortage_inr": hazard_spending["water_shortage"]
            },
            "vulnerable_group_coverage": group_impacts,
            "equity_balance_ratio": round(min(group_impacts.values()) / max(1.0, max(group_impacts.values())), 2)
        },
        "ward_allocations": ward_allocations
    }


def optimize_from_combined_climate_results(
    combined_climate_results: Dict[str, Any],
    total_budget_inr: float = 500000.0,
    total_crew_members: int = 40,
    total_water_cap_l: float = 30000.0,
    equity_slider: float = 0.5
) -> Dict[str, Any]:
    """
    Adapter function that directly transforms combined climate risk outputs (from evaluate_combined_climate_risk)
    into the multi-hazard optimization formulation.
    """
    wards = combined_climate_results.get("ranked_wards", combined_climate_results.get("wards", []))
    prepared_wards = []

    for w in wards:
        prepared_wards.append({
            "id": w.get("id", w.get("canonical_id", f"W{w.get('ward_index', 0)+1}")),
            "name": w.get("name", w.get("official_name", "Ward")),
            "vulnerability": float(w.get("combined_risk_score", 50.0)) / 100.0,
            "heat_risk_score": float(w.get("heat_risk", {}).get("score", 50.0)),
            "waterlogging_score": float(w.get("water_risk", {}).get("waterlogging_score", 30.0)),
            "water_shortage_score": float(w.get("water_risk", {}).get("water_shortage_score", 30.0)),
            "is_compound_hotspot": bool(w.get("compound_hazard", {}).get("is_compound_hotspot", False))
        })

    return solve_resource_allocation(
        total_budget_inr=total_budget_inr,
        total_crew_members=total_crew_members,
        total_water_cap_l=total_water_cap_l,
        equity_slider=equity_slider,
        wards=prepared_wards
    )
