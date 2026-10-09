"""
ClimateShield - End-to-End Integration Tests for Impact Verification Module
Verifies:
1. Correct absolute and percentage change calculations.
2. Directional indicators (lower is better vs higher is better).
3. Missing baseline and follow-up values handling.
4. Zero denominators and invalid numeric inputs.
5. Unit mismatches and incompatible measurement periods.
6. Measured vs estimated vs simulated data segregation.
7. Assessment storage, retrieval, and duplicate prevention.
8. Ward-level and overall summaries.
9. API validation and error responses.
10. Action Centre and Learning Loop integration boundary contracts remain intact and read-only.
"""

import os
import sys
import unittest
from datetime import datetime

# Ensure workspace root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import get_db_connection
from backend.impact_verification import (
    assess_intervention_impact,
    record_impact_assessment,
    retrieve_impact_assessment,
    list_impact_assessments,
    retrieve_assessment_history,
    update_impact_assessment,
    generate_impact_verification_summary,
    validate_intervention_against_action_centre,
    export_learning_loop_signals,
    generate_synthetic_demonstration_data,
    SourceType,
    QualityStatus,
    Direction,
    ExecutionStatus,
    ATTRIBUTION_DISCLAIMER
)
from backend.intervention_engine import INTERVENTIONS_CATALOG


