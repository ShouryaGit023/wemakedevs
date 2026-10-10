"""
ClimateShield - Automated Test Suite for Impact Verification Engine
Tests:
1. Simple before-and-after comparison with strict non-causal labeling.
2. Difference-in-Differences (DiD) estimation when valid control ward data is available.
3. Safe handling of incomplete, scheduled, or failed actions.
4. Insufficient data reporting when baseline or follow-up observations are missing.
5. Graceful fallback when comparison control ward data is unavailable.
6. Clear labeling and disclaimers for synthetic / simulated demonstrations.
7. Tracking whether intended outcome was observed relative to expected recommendations.
8. Multi-hazard support for heat, waterlogging depth, and water scarcity complaints.
9. FastAPI REST endpoints for impact verification.
10. Error handling, input validation, and 404 responses.
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.main import app
from backend.learning_loop import (
    record_prediction,
    record_recommendations,
    record_executed_action,
    update_executed_action,
    record_verified_outcome,
    PredictionRecordCreate,
    RecommendationItemCreate,
    ExecutedActionCreate,
    ExecutedActionUpdate,
    VerifiedOutcomeCreate
)
from backend.impact_verification import (
    verify_intervention_impact,
    get_verification,
    list_verifications,
    ImpactVerificationRequest
)


@pytest.fixture
def client():
    return TestClient(app)


class TestImpactVerificationEngine:

    def test_01_simple_before_after_labeled_non_causal(self):
        """Test before-and-after comparison and ensure causal claim is strictly denied."""
        # 1. Action executed in W1
        action = record_executed_action(ExecutedActionCreate(
            ward_id="W1",
            intervention_type="cooling_center",
            approval_status="APPROVED",
            approved_by="AMC_HEALTH_OFFICER",
            execution_status="COMPLETED",
            started_at="2026-06-01T09:00:00Z",
            completed_at="2026-06-01T19:00:00Z",
            actual_cost_inr=50000.0,
            actual_crew_used=4
        ))
        act_id = action["action_id"]

        # 2. Baseline outcome before action
        record_verified_outcome(VerifiedOutcomeCreate(
            ward_id="W1",
            measurement_date="2026-06-01",
            hazard_type="heat",
            hospital_heat_admissions=12,
            emergency_108_calls=15,
            data_source="AMC_HEALTH_SURVEILLANCE",
            provenance="REAL"
        ))

        # 3. Follow-up outcome post-intervention
        record_verified_outcome(VerifiedOutcomeCreate(
            ward_id="W1",
            action_id=act_id,
            measurement_date="2026-06-02",
            hazard_type="heat",
            hospital_heat_admissions=7,
            emergency_108_calls=9,
            data_source="AMC_HEALTH_SURVEILLANCE",
            provenance="REAL"
        ))

        # 4. Verify impact
        req = ImpactVerificationRequest(
            action_id=act_id,
            primary_metric="hospital_heat_admissions",
            baseline_date="2026-06-01",
            followup_date="2026-06-02"
        )
        res = verify_intervention_impact(req)

        assert res["status"] == "VERIFIED_COMPLETED"
        assert res["action_completed"] is True
        assert res["evaluation_methodology"] == "SIMPLE_BEFORE_AFTER"
        # Strict Epistemic Guardrail: Causal claim MUST be False
        assert res["causal_claim_allowed"] is False
        assert "CORRELATIONAL_ONLY" in res["causal_disclaimer"]
        assert res["observed_delta"] == -5.0  # 7 - 12
        assert res["intended_outcome_observed"] is True

    def test_02_difference_in_differences_valid_control(self):
        """Test quasi-experimental DiD estimation when treated and control wards both have data."""
        # 1. Action completed in treated ward W2
        action = record_executed_action(ExecutedActionCreate(
            ward_id="W2",
            intervention_type="cooling_center",
            approval_status="APPROVED",
            approved_by="AMC_HEALTH_OFFICER",
            execution_status="COMPLETED",
            started_at="2026-06-03T09:00:00Z",
            completed_at="2026-06-03T19:00:00Z"
        ))
        act_id = action["action_id"]

        # Treated ward (W2) outcomes: 10 admissions -> 5 admissions (Delta = -5)
        record_verified_outcome(VerifiedOutcomeCreate(
            ward_id="W2",
            measurement_date="2026-06-03",
            hazard_type="heat",
            hospital_heat_admissions=10,
            provenance="REAL"
        ))
        record_verified_outcome(VerifiedOutcomeCreate(
            ward_id="W2",
            action_id=act_id,
            measurement_date="2026-06-04",
            hazard_type="heat",
            hospital_heat_admissions=5,
            provenance="REAL"
        ))

        # Control ward (W9) outcomes: 4 admissions -> 3 admissions (Delta = -1 due to ambient cooling)
        record_verified_outcome(VerifiedOutcomeCreate(
            ward_id="W9",
            measurement_date="2026-06-03",
            hazard_type="heat",
            hospital_heat_admissions=4,
            provenance="REAL"
        ))
        record_verified_outcome(VerifiedOutcomeCreate(
            ward_id="W9",
            measurement_date="2026-06-04",
            hazard_type="heat",
            hospital_heat_admissions=3,
            provenance="REAL"
        ))

        # Verify impact with control ward W9
        res = verify_intervention_impact(ImpactVerificationRequest(
            action_id=act_id,
            control_ward_id="W9",
            primary_metric="hospital_heat_admissions",
            baseline_date="2026-06-03",
            followup_date="2026-06-04"
        ))

        assert res["evaluation_methodology"] == "DIFFERENCE_IN_DIFFERENCES"
        assert res["causal_claim_allowed"] is True
        assert res["difference_in_differences"]["eligible"] is True
        # DiD = (-5) - (-1) = -4.0 net hospital admissions prevented
        assert res["difference_in_differences"]["did_estimate"] == -4.0
        assert "confidence_interval_95" in res["difference_in_differences"]
        assert res["confidence_score"] > 0.80

    def test_03_incomplete_or_failed_action_handled_safely(self):
        """Ensure incomplete or failed actions refuse to manufacture impact claims."""
        failed_act = record_executed_action(ExecutedActionCreate(
            ward_id="W3",
            intervention_type="mobile_pumping",
            approval_status="APPROVED",
            approved_by="DISASTER_MGMT_CELL",
            execution_status="FAILED",
            failure_reason="Submersible pump generator caught fire en route",
            actual_cost_inr=8000.0
        ))

        res = verify_intervention_impact(ImpactVerificationRequest(
            action_id=failed_act["action_id"]
        ))

        assert res["status"] == "INSUFFICIENT_DATA_INCOMPLETE_ACTION"
        assert res["action_completed"] is False
        assert res["causal_claim_allowed"] is False
        assert "generator caught fire" in res["explanation"]
        assert "No impact result calculated" in res["disclaimer"]

    def test_04_missing_observations_reported_safely(self):
        """Ensure missing follow-up observation halts evaluation without fabricating numbers."""
        # Action completed in ward with NO outcomes recorded
        action = record_executed_action(ExecutedActionCreate(
            ward_id="W10",
            intervention_type="shade_canopy",
            approval_status="APPROVED",
            approved_by="AMC_TRANSIT_CELL",
            execution_status="COMPLETED",
            started_at="2026-06-05T08:00:00Z",
            completed_at="2026-06-05T18:00:00Z"
        ))

        res = verify_intervention_impact(ImpactVerificationRequest(
            action_id=action["action_id"],
            baseline_date="2026-06-05",
            followup_date="2026-06-06"
        ))

        assert res["status"] == "INSUFFICIENT_DATA_MISSING_OBSERVATIONS"
        assert res["action_completed"] is True
        assert res["causal_claim_allowed"] is False
        assert "missing_components" in res
        assert "Impact results not manufactured" in res["disclaimer"]

    def test_05_missing_control_data_falls_back_safely(self):
        """When control ward data is missing, DiD must not be manufactured."""
        # W4 has completed action and treated outcomes
        action = record_executed_action(ExecutedActionCreate(
            ward_id="W4",
            intervention_type="hydration_kiosk",
            approval_status="APPROVED",
            approved_by="AMC_HEALTH_OFFICER",
            execution_status="COMPLETED",
            started_at="2026-06-07T08:00:00Z",
            completed_at="2026-06-07T18:00:00Z"
        ))
        record_verified_outcome(VerifiedOutcomeCreate(
            ward_id="W4",
            measurement_date="2026-06-07",
            hospital_heat_admissions=8,
            provenance="REAL"
        ))
        record_verified_outcome(VerifiedOutcomeCreate(
            ward_id="W4",
            action_id=action["action_id"],
            measurement_date="2026-06-08",
            hospital_heat_admissions=4,
            provenance="REAL"
        ))

        # Specify control ward W8 which has NO outcomes for these dates
        res = verify_intervention_impact(ImpactVerificationRequest(
            action_id=action["action_id"],
            control_ward_id="W8",
            baseline_date="2026-06-07",
            followup_date="2026-06-08"
        ))

        # DiD must be flagged ineligible
        assert res["difference_in_differences"]["eligible"] is False
        assert "Insufficient data for comparison ward" in res["difference_in_differences"]["reason"]
        # Falls back to simple before-after without causal claim
        assert res["evaluation_methodology"] == "SIMPLE_BEFORE_AFTER"
        assert res["causal_claim_allowed"] is False

    def test_06_synthetic_data_labeled_as_simulated(self):
        """Ensure simulations and synthetic data are explicitly labeled and disclaimed."""
        action = record_executed_action(ExecutedActionCreate(
            ward_id="W5",
            intervention_type="drainage_inspection_clean",
            approval_status="APPROVED",
            approved_by="AMC_ENGINEERING_DEPT",
            execution_status="COMPLETED",
            started_at="2026-06-09T08:00:00Z",
            completed_at="2026-06-09T16:00:00Z"
        ))

        # Ingest SIMULATED outcomes
        record_verified_outcome(VerifiedOutcomeCreate(
            ward_id="W5",
            measurement_date="2026-06-09",
            hazard_type="waterlogging",
            waterlogging_depth_cm=55.0,
            provenance="SIMULATED",
            data_source="SWMM_SIMULATOR"
        ))
        record_verified_outcome(VerifiedOutcomeCreate(
            ward_id="W5",
            action_id=action["action_id"],
            measurement_date="2026-06-10",
            hazard_type="waterlogging",
            waterlogging_depth_cm=20.0,
            provenance="SIMULATED",
            data_source="SWMM_SIMULATOR"
        ))

        res = verify_intervention_impact(ImpactVerificationRequest(
            action_id=action["action_id"],
            primary_metric="waterlogging_depth_cm",
            baseline_date="2026-06-09",
            followup_date="2026-06-10"
        ))

        assert res["is_synthetic_demonstration"] is True
        assert res["synthetic_disclaimer"] is not None
        assert "DEMONSTRATION ONLY" in res["synthetic_disclaimer"]

    def test_07_water_shortage_complaints_verification(self):
        """Test verification on water shortage complaints metric."""
        action = record_executed_action(ExecutedActionCreate(
            ward_id="W7",
            intervention_type="water_tanker_dispatch",
            approval_status="APPROVED",
            approved_by="AMC_WATER_SUPPLY_CELL",
            execution_status="COMPLETED",
            started_at="2026-06-11T07:00:00Z",
            completed_at="2026-06-11T15:00:00Z"
        ))

        record_verified_outcome(VerifiedOutcomeCreate(
            ward_id="W7",
            measurement_date="2026-06-11",
            hazard_type="water_shortage",
            water_scarcity_complaints=24,
            provenance="REAL"
        ))
        record_verified_outcome(VerifiedOutcomeCreate(
            ward_id="W7",
            action_id=action["action_id"],
            measurement_date="2026-06-12",
            hazard_type="water_shortage",
            water_scarcity_complaints=8,
            provenance="REAL"
        ))

        res = verify_intervention_impact(ImpactVerificationRequest(
            action_id=action["action_id"],
            primary_metric="water_scarcity_complaints",
            baseline_date="2026-06-11",
            followup_date="2026-06-12"
        ))

        assert res["primary_metric"] == "water_scarcity_complaints"
        assert res["observed_delta"] == -16.0
        assert res["intended_outcome_observed"] is True

    def test_08_fastapi_endpoints_integration(self, client):
        """Test REST API endpoints for impact verification."""
        # 1. Create completed action
        action = record_executed_action(ExecutedActionCreate(
            ward_id="W6",
            intervention_type="cooling_center",
            approval_status="APPROVED",
            approved_by="AMC_HEALTH_OFFICER",
            execution_status="COMPLETED",
            started_at="2026-06-13T09:00:00Z",
            completed_at="2026-06-13T19:00:00Z"
        ))
        act_id = action["action_id"]

        record_verified_outcome(VerifiedOutcomeCreate(
            ward_id="W6",
            measurement_date="2026-06-13",
            hospital_heat_admissions=9,
            provenance="REAL"
        ))
        record_verified_outcome(VerifiedOutcomeCreate(
            ward_id="W6",
            action_id=act_id,
            measurement_date="2026-06-14",
            hospital_heat_admissions=4,
            provenance="REAL"
        ))

        # 2. POST /api/impact/verify
        r_post = client.post("/api/impact/verify", json={
            "action_id": act_id,
            "primary_metric": "hospital_heat_admissions",
            "baseline_date": "2026-06-13",
            "followup_date": "2026-06-14"
        })
        assert r_post.status_code == 200
        data = r_post.json()
        verif_id = data["verification_id"]
        assert data["status"] == "VERIFIED_COMPLETED"
        assert data["observed_delta"] == -5.0

        # 3. GET /api/impact/verifications
        r_list = client.get(f"/api/impact/verifications?action_id={act_id}")
        assert r_list.status_code == 200
        assert len(r_list.json()["verifications"]) >= 1

        # 4. GET /api/impact/verifications/{verification_id}
        r_single = client.get(f"/api/impact/verifications/{verif_id}")
        assert r_single.status_code == 200
        assert r_single.json()["verification_id"] == verif_id

        # 5. GET /api/impact/actions/{action_id}
        r_act_verif = client.get(f"/api/impact/actions/{act_id}")
        assert r_act_verif.status_code == 200
        assert len(r_act_verif.json()["verifications"]) >= 1

    def test_09_error_handling_and_404s(self, client):
        """Test HTTP 404 on non-existent action or verification IDs."""
        r_bad_act = client.post("/api/impact/verify", json={
            "action_id": "non_existent_action_999"
        })
        assert r_bad_act.status_code == 404

        r_bad_verif = client.get("/api/impact/verifications/non_existent_verif_999")
        assert r_bad_verif.status_code == 404


"""
ClimateShield - Unit Tests for Impact Verification Module
Validates empirical change calculation, indicator compatibility, directional improvement,
data provenance classification, zero-division resilience, and synthetic demonstration datasets.
"""

import unittest
from datetime import datetime, timezone
import math

from backend.impact_verification import (
    SourceType,
    QualityStatus,
    Direction,
    Observation,
    ObservationAggregate,
    IndicatorImpactResult,
    InterventionImpactAssessment,
    ATTRIBUTION_DISCLAIMER,
    DEMONSTRATION_DATA_NOTICE,
    INDICATOR_REGISTRY,
    resolve_canonical_indicator,
    normalize_unit_string,
    convert_value_to_canonical,
    validate_observation,
    aggregate_observations,
    calculate_indicator_change,
    assess_intervention_impact,
    generate_synthetic_demonstration_data
)


class TestImpactVerificationIndicators(unittest.TestCase):
    """Test resolution of canonical indicators and unit normalization."""

    def test_canonical_indicator_resolution(self):
        self.assertEqual(resolve_canonical_indicator("ambient_temperature"), "ambient_temperature")
        self.assertEqual(resolve_canonical_indicator("temp_c"), "ambient_temperature")
        self.assertEqual(resolve_canonical_indicator("wbgt"), "wbgt")
        self.assertEqual(resolve_canonical_indicator("water_depth"), "flood_water_depth")
        self.assertEqual(resolve_canonical_indicator("flood_duration"), "waterlogging_duration")
        self.assertEqual(resolve_canonical_indicator("water_delivered"), "water_delivered")
        self.assertEqual(resolve_canonical_indicator("scarcity_complaints"), "water_scarcity_complaints")

    def test_unit_normalization(self):
        self.assertEqual(normalize_unit_string("°C"), "celsius")
        self.assertEqual(normalize_unit_string("degC"), "celsius")
        self.assertEqual(normalize_unit_string("m"), "m")
        self.assertEqual(normalize_unit_string("cm"), "cm")
        self.assertEqual(normalize_unit_string("litres"), "liters")
        self.assertEqual(normalize_unit_string("hrs"), "hours")

    def test_unit_conversion_to_canonical(self):
        # 0.5 meters -> 50.0 cm for flood water depth
        val, ok = convert_value_to_canonical(0.5, "m", "cm")
        self.assertTrue(ok)
        self.assertAlmostEqual(val, 50.0)

        # 120 minutes -> 2.0 hours for waterlogging duration
        val, ok = convert_value_to_canonical(120.0, "minutes", "hours")
        self.assertTrue(ok)
        self.assertAlmostEqual(val, 2.0)

        # 5 kL -> 5000 liters for water availability
        val, ok = convert_value_to_canonical(5.0, "kl", "liters")
        self.assertTrue(ok)
        self.assertAlmostEqual(val, 5000.0)


class TestObservationValidation(unittest.TestCase):
    """Test validation of observation data and physical plausibility bounds."""

    def test_valid_observation(self):
        raw = {
            "indicator": "ambient_temperature",
            "value": 42.5,
            "unit": "°C",
            "timestamp": "2026-05-15T14:00:00Z",
            "period": "BASELINE",
            "ward_id": "W1"
        }
        obs, err = validate_observation(raw)
        self.assertIsNone(err)
        self.assertIsNotNone(obs)
        self.assertEqual(obs.value, 42.5)
        self.assertEqual(obs.unit, "celsius")
        self.assertEqual(obs.period, "BASELINE")

    def test_reject_nan_or_infinite_value(self):
        raw_nan = {
            "indicator": "wbgt",
            "value": float("nan"),
            "unit": "°C",
            "timestamp": "2026-05-15T14:00:00Z"
        }
        obs, err = validate_observation(raw_nan)
        self.assertIsNone(obs)
        self.assertIn("NaN", err)

        raw_inf = {
            "indicator": "wbgt",
            "value": float("inf"),
            "unit": "°C",
            "timestamp": "2026-05-15T14:00:00Z"
        }
        obs, err = validate_observation(raw_inf)
        self.assertIsNone(obs)
        self.assertIn("Infinite", err)

    def test_reject_out_of_bounds_physical_value(self):
        # 95°C air temperature is physically impossible for weather observation
        raw = {
            "indicator": "ambient_temperature",
            "value": 95.0,
            "unit": "°C",
            "timestamp": "2026-05-15T14:00:00Z"
        }
        obs, err = validate_observation(raw)
        self.assertIsNone(obs)
        self.assertIn("exceeds physical plausibility bounds", err)

        # Negative water depth is invalid
        raw_neg_depth = {
            "indicator": "flood_water_depth",
            "value": -15.0,
            "unit": "cm",
            "timestamp": "2026-07-15T10:00:00Z"
        }
        obs, err = validate_observation(raw_neg_depth)
        self.assertIsNone(obs)
        self.assertIn("exceeds physical plausibility bounds", err)

    def test_reject_incompatible_unit_for_known_indicator(self):
        # Liters is incompatible with temperature
        raw = {
            "indicator": "ambient_temperature",
            "value": 40.0,
            "unit": "liters",
            "timestamp": "2026-05-15T14:00:00Z"
        }
        obs, err = validate_observation(raw)
        self.assertIsNone(obs)
        self.assertIn("Incompatible unit", err)


class TestObservationAggregation(unittest.TestCase):
    """Test aggregation of multiple observations with compatibility checks."""

    def test_aggregate_compatible_observations(self):
        obs_list = [
            {"indicator": "ambient_temperature", "value": 42.0, "unit": "°C", "timestamp": "2026-05-11T12:00:00Z", "period": "BASELINE", "ward_id": "W1"},
            {"indicator": "ambient_temperature", "value": 44.0, "unit": "°C", "timestamp": "2026-05-11T14:00:00Z", "period": "BASELINE", "ward_id": "W1"},
            {"indicator": "ambient_temperature", "value": 43.0, "unit": "°C", "timestamp": "2026-05-11T16:00:00Z", "period": "BASELINE", "ward_id": "W1"}
        ]
        agg, err = aggregate_observations(obs_list, "BASELINE", target_ward_id="W1")
        self.assertIsNone(err)
        self.assertIsNotNone(agg)
        self.assertEqual(agg.observation_count, 3)
        self.assertEqual(agg.mean_value, 43.0)
        self.assertEqual(agg.median_value, 43.0)
        self.assertEqual(agg.min_value, 42.0)
        self.assertEqual(agg.max_value, 44.0)

    def test_reject_aggregation_of_mismatched_locations(self):
        obs_list = [
            {"indicator": "ambient_temperature", "value": 42.0, "unit": "°C", "timestamp": "2026-05-11T12:00:00Z", "period": "BASELINE", "ward_id": "W1"},
            {"indicator": "ambient_temperature", "value": 43.0, "unit": "°C", "timestamp": "2026-05-11T14:00:00Z", "period": "BASELINE", "ward_id": "W2"}
        ]
        agg, err = aggregate_observations(obs_list, "BASELINE", target_ward_id="W1")
        self.assertIsNone(agg)
        self.assertIn("INCOMPATIBLE_LOCATIONS", err)


class TestImpactCalculations(unittest.TestCase):
    """Test calculation of absolute change, percentage change, and directionality."""

    def test_decrease_is_beneficial_improvement(self):
        # Ambient temperature drops from 44.0°C to 40.0°C
        base_agg = ObservationAggregate(
            indicator="ambient_temperature", canonical_indicator="ambient_temperature",
            period="BASELINE", unit="celsius", mean_value=44.0, median_value=44.0,
            min_value=44.0, max_value=44.0, observation_count=1,
            timestamps=["2026-05-11T14:00:00Z"], source_types=[SourceType.MEASURED],
            source_names=["MET_STATION_1"], quality_statuses=[QualityStatus.VERIFIED],
            is_synthetic=False, location_tags=[]
        )
        post_agg = ObservationAggregate(
            indicator="ambient_temperature", canonical_indicator="ambient_temperature",
            period="FOLLOW_UP", unit="celsius", mean_value=40.0, median_value=40.0,
            min_value=40.0, max_value=40.0, observation_count=1,
            timestamps=["2026-05-15T14:00:00Z"], source_types=[SourceType.MEASURED],
            source_names=["MET_STATION_1"], quality_statuses=[QualityStatus.VERIFIED],
            is_synthetic=False, location_tags=[]
        )

        res = calculate_indicator_change(base_agg, post_agg, "ambient_temperature")
        self.assertEqual(res.difference, -4.0)
        self.assertAlmostEqual(res.percentage_change, -9.09, places=2)
        self.assertTrue(res.is_improvement)
        self.assertEqual(res.improvement_magnitude, 4.0)
        self.assertEqual(res.quality_status, QualityStatus.VERIFIED)
        self.assertFalse(res.is_synthetic)
        # Verify interval scale note is present for Celsius
        self.assertTrue(any("INTERVAL_SCALE_NOTE" in n for n in res.notes))

    def test_increase_is_beneficial_improvement(self):
        # Water delivered increases from 10,000L to 30,000L
        base_agg = ObservationAggregate(
            indicator="water_delivered", canonical_indicator="water_delivered",
            period="BASELINE", unit="liters", mean_value=10000.0, median_value=10000.0,
            min_value=10000.0, max_value=10000.0, observation_count=1,
            timestamps=["2026-05-10T10:00:00Z"], source_types=[SourceType.EXTERNAL_OBSERVATION],
            source_names=["TANKER_LOG"], quality_statuses=[QualityStatus.VERIFIED],
            is_synthetic=False, location_tags=[]
        )
        post_agg = ObservationAggregate(
            indicator="water_delivered", canonical_indicator="water_delivered",
            period="FOLLOW_UP", unit="liters", mean_value=30000.0, median_value=30000.0,
            min_value=30000.0, max_value=30000.0, observation_count=1,
            timestamps=["2026-05-16T10:00:00Z"], source_types=[SourceType.EXTERNAL_OBSERVATION],
            source_names=["TANKER_LOG"], quality_statuses=[QualityStatus.VERIFIED],
            is_synthetic=False, location_tags=[]
        )

        res = calculate_indicator_change(base_agg, post_agg, "water_delivered")
        self.assertEqual(res.difference, 20000.0)
        self.assertEqual(res.percentage_change, 200.0)
        self.assertTrue(res.is_improvement)
        self.assertEqual(res.improvement_magnitude, 20000.0)

    def test_zero_baseline_division_safety(self):
        # Baseline complaints = 0, Follow-up complaints = 5
        base_agg = ObservationAggregate(
            indicator="water_scarcity_complaints", canonical_indicator="water_scarcity_complaints",
            period="BASELINE", unit="count", mean_value=0.0, median_value=0.0,
            min_value=0.0, max_value=0.0, observation_count=1,
            timestamps=["2026-05-10T00:00:00Z"], source_types=[SourceType.EXTERNAL_OBSERVATION],
            source_names=["HELPLINE"], quality_statuses=[QualityStatus.VERIFIED],
            is_synthetic=False, location_tags=[]
        )
        post_agg = ObservationAggregate(
            indicator="water_scarcity_complaints", canonical_indicator="water_scarcity_complaints",
            period="FOLLOW_UP", unit="count", mean_value=5.0, median_value=5.0,
            min_value=5.0, max_value=5.0, observation_count=1,
            timestamps=["2026-05-16T00:00:00Z"], source_types=[SourceType.EXTERNAL_OBSERVATION],
            source_names=["HELPLINE"], quality_statuses=[QualityStatus.VERIFIED],
            is_synthetic=False, location_tags=[]
        )

        res = calculate_indicator_change(base_agg, post_agg, "water_scarcity_complaints")
        self.assertEqual(res.difference, 5.0)
        # Percentage change must be None to prevent ZeroDivisionError
        self.assertIsNone(res.percentage_change)
        self.assertFalse(res.is_improvement)
        self.assertTrue(any("ZERO_BASELINE_PERCENTAGE_UNDEFINED" in n for n in res.notes))

    def test_no_change_neutral(self):
        base_agg = ObservationAggregate(
            indicator="hospital_heat_admissions", canonical_indicator="hospital_heat_admissions",
            period="BASELINE", unit="count", mean_value=12.0, median_value=12.0,
            min_value=12.0, max_value=12.0, observation_count=1,
            timestamps=["2026-05-10T00:00:00Z"], source_types=[SourceType.MEASURED],
            source_names=["AMC_SURVEILLANCE"], quality_statuses=[QualityStatus.VERIFIED],
            is_synthetic=False, location_tags=[]
        )
        post_agg = ObservationAggregate(
            indicator="hospital_heat_admissions", canonical_indicator="hospital_heat_admissions",
            period="FOLLOW_UP", unit="count", mean_value=12.0, median_value=12.0,
            min_value=12.0, max_value=12.0, observation_count=1,
            timestamps=["2026-05-16T00:00:00Z"], source_types=[SourceType.MEASURED],
            source_names=["AMC_SURVEILLANCE"], quality_statuses=[QualityStatus.VERIFIED],
            is_synthetic=False, location_tags=[]
        )

        res = calculate_indicator_change(base_agg, post_agg, "hospital_heat_admissions")
        self.assertEqual(res.difference, 0.0)
        self.assertEqual(res.percentage_change, 0.0)
        self.assertFalse(res.is_improvement)
        self.assertEqual(res.improvement_magnitude, 0.0)
        self.assertTrue(any("NO_CHANGE" in n for n in res.notes))

    def test_missing_baseline_handling(self):
        post_agg = ObservationAggregate(
            indicator="flood_water_depth", canonical_indicator="flood_water_depth",
            period="FOLLOW_UP", unit="cm", mean_value=25.0, median_value=25.0,
            min_value=25.0, max_value=25.0, observation_count=1,
            timestamps=["2026-07-16T10:00:00Z"], source_types=[SourceType.MEASURED],
            source_names=["DEPTH_SENSOR_1"], quality_statuses=[QualityStatus.VERIFIED],
            is_synthetic=False, location_tags=[]
        )

        res = calculate_indicator_change(None, post_agg, "flood_water_depth")
        self.assertIsNone(res.baseline_value)
        self.assertEqual(res.follow_up_value, 25.0)
        self.assertIsNone(res.difference)
        self.assertIsNone(res.percentage_change)
        self.assertIsNone(res.is_improvement)
        self.assertEqual(res.quality_status, QualityStatus.MISSING_BASELINE)

    def test_missing_follow_up_handling(self):
        base_agg = ObservationAggregate(
            indicator="flood_water_depth", canonical_indicator="flood_water_depth",
            period="BASELINE", unit="cm", mean_value=70.0, median_value=70.0,
            min_value=70.0, max_value=70.0, observation_count=1,
            timestamps=["2026-07-15T10:00:00Z"], source_types=[SourceType.MEASURED],
            source_names=["DEPTH_SENSOR_1"], quality_statuses=[QualityStatus.VERIFIED],
            is_synthetic=False, location_tags=[]
        )

        res = calculate_indicator_change(base_agg, None, "flood_water_depth")
        self.assertEqual(res.baseline_value, 70.0)
        self.assertIsNone(res.follow_up_value)
        self.assertIsNone(res.difference)
        self.assertIsNone(res.percentage_change)
        self.assertIsNone(res.is_improvement)
        self.assertEqual(res.quality_status, QualityStatus.MISSING_FOLLOW_UP)

    def test_incompatible_units_between_periods(self):
        base_agg = ObservationAggregate(
            indicator="flood_water_depth", canonical_indicator="flood_water_depth",
            period="BASELINE", unit="cm", mean_value=60.0, median_value=60.0,
            min_value=60.0, max_value=60.0, observation_count=1,
            timestamps=["2026-07-15T10:00:00Z"], source_types=[SourceType.MEASURED],
            source_names=["DEPTH_SENSOR_1"], quality_statuses=[QualityStatus.VERIFIED],
            is_synthetic=False, location_tags=[]
        )
        post_agg = ObservationAggregate(
            indicator="flood_water_depth", canonical_indicator="flood_water_depth",
            period="FOLLOW_UP", unit="liters", mean_value=2000.0, median_value=2000.0,
            min_value=2000.0, max_value=2000.0, observation_count=1,
            timestamps=["2026-07-16T10:00:00Z"], source_types=[SourceType.MEASURED],
            source_names=["DEPTH_SENSOR_1"], quality_statuses=[QualityStatus.VERIFIED],
            is_synthetic=False, location_tags=[]
        )

        res = calculate_indicator_change(base_agg, post_agg, "flood_water_depth")
        self.assertIsNone(res.difference)
        self.assertIsNone(res.percentage_change)
        self.assertEqual(res.quality_status, QualityStatus.INCOMPATIBLE_UNITS)


class TestStructuredInterventionImpactAssessment(unittest.TestCase):
    """Test full structured impact assessment workflow across multiple indicators."""

    def test_multi_indicator_real_assessment(self):
        observations = [
            # Heat observations in W1
            {"indicator": "ambient_temperature", "value": 44.5, "unit": "°C", "timestamp": "2026-05-11T14:00:00Z", "period": "BASELINE", "ward_id": "W1", "source_type": SourceType.MEASURED},
            {"indicator": "ambient_temperature", "value": 41.5, "unit": "°C", "timestamp": "2026-05-15T14:00:00Z", "period": "FOLLOW_UP", "ward_id": "W1", "source_type": SourceType.MEASURED},
            # 108 Emergency calls in W1
            {"indicator": "emergency_108_calls", "value": 18.0, "unit": "count", "timestamp": "2026-05-11T20:00:00Z", "period": "BASELINE", "ward_id": "W1", "source_type": SourceType.EXTERNAL_OBSERVATION},
            {"indicator": "emergency_108_calls", "value": 10.0, "unit": "count", "timestamp": "2026-05-15T20:00:00Z", "period": "FOLLOW_UP", "ward_id": "W1", "source_type": SourceType.EXTERNAL_OBSERVATION}
        ]

        assessment = assess_intervention_impact(
            intervention_id="cooling_center",
            ward_id="W1",
            intervention_type="PHYSICAL_REFUGE_AND_COOLING",
            observations=observations,
            baseline_period={"start": "2026-05-11", "end": "2026-05-12"},
            follow_up_period={"start": "2026-05-15", "end": "2026-05-16"}
        )

        self.assertEqual(assessment.ward_id, "W1")
        self.assertEqual(assessment.intervention_id, "cooling_center")
        self.assertEqual(len(assessment.indicators_assessed), 2)
        self.assertEqual(assessment.summary["improved_indicators_count"], 2)
        self.assertFalse(assessment.overall_is_synthetic)
        self.assertEqual(assessment.attribution_disclaimer, ATTRIBUTION_DISCLAIMER)

        # Inspect ambient_temperature
        temp_res = assessment.results_by_indicator["ambient_temperature"]
        self.assertEqual(temp_res["difference"], -3.0)
        self.assertTrue(temp_res["is_improvement"])

        # Inspect emergency_108_calls
        calls_res = assessment.results_by_indicator["emergency_108_calls"]
        self.assertEqual(calls_res["difference"], -8.0)
        self.assertTrue(calls_res["is_improvement"])


class TestSyntheticDemonstrationMode(unittest.TestCase):
    """Test clearly labelled synthetic demonstration data mode."""

    def test_generate_synthetic_heat_data(self):
        demo = generate_synthetic_demonstration_data("cooling_center", "W1", "PHYSICAL_REFUGE_AND_COOLING", hazard_type="heat")
        self.assertTrue(demo["is_synthetic"])
        self.assertIn("DEMONSTRATION ONLY", demo["demonstration_notice"])
        self.assertGreater(len(demo["observations"]), 0)

        # All generated observations must be explicitly flagged as SYNTHETIC_DEMO
        for obs in demo["observations"]:
            self.assertEqual(obs["source_type"], SourceType.SYNTHETIC_DEMO)
            self.assertEqual(obs["quality_status"], QualityStatus.SYNTHETIC_DEMO)

        # Execute structured assessment with the synthetic data
        assessment = assess_intervention_impact(
            intervention_id=demo["intervention_id"],
            ward_id=demo["ward_id"],
            intervention_type=demo["intervention_type"],
            observations=demo["observations"],
            baseline_period=demo["baseline_period"],
            follow_up_period=demo["follow_up_period"]
        )

        self.assertTrue(assessment.overall_is_synthetic)
        self.assertEqual(assessment.overall_quality_status, QualityStatus.SYNTHETIC_DEMO)
        self.assertIn("ambient_temperature", assessment.results_by_indicator)
        temp_res = assessment.results_by_indicator["ambient_temperature"]
        self.assertTrue(temp_res["is_synthetic"])
        self.assertTrue(any("DEMONSTRATION ONLY" in n for n in temp_res["notes"]))

    def test_generate_synthetic_flood_data(self):
        demo = generate_synthetic_demonstration_data("dewatering_pump_deployment", "W4", "DEWATERING_OPERATION", hazard_type="flood")
        self.assertTrue(demo["is_synthetic"])
        assessment = assess_intervention_impact(
            intervention_id=demo["intervention_id"],
            ward_id=demo["ward_id"],
            intervention_type=demo["intervention_type"],
            observations=demo["observations"]
        )
        self.assertTrue(assessment.overall_is_synthetic)
        self.assertIn("flood_water_depth", assessment.results_by_indicator)
        self.assertTrue(assessment.results_by_indicator["flood_water_depth"]["is_improvement"])

    def test_generate_synthetic_water_shortage_data(self):
        demo = generate_synthetic_demonstration_data("water_tanker_allocation", "W7", "POTABLE_WATER_SUPPLY", hazard_type="water_shortage")
        self.assertTrue(demo["is_synthetic"])
        assessment = assess_intervention_impact(
            intervention_id=demo["intervention_id"],
            ward_id=demo["ward_id"],
            intervention_type=demo["intervention_type"],
            observations=demo["observations"]
        )
        self.assertTrue(assessment.overall_is_synthetic)
        self.assertIn("water_delivered", assessment.results_by_indicator)
        self.assertTrue(assessment.results_by_indicator["water_delivered"]["is_improvement"])


class TestImpactAssessmentStorage(unittest.TestCase):
    """Test recording, retrieval, validation, duplicate prevention, and history preservation."""

    def setUp(self):
        from backend.database import get_db_connection
        # Clean test records if left over
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM impact_assessment_history WHERE assessment_id LIKE 'TEST_%';")
        cursor.execute("DELETE FROM impact_assessments WHERE assessment_id LIKE 'TEST_%';")
        conn.commit()
        conn.close()

    def test_record_and_retrieve_valid_assessment(self):
        from backend.impact_verification import (
            record_impact_assessment,
            retrieve_impact_assessment,
            ExecutionStatus
        )
        test_aid = "TEST_REC_001"
        payload = {
            "assessment_id": test_aid,
            "intervention_id": "cooling_center",
            "ward_id": "W1",
            "intervention_type": "PHYSICAL_REFUGE_AND_COOLING",
            "execution_status": ExecutionStatus.COMPLETED,
            "verification_status": "VERIFIED_EFFECTIVE",
            "provenance_mode": "MEASURED",
            "is_synthetic": False,
            "baseline_period": {"start": "2026-05-11", "end": "2026-05-12"},
            "follow_up_period": {"start": "2026-05-15", "end": "2026-05-16"},
            "indicators": {
                "ambient_temperature": {
                    "indicator": "ambient_temperature",
                    "baseline_value": 44.0,
                    "follow_up_value": 40.5,
                    "unit": "celsius",
                    "difference": -3.5,
                    "percentage_change": -7.95,
                    "beneficial_direction": "DECREASE_IS_BENEFICIAL",
                    "is_improvement": True,
                    "baseline_timestamps": ["2026-05-11T14:00:00Z"],
                    "follow_up_timestamps": ["2026-05-15T14:00:00Z"],
                    "source_types": ["MEASURED"],
                    "quality_status": "VERIFIED"
                }
            },
            "data_quality_warnings": [],
            "summary": {"improved_indicators_count": 1}
        }

        saved = record_impact_assessment(payload)
        self.assertEqual(saved["assessment_id"], test_aid)
        self.assertEqual(saved["save_status"], "CREATED")
        self.assertEqual(saved["version"], 1)

        retrieved = retrieve_impact_assessment(test_aid)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["assessment_id"], test_aid)
        self.assertEqual(retrieved["intervention_id"], "cooling_center")
        self.assertEqual(retrieved["ward_id"], "W1")
        self.assertEqual(retrieved["execution_status"], "COMPLETED")
        self.assertIn("ambient_temperature", retrieved["indicators"])
        self.assertEqual(retrieved["indicators"]["ambient_temperature"]["difference"], -3.5)
        self.assertEqual(retrieved["version"], 1)
        self.assertIn("created_at", retrieved)
        self.assertIn("updated_at", retrieved)

    def test_missing_required_fields_rejection(self):
        from backend.impact_verification import record_impact_assessment

        # Missing assessment_id
        with self.assertRaises(ValueError):
            record_impact_assessment({
                "intervention_id": "cooling_center",
                "ward_id": "W1",
                "intervention_type": "COOLING",
                "indicators": {"wbgt": {"unit": "celsius"}}
            })

        # Missing intervention_id
        with self.assertRaises(ValueError):
            record_impact_assessment({
                "assessment_id": "TEST_INVALID_2",
                "ward_id": "W1",
                "intervention_type": "COOLING",
                "indicators": {"wbgt": {"unit": "celsius"}}
            })

        # Missing indicators
        with self.assertRaises(ValueError):
            record_impact_assessment({
                "assessment_id": "TEST_INVALID_3",
                "intervention_id": "cooling_center",
                "ward_id": "W1",
                "intervention_type": "COOLING"
            })

    def test_inconsistent_unit_rejection(self):
        from backend.impact_verification import record_impact_assessment
        # Liters is inconsistent with ambient temperature
        payload = {
            "assessment_id": "TEST_BAD_UNIT",
            "intervention_id": "cooling_center",
            "ward_id": "W1",
            "intervention_type": "COOLING",
            "indicators": {
                "ambient_temperature": {
                    "baseline_value": 44.0,
                    "follow_up_value": 40.0,
                    "unit": "liters"  # Incompatible unit!
                }
            }
        }
        with self.assertRaises(ValueError) as ctx:
            record_impact_assessment(payload)
        self.assertIn("Inconsistent unit", str(ctx.exception))

    def test_reject_uncompleted_recommendation(self):
        from backend.impact_verification import record_impact_assessment
        # Attempting to verify an uncompleted intervention merely because it was recommended
        payload = {
            "assessment_id": "TEST_UNCOMPLETED",
            "intervention_id": "shade_tree_deployment",
            "ward_id": "W3",
            "intervention_type": "PASSIVE_COOLING",
            "execution_status": "RECOMMENDED",  # Merely recommended!
            "indicators": {
                "ambient_temperature": {"unit": "celsius", "difference": -2.0}
            }
        }
        with self.assertRaises(ValueError) as ctx:
            record_impact_assessment(payload)
        self.assertIn("UNCOMPLETED_INTERVENTION", str(ctx.exception))

        # PENDING_HUMAN_APPROVAL should also be rejected
        payload["execution_status"] = "PENDING_HUMAN_APPROVAL"
        with self.assertRaises(ValueError) as ctx:
            record_impact_assessment(payload)
        self.assertIn("UNCOMPLETED_INTERVENTION", str(ctx.exception))

    def test_duplicate_prevention_and_idempotency(self):
        from backend.impact_verification import record_impact_assessment
        from backend.database import DuplicateAssessmentError

        test_aid = "TEST_DUP_CHECK"
        payload = {
            "assessment_id": test_aid,
            "intervention_id": "drinking_water_point",
            "ward_id": "W2",
            "intervention_type": "HYDRATION_DISTRIBUTION",
            "execution_status": "COMPLETED",
            "indicators": {
                "water_delivered": {
                    "baseline_value": 1000.0,
                    "follow_up_value": 3000.0,
                    "unit": "liters",
                    "difference": 2000.0
                }
            }
        }

        # 1. Initial save
        saved = record_impact_assessment(payload)
        self.assertEqual(saved["save_status"], "CREATED")

        # 2. Idempotent save with exact identical payload
        resaved = record_impact_assessment(payload)
        self.assertEqual(resaved["save_status"], "IDEMPOTENT_UNCHANGED")
        self.assertEqual(resaved["version"], 1)

        # 3. Accidental duplicate with conflicting/different payload without allow_update
        conflicting = dict(payload)
        conflicting["indicators"] = {
            "water_delivered": {
                "baseline_value": 1000.0,
                "follow_up_value": 5000.0,  # Changed value!
                "unit": "liters",
                "difference": 4000.0
            }
        }
        with self.assertRaises(DuplicateAssessmentError) as ctx:
            record_impact_assessment(conflicting, allow_update=False)
        self.assertIn("already exists", str(ctx.exception))

    def test_history_preservation_on_update(self):
        from backend.impact_verification import (
            record_impact_assessment,
            update_impact_assessment,
            retrieve_impact_assessment,
            retrieve_assessment_history
        )

        test_aid = "TEST_HIST_PRESERVE"
        initial_payload = {
            "assessment_id": test_aid,
            "intervention_id": "dewatering_pump",
            "ward_id": "W4",
            "intervention_type": "DEWATERING",
            "execution_status": "COMPLETED",
            "indicators": {
                "flood_water_depth": {
                    "baseline_value": 50.0,
                    "follow_up_value": 20.0,
                    "unit": "cm",
                    "difference": -30.0
                }
            }
        }

        # 1. Save version 1
        record_impact_assessment(initial_payload)
        v1 = retrieve_impact_assessment(test_aid)
        self.assertEqual(v1["version"], 1)

        # 2. Update to version 2
        updated_payload = dict(initial_payload)
        updated_payload["indicators"] = {
            "flood_water_depth": {
                "baseline_value": 50.0,
                "follow_up_value": 10.0,
                "unit": "cm",
                "difference": -40.0
            }
        }
        update_res = update_impact_assessment(
            test_aid,
            updated_payload,
            change_reason="Post-storm culvert recalibration"
        )
        self.assertEqual(update_res["save_status"], "UPDATED_AND_ARCHIVED")
        self.assertEqual(update_res["version"], 2)

        # 3. Verify current record has new values and version 2
        current = retrieve_impact_assessment(test_aid)
        self.assertEqual(current["version"], 2)
        self.assertEqual(current["indicators"]["flood_water_depth"]["difference"], -40.0)

        # 4. Verify historical snapshot preserved in impact_assessment_history
        history = retrieve_assessment_history(test_aid)
        self.assertEqual(len(history), 1)
        snapshot_v1 = history[0]
        self.assertEqual(snapshot_v1["version"], 1)
        self.assertEqual(snapshot_v1["change_reason"], "Post-storm culvert recalibration")
        self.assertEqual(snapshot_v1["snapshot"]["version"], 1)

    def test_pydantic_schema_validation(self):
        from backend.schemas import ImpactAssessmentCreate, ImpactAssessmentResponse

        valid_data = {
            "assessment_id": "TEST_SCHEMA_1",
            "intervention_id": "cool_roof_initiative",
            "ward_id": "W5",
            "intervention_type": "PASSIVE_COOLING",
            "execution_status": "COMPLETED",
            "verification_status": "VERIFIED_EFFECTIVE",
            "provenance_mode": "MEASURED",
            "is_synthetic": False,
            "baseline_period": {"start": "2026-05-01"},
            "follow_up_period": {"start": "2026-05-15"},
            "indicators": {
                "surface_temperature": {
                    "indicator": "surface_temperature",
                    "baseline_value": 52.0,
                    "follow_up_value": 44.0,
                    "unit": "celsius",
                    "difference": -8.0,
                    "percentage_change": -15.38,
                    "beneficial_direction": "DECREASE_IS_BENEFICIAL",
                    "is_improvement": True
                }
            }
        }

        # Should validate cleanly
        model = ImpactAssessmentCreate(**valid_data)
        self.assertEqual(model.assessment_id, "TEST_SCHEMA_1")
        self.assertEqual(model.indicators["surface_temperature"].unit, "celsius")


class TestImpactReportingSummary(unittest.TestCase):
    """Test reporting summary engine for empty datasets, mixed quality, deduplication, and aggregation."""

    def test_empty_dataset_handling(self):
        from backend.impact_verification import generate_impact_verification_summary
        res = generate_impact_verification_summary(assessments=[])
        self.assertEqual(res["status"], "EMPTY_DATASET")
        self.assertEqual(res["kpis"]["total_assessments_recorded"], 0)
        self.assertEqual(res["kpis"]["valid_before_after_comparisons_count"], 0)
        self.assertEqual(res["kpis"]["incomplete_assessments_count"], 0)
        self.assertEqual(res["by_ward"], {})
        self.assertEqual(res["by_indicator"], {})
        self.assertIn("PAIRWISE_ARITHMETIC_MEAN", res["aggregation_method"])
        self.assertIn("COUNTERFACTUAL CAUSATION", res["causal_attribution_caveat"].upper())

    def test_duplicate_pruning_and_version_selection(self):
        from backend.impact_verification import generate_impact_verification_summary
        # Two versions of ASSESS_01 (version 1 with diff -2.0, version 2 with diff -5.0) and one ASSESS_02
        records = [
            {
                "assessment_id": "ASSESS_01",
                "ward_id": "W1",
                "intervention_type": "COOLING",
                "version": 1,
                "provenance_mode": "MEASURED",
                "indicators": {
                    "ambient_temperature": {"baseline_value": 44.0, "follow_up_value": 42.0, "difference": -2.0, "unit": "celsius", "is_improvement": True}
                }
            },
            {
                "assessment_id": "ASSESS_01",
                "ward_id": "W1",
                "intervention_type": "COOLING",
                "version": 2,  # Latest version should be kept!
                "provenance_mode": "MEASURED",
                "indicators": {
                    "ambient_temperature": {"baseline_value": 44.0, "follow_up_value": 39.0, "difference": -5.0, "unit": "celsius", "is_improvement": True}
                }
            },
            {
                "assessment_id": "ASSESS_02",
                "ward_id": "W2",
                "intervention_type": "COOLING",
                "version": 1,
                "provenance_mode": "MEASURED",
                "indicators": {
                    "ambient_temperature": {"baseline_value": 42.0, "follow_up_value": 39.0, "difference": -3.0, "unit": "celsius", "is_improvement": True}
                }
            }
        ]

        summary = generate_impact_verification_summary(assessments=records)
        self.assertEqual(summary["kpis"]["total_assessments_recorded"], 3)
        self.assertEqual(summary["kpis"]["unique_assessments_count"], 2)
        self.assertEqual(summary["kpis"]["duplicate_records_pruned"], 1)

        # Ambient temperature mean diff should be (-5.0 + -3.0) / 2 = -4.0 (using version 2 of ASSESS_01)
        temp_stat = summary["by_indicator"]["ambient_temperature"]
        self.assertEqual(temp_stat["sample_size"], 2)
        self.assertEqual(temp_stat["mean_absolute_difference"], -4.0)

    def test_mixed_data_quality_and_provenance_counts(self):
        from backend.impact_verification import generate_impact_verification_summary, SourceType
        records = [
            {"assessment_id": "M1", "ward_id": "W1", "intervention_type": "T1", "provenance_mode": SourceType.MEASURED, "is_synthetic": False, "indicators": {"wbgt": {"baseline_value": 35.0, "follow_up_value": 32.0, "difference": -3.0, "unit": "celsius", "is_improvement": True}}},
            {"assessment_id": "M2", "ward_id": "W2", "intervention_type": "T1", "provenance_mode": SourceType.EXTERNAL_OBSERVATION, "is_synthetic": False, "indicators": {"wbgt": {"baseline_value": 36.0, "follow_up_value": 33.0, "difference": -3.0, "unit": "celsius", "is_improvement": True}}},
            {"assessment_id": "M3", "ward_id": "W3", "intervention_type": "T1", "provenance_mode": SourceType.ESTIMATED, "is_synthetic": False, "indicators": {"wbgt": {"baseline_value": 34.0, "follow_up_value": 32.0, "difference": -2.0, "unit": "celsius", "is_improvement": True}}},
            {"assessment_id": "M4", "ward_id": "W4", "intervention_type": "T1", "provenance_mode": SourceType.SYNTHETIC_DEMO, "is_synthetic": True, "indicators": {"wbgt": {"baseline_value": 38.0, "follow_up_value": 30.0, "difference": -8.0, "unit": "celsius", "is_improvement": True}}}
        ]

        # 1. Real-world verified only (include_synthetic=False)
        real_summary = generate_impact_verification_summary(assessments=records, include_synthetic=False)
        self.assertEqual(real_summary["data_integrity_mode"], "REAL_WORLD_VERIFIED_ONLY")
        self.assertEqual(real_summary["kpis"]["provenance_counts"]["measured"], 1)
        self.assertEqual(real_summary["kpis"]["provenance_counts"]["external_observation"], 1)
        self.assertEqual(real_summary["kpis"]["provenance_counts"]["estimated"], 1)
        self.assertEqual(real_summary["kpis"]["provenance_counts"]["simulated_demo"], 1)
        # Synthetic record M4 must NOT be included in indicator statistics!
        wbgt_real = real_summary["by_indicator"]["wbgt"]
        self.assertEqual(wbgt_real["sample_size"], 3)  # Only M1, M2, M3
        self.assertAlmostEqual(wbgt_real["mean_absolute_difference"], -2.67, places=2)

        # 2. Including synthetic (include_synthetic=True)
        all_summary = generate_impact_verification_summary(assessments=records, include_synthetic=True)
        self.assertEqual(all_summary["data_integrity_mode"], "INCLUDES_SIMULATED_DEMO")
        wbgt_all = all_summary["by_indicator"]["wbgt"]
        self.assertEqual(wbgt_all["sample_size"], 4)

    def test_incomplete_assessments_categorization(self):
        from backend.impact_verification import generate_impact_verification_summary, QualityStatus
        records = [
            # 1. Valid before/after
            {"assessment_id": "INC_01", "ward_id": "W1", "intervention_type": "T1", "indicators": {"wbgt": {"baseline_value": 34.0, "follow_up_value": 31.0, "difference": -3.0, "unit": "celsius"}}},
            # 2. Missing baseline
            {"assessment_id": "INC_02", "ward_id": "W1", "intervention_type": "T1", "indicators": {"wbgt": {"baseline_value": None, "follow_up_value": 31.0, "difference": None, "unit": "celsius", "quality_status": QualityStatus.MISSING_BASELINE}}},
            # 3. Missing follow-up
            {"assessment_id": "INC_03", "ward_id": "W1", "intervention_type": "T1", "indicators": {"wbgt": {"baseline_value": 34.0, "follow_up_value": None, "difference": None, "unit": "celsius", "quality_status": QualityStatus.MISSING_FOLLOW_UP}}},
            # 4. Incompatible units
            {"assessment_id": "INC_04", "ward_id": "W1", "intervention_type": "T1", "indicators": {"wbgt": {"baseline_value": 34.0, "follow_up_value": 100.0, "difference": None, "unit": "liters", "quality_status": QualityStatus.INCOMPATIBLE_UNITS}}}
        ]

        summary = generate_impact_verification_summary(assessments=records)
        self.assertEqual(summary["kpis"]["valid_before_after_comparisons_count"], 1)
        self.assertEqual(summary["kpis"]["incomplete_assessments_count"], 3)
        self.assertEqual(summary["incomplete_breakdown"]["missing_baseline"], 1)
        self.assertEqual(summary["incomplete_breakdown"]["missing_follow_up"], 1)
        self.assertEqual(summary["incomplete_breakdown"]["incompatible_units"], 1)

    def test_aggregation_never_treats_missing_as_zero(self):
        from backend.impact_verification import generate_impact_verification_summary, QualityStatus
        records = [
            # Two valid records
            {"assessment_id": "W_01", "ward_id": "W7", "intervention_type": "TANKER", "indicators": {"water_delivered": {"baseline_value": 10000.0, "follow_up_value": 20000.0, "difference": 10000.0, "unit": "liters", "is_improvement": True}}},
            {"assessment_id": "W_02", "ward_id": "W7", "intervention_type": "TANKER", "indicators": {"water_delivered": {"baseline_value": 20000.0, "follow_up_value": 40000.0, "difference": 20000.0, "unit": "liters", "is_improvement": True}}},
            # Record with missing follow-up (MUST NOT BE IMPUTED AS ZERO)
            {"assessment_id": "W_03", "ward_id": "W7", "intervention_type": "TANKER", "indicators": {"water_delivered": {"baseline_value": 15000.0, "follow_up_value": None, "difference": None, "unit": "liters", "quality_status": QualityStatus.MISSING_FOLLOW_UP}}}
        ]

        summary = generate_impact_verification_summary(assessments=records)
        stat = summary["by_indicator"]["water_delivered"]
        self.assertEqual(stat["sample_size"], 2)
        # Mean follow-up must be (20,000 + 40,000) / 2 = 30,000; NOT (20,000 + 40,000 + 0) / 3 = 20,000!
        self.assertEqual(stat["follow_up_aggregate_value"], 30000.0)
        self.assertEqual(stat["baseline_aggregate_value"], 15000.0)
        self.assertEqual(stat["mean_absolute_difference"], 15000.0)

    def test_indicator_unit_normalization_during_aggregation(self):
        from backend.impact_verification import generate_impact_verification_summary
        records = [
            # Record 1: Flood depth in cm (60 cm -> 20 cm, diff -40 cm)
            {"assessment_id": "F_01", "ward_id": "W4", "intervention_type": "PUMP", "indicators": {"flood_water_depth": {"baseline_value": 60.0, "follow_up_value": 20.0, "difference": -40.0, "unit": "cm", "is_improvement": True}}},
            # Record 2: Flood depth in meters (0.8 m -> 0.3 m, diff -0.5 m -> 80 cm -> 30 cm, diff -50 cm)
            {"assessment_id": "F_02", "ward_id": "W4", "intervention_type": "PUMP", "indicators": {"flood_water_depth": {"baseline_value": 0.8, "follow_up_value": 0.3, "difference": -0.5, "unit": "m", "is_improvement": True}}}
        ]

        summary = generate_impact_verification_summary(assessments=records)
        flood_stat = summary["by_indicator"]["flood_water_depth"]
        self.assertEqual(flood_stat["sample_size"], 2)
        self.assertEqual(flood_stat["unit"], "cm")
        # Baselines in cm: 60 and 80 -> mean 70.0 cm
        self.assertEqual(flood_stat["baseline_aggregate_value"], 70.0)
        # Follow-ups in cm: 20 and 30 -> mean 25.0 cm
        self.assertEqual(flood_stat["follow_up_aggregate_value"], 25.0)
        # Difference: (-40 + -50) / 2 = -45.0 cm
        self.assertEqual(flood_stat["mean_absolute_difference"], -45.0)

    def test_grouping_by_ward_and_intervention_type(self):
        from backend.impact_verification import generate_impact_verification_summary
        records = [
            {"assessment_id": "G_01", "ward_id": "W1", "intervention_type": "COOLING_CENTER", "indicators": {"wbgt": {"baseline_value": 35.0, "follow_up_value": 32.0, "difference": -3.0, "unit": "celsius", "is_improvement": True}}},
            {"assessment_id": "G_02", "ward_id": "W1", "intervention_type": "HYDRATION_KIOSK", "indicators": {"water_delivered": {"baseline_value": 1000.0, "follow_up_value": 3000.0, "difference": 2000.0, "unit": "liters", "is_improvement": True}}},
            {"assessment_id": "G_03", "ward_id": "W2", "intervention_type": "COOLING_CENTER", "indicators": {"wbgt": {"baseline_value": 34.0, "follow_up_value": 31.0, "difference": -3.0, "unit": "celsius", "is_improvement": True}}}
        ]

        summary = generate_impact_verification_summary(assessments=records)
        # Check ward grouping
        self.assertIn("W1", summary["by_ward"])
        w1_data = summary["by_ward"]["W1"]
        self.assertEqual(w1_data["total_assessments"], 2)
        self.assertEqual(w1_data["valid_comparisons"], 2)
        self.assertIn("COOLING_CENTER", w1_data["interventions_evaluated"])
        self.assertIn("HYDRATION_KIOSK", w1_data["interventions_evaluated"])

        # Check intervention type grouping
        self.assertIn("COOLING_CENTER", summary["by_intervention_type"])
        cc_data = summary["by_intervention_type"]["COOLING_CENTER"]
        self.assertEqual(cc_data["total_assessments"], 2)
        self.assertIn("W1", cc_data["wards_covered"])
        self.assertIn("W2", cc_data["wards_covered"])


if __name__ == "__main__":
    unittest.main()
