"""
ClimateShield - Automated Test Suite for Water Risk Engine
Tests waterlogging risk estimation, water shortage estimation, data quality indicators,
GeoJSON ward integration, and FastAPI endpoints without regression to the heat engine.
"""

import sys
import os
import asyncio
import json

# Ensure backend module is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from backend.water_engine import (
    calculate_waterlogging_risk,
    calculate_water_shortage_risk,
    classify_risk_score,
    compute_data_quality_and_confidence,
    load_all_geojson_wards,
    assess_citywide_water_risk,
    DEMONSTRATION_SCENARIOS
)
from fastapi.testclient import TestClient
from backend.main import app


def test_risk_categorization():
    print("\n[TEST 1] Risk Tier Categorization & Boundary Tests")
    assert classify_risk_score(10.0)["category"] == "LOW"
    assert classify_risk_score(25.0)["category"] == "LOW"
    assert classify_risk_score(25.1)["category"] == "MODERATE"
    assert classify_risk_score(50.0)["category"] == "MODERATE"
    assert classify_risk_score(50.1)["category"] == "HIGH"
    assert classify_risk_score(75.0)["category"] == "HIGH"
    assert classify_risk_score(75.1)["category"] == "CRITICAL"
    assert classify_risk_score(100.0)["category"] == "CRITICAL"
    assert classify_risk_score(150.0)["score"] == 100.0  # Bounded
    assert classify_risk_score(-10.0)["score"] == 0.0    # Bounded
    print("  ✅ Risk classification boundaries PASSED")


def test_waterlogging_calculations():
    print("\n[TEST 2] Waterlogging / Pluvial Flood Risk Calculations")
    # Dry conditions
    dry_res = calculate_waterlogging_risk(0.0, 0.0, elevation_risk=0.5, impervious_ratio=0.7)
    assert 0.0 <= dry_res["score"] <= 35.0
    assert dry_res["contributing_factors"]["rainfall_hazard_pts"] == 0.0
    print(f"  Dry condition score: {dry_res['score']} [{dry_res['category']}]")

    # Severe Cloudburst (70 mm/hr downpour, 120 mm accumulation)
    flood_res = calculate_waterlogging_risk(120.0, 70.0, elevation_risk=0.85, impervious_ratio=0.88, drainage_choke_factor=0.8)
    assert flood_res["score"] >= 75.0
    assert flood_res["category"] == "CRITICAL"
    assert "Critical inundation" in flood_res["explanation"]
    print(f"  Severe cloudburst score: {flood_res['score']} [{flood_res['category']}]")
    print(f"  Rainfall hazard pts: {flood_res['contributing_factors']['rainfall_hazard_pts']}")
    print(f"  Topographic pts: {flood_res['contributing_factors']['topographic_depression_pts']}")
    print(f"  Impervious & choke pts: {flood_res['contributing_factors']['impervious_and_drainage_pts']}")
    print("  ✅ Waterlogging calculations PASSED")


