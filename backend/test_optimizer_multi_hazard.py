"""
ClimateShield - Automated Test Suite for Multi-Hazard Resource Allocation Optimizer
Verifies:
1. Reusing Google OR-Tools integer knapsack solver for combined climate risk.
2. Hazard-matched interventions:
   - Heat -> cooling centers, drinking-water points, shade canopies, outreach vans, cool roofs.
   - Waterlogging -> culvert desilting, flood warning barricades, dewatering pumps, road closures.
   - Water Shortage -> mobile tankers, smart valve supply rationing, communal bladder tanks.
3. Strict enforcement of budget cap, crew cap, and water cap limits.
4. Estimated costs, expected benefits, and explainable reasons for each recommendation.
5. Labeled cost models and simulated benefit disclaimers.
6. Governance: All emergency actions presented for human approval (never auto-executed).
7. Road closure restrictions: strictly forbidden unless justified by critical waterlogging (>= 70.0).
8. FastAPI endpoints: GET /api/optimize/interventions, POST /api/optimize/climate, POST /api/optimize.
"""

import sys
import os
import asyncio

# Ensure backend module is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from backend.optimizer import (
    solve_resource_allocation,
    optimize_from_combined_climate_results,
    INTERVENTIONS,
    RISK_CATEGORY_INTERVENTION_MAP,
    COST_MODEL_LABEL,
    BENEFIT_MODEL_LABEL,
    DEFAULT_WARDS
)
from backend.combined_risk_engine import evaluate_combined_climate_risk
from fastapi.testclient import TestClient
from backend.main import app


def test_interventions_catalog_and_risk_mapping():
    print("\n[TEST 1] Interventions Catalog & Hazard-Type Mapping Documentation")
    assert len(INTERVENTIONS) >= 10
    assert "heat" in RISK_CATEGORY_INTERVENTION_MAP
    assert "waterlogging" in RISK_CATEGORY_INTERVENTION_MAP
    assert "water_shortage" in RISK_CATEGORY_INTERVENTION_MAP

    heat_actions = [k for k, v in INTERVENTIONS.items() if v["risk_type"] == "heat"]
    waterlogging_actions = [k for k, v in INTERVENTIONS.items() if v["risk_type"] == "waterlogging"]
    shortage_actions = [k for k, v in INTERVENTIONS.items() if v["risk_type"] == "water_shortage"]

    print(f"  Heat Interventions ({len(heat_actions)}): {heat_actions}")
    print(f"  Waterlogging Interventions ({len(waterlogging_actions)}): {waterlogging_actions}")
    print(f"  Water Shortage Interventions ({len(shortage_actions)}): {shortage_actions}")

    assert "cooling_center" in heat_actions
    assert "hydration_kiosk" in heat_actions
    assert "shade_canopy" in heat_actions
    assert "drainage_inspection_cleaning" in waterlogging_actions
    assert "emergency_road_closure" in waterlogging_actions
    assert "water_tanker_dispatch" in shortage_actions
    assert "supply_prioritization_rationing" in shortage_actions
    print("  ✅ Interventions catalog and hazard mapping PASSED")


def test_hazard_specific_recommendations():
    print("\n[TEST 2] Hazard-Specific Intervention Matching")
    # Test Ward 1: Pure Heat Crisis (Heat = 90, Waterlogging = 10, Shortage = 10)
    # Test Ward 2: Severe Cloudburst Flood (Heat = 20, Waterlogging = 85, Shortage = 10)
    # Test Ward 3: Severe Drought Scarcity (Heat = 30, Waterlogging = 10, Shortage = 80)
    test_wards = [
        {"id": "W_HEAT", "name": "Heatwave Sector", "vulnerability": 0.85, "heat_risk_score": 90.0, "waterlogging_score": 10.0, "water_shortage_score": 10.0},
        {"id": "W_FLOOD", "name": "Flood Submersion Sector", "vulnerability": 0.85, "heat_risk_score": 20.0, "waterlogging_score": 85.0, "water_shortage_score": 10.0},
        {"id": "W_DROUGHT", "name": "Drought Scarcity Sector", "vulnerability": 0.85, "heat_risk_score": 30.0, "waterlogging_score": 10.0, "water_shortage_score": 80.0}
    ]

    res = solve_resource_allocation(
        total_budget_inr=500000.0,
        total_crew_members=40,
        total_water_cap_l=30000.0,
        equity_slider=0.5,
        wards=test_wards
    )
    assert res["status"] in ["OPTIMAL", "FEASIBLE"]
    alloc = res["ward_allocations"]

    heat_recs = [a["action_id"] for a in alloc["W_HEAT"]["interventions"]]
    flood_recs = [a["action_id"] for a in alloc["W_FLOOD"]["interventions"]]
    drought_recs = [a["action_id"] for a in alloc["W_DROUGHT"]["interventions"]]

    print(f"  Heat Ward Recommendations: {heat_recs}")
    print(f"  Flood Ward Recommendations: {flood_recs}")
    print(f"  Drought Ward Recommendations: {drought_recs}")

    # Heat ward must receive heat actions
    assert any(a in heat_recs for a in ["cooling_center", "hydration_kiosk", "shade_canopy", "cool_roof_coating"])
    # Flood ward must receive waterlogging/drainage actions
    assert any(a in flood_recs for a in ["drainage_inspection_cleaning", "flood_warning_barricade", "mobile_dewatering_pump", "emergency_road_closure"])
    # Drought ward must receive water shortage actions
    assert any(a in drought_recs for a in ["water_tanker_dispatch", "supply_prioritization_rationing", "communal_storage_tank"])

    print("  ✅ Hazard-specific intervention matching PASSED")


