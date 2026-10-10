"""
Tests for Water Scarcity / Drought Advisory Workflow and System Health Diagnostics.
Validates:
1. Water scarcity advisory creation with required confirmation.
2. Enforcement of validation rules (missing confirmation, missing zones, missing recommendations).
3. Distinction between recommendations and physical dispatches (status 'proposed', is_executed=False).
4. Preservation of existing heat advisory workflow.
5. System health diagnostics reporting genuine database and dataset statuses.
"""

import unittest
from fastapi.testclient import TestClient
from backend.main import app
from backend.action_centre import get_action_store, ACTION_TYPES


class TestWaterScarcityAdvisory(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.store = get_action_store()

    def test_water_advisory_successful_creation(self):
        """Tests valid water scarcity advisory creation with confirmation."""
        payload = {
            "advisory_type": "water_scarcity",
            "severity_tier": "SEVERE",
            "target_zones": ["East Zone", "South Zone"],
            "target_wards": ["W7", "W1"],
            "recommendations": [
                "water_conservation_messaging",
                "water_tanker_dispatch",
                "leak_inspection_repair"
            ],
            "reason": "Secular drawdown and rising summer demand across informal industrial belts.",
            "confirmed_by": "Disaster Management Cell",
            "data_sources": [
                "Central Water Commission (CWC) Weekly Bulletin",
                "Central Ground Water Board (CGWB) In-Situ Telemetry"
            ],
            "observation_dates": {
                "cwc_bulletin": "2024-05-15",
                "cgwb_groundwater": "2024-05-15"
            },
            "confidence_level": "MODERATE",
            "confirmation_acknowledged": True
        }

        resp = self.client.post("/api/water/advisory", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["status"], "SUCCESS")
        self.assertTrue(data["advisory_id"].startswith("ADV-WTR-"))
        self.assertEqual(data["severity_tier"], "SEVERE")
        self.assertFalse(data["is_executed"], "Must never claim physical dispatches were executed")
        self.assertTrue(data["human_approval_required"])
        self.assertIn("DECISION SUPPORT ADVISORY", data["notice"])

        # Check action record stored in Action Centre
        action = data["action_record"]
        self.assertEqual(action["status"], "proposed")
        self.assertEqual(action["action_type"], "water_conservation_advisory")
        self.assertEqual(action["related_hazard"], "water_shortage")
        self.assertFalse(action["required_resources"]["is_physical_execution"])

    def test_water_advisory_missing_confirmation_fails(self):
        """Tests that submitting without confirmation acknowledgment is rejected (422)."""
        payload = {
            "advisory_type": "water_scarcity",
            "severity_tier": "CRITICAL",
            "target_zones": ["East Zone"],
            "recommendations": ["water_conservation_messaging"],
            "reason": "Test water scarcity reason",
            "confirmation_acknowledged": False  # Not confirmed
        }

        resp = self.client.post("/api/water/advisory", json=payload)
        self.assertEqual(resp.status_code, 422)
        self.assertIn("confirmation", resp.json()["detail"].lower())

    def test_water_advisory_missing_zones_fails(self):
        """Tests that submitting without target zones or wards is rejected (422)."""
        payload = {
            "advisory_type": "water_scarcity",
            "severity_tier": "MODERATE",
            "target_zones": [],
            "target_wards": [],
            "recommendations": ["water_conservation_messaging"],
            "reason": "Test water scarcity reason",
            "confirmation_acknowledged": True
        }

        resp = self.client.post("/api/water/advisory", json=payload)
        self.assertEqual(resp.status_code, 422)
        self.assertIn("zone or ward", resp.json()["detail"].lower())

    def test_water_advisory_missing_recommendations_fails(self):
        """Tests that submitting without recommendations is rejected (422)."""
        payload = {
            "advisory_type": "water_scarcity",
            "severity_tier": "MODERATE",
            "target_zones": ["East Zone"],
            "recommendations": [],
            "reason": "Test water scarcity reason",
            "confirmation_acknowledged": True
        }

        resp = self.client.post("/api/water/advisory", json=payload)
        self.assertEqual(resp.status_code, 422)
        self.assertIn("recommendation", resp.json()["detail"].lower())

    def test_heat_advisory_regression_intact(self):
        """Verifies that the existing Heat Action Plan manual action workflow remains functional."""
        payload = {
            "ward_id": "AMC-CENTRAL",
            "ward_name": "Ahmedabad Citywide (East Zone, South Zone)",
            "action_type": "heat_alert",
            "priority": "high",
            "reason": "Heat Action Plan (HAP) Tier Orange municipal advisory authorized.",
            "required_resources": {
                "cost_inr": 20000,
                "crew_required": 6,
                "water_required_l": 30000
            },
            "related_hazard": "heat",
            "risk_score": 75.0
        }

        resp = self.client.post("/api/action-centre/create", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["action"]["action_type"], "heat_alert")
        self.assertEqual(data["action"]["related_hazard"], "heat")
        self.assertEqual(data["action"]["status"], "proposed")

    def test_system_health_diagnostics(self):
        """Verifies genuine system health diagnostics endpoint."""
        resp = self.client.get("/api/system/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertIn(data["overall_status"], ["HEALTHY", "DEGRADED"])
        comps = data["components"]

        # 1. Database
        self.assertIn("database", comps)
        self.assertTrue(comps["database"]["is_accessible"])
        self.assertGreater(comps["database"]["records"]["wards"], 0)

        # 2. CGWB Groundwater
        self.assertIn("cgwb_groundwater", comps)
        gw = comps["cgwb_groundwater"]
        self.assertFalse(gw["is_live_telemetry"], "Must never report static historical dataset as live")
        self.assertIn("CGWB", gw["provenance"])
        self.assertGreater(gw["active_stations_count"], 0)
        self.assertIsNotNone(gw["latest_observation_date"])

        # 3. CWC Reservoirs
        self.assertIn("cwc_reservoirs", comps)
        cwc = comps["cwc_reservoirs"]
        self.assertFalse(cwc["is_live_telemetry"], "Must never report bulletin as live SCADA")
        self.assertIn("CWC", cwc["provenance"])
        self.assertIsNotNone(cwc["composite_storage_pct"])
        self.assertIsNotNone(cwc["latest_observation_date"])

        # 4. Water Shortage Engine
        self.assertIn("water_shortage_engine", comps)
        self.assertEqual(comps["water_shortage_engine"]["status"], "OPERATIONAL")


if __name__ == "__main__":
    unittest.main()
