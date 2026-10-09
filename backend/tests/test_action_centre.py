"""
ClimateShield - Action Centre Unit & Integration Tests
=======================================================
Tests the Action Centre module independently using mocked engine outputs.
Does NOT call real external APIs or modify existing engines.
"""

import pytest
import sys
import os

# Ensure project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from backend.action_centre import (
    ActionStore,
    get_action_store,
    generate_actions_from_climate_risk,
    generate_actions_from_interventions,
    build_action_centre_dashboard,
    ACTION_TYPES,
    VALID_STATUSES,
    VALID_STATUS_TRANSITIONS,
    HUMAN_APPROVAL_NOTICE,
)


# ---------------------------------------------------------------------------
# Fixtures: realistic mock data that mirrors real engine outputs
# ---------------------------------------------------------------------------

def _make_mock_climate_risk_data():
    """Produces a realistic Combined Climate Risk Engine output dict."""
    return {
        "city": "Ahmedabad",
        "coordinates": {"lat": 23.0225, "lon": 72.5714},
        "timestamp": "2026-10-09T12:00:00+00:00",
        "scoring_configuration": {
            "scoring_mode": "COMPOUND_SYNERGY",
            "weight_heat": 0.5,
            "weight_water": 0.5,
        },
        "data_quality_and_confidence": {
            "heat_data_source": "Open-Meteo real-time weather API",
            "water_data_source": "Open-Meteo precipitation + synthetic demo",
            "overall_confidence": "MODERATE",
        },
        "ranked_wards": [
            {
                "id": "W1",
                "name": "Danilimda",
                "official_name": "36 DANILIMDA",
                "ward_index": 0,
                "combined_risk_score": 82.5,
                "heat_risk_score": 78.0,
                "water_risk_score": 65.0,
                "combined_risk_category": "CRITICAL",
                "heat_risk_category": "HIGH",
                "water_risk_category": "ELEVATED",
                "compound_hazard": {
                    "is_compound_hotspot": True,
                    "tier": "DUAL_HIGH",
                    "badge": "⚠️ COMPOUND HIGH RISK",
                    "summary": "Both heat and water risks elevated.",
                },
                "heat_contributing_factors": "High slum density, outdoor labor",
                "water_contributing_factors": "Low drainage capacity",
            },
            {
                "id": "W2",
                "name": "Behrampura",
                "official_name": "37 BEHRAMPURA",
                "ward_index": 1,
                "combined_risk_score": 71.0,
                "heat_risk_score": 68.0,
                "water_risk_score": 55.0,
                "combined_risk_category": "HIGH",
                "heat_risk_category": "HIGH",
                "water_risk_category": "ELEVATED",
                "compound_hazard": {
                    "is_compound_hotspot": True,
                    "tier": "DUAL_HIGH",
                    "badge": "⚠️ COMPOUND HIGH RISK",
                    "summary": "Both elevated.",
                },
            },
            {
                "id": "W3",
                "name": "Sabarmati",
                "official_name": "10 SABARMATI",
                "ward_index": 2,
                "combined_risk_score": 35.0,
                "heat_risk_score": 32.0,
                "water_risk_score": 28.0,
                "combined_risk_category": "MODERATE",
                "heat_risk_category": "MODERATE",
                "water_risk_category": "MODERATE",
                "compound_hazard": {
                    "is_compound_hotspot": False,
                    "tier": "MODERATE_OR_LOW",
                    "badge": "✅ NORMAL",
                    "summary": "Normal operations.",
                },
            },
            {
                "id": "W4",
                "name": "Maninagar",
                "official_name": "14 MANINAGAR",
                "ward_index": 3,
                "combined_risk_score": 18.0,
                "heat_risk_score": 20.0,
                "water_risk_score": 15.0,
                "combined_risk_category": "LOW",
                "heat_risk_category": "LOW",
                "water_risk_category": "LOW",
                "compound_hazard": {
                    "is_compound_hotspot": False,
                    "tier": "MODERATE_OR_LOW",
                    "badge": "✅ NORMAL",
                    "summary": "Normal.",
                },
            },
        ],
    }