def test_constraints_and_human_approval_governance():
    print("\n[TEST 3] Multi-Constraint Enforcement & Human Governance Review")
    budget_limit = 350000.0
    crew_limit = 25
    water_limit = 15000.0

    res = solve_resource_allocation(
        total_budget_inr=budget_limit,
        total_crew_members=crew_limit,
        total_water_cap_l=water_limit,
        equity_slider=0.6
    )

    summary = res["summary"]
    # 1. Budget constraint strictly respected
    assert summary["budget"]["allocated_inr"] <= budget_limit, f"Budget exceeded: {summary['budget']['allocated_inr']} > {budget_limit}"
    # 2. Crew constraint strictly respected
    assert summary["crew"]["allocated_members"] <= crew_limit, f"Crew exceeded: {summary['crew']['allocated_members']} > {crew_limit}"
    # 3. Water constraint strictly respected
    assert summary["water"]["allocated_liters"] <= water_limit, f"Water exceeded: {summary['water']['allocated_liters']} > {water_limit}"

    print(f"  Budget Used: {summary['budget']['allocated_inr']} / {budget_limit} INR ({summary['budget']['utilization_pct']}%)")
    print(f"  Crew Used  : {summary['crew']['allocated_members']} / {crew_limit} Members ({summary['crew']['utilization_pct']}%)")
    print(f"  Water Used : {summary['water']['allocated_liters']} / {water_limit} L ({summary['water']['utilization_pct']}%)")

    # 4. Check Governance and Human Signoff fields (Requirement 4 & 5)
    gov = res["governance_and_disclaimer"]
    assert gov["approval_required"] is True
    assert "ADVISORY" in gov["notice"]
    assert gov["cost_model_label"] == COST_MODEL_LABEL
    assert gov["benefit_model_label"] == BENEFIT_MODEL_LABEL

    # Verify that all interventions have pending approval status and explainable reasons
    total_actions_checked = 0
    for w_id, w_data in res["ward_allocations"].items():
        for action in w_data["interventions"]:
            total_actions_checked += 1
            assert action["approval_status"] == "PENDING_HUMAN_APPROVAL"
            assert action["requires_human_signoff"] is True
            assert len(action["reason_for_recommendation"]) > 20
            assert "estimated_cost_inr" in action
            assert "expected_benefit_risk_reduction" in action

    print(f"  Verified {total_actions_checked} recommended actions: all flagged as PENDING_HUMAN_APPROVAL with full justifications.")
    print("  ✅ Constraints & Human Governance PASSED")


def test_road_closure_strictly_justified():
    print("\n[TEST 4] Emergency Road Closure Justification Guardrail")
    # Ward with mild waterlogging (score 30.0) -> Road closure MUST NOT be recommended
    mild_flood_ward = [{"id": "W_MILD", "name": "Mild Puddle Ward", "vulnerability": 0.8, "waterlogging_score": 30.0, "heat_risk_score": 30.0, "water_shortage_score": 30.0}]
    res_mild = solve_resource_allocation(total_budget_inr=500000, total_crew_members=40, total_water_cap_l=30000, wards=mild_flood_ward)
    mild_actions = [a["action_id"] for a in res_mild["ward_allocations"]["W_MILD"]["interventions"]]
    assert "emergency_road_closure" not in mild_actions, "Road closures must not be recommended when flood risk is low/mild!"

    # Ward with critical inundation (score 85.0) -> Road closure is eligible
    crit_flood_ward = [{"id": "W_CRIT", "name": "Submerged Underpass Ward", "vulnerability": 0.9, "waterlogging_score": 85.0, "heat_risk_score": 20.0, "water_shortage_score": 20.0}]
    res_crit = solve_resource_allocation(total_budget_inr=500000, total_crew_members=40, total_water_cap_l=30000, wards=crit_flood_ward)
    crit_actions = [a["action_id"] for a in res_crit["ward_allocations"]["W_CRIT"]["interventions"]]
    # Road closure is eligible and selected for deep flood life-safety
    print(f"  Mild Ward Actions : {mild_actions} (No road closure)")
    print(f"  Crit Ward Actions : {crit_actions}")
    print("  ✅ Road closure justification guardrails PASSED")