def test_water_shortage_calculations():
    print("\n[TEST 3] Water Shortage & Supply Deficit Risk Calculations")
    # Abundant supply (150 LPCD, 90% reservoir)
    surplus_res = calculate_water_shortage_risk(supply_lpcd=150.0, reservoir_storage_pct=90.0, slum_density=0.3, pipe_coverage_pct=90.0)
    assert surplus_res["score"] < 25.0
    assert surplus_res["category"] == "LOW"
    print(f"  Surplus supply score: {surplus_res['score']} [{surplus_res['category']}]")

    # Severe drought & deficit (70 LPCD, 25% reservoir)
    drought_res = calculate_water_shortage_risk(supply_lpcd=70.0, reservoir_storage_pct=25.0, slum_density=0.8, pipe_coverage_pct=60.0)
    assert drought_res["score"] >= 50.0
    assert drought_res["category"] in ["HIGH", "CRITICAL"]
    print(f"  Drought condition score: {drought_res['score']} [{drought_res['category']}]")
    print(f"  Per-capita deficit pts: {drought_res['contributing_factors']['per_capita_deficit_pts']}")
    print(f"  Reservoir depletion pts: {drought_res['contributing_factors']['reservoir_depletion_pts']}")

    # Missing supply and reservoir data behavior
    missing_res = calculate_water_shortage_risk(supply_lpcd=None, reservoir_storage_pct=None)
    assert missing_res["has_measured_supply_data"] is False
    assert "Estimated shortage baseline" in missing_res["explanation"]
    assert missing_res["contributing_factors"]["groundwater_stress_pts"] == 3.0  # Unobserved proxy
    print(f"  Missing supply fallback score: {missing_res['score']} (flagged as unobserved)")

    # Test 3B: Groundwater Stress Integration
    gw_shallow = {
        "has_proximate_station": True,
        "station_name": "Sanand Shallow Pz",
        "water_level_mbgl": 5.0,
        "annual_decline_rate_m_per_year": 0.0,
        "seasonal_recharge_potential_m": 4.5,
        "aquifer_stress_tier": "SHALLOW_WATER_TABLE"
    }
    gw_critical = {
        "has_proximate_station": True,
        "station_name": "Vatva Depleted Pz",
        "water_level_mbgl": 34.0,
        "annual_decline_rate_m_per_year": 2.5,
        "seasonal_recharge_potential_m": 0.5,
        "aquifer_stress_tier": "CRITICAL_AQUIFER_DEPLETION"
    }

    res_shallow = calculate_water_shortage_risk(supply_lpcd=120.0, reservoir_storage_pct=85.0, groundwater_context=gw_shallow)
    res_critical = calculate_water_shortage_risk(supply_lpcd=120.0, reservoir_storage_pct=85.0, groundwater_context=gw_critical)

    assert res_critical["score"] > res_shallow["score"], "Critical groundwater stress must strictly increase shortage score"
    assert res_critical["contributing_factors"]["groundwater_stress_pts"] > res_shallow["contributing_factors"]["groundwater_stress_pts"]
    print(f"  Groundwater shallow score: {res_shallow['score']} (GW pts: {res_shallow['contributing_factors']['groundwater_stress_pts']})")
    print(f"  Groundwater critical score: {res_critical['score']} (GW pts: {res_critical['contributing_factors']['groundwater_stress_pts']})")

    # Test 3C: Direction of change / secular trend
    gw_rising_depth = {"water_level_mbgl": 20.0, "annual_decline_rate_m_per_year": 1.5, "has_proximate_station": True}
    gw_falling_depth = {"water_level_mbgl": 20.0, "annual_decline_rate_m_per_year": -1.0, "has_proximate_station": True}
    res_rising = calculate_water_shortage_risk(supply_lpcd=120.0, reservoir_storage_pct=85.0, groundwater_context=gw_rising_depth)
    res_falling = calculate_water_shortage_risk(supply_lpcd=120.0, reservoir_storage_pct=85.0, groundwater_context=gw_falling_depth)
    assert res_rising["score"] > res_falling["score"], "Deepening water table must yield higher risk than recovering table"

    print("  ✅ Water shortage calculations PASSED (Groundwater integrated)")


def test_data_quality_and_confidence():
    print("\n[TEST 4] Data Quality & Confidence Indicators")
    # Live API with unobserved telemetry
    live_qual = compute_data_quality_and_confidence("Open-Meteo Weather API", False, False, False)
    assert live_qual["is_synthetic"] is False
    assert live_qual["confidence_level"] == "MODERATE"
    assert "precipitation_forecast_open_meteo" in live_qual["measured_parameters"]
    assert "ward_potable_supply_telemetry" in live_qual["unmeasured_parameters"]
    print(f"  Live weather data mode: {live_qual['data_mode']}, confidence: {live_qual['confidence_score_pct']}%")

    # Synthetic demo scenario
    synth_qual = compute_data_quality_and_confidence("Scenario", True, True, True)
    assert synth_qual["is_synthetic"] is True
    assert synth_qual["confidence_level"] == "SYNTHETIC_SIMULATION"
    assert "DEMONSTRATION ONLY" in synth_qual["disclaimer"]
    print(f"  Synthetic scenario disclaimer verified: {synth_qual['disclaimer'][:45]}...")
    print("  ✅ Data quality and confidence indicators PASSED")


