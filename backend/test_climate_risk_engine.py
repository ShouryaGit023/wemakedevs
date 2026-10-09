"""
ClimateShield - Unit Test Suite for Climate Risk Engine (backend/climate_risk_engine.py)
Tests all core responsibilities and strict data integrity rules:
1. Consumes heat and water engine outputs using verified ward IDs (never array index).
2. Normalizes heat WBGT to 0–100 scale; preserves original and normalized scores.
3. Validates and normalizes weights (sum = 1.0; rejects invalid/negative weights).
4. Configurable risk thresholds and classification.
5. Compound hazard hotspot detection and classification.
6. Missing data rule: never replaces missing data with zero (uses baseline priors with warnings).
7. Distinguishes complete vs partial assessments.
8. Deterministic sorting and tie-breaking.
9. Distinguishes linear weighted average from non-linear compound synergy models.
"""

import sys
import os
import unittest
import asyncio
import random

# Ensure workspace root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from backend.climate_risk_engine import (
    validate_and_normalize_weights,
    convert_wbgt_to_risk_score,
    classify_climate_risk,
    compute_combined_risk_score,
    classify_compound_hazard_tier,
    match_and_combine_ward_risks,
    evaluate_combined_climate_risk,
    DEFAULT_RISK_THRESHOLDS,
    SCORING_MODES
)


