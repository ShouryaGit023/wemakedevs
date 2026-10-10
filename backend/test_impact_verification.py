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
