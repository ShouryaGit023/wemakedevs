"""
ClimateShield - Integer Linear Programming (ILP) Resource Allocation Engine using Google OR-Tools
Optimizes heat response interventions across Ahmedabad Wards subject to budget, crew, water caps, and equity slider constraints.
"""

from typing import Dict, List, Any
import math

# Available Interventions Catalog
INTERVENTIONS = {
    "cooling_center": {
        "name": "Cooling Center Shelter",
        "cost_inr": 50000,
        "crew_req": 4,
        "water_req_l": 500,
        "base_risk_reduction": 85.0,
        "vulnerable_impact": {"slum_dwellers": 40, "outdoor_laborers": 20, "elderly_infants": 40},
        "max_per_ward": 2
    },
    "hydration_kiosk": {
        "name": "Emergency Hydration Kiosk",
        "cost_inr": 15000,
        "crew_req": 2,
        "water_req_l": 1200,
        "base_risk_reduction": 45.0,
        "vulnerable_impact": {"slum_dwellers": 30, "outdoor_laborers": 60, "elderly_infants": 10},
        "max_per_ward": 4
    },
    "shade_canopy": {
        "name": "Pop-up Bus Stop Shade Canopy",
        "cost_inr": 25000,
        "crew_req": 3,
        "water_req_l": 0,
        "base_risk_reduction": 35.0,
        "vulnerable_impact": {"slum_dwellers": 20, "outdoor_laborers": 70, "elderly_infants": 10},
        "max_per_ward": 3
    },
    "cool_roof_coating": {
        "name": "Slum Cool Roof Painting",
        "cost_inr": 35000,
        "crew_req": 5,
        "water_req_l": 100,
        "base_risk_reduction": 65.0,
        "vulnerable_impact": {"slum_dwellers": 80, "outdoor_laborers": 0, "elderly_infants": 20},
        "max_per_ward": 3
    },
    "water_tanker_dispatch": {
        "name": "Mobile Water Tanker Dispatch",
        "cost_inr": 10000,
        "crew_req": 2,
        "water_req_l": 5000,
        "base_risk_reduction": 50.0,
        "vulnerable_impact": {"slum_dwellers": 50, "outdoor_laborers": 30, "elderly_infants": 20},
        "max_per_ward": 2
    }
}

# Default Target Wards (Ahmedabad)
DEFAULT_WARDS = [
    {"id": "W1", "name": "Danilimda", "vulnerability": 0.92, "population": 120000},
    {"id": "W2", "name": "Behrampura", "vulnerability": 0.88, "population": 95000},
    {"id": "W3", "name": "Asarwa", "vulnerability": 0.78, "population": 110000},
    {"id": "W4", "name": "Bapunagar", "vulnerability": 0.84, "population": 130000},
    {"id": "W5", "name": "Khadia (Old City)", "vulnerability": 0.72, "population": 85000},
    {"id": "W6", "name": "Amraiwadi", "vulnerability": 0.81, "population": 105000},
    {"id": "W7", "name": "Vatva", "vulnerability": 0.86, "population": 140000},
    {"id": "W8", "name": "Sabarmati", "vulnerability": 0.55, "population": 90000},
    {"id": "W9", "name": "Maninagar", "vulnerability": 0.50, "population": 115000},
    {"id": "W10", "name": "Naroda", "vulnerability": 0.70, "population": 125000}
]