class TestE2EImpactVerificationIntegration(unittest.TestCase):
    """End-to-End integration test suite for Impact Verification."""

    def setUp(self):
        self.client = TestClient(app)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM impact_assessment_history WHERE assessment_id LIKE 'E2E_%';")
        cursor.execute("DELETE FROM impact_assessments WHERE assessment_id LIKE 'E2E_%';")
        conn.commit()
        conn.close()

    def tearDown(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM impact_assessment_history WHERE assessment_id LIKE 'E2E_%';")
        cursor.execute("DELETE FROM impact_assessments WHERE assessment_id LIKE 'E2E_%';")
        conn.commit()
        conn.close()

    # -------------------------------------------------------------
    # 1 & 2. Mathematical Calculations & Directional Indicators
    # -------------------------------------------------------------
    def test_01_absolute_and_percentage_change_directional(self):
        """Test correct delta and percentage change for both directional indicators."""
        # A. Decrease is beneficial: Heat WBGT drops from 36.0°C to 32.4°C
        heat_obs = [
            {"indicator": "wbgt", "value": 36.0, "unit": "°C", "timestamp": "2026-05-11T12:00:00Z", "period": "BASELINE", "ward_id": "W1"},
            {"indicator": "wbgt", "value": 32.4, "unit": "°C", "timestamp": "2026-05-15T12:00:00Z", "period": "FOLLOW_UP", "ward_id": "W1"}
        ]
        heat_res = assess_intervention_impact(
            intervention_id="cooling_center", ward_id="W1",
            intervention_type="COOLING", observations=heat_obs
        )
        wbgt_metric = heat_res.results_by_indicator["wbgt"]
        self.assertEqual(wbgt_metric["difference"], -3.6)
        self.assertEqual(wbgt_metric["percentage_change"], -10.0)
        self.assertTrue(wbgt_metric["is_improvement"])
        self.assertEqual(wbgt_metric["improvement_magnitude"], 3.6)

        # B. Increase is beneficial: Water delivered rises from 15,000L to 45,000L
        water_obs = [
            {"indicator": "water_delivered", "value": 15000.0, "unit": "liters", "timestamp": "2026-05-11T12:00:00Z", "period": "BASELINE", "ward_id": "W7"},
            {"indicator": "water_delivered", "value": 45000.0, "unit": "liters", "timestamp": "2026-05-15T12:00:00Z", "period": "FOLLOW_UP", "ward_id": "W7"}
        ]
        water_res = assess_intervention_impact(
            intervention_id="water_tanker_allocation", ward_id="W7",
            intervention_type="WATER_SUPPLY", observations=water_obs
        )
        deliv_metric = water_res.results_by_indicator["water_delivered"]
        self.assertEqual(deliv_metric["difference"], 30000.0)
        self.assertEqual(deliv_metric["percentage_change"], 200.0)
        self.assertTrue(deliv_metric["is_improvement"])
        self.assertEqual(deliv_metric["improvement_magnitude"], 30000.0)

    # -------------------------------------------------------------
    # 3. Missing Baseline and Follow-up Values
    # -------------------------------------------------------------
    def test_02_missing_baseline_and_follow_up(self):
        """Test handling when baseline or follow-up observations are missing."""
        # Only follow-up provided
        post_only = [
            {"indicator": "flood_water_depth", "value": 18.0, "unit": "cm", "timestamp": "2026-07-16T10:00:00Z", "period": "FOLLOW_UP", "ward_id": "W4"}
        ]
        post_res = assess_intervention_impact(
            intervention_id="dewatering_pump", ward_id="W4",
            intervention_type="PUMP", observations=post_only
        )
        depth_metric = post_res.results_by_indicator["flood_water_depth"]
        self.assertIsNone(depth_metric["baseline_value"])
        self.assertEqual(depth_metric["follow_up_value"], 18.0)
        self.assertIsNone(depth_metric["difference"])
        self.assertIsNone(depth_metric["percentage_change"])
        self.assertEqual(depth_metric["quality_status"], QualityStatus.MISSING_BASELINE)

        # Only baseline provided
        base_only = [
            {"indicator": "flood_water_depth", "value": 65.0, "unit": "cm", "timestamp": "2026-07-15T10:00:00Z", "period": "BASELINE", "ward_id": "W4"}
        ]
        base_res = assess_intervention_impact(
            intervention_id="dewatering_pump", ward_id="W4",
            intervention_type="PUMP", observations=base_only
        )
        base_metric = base_res.results_by_indicator["flood_water_depth"]
        self.assertEqual(base_metric["baseline_value"], 65.0)
        self.assertIsNone(base_metric["follow_up_value"])
        self.assertEqual(base_metric["quality_status"], QualityStatus.MISSING_FOLLOW_UP)

    # -------------------------------------------------------------
    # 4. Zero Denominators and Invalid Numeric Inputs
    # -------------------------------------------------------------
    def test_03_zero_denominator_and_invalid_inputs(self):
        """Test that zero baseline does not cause ZeroDivisionError and NaN/Inf are rejected."""
        # Zero baseline
        obs_zero = [
            {"indicator": "water_scarcity_complaints", "value": 0.0, "unit": "count", "timestamp": "2026-05-10T00:00:00Z", "period": "BASELINE", "ward_id": "W9"},
            {"indicator": "water_scarcity_complaints", "value": 8.0, "unit": "count", "timestamp": "2026-05-15T00:00:00Z", "period": "FOLLOW_UP", "ward_id": "W9"}
        ]
        res_zero = assess_intervention_impact(
            intervention_id="water_tanker_allocation", ward_id="W9",
            intervention_type="WATER_SUPPLY", observations=obs_zero
        )
        complaints_metric = res_zero.results_by_indicator["water_scarcity_complaints"]
        self.assertEqual(complaints_metric["baseline_value"], 0.0)
        self.assertEqual(complaints_metric["difference"], 8.0)
        self.assertIsNone(complaints_metric["percentage_change"])  # Must be None, zero division protected!
        self.assertTrue(any("ZERO_BASELINE_PERCENTAGE_UNDEFINED" in n for n in complaints_metric["notes"]))

        # Invalid NaN input
        obs_nan = [
            {"indicator": "wbgt", "value": float("nan"), "unit": "°C", "timestamp": "2026-05-10T00:00:00Z", "period": "BASELINE", "ward_id": "W1"}
        ]
        res_nan = assess_intervention_impact(
            intervention_id="cooling_center", ward_id="W1",
            intervention_type="COOLING", observations=obs_nan
        )
        self.assertIn("Observation #0: Observation value is NaN or Infinite.", res_nan.summary["validation_errors"])

    # -------------------------------------------------------------
    # 5. Unit Mismatches and Incompatible Measurement Periods
    # -------------------------------------------------------------
    def test_04_unit_mismatches_rejected(self):
        """Test that disparate units across periods are not subtracted or coerced."""
        # 1. Registered indicator with incompatible unit is caught during validation
        obs_mismatch = [
            {"indicator": "flood_water_depth", "value": 60.0, "unit": "cm", "timestamp": "2026-07-15T00:00:00Z", "period": "BASELINE", "ward_id": "W4"},
            {"indicator": "flood_water_depth", "value": 1500.0, "unit": "liters", "timestamp": "2026-07-16T00:00:00Z", "period": "FOLLOW_UP", "ward_id": "W4"}
        ]
        res_mismatch = assess_intervention_impact(
            intervention_id="drainage_inspection_cleaning", ward_id="W4",
            intervention_type="INFRASTRUCTURE_MAINTENANCE", observations=obs_mismatch
        )
        self.assertTrue(any("Incompatible unit 'liters'" in err for err in res_mismatch.summary["validation_errors"]))
        ind_metric = res_mismatch.results_by_indicator["flood_water_depth"]
        self.assertEqual(ind_metric["quality_status"], QualityStatus.MISSING_FOLLOW_UP)
        self.assertIsNone(ind_metric["difference"])

        # 2. Custom indicator with disparate units between baseline and follow-up produces INCOMPATIBLE_UNITS
        obs_disparate = [
            {"indicator": "custom_pressure", "value": 50.0, "unit": "psi", "timestamp": "2026-07-15T00:00:00Z", "period": "BASELINE", "ward_id": "W4"},
            {"indicator": "custom_pressure", "value": 3.0, "unit": "bar", "timestamp": "2026-07-16T00:00:00Z", "period": "FOLLOW_UP", "ward_id": "W4"}
        ]
        res_disparate = assess_intervention_impact(
            intervention_id="drainage_inspection_cleaning", ward_id="W4",
            intervention_type="INFRASTRUCTURE_MAINTENANCE", observations=obs_disparate
        )
        ind_custom = res_disparate.results_by_indicator["custom_pressure"]
        self.assertEqual(ind_custom["quality_status"], QualityStatus.INCOMPATIBLE_UNITS)
        self.assertIsNone(ind_custom["difference"])
        self.assertIsNone(ind_custom["percentage_change"])
        self.assertTrue(any("INCOMPATIBLE_UNITS" in note for note in ind_custom["notes"]))

    # -------------------------------------------------------------
    # 6. Measured vs Estimated vs Simulated Data Segregation
    # -------------------------------------------------------------
    def test_05_provenance_and_synthetic_segregation(self):
        """Test that synthetic demonstration data is explicitly flagged and never conflated with empirical."""
        demo_data = generate_synthetic_demonstration_data("cooling_center", "W1", "PHYSICAL_REFUGE_AND_COOLING", hazard_type="heat")
        self.assertTrue(demo_data["is_synthetic"])
        self.assertIn("DEMONSTRATION ONLY", demo_data["demonstration_notice"])

        saved = record_impact_assessment({
            "assessment_id": "E2E_SYN_01",
            "intervention_id": "cooling_center",
            "ward_id": "W1",
            "intervention_type": "PHYSICAL_REFUGE_AND_COOLING",
            "execution_status": ExecutionStatus.SYNTHETIC_DEMO,
            "is_synthetic": True,
            "provenance_mode": SourceType.SYNTHETIC_DEMO,
            "indicators": {
                "ambient_temperature": {
                    "baseline_value": 44.0, "follow_up_value": 41.0, "difference": -3.0,
                    "unit": "celsius", "is_improvement": True
                }
            }
        })
        self.assertTrue(saved["is_synthetic"])

        # Also save an empirical measured record
        record_impact_assessment({
            "assessment_id": "E2E_EMP_01",
            "intervention_id": "cooling_center",
            "ward_id": "W1",
            "intervention_type": "PHYSICAL_REFUGE_AND_COOLING",
            "execution_status": ExecutionStatus.COMPLETED,
            "is_synthetic": False,
            "provenance_mode": SourceType.MEASURED,
            "indicators": {
                "ambient_temperature": {
                    "baseline_value": 43.5, "follow_up_value": 40.5, "difference": -3.0,
                    "unit": "celsius", "is_improvement": True
                }
            }
        })

        # Summary with include_synthetic=False
        summary_empirical = generate_impact_verification_summary(
            ward_id="W1", include_synthetic=False
        )
        self.assertEqual(summary_empirical["data_integrity_mode"], "REAL_WORLD_VERIFIED_ONLY")
        self.assertEqual(summary_empirical["by_indicator"]["ambient_temperature"]["sample_size"], 1)

        # Summary with include_synthetic=True
        summary_all = generate_impact_verification_summary(
            ward_id="W1", include_synthetic=True
        )
        self.assertEqual(summary_all["data_integrity_mode"], "INCLUDES_SIMULATED_DEMO")
        self.assertEqual(summary_all["by_indicator"]["ambient_temperature"]["sample_size"], 2)

    # -------------------------------------------------------------
    # 7. Assessment Storage, Retrieval, and Duplicate Prevention
    # -------------------------------------------------------------
    def test_06_storage_retrieval_and_history(self):
        """Test persistence, retrieval, idempotency, duplicate prevention, and version history."""
        aid = "E2E_STORE_01"
        payload = {
            "assessment_id": aid,
            "intervention_id": "shade_tree_deployment",
            "ward_id": "W3",
            "intervention_type": "PASSIVE_COOLING",
            "execution_status": ExecutionStatus.COMPLETED,
            "indicators": {
                "surface_temperature": {
                    "baseline_value": 48.0, "follow_up_value": 42.0, "difference": -6.0,
                    "unit": "celsius", "is_improvement": True
                }
            }
        }

        # 1. Initial save
        saved = record_impact_assessment(payload)
        self.assertEqual(saved["version"], 1)

        # 2. Idempotent re-save
        resaved = record_impact_assessment(payload)
        self.assertEqual(resaved["save_status"], "IDEMPOTENT_UNCHANGED")

        # 3. Update with history preservation
        updated_payload = dict(payload)
        updated_payload["indicators"] = {
            "surface_temperature": {
                "baseline_value": 48.0, "follow_up_value": 40.0, "difference": -8.0,
                "unit": "celsius", "is_improvement": True
            }
        }
        updated = update_impact_assessment(aid, updated_payload, change_reason="Thermographic recalibration")
        self.assertEqual(updated["version"], 2)

        # 4. Verify history contains version 1 snapshot
        history = retrieve_assessment_history(aid)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["version"], 1)

    # -------------------------------------------------------------
    # 8. Ward-level and Overall Summaries
    # -------------------------------------------------------------
    def test_07_ward_and_overall_summaries(self):
        """Test structured summary generation across multiple wards and interventions."""
        record_impact_assessment({
            "assessment_id": "E2E_SUM_W1",
            "intervention_id": "cooling_center",
            "ward_id": "W1",
            "intervention_type": "PHYSICAL_REFUGE_AND_COOLING",
            "execution_status": ExecutionStatus.COMPLETED,
            "indicators": {
                "wbgt": {"baseline_value": 35.0, "follow_up_value": 32.0, "difference": -3.0, "unit": "celsius", "is_improvement": True}
            }
        })
        record_impact_assessment({
            "assessment_id": "E2E_SUM_W2",
            "intervention_id": "drinking_water_point",
            "ward_id": "W2",
            "intervention_type": "HYDRATION_DISTRIBUTION",
            "execution_status": ExecutionStatus.COMPLETED,
            "indicators": {
                "water_delivered": {"baseline_value": 2000.0, "follow_up_value": 5000.0, "difference": 3000.0, "unit": "liters", "is_improvement": True}
            }
        })

        summary = generate_impact_verification_summary(include_synthetic=False)
        self.assertEqual(summary["kpis"]["valid_before_after_comparisons_count"], 2)
        self.assertIn("W1", summary["by_ward"])
        self.assertIn("W2", summary["by_ward"])
        self.assertIn("wbgt", summary["by_indicator"])
        self.assertIn("water_delivered", summary["by_indicator"])

    # -------------------------------------------------------------
    # 9. API Validation and Error Responses
    # -------------------------------------------------------------
    def test_08_api_validation_and_errors(self):
        """Test API status codes: 201, 200, 404, 409, 422."""
        # 422: Uncompleted recommendation rejection
        bad_rec = self.client.post("/api/impact/assessments", json={
            "assessment_id": "E2E_API_REC",
            "intervention_id": "cooling_center",
            "ward_id": "W1",
            "intervention_type": "COOLING",
            "execution_status": "RECOMMENDED",
            "indicators": {"wbgt": {"unit": "celsius"}}
        })
        self.assertEqual(bad_rec.status_code, 422)

        # 404: Nonexistent assessment
        not_found = self.client.get("/api/impact/assessments/NONEXISTENT_9999")
        self.assertEqual(not_found.status_code, 404)

        # 201: Valid POST
        valid_post = self.client.post("/api/impact/assessments", json={
            "assessment_id": "E2E_API_VALID",
            "intervention_id": "cooling_center",
            "ward_id": "W1",
            "intervention_type": "PHYSICAL_REFUGE_AND_COOLING",
            "execution_status": "COMPLETED",
            "indicators": {
                "wbgt": {"baseline_value": 34.0, "follow_up_value": 31.0, "difference": -3.0, "unit": "celsius", "is_improvement": True}
            }
        })
        self.assertEqual(valid_post.status_code, 201)

        # 409: Duplicate without allow_update
        dup_post = self.client.post("/api/impact/assessments", json={
            "assessment_id": "E2E_API_VALID",
            "intervention_id": "cooling_center",
            "ward_id": "W1",
            "intervention_type": "PHYSICAL_REFUGE_AND_COOLING",
            "execution_status": "COMPLETED",
            "indicators": {
                "wbgt": {"baseline_value": 34.0, "follow_up_value": 29.0, "difference": -5.0, "unit": "celsius", "is_improvement": True}
            }
        })
        self.assertEqual(dup_post.status_code, 409)

    # -------------------------------------------------------------
    # 10. Action Centre & Learning Loop Integration Boundaries
    # -------------------------------------------------------------
    def test_09_action_centre_interface_intact(self):
        """Test consuming Action Centre intervention catalog without mutating it."""
        # Action Centre catalog must remain intact
        self.assertIn("cooling_center", INTERVENTIONS_CATALOG)
        self.assertIn("drinking_water_point", INTERVENTIONS_CATALOG)
        self.assertIn("drainage_inspection_cleaning", INTERVENTIONS_CATALOG)

        # Impact Verification validates against Action Centre interface
        check = validate_intervention_against_action_centre("cooling_center")
        self.assertTrue(check["is_recognized"])
        self.assertEqual(check["unit_cost_inr"], 50000.0)
        self.assertEqual(check["crew_required"], 4)

    def test_10_learning_loop_signals_interface(self):
        """Test exposing read-only empirical signals for Learning Loop."""
        # Seed verified assessment
        record_impact_assessment({
            "assessment_id": "E2E_LEARN_01",
            "intervention_id": "cooling_center",
            "ward_id": "W1",
            "intervention_type": "PHYSICAL_REFUGE_AND_COOLING",
            "execution_status": ExecutionStatus.COMPLETED,
            "provenance_mode": SourceType.MEASURED,
            "indicators": {
                "ambient_temperature": {
                    "baseline_value": 43.5, "follow_up_value": 40.0, "difference": -3.5,
                    "percentage_change": -8.05, "unit": "celsius", "is_improvement": True
                }
            }
        })

        signals = export_learning_loop_signals(ward_id="W1", include_synthetic=False)
        self.assertGreaterEqual(len(signals), 1)
        sig = signals[0]
        self.assertEqual(sig["intervention_id"], "cooling_center")
        self.assertEqual(sig["observed_absolute_difference"], -3.5)
        self.assertEqual(sig["calibration_weight"], 1.0)
        self.assertEqual(sig["learning_feedback"], "EFFECTIVE_EMPIRICAL_BENEFIT")

        # Test via API
        api_res = self.client.get("/api/impact/learning-signals?ward_id=W1")
        self.assertEqual(api_res.status_code, 200)
        self.assertGreaterEqual(api_res.json()["total_signals"], 1)


if __name__ == "__main__":
    unittest.main()
