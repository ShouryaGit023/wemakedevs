"""
ClimateShield - Automated Test Suite for Learning Loop Foundation
Tests:
1. Prediction record creation, validation, and historical persistence.
2. Candidate recommendation recording with assumptions and impact bounds.
3. Strict separation of recommendations from executed field actions.
4. Human approval authorization and action dispatch tracking.
5. Action execution state transitions, failure reasons, and actual resource draws.
6. Verified municipal outcomes ingestion and aggregated non-PII privacy guardrails.
7. Explicit data provenance (REAL, ESTIMATED, SIMULATED, UNVERIFIED).
8. End-to-end decision lineage reconstruction across stable IDs.
9. FastAPI REST endpoints for predictions, recommendations, actions, outcomes, and lineage.
10. Edge cases: missing data, invalid timestamps, PII rejection, and malformed inputs.
"""

import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.main import app
from backend.learning_loop import (
    record_prediction,
    get_prediction,
    list_predictions,
    record_recommendations,
    list_recommendations,
    record_executed_action,
    update_executed_action,
    get_action,
    list_actions,
    record_verified_outcome,
    get_outcome,
    list_outcomes,
    get_learning_lineage,
    PredictionRecordCreate,
    RecommendationItemCreate,
    ExecutedActionCreate,
    ExecutedActionUpdate,
    VerifiedOutcomeCreate,
    sanitize_text_non_pii
)


@pytest.fixture
def client():
    return TestClient(app)


