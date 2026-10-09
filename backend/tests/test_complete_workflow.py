"""
ClimateShield - Complete Backend Workflow Test Suite
Comprehensive automated test suite covering:
1. Heat Pipeline (WBGT physics, risk classification, forecast processing).
2. Water Risk Engine (Waterlogging, shortage, ward-level 0-100 scoring, classifications).
3. Water API Endpoints (/api/water/wards, /api/water/wards/{id}, /api/water/risk, /api/water/scenarios).
4. Combined Climate Risk Engine (Geographic matching, heat/water separation, compound synergy).
5. Multi-Hazard Optimizer (Resource caps, hazard-matched interventions, human approval flags).
6. Missing/Unavailable Data Handling (Non-zero hydrology priors, offline weather fallback).
7. Error Handling & Malformed Inputs (404 for unknown wards, 422 for out-of-range parameters).

All tests use deterministic mocks for external APIs so they run 100% offline and repeatably.
Compatible with both `pytest` and `python -m unittest`.
"""

import sys
import os
import unittest
from unittest.mock import patch, AsyncMock
import json

# Ensure workspace root is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi.testclient import TestClient
from backend.main import app
from backend.wbgt_pipeline import (
    calculate_stull_natural_wet_bulb,
    calculate_swbgt,
    calculate_outdoor_wbgt,
    classify_wbgt_risk,
    process_wbgt_forecast
)
from backend.water_engine import (
    calculate_waterlogging_risk,
    calculate_water_shortage_risk,
    classify_risk_score,
    compute_data_quality_and_confidence,
    assess_citywide_water_risk,
    get_single_ward_water_risk
)
from backend.combined_risk_engine import (
    evaluate_combined_climate_risk,
    compute_combined_risk_score,
    classify_compound_hazard_tier
)
from backend.optimizer import (
    solve_resource_allocation,
    optimize_from_combined_climate_results,
    INTERVENTIONS,
    RISK_CATEGORY_INTERVENTION_MAP
)

# -------------------------------------------------------------
# MOCK FIXTURES FOR OFFLINE / DETERMINISTIC TESTS
# -------------------------------------------------------------

MOCK_OPEN_METEO_WEATHER_PAYLOAD = {
    "latitude": 23.0225,
    "longitude": 72.5714,
    "hourly": {
        "time": [f"2026-10-10T{h:02d}:00" for h in range(24)],
        "temperature_2m": [28.0 + (10.0 if 12 <= h <= 15 else 2.0) for h in range(24)],
        "relative_humidity_2m": [45.0 for _ in range(24)],
        "direct_normal_irradiance": [750.0 if 10 <= h <= 16 else 0.0 for h in range(24)],
        "wind_speed_10m": [2.5 for _ in range(24)],
        "precipitation": [0.0 for _ in range(24)],
        "precipitation_probability": [0 for _ in range(24)]
    }
}

MOCK_OPEN_METEO_RAIN_PAYLOAD = {
    "source": "Open-Meteo Weather API",
    "is_measured_or_forecast": True,
    "timestamp": "2026-10-10T14:00:00Z",
    "coordinates": {"latitude": 23.0225, "longitude": 72.5714},
    "rainfall_24h_cumulative_mm": 5.0,
    "peak_hourly_rainfall_mm": 2.0,
    "max_precipitation_probability_pct": 25,
    "hourly_series": [{"timestamp": f"2026-10-10T{h:02d}:00", "precipitation_mm": 0.2, "probability_pct": 20} for h in range(24)]
}


class TestCompleteBackendWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    # =========================================================
    # 1. VERIFY: EXISTING HEAT PIPELINE STILL WORKS
    # =========================================================
    def test_01_heat_physics_calculations(self):
        """Verifies Stull empirical wet-bulb, sWBGT, and outdoor WBGT formulas."""
        tnw = calculate_stull_natural_wet_bulb(temp_c=38.0, rh_percent=30.0)
        swbgt = calculate_swbgt(temp_c=38.0, rh_percent=30.0)
        wbgt_outdoor = calculate_outdoor_wbgt(temp_c=38.0, rh_percent=30.0, direct_radiation_wm2=800.0, wind_speed_ms=2.0)

        self.assertTrue(22.0 <= tnw <= 26.0, f"Unexpected natural wet bulb: {tnw}")
        self.assertTrue(30.0 <= swbgt <= 35.0, f"Unexpected sWBGT: {swbgt}")
        self.assertTrue(wbgt_outdoor > tnw, "Outdoor WBGT must incorporate solar radiative gain")

        risk_mod = classify_wbgt_risk(28.5)
        self.assertEqual(risk_mod["tier"], "MODERATE")
        risk_crit = classify_wbgt_risk(34.0)
        self.assertEqual(risk_crit["tier"], "CRITICAL")

    @patch("backend.wbgt_pipeline.fetch_open_meteo_weather", new_callable=AsyncMock)
    def test_02_heat_endpoint_with_mock_weather(self, mock_fetch):
        """Verifies GET /api/weather/wbgt returns proper heat risk series using mock API response."""
        mock_fetch.return_value = MOCK_OPEN_METEO_WEATHER_PAYLOAD
        resp = self.client.get("/api/weather/wbgt")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["city"], "Ahmedabad")
        self.assertIn("current_heat_status", data)
        self.assertIn("ward_heat_risks", data)
        self.assertEqual(len(data["ward_heat_risks"]), 10)
        self.assertIn("effective_wbgt_c", data["ward_heat_risks"][0])

    # =========================================================
    # 2. VERIFY: WATER ENGINE CALCULATES AND CLASSIFIES WARD RISKS
    # =========================================================
    def test_03_waterlogging_risk_calculation(self):
        """Tests waterlogging flood risk scores and factor contributions."""
        # Dry case
        res_dry = calculate_waterlogging_risk(0.0, 0.0, elevation_risk=0.5, impervious_ratio=0.6)
        self.assertTrue(res_dry["score"] <= 35.0)
        self.assertEqual(res_dry["contributing_factors"]["rainfall_hazard_pts"], 0.0)

        # Torrential cloudburst case
        res_flood = calculate_waterlogging_risk(120.0, 65.0, elevation_risk=0.85, impervious_ratio=0.88, drainage_choke_factor=0.8)
        self.assertTrue(res_flood["score"] >= 75.0)
        self.assertEqual(res_flood["category"], "CRITICAL")
        self.assertIn("rainfall_hazard_pts", res_flood["contributing_factors"])
        self.assertIn("topographic_depression_pts", res_flood["contributing_factors"])
        self.assertIn("impervious_and_drainage_pts", res_flood["contributing_factors"])

    def test_04_water_shortage_risk_calculation(self):
        """Tests water shortage scoring against the 140 LPCD urban benchmark."""
        # Adequate supply (140 LPCD, 80% reservoir)
        res_adequate = calculate_water_shortage_risk(supply_lpcd=140.0, reservoir_storage_pct=80.0, slum_density=0.3, pipe_coverage_pct=90.0)
        self.assertTrue(res_adequate["score"] <= 25.0)
        self.assertEqual(res_adequate["category"], "LOW")

        # Acute deficit (70 LPCD, 30% reservoir)
        res_deficit = calculate_water_shortage_risk(supply_lpcd=70.0, reservoir_storage_pct=30.0, slum_density=0.8, pipe_coverage_pct=60.0)
        self.assertTrue(res_deficit["score"] >= 50.0)
        self.assertIn(res_deficit["category"], ["HIGH", "CRITICAL"])
        self.assertTrue(res_deficit["contributing_factors"]["per_capita_deficit_pts"] > 20.0)

    # =========================================================
    # 3. VERIFY: NEW WATER ENDPOINTS RETURN VALID RESPONSES
    # =========================================================
    @patch("backend.water_engine.fetch_open_meteo_rainfall", new_callable=AsyncMock)
    def test_05_water_wards_endpoints(self, mock_fetch_rain):
        """Verifies GET /api/water/wards and GET /api/water/wards/{id} endpoints."""
        mock_fetch_rain.return_value = MOCK_OPEN_METEO_RAIN_PAYLOAD

        # All wards endpoint
        r_all = self.client.get("/api/water/wards")
        self.assertEqual(r_all.status_code, 200)
        data_all = r_all.json()
        self.assertEqual(data_all["city"], "Ahmedabad")
        self.assertEqual(len(data_all["ward_water_risks"]), 48)

        # Single ward by ID
        r_w1 = self.client.get("/api/water/wards/W1")
        self.assertEqual(r_w1.status_code, 200)
        data_w1 = r_w1.json()
        self.assertEqual(data_w1["ward"]["id"], "W1")
        self.assertIn("contributing_factors", data_w1["ward"])

        # Single ward by Name
        r_name = self.client.get("/api/water/wards/Vatva")
        self.assertEqual(r_name.status_code, 200)
        self.assertIn("Vatva", r_name.json()["ward"]["name"])

        # Scenarios endpoint
        r_scen = self.client.get("/api/water/scenarios")
        self.assertEqual(r_scen.status_code, 200)
        self.assertIn("monsoon_cloudburst", r_scen.json()["scenarios"])

    # =========================================================
    # 4. VERIFY: COMBINED RISK ENGINE CORRECTLY MATCHES WARD DATA
    # =========================================================
    @patch("backend.combined_risk_engine.fetch_open_meteo_weather", new_callable=AsyncMock)
    @patch("backend.combined_risk_engine.assess_citywide_water_risk", new_callable=AsyncMock)
    def test_06_combined_climate_risk_matching(self, mock_water, mock_weather):
        """Tests 1-to-1 geographic matching of heat and water data across all 48 wards."""
        mock_weather.return_value = MOCK_OPEN_METEO_WEATHER_PAYLOAD
        
        # Return mock 48-ward water list
        mock_water.return_value = {
            "city": "Ahmedabad",
            "data_source": "Mock Water Model",
            "data_quality": {"is_synthetic": False, "unmeasured_parameters": []},
            "ward_water_risks": [
                {
                    "id": f"W{i+1}",
                    "ward_index": i,
                    "name": f"Ward_{i+1}",
                    "risk_score": 40.0 + (i % 30),
                    "risk_category": "MODERATE",
                    "risk_color": "#F59E0B",
                    "contributing_factors": {
                        "waterlogging": {"score": 35.0, "category": "MODERATE"},
                        "water_shortage": {"score": 40.0, "category": "MODERATE"}
                    }
                }
                for i in range(48)
            ]
        }

        r_comb = self.client.get("/api/climate/combined-risk?weight_heat=0.5&weight_water=0.5&scoring_mode=COMPOUND_SYNERGY")
        self.assertEqual(r_comb.status_code, 200)
        data_comb = r_comb.json()

        self.assertEqual(len(data_comb["ranked_wards"]), 48)
        # Check strict descending sort
        scores = [w["combined_risk_score"] for w in data_comb["ranked_wards"]]
        self.assertEqual(scores, sorted(scores, reverse=True))

        # Check distinct dimensions on sample ward
        first = data_comb["ranked_wards"][0]
        self.assertIn("heat_risk", first)
        self.assertIn("water_risk", first)
        self.assertIn("combined_risk_score", first)
        self.assertIn("ranking_rationale", first)
        self.assertEqual(first["rank"], 1)

    # =========================================================
    # 5. VERIFY: OPTIMIZER PRODUCES VALID RECOMMENDATIONS
    # =========================================================
    def test_07_optimizer_produces_hazard_matched_recommendations(self):
        """Tests that the optimizer respects budget/crew/water caps and recommends hazard-matched actions."""
        # Simulated test wards with distinct hazard dominances
        custom_wards = [
            {"id": "W_HEAT_1", "name": "Heatwave Core", "vulnerability": 0.85, "heat_risk_score": 92.0, "waterlogging_score": 15.0, "water_shortage_score": 10.0},
            {"id": "W_FLOOD_1", "name": "Flood Basin", "vulnerability": 0.85, "heat_risk_score": 15.0, "waterlogging_score": 88.0, "water_shortage_score": 10.0},
            {"id": "W_SHORT_1", "name": "Dry Informal Cluster", "vulnerability": 0.85, "heat_risk_score": 25.0, "waterlogging_score": 10.0, "water_shortage_score": 82.0}
        ]

        budget_cap = 400000.0
        crew_cap = 30
        water_cap = 25000.0

        plan = solve_resource_allocation(
            total_budget_inr=budget_cap,
            total_crew_members=crew_cap,
            total_water_cap_l=water_cap,
            equity_slider=0.5,
            wards=custom_wards
        )

        self.assertIn(plan["status"], ["OPTIMAL", "FEASIBLE"])
        summary = plan["summary"]
        self.assertTrue(summary["budget"]["allocated_inr"] <= budget_cap)
        self.assertTrue(summary["crew"]["allocated_members"] <= crew_cap)
        self.assertTrue(summary["water"]["allocated_liters"] <= water_cap)

        alloc = plan["ward_allocations"]
        heat_actions = [a["action_id"] for a in alloc["W_HEAT_1"]["interventions"]]
        flood_actions = [a["action_id"] for a in alloc["W_FLOOD_1"]["interventions"]]
        shortage_actions = [a["action_id"] for a in alloc["W_SHORT_1"]["interventions"]]

        # Heat ward received heat actions
        self.assertTrue(any(a in heat_actions for a in ["cooling_center", "hydration_kiosk", "shade_canopy", "cool_roof_coating"]))
        # Flood ward received drainage / flood warning / dewatering actions
        self.assertTrue(any(a in flood_actions for a in ["drainage_inspection_cleaning", "flood_warning_barricade", "mobile_dewatering_pump", "emergency_road_closure"]))
        # Shortage ward received water tanker / valve / storage actions
        self.assertTrue(any(a in shortage_actions for a in ["water_tanker_dispatch", "supply_prioritization_rationing", "communal_storage_tank"]))

        # Check Human Authorization flags on all recommended interventions
        for w_id in alloc:
            for act in alloc[w_id]["interventions"]:
                self.assertEqual(act["approval_status"], "PENDING_HUMAN_APPROVAL")
                self.assertTrue(act["requires_human_signoff"])
                self.assertTrue(len(act["reason_for_recommendation"]) > 10)

    # =========================================================
    # 6. VERIFY: MISSING OR UNAVAILABLE DATA IS HANDLED SAFELY
    # =========================================================
    def test_08_missing_water_data_not_treated_as_zero(self):
        """Verifies missing water telemetry defaults to non-zero structural prior with uncertainty margin."""
        res_missing = calculate_water_shortage_risk(supply_lpcd=None, reservoir_storage_pct=None)
        self.assertFalse(res_missing["has_measured_supply_data"])
        self.assertFalse(res_missing["has_measured_reservoir_data"])
        # Must NOT be zero
        self.assertTrue(res_missing["score"] >= 20.0, "Missing supply data must never be treated as zero risk!")
        self.assertIn("Estimated shortage baseline", res_missing["explanation"])

        # Check confidence indicator flags unmeasured telemetry
        conf = compute_data_quality_and_confidence("Open-Meteo Weather API", False, False, False)
        self.assertIn("ward_potable_supply_telemetry", conf["unmeasured_parameters"])
        self.assertEqual(conf["confidence_level"], "MODERATE")

    # =========================================================
    # 7. VERIFY: API ERRORS AND MALFORMED INPUTS ARE HANDLED PROPERLY
    # =========================================================
    def test_09_api_validation_and_not_found_errors(self):
        """Tests that invalid inputs trigger HTTP 422 and non-existent wards trigger HTTP 404."""
        # 1. Non-existent ward lookup -> 404
        r_404 = self.client.get("/api/water/wards/ward_does_not_exist_999")
        self.assertEqual(r_404.status_code, 404)
        self.assertIn("not found", r_404.json()["detail"].lower())

        # 2. Out-of-bounds supply parameter (> 300 LPCD) -> 422
        r_422_supply = self.client.get("/api/water/wards?supply_lpcd=9999.0")
        self.assertEqual(r_422_supply.status_code, 422)

        # 3. Negative rainfall parameter -> 422
        r_422_rain = self.client.get("/api/water/wards?rainfall_24h_mm=-15.0")
        self.assertEqual(r_422_rain.status_code, 422)

        # 4. Out-of-bounds latitude -> 422
        r_422_lat = self.client.get("/api/water/wards?lat=150.0")
        self.assertEqual(r_422_lat.status_code, 422)

        # 5. Invalid optimizer budget (< 10000 INR) -> 422
        r_422_opt = self.client.post("/api/optimize", json={"total_budget_inr": -500.0})
        self.assertEqual(r_422_opt.status_code, 422)

    def test_10_road_closure_guardrail_enforcement(self):
        """Verifies road closures are strictly blocked when flood risk is low/moderate."""
        low_flood_ward = [{"id": "W_DRY", "name": "Dry Ward", "vulnerability": 0.8, "waterlogging_score": 25.0, "heat_risk_score": 30.0, "water_shortage_score": 20.0}]
        res = solve_resource_allocation(total_budget_inr=500000, total_crew_members=40, total_water_cap_l=30000, wards=low_flood_ward)
        allocated_actions = [a["action_id"] for a in res["ward_allocations"]["W_DRY"]["interventions"]]
        self.assertNotIn("emergency_road_closure", allocated_actions, "Road closures must not be recommended without severe flood justification")


def run_tests_programmatically():
    """Programmatic test runner that executes the test suite and returns structured results."""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCompleteBackendWorkflow)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return {
        "total_tests": result.testsRun,
        "passed": result.testsRun - len(result.failures) - len(result.errors),
        "failed": len(result.failures),
        "errors": len(result.errors),
        "was_successful": result.wasSuccessful()
    }


if __name__ == "__main__":
    unittest.main()