def _make_mock_intervention_plan():
    """Produces a realistic Intervention Engine dispatch plan output."""
    return {
        "status": "SUCCESS",
        "optimized_dispatch_plan": [
            {
                "intervention_id": "cooling_center",
                "target_ward": {"ward_id": "W1", "ward_name": "Danilimda"},
                "reason": "Severe ambient heat stress in Danilimda.",
                "composite_priority_score": 0.88,
                "unit_cost_inr": 50000.0,
                "crew_required": 4,
                "water_required_l": 500.0,
                "related_hazard": "heat",
                "ward_combined_risk_score": 82.5,
            },
            {
                "intervention_id": "hydration_kiosk",
                "target_ward": {"ward_id": "W1", "ward_name": "Danilimda"},
                "reason": "High outdoor occupational heat exposure in Danilimda.",
                "composite_priority_score": 0.72,
                "unit_cost_inr": 15000.0,
                "crew_required": 2,
                "water_required_l": 1200.0,
                "related_hazard": "heat",
                "ward_combined_risk_score": 82.5,
            },
            {
                "intervention_id": "drainage_inspection_cleaning",
                "target_ward": {"ward_id": "W2", "ward_name": "Behrampura"},
                "reason": "Storm drain capacity saturated in Behrampura.",
                "composite_priority_score": 0.65,
                "unit_cost_inr": 30000.0,
                "crew_required": 4,
                "water_required_l": 0.0,
                "related_hazard": "waterlogging",
                "ward_combined_risk_score": 71.0,
            },
        ],
    }


# ---------------------------------------------------------------------------
# ActionStore unit tests
# ---------------------------------------------------------------------------

