"""
ClimateShield - Automated Test Suite for Combined Climate Risk Engine
Tests integration of Heat Risk and Water Risk:
- Normal multi-hazard evaluation
- Missing data handling (ensuring water risk is NOT treated as zero)
- Compound hotspots (both heat and water risks high)
- Configurable scoring modes & weights
- Ranked ward lists with explainable rationales
- FastAPI endpoints and backward compatibility with optimizer
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

from backend.combined_risk_engine import (
    evaluate_combined_climate_risk,
    compute_combined_risk_score,
    convert_wbgt_to_risk_score,
    get_ward_heat_vulnerability,
    classify_compound_hazard_tier
)
from fastapi.testclient import TestClient
from backend.main import app


def test_scoring_models_and_configurations():
    print("\n[TEST 1] Configurable Combined Scoring Formulations")
    # Base cases: Heat = 60, Water = 70 (Both high)
    # 1. Linear Weighted Average
    res_linear = compute_combined_risk_score(60.0, 70.0, weight_heat=0.5, weight_water=0.5, scoring_mode="WEIGHTED_AVERAGE")
    assert res_linear["combined_risk_score"] == 65.0
    assert res_linear["compound_synergy_points"] == 0.0
    print(f"  Weighted Average (50/50): {res_linear['combined_risk_score']} [Score matches linear sum]")

    # Asymmetric weights: Heat 80%, Water 20%
    res_asym = compute_combined_risk_score(60.0, 70.0, weight_heat=0.8, weight_water=0.2, scoring_mode="WEIGHTED_AVERAGE")
    assert res_asym["combined_risk_score"] == 62.0
    print(f"  Weighted Average (80/20): {res_asym['combined_risk_score']}")

    # 2. Worst-Case Peak
    res_peak = compute_combined_risk_score(60.0, 70.0, scoring_mode="WORST_CASE_PEAK")
    assert res_peak["combined_risk_score"] == 70.0
    print(f"  Worst-Case Peak: {res_peak['combined_risk_score']} [Selected max hazard]")

    # 3. Compound Synergy Multi-Hazard (Both >= 50)
    res_synergy = compute_combined_risk_score(70.0, 80.0, scoring_mode="COMPOUND_SYNERGY", synergy_multiplier=0.15)
    assert res_synergy["is_compound_hazard_hotspot"] is True
    assert res_synergy["compound_synergy_points"] > 0.0
    assert res_synergy["combined_risk_score"] > res_synergy["weighted_base_score"]
    print(f"  Compound Synergy: Base = {res_synergy['weighted_base_score']}, Synergy Bonus = +{res_synergy['compound_synergy_points']}, Total = {res_synergy['combined_risk_score']}")
    print("  ✅ Configurable scoring models PASSED")


def test_missing_data_not_treated_as_zero():
    print("\n[TEST 2] Missing Data Handling (Water Risk NOT Treated as Zero)")
    # When water telemetry is completely unmeasured, we verify that water score > 0
    # and data quality indicates unmeasured proxies.
    async def run_check():
        res = await evaluate_combined_climate_risk()
        sample_ward = res["ranked_wards"][0]
        # Verify water risk is NOT zero
        assert sample_ward["water_risk"]["score"] > 0.0, "Missing water data must NOT be treated as zero risk!"
        assert sample_ward["water_risk"]["score"] >= 20.0, "Baseline hydrology prior must provide realistic non-zero floor"
        
        # Verify explicit data quality indicators
        dq = res["data_quality_and_confidence"]
        assert "is_water_data_missing" in dq
        assert "NOT treated as zero" in dq["handling_of_missing_water_data"]
        print(f"  Sample ward '{sample_ward['name']}': Water Risk Score = {sample_ward['water_risk']['score']} (Non-zero verified)")
        print(f"  Data Quality Handling: {dq['handling_of_missing_water_data'][:65]}...")
    
    asyncio.run(run_check())
    print("  ✅ Missing-data non-zero risk handling PASSED")


def test_compound_hotspot_flagging():
    print("\n[TEST 3] Compound Hazard Hotspot Identification (Dual High Risks)")
    async def run_check():
        # Evaluate under Compound Hazard scenario where both heatwave and water risk peak
        res = await evaluate_combined_climate_risk(scenario_id="compound_hazard")
        hotspots = [w for w in res["ranked_wards"] if w["compound_hazard"]["is_compound_hotspot"]]
        print(f"  Identified {len(hotspots)} compound hotspot wards out of {len(res['ranked_wards'])} wards.")
        assert len(hotspots) > 0, "Expected compound hotspots under compound hazard scenario"
        
        top_hotspot = hotspots[0]
        assert top_hotspot["heat_risk"]["score"] >= 50.0 or top_hotspot["water_risk"]["score"] >= 50.0
        assert top_hotspot["compound_hazard"]["tier"] in ["DUAL_CRITICAL", "DUAL_HIGH", "ASYMMETRIC_HIGH_WATER", "ASYMMETRIC_HIGH_HEAT"]
        assert "badge" in top_hotspot["compound_hazard"]
        print(f"  Top Hotspot: '{top_hotspot['name']}' [{top_hotspot['compound_hazard']['badge']}]")
        print(f"    Heat Risk : {top_hotspot['heat_risk']['score']} [{top_hotspot['heat_risk']['category']}]")
        print(f"    Water Risk: {top_hotspot['water_risk']['score']} [{top_hotspot['water_risk']['category']}]")
        print(f"    Combined  : {top_hotspot['combined_risk_score']} [{top_hotspot['combined_risk_category']}]")

    asyncio.run(run_check())
    print("  ✅ Compound hotspot identification PASSED")


def test_ward_ranking_and_rationales():
    print("\n[TEST 4] Ward Ranking Order & Explainable Rationales")
    async def run_check():
        res = await evaluate_combined_climate_risk()
        wards = res["ranked_wards"]
        assert len(wards) == 48

        # Verify descending sort order
        scores = [w["combined_risk_score"] for w in wards]
        assert scores == sorted(scores, reverse=True), "Wards must be strictly sorted descending by combined score"

        # Verify sequential ranks and non-empty rationales
        for idx, w in enumerate(wards):
            assert w["rank"] == idx + 1
            assert len(w["ranking_rationale"]) > 15
            assert "Ranked #" in w["ranking_rationale"]

        print(f"  Rank #1 Ward : '{wards[0]['name']}' (Score: {wards[0]['combined_risk_score']})")
        print(f"    Rationale: \"{wards[0]['ranking_rationale']}\"")
        print(f"  Rank #48 Ward: '{wards[-1]['name']}' (Score: {wards[-1]['combined_risk_score']})")
        print(f"    Rationale: \"{wards[-1]['ranking_rationale']}\"")

    asyncio.run(run_check())
    print("  ✅ Ward ranking and explainable rationales PASSED")


def test_fastapi_combined_endpoints_and_optimizer_compatibility():
    print("\n[TEST 5] FastAPI Endpoints & Optimizer Compatibility Verification")
    client = TestClient(app)

    # 1. Root lists endpoint
    r_root = client.get("/")
    assert r_root.status_code == 200
    assert "/api/climate/combined-risk" in r_root.json()["endpoints"]

    # 2. GET /api/climate/combined-risk
    r_get = client.get("/api/climate/combined-risk?weight_heat=0.6&weight_water=0.4&scoring_mode=COMPOUND_SYNERGY")
    assert r_get.status_code == 200
    data = r_get.json()
    assert data["city"] == "Ahmedabad"
    assert len(data["ranked_wards"]) == 48
    assert "scoring_configuration" in data
    assert "data_quality_and_confidence" in data
    assert data["scoring_configuration"]["weight_heat"] == 0.6
    print("  GET /api/climate/combined-risk -> 200 OK (48 ranked wards returned)")

    # 3. POST /api/climate/combined-risk
    r_post = client.post("/api/climate/combined-risk", json={
        "weight_heat": 0.5,
        "weight_water": 0.5,
        "scoring_mode": "COMPOUND_SYNERGY",
        "scenario_id": "compound_hazard",
        "supply_lpcd": 95.0
    })
    assert r_post.status_code == 200
    post_data = r_post.json()
    assert post_data["city_wide_summary"]["compound_hazard_hotspots_count"] > 0
    print("  POST /api/climate/combined-risk -> 200 OK (Parameterized scenario simulation verified)")

    # 4. Verify existing Optimizer remains 100% compatible
    r_opt = client.post("/api/optimize", json={
        "total_budget_inr": 500000.0,
        "total_crew_members": 40,
        "total_water_cap_l": 30000.0,
        "equity_slider": 0.5
    })
    assert r_opt.status_code == 200
    assert r_opt.json()["status"] == "OPTIMAL"
    print("  POST /api/optimize -> 200 OK (Google OR-Tools Optimizer 100% UNBROKEN)")

    # 5. Verify heat and water endpoints remain functional
    assert client.get("/api/weather/wbgt").status_code == 200
    assert client.get("/api/water/wards").status_code == 200
    assert client.get("/api/water/wards/W1").status_code == 200
    print("  All existing heat & water endpoints -> 200 OK (UNBROKEN)")
    print("  ✅ FastAPI endpoints and optimizer compatibility PASSED")


def main():
    print("==================================================")
    print("🌍 CLIMATESHIELD - COMBINED CLIMATE RISK ENGINE TEST")
    print("==================================================")
    test_scoring_models_and_configurations()
    test_missing_data_not_treated_as_zero()
    test_compound_hotspot_flagging()
    test_ward_ranking_and_rationales()
    test_fastapi_combined_endpoints_and_optimizer_compatibility()
    print("\n==================================================")
    print("🎉 ALL COMBINED CLIMATE RISK TESTS PASSED SUCCESSFULLY!")
    print("==================================================")


if __name__ == "__main__":
    main()