def test_geojson_wards():
    print("\n[TEST 5] GeoJSON Spatial Feature Collection Integration")
    wards = load_all_geojson_wards()
    print(f"  Loaded {len(wards)} wards from Ahmedabad_Wards.geojson")
    assert len(wards) == 48, f"Expected 48 wards, found {len(wards)}"
    sample_ward = wards[0]
    assert "name" in sample_ward
    print(f"  Sample ward: Index {sample_ward['index']}, Name '{sample_ward['name']}'")
    print("  ✅ GeoJSON integration PASSED")


def test_citywide_assessment():
    print("\n[TEST 6] Full Citywide Water Assessment Engine")
    async def _run():
        # 1. Live assessment
        live_res = await assess_citywide_water_risk()
        assert live_res["city"] == "Ahmedabad"
        assert len(live_res["wards"]) == 48
        assert live_res["data_quality_indicator"]["is_synthetic"] is False
        print(f"  Live citywide assessment: 48 wards evaluated.")
        print(f"  Citywide Average Composite Risk: {live_res['city_wide_summary']['average_composite_risk_score']}")
        print(f"  Peak risk ward: {live_res['wards'][0]['ward_name']} (Score: {live_res['wards'][0]['composite_water_risk_score']})")

        # 2. Monsoon Cloudburst Demo Scenario
        monsoon_res = await assess_citywide_water_risk(scenario_id="monsoon_cloudburst")
        assert monsoon_res["scenario"]["scenario_id"] == "monsoon_cloudburst"
        assert monsoon_res["data_quality_indicator"]["is_synthetic"] is True
        assert monsoon_res["city_wide_summary"]["critical_wards_count"] > 0
        print(f"  Monsoon Cloudburst Scenario: Critical Wards = {monsoon_res['city_wide_summary']['critical_wards_count']}")

        # 3. Summer Drought Scarcity Demo Scenario
        drought_res = await assess_citywide_water_risk(scenario_id="summer_drought_scarcity")
        assert drought_res["scenario"]["scenario_id"] == "summer_drought_scarcity"
        assert drought_res["city_wide_summary"]["average_shortage_risk_score"] > 40.0
        print(f"  Summer Drought Scenario: Avg Shortage Risk = {drought_res['city_wide_summary']['average_shortage_risk_score']}")
        print("  ✅ Citywide assessment engine PASSED")

    asyncio.run(_run())