class TestActionStore:
    """Tests for the in-memory ActionStore."""

    def setup_method(self):
        self.store = ActionStore()

    def test_create_action_basic(self):
        action = self.store.create_action(
            ward_id="W1",
            ward_name="Danilimda",
            action_type="heat_alert",
            priority="critical",
            reason="Test heat alert",
        )
        assert action["action_id"].startswith("ACT-")
        assert action["ward_id"] == "W1"
        assert action["ward_name"] == "Danilimda"
        assert action["action_type"] == "heat_alert"
        assert action["priority"] == "critical"
        assert action["status"] == "proposed"
        assert action["reason"] == "Test heat alert"
        assert action["created_at"] is not None
        assert len(action["status_history"]) == 1
        assert action["status_history"][0]["status"] == "proposed"

    def test_create_action_invalid_type(self):
        with pytest.raises(ValueError, match="Invalid action_type"):
            self.store.create_action(
                ward_id="W1",
                ward_name="Danilimda",
                action_type="invalid_type",
                priority="high",
                reason="Test",
            )

    def test_create_action_with_resources(self):
        action = self.store.create_action(
            ward_id="W1",
            ward_name="Danilimda",
            action_type="cooling_centre",
            priority="high",
            reason="Cooling centre needed",
            required_resources={"cost_inr": 50000, "crew_required": 4},
            related_hazard="heat",
            risk_score=78.0,
        )
        assert action["required_resources"]["cost_inr"] == 50000
        assert action["related_hazard"] == "heat"
        assert action["risk_score"] == 78.0

    def test_get_action(self):
        created = self.store.create_action(
            ward_id="W1", ward_name="Test", action_type="heat_alert",
            priority="high", reason="R"
        )
        retrieved = self.store.get_action(created["action_id"])
        assert retrieved is not None
        assert retrieved["action_id"] == created["action_id"]

    def test_get_action_not_found(self):
        assert self.store.get_action("ACT-NONEXIST") is None

    def test_list_actions_no_filter(self):
        self.store.create_action(
            ward_id="W1", ward_name="A", action_type="heat_alert",
            priority="high", reason="R1"
        )
        self.store.create_action(
            ward_id="W2", ward_name="B", action_type="drainage_cleaning",
            priority="medium", reason="R2"
        )
        actions = self.store.list_actions()
        assert len(actions) == 2

    def test_list_actions_filter_ward(self):
        self.store.create_action(
            ward_id="W1", ward_name="Danilimda", action_type="heat_alert",
            priority="high", reason="R1"
        )
        self.store.create_action(
            ward_id="W2", ward_name="Behrampura", action_type="drainage_cleaning",
            priority="medium", reason="R2"
        )
        results = self.store.list_actions(ward_id="W1")
        assert len(results) == 1
        assert results[0]["ward_id"] == "W1"

    def test_list_actions_filter_by_name(self):
        self.store.create_action(
            ward_id="W1", ward_name="Danilimda", action_type="heat_alert",
            priority="high", reason="R1"
        )
        results = self.store.list_actions(ward_id="danilimda")
        assert len(results) == 1

    def test_list_actions_filter_type(self):
        self.store.create_action(
            ward_id="W1", ward_name="A", action_type="heat_alert",
            priority="high", reason="R1"
        )
        self.store.create_action(
            ward_id="W2", ward_name="B", action_type="drainage_cleaning",
            priority="medium", reason="R2"
        )
        results = self.store.list_actions(action_type="heat_alert")
        assert len(results) == 1
        assert results[0]["action_type"] == "heat_alert"

    def test_list_actions_filter_status(self):
        a1 = self.store.create_action(
            ward_id="W1", ward_name="A", action_type="heat_alert",
            priority="high", reason="R1"
        )
        self.store.create_action(
            ward_id="W2", ward_name="B", action_type="drainage_cleaning",
            priority="medium", reason="R2"
        )
        self.store.update_status(a1["action_id"], "approved")
        results = self.store.list_actions(status="approved")
        assert len(results) == 1
        assert results[0]["status"] == "approved"

    def test_status_transitions_happy_path(self):
        action = self.store.create_action(
            ward_id="W1", ward_name="A", action_type="heat_alert",
            priority="high", reason="R"
        )
        aid = action["action_id"]

        # proposed -> approved
        updated = self.store.update_status(aid, "approved", changed_by="commissioner")
        assert updated["status"] == "approved"
        assert len(updated["status_history"]) == 2

        # approved -> in_progress
        updated = self.store.update_status(aid, "in_progress", changed_by="field_team")
        assert updated["status"] == "in_progress"

        # in_progress -> completed
        updated = self.store.update_status(
            aid, "completed", changed_by="field_team", notes="Deployment finished"
        )
        assert updated["status"] == "completed"
        assert len(updated["status_history"]) == 4
        assert updated["status_history"][-1]["notes"] == "Deployment finished"

    def test_status_transition_cancel(self):
        action = self.store.create_action(
            ward_id="W1", ward_name="A", action_type="heat_alert",
            priority="high", reason="R"
        )
        updated = self.store.update_status(action["action_id"], "cancelled")
        assert updated["status"] == "cancelled"

    def test_status_transition_invalid(self):
        action = self.store.create_action(
            ward_id="W1", ward_name="A", action_type="heat_alert",
            priority="high", reason="R"
        )
        with pytest.raises(ValueError, match="Cannot transition"):
            # proposed -> completed is not allowed
            self.store.update_status(action["action_id"], "completed")

    def test_status_transition_from_terminal(self):
        action = self.store.create_action(
            ward_id="W1", ward_name="A", action_type="heat_alert",
            priority="high", reason="R"
        )
        self.store.update_status(action["action_id"], "cancelled")

        with pytest.raises(ValueError, match="Cannot transition"):
            self.store.update_status(action["action_id"], "proposed")

    def test_invalid_status_value(self):
        action = self.store.create_action(
            ward_id="W1", ward_name="A", action_type="heat_alert",
            priority="high", reason="R"
        )
        with pytest.raises(ValueError, match="Invalid status"):
            self.store.update_status(action["action_id"], "nonexistent_status")

    def test_update_nonexistent_action(self):
        with pytest.raises(KeyError, match="not found"):
            self.store.update_status("ACT-DOESNOTEXIST", "approved")

    def test_count_by_status(self):
        a1 = self.store.create_action(
            ward_id="W1", ward_name="A", action_type="heat_alert",
            priority="high", reason="R1"
        )
        self.store.create_action(
            ward_id="W2", ward_name="B", action_type="drainage_cleaning",
            priority="medium", reason="R2"
        )
        self.store.update_status(a1["action_id"], "approved")

        counts = self.store.count_by_status()
        assert counts["approved"] == 1
        assert counts["proposed"] == 1
        assert counts["completed"] == 0

    def test_clear(self):
        self.store.create_action(
            ward_id="W1", ward_name="A", action_type="heat_alert",
            priority="high", reason="R"
        )
        assert len(self.store.list_actions()) == 1
        self.store.clear()
        assert len(self.store.list_actions()) == 0


# ---------------------------------------------------------------------------
# Action generation from engine outputs
# ---------------------------------------------------------------------------

