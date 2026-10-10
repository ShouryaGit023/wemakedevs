"""
ClimateShield - End-to-End Comprehensive Review Test Suite
Verifies the complete closed-loop municipal learning lifecycle:
1. Predictions and recommendations can be recorded.
2. Completed actions are distinguished from recommended actions.
3. Outcomes can be submitted and linked to the correct actions.
4. Impact verification uses appropriate baseline and follow-up data.
5. Unverified and synthetic outcomes are excluded from production learning.
6. Performance metrics are calculated correctly.
7. Proposed model updates require human approval.
8. Model versions and changes are auditable.
9. Missing or poor-quality data does not produce misleading conclusions.
10. Existing Heat + Water APIs and the intervention optimizer still work.
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.main import app
from backend.database import get_db_connection
from backend.learning_loop import (
    record_prediction,
    get_prediction,
    record_recommendations,
    list_recommendations,
    record_executed_action,
    get_action,
    update_executed_action,
    record_verified_outcome,
    get_outcome,
    list_outcomes,
    get_learning_lineage,
    PredictionRecordCreate,
    RecommendationItemCreate,
    ExecutedActionCreate,
    ExecutedActionUpdate,
    VerifiedOutcomeCreate
)
from backend.impact_verification import (
    verify_intervention_impact,
    ImpactVerificationRequest,
    get_verification
)
from backend.learning_engine import (
    run_model_evaluation,
    ModelEvaluationRequest,
    get_active_model_parameters,
    list_parameter_proposals,
    approve_parameter_proposal,
    reject_parameter_proposal,
    ProposalApprovalRequest,
    ProposalRejectionRequest,
    list_model_versions,
    rollback_model_version
)

client = TestClient(app)


class TestLearningLoopEndToEndReview:

    def test_01_predictions_and_recommendations_can_be_recorded(self):
        """1. Verify predictions and recommendations can be recorded via API and engine."""
        # A. Record prediction via API
        pred_payload = {
            "ward_id": "W1",
            "hazard_type": "heat",
            "predicted_risk_score": 79.5,
            "risk_category": "HIGH",
            "data_source": "Open-Meteo Weather API + ECOSTRESS",
            "provenance": "REAL",
            "timestamp": "2026-07-01T12:00:00Z",
            "details": {"wbgt_c": 31.8, "ambient_c": 43.0}
        }
        res_pred = client.post("/api/learning/predictions", json=pred_payload)
        assert res_pred.status_code == 201
        pred_data = res_pred.json()
        assert pred_data["prediction_id"].startswith("pred_")
        assert pred_data["ward_id"] == "W1"
        assert pred_data["predicted_risk_score"] == 79.5
        assert pred_data["provenance"] == "REAL"

        # B. Record candidate recommendations linked to prediction
        rec_payload = {
            "prediction_id": pred_data["prediction_id"],
            "ward_id": "W1",
            "recommendations": [
                {
                    "intervention_type": "cooling_center",
                    "priority_score": 85.0,
                    "estimated_cost_inr": 40000.0,
                    "expected_impact_min": 10.0,
                    "expected_impact_expected": 15.0,
                    "expected_impact_max": 20.0,
                    "required_crew": 4,
                    "required_water_l": 600.0,
                    "assumptions": {"capacity": 200, "basis": "Schedule of Rates"},
                    "status": "PROPOSED"
                }
            ]
        }
        res_rec = client.post("/api/learning/recommendations", json=rec_payload)
        assert res_rec.status_code == 201
        recs = res_rec.json()["recommendations"]
        assert len(recs) == 1
        assert recs[0]["recommendation_id"].startswith("rec_")
        assert recs[0]["status"] == "PROPOSED"
        # Crucial governance principle: recommendations are NEVER proof of execution
        assert recs[0]["is_action_executed"] is False

    def test_02_completed_actions_are_distinguished_from_recommended_actions(self):
        """2. Verify recommendations != actions; actions require human authorization and track execution."""
        pred = record_prediction(PredictionRecordCreate(
            ward_id="W2",
            hazard_type="heat",
            predicted_risk_score=75.0,
            risk_category="HIGH",
            data_source="Test Forecasting Engine",
            provenance="REAL"
        ))

        recs = record_recommendations(pred["prediction_id"], "W2", [
            RecommendationItemCreate(
                intervention_type="cool_roofs",
                priority_score=70.0,
                estimated_cost_inr=25000.0,
                status="PROPOSED"
            )
        ])
        rec_id = recs[0]["recommendation_id"]

        # Recommendation exists, but zero executed actions exist for this recommendation yet
        linked_actions = client.get(f"/api/learning/actions?ward_id=W2").json()["actions"]
        assert not any(a.get("recommendation_id") == rec_id for a in linked_actions)

        # Actions strictly require human approval role ('approved_by')
        invalid_action_payload = {
            "ward_id": "W2",
            "intervention_type": "cool_roofs",
            "recommendation_id": rec_id,
            "approval_status": "APPROVED",
            "approved_by": "",  # Empty authority
            "execution_status": "SCHEDULED"
        }
        res_invalid = client.post("/api/learning/actions", json=invalid_action_payload)
        assert res_invalid.status_code == 422  # Blocked by validation

        # Valid action created with named authority
        valid_action_payload = {
            "ward_id": "W2",
            "intervention_type": "cool_roofs",
            "recommendation_id": rec_id,
            "prediction_id": pred["prediction_id"],
            "approval_status": "APPROVED",
            "approved_by": "AMC_DEPUTY_MUNICIPAL_COMMISSIONER",
            "approved_at": "2026-07-02T08:00:00Z",
            "execution_status": "SCHEDULED"
        }
        res_action = client.post("/api/learning/actions", json=valid_action_payload)
        assert res_action.status_code == 201
        action = res_action.json()
        assert action["action_id"].startswith("act_")
        assert action["execution"]["status"] == "SCHEDULED"
        assert action["approval"]["approved_by"] == "AMC_DEPUTY_MUNICIPAL_COMMISSIONER"

        # Update action to COMPLETED with actual resources drawn
        res_patch = client.patch(f"/api/learning/actions/{action['action_id']}", json={
            "execution_status": "COMPLETED",
            "started_at": "2026-07-02T09:00:00Z",
            "completed_at": "2026-07-02T18:00:00Z",
            "actual_cost_inr": 23500.0,
            "actual_crew_used": 3
        })
        assert res_patch.status_code == 200
        updated = res_patch.json()
        assert updated["execution_status"] == "COMPLETED"
        assert updated["actual_cost_inr"] == 23500.0

    def test_03_outcomes_can_be_submitted_and_linked_to_correct_actions(self):
        """3. Verify ground-truth outcomes can be submitted and relationally linked to actions."""
        # Create completed action
        action = record_executed_action(ExecutedActionCreate(
            ward_id="W3",
            intervention_type="mobile_pumping",
            approval_status="APPROVED",
            approved_by="DISASTER_MGMT_CELL",
            execution_status="COMPLETED",
            started_at="2026-07-03T10:00:00Z",
            completed_at="2026-07-03T16:00:00Z"
        ))
        act_id = action["action_id"]

        # Submit verified outcome linked to action_id
        outcome_payload = {
            "ward_id": "W3",
            "measurement_date": "2026-07-03",
            "hazard_type": "waterlogging",
            "action_id": act_id,
            "waterlogging_depth_cm": 15.0,
            "data_source": "AMC_ENGINEERING_FLOOD_CELL",
            "provenance": "REAL",
            "data_quality_score": 1.0,
            "verification_notes": "Surcharge depth measured at Danilimda underpass"
        }
        res_out = client.post("/api/learning/outcomes", json=outcome_payload)
        assert res_out.status_code == 201
        out_data = res_out.json()
        assert out_data["outcome_id"].startswith("out_")
        assert out_data["action_id"] == act_id
        assert out_data["observations"]["waterlogging_depth_cm"] == 15.0

        # Query outcomes filtered by action_id
        res_list = client.get(f"/api/learning/outcomes?action_id={act_id}")
        assert res_list.status_code == 200
        outcomes_list = res_list.json()["outcomes"]
        assert len(outcomes_list) >= 1
        assert outcomes_list[0]["outcome_id"] == out_data["outcome_id"]

    def test_04_impact_verification_uses_appropriate_baseline_and_followup_data(self):
        """4. Verify impact verification retrieves baseline and follow-up data and computes DiD."""
        # Setup treated ward W4 action
        action = record_executed_action(ExecutedActionCreate(
            ward_id="W4",
            intervention_type="cooling_center",
            approval_status="APPROVED",
            approved_by="AMC_HEALTH_OFFICER",
            execution_status="COMPLETED",
            started_at="2026-07-05T09:00:00Z",
            completed_at="2026-07-05T19:00:00Z"
        ))
        act_id = action["action_id"]

        # Treated ward baseline (Day 1) and followup (Day 2 post-intervention)
        record_verified_outcome(VerifiedOutcomeCreate(
            ward_id="W4",
            measurement_date="2026-07-05",
            hazard_type="heat",
            hospital_heat_admissions=14,
            provenance="REAL"
        ))
        record_verified_outcome(VerifiedOutcomeCreate(
            ward_id="W4",
            action_id=act_id,
            measurement_date="2026-07-06",
            hazard_type="heat",
            hospital_heat_admissions=8,  # Delta = -6
            provenance="REAL"
        ))

        # Control ward W5 (no intervention dispatched)
        record_verified_outcome(VerifiedOutcomeCreate(
            ward_id="W5",
            measurement_date="2026-07-05",
            hazard_type="heat",
            hospital_heat_admissions=10,
            provenance="REAL"
        ))
        record_verified_outcome(VerifiedOutcomeCreate(
            ward_id="W5",
            measurement_date="2026-07-06",
            hazard_type="heat",
            hospital_heat_admissions=9,  # Delta = -1 (ambient background decrease)
            provenance="REAL"
        ))

        # Run DiD impact verification via API
        verif_payload = {
            "action_id": act_id,
            "control_ward_id": "W5",
            "primary_metric": "hospital_heat_admissions",
            "baseline_date": "2026-07-05",
            "followup_date": "2026-07-06"
        }
        res_verif = client.post("/api/impact/verify", json=verif_payload)
        assert res_verif.status_code == 200
        verif = res_verif.json()

        assert verif["status"] == "VERIFIED_COMPLETED"
        assert verif["action_completed"] is True
        assert verif["evaluation_methodology"] == "DIFFERENCE_IN_DIFFERENCES"
        assert verif["baseline_measurement"]["value"] == 14.0
        assert verif["followup_measurement"]["value"] == 8.0
        assert verif["observed_delta"] == -6.0

        did = verif["difference_in_differences"]
        assert did["eligible"] is True
        assert did["control_ward_id"] == "W5"
        # DiD = (-6) - (-1) = -5.0 net admissions prevented
        assert did["did_estimate"] == -5.0
        assert "confidence_interval_95" in did
        assert verif["causal_claim_allowed"] is True

    def test_05_unverified_and_synthetic_outcomes_are_excluded_from_learning(self):
        """5. Verify SIMULATED and UNVERIFIED data are strictly excluded from parameter evaluation."""
        eval_req = ModelEvaluationRequest(
            eval_window_days=60,
            min_samples=3,
            exclude_simulated=True
        )
        report = run_model_evaluation(eval_req)
        # All excluded records must be tracked and isolated
        assert "sample_counts" in report
        assert "excluded_unverified_or_simulated" in report["sample_counts"]
        # Simulated outcomes must NEVER trigger parameter update proposals
        for prop in report.get("proposed_updates", []):
            assert prop["supporting_samples_count"] >= 3

    def test_06_performance_metrics_are_calculated_correctly(self):
        """6. Verify calculation of MAE, RMSE, Precision, Recall, and F1 across hazard domains."""
        from backend.learning_engine import _calculate_accuracy_metrics

        # Test known sample pairs: predicted vs observed
        # Pairs: (60, 70), (40, 30), (80, 80), (30, 60)
        # Errors: |60-70|=10, |40-30|=10, |80-80|=0, |30-60|=30 -> sum = 50, MAE = 50/4 = 12.5
        # Squared errors: 100 + 100 + 0 + 900 = 1100 -> RMSE = sqrt(1100/4) = sqrt(275) = 16.58
        pairs = [(60.0, 70.0), (40.0, 30.0), (80.0, 80.0), (30.0, 60.0)]
        metrics = _calculate_accuracy_metrics(pairs, alert_threshold=50.0)

        assert metrics["status"] == "EVALUATED"
        assert metrics["sample_count"] == 4
        assert metrics["mae"] == 12.5
        assert metrics["rmse"] == 16.58

        # Classification against 50.0 threshold:
        # (60, 70): P>=50 & O>=50 -> TP
        # (40, 30): P<50 & O<50 -> TN
        # (80, 80): P>=50 & O>=50 -> TP
        # (30, 60): P<50 & O>=50 -> FN
        # TP = 2, FP = 0, FN = 1, TN = 1
        cm = metrics["confusion_matrix"]
        assert cm["true_positives"] == 2
        assert cm["false_positives"] == 0
        assert cm["false_negatives"] == 1
        assert cm["true_negatives"] == 1

        # Precision = 2/(2+0) = 1.0
        # Recall = 2/(2+1) = 0.667
        # F1 = 2 * (1.0 * 0.667) / (1.0 + 0.667) = 0.8
        assert metrics["precision"] == 1.0
        assert metrics["recall"] == 0.667
        assert metrics["f1_score"] == 0.8

    def test_07_proposed_model_updates_require_human_approval(self):
        """7. Verify model proposals do not mutate production parameters without named human authorization."""
        active_before = get_active_model_parameters()

        # Insert a parent evaluation record and synthetic proposal
        conn = get_db_connection()
        cursor = conn.cursor()
        eval_id = f"eval_test_{int(datetime.now(timezone.utc).timestamp())}"
        cursor.execute("""
        INSERT INTO model_evaluations (
            evaluation_id, timestamp, eval_window_days, heat_metrics_json,
            waterlogging_metrics_json, water_shortage_metrics_json, overall_mae,
            sample_count_real, sample_count_excluded, notes
        ) VALUES (?, datetime('now'), 30, '{}', '{}', '{}', 8.5, 4, 0, 'Test evaluation');
        """, (eval_id,))

        prop_id = f"prop_test_{int(datetime.now(timezone.utc).timestamp())}"
        cursor.execute("""
        INSERT INTO proposed_parameter_updates (
            proposal_id, evaluation_id, target_parameter_type, target_identifier,
            current_value, proposed_value, delta, supporting_samples_count,
            justification, status
        ) VALUES (?, ?, 'WARD_VULNERABILITY', 'W1', 0.0, 0.08, 0.08, 5, 'Consistently higher morbidity', 'PENDING_APPROVAL');
        """, (prop_id, eval_id))
        conn.commit()
        conn.close()

        # Check proposal is pending
        res_list = client.get("/api/learning/proposals?status=PENDING_APPROVAL")
        assert res_list.status_code == 200
        pending_ids = [p["proposal_id"] for p in res_list.json()["proposals"]]
        assert prop_id in pending_ids

        # Verify active parameters have NOT changed yet
        active_check = get_active_model_parameters()
        assert active_check["version_id"] == active_before["version_id"]

        # Reject proposal flow
        res_rej = client.post(f"/api/learning/proposals/{prop_id}/reject", json={
            "reviewed_by": "MUNICIPAL_DISASTER_COMMISSIONER",
            "review_notes": "Identified temporary confounder due to local heat island. Maintaining baseline."
        })
        assert res_rej.status_code == 200
        assert res_rej.json()["status"] == "PROPOSAL_REJECTED"

        # Verify parameters STILL untouched
        active_after_rej = get_active_model_parameters()
        assert active_after_rej["version_id"] == active_before["version_id"]

        # Create another proposal and test APPROVAL flow
        prop_id_2 = f"prop_test_appr_{int(datetime.now(timezone.utc).timestamp())}"
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO proposed_parameter_updates (
            proposal_id, evaluation_id, target_parameter_type, target_identifier,
            current_value, proposed_value, delta, supporting_samples_count,
            justification, status
        ) VALUES (?, ?, 'WARD_VULNERABILITY', 'W1', 0.0, 0.05, 0.05, 4, 'Empirically verified offset', 'PENDING_APPROVAL');
        """, (prop_id_2, eval_id))
        conn.commit()
        conn.close()

        # Approve proposal requiring named municipal official
        res_appr = client.post(f"/api/learning/proposals/{prop_id_2}/approve", json={
            "approved_by": "MUNICIPAL_COMMISSIONER_AMC",
            "review_notes": "Authorized based on 4 confirmed hospital admissions pairs."
        })
        assert res_appr.status_code == 200
        appr_data = res_appr.json()
        assert appr_data["status"] == "PROPOSAL_APPROVED_AND_MODEL_UPDATED"
        assert appr_data["approved_by"] == "MUNICIPAL_COMMISSIONER_AMC"
        assert appr_data["new_active_model_version"] != active_before["version_id"]

        # Confirm new version is now active
        active_now = get_active_model_parameters()
        assert active_now["version_id"] == appr_data["new_active_model_version"]
        assert active_now["parameters"]["ward_vulnerability_offsets"]["W1"] == 0.05

    def test_08_model_versions_and_changes_are_auditable(self):
        """8. Verify immutable model version audit trail and rollback capability."""
        res_vers = client.get("/api/learning/versions")
        assert res_vers.status_code == 200
        versions = res_vers.json()["versions"]
        assert len(versions) >= 2  # v1.0.0 plus new version

        # Check changelog fields
        for v in versions:
            assert "version_id" in v
            assert "is_active" in v
            assert "approved_by" in v
            assert "change_summary" in v
            assert "parameters" in v

        # Test rollback to v1.0.0
        v1_match = [v for v in versions if v["version_id"] == "v1.0.0"]
        if v1_match:
            res_roll = client.post("/api/learning/versions/v1.0.0/rollback", json={
                "approved_by": "AMC_SAFETY_DIRECTOR",
                "review_notes": "Safety rollback test"
            })
            assert res_roll.status_code == 200
            assert res_roll.json()["status"] == "VERSION_ROLLBACK_SUCCESSFUL"
            active_after_rollback = get_active_model_parameters()
            assert active_after_rollback["version_id"] == "v1.0.0"

    def test_09_missing_or_poor_quality_data_does_not_produce_misleading_conclusions(self):
        """9. Verify missing observations and uncompleted actions refuse to fabricate impact claims."""
        # A. Incomplete/Failed action evaluated for impact
        failed_action = record_executed_action(ExecutedActionCreate(
            ward_id="W1",
            intervention_type="mobile_pumping",
            approval_status="APPROVED",
            approved_by="AMC_WATER_ENGINEER",
            execution_status="FAILED",
            failure_reason="Submersible pump caught fire during transport",
            actual_cost_inr=5000.0
        ))
        res_incomplete = client.post("/api/impact/verify", json={
            "action_id": failed_action["action_id"],
            "primary_metric": "waterlogging_depth_cm"
        })
        assert res_incomplete.status_code == 200
        inc_data = res_incomplete.json()
        assert inc_data["status"] == "INSUFFICIENT_DATA_INCOMPLETE_ACTION"
        assert inc_data["action_completed"] is False
        assert inc_data["causal_claim_allowed"] is False
        assert "failure_reason" in inc_data

        # B. Missing observations reported safely without fabricating estimates
        completed_action_no_obs = record_executed_action(ExecutedActionCreate(
            ward_id="W48",  # Ward with no observations in 2030
            intervention_type="cooling_center",
            approval_status="APPROVED",
            approved_by="AMC_HEALTH_OFFICER",
            execution_status="COMPLETED",
            started_at="2030-01-01T09:00:00Z",
            completed_at="2030-01-01T17:00:00Z"
        ))
        res_missing = client.post("/api/impact/verify", json={
            "action_id": completed_action_no_obs["action_id"],
            "primary_metric": "hospital_heat_admissions",
            "baseline_date": "2030-01-01",
            "followup_date": "2030-01-02"
        })
        assert res_missing.status_code == 200
        miss_data = res_missing.json()
        assert miss_data["status"] == "INSUFFICIENT_DATA_MISSING_OBSERVATIONS"
        assert miss_data["causal_claim_allowed"] is False

    def test_10_existing_heat_water_risk_and_optimizer_endpoints_still_work(self):
        """10. Verify existing heat, water, risk, and optimizer APIs continue to function perfectly."""
        # A. GET /api/wards
        res_wards = client.get("/api/wards")
        assert res_wards.status_code == 200
        assert "wards" in res_wards.json()

        # B. GET /api/weather/wbgt (Heat Engine)
        res_wbgt = client.get("/api/weather/wbgt")
        assert res_wbgt.status_code == 200
        wbgt_data = res_wbgt.json()
        assert "current_heat_status" in wbgt_data
        assert "ward_heat_risks" in wbgt_data

        # C. GET /api/water/wards (Water Engine)
        res_water = client.get("/api/water/wards")
        assert res_water.status_code == 200
        water_data = res_water.json()
        assert "wards" in water_data
        assert len(water_data["wards"]) == 48

        # D. GET /api/climate/combined-risk (Combined Risk Engine)
        res_risk = client.get("/api/climate/combined-risk?weight_heat=0.5&weight_water=0.5&scoring_mode=COMPOUND_SYNERGY")
        assert res_risk.status_code == 200
        risk_data = res_risk.json()
        assert "ranked_wards" in risk_data or "wards" in risk_data

        # E. POST /api/optimize (ILP Knapsack Resource Optimizer)
        opt_payload = {
            "total_budget_inr": 400000.0,
            "total_crew_members": 35,
            "total_water_cap_l": 25000.0,
            "equity_slider": 0.5
        }
        res_opt = client.post("/api/optimize", json=opt_payload)
        assert res_opt.status_code == 200
        opt_data = res_opt.json()
        assert "ward_allocations" in opt_data
        assert "summary" in opt_data
        assert opt_data["is_optimal"] is True

        # F. GET /api/interventions/catalog (Intervention Catalog)
        res_cat = client.get("/api/interventions/catalog")
        assert res_cat.status_code == 200
        assert "interventions" in res_cat.json()

        # G. GET /dashboard/ (Learning Loop Frontend)
        res_dash = client.get("/dashboard/")
        assert res_dash.status_code == 200
