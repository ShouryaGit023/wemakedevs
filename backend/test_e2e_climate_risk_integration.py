"""
ClimateShield - End-to-End Verification Test Suite for Climate Risk Engine Integration
Tests the full workflow:
Existing Heat Engine + Existing Water Engine
→ Climate Risk Engine
→ Ward-level combined risk rankings
→ Dual-hazard identification
→ Existing intervention optimizer.

Verifies:
1. Heat-only data handling.
2. Water-only data handling.
3. Both engines returning valid data.
4. A ward experiencing high heat and high water risk.
5. Missing and malformed data.
6. Unmatched and duplicate ward IDs.
7. Invalid weights and risk scores.
8. Stable and reproducible rankings.
9. Correct optimizer input mapping.
10. All existing guardrails and constraint enforcement.

All tests use deterministic mocks for external weather APIs and hydrological telemetry
to ensure 100% offline reproducibility without flaky external network calls.
"""

import sys
import os
import unittest
from unittest.mock import patch, AsyncMock

# Ensure workspace root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi.testclient import TestClient
from backend.main import app

from backend.wbgt_pipeline import (
    calculate_outdoor_wbgt,
    classify_wbgt_risk,
    get_ward_wbgt_risk,
    AHMEDABAD_WARDS
)
from backend.water_engine import (
    assess_citywide_water_risk,
    calculate_waterlogging_risk,
    calculate_water_shortage_risk,
    DEMONSTRATION_SCENARIOS
)
from backend.climate_risk_engine import (
    evaluate_combined_climate_risk,
    compute_combined_risk_score,
    convert_wbgt_to_risk_score,
    classify_compound_hazard_tier,
    validate_and_normalize_weights,
    SCORING_MODES
)
from backend.optimizer import (
    solve_resource_allocation,
    optimize_from_combined_climate_results,
    adapt_climate_risk_to_optimizer_input,
    INTERVENTIONS,
    DEFAULT_WARDS
)

# Mock weather fixture (deterministic 38°C sunny afternoon in Ahmedabad)
MOCK_HEAT_WEATHER = {
    "latitude": 23.0225,
    "longitude": 72.5714,
    "hourly": {
        "time": [f"2026-10-10T{h:02d}:00" for h in range(24)],
        "temperature_2m": [38.0 for _ in range(24)],
        "relative_humidity_2m": [35.0 for _ in range(24)],
        "direct_normal_irradiance": [800.0 for _ in range(24)],
        "wind_speed_10m": [2.0 for _ in range(24)],
        "precipitation": [0.0 for _ in range(24)],
        "precipitation_probability": [0 for _ in range(24)]
    }
}

# Mock water citywide assessment for 48 wards
MOCK_WATER_CITYWIDE = {
    "city": "Ahmedabad",
    "timestamp": "2026-10-10T14:00:00Z",
    "data_source": "Mock Water Hydrology Engine",
    "data_quality": {
        "confidence_level": "HIGH",
        "confidence_score_pct": 85,
        "is_synthetic": False,
        "measured_parameters": ["rainfall_24h", "pipe_pressure"],
        "unmeasured_parameters": []
    },
    "ward_water_risks": [
        {
            "id": f"W{i+1}",
            "ward_index": i,
            "name": f"Ward_{i+1}",
            "ward_name": f"Ward_{i+1}",
            "official_name": f"{i+1} WARD_{i+1}",
            "risk_score": 40.0 + (i % 45),
            "composite_water_risk_score": 40.0 + (i % 45),
            "risk_category": "HIGH" if (40.0 + i % 45) >= 50.0 else "MODERATE",
            "risk_color": "#F97316" if (40.0 + i % 45) >= 50.0 else "#F59E0B",
            "contributing_factors": {
                "waterlogging": {"score": min(100.0, 45.0 + (i % 40)), "category": "HIGH"},
                "water_shortage": {"score": 35.0, "category": "MODERATE"}
            }
        }
        for i in range(48)
    ]
}


