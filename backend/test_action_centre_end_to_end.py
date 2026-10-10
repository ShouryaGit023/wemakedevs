"""
ClimateShield - End-to-End Tests for Action Centre Functionality
================================================================
Validates:
1. Decision Workflow: Approve, Reject, Hold/Block, Unblock, Request Changes.
2. Reason enforcement for rejection, blocking, and changes requested.
3. Verification requirements preventing approval/dispatch when checks FAIL.
4. Quick Dispatch eligibility, duplicate-dispatch prevention, and SQLite persistence.
5. Immutable SQLite Audit Trail for actions and dispatches.
6. Real backend metrics calculation for dashboard.
"""

import unittest
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.action_centre import (
    ActionStore,
    VALID_STATUSES,
    VALID_STATUS_TRANSITIONS,
    build_action_centre_dashboard,
    dispatch_quick_action,
    get_prioritized_actions,
    verify_intervention_evidence,
)
from backend.database import list_action_audit_events, record_action_verification


class TestActionCentreEndToEnd(unittest.TestCase):

    def setUp(self):
        self.store = ActionStore()

    def test_decision_workflow_valid_transitions(self):
        # 1. Create proposed action
        action = self.store.create_action(
            ward_id="W1",
            ward_name="Danilimda",
            action_type="cooling_centre",
            priority="high",
            reason="High heat index forecasted.",
            required_resources={"cost_inr": 50000, "crew_required": 4, "water_required_l": 1000},
            risk_score=75.0,
        )
        action_id = action["action_id"]
        self.assertEqual(action["status"], "proposed")

        # 2. Block/Hold requires reason
        with self.assertRaises(ValueError):
            self.store.update_status(action_id, "blocked", changed_by="Incident Commander", notes="")

        # 3. Block with valid reason
        blocked = self.store.update_status(
            action_id, "blocked", changed_by="Incident Commander", notes="Awaiting electrical safety sign-off."
        )
        self.assertEqual(blocked["status"], "blocked")

        # 4. Unblock back to proposed
        unblocked = self.store.update_status(
            action_id, "proposed", changed_by="Incident Commander", notes="Safety clearance granted."
        )
        self.assertEqual(unblocked["status"], "proposed")

        # 5. Request Changes requires reason
        with self.assertRaises(ValueError):
            self.store.update_status(action_id, "changes_requested", changed_by="Commissioner", notes="")

        # 6. Reject requires reason
        with self.assertRaises(ValueError):
            self.store.update_status(action_id, "rejected", changed_by="Commissioner", notes="")

        # 7. Approve with authorized role
        approved = self.store.update_status(
            action_id, "approved", changed_by="Municipal Commissioner", notes="Approved for field deployment."
        )
        self.assertEqual(approved["status"], "approved")

        # 8. Deploy to in_progress
        deployed = self.store.update_status(
            action_id, "in_progress", changed_by="Incident Commander", notes="Field teams deployed."
        )
        self.assertEqual(deployed["status"], "in_progress")

        # 9. Complete operation
        completed = self.store.update_status(
            action_id, "completed", changed_by="Field Lead", notes="Mission completed."
        )
        self.assertEqual(completed["status"], "completed")

        # 10. Completed is terminal - cannot transition to approved or proposed
        with self.assertRaises(ValueError):
            self.store.update_status(action_id, "approved", changed_by="Incident Commander")

    def test_failed_verification_blocks_approval(self):
        # Action with invalid negative budget to trigger verification failure
        action = self.store.create_action(
            ward_id="W1",
            ward_name="Danilimda",
            action_type="cooling_centre",
            priority="high",
            reason="Testing failed verification block.",
            required_resources={"cost_inr": -5000, "crew_required": 4},
            risk_score=80.0,
        )
        action_id = action["action_id"]

        # Run verification which will fail due to negative cost
        verif = verify_intervention_evidence(action, store=self.store)
        self.assertEqual(verif["overall_status"], "FAILED")

        # Attempting to approve must raise ValueError due to FAILED verification
        with self.assertRaises(ValueError) as ctx:
            self.store.update_status(action_id, "approved", changed_by="Municipal Commissioner")
        self.assertIn("FAILED mandatory checks", str(ctx.exception))

    def test_quick_dispatch_duplicate_prevention(self):
        # First dispatch should succeed
        res1 = dispatch_quick_action(
            ward_id="W1",
            ward_name="Danilimda",
            action_type="water_tanker_dispatch",
            priority="critical",
            reason="Initial emergency water tanker dispatch.",
            required_resources={"cost_inr": 72000, "crew_required": 12, "water_required_l": 30000},
            risk_score=85.0,
            authorized_by="Municipal Incident Commander",
            initial_status="in_progress",
            store=self.store,
        )
        self.assertEqual(res1["status"], "SUCCESS")
        self.assertEqual(res1["action"]["status"], "in_progress")

        # Duplicate dispatch of same type to same ward without force should be blocked
        with self.assertRaises(ValueError) as ctx:
            dispatch_quick_action(
                ward_id="W1",
                ward_name="Danilimda",
                action_type="water_tanker_dispatch",
                priority="critical",
                reason="Duplicate dispatch attempt.",
                authorized_by="Municipal Incident Commander",
                store=self.store,
            )
        self.assertIn("Active duplicate dispatch prevented", str(ctx.exception))

        # Forced emergency dispatch override should succeed
        res_forced = dispatch_quick_action(
            ward_id="W1",
            ward_name="Danilimda",
            action_type="water_tanker_dispatch",
            priority="critical",
            reason="Second emergency wave override.",
            authorized_by="Municipal Incident Commander",
            force=True,
            store=self.store,
        )
        self.assertEqual(res_forced["status"], "SUCCESS")

    def test_quick_dispatch_invalid_ward_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            dispatch_quick_action(
                ward_id="INVALID_WARD_99",
                action_type="cooling_centre",
                authorized_by="Incident Commander",
                store=self.store,
            )
        self.assertIn("not recognized in the AMC municipal boundary registry", str(ctx.exception))

    def test_audit_history_logging(self):
        action = self.store.create_action(
            ward_id="W2",
            ward_name="Kalupur",
            action_type="drinking_water_point",
            priority="medium",
            reason="Misting stations at Kalupur.",
            required_resources={"cost_inr": 30000, "crew_required": 3},
            risk_score=60.0,
        )
        action_id = action["action_id"]

        # Transition status
        self.store.update_status(
            action_id, "approved", changed_by="Zonal Officer", notes="Operational permit issued."
        )

        # Retrieve audit events from SQLite
        events = list_action_audit_events(action_id=action_id)
        self.assertGreaterEqual(len(events), 2)
        event_types = [e["event_type"] for e in events]
        self.assertIn("ACTION_CREATED", event_types)
        self.assertIn("STATUS_TRANSITION_APPROVED", event_types)

        approved_event = next(e for e in events if e["event_type"] == "STATUS_TRANSITION_APPROVED")
        self.assertEqual(approved_event["actor"], "Zonal Officer")
        self.assertEqual(approved_event["reason"], "Operational permit issued.")

    def test_dashboard_metrics_calculation(self):
        # Create a mix of actions with different statuses and priorities
        self.store.create_action(
            ward_id="W1", ward_name="Danilimda", action_type="heat_alert", priority="critical", reason="Alert 1"
        )
        a2 = self.store.create_action(
            ward_id="W2", ward_name="Kalupur", action_type="cooling_centre", priority="high", reason="Alert 2"
        )
        self.store.update_status(a2["action_id"], "approved", changed_by="Officer", notes="Approved")

        a3 = self.store.create_action(
            ward_id="W3", ward_name="Khokhra", action_type="mobile_pump", priority="critical", reason="Alert 3"
        )
        self.store.update_status(a3["action_id"], "approved", changed_by="Officer", notes="Approved")
        self.store.update_status(a3["action_id"], "in_progress", changed_by="Officer", notes="Deployed")

        a4 = self.store.create_action(
            ward_id="W4", ward_name="Gomtipur", action_type="drainage_cleaning", priority="medium", reason="Alert 4"
        )
        self.store.update_status(a4["action_id"], "blocked", changed_by="Officer", notes="Road blocked")

        dashboard = build_action_centre_dashboard(store=self.store)
        metrics = dashboard["metrics"]

        # 4 total registered actions
        self.assertEqual(metrics["total_registered_actions"], 4)
        # 2 active deployments (1 approved + 1 in_progress)
        self.assertEqual(metrics["active_deployments"], 2)
        # 2 critical interventions
        self.assertEqual(metrics["critical_interventions"], 2)
        # 1 pending sign-off (proposed)
        self.assertEqual(metrics["pending_sign_off"], 1)
        # 1 blocked operation
        self.assertEqual(metrics["blocked_operations"], 1)


if __name__ == "__main__":
    unittest.main()