class TestClimateRiskEngine(unittest.TestCase):

    def test_01_weight_validation_and_normalization(self):
        """Tests that weights are validated and normalized to sum to 1.0."""
        # Standard 50/50
        wh, ww = validate_and_normalize_weights(0.5, 0.5)
        self.assertEqual(wh, 0.5)
        self.assertEqual(ww, 0.5)

        # Unnormalized weights (e.g. 3 and 1)
        wh, ww = validate_and_normalize_weights(3.0, 1.0)
        self.assertEqual(wh, 0.75)
        self.assertEqual(ww, 0.25)
        self.assertAlmostEqual(wh + ww, 1.0)

        # Error cases: negative weights
        with self.assertRaises(ValueError):
            validate_and_normalize_weights(-0.5, 0.5)

        with self.assertRaises(ValueError):
            validate_and_normalize_weights(0.5, -0.2)

        # Error cases: zero sum
        with self.assertRaises(ValueError):
            validate_and_normalize_weights(0.0, 0.0)

    def test_02_heat_score_normalization_and_preservation(self):
        """Verifies heat WBGT is converted to 0–100 scale and original is preserved."""
        # Below 20°C
        self.assertEqual(convert_wbgt_to_risk_score(18.0), 10.0)
        # Moderate heat (~26°C)
        self.assertEqual(convert_wbgt_to_risk_score(26.0), 37.5)
        # High heat (30°C)
        self.assertEqual(convert_wbgt_to_risk_score(30.0), 62.5)
        # Critical heat (34°C)
        self.assertEqual(convert_wbgt_to_risk_score(34.0), 87.5)
        # Extreme overshoot
        self.assertLessEqual(convert_wbgt_to_risk_score(45.0), 100.0)

    def test_03_configurable_classification_thresholds(self):
        """Tests classification with default and custom thresholds."""
        # Default thresholds
        self.assertEqual(classify_climate_risk(20.0)["category"], "LOW")
        self.assertEqual(classify_climate_risk(35.0)["category"], "MODERATE")
        self.assertEqual(classify_climate_risk(65.0)["category"], "HIGH")
        self.assertEqual(classify_climate_risk(85.0)["category"], "CRITICAL")

        # Custom thresholds
        custom_thresholds = [
            {"max": 30.0, "category": "MILD", "color": "#00FF00", "action": "None"},
            {"max": 70.0, "category": "SEVERE", "color": "#FFA500", "action": "Caution"},
            {"max": 100.0, "category": "DISASTER", "color": "#FF0000", "action": "Evacuate"}
        ]
        self.assertEqual(classify_climate_risk(25.0, custom_thresholds)["category"], "MILD")
        self.assertEqual(classify_climate_risk(50.0, custom_thresholds)["category"], "SEVERE")
        self.assertEqual(classify_climate_risk(80.0, custom_thresholds)["category"], "DISASTER")

    def test_04_compound_hazard_detection(self):
        """Verifies compound hazard hotspots and tiering."""
        # Dual Critical (both >= 75)
        tier_crit = classify_compound_hazard_tier(80.0, 85.0)
        self.assertEqual(tier_crit["tier"], "DUAL_CRITICAL")

        # Dual High (both >= 50)
        tier_high = classify_compound_hazard_tier(60.0, 55.0)
        self.assertEqual(tier_high["tier"], "DUAL_HIGH")

        # Asymmetric Heat (Heat >= 50, Water < 50)
        tier_heat = classify_compound_hazard_tier(70.0, 30.0)
        self.assertEqual(tier_heat["tier"], "ASYMMETRIC_HIGH_HEAT")

        # Asymmetric Water (Water >= 50, Heat < 50)
        tier_water = classify_compound_hazard_tier(30.0, 75.0)
        self.assertEqual(tier_water["tier"], "ASYMMETRIC_HIGH_WATER")

        # Moderate/Low
        tier_mod = classify_compound_hazard_tier(40.0, 40.0)
        self.assertEqual(tier_mod["tier"], "MODERATE_OR_LOW")

    def test_05_scoring_modes_distinction(self):
        """Verifies that weighted average, worst-case peak, and compound synergy differ appropriately."""
        h_score = 70.0
        w_score = 80.0

        # Linear weighted average (50/50)
        res_linear = compute_combined_risk_score(h_score, w_score, scoring_mode="WEIGHTED_AVERAGE")
        self.assertEqual(res_linear["combined_risk_score"], 75.0)
        self.assertEqual(res_linear["compound_synergy_points"], 0.0)
        self.assertIn("does not model non-linear", res_linear["scoring_method_description"])

        # Worst-Case Peak
        res_peak = compute_combined_risk_score(h_score, w_score, scoring_mode="WORST_CASE_PEAK")
        self.assertEqual(res_peak["combined_risk_score"], 80.0)

        # Compound Synergy
        res_synergy = compute_combined_risk_score(h_score, w_score, scoring_mode="COMPOUND_SYNERGY", synergy_multiplier=0.15)
        self.assertTrue(res_synergy["is_compound_hazard_hotspot"])
        self.assertGreater(res_synergy["combined_risk_score"], 75.0)
        self.assertGreater(res_synergy["compound_synergy_points"], 0.0)

    def test_06_matching_by_verified_ward_id_never_array_position(self):
        """CRITICAL: Tests that wards match strictly by ward ID, even if inputs are reversed or shuffled."""
        heat_wards = [
            {"id": "W1", "name": "Danilimda", "effective_wbgt_c": 35.0},
            {"id": "W2", "name": "Behrampura", "effective_wbgt_c": 28.0},
            {"id": "W3", "name": "Asarwa", "effective_wbgt_c": 24.0}
        ]
        # Inverted / shuffled water wards
        water_wards = [
            {"id": "W3", "name": "Asarwa", "risk_score": 30.0},
            {"id": "W1", "name": "Danilimda", "risk_score": 85.0},
            {"id": "W2", "name": "Behrampura", "risk_score": 60.0}
        ]

        result = match_and_combine_ward_risks(heat_wards, water_wards, scoring_mode="WEIGHTED_AVERAGE")
        wards_map = {w["id"]: w for w in result["ranked_wards"]}

        # Check W1 Danilimda correctly matched W1 heat and W1 water
        w1 = wards_map["W1"]
        self.assertEqual(w1["heat_risk"]["original_score"], 35.0)
        self.assertEqual(w1["water_risk"]["original_score"], 85.0)

        # Check W3 Asarwa correctly matched W3 heat and W3 water
        w3 = wards_map["W3"]
        self.assertEqual(w3["heat_risk"]["original_score"], 24.0)
        self.assertEqual(w3["water_risk"]["original_score"], 30.0)

    def test_07_missing_data_never_zero_and_partial_flagging(self):
        """CRITICAL: Missing heat or water data must NEVER be set to zero. Must flag partial assessment."""
        # W1 has both; W2 is missing water; W4 is missing heat
        heat_wards = [
            {"id": "W1", "name": "Danilimda", "effective_wbgt_c": 32.0},
            {"id": "W2", "name": "Behrampura", "effective_wbgt_c": 30.0}
        ]
        water_wards = [
            {"id": "W1", "name": "Danilimda", "risk_score": 75.0},
            {"id": "W4", "name": "Bapunagar", "risk_score": 65.0}
        ]

        result = match_and_combine_ward_risks(heat_wards, water_wards)
        wards_map = {w["id"]: w for w in result["ranked_wards"]}

        # W1: Complete assessment
        w1 = wards_map["W1"]
        self.assertEqual(w1["assessment_status"], "COMPLETE")
        self.assertTrue(w1["is_complete_assessment"])
        self.assertEqual(len(w1["warnings"]), 0)

        # W2: Missing water data -> score must NOT be 0!
        w2 = wards_map["W2"]
        self.assertEqual(w2["assessment_status"], "PARTIAL")
        self.assertFalse(w2["is_complete_assessment"])
        self.assertGreater(w2["water_risk"]["score"], 0.0)
        self.assertEqual(w2["water_risk"]["original_scale"], "ESTIMATED_PRIOR_0_TO_100")
        self.assertTrue(any("Water engine assessment missing" in warn for warn in w2["warnings"]))

        # W4: Missing heat data -> score must NOT be 0!
        w4 = wards_map["W4"]
        self.assertEqual(w4["assessment_status"], "PARTIAL")
        self.assertFalse(w4["is_complete_assessment"])
        self.assertGreater(w4["heat_risk"]["score"], 0.0)
        self.assertEqual(w4["heat_risk"]["original_scale"], "SCALED_CITY_WBGT_CELSIUS")
        self.assertTrue(any("Heat observation missing" in warn for warn in w4["warnings"]))

    def test_08_deterministic_sorting_and_tie_breaking(self):
        """Verifies deterministic sorting with tie-breaker attributes."""
        # Create identical score wards to test tie-breaker
        heat_wards = [
            {"id": "W_B", "name": "Ward B", "effective_wbgt_c": 28.0},
            {"id": "W_A", "name": "Ward A", "effective_wbgt_c": 28.0}
        ]
        water_wards = [
            {"id": "W_B", "name": "Ward B", "risk_score": 50.0},
            {"id": "W_A", "name": "Ward A", "risk_score": 50.0}
        ]

        # Invert input order in two calls and verify output rank order is 100% deterministic
        res1 = match_and_combine_ward_risks(heat_wards, water_wards)
        res2 = match_and_combine_ward_risks(list(reversed(heat_wards)), list(reversed(water_wards)))

        ranks1 = [w["id"] for w in res1["ranked_wards"]]
        ranks2 = [w["id"] for w in res2["ranked_wards"]]
        self.assertEqual(ranks1, ranks2)

    def test_09_full_async_pipeline_orchestration(self):
        """Tests evaluate_combined_climate_risk end-to-end integration."""
        async def run_pipeline():
            res = await evaluate_combined_climate_risk(
                weight_heat=0.6,
                weight_water=0.4,
                scoring_mode="COMPOUND_SYNERGY",
                heat_wbgt_override=34.0,
                rainfall_24h_override=80.0,
                peak_hourly_override=40.0
            )
            self.assertEqual(res["city"], "Ahmedabad")
            self.assertEqual(res["scoring_configuration"]["weight_heat"], 0.6)
            self.assertEqual(res["scoring_configuration"]["weight_water"], 0.4)
            self.assertIn("ranked_wards", res)
            self.assertGreaterEqual(len(res["ranked_wards"]), 10)

            top_ward = res["ranked_wards"][0]
            self.assertEqual(top_ward["rank"], 1)
            self.assertIn("heat_risk", top_ward)
            self.assertIn("water_risk", top_ward)
            self.assertIn("combined_risk_score", top_ward)
            self.assertIn("compound_hazard", top_ward)
            self.assertIn("ranking_rationale", top_ward)

            # Preserved scores verified
            self.assertIn("original_score", top_ward["heat_risk"])
            self.assertIn("normalized_score", top_ward["heat_risk"])
            self.assertIn("original_score", top_ward["water_risk"])
            self.assertIn("normalized_score", top_ward["water_risk"])

        asyncio.run(run_pipeline())


if __name__ == "__main__":
    unittest.main()