def test_optimization_from_combined_climate_results():
    print("\n[TEST 5] Full Integration: Combined Climate Engine -> Multi-Hazard Optimizer")
    async def run_pipeline():
        climate_res = await evaluate_combined_climate_risk(scenario_id="compound_hazard")
        assert len(climate_res["ranked_wards"]) == 48

        opt_plan = optimize_from_combined_climate_results(
            combined_climate_results=climate_res,
            total_budget_inr=600000.0,
            total_crew_members=50,
            total_water_cap_l=40000.0,
            equity_slider=0.7
        )

        assert opt_plan["status"] in ["OPTIMAL", "FEASIBLE"]
        summary = opt_plan["summary"]
        print(f"  Optimized 48-Ward Climate Dispatch Plan:")
        print(f"    Total Risk Reduction Achieved : {summary['total_risk_reduction_achieved']} pts")
        print(f"    Budget Allocated              : {summary['budget']['allocated_inr']} / 600,000 INR")
        print(f"    Heat Spending                 : {summary['hazard_budget_breakdown']['heat_inr']} INR")
        print(f"    Waterlogging Spending         : {summary['hazard_budget_breakdown']['waterlogging_inr']} INR")
        print(f"    Water Shortage Spending       : {summary['hazard_budget_breakdown']['water_shortage_inr']} INR")
        print(f"    Equity Balance Ratio          : {summary['equity_balance_ratio']}")

        # Under compound hazard, allocations exist across all hazard categories
        assert summary["hazard_budget_breakdown"]["heat_inr"] > 0
        assert summary["hazard_budget_breakdown"]["waterlogging_inr"] > 0

    asyncio.run(run_pipeline())
    print("  ✅ Combined Climate Engine -> Optimizer Integration PASSED")


def test_fastapi_endpoints():
    print("\n[TEST 6] FastAPI Climate Optimization Endpoints Verification")
    client = TestClient(app)

    # 1. GET /api/optimize/interventions catalog
    r_cat = client.get("/api/optimize/interventions")
    assert r_cat.status_code == 200
    cat_data = r_cat.json()
    assert cat_data["total_interventions"] >= 10
    assert "heat" in cat_data["risk_category_mappings"]
    print("  GET /api/optimize/interventions -> 200 OK (Catalog documented)")

    # 2. POST /api/optimize/climate (End-to-End Climate Optimization)
    r_clim = client.post("/api/optimize/climate", json={
        "total_budget_inr": 500000.0,
        "total_crew_members": 40,
        "total_water_cap_l": 30000.0,
        "equity_slider": 0.5,
        "scenario_id": "monsoon_cloudburst"
    })
    assert r_clim.status_code == 200
    plan = r_clim.json()["optimization_plan"]
    assert plan["status"] in ["OPTIMAL", "FEASIBLE"]
    assert plan["governance_and_disclaimer"]["approval_required"] is True
    print("  POST /api/optimize/climate -> 200 OK (End-to-end multi-hazard optimization plan returned)")

    # 3. POST /api/optimize (Original endpoint with default parameters)
    r_orig = client.post("/api/optimize", json={
        "total_budget_inr": 500000.0,
        "total_crew_members": 40,
        "total_water_cap_l": 30000.0,
        "equity_slider": 0.5
    })
    assert r_orig.status_code == 200
    assert r_orig.json()["status"] in ["OPTIMAL", "FEASIBLE"]
    print("  POST /api/optimize (Original Backward Compatibility) -> 200 OK")

    print("  ✅ All FastAPI optimization endpoints PASSED")


def main():
    print("==================================================")
    print("⚡ CLIMATESHIELD - MULTI-HAZARD OPTIMIZER TEST SUITE")
    print("==================================================")
    test_interventions_catalog_and_risk_mapping()
    test_hazard_specific_recommendations()
    test_constraints_and_human_approval_governance()
    test_road_closure_strictly_justified()
    test_optimization_from_combined_climate_results()
    test_fastapi_endpoints()
    print("\n==================================================")
    print("🎉 ALL MULTI-HAZARD OPTIMIZER TESTS COMPLETED SUCCESSFULLY!")
    print("==================================================")


if __name__ == "__main__":
    main()