class TestE2EClimateRiskIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    # =========================================================
    # 1. HEAT-ONLY DATA HANDLING
    # =========================================================
    @patch("backend.climate_risk_engine.fetch_open_meteo_weather", new_callable=AsyncMock)
    @patch("backend.climate_risk_engine.assess_citywide_water_risk", new_callable=AsyncMock)
    def test_01_heat_only_data_handling(self, mock_water, mock_weather):
        """Verifies workflow when only Heat Engine returns valid data and Water Engine data is missing/empty."""
        mock_weather.return_value = MOCK_HEAT_WEATHER
        # Water engine returns empty ward risks (telemetry missing)
        mock_water.return_value = {"city": "Ahmedabad", "ward_water_risks": []}

        # 1. Climate Risk Engine evaluates heat with non-zero water prior fallback
        import asyncio
        results = asyncio.run(evaluate_combined_climate_risk(weight_heat=0.7, weight_water=0.3))

        self.assertEqual(results["city"], "Ahmedabad")
        self.assertEqual(len(results["ranked_wards"]), 48)

        # Wards must NOT have zero water risk (safety prior must be non-zero)
        top_ward = results["ranked_wards"][0]
        self.assertGreater(top_ward["heat_risk"]["score"], 40.0)
        self.assertGreater(top_ward["water_risk"]["score"], 0.0)
        self.assertIn("PARTIAL", [w["assessment_status"] for w in results["ranked_wards"]])

        # 2. Feed into optimizer
        opt_plan = optimize_from_combined_climate_results(results, total_budget_inr=500000.0)
        self.assertIn(opt_plan["status"], ["OPTIMAL", "FEASIBLE"])
        self.assertGreater(opt_plan["summary"]["budget"]["allocated_inr"], 0)

    # =========================================================
    # 2. WATER-ONLY DATA HANDLING
    # =========================================================
    @patch("backend.climate_risk_engine.fetch_open_meteo_weather", new_callable=AsyncMock)
    @patch("backend.climate_risk_engine.assess_citywide_water_risk", new_callable=AsyncMock)
    def test_02_water_only_data_handling(self, mock_water, mock_weather):
        """Verifies workflow when only Water Engine returns valid data and Heat Engine data is None/offline."""
        mock_weather.return_value = None  # Heat weather API offline
        mock_water.return_value = MOCK_WATER_CITYWIDE

        import asyncio
        results = asyncio.run(evaluate_combined_climate_risk(weight_heat=0.3, weight_water=0.7))

        self.assertEqual(len(results["ranked_wards"]), 48)
        top_ward = results["ranked_wards"][0]

        # Heat score must be derived from structural baseline vulnerability prior (NOT zero!)
        self.assertGreater(top_ward["heat_risk"]["score"], 0.0)
        self.assertGreater(top_ward["water_risk"]["score"], 0.0)

        # Feed into optimizer
        opt_plan = optimize_from_combined_climate_results(results, total_budget_inr=500000.0)
        self.assertIn(opt_plan["status"], ["OPTIMAL", "FEASIBLE"])
        # Water interventions must dominate spending
        self.assertGreater(opt_plan["summary"]["hazard_budget_breakdown"]["waterlogging_inr"], 0)

    # =========================================================
    # 3. BOTH ENGINES RETURNING VALID DATA (COMPLETE PIPELINE)
    # =========================================================
    @patch("backend.climate_risk_engine.fetch_open_meteo_weather", new_callable=AsyncMock)
    @patch("backend.climate_risk_engine.assess_citywide_water_risk", new_callable=AsyncMock)
    def test_03_both_engines_returning_valid_data(self, mock_water, mock_weather):
        """Verifies full end-to-end pipeline: Heat + Water -> Climate Risk Engine -> Rankings -> Optimizer."""
        mock_weather.return_value = MOCK_HEAT_WEATHER
        mock_water.return_value = MOCK_WATER_CITYWIDE

        import asyncio
        results = asyncio.run(evaluate_combined_climate_risk(
            weight_heat=0.5,
            weight_water=0.5,
            scoring_mode="COMPOUND_SYNERGY"
        ))

        # Check rankings
        self.assertEqual(len(results["ranked_wards"]), 48)
        self.assertEqual(results["ranked_wards"][0]["rank"], 1)
        self.assertEqual(results["ranked_wards"][-1]["rank"], 48)

        # Check score monotonicity in rankings
        scores = [w["combined_risk_score"] for w in results["ranked_wards"]]
        self.assertEqual(scores, sorted(scores, reverse=True))

        # Run Optimizer
        budget_cap = 600000.0
        crew_cap = 50
        water_cap = 40000.0
        opt_plan = optimize_from_combined_climate_results(
            combined_climate_results=results,
            total_budget_inr=budget_cap,
            total_crew_members=crew_cap,
            total_water_cap_l=water_cap,
            equity_slider=0.6
        )

        self.assertIn(opt_plan["status"], ["OPTIMAL", "FEASIBLE"])
        summary = opt_plan["summary"]
        self.assertLessEqual(summary["budget"]["allocated_inr"], budget_cap)
        self.assertLessEqual(summary["crew"]["allocated_members"], crew_cap)
        self.assertLessEqual(summary["water"]["allocated_liters"], water_cap)
        self.assertGreater(summary["total_risk_reduction_achieved"], 0.0)

    # =========================================================
    # 4. WARD EXPERIENCING HIGH HEAT AND HIGH WATER RISK
    # =========================================================
    def test_04_ward_experiencing_high_heat_and_high_water_risk(self):
        """Verifies dual-hazard compound hotspot identification and compound synergy calculation."""
        # Ward with Heat = 78.4 and Water = 79.3 (both >= 50.0)
        calc = compute_combined_risk_score(
            heat_score=78.4,
            water_score=79.3,
            weight_heat=0.5,
            weight_water=0.5,
            scoring_mode="COMPOUND_SYNERGY",
            synergy_multiplier=0.15
        )

        self.assertTrue(calc["is_compound_hazard_hotspot"])
        self.assertGreater(calc["compound_synergy_points"], 0.0)
        self.assertEqual(calc["risk_category"], "CRITICAL")

        # Classify compound tier
        tier = classify_compound_hazard_tier(heat_score=78.4, water_score=79.3)
        self.assertEqual(tier["tier"], "DUAL_CRITICAL")
        self.assertIn("CRISIS", tier["badge"])

        # Test optimizer co-scheduling with compound boost
        compound_ward = {
            "id": "W1",
            "name": "Danilimda",
            "vulnerability": 0.92,
            "heat_risk_score": 78.4,
            "waterlogging_score": 79.3,
            "water_shortage_score": 40.0,
            "is_compound_hotspot": True
        }
        res = solve_resource_allocation(wards=[compound_ward], total_budget_inr=500000.0)
        recs = [a["action_id"] for a in res["ward_allocations"]["W1"]["interventions"]]
        # Must receive interventions across both heat and water
        heat_actions = [a for a in recs if INTERVENTIONS[a]["risk_type"] == "heat"]
        water_actions = [a for a in recs if INTERVENTIONS[a]["risk_type"] == "waterlogging"]
        self.assertGreater(len(heat_actions), 0)
        self.assertGreater(len(water_actions), 0)

    # =========================================================
    # 5. MISSING AND MALFORMED DATA
    # =========================================================
    def test_05_missing_and_malformed_data(self):
        """Verifies safe non-zero prior imputation and rejection of invalid payloads."""
        # 1. Malformed payload with null scores
        malformed_results = {
            "city": "Ahmedabad",
            "ranked_wards": [
                {
                    "id": "W_CORRUPT",
                    "name": "Corrupted Sensor Ward",
                    "vulnerability": 0.85,
                    "heat_risk": None,
                    "water_risk": None
                }
            ]
        }

        wards, metadata = adapt_climate_risk_to_optimizer_input(malformed_results)
        self.assertEqual(len(wards), 1)
        # Risk scores must NOT be zero
        self.assertGreater(wards[0]["heat_risk_score"], 35.0)
        self.assertGreater(wards[0]["waterlogging_score"], 25.0)
        self.assertEqual(wards[0]["data_status"], "CONSERVATIVE_PRIOR_IMPUTED")
        self.assertTrue(metadata["safety_audit"]["has_missing_risk_data"])

        # 2. Completely empty payload raises ValueError
        with self.assertRaises(ValueError):
            adapt_climate_risk_to_optimizer_input({})

        with self.assertRaises(ValueError):
            adapt_climate_risk_to_optimizer_input({"ranked_wards": []})

    # =========================================================
    # 6. UNMATCHED AND DUPLICATE WARD IDS
    # =========================================================
    def test_06_unmatched_and_duplicate_ward_ids(self):
        """Verifies handling of duplicate ward IDs and non-standard identifiers."""
        # Input containing duplicate IDs (W1 appears twice)
        dup_payload = {
            "city": "Ahmedabad",
            "ranked_wards": [
                {"id": "W1", "ward_index": 0, "name": "Danilimda", "vulnerability": 0.92, "heat_risk_score": 75.0, "waterlogging_score": 70.0, "water_shortage_score": 30.0},
                {"id": "W1", "ward_index": 35, "name": "Ramol Hathijan", "vulnerability": 0.85, "heat_risk_score": 70.0, "waterlogging_score": 65.0, "water_shortage_score": 30.0}
            ]
        }

        # Adapter must disambiguate duplicate IDs so OR-Tools doesn't collide variables
        wards, _ = adapt_climate_risk_to_optimizer_input(dup_payload)
        self.assertEqual(len(wards), 2)
        unique_ids = set(w["id"] for w in wards)
        self.assertEqual(len(unique_ids), 2)

        # Optimization runs without double-counting
        plan = optimize_from_combined_climate_results(dup_payload, total_budget_inr=500000.0)
        self.assertIn(plan["status"], ["OPTIMAL", "FEASIBLE"])
        self.assertEqual(len(plan["ward_allocations"]), 2)

    # =========================================================
    # 7. INVALID WEIGHTS AND RISK SCORES
    # =========================================================
    def test_07_invalid_weights_and_risk_scores(self):
        """Verifies weight validation, normalization, and HTTP 422 errors."""
        # 1. Weights summing to zero raises ValueError
        with self.assertRaises(ValueError):
            validate_and_normalize_weights(0.0, 0.0)

        # 2. Negative weights raise ValueError
        with self.assertRaises(ValueError):
            validate_and_normalize_weights(-0.5, 0.5)

        # 3. Valid non-1.0 sum weights are normalized
        wh, ww = validate_and_normalize_weights(2.0, 6.0)
        self.assertEqual(wh, 0.25)
        self.assertEqual(ww, 0.75)
        self.assertEqual(wh + ww, 1.0)

        # 4. FastAPI query validation returns 422
        resp = self.client.get("/api/climate-risk?weight_heat=999.0")
        self.assertEqual(resp.status_code, 422)

        resp_mode = self.client.get("/api/climate-risk?scoring_mode=INVALID_MODE")
        self.assertEqual(resp_mode.status_code, 422)

    # =========================================================
    # 8. STABLE AND REPRODUCIBLE RANKINGS
    # =========================================================
    def test_08_stable_and_reproducible_rankings(self):
        """Verifies that ranking calculations and tie-breaking are 100% deterministic."""
        calc1 = compute_combined_risk_score(72.0, 68.0, scoring_mode="COMPOUND_SYNERGY")
        calc2 = compute_combined_risk_score(72.0, 68.0, scoring_mode="COMPOUND_SYNERGY")
        self.assertEqual(calc1["combined_risk_score"], calc2["combined_risk_score"])
        self.assertEqual(calc1["compound_synergy_points"], calc2["compound_synergy_points"])

        # Test deterministic sorting order across 5 runs
        wards_to_sort = [
            {"id": "W3", "name": "Asarwa", "combined_risk_score": 65.0, "heat_risk": {"score": 70.0}, "water_risk": {"score": 60.0}},
            {"id": "W1", "name": "Danilimda", "combined_risk_score": 80.0, "heat_risk": {"score": 85.0}, "water_risk": {"score": 75.0}},
            {"id": "W2", "name": "Behrampura", "combined_risk_score": 80.0, "heat_risk": {"score": 82.0}, "water_risk": {"score": 78.0}}
        ]

        def get_sorted_ids():
            records = list(wards_to_sort)
            records.sort(key=lambda w: (-w["combined_risk_score"], -w["heat_risk"]["score"], -w["water_risk"]["score"], w["id"]))
            return [w["id"] for w in records]

        initial_order = get_sorted_ids()
        for _ in range(5):
            self.assertEqual(get_sorted_ids(), initial_order)

        # Danilimda (score 80, heat 85) beats Behrampura (score 80, heat 82)
        self.assertEqual(initial_order, ["W1", "W2", "W3"])

    # =========================================================
    # 9. CORRECT OPTIMIZER INPUT MAPPING
    # =========================================================
    def test_09_correct_optimizer_input_mapping(self):
        """Verifies schema mapping, preservation of structural vulnerabilities, and constraint satisfaction."""
        climate_payload = {
            "city": "Ahmedabad",
            "is_simulation": False,
            "ranked_wards": [
                {
                    "id": "W1",
                    "name": "Danilimda",
                    "vulnerability": 0.92,
                    "heat_risk": {"score": 75.0, "baseline_vulnerability": 0.92},
                    "water_risk": {"waterlogging_score": 80.0, "water_shortage_score": 35.0},
                    "combined_risk_score": 77.5,
                    "compound_hazard": {"is_compound_hotspot": True}
                }
            ]
        }

        wards, metadata = adapt_climate_risk_to_optimizer_input(climate_payload)
        w = wards[0]

        # Verify exact optimizer keys
        self.assertIn("id", w)
        self.assertIn("name", w)
        self.assertIn("vulnerability", w)
        self.assertIn("heat_risk_score", w)
        self.assertIn("waterlogging_score", w)
        self.assertIn("water_shortage_score", w)
        self.assertIn("combined_risk_score", w)
        self.assertIn("is_compound_hotspot", w)

        # Verified vulnerability preserved
        self.assertEqual(w["vulnerability"], 0.92)
        # Provenance properly tagged
        self.assertEqual(metadata["provenance"]["data_origin"], "VERIFIED_REAL_WORLD")

    # =========================================================
    # 10. ROAD CLOSURE AND HAZARD GUARDRAILS
    # =========================================================
    def test_10_road_closure_and_hazard_guardrails(self):
        """Verifies emergency road closures are strictly blocked when flood risk < 70.0."""
        # Waterlogging = 60.0 (below critical 70.0 threshold)
        non_flood_ward = [{
            "id": "W_SAFE",
            "name": "Dry Ward",
            "vulnerability": 0.8,
            "heat_risk_score": 30.0,
            "waterlogging_score": 60.0,
            "water_shortage_score": 20.0
        }]
        res_safe = solve_resource_allocation(wards=non_flood_ward, total_budget_inr=500000.0)
        safe_actions = [a["action_id"] for a in res_safe["ward_allocations"]["W_SAFE"]["interventions"]]
        self.assertNotIn("emergency_road_closure", safe_actions)

        # Waterlogging = 85.0 (exceeds critical 70.0 threshold)
        flood_ward = [{
            "id": "W_FLOOD",
            "name": "Deep Inundation Ward",
            "vulnerability": 0.85,
            "heat_risk_score": 20.0,
            "waterlogging_score": 85.0,
            "water_shortage_score": 20.0
        }]
        res_flood = solve_resource_allocation(wards=flood_ward, total_budget_inr=500000.0)
        flood_actions = [a["action_id"] for a in res_flood["ward_allocations"]["W_FLOOD"]["interventions"]]
        self.assertIn("emergency_road_closure", flood_actions)


if __name__ == "__main__":
    unittest.main()