class TestLearningLoopFoundation:

    def test_01_prediction_creation_and_persistence(self):
        """Test recording a risk prediction with stable ID, bounds, and provenance."""
        pred_data = PredictionRecordCreate(
            ward_id="W1",
            hazard_type="heat",
            predicted_risk_score=78.5,
            risk_category="HIGH",
            data_source="Open-Meteo Weather API",
            provenance="REAL",
            timestamp="2026-05-18T14:00:00Z",
            details={"ambient_temp_c": 43.5, "wbgt_c": 31.2}
        )
        rec = record_prediction(pred_data)

        assert rec["prediction_id"].startswith("pred_")
        assert rec["ward_id"] == "W1"
        assert rec["predicted_risk_score"] == 78.5
        assert rec["risk_category"] == "HIGH"
        assert rec["provenance"] == "REAL"
        assert rec["is_real_observation"] is True
        assert rec["details"]["wbgt_c"] == 31.2

        # Verify retrieval by ID
        fetched = get_prediction(rec["prediction_id"])
        assert fetched is not None
        assert fetched["prediction_id"] == rec["prediction_id"]
        assert fetched["details"]["ambient_temp_c"] == 43.5

    def test_02_recommendations_linked_to_prediction(self):
        """Test recording candidate recommendations tied to a prediction ID."""
        pred = record_prediction(PredictionRecordCreate(
            ward_id="W2",
            hazard_type="compound",
            predicted_risk_score=85.0,
            risk_category="CRITICAL",
            data_source="ERA5-Land + Open-Meteo",
            provenance="ESTIMATED"
        ))

        recs_input = [
            RecommendationItemCreate(
                intervention_type="cooling_center",
                priority_score=88.5,
                estimated_cost_inr=50000.0,
                expected_impact_min=8.0,
                expected_impact_expected=14.0,
                expected_impact_max=18.0,
                required_crew=4,
                required_water_l=500.0,
                assumptions={"basis": "Municipal Schedule of Rates 2024", "capacity": "250 persons"}
            ),
            RecommendationItemCreate(
                intervention_type="drainage_inspection_clean",
                priority_score=82.0,
                estimated_cost_inr=20000.0,
                expected_impact_min=5.0,
                expected_impact_expected=10.0,
                expected_impact_max=15.0,
                required_crew=3,
                required_water_l=0.0,
                assumptions={"basis": "Emergency culvert clearance"}
            )
        ]

        created_recs = record_recommendations(pred["prediction_id"], "W2", recs_input)
        assert len(created_recs) == 2
        for r in created_recs:
            assert r["prediction_id"] == pred["prediction_id"]
            assert r["status"] == "PROPOSED"
            assert r["is_action_executed"] is False  # Never treated as proof of execution

        # List recommendations
        query_recs = list_recommendations(prediction_id=pred["prediction_id"])
        assert len(query_recs) == 2
        types = [r["intervention_type"] for r in query_recs]
        assert "cooling_center" in types
        assert "drainage_inspection_clean" in types

    def test_03_recommendation_does_not_create_executed_action(self):
        """Ensure recommending an intervention does NOT automatically create an action."""
        pred = record_prediction(PredictionRecordCreate(
            ward_id="W3",
            hazard_type="heat",
            predicted_risk_score=60.0,
            risk_category="HIGH",
            data_source="Open-Meteo",
            provenance="REAL"
        ))

        record_recommendations(pred["prediction_id"], "W3", [
            RecommendationItemCreate(
                intervention_type="hydration_kiosk",
                priority_score=65.0,
                estimated_cost_inr=15000.0
            )
        ])

        # Verify that no action was created for W3
        actions = list_actions(ward_id="W3")
        linked_actions = [a for a in actions if a.get("prediction_id") == pred["prediction_id"]]
        assert len(linked_actions) == 0

    def test_04_action_creation_requires_human_approval(self):
        """Test recording an executed field action with explicit municipal approval."""
        pred = record_prediction(PredictionRecordCreate(
            ward_id="W4",
            hazard_type="heat",
            predicted_risk_score=72.0,
            risk_category="HIGH",
            data_source="Open-Meteo",
            provenance="REAL"
        ))

        recs = record_recommendations(pred["prediction_id"], "W4", [
            RecommendationItemCreate(
                intervention_type="cooling_center",
                estimated_cost_inr=50000.0
            )
        ])
        rec_id = recs[0]["recommendation_id"]

        action_data = ExecutedActionCreate(
            ward_id="W4",
            intervention_type="cooling_center",
            recommendation_id=rec_id,
            prediction_id=pred["prediction_id"],
            approval_status="APPROVED",
            approved_by="AMC_HEALTH_OFFICER_DANAPITH",
            approved_at="2026-05-18T10:00:00Z",
            execution_status="IN_PROGRESS",
            started_at="2026-05-18T11:30:00Z",
            actual_crew_used=4,
            actual_cost_inr=48000.0,
            notes="Shelter opened at Bapunagar Community Hall"
        )

        act = record_executed_action(action_data)
        assert act["action_id"].startswith("act_")
        assert act["approval"]["status"] == "APPROVED"
        assert act["approval"]["approved_by"] == "AMC_HEALTH_OFFICER_DANAPITH"
        assert act["execution"]["status"] == "IN_PROGRESS"
        assert act["execution"]["actual_crew_used"] == 4

        # Recommendation should now be updated to APPROVED
        updated_recs = list_recommendations(prediction_id=pred["prediction_id"])
        assert updated_recs[0]["status"] == "APPROVED"

    def test_05_failed_action_requires_documented_reason(self):
        """Test that failed or canceled actions require failure reasons and track resources."""
        # Must fail validation if reason omitted
        with pytest.raises(ValueError, match="failure_reason is required"):
            ExecutedActionCreate(
                ward_id="W5",
                intervention_type="mobile_pumping",
                approval_status="APPROVED",
                approved_by="DISASTER_MGMT_CELL",
                execution_status="FAILED",
                failure_reason=None
            )

        # Valid failed action recording
        failed_action = record_executed_action(ExecutedActionCreate(
            ward_id="W5",
            intervention_type="mobile_pumping",
            approval_status="APPROVED",
            approved_by="DISASTER_MGMT_CELL",
            execution_status="FAILED",
            failure_reason="Pump engine mechanical failure en route due to high water level",
            actual_crew_used=2,
            actual_cost_inr=5000.0,
            notes="Crew redirected back to depot"
        ))
        assert failed_action["execution"]["status"] == "FAILED"
        assert "mechanical failure" in failed_action["execution"]["failure_reason"]
        assert failed_action["execution"]["actual_cost_inr"] == 5000.0

    def test_06_action_status_patch_update(self):
        """Test updating an action from SCHEDULED to COMPLETED."""
        action = record_executed_action(ExecutedActionCreate(
            ward_id="W6",
            intervention_type="hydration_kiosk",
            approval_status="APPROVED",
            approved_by="AMC_WARD_SUPERVISOR",
            execution_status="SCHEDULED"
        ))
        act_id = action["action_id"]

        updated = update_executed_action(act_id, ExecutedActionUpdate(
            execution_status="COMPLETED",
            started_at="2026-05-19T08:00:00Z",
            completed_at="2026-05-19T18:00:00Z",
            actual_crew_used=2,
            actual_water_used_l=1200.0,
            actual_cost_inr=14500.0,
            notes="Distributed 850 ORS sachets along Amraiwadi BRTS corridor"
        ))
        assert updated["execution_status"] == "COMPLETED"
        assert updated["actual_water_used_l"] == 1200.0
        assert updated["completed_at"] is not None

    def test_07_verified_outcomes_recording_and_provenance(self):
        """Test recording verified outcomes with REAL vs SIMULATED tags."""
        pred = record_prediction(PredictionRecordCreate(
            ward_id="W7",
            hazard_type="heat",
            predicted_risk_score=80.0,
            risk_category="CRITICAL",
            data_source="Open-Meteo",
            provenance="REAL"
        ))

        # 1. Real ground-truth outcome
        real_outcome = record_verified_outcome(VerifiedOutcomeCreate(
            ward_id="W7",
            prediction_id=pred["prediction_id"],
            measurement_date="2026-05-19",
            measurement_window_hours=24,
            hazard_type="heat",
            hospital_heat_admissions=8,
            mortality_count=1,
            emergency_108_calls=12,
            water_scarcity_complaints=5,
            data_source="AMC_HEALTH_SURVEILLANCE",
            provenance="REAL",
            data_quality_score=0.95
        ))
        assert real_outcome["outcome_id"].startswith("out_")
        assert real_outcome["provenance"] == "REAL"
        assert real_outcome["is_real_observation"] is True
        assert real_outcome["observations"]["hospital_heat_admissions"] == 8

        # 2. Simulated demonstration outcome
        sim_outcome = record_verified_outcome(VerifiedOutcomeCreate(
            ward_id="W7",
            measurement_date="2026-05-19",
            hazard_type="waterlogging",
            waterlogging_depth_cm=45.0,
            data_source="SWMM_HYDROLOGY_SIMULATOR",
            provenance="SIMULATED",
            verification_notes="Synthetic scenario validation run"
        ))
        assert sim_outcome["provenance"] == "SIMULATED"
        assert sim_outcome["is_real_observation"] is False  # Never treated as real observation

    def test_08_privacy_pii_blocking_guardrail(self):
        """Test that free-text inputs containing phone numbers, emails, or IDs are strictly rejected."""
        with pytest.raises(ValueError, match="Privacy violation: Text contains a potential phone number"):
            sanitize_text_non_pii("Call patient relative at +91 9876543210 for follow up")

        with pytest.raises(ValueError, match="Privacy violation: Text contains an email address"):
            sanitize_text_non_pii("Send hospital report to dr.patel@hospital.com")

        with pytest.raises(ValueError, match="Privacy violation: Text contains an identification number"):
            sanitize_text_non_pii("Verified Aadhaar 2345 6789 0123")

        # Clean text passes without error
        clean = sanitize_text_non_pii("Ward health centre operational with 50 emergency beds.")
        assert clean == "Ward health centre operational with 50 emergency beds."

    def test_09_end_to_end_learning_lineage_linking(self):
        """Test full lineage chain: Prediction -> Recommendations -> Action -> Outcome."""
        # 1. Prediction
        pred = record_prediction(PredictionRecordCreate(
            ward_id="W1",
            hazard_type="compound",
            predicted_risk_score=91.0,
            risk_category="CRITICAL",
            data_source="Open-Meteo + Reanalysis",
            provenance="REAL",
            timestamp="2026-05-20T06:00:00Z"
        ))
        p_id = pred["prediction_id"]

        # 2. Recommendations
        recs = record_recommendations(p_id, "W1", [
            RecommendationItemCreate(
                intervention_type="cooling_center",
                estimated_cost_inr=50000.0,
                expected_impact_expected=15.0
            ),
            RecommendationItemCreate(
                intervention_type="water_tanker_dispatch",
                estimated_cost_inr=10000.0,
                expected_impact_expected=10.0
            )
        ])
        rec_cooling = recs[0]["recommendation_id"]

        # 3. Executed Action
        action = record_executed_action(ExecutedActionCreate(
            ward_id="W1",
            intervention_type="cooling_center",
            recommendation_id=rec_cooling,
            prediction_id=p_id,
            approval_status="APPROVED",
            approved_by="AMC_INCIDENT_COMMANDER",
            execution_status="COMPLETED",
            actual_cost_inr=49500.0,
            actual_crew_used=4
        ))
        a_id = action["action_id"]

        # 4. Verified Outcome
        outcome = record_verified_outcome(VerifiedOutcomeCreate(
            ward_id="W1",
            prediction_id=p_id,
            action_id=a_id,
            measurement_date="2026-05-20",
            hazard_type="heat",
            hospital_heat_admissions=5,
            emergency_108_calls=9,
            data_source="AMC_HEALTH_SURVEILLANCE",
            provenance="REAL"
        ))

        # 5. Lineage Query
        lineage = get_learning_lineage(p_id)
        assert lineage["prediction_id"] == p_id
        assert lineage["ward_id"] == "W1"
        assert lineage["recommendations_count"] == 2
        assert lineage["actions_count"] == 1
        assert lineage["outcomes_count"] == 1
        assert lineage["has_completed_action"] is True
        assert lineage["has_verified_real_outcome"] is True

        # Verify linked IDs
        assert lineage["executed_actions"][0]["action_id"] == a_id
        assert lineage["verified_outcomes"][0]["outcome_id"] == outcome["outcome_id"]

    def test_10_fastapi_endpoints_integration(self, client):
        """Test FastAPI REST endpoints for the complete Learning Loop."""
        # 1. POST /api/learning/predictions
        r_pred = client.post("/api/learning/predictions", json={
            "ward_id": "W8",
            "hazard_type": "heat",
            "predicted_risk_score": 55.0,
            "risk_category": "MODERATE",
            "data_source": "Open-Meteo",
            "provenance": "REAL"
        })
        assert r_pred.status_code == 201
        pred_id = r_pred.json()["prediction_id"]

        # 2. GET /api/learning/predictions
        r_list_pred = client.get(f"/api/learning/predictions?ward_id=W8")
        assert r_list_pred.status_code == 200
        assert len(r_list_pred.json()["predictions"]) >= 1

        # 3. POST /api/learning/recommendations
        r_recs = client.post("/api/learning/recommendations", json={
            "prediction_id": pred_id,
            "ward_id": "W8",
            "recommendations": [
                {
                    "intervention_type": "shade_canopy",
                    "priority_score": 62.0,
                    "estimated_cost_inr": 25000.0,
                    "expected_impact_expected": 8.0
                }
            ]
        })
        assert r_recs.status_code == 201
        rec_id = r_recs.json()["recommendations"][0]["recommendation_id"]

        # 4. POST /api/learning/actions
        r_act = client.post("/api/learning/actions", json={
            "ward_id": "W8",
            "intervention_type": "shade_canopy",
            "recommendation_id": rec_id,
            "prediction_id": pred_id,
            "approval_status": "APPROVED",
            "approved_by": "AMC_TRANSIT_CELL",
            "execution_status": "SCHEDULED"
        })
        assert r_act.status_code == 201
        act_id = r_act.json()["action_id"]

        # 5. PATCH /api/learning/actions/{id}
        r_patch = client.patch(f"/api/learning/actions/{act_id}", json={
            "execution_status": "COMPLETED",
            "actual_cost_inr": 24000.0,
            "actual_crew_used": 3
        })
        assert r_patch.status_code == 200
        assert r_patch.json()["execution_status"] == "COMPLETED"

        # 6. POST /api/learning/outcomes
        r_out = client.post("/api/learning/outcomes", json={
            "ward_id": "W8",
            "prediction_id": pred_id,
            "action_id": act_id,
            "measurement_date": "2026-05-21",
            "hospital_heat_admissions": 1,
            "mortality_count": 0,
            "emergency_108_calls": 2,
            "data_source": "AMC_HEALTH_SURVEILLANCE",
            "provenance": "REAL"
        })
        assert r_out.status_code == 201

        # 7. GET /api/learning/lineage/{prediction_id}
        r_lin = client.get(f"/api/learning/lineage/{pred_id}")
        assert r_lin.status_code == 200
        data = r_lin.json()
        assert data["prediction_id"] == pred_id
        assert data["actions_count"] == 1
        assert data["outcomes_count"] == 1

    def test_11_validation_and_error_handling(self, client):
        """Test HTTP 422 and 404 error handling on invalid learning loop inputs."""
        # Invalid risk score > 100
        r_bad_score = client.post("/api/learning/predictions", json={
            "ward_id": "W1",
            "hazard_type": "heat",
            "predicted_risk_score": 150.0,  # Invalid
            "risk_category": "CRITICAL",
            "data_source": "Open-Meteo"
        })
        assert r_bad_score.status_code == 422

        # Non-existent prediction ID in recommendations
        r_bad_pred = client.post("/api/learning/recommendations", json={
            "prediction_id": "non_existent_pred_id",
            "ward_id": "W1",
            "recommendations": [{"intervention_type": "cooling_center"}]
        })
        assert r_bad_pred.status_code == 404

        # Non-existent lineage query
        r_404_lin = client.get("/api/learning/lineage/non_existent_pred_123")
        assert r_404_lin.status_code == 404

        # PII rejection in outcome notes
        r_pii = client.post("/api/learning/outcomes", json={
            "ward_id": "W1",
            "measurement_date": "2026-05-21",
            "verification_notes": "Call nurse at 9876543210 for record"
        })
        assert r_pii.status_code == 422