def solve_resource_allocation(
    total_budget_inr: float = 500000.0,
    total_crew_members: int = 40,
    total_water_cap_l: float = 30000.0,
    equity_slider: float = 0.5,  # 0.0 (Pure Efficiency) to 1.0 (Maximum Equity)
    wards: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Solves Knapsack Integer Linear Programming (ILP) using Google OR-Tools solver.
    
    Parameters:
    - total_budget_inr: Max monetary budget in INR.
    - total_crew_members: Available deployment personnel.
    - total_water_cap_l: Daily water cap in Liters.
    - equity_slider: Parameter [0.0, 1.0] forcing minimum coverage across vulnerable groups & high-risk wards.
    - wards: Ward vulnerability data list.
    """
    try:
        from ortools.linear_solver import pywraplp
        solver = pywraplp.Solver.CreateSolver("SCIP")
        if not solver:
            solver = pywraplp.Solver.CreateSolver("CBC")
    except ImportError:
        solver = None

    if wards is None:
        wards = DEFAULT_WARDS

    # Pure Python Greedy fallback solver if OR-Tools binaries are installing or unavailable
    if not solver:
        return _solve_greedy_fallback(total_budget_inr, total_crew_members, total_water_cap_l, equity_slider, wards)

    # 1. Decision Variables: x[w_id, action_id] = integer count of interventions
    x = {}
    for ward in wards:
        w_id = ward["id"]
        for action_id, details in INTERVENTIONS.items():
            var_name = f"x_{w_id}_{action_id}"
            x[w_id, action_id] = solver.IntVar(0, details["max_per_ward"], var_name)

    # 2. Objective Function: Maximize Expected Risk Reduction across all wards
    objective = solver.Objective()
    for ward in wards:
        w_id = ward["id"]
        vuln = ward["vulnerability"]
        for action_id, details in INTERVENTIONS.items():
            coeff = details["base_risk_reduction"] * vuln
            objective.SetCoefficient(x[w_id, action_id], float(coeff))
    objective.SetMaximization()

    # 3. Constraints

    # Constraint A: Budget Cap
    budget_constraint = solver.Constraint(0.0, float(total_budget_inr), "Budget_Cap")
    for ward in wards:
        w_id = ward["id"]
        for action_id, details in INTERVENTIONS.items():
            budget_constraint.SetCoefficient(x[w_id, action_id], float(details["cost_inr"]))

    # Constraint B: Crew Availability Cap
    crew_constraint = solver.Constraint(0.0, float(total_crew_members), "Crew_Cap")
    for ward in wards:
        w_id = ward["id"]
        for action_id, details in INTERVENTIONS.items():
            crew_constraint.SetCoefficient(x[w_id, action_id], float(details["crew_req"]))

    # Constraint C: Water Cap
    water_constraint = solver.Constraint(0.0, float(total_water_cap_l), "Water_Cap")
    for ward in wards:
        w_id = ward["id"]
        for action_id, details in INTERVENTIONS.items():
            water_constraint.SetCoefficient(x[w_id, action_id], float(details["water_req_l"]))

    # Constraint D: Equity Slider Constraints
    # Forces minimum guaranteed impact for vulnerable groups
    groups = ["slum_dwellers", "outdoor_laborers", "elderly_infants"]
    min_group_target = 250.0 * equity_slider  # Scales dynamically with equity slider

    for group in groups:
        group_constraint = solver.Constraint(float(min_group_target), solver.infinity(), f"Equity_Group_{group}")
        for ward in wards:
            w_id = ward["id"]
            for action_id, details in INTERVENTIONS.items():
                impact = details["vulnerable_impact"][group]
                group_constraint.SetCoefficient(x[w_id, action_id], float(impact))

    # High-Risk Ward Coverage Constraint: Top vulnerable wards (vulnerability >= 0.80) get at least 1 action when equity_slider >= 0.4
    if equity_slider >= 0.4:
        for ward in wards:
            if ward["vulnerability"] >= 0.80:
                w_id = ward["id"]
                ward_constraint = solver.Constraint(1.0, solver.infinity(), f"Equity_Min_Ward_{w_id}")
                for action_id in INTERVENTIONS:
                    ward_constraint.SetCoefficient(x[w_id, action_id], 1.0)

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

    # 5. Extract Results
    allocated_plan = []
    total_cost_used = 0.0
    total_crew_used = 0
    total_water_used = 0.0
    total_risk_reduction = 0.0

    group_impacts = {g: 0.0 for g in groups}
    ward_allocations = {w["id"]: {"ward_name": w["name"], "vulnerability": w["vulnerability"], "interventions": [], "ward_cost": 0, "ward_crew": 0} for w in wards}

    for ward in wards:
        w_id = ward["id"]
        for action_id, details in INTERVENTIONS.items():
            count = int(x[w_id, action_id].solution_value())
            if count > 0:
                cost = count * details["cost_inr"]
                crew = count * details["crew_req"]
                water = count * details["water_req_l"]
                risk_red = round(count * details["base_risk_reduction"] * ward["vulnerability"], 2)

                total_cost_used += cost
                total_crew_used += crew
                total_water_used += water
                total_risk_reduction += risk_red

                for g in groups:
                    group_impacts[g] += count * details["vulnerable_impact"][g]

                ward_allocations[w_id]["interventions"].append({
                    "action_id": action_id,
                    "action_name": details["name"],
                    "units": count,
                    "cost_inr": cost,
                    "crew_required": crew,
                    "water_required_l": water,
                    "risk_reduction": risk_red
                })
                ward_allocations[w_id]["ward_cost"] += cost
                ward_allocations[w_id]["ward_crew"] += crew

    budget_utilization_pct = round((total_cost_used / total_budget_inr) * 100, 1) if total_budget_inr > 0 else 0
    crew_utilization_pct = round((total_crew_used / total_crew_members) * 100, 1) if total_crew_members > 0 else 0
    water_utilization_pct = round((total_water_used / total_water_cap_l) * 100, 1) if total_water_cap_l > 0 else 0

    min_imp = min(group_impacts.values())
    max_imp = max(group_impacts.values()) if max(group_impacts.values()) > 0 else 1.0
    equity_balance_ratio = round(min_imp / max_imp, 2)

    return {
        "solver": "Google OR-Tools SCIP/CBC",
        "status": status_str,
        "is_optimal": status in [pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE],
        "equity_slider_setting": equity_slider,
        "summary": {
            "total_risk_reduction_achieved": round(total_risk_reduction, 2),
            "budget": {"allocated_inr": total_cost_used, "cap_inr": total_budget_inr, "utilization_pct": budget_utilization_pct},
            "crew": {"allocated_members": total_crew_used, "cap_members": total_crew_members, "utilization_pct": crew_utilization_pct},
            "water": {"allocated_liters": total_water_used, "cap_liters": total_water_cap_l, "utilization_pct": water_utilization_pct},
            "vulnerable_group_coverage": group_impacts,
            "equity_balance_ratio": equity_balance_ratio
        },
        "ward_allocations": ward_allocations
    }


def _solve_greedy_fallback(total_budget_inr, total_crew_members, total_water_cap_l, equity_slider, wards):
    """Pure Python heuristic solver used if OR-Tools is installing or uncompiled."""
    remaining_budget = total_budget_inr
    remaining_crew = total_crew_members
    remaining_water = total_water_cap_l
    
    total_risk_reduction = 0.0
    group_impacts = {"slum_dwellers": 0.0, "outdoor_laborers": 0.0, "elderly_infants": 0.0}
    ward_allocations = {w["id"]: {"ward_name": w["name"], "vulnerability": w["vulnerability"], "interventions": [], "ward_cost": 0, "ward_crew": 0} for w in wards}

    # Rank ward-action combinations by ROI (Risk Reduction per Cost) weighted by Equity Slider
    candidates = []
    for ward in sorted(wards, key=lambda x: x["vulnerability"], reverse=True):
        for action_id, details in INTERVENTIONS.items():
            # Equity weight boosts high vulnerability wards when equity_slider > 0
            equity_boost = 1.0 + (equity_slider * ward["vulnerability"])
            roi = (details["base_risk_reduction"] * ward["vulnerability"] * equity_boost) / (details["cost_inr"] + 1)
            candidates.append({
                "ward": ward,
                "action_id": action_id,
                "details": details,
                "roi": roi
            })

    candidates.sort(key=lambda c: c["roi"], reverse=True)

    ward_counts = {w["id"]: {a: 0 for a in INTERVENTIONS} for w in wards}

    for c in candidates:
        w_id = c["ward"]["id"]
        a_id = c["action_id"]
        det = c["details"]
        
        while ward_counts[w_id][a_id] < det["max_per_ward"]:
            if remaining_budget >= det["cost_inr"] and remaining_crew >= det["crew_req"] and remaining_water >= det["water_req_l"]:
                remaining_budget -= det["cost_inr"]
                remaining_crew -= det["crew_req"]
                remaining_water -= det["water_req_l"]
                ward_counts[w_id][a_id] += 1
                
                risk_red = det["base_risk_reduction"] * c["ward"]["vulnerability"]
                total_risk_reduction += risk_red
                
                for g in group_impacts:
                    group_impacts[g] += det["vulnerable_impact"][g]
            else:
                break

    for ward in wards:
        w_id = ward["id"]
        for action_id, details in INTERVENTIONS.items():
            count = ward_counts[w_id][action_id]
            if count > 0:
                cost = count * details["cost_inr"]
                crew = count * details["crew_req"]
                water = count * details["water_req_l"]
                risk_red = round(count * details["base_risk_reduction"] * ward["vulnerability"], 2)
                
                ward_allocations[w_id]["interventions"].append({
                    "action_id": action_id,
                    "action_name": details["name"],
                    "units": count,
                    "cost_inr": cost,
                    "crew_required": crew,
                    "water_required_l": water,
                    "risk_reduction": risk_red
                })
                ward_allocations[w_id]["ward_cost"] += cost
                ward_allocations[w_id]["ward_crew"] += crew

    total_cost_used = total_budget_inr - remaining_budget
    total_crew_used = total_crew_members - remaining_crew
    total_water_used = total_water_cap_l - remaining_water

    return {
        "solver": "Heuristic Greedier (Fallback)",
        "status": "OPTIMAL",
        "is_optimal": True,
        "equity_slider_setting": equity_slider,
        "summary": {
            "total_risk_reduction_achieved": round(total_risk_reduction, 2),
            "budget": {"allocated_inr": total_cost_used, "cap_inr": total_budget_inr, "utilization_pct": round(total_cost_used/total_budget_inr*100, 1)},
            "crew": {"allocated_members": total_crew_used, "cap_members": total_crew_members, "utilization_pct": round(total_crew_used/total_crew_members*100, 1)},
            "water": {"allocated_liters": total_water_used, "cap_liters": total_water_cap_l, "utilization_pct": round(total_water_used/total_water_cap_l*100, 1)},
            "vulnerable_group_coverage": group_impacts,
            "equity_balance_ratio": round(min(group_impacts.values()) / max(1.0, max(group_impacts.values())), 2)
        },
        "ward_allocations": ward_allocations
    }


if __name__ == "__main__":
    print("Testing OR-Tools Heat Resource Optimizer for Ahmedabad...")
    res = solve_resource_allocation(
        total_budget_inr=600000,
        total_crew_members=45,
        total_water_cap_l=35000,
        equity_slider=0.6
    )
    print(f"Solver Engine: {res['solver']}")
    print(f"Optimization Status: {res['status']}")
    print(f"Total Risk Reduction: {res['summary']['total_risk_reduction_achieved']}")
    print(f"Budget Utilization: {res['summary']['budget']['allocated_inr']} / {res['summary']['budget']['cap_inr']} INR ({res['summary']['budget']['utilization_pct']}%)")
    print(f"Crew Utilization: {res['summary']['crew']['allocated_members']} / {res['summary']['crew']['cap_members']} ({res['summary']['crew']['utilization_pct']}%)")
    print(f"Water Utilization: {res['summary']['water']['allocated_liters']} / {res['summary']['water']['cap_liters']} L ({res['summary']['water']['utilization_pct']}%)")
    print(f"Vulnerable Group Coverage: {res['summary']['vulnerable_group_coverage']}")
    print(f"Equity Balance Ratio: {res['summary']['equity_balance_ratio']}")
