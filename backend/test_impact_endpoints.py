"""
ClimateShield - Unit Tests for Impact Verification FastAPI Endpoints
Tests:
1. POST /api/impact/assessments (Submitting raw observations and pre-computed assessments)
2. Rejection of uncompleted recommendations (execution_status="RECOMMENDED") -> 422
3. Duplicate prevention -> 409 Conflict
4. Update with history preservation -> 201/200, version incremented
5. GET /api/impact/assessments/{assessment_id} (Retrieval, 404 for missing, audit history)
6. GET /api/impact/wards/{ward_id} (Ward-level querying, synthetic filtering)
7. GET /api/impact/summary (Segregation of empirical verified records vs synthetic demo)
8. Backward compatibility and catalog registration in GET /
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


class TestImpactVerificationEndpoints(unittest.TestCase):
    """Test suite for FastAPI Impact Verification endpoints."""

    def setUp(self):
        self.client = TestClient(app)
        # Clean test records before each test
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM impact_assessment_history WHERE assessment_id LIKE 'API_TEST_%';")
        cursor.execute("DELETE FROM impact_assessments WHERE assessment_id LIKE 'API_TEST_%';")
        conn.commit()
        conn.close()

    def tearDown(self):
        # Clean test records after each test
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM impact_assessment_history WHERE assessment_id LIKE 'API_TEST_%';")
        cursor.execute("DELETE FROM impact_assessments WHERE assessment_id LIKE 'API_TEST_%';")
        conn.commit()
        conn.close()

    def test_root_catalog_contains_impact_endpoints(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        endpoints = data.get("endpoints", [])
        self.assertIn("/api/impact/assessments", endpoints)
        self.assertIn("/api/impact/assessments/{assessment_id}", endpoints)
        self.assertIn("/api/impact/wards/{ward_id}", endpoints)
        self.assertIn("/api/impact/summary", endpoints)

    def test_submit_assessment_with_raw_observations_success(self):
        payload = {
            "assessment_id": "API_TEST_COOLING_01",
            "intervention_id": "cooling_center",
            "ward_id": "W1",
            "intervention_type": "PHYSICAL_REFUGE_AND_COOLING",
            "execution_status": "COMPLETED",
            "baseline_period": {"start": "2026-05-11", "end": "2026-05-12"},
            "follow_up_period": {"start": "2026-05-15", "end": "2026-05-16"},
            "observations": [
                {
                    "indicator": "ambient_temperature",
                    "value": 44.0,
                    "unit": "°C",
                    "timestamp": "2026-05-11T14:00:00Z",
                    "period": "BASELINE",
                    "ward_id": "W1",
                    "source_type": "MEASURED"
                },
                {
                    "indicator": "ambient_temperature",
                    "value": 40.5,
                    "unit": "°C",
                    "timestamp": "2026-05-15T14:00:00Z",
                    "period": "FOLLOW_UP",
                    "ward_id": "W1",
                    "source_type": "MEASURED"
                }
            ]
        }

        response = self.client.post("/api/impact/assessments", json=payload)
        self.assertEqual(response.status_code, 201)
        data = response.json()

        self.assertEqual(data["assessment_id"], "API_TEST_COOLING_01")
        self.assertEqual(data["ward_id"], "W1")
        self.assertEqual(data["intervention_id"], "cooling_center")
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["save_status"], "CREATED")
        self.assertIn("indicators", data)
        self.assertIn("ambient_temperature", data["indicators"])

        temp_res = data["indicators"]["ambient_temperature"]
        self.assertEqual(temp_res["difference"], -3.5)
        self.assertTrue(temp_res["is_improvement"])
        self.assertFalse(data["is_synthetic"])

    def test_submit_assessment_rejects_uncompleted_recommendation(self):
        # Attempting to verify an intervention that was merely recommended without deployment
        payload = {
            "assessment_id": "API_TEST_UNCOMPLETED",
            "intervention_id": "cooling_center",
            "ward_id": "W1",
            "intervention_type": "PHYSICAL_REFUGE_AND_COOLING",
            "execution_status": "RECOMMENDED",  # Merely recommended!
            "indicators": {
                "ambient_temperature": {"unit": "celsius", "difference": -2.0}
            }
        }
        response = self.client.post("/api/impact/assessments", json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertIn("UNCOMPLETED_INTERVENTION", response.json()["detail"])

        # Also test PENDING_HUMAN_APPROVAL
        payload["execution_status"] = "PENDING_HUMAN_APPROVAL"
        response = self.client.post("/api/impact/assessments", json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertIn("UNCOMPLETED_INTERVENTION", response.json()["detail"])

    def test_submit_assessment_missing_payload(self):
        # Missing both observations and indicators
        payload = {
            "assessment_id": "API_TEST_EMPTY",
            "intervention_id": "cooling_center",
            "ward_id": "W1",
            "intervention_type": "PHYSICAL_REFUGE_AND_COOLING",
            "execution_status": "COMPLETED"
        }
        response = self.client.post("/api/impact/assessments", json=payload)
        self.assertEqual(response.status_code, 422)
        self.assertIn("Missing assessment payload", response.json()["detail"])

    def test_duplicate_prevention_returns_409(self):
        payload = {
            "assessment_id": "API_TEST_DUP_01",
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
        # First save
        res1 = self.client.post("/api/impact/assessments", json=payload)
        self.assertEqual(res1.status_code, 201)

        # Conflicting second save with allow_update=False
        conflicting = dict(payload)
        conflicting["indicators"] = {
            "water_delivered": {
                "baseline_value": 1000.0,
                "follow_up_value": 9000.0,  # Changed!
                "unit": "liters",
                "difference": 8000.0
            }
        }
        res2 = self.client.post("/api/impact/assessments", json=conflicting)
        self.assertEqual(res2.status_code, 409)
        self.assertIn("already exists", res2.json()["detail"])

    def test_update_assessment_preserves_history(self):
        aid = "API_TEST_UPDATE_01"
        payload = {
            "assessment_id": aid,
            "intervention_id": "dewatering_pump",
            "ward_id": "W4",
            "intervention_type": "DEWATERING",
            "execution_status": "COMPLETED",
            "indicators": {
                "flood_water_depth": {
                    "baseline_value": 60.0,
                    "follow_up_value": 25.0,
                    "unit": "cm",
                    "difference": -35.0
                }
            }
        }
        # 1. Save version 1
        res1 = self.client.post("/api/impact/assessments", json=payload)
        self.assertEqual(res1.status_code, 201)
        self.assertEqual(res1.json()["version"], 1)

        # 2. Update with allow_update=True
        updated_payload = dict(payload)
        updated_payload["allow_update"] = True
        updated_payload["change_reason"] = "Recalibrated post-storm depth measurement"
        updated_payload["indicators"] = {
            "flood_water_depth": {
                "baseline_value": 60.0,
                "follow_up_value": 15.0,
                "unit": "cm",
                "difference": -45.0
            }
        }
        res2 = self.client.post("/api/impact/assessments", json=updated_payload)
        self.assertEqual(res2.status_code, 201)
        self.assertEqual(res2.json()["version"], 2)
        self.assertEqual(res2.json()["save_status"], "UPDATED_AND_ARCHIVED")

        # 3. Retrieve with include_history=true
        get_res = self.client.get(f"/api/impact/assessments/{aid}?include_history=true")
        self.assertEqual(get_res.status_code, 200)
        data = get_res.json()
        self.assertEqual(data["version"], 2)
        self.assertIn("audit_history", data)
        self.assertEqual(len(data["audit_history"]), 1)
        self.assertEqual(data["audit_history"][0]["version"], 1)
        self.assertEqual(data["audit_history"][0]["change_reason"], "Recalibrated post-storm depth measurement")

    def test_get_assessment_not_found(self):
        res = self.client.get("/api/impact/assessments/NONEXISTENT_ASSESSMENT_999")
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found", res.json()["detail"])

    def test_get_ward_impact_assessments(self):
        # Create assessment in W7
        payload = {
            "assessment_id": "API_TEST_W7_01",
            "intervention_id": "water_tanker_allocation",
            "ward_id": "W7",
            "intervention_type": "POTABLE_WATER_SUPPLY",
            "execution_status": "COMPLETED",
            "indicators": {
                "water_delivered": {
                    "baseline_value": 5000.0,
                    "follow_up_value": 15000.0,
                    "unit": "liters",
                    "difference": 10000.0
                }
            }
        }
        self.client.post("/api/impact/assessments", json=payload)

        # Query ward W7
        res = self.client.get("/api/impact/wards/W7")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["ward_id"], "W7")
        self.assertGreaterEqual(data["total_assessments"], 1)
        ids = [a["assessment_id"] for a in data["assessments"]]
        self.assertIn("API_TEST_W7_01", ids)

    def test_get_impact_summary_segregates_synthetic_demo(self):
        # 1. Insert empirical assessment
        emp_payload = {
            "assessment_id": "API_TEST_EMP_01",
            "intervention_id": "cooling_center",
            "ward_id": "W1",
            "intervention_type": "PHYSICAL_REFUGE_AND_COOLING",
            "execution_status": "COMPLETED",
            "is_synthetic": False,
            "provenance_mode": "MEASURED",
            "indicators": {
                "ambient_temperature": {
                    "baseline_value": 43.0,
                    "follow_up_value": 40.0,
                    "unit": "celsius",
                    "difference": -3.0,
                    "is_improvement": True,
                    "hazard_category": "heat"
                }
            }
        }
        self.client.post("/api/impact/assessments", json=emp_payload)

        # 2. Insert synthetic demo assessment
        syn_payload = {
            "assessment_id": "API_TEST_SYN_01",
            "intervention_id": "cooling_center",
            "ward_id": "W1",
            "intervention_type": "PHYSICAL_REFUGE_AND_COOLING",
            "execution_status": "SYNTHETIC_DEMO",
            "is_synthetic": True,
            "provenance_mode": "SYNTHETIC_DEMO",
            "indicators": {
                "ambient_temperature": {
                    "baseline_value": 45.0,
                    "follow_up_value": 41.0,
                    "unit": "celsius",
                    "difference": -4.0,
                    "is_improvement": True,
                    "hazard_category": "heat"
                }
            }
        }
        self.client.post("/api/impact/assessments", json=syn_payload)

        # 3. GET /api/impact/summary with default include_synthetic=false
        res_real = self.client.get("/api/impact/summary")
        self.assertEqual(res_real.status_code, 200)
        data_real = res_real.json()
        self.assertEqual(data_real["data_integrity_mode"], "REAL_WORLD_VERIFIED_ONLY")
        self.assertIn("Real-world verified outcomes are strictly segregated", data_real["data_integrity_notice"])
        self.assertGreaterEqual(data_real["empirical_verified_assessments_count"], 1)
        self.assertGreaterEqual(data_real["synthetic_demo_assessments_count"], 1)
        # Empirical summary must not include synthetic demo in summarized_assessments_count
        self.assertEqual(
            data_real["summarized_assessments_count"],
            data_real["empirical_verified_assessments_count"]
        )

        # 4. GET /api/impact/summary?include_synthetic=true
        res_all = self.client.get("/api/impact/summary?include_synthetic=true")
        self.assertEqual(res_all.status_code, 200)
        data_all = res_all.json()
        self.assertEqual(data_all["data_integrity_mode"], "INCLUDES_SIMULATED_DEMO")
        self.assertEqual(
            data_all["summarized_assessments_count"],
            data_all["empirical_verified_assessments_count"] + data_all["synthetic_demo_assessments_count"]
        )


if __name__ == "__main__":
    unittest.main()