class TestActionGeneration:
    """Tests for generating actions from risk and intervention outputs."""

    def setup_method(self):
        self.store = ActionStore()

    def test_generate_from_climate_risk(self):
        climate_data = _make_mock_climate_risk_data()
        result = generate_actions_from_climate_risk(climate_data, store=self.store)

        assert result["status"] == "SUCCESS"
        assert result["total_actions_created"] > 0
        assert "advisory" in result

        # Danilimda (78 heat) and Behrampura (68 heat) and Sabarmati (32 heat)
        # should all get heat alerts (>=30)
        # Maninagar (20 heat, combined 18) should NOT (combined < 25)
        action_wards = {a["ward_id"] for a in result["actions"]}
        assert "W1" in action_wards  # Danilimda
        assert "W2" in action_wards  # Behrampura
        assert "W3" in action_wards  # Sabarmati (heat=32, combined=35)
        assert "W4" not in action_wards  # Maninagar (combined=18 < 25)

    def test_generate_from_climate_risk_all_actions_are_proposed(self):
        climate_data = _make_mock_climate_risk_data()
        result = generate_actions_from_climate_risk(climate_data, store=self.store)
        for action in result["actions"]:
            assert action["status"] == "proposed"
            assert action["action_type"] == "heat_alert"
            assert action["source"] == "climate_risk_engine"

    def test_generate_from_climate_risk_includes_compound_info(self):
        climate_data = _make_mock_climate_risk_data()
        result = generate_actions_from_climate_risk(climate_data, store=self.store)
        w1_actions = [a for a in result["actions"] if a["ward_id"] == "W1"]
        assert len(w1_actions) == 1
        assert "compound" in w1_actions[0]["reason"].lower()

    def test_generate_from_climate_risk_empty_input(self):
        result = generate_actions_from_climate_risk(
            {"ranked_wards": []}, store=self.store
        )
        assert result["total_actions_created"] == 0
        assert result["actions"] == []

    def test_generate_from_interventions(self):
        plan = _make_mock_intervention_plan()
        result = generate_actions_from_interventions(plan, store=self.store)

        assert result["status"] == "SUCCESS"
        assert result["total_actions_created"] == 3
        assert "advisory" in result

        action_types = [a["action_type"] for a in result["actions"]]
        assert "cooling_centre" in action_types
        assert "drinking_water_point" in action_types
        assert "drainage_cleaning" in action_types

    def test_generate_from_interventions_preserves_resources(self):
        plan = _make_mock_intervention_plan()
        result = generate_actions_from_interventions(plan, store=self.store)
        cooling = [a for a in result["actions"] if a["action_type"] == "cooling_centre"][0]
        assert cooling["required_resources"]["cost_inr"] == 50000.0
        assert cooling["required_resources"]["crew_required"] == 4

    def test_generate_from_interventions_empty_plan(self):
        result = generate_actions_from_interventions({}, store=self.store)
        assert result["total_actions_created"] == 0

    def test_actions_are_stored(self):
        climate_data = _make_mock_climate_risk_data()
        generate_actions_from_climate_risk(climate_data, store=self.store)
        all_actions = self.store.list_actions()
        assert len(all_actions) > 0


# ---------------------------------------------------------------------------
# Dashboard builder tests
# ---------------------------------------------------------------------------

