"""
Tests for Action Centre Evidence Verification Engine and Checklist
===================================================================
Uses Python built-in unittest framework.
Validates:
1. Checklist generation with clear states (VERIFIED, FAILED, NOT_VERIFIED, UNABLE_TO_VERIFY)
2. Mandatory check failure prevention (preventing failed checks from succeeding)
3. No fabrication of empirical evidence
4. Relational persistence to SQLite database
5. Real data validation (AMC ward registry, resource constraints, risk bounds)
"""

import unittest
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.action_centre import (
    ActionStore,
    verify_intervention_evidence,
    get_action_verification_report,
    get_default_verification_checklist,
    _is_valid_amc_ward,
)
from backend.database import get_action_verification


class TestActionEvidenceVerification(unittest.TestCase):

    def test_is_valid_amc_ward(self):
        # Valid known wards
        valid_w1, name_w1 = _is_valid_amc_ward("W1", "Danilimda")
        self.assertTrue(valid_w1)
        self.assertTrue("Danilimda" in name_w1 or "W1" in name_w1)

        valid_central, _ = _is_valid_amc_ward("AMC-CENTRAL", "Ahmedabad Citywide")
        self.assertTrue(valid_central)

        # Invalid ward
        invalid_res, _ = _is_valid_amc_ward("INVALID-WARD-999", "Atlantis")
        self.assertFalse(invalid_res)

        # Empty ward
        empty_res, _ = _is_valid_amc_ward("", "")
        self.assertFalse(empty_res)

    def test_default_verification_checklist(self):
        action = {
            "action_id": "ACT-TEST-01",
            "ward_id": "W1",
            "ward_name": "Danilimda",
            "action_type": "cooling_centre",
            "risk_score": 85.0,
            "required_resources": {"cost_inr": 50000, "crew_required": 4, "water_required_l": 500},
        }
        template = get_default_verification_checklist(action)
        self.assertEqual(template["overall_status"], "NOT_VERIFIED")
        self.assertEqual(len(template["checklist"]), 5)
        for item in template["checklist"]:
            self.assertEqual(item["status"], "NOT_VERIFIED")
            self.assertIn("pending", item["message"].lower())

    def test_verify_valid_intervention(self):
        store = ActionStore()
        now_iso = datetime.now(timezone.utc).isoformat()
        action = store.create_action(
            ward_id="W1",
            ward_name="Danilimda",
            action_type="cooling_centre",
            priority="high",
            reason="Activate Danilimda Community Hall shelter.",
            required_resources={"cost_inr": 50000, "crew_required": 4, "water_required_l": 500},
            risk_score=85.0,
        )

        climate_risk_data = {
            "timestamp": now_iso,
            "ranked_wards": [
                {
                    "id": "W1",
                    "name": "Danilimda",
                    "combined_risk_score": 88.0,
                    "combined_risk_category": "CRITICAL",
                }
            ]
        }

        result = verify_intervention_evidence(
            action=action,
            climate_risk_data=climate_risk_data,
            verified_by="Chief Medical Officer",
            notes="Pre-dispatch verification passed.",
            store=store,
        )

        self.assertEqual(result["overall_status"], "VERIFIED")
        self.assertEqual(result["verified_by"], "Chief Medical Officer")
        self.assertEqual(result["failed_checks_count"], 0)

        # Verify individual checklist statuses
        checks = {c["check_id"]: c for c in result["checklist"]}
        self.assertEqual(checks["ward_association"]["status"], "VERIFIED")
        self.assertEqual(checks["risk_assessment"]["status"], "VERIFIED")
        self.assertEqual(checks["data_freshness"]["status"], "VERIFIED")
        self.assertEqual(checks["operational_details"]["status"], "VERIFIED")

        # Evidence check is UNABLE_TO_VERIFY because no physical sensor is attached (no fabrication!)
        self.assertEqual(checks["available_evidence"]["status"], "UNABLE_TO_VERIFY")
        self.assertIn("post-execution", checks["available_evidence"]["reason"].lower())

        # Verify persistence to SQLite
        persisted = get_action_verification(action["action_id"])
        self.assertIsNotNone(persisted)
        self.assertEqual(persisted["overall_status"], "VERIFIED")
        self.assertEqual(persisted["verified_by"], "Chief Medical Officer")

    def test_mandatory_failure_prevents_overall_success(self):
        store = ActionStore()
        # Invalid ward and negative budget
        action = store.create_action(
            ward_id="NON_EXISTENT_WARD_99",
            ward_name="Unknown Zone",
            action_type="water_tanker_dispatch",
            priority="critical",
            reason="Dispatch water tankers.",
            required_resources={"cost_inr": -10000, "crew_required": 2, "water_required_l": 5000},
            risk_score=75.0,
        )

        result = verify_intervention_evidence(
            action=action,
            verified_by="Inspector",
            store=store,
        )

        # Mandatory checks failed -> Overall status MUST be FAILED
        self.assertEqual(result["overall_status"], "FAILED")
        self.assertGreaterEqual(result["failed_checks_count"], 2)

        checks = {c["check_id"]: c for c in result["checklist"]}
        self.assertEqual(checks["ward_association"]["status"], "FAILED")
        self.assertEqual(checks["operational_details"]["status"], "FAILED")
        self.assertIn("negative", checks["operational_details"]["reason"].lower())

    def test_missing_risk_score_fails_mandatory(self):
        store = ActionStore()
        action = store.create_action(
            ward_id="W1",
            ward_name="Danilimda",
            action_type="drinking_water_point",
            priority="medium",
            reason="Deploy drinking water.",
            required_resources={"cost_inr": 20000, "crew_required": 2, "water_required_l": 1000},
            risk_score=None,  # Missing risk score
        )

        result = verify_intervention_evidence(
            action=action,
            verified_by="Inspector",
            store=store,
        )

        self.assertEqual(result["overall_status"], "FAILED")
        checks = {c["check_id"]: c for c in result["checklist"]}
        self.assertEqual(checks["risk_assessment"]["status"], "FAILED")
        self.assertIn("missing risk score", checks["risk_assessment"]["reason"].lower())

    def test_get_action_verification_report_flow(self):
        store = ActionStore()
        action = store.create_action(
            ward_id="W2",
            ward_name="Behrampura",
            action_type="shade_canopy",
            priority="high",
            reason="Deploy shade canopy at BRTS station.",
            required_resources={"cost_inr": 30000, "crew_required": 3, "water_required_l": 0},
            risk_score=78.0,
        )

        # Before verification, report should be NOT_VERIFIED
        pre_report = get_action_verification_report(action["action_id"], store=store)
        self.assertEqual(pre_report["overall_status"], "NOT_VERIFIED")

        # Run verification
        verify_intervention_evidence(action, verified_by="Nodal Officer", store=store)

        # After verification, report reflects persisted result
        post_report = get_action_verification_report(action["action_id"], store=store)
        self.assertEqual(post_report["overall_status"], "VERIFIED")
        self.assertEqual(post_report["verified_by"], "Nodal Officer")


if __name__ == "__main__":
    unittest.main()
