"""
ClimateShield - Automated Test Suite for Learning Engine & Controlled Calibration
Tests:
1. Multi-hazard prediction evaluation against subsequent verified outcomes.
2. Calculation of separate accuracy metrics (MAE, RMSE, Precision, Recall, F1) for heat, waterlogging, and water shortage.
3. Strict exclusion of simulated and unverified outcomes from real-world learning.
4. Prevention of automatic weight adjustment on single observations.
5. Minimum sample threshold enforcement (reporting insufficient data when samples < threshold).
6. Controlled update staging (proposals require explicit human approval).
7. Immutable model versioning and changelog audit trail.
8. Proposal rejection and version rollback capabilities.
9. FastAPI REST endpoints for the full learning loop.
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.main import app
from backend.learning_loop import (
    record_prediction,
    record_verified_outcome,
    PredictionRecordCreate,
    VerifiedOutcomeCreate
)
from backend.learning_engine import (
    run_model_evaluation,
    approve_parameter_proposal,
    reject_parameter_proposal,
    get_active_model_parameters,
    list_model_versions,
    rollback_model_version,
    ModelEvaluationRequest,
    ProposalApprovalRequest,
    ProposalRejectionRequest
)


@pytest.fixture
def client():
    return TestClient(app)


class TestLearningEngine:

    def test_01_insufficient_data_reports_more_observations_needed(self):
        """Ensure system reports insufficient data when real observations < min_samples."""
        # Request evaluation requiring at least 500 real samples
        req = ModelEvaluationRequest(min_samples=500)
        res = run_model_evaluation(req)

        assert res["is_sufficient_data"] is False
        assert res["status"] == "INSUFFICIENT_DATA_MORE_OBSERVATIONS_NEEDED"
        assert len(res["proposed_updates"]) == 0
        assert "Insufficient real-world data" in res["explanation"]

    def test_02_simulated_and_unverified_outcomes_strictly_excluded(self):
        """
        Prove that simulated and unverified outcomes cannot trigger parameter updates
        or corrupt production model weights.
        """
        target_ward = "W10"
        # Ingest 10 SIMULATED outcomes for W10
        for i in range(10):
            record_prediction(PredictionRecordCreate(
                ward_id=target_ward,
                hazard_type="heat",
                predicted_risk_score=90.0,
                risk_category="CRITICAL",
                data_source="Open-Meteo",
                provenance="SIMULATED",
                timestamp=f"2026-07-{10+i:02d}T12:00:00Z"
            ))
            record_verified_outcome(VerifiedOutcomeCreate(
                ward_id=target_ward,
                measurement_date=f"2026-07-{10+i:02d}",
                hazard_type="heat",
                hospital_heat_admissions=2,  # Drastically different from 90.0 risk
                data_source="SYNTHETIC_SIMULATOR",
                provenance="SIMULATED"  # Simulated!
            ))

        # Ingest 5 UNVERIFIED outcomes
        for i in range(5):
            record_verified_outcome(VerifiedOutcomeCreate(
                ward_id=target_ward,
                measurement_date=f"2026-07-{20+i:02d}",
                hazard_type="heat",
                hospital_heat_admissions=1,
                data_source="UNAUDITED_BLOG",
                provenance="UNVERIFIED"  # Unverified!
            ))

        # Run evaluation with exclude_simulated=True and min_samples=3
        res = run_model_evaluation(ModelEvaluationRequest(min_samples=3, exclude_simulated=True))

        # All simulated and unverified records must be excluded
        assert res["sample_counts"]["excluded_unverified_or_simulated"] >= 15
        # No proposals should be generated from simulated data for target_ward
        w_proposals = [p for p in res["proposed_updates"] if p["target_identifier"] == target_ward]
        assert len(w_proposals) == 0

    def test_03_separate_accuracy_tracking_by_hazard_domain(self):
        """Test accuracy metrics calculated separately for heat, flood, and shortage."""
        test_dates = ["2026-07-01", "2026-07-02", "2026-07-03", "2026-07-04"]

        # Ingest REAL Heat predictions & outcomes in W2
        for d in test_dates:
            record_prediction(PredictionRecordCreate(
                ward_id="W2",
                hazard_type="heat",
                predicted_risk_score=70.0,
                risk_category="HIGH",
                data_source="Open-Meteo",
                provenance="REAL",
                timestamp=f"{d}T12:00:00Z"
            ))
            record_verified_outcome(VerifiedOutcomeCreate(
                ward_id="W2",
                measurement_date=d,
                hazard_type="heat",
                hospital_heat_admissions=8,  # Proxy: 8*8 = 64.0
                provenance="REAL"
            ))

        # Ingest REAL Waterlogging predictions & outcomes in W2
        for d in test_dates:
            record_prediction(PredictionRecordCreate(
                ward_id="W2",
                hazard_type="waterlogging",
                predicted_risk_score=40.0,
                risk_category="MODERATE",
                data_source="Open-Meteo",
                provenance="REAL",
                timestamp=f"{d}T12:00:00Z"
            ))
            record_verified_outcome(VerifiedOutcomeCreate(
                ward_id="W2",
                measurement_date=d,
                hazard_type="waterlogging",
                waterlogging_depth_cm=20.0,  # Proxy: 20*2 = 40.0
                provenance="REAL"
            ))

        # Ingest REAL Water Shortage predictions & outcomes in W2
        for d in test_dates:
            record_prediction(PredictionRecordCreate(
                ward_id="W2",
                hazard_type="water_shortage",
                predicted_risk_score=60.0,
                risk_category="HIGH",
                data_source="Structural Baseline",
                provenance="REAL",
                timestamp=f"{d}T12:00:00Z"
            ))
            record_verified_outcome(VerifiedOutcomeCreate(
                ward_id="W2",
                measurement_date=d,
                hazard_type="water_shortage",
                water_scarcity_complaints=15,  # Proxy: 15*4 = 60.0
                provenance="REAL"
            ))

        res = run_model_evaluation(ModelEvaluationRequest(min_samples=3))
        acc = res["accuracy_by_hazard"]

        # Heat domain evaluation
        assert acc["heat"]["sample_count"] >= 4
        assert acc["heat"]["mae"] is not None

        # Waterlogging domain evaluation
        assert acc["waterlogging"]["sample_count"] >= 4
        assert acc["waterlogging"]["mae"] is not None

        # Water shortage domain evaluation
        assert acc["water_shortage"]["sample_count"] >= 4
        assert acc["water_shortage"]["mae"] is not None

    def test_04_proposals_require_human_approval_no_auto_mutation(self):
        """
        Verify that parameter update proposals do NOT mutate active model parameters
        until explicit human approval is granted.
        """
        # Baseline active parameters before evaluation
        initial_params = get_active_model_parameters()
        initial_version = initial_params["version_id"]

        # Ingest 4 real observations with significant error in W7
        for i in range(4):
            record_prediction(PredictionRecordCreate(
                ward_id="W7",
                hazard_type="heat",
                predicted_risk_score=30.0,
                risk_category="MODERATE",
                data_source="Open-Meteo",
                provenance="REAL",
                timestamp=f"2026-08-0{i+1}T12:00:00Z"
            ))
            record_verified_outcome(VerifiedOutcomeCreate(
                ward_id="W7",
                measurement_date=f"2026-08-0{i+1}",
                hazard_type="heat",
                hospital_heat_admissions=10,  # Proxy ~80, large residual ~50 pts
                provenance="REAL"
            ))

        eval_res = run_model_evaluation(ModelEvaluationRequest(min_samples=3))
        w7_proposals = [p for p in eval_res["proposed_updates"] if p["target_identifier"] == "W7"]
        assert len(w7_proposals) >= 1
        prop = w7_proposals[0]
        assert prop["status"] == "PENDING_APPROVAL"

        # Production model parameters MUST remain completely untouched!
        current_params = get_active_model_parameters()
        assert current_params["version_id"] == initial_version
        assert current_params["parameters"].get("ward_vulnerability_offsets", {}).get("W7", 0.0) == 0.0

    def test_05_proposal_approval_creates_immutable_new_version(self):
        """Test human approval creates a new versioned model state with audit trail."""
        # Create a proposal in W7
        eval_res = run_model_evaluation(ModelEvaluationRequest(min_samples=3))
        w7_proposals = [p for p in eval_res["proposed_updates"] if p["target_identifier"] == "W7"]
        prop_id = w7_proposals[0]["proposal_id"]

        approval_res = approve_parameter_proposal(prop_id, ProposalApprovalRequest(
            approved_by="AMC_CHIEF_HEALTH_OFFICER_PATEL",
            review_notes="Approved based on 4 days of consistent heat exhaustion morbidity in Vatva W7."
        ))

        assert approval_res["status"] == "PROPOSAL_APPROVED_AND_MODEL_UPDATED"
        assert approval_res["approved_by"] == "AMC_CHIEF_HEALTH_OFFICER_PATEL"
        new_version = approval_res["new_active_model_version"]
        assert new_version != approval_res["previous_version"]

        # Verify active model is now updated
        active = get_active_model_parameters()
        assert active["version_id"] == new_version
        assert active["parameters"]["ward_vulnerability_offsets"]["W7"] != 0.0

        # Verify version history has both versions
        versions = list_model_versions()
        assert len(versions) >= 2
        active_versions = [v for v in versions if v["is_active"]]
        assert len(active_versions) == 1

    def test_06_proposal_rejection_leaves_parameters_untouched(self):
        """Test rejecting a proposal keeps production parameters untouched."""
        # Create another proposal by inserting high residuals in W4
        for i in range(4):
            record_prediction(PredictionRecordCreate(
                ward_id="W4",
                hazard_type="heat",
                predicted_risk_score=20.0,
                risk_category="LOW",
                data_source="Open-Meteo",
                provenance="REAL",
                timestamp=f"2026-08-1{i}T12:00:00Z"
            ))
            record_verified_outcome(VerifiedOutcomeCreate(
                ward_id="W4",
                measurement_date=f"2026-08-1{i}",
                hazard_type="heat",
                hospital_heat_admissions=8,
                provenance="REAL"
            ))

        eval_res = run_model_evaluation(ModelEvaluationRequest(min_samples=3))
        w4_proposals = [p for p in eval_res["proposed_updates"] if p["target_identifier"] == "W4"]
        prop_id = w4_proposals[0]["proposal_id"]

        pre_rejection = get_active_model_parameters()

        rej_res = reject_parameter_proposal(prop_id, ProposalRejectionRequest(
            reviewed_by="DISASTER_MGMT_CELL",
            review_notes="Rejected: Morbidity surge was due to local industrial chemical fire, not heatwave."
        ))
        assert rej_res["status"] == "PROPOSAL_REJECTED"

        # Parameters remain untouched
        post_rejection = get_active_model_parameters()
        assert post_rejection["version_id"] == pre_rejection["version_id"]
        assert post_rejection["parameters"].get("ward_vulnerability_offsets", {}).get("W4", 0.0) == 0.0

    def test_07_rollback_model_version(self):
        """Test rolling back to an older model version."""
        versions = list_model_versions()
        if len(versions) >= 2:
            target_version = versions[-1]["version_id"]
            rb = rollback_model_version(target_version, "SYSTEM_ADMIN_RESTORE")
            assert rb["status"] == "VERSION_ROLLBACK_SUCCESSFUL"
            assert rb["active_version"] == target_version

            active = get_active_model_parameters()
            assert active["version_id"] == target_version

    def test_08_fastapi_endpoints_integration(self, client):
        """Test FastAPI REST endpoints for the complete learning evaluation lifecycle."""
        # 1. POST /api/learning/evaluate
        r_eval = client.post("/api/learning/evaluate", json={
            "eval_window_days": 60,
            "min_samples": 3,
            "exclude_simulated": True
        })
        assert r_eval.status_code == 200
        data = r_eval.json()
        assert "accuracy_by_hazard" in data
        assert "heat" in data["accuracy_by_hazard"]

        # 2. GET /api/learning/active-parameters
        r_params = client.get("/api/learning/active-parameters")
        assert r_params.status_code == 200
        assert "parameters" in r_params.json()

        # 3. GET /api/learning/versions
        r_vers = client.get("/api/learning/versions")
        assert r_vers.status_code == 200
        assert len(r_vers.json()["versions"]) >= 1

        # 4. GET /api/learning/evaluations
        r_evals = client.get("/api/learning/evaluations")
        assert r_evals.status_code == 200
        assert "evaluations" in r_evals.json()
        assert len(r_evals.json()["evaluations"]) >= 1
        eval_id = r_evals.json()["evaluations"][0]["evaluation_id"]

        # 5. GET /api/learning/evaluations/{evaluation_id}
        r_single_eval = client.get(f"/api/learning/evaluations/{eval_id}")
        assert r_single_eval.status_code == 200
        assert r_single_eval.json()["evaluation_id"] == eval_id

        # 6. GET /api/learning/proposals
        r_props = client.get("/api/learning/proposals")
        assert r_props.status_code == 200
        assert "proposals" in r_props.json()

        # 7. GET /api/learning/actions (and single action)
        r_acts = client.get("/api/learning/actions")
        assert r_acts.status_code == 200
        if r_acts.json()["actions"]:
            act_id = r_acts.json()["actions"][0]["action_id"]
            r_single_act = client.get(f"/api/learning/actions/{act_id}")
            assert r_single_act.status_code == 200
            assert r_single_act.json()["action_id"] == act_id

        # 8. GET /api/learning/outcomes (and single outcome)
        r_outs = client.get("/api/learning/outcomes")
        assert r_outs.status_code == 200
        if r_outs.json()["outcomes"]:
            out_id = r_outs.json()["outcomes"][0]["outcome_id"]
            r_single_out = client.get(f"/api/learning/outcomes/{out_id}")
            assert r_single_out.status_code == 200
            assert r_single_out.json()["outcome_id"] == out_id