class TestDashboard:
    """Tests for the dashboard summary builder."""

    def setup_method(self):
        self.store = ActionStore()

    def test_dashboard_with_risk_data(self):
        climate_data = _make_mock_climate_risk_data()
        dashboard = build_action_centre_dashboard(
            climate_risk_data=climate_data, store=self.store
        )
        assert dashboard["status"] == "SUCCESS"
        assert "advisory" in dashboard
        assert dashboard["high_risk_wards"]["count"] >= 1  # Danilimda & Behrampura

        # Only wards with combined >= 50 should appear
        for w in dashboard["high_risk_wards"]["wards"]:
            assert w["combined_risk_score"] >= 50.0

    def test_dashboard_contributing_factors(self):
        climate_data = _make_mock_climate_risk_data()
        dashboard = build_action_centre_dashboard(
            climate_risk_data=climate_data, store=self.store
        )
        ward = dashboard["high_risk_wards"]["wards"][0]
        assert "contributing_factors" in ward
        assert "heat" in ward["contributing_factors"]
        assert "water" in ward["contributing_factors"]

    def test_dashboard_data_freshness(self):
        climate_data = _make_mock_climate_risk_data()
        dashboard = build_action_centre_dashboard(
            climate_risk_data=climate_data,
            data_quality={"overall_confidence": "HIGH"},
            store=self.store,
        )
        assert dashboard["data_freshness"]["climate_risk_available"] is True
        assert dashboard["data_freshness"]["data_quality"]["overall_confidence"] == "HIGH"

    def test_dashboard_without_risk_data(self):
        dashboard = build_action_centre_dashboard(
            climate_risk_data=None, store=self.store
        )
        assert dashboard["high_risk_wards"]["count"] == 0
        assert dashboard["data_freshness"]["climate_risk_available"] is False

    def test_dashboard_includes_action_summary(self):
        self.store.create_action(
            ward_id="W1", ward_name="A", action_type="heat_alert",
            priority="high", reason="R1"
        )
        a2 = self.store.create_action(
            ward_id="W2", ward_name="B", action_type="drainage_cleaning",
            priority="medium", reason="R2"
        )
        self.store.update_status(a2["action_id"], "approved")

        dashboard = build_action_centre_dashboard(store=self.store)
        assert dashboard["action_summary"]["total_actions"] == 2
        assert dashboard["action_summary"]["by_status"]["proposed"] == 1
        assert dashboard["action_summary"]["by_status"]["approved"] == 1

    def test_dashboard_recent_actions_ordered(self):
        self.store.create_action(
            ward_id="W1", ward_name="First", action_type="heat_alert",
            priority="high", reason="R1"
        )
        self.store.create_action(
            ward_id="W2", ward_name="Second", action_type="cooling_centre",
            priority="critical", reason="R2"
        )
        dashboard = build_action_centre_dashboard(store=self.store)
        assert len(dashboard["recent_actions"]) == 2
        # Most recent first
        assert dashboard["recent_actions"][0]["created_at"] >= dashboard["recent_actions"][1]["created_at"]


# ---------------------------------------------------------------------------
# Validation & edge cases
# ---------------------------------------------------------------------------

class TestValidation:
    """Tests for validation, error handling, and edge cases."""

    def test_all_action_types_are_valid(self):
        store = ActionStore()
        for at in ACTION_TYPES:
            action = store.create_action(
                ward_id="W1", ward_name="Test", action_type=at,
                priority="medium", reason="Testing type"
            )
            assert action["action_type"] == at

    def test_all_status_transitions_defined(self):
        for status in VALID_STATUSES:
            assert status in VALID_STATUS_TRANSITIONS

    def test_terminal_states_have_no_transitions(self):
        assert VALID_STATUS_TRANSITIONS["completed"] == set()
        assert VALID_STATUS_TRANSITIONS["cancelled"] == set()

    def test_unique_action_ids(self):
        store = ActionStore()
        ids = set()
        for i in range(50):
            action = store.create_action(
                ward_id="W1", ward_name="Test", action_type="heat_alert",
                priority="medium", reason=f"Action {i}"
            )
            ids.add(action["action_id"])
        assert len(ids) == 50  # All unique

    def test_never_marks_completed_unless_explicit(self):
        """Actions never start as completed."""
        store = ActionStore()
        action = store.create_action(
            ward_id="W1", ward_name="Test", action_type="heat_alert",
            priority="high", reason="Test"
        )
        assert action["status"] == "proposed"
        assert action["status"] != "completed"

    def test_missing_data_marked_not_fabricated(self):
        """Dashboard marks unavailable data explicitly."""
        store = ActionStore()
        dashboard = build_action_centre_dashboard(
            climate_risk_data=None, store=store
        )
        assert dashboard["data_freshness"]["climate_risk_available"] is False
        assert dashboard["data_freshness"]["climate_risk_timestamp"] is None
        assert "unavailable" in str(dashboard["data_freshness"]["data_quality"])

    def test_human_approval_notice_present(self):
        assert "DECISION SUPPORT ADVISORY" in HUMAN_APPROVAL_NOTICE
        assert "human review" in HUMAN_APPROVAL_NOTICE

    def test_singleton_store(self):
        s1 = get_action_store()
        s2 = get_action_store()
        assert s1 is s2


# ---------------------------------------------------------------------------
# Run with pytest
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