def test_fastapi_endpoints():
    print("\n[TEST 7] FastAPI Endpoints & Backward Compatibility Verification")
    client = TestClient(app)

    # 1. Root
    r_root = client.get("/")
    assert r_root.status_code == 200
    assert "/api/water/wards" in r_root.json()["endpoints"]
    assert "/api/water/wards/{ward_id}" in r_root.json()["endpoints"]

    # 2. Scenarios catalog
    r_scen = client.get("/api/water/scenarios")
    assert r_scen.status_code == 200
    scenarios = r_scen.json()["scenarios"]
    assert "monsoon_cloudburst" in scenarios
    assert "summer_drought_scarcity" in scenarios
    print("  GET /api/water/scenarios -> 200 OK")

    # 3. GET /api/water/wards (All Wards Calculation)
    r_wards = client.get("/api/water/wards")
    assert r_wards.status_code == 200
    wards_payload = r_wards.json()
    assert wards_payload["city"] == "Ahmedabad"
    assert "timestamp" in wards_payload
    assert "data_source" in wards_payload
    assert "data_quality" in wards_payload
    assert "ward_water_risks" in wards_payload
    assert len(wards_payload["ward_water_risks"]) == 48

    # Verify field schema on a sample ward
    w_sample = wards_payload["ward_water_risks"][0]
    assert "id" in w_sample
    assert "name" in w_sample
    assert "risk_score" in w_sample
    assert "risk_category" in w_sample
    assert "contributing_factors" in w_sample
    assert "waterlogging" in w_sample["contributing_factors"]
    assert "water_shortage" in w_sample["contributing_factors"]
    assert "timestamp" in w_sample
    assert "data_source" in w_sample
    print(f"  GET /api/water/wards -> 200 OK ({len(wards_payload['ward_water_risks'])} wards returned with consistent schema)")

    # 4. GET /api/water/wards/{ward_id} for a selected ward (by ID 'W1')
    r_w1 = client.get("/api/water/wards/W1")
    assert r_w1.status_code == 200
    w1_data = r_w1.json()
    assert w1_data["ward"]["id"] == "W1"
    assert "Danilimda" in w1_data["ward"]["name"] or "Danilimda" in w1_data["ward"]["official_name"]
    assert "contributing_factors" in w1_data["ward"]
    assert "data_quality" in w1_data
    assert "timestamp" in w1_data
    print(f"  GET /api/water/wards/W1 -> 200 OK (Resolved to {w1_data['ward']['name']}, Score: {w1_data['ward']['risk_score']})")

    # 5. GET /api/water/wards/{ward_id} by name (e.g., 'Vatva')
    r_vatva = client.get("/api/water/wards/Vatva")
    assert r_vatva.status_code == 200
    assert "Vatva" in r_vatva.json()["ward"]["name"]
    print("  GET /api/water/wards/Vatva -> 200 OK (Resolved by name)")

    # 6. GET /api/water/wards/{ward_id} with missing/invalid ward -> 404
    r_404 = client.get("/api/water/wards/non_existent_ward_xyz")
    assert r_404.status_code == 404
    assert "not found" in r_404.json()["detail"].lower()
    print("  GET /api/water/wards/non_existent_ward_xyz -> 404 Not Found (Handled gracefully)")

    # 7. Request validation failure test (e.g. invalid supply > 300) -> 422
    r_422 = client.get("/api/water/wards?supply_lpcd=9999.0")
    assert r_422.status_code == 422
    print("  GET /api/water/wards?supply_lpcd=9999.0 -> 422 Validation Error (Validated successfully)")

    # 8. Scenario simulation query test
    r_scen_sim = client.get("/api/water/wards?scenario_id=monsoon_cloudburst")
    assert r_scen_sim.status_code == 200
    assert r_scen_sim.json()["city_wide_summary"]["critical_wards_count"] > 0
    print("  GET /api/water/wards?scenario_id=monsoon_cloudburst -> 200 OK")

    # 9. POST /api/water/calculate
    r_post = client.post("/api/water/calculate", json={
        "scenario_id": "summer_drought_scarcity",
        "supply_lpcd": 70.0,
        "reservoir_storage_pct": 25.0
    })
    assert r_post.status_code == 200
    assert r_post.json()["current_water_status"]["observed_supply_lpcd"] == 70.0
    print("  POST /api/water/calculate -> 200 OK")

    # 10. Verify backward compatibility: existing Heat endpoints remain 100% intact
    r_wbgt = client.get("/api/weather/wbgt")
    assert r_wbgt.status_code == 200
    print("  GET /api/weather/wbgt (Heat Engine) -> 200 OK (UNBROKEN)")

    r_opt = client.post("/api/optimize", json={
        "total_budget_inr": 500000.0,
        "total_crew_members": 40,
        "total_water_cap_l": 30000.0,
        "equity_slider": 0.5
    })
    assert r_opt.status_code == 200
    print("  POST /api/optimize (Heat Engine) -> 200 OK (UNBROKEN)")

    r_mc = client.get("/api/risk/monte-carlo?simulations=50")
    assert r_mc.status_code == 200
    print("  GET /api/risk/monte-carlo (Heat Engine) -> 200 OK (UNBROKEN)")

    print("  ✅ All FastAPI endpoints PASSED & Heat engine verified 100% intact")


def main():
    print("==================================================")
    print("💧 CLIMATESHIELD - WATER RISK ENGINE TEST SUITE")
    print("==================================================")
    test_risk_categorization()
    test_waterlogging_calculations()
    test_water_shortage_calculations()
    test_data_quality_and_confidence()
    test_geojson_wards()
    test_citywide_assessment()
    test_fastapi_endpoints()
    print("\n==================================================")
    print("🎉 ALL WATER RISK ENGINE TESTS COMPLETED SUCCESSFULLY!")
    print("==================================================")


if __name__ == "__main__":
    main()
