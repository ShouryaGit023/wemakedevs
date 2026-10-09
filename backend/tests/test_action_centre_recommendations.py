"""
ClimateShield - Action Centre Rule-Based Recommendation Layer Tests
===================================================================
Tests for transparent, configurable rule-based recommendations:
- Heat action category (heat alerts, cooling centres, hydration kiosks, shade canopies)
- Flood action category (drainage inspection/cleaning, mobile pumps, flood barricades)
- Drought / water stress action category (water conservation, allocation review, tankers)
- Missing inputs handling (never invents sensor readings, infrastructure, or missing risks)
- Duplicate prevention for unresolved risks (proposed, approved, in_progress)
- Re-recommendation enabled when prior action is completed or cancelled
- Respecting staff, budget, and water resource constraints (including Optimizer plans)
- Advisory safety rules (always status 'proposed', never claims execution or broadcast)
- API endpoint integration
"""

import unittest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.main import app
from backend.action_centre import (
    ActionStore,
    RuleBasedRecommendationEngine,
    generate_rule_based_recommendations,
    get_prioritized_actions,
    get_ward_wise_action_summary,
    evaluate_risk_data_freshness,
    build_action_centre_dashboard,
    DEFAULT_RECOMMENDATION_THRESHOLDS,
    ACTION_RESOURCE_ESTIMATES,
    RULE_DEFINITIONS,
    UNRESOLVED_STATUSES,
    RESOLVED_STATUSES,
    HUMAN_APPROVAL_NOTICE,
)


def _make_mock_ward(
    ward_id: str = "W1",
    name: str = "Danilimda",
    heat_score: float = 75.0,
    waterlogging_score: float = 60.0,
    water_shortage_score: float = 55.0,
    is_compound: bool = False,
    wbgt: float = 32.5,
):
    """Produces a realistic mock ward record."""
    return {
        "id": ward_id,
        "name": name,
        "official_name": f"36 {name.upper()}",
        "combined_risk_score": max(heat_score, waterlogging_score, water_shortage_score),
        "heat_risk_score": heat_score,
        "heat_risk": {
            "score": heat_score,
            "category": "HIGH" if heat_score >= 50 else "MODERATE",
            "effective_wbgt_c": wbgt,
        },
        "water_risk": {
            "score": max(waterlogging_score, water_shortage_score),
            "waterlogging_score": waterlogging_score,
            "water_shortage_score": water_shortage_score,
            "contributing_factors": {
                "waterlogging": {"score": waterlogging_score, "category": "HIGH"},
                "water_shortage": {"score": water_shortage_score, "category": "HIGH"},
            },
        },
        "compound_hazard": {
            "is_compound_hotspot": is_compound,
            "tier": "DUAL_HIGH" if is_compound else "MODERATE_OR_LOW",
            "badge": "⚠️ COMPOUND HIGH RISK" if is_compound else "✅ NORMAL",
        },
    }


class TestHeatRecommendations(unittest.TestCase):
    """Tests for the extreme heat action recommendation category."""

    def setUp(self):
        self.store = ActionStore()

    def test_high_heat_recommends_alerts_cooling_and_hydration(self):
        """A ward with high heat risk (75.0) triggers heat alerts, cooling centre, and hydration point."""
        ward = _make_mock_ward(
            ward_id="W1",
            name="Danilimda",
            heat_score=75.0,
            waterlogging_score=20.0,  # below flood thresholds
            water_shortage_score=20.0,  # below drought thresholds
        )
        engine = RuleBasedRecommendationEngine()
        candidates = engine.evaluate_ward(ward)

        action_types = [c["action_type"] for c in candidates]
        self.assertIn("heat_alert", action_types)
        self.assertIn("cooling_centre", action_types)
        self.assertIn("drinking_water_point", action_types)
        self.assertIn("shade_canopy", action_types)

        # Flood and drought rules should NOT have triggered
        self.assertNotIn("drainage_cleaning", action_types)
        self.assertNotIn("water_conservation_advisory", action_types)

    def test_moderate_heat_threshold_scaling(self):
        """Heat risk at 48.0 triggers drinking_water_point (threshold 45.0) but not heat_alert (50.0) or cooling_centre (60.0)."""
        ward = _make_mock_ward(
            ward_id="W2",
            name="Behrampura",
            heat_score=48.0,
            waterlogging_score=10.0,
            water_shortage_score=10.0,
        )
        engine = RuleBasedRecommendationEngine()
        candidates = engine.evaluate_ward(ward)
        action_types = [c["action_type"] for c in candidates]

        self.assertIn("drinking_water_point", action_types)
        self.assertNotIn("heat_alert", action_types)
        self.assertNotIn("cooling_centre", action_types)

    def test_low_heat_triggers_no_heat_recommendations(self):
        """Heat risk below 45.0 triggers no heat actions."""
        ward = _make_mock_ward(
            ward_id="W3",
            name="Sabarmati",
            heat_score=30.0,
            waterlogging_score=10.0,
            water_shortage_score=10.0,
        )
        engine = RuleBasedRecommendationEngine()
        candidates = engine.evaluate_ward(ward)
        heat_candidates = [c for c in candidates if c["related_hazard"] == "heat"]
        self.assertEqual(len(heat_candidates), 0)

    def test_heat_explanation_is_transparent_and_factual(self):
        """Explanations cite heat risk score, threshold, effective WBGT, and disclaim physical broadcasts."""
        ward = _make_mock_ward(
            ward_id="W1",
            name="Danilimda",
            heat_score=72.5,
            waterlogging_score=10.0,
            water_shortage_score=10.0,
            wbgt=33.1,
        )
        res = generate_rule_based_recommendations(
            climate_risk_data={"ranked_wards": [ward]},
            store=self.store,
        )
        actions = res["recommendations"]
        heat_alert = next(a for a in actions if a["action_type"] == "heat_alert")

        self.assertIn("72.5/100", heat_alert["reason"])
        self.assertIn("50.0", heat_alert["reason"])
        self.assertIn("Danilimda", heat_alert["reason"])
        self.assertIn("33.1°C", heat_alert["reason"])
        self.assertIn("Advisory only", heat_alert["reason"])
        self.assertIn("no real-time public alerts have been broadcast", heat_alert["reason"])


class TestFloodRecommendations(unittest.TestCase):
    """Tests for the pluvial flood / waterlogging action recommendation category."""

    def setUp(self):
        self.store = ActionStore()

    def test_flood_recommends_drainage_cleaning_when_supported(self):
        """Waterlogging indicator at 45.0 triggers drainage_cleaning (threshold 40.0)."""
        ward = _make_mock_ward(
            ward_id="W2",
            name="Behrampura",
            heat_score=20.0,
            waterlogging_score=45.0,
            water_shortage_score=10.0,
        )
        res = generate_rule_based_recommendations(
            climate_risk_data={"ranked_wards": [ward]},
            store=self.store,
        )
        action_types = [a["action_type"] for a in res["recommendations"]]
        self.assertIn("drainage_cleaning", action_types)
        self.assertNotIn("mobile_pump", action_types)  # threshold 55.0
        self.assertNotIn("flood_barricade", action_types)  # threshold 65.0

    def test_severe_flood_recommends_pump_and_barricade(self):
        """Severe waterlogging at 68.0 triggers drainage cleaning, mobile pump, and barricade."""
        ward = _make_mock_ward(
            ward_id="W2",
            name="Behrampura",
            heat_score=20.0,
            waterlogging_score=68.0,
            water_shortage_score=10.0,
        )
        res = generate_rule_based_recommendations(
            climate_risk_data={"ranked_wards": [ward]},
            store=self.store,
        )
        action_types = [a["action_type"] for a in res["recommendations"]]
        self.assertIn("drainage_cleaning", action_types)
        self.assertIn("mobile_pump", action_types)
        self.assertIn("flood_barricade", action_types)

    def test_low_waterlogging_triggers_no_flood_recommendations(self):
        """Waterlogging below 40.0 triggers no flood actions."""
        ward = _make_mock_ward(
            ward_id="W4",
            name="Maninagar",
            heat_score=20.0,
            waterlogging_score=35.0,
            water_shortage_score=10.0,
        )
        engine = RuleBasedRecommendationEngine()
        candidates = engine.evaluate_ward(ward)
        flood_cands = [c for c in candidates if c["related_hazard"] == "flood"]
        self.assertEqual(len(flood_cands), 0)

    def test_flood_explanation_is_transparent_and_factual(self):
        """Flood explanation cites waterlogging score, threshold, and disclaims physical desilting work."""
        ward = _make_mock_ward(
            ward_id="W2",
            name="Behrampura",
            heat_score=15.0,
            waterlogging_score=58.0,
            water_shortage_score=15.0,
        )
        res = generate_rule_based_recommendations(
            climate_risk_data={"ranked_wards": [ward]},
            store=self.store,
        )
        actions = res["recommendations"]
        drainage = next(a for a in actions if a["action_type"] == "drainage_cleaning")

        self.assertIn("58.0/100", drainage["reason"])
        self.assertIn("40.0", drainage["reason"])
        self.assertIn("Behrampura", drainage["reason"])
        self.assertIn("Advisory only", drainage["reason"])
        self.assertIn("no physical desilting work has been performed", drainage["reason"])


class TestDroughtWaterStressRecommendations(unittest.TestCase):
    """Tests for the drought / water shortage action recommendation category."""

    def setUp(self):
        self.store = ActionStore()

    def test_drought_recommends_conservation_when_supported(self):
        """Water shortage indicator at 45.0 triggers water_conservation_advisory (threshold 40.0)."""
        ward = _make_mock_ward(
            ward_id="W5",
            name="Khadia",
            heat_score=20.0,
            waterlogging_score=10.0,
            water_shortage_score=45.0,
        )
        res = generate_rule_based_recommendations(
            climate_risk_data={"ranked_wards": [ward]},
            store=self.store,
        )
        action_types = [a["action_type"] for a in res["recommendations"]]
        self.assertIn("water_conservation_advisory", action_types)
        self.assertNotIn("water_allocation_review", action_types)  # threshold 50.0
        self.assertNotIn("water_tanker_dispatch", action_types)  # threshold 55.0

    def test_severe_drought_recommends_allocation_and_tankers(self):
        """Severe water shortage at 58.0 triggers conservation, allocation review, and tanker dispatch."""
        ward = _make_mock_ward(
            ward_id="W5",
            name="Khadia",
            heat_score=20.0,
            waterlogging_score=10.0,
            water_shortage_score=58.0,
        )
        res = generate_rule_based_recommendations(
            climate_risk_data={"ranked_wards": [ward]},
            store=self.store,
        )
        action_types = [a["action_type"] for a in res["recommendations"]]
        self.assertIn("water_conservation_advisory", action_types)
        self.assertIn("water_allocation_review", action_types)
        self.assertIn("water_tanker_dispatch", action_types)

    def test_low_water_shortage_triggers_no_drought_recommendations(self):
        """Water shortage below 40.0 triggers no drought actions."""
        ward = _make_mock_ward(
            ward_id="W6",
            name="Amraiwadi",
            heat_score=20.0,
            waterlogging_score=10.0,
            water_shortage_score=35.0,
        )
        engine = RuleBasedRecommendationEngine()
        candidates = engine.evaluate_ward(ward)
        drought_cands = [c for c in candidates if c["related_hazard"] == "water_stress"]
        self.assertEqual(len(drought_cands), 0)

    def test_drought_explanation_is_transparent_and_factual(self):
        """Drought explanation cites shortage score, threshold, and disclaims physical enforcement/dispatch."""
        ward = _make_mock_ward(
            ward_id="W5",
            name="Khadia",
            heat_score=10.0,
            waterlogging_score=10.0,
            water_shortage_score=52.0,
        )
        res = generate_rule_based_recommendations(
            climate_risk_data={"ranked_wards": [ward]},
            store=self.store,
        )
        actions = res["recommendations"]
        alloc = next(a for a in actions if a["action_type"] == "water_allocation_review")

        self.assertIn("52.0/100", alloc["reason"])
        self.assertIn("50.0", alloc["reason"])
        self.assertIn("Khadia", alloc["reason"])
        self.assertIn("Advisory only", alloc["reason"])
        self.assertIn("no valve adjustments or quota shifts have been executed", alloc["reason"])


class TestMissingInputsHandling(unittest.TestCase):
    """Tests that missing inputs never crash and never invent fabricated numbers."""

    def setUp(self):
        self.store = ActionStore()

    def test_missing_water_indicators_never_invents_flood_or_drought_actions(self):
        """When ward has only heat data, flood and drought rules do NOT fire."""
        ward = {
            "id": "W1",
            "name": "Danilimda",
            "heat_risk_score": 80.0,
            # No water_risk, no waterlogging_score, no water_shortage_score
        }
        res = generate_rule_based_recommendations(
            climate_risk_data={"ranked_wards": [ward]},
            store=self.store,
        )
        action_types = [a["action_type"] for a in res["recommendations"]]
        self.assertIn("heat_alert", action_types)
        self.assertNotIn("drainage_cleaning", action_types)
        self.assertNotIn("water_conservation_advisory", action_types)

    def test_missing_heat_indicators_never_invents_heat_actions(self):
        """When ward has only flood data, heat rules do NOT fire."""
        ward = {
            "id": "W2",
            "name": "Behrampura",
            "waterlogging_score": 65.0,
            # No heat_risk_score, no heat_risk
        }
        res = generate_rule_based_recommendations(
            climate_risk_data={"ranked_wards": [ward]},
            store=self.store,
        )
        action_types = [a["action_type"] for a in res["recommendations"]]
        self.assertIn("drainage_cleaning", action_types)
        self.assertNotIn("heat_alert", action_types)
        self.assertNotIn("cooling_centre", action_types)

    def test_completely_empty_ward_produces_zero_recommendations(self):
        """An empty ward record produces no recommendations and does not error."""
        ward = {"id": "W99"}
        res = generate_rule_based_recommendations(
            climate_risk_data={"ranked_wards": [ward]},
            store=self.store,
        )
        self.assertEqual(res["total_recommendations"], 0)
        self.assertEqual(res["status"], "SUCCESS")

    def test_empty_or_none_climate_data_handled_gracefully(self):
        """None or empty climate data returns SUCCESS with 0 recommendations."""
        res_none = generate_rule_based_recommendations(climate_risk_data=None, store=self.store)
        self.assertEqual(res_none["status"], "SUCCESS")
        self.assertEqual(res_none["total_recommendations"], 0)

        res_empty = generate_rule_based_recommendations(climate_risk_data={}, store=self.store)
        self.assertEqual(res_empty["status"], "SUCCESS")
        self.assertEqual(res_empty["total_recommendations"], 0)

        res_empty_list = generate_rule_based_recommendations(climate_risk_data={"ranked_wards": []}, store=self.store)
        self.assertEqual(res_empty_list["status"], "SUCCESS")
        self.assertEqual(res_empty_list["total_recommendations"], 0)


class TestDuplicatePrevention(unittest.TestCase):
    """Tests preventing duplicate recommendations for the same ward and unresolved risk."""

    def setUp(self):
        self.store = ActionStore()

    def test_duplicate_prevented_when_proposed_action_exists(self):
        """If ward W1 already has an unresolved 'proposed' heat_alert, duplicate is skipped."""
        self.store.create_action(
            ward_id="W1",
            ward_name="Danilimda",
            action_type="heat_alert",
            priority="high",
            reason="Pre-existing active action",
        )

        ward = _make_mock_ward(ward_id="W1", heat_score=75.0, waterlogging_score=10.0, water_shortage_score=10.0)
        res = generate_rule_based_recommendations(
            climate_risk_data={"ranked_wards": [ward]},
            store=self.store,
        )

        # The new heat_alert must NOT be created
        created_heat_alerts = [a for a in res["recommendations"] if a["action_type"] == "heat_alert"]
        self.assertEqual(len(created_heat_alerts), 0)

        # It must be recorded in skipped_duplicates
        dup = next((d for d in res["skipped_duplicates"] if d["action_type"] == "heat_alert"), None)
        self.assertIsNotNone(dup)
        self.assertEqual(dup["ward_id"], "W1")
        self.assertIn("already exists", dup["reason"])

    def test_duplicate_prevented_when_approved_action_exists(self):
        """If ward W1 has an 'approved' action, duplicate recommendation is skipped."""
        act = self.store.create_action(
            ward_id="W1",
            ward_name="Danilimda",
            action_type="heat_alert",
            priority="high",
            reason="Prior approved action",
        )
        self.store.update_status(act["action_id"], "approved")

        ward = _make_mock_ward(ward_id="W1", heat_score=75.0, waterlogging_score=10.0, water_shortage_score=10.0)
        res = generate_rule_based_recommendations(
            climate_risk_data={"ranked_wards": [ward]},
            store=self.store,
        )
        dup = next((d for d in res["skipped_duplicates"] if d["action_type"] == "heat_alert"), None)
        self.assertIsNotNone(dup)
        self.assertEqual(dup["existing_status"], "approved")

    def test_duplicate_prevented_when_in_progress_action_exists(self):
        """If ward W1 has an 'in_progress' action, duplicate recommendation is skipped."""
        act = self.store.create_action(
            ward_id="W1",
            ward_name="Danilimda",
            action_type="drainage_cleaning",
            priority="high",
            reason="Prior in progress action",
        )
        self.store.update_status(act["action_id"], "approved")
        self.store.update_status(act["action_id"], "in_progress")

        ward = _make_mock_ward(ward_id="W1", heat_score=10.0, waterlogging_score=50.0, water_shortage_score=10.0)
        res = generate_rule_based_recommendations(
            climate_risk_data={"ranked_wards": [ward]},
            store=self.store,
        )
        dup = next((d for d in res["skipped_duplicates"] if d["action_type"] == "drainage_cleaning"), None)
        self.assertIsNotNone(dup)
        self.assertEqual(dup["existing_status"], "in_progress")

    def test_new_recommendation_allowed_when_previous_completed(self):
        """If prior action was completed (resolved risk), a new recommendation CAN be created."""
        act = self.store.create_action(
            ward_id="W1",
            ward_name="Danilimda",
            action_type="heat_alert",
            priority="high",
            reason="Old resolved heatwave action",
        )
        self.store.update_status(act["action_id"], "approved")
        self.store.update_status(act["action_id"], "in_progress")
        self.store.update_status(act["action_id"], "completed")

        ward = _make_mock_ward(ward_id="W1", heat_score=75.0, waterlogging_score=10.0, water_shortage_score=10.0)
        res = generate_rule_based_recommendations(
            climate_risk_data={"ranked_wards": [ward]},
            store=self.store,
        )
        created_heat_alerts = [a for a in res["recommendations"] if a["action_type"] == "heat_alert"]
        self.assertEqual(len(created_heat_alerts), 1)

    def test_new_recommendation_allowed_when_previous_cancelled(self):
        """If prior action was cancelled (terminal state), a new recommendation CAN be created."""
        act = self.store.create_action(
            ward_id="W1",
            ward_name="Danilimda",
            action_type="heat_alert",
            priority="high",
            reason="Cancelled action",
        )
        self.store.update_status(act["action_id"], "cancelled")

        ward = _make_mock_ward(ward_id="W1", heat_score=75.0, waterlogging_score=10.0, water_shortage_score=10.0)
        res = generate_rule_based_recommendations(
            climate_risk_data={"ranked_wards": [ward]},
            store=self.store,
        )
        created_heat_alerts = [a for a in res["recommendations"] if a["action_type"] == "heat_alert"]
        self.assertEqual(len(created_heat_alerts), 1)

    def test_batch_deduplication(self):
        """Multiple duplicate candidate evaluations in a single pass produce only one recommendation."""
        # Ward appears twice in ranked list
        ward = _make_mock_ward(ward_id="W1", heat_score=75.0, waterlogging_score=10.0, water_shortage_score=10.0)
        res = generate_rule_based_recommendations(
            climate_risk_data={"ranked_wards": [ward, ward]},
            store=self.store,
        )
        heat_alerts = [a for a in res["recommendations"] if a["action_type"] == "heat_alert"]
        self.assertEqual(len(heat_alerts), 1)
        self.assertGreaterEqual(res["skipped_duplicates_count"], 1)

    def test_different_action_types_for_same_ward_allowed(self):
        """Different action types for the same ward are both recommended (not falsely deduplicated)."""
        ward = _make_mock_ward(ward_id="W1", heat_score=75.0, waterlogging_score=10.0, water_shortage_score=10.0)
        res = generate_rule_based_recommendations(
            climate_risk_data={"ranked_wards": [ward]},
            store=self.store,
        )
        types = [a["action_type"] for a in res["recommendations"]]
        self.assertIn("heat_alert", types)
        self.assertIn("cooling_centre", types)
        self.assertIn("drinking_water_point", types)


class TestResourceConstraints(unittest.TestCase):
    """Tests respecting staff, budget, and water resource constraints."""

    def setUp(self):
        self.store = ActionStore()

    def test_budget_constraint_enforces_ceiling(self):
        """Actions exceeding available budget are skipped and marked in skipped_resource_constrained."""
        # Cooling centre costs 50,000 INR; shade canopy costs 25,000 INR
        ward = _make_mock_ward(ward_id="W1", heat_score=75.0, waterlogging_score=10.0, water_shortage_score=10.0)
        res = generate_rule_based_recommendations(
            climate_risk_data={"ranked_wards": [ward]},
            resource_constraints={"available_budget_inr": 55000.0},
            store=self.store,
        )
        # Cooling centre (50,000) and heat alert (5,000) fit (total 55,000).
        # Shade canopy (25,000) or drinking water (15,000) cannot fit after budget depleted.
        self.assertGreater(res["skipped_resource_constrained_count"], 0)
        total_cost_allocated = sum(
            a["required_resources"].get("cost_inr", 0) for a in res["recommendations"]
        )
        self.assertLessEqual(total_cost_allocated, 55000.0)
        self.assertTrue(res["resource_summary"]["constraints_enforced"])

    def test_crew_constraint_enforces_ceiling(self):
        """Actions exceeding available crew are skipped."""
        # Cooling centre requires 4 crew. Provide only 2 crew.
        ward = _make_mock_ward(ward_id="W1", heat_score=75.0, waterlogging_score=10.0, water_shortage_score=10.0)
        res = generate_rule_based_recommendations(
            climate_risk_data={"ranked_wards": [ward]},
            resource_constraints={"available_crew": 2},
            store=self.store,
        )
        types = [a["action_type"] for a in res["recommendations"]]
        self.assertNotIn("cooling_centre", types)  # requires 4 crew
        # Actions requiring <= 2 crew (heat_alert=1, drinking_water_point=2) can be considered
        for a in res["recommendations"]:
            self.assertLessEqual(a["required_resources"].get("crew_required", 0), 2)

    def test_water_constraint_enforces_ceiling(self):
        """Water tanker requiring 5,000L is skipped when water cap is 1,000L."""
        ward = _make_mock_ward(ward_id="W5", heat_score=10.0, waterlogging_score=10.0, water_shortage_score=60.0)
        res = generate_rule_based_recommendations(
            climate_risk_data={"ranked_wards": [ward]},
            resource_constraints={"available_water_l": 1000.0},
            store=self.store,
        )
        types = [a["action_type"] for a in res["recommendations"]]
        self.assertNotIn("water_tanker_dispatch", types)  # requires 5,000L
        skipped_types = [s["action_type"] for s in res["skipped_resource_constrained"]]
        self.assertIn("water_tanker_dispatch", skipped_types)

    def test_priority_allocation_order(self):
        """Critical priority actions are allocated before lower priority ones under limited resources."""
        # W1 critical heat (80.0), W2 high heat (65.0) - both trigger cooling_centre
        w1 = _make_mock_ward(ward_id="W1", name="Danilimda", heat_score=80.0, waterlogging_score=10.0, water_shortage_score=10.0)
        w2 = _make_mock_ward(ward_id="W2", name="Behrampura", heat_score=65.0, waterlogging_score=10.0, water_shortage_score=10.0)

        # Budget of 60,000 INR covers W1's heat_alert (5,000) + cooling_centre (50,000) = 55,000 INR.
        # W2's cooling_centre (50,000) is evaluated later (lower priority/score) and cannot fit into remaining 5,000 INR.
        res = generate_rule_based_recommendations(
            climate_risk_data={"ranked_wards": [w1, w2]},
            resource_constraints={"available_budget_inr": 60000.0},
            store=self.store,
        )
        cooling_actions = [a for a in res["recommendations"] if a["action_type"] == "cooling_centre"]
        self.assertEqual(len(cooling_actions), 1)
        self.assertEqual(cooling_actions[0]["ward_id"], "W1")
        # Verify W2's cooling centre was skipped due to budget constraint
        skipped_cooling = [s for s in res["skipped_resource_constrained"] if s["action_type"] == "cooling_centre"]
        self.assertEqual(len(skipped_cooling), 1)
        self.assertEqual(skipped_cooling[0]["ward_id"], "W2")

    def test_unconstrained_mode_when_no_limits_provided(self):
        """When no resource constraints are passed, all rule-triggered recommendations are generated."""
        ward = _make_mock_ward(ward_id="W1", heat_score=75.0, waterlogging_score=65.0, water_shortage_score=60.0)
        res = generate_rule_based_recommendations(
            climate_risk_data={"ranked_wards": [ward]},
            resource_constraints=None,
            store=self.store,
        )
        self.assertEqual(res["skipped_resource_constrained_count"], 0)
        self.assertFalse(res["resource_summary"]["constraints_enforced"])
        self.assertGreater(res["total_recommendations"], 4)

    def test_optimizer_plan_ingestion(self):
        """Recommender can ingest and respect an Optimizer plan with resource limits."""
        optimizer_plan = {
            "resource_limits": {
                "budget_inr": 200000.0,
                "crew_members": 20,
                "water_liters": 15000.0,
            },
            "dispatch_plan": [
                {
                    "intervention_id": "cooling_center",
                    "target_ward": {"ward_id": "W1", "ward_name": "Danilimda"},
                    "reason": "Severe thermal stress refugee center.",
                    "unit_cost_inr": 50000.0,
                    "crew_required": 4,
                    "water_required_l": 500.0,
                    "composite_priority_score": 0.88,
                    "related_hazard": "heat",
                },
                {
                    "intervention_id": "drainage_inspection_cleaning",
                    "target_ward": {"ward_id": "W2", "ward_name": "Behrampura"},
                    "reason": "Clear choked storm culverts.",
                    "unit_cost_inr": 30000.0,
                    "crew_required": 4,
                    "water_required_l": 0.0,
                    "composite_priority_score": 0.75,
                    "related_hazard": "waterlogging",
                },
            ]
        }
        res = generate_rule_based_recommendations(
            optimizer_plan=optimizer_plan,
            store=self.store,
        )
        self.assertEqual(res["total_recommendations"], 2)
        types = [a["action_type"] for a in res["recommendations"]]
        self.assertIn("cooling_centre", types)
        self.assertIn("drainage_cleaning", types)
        self.assertTrue(res["resource_summary"]["constraints_enforced"])
        self.assertEqual(res["resource_summary"]["consumed_resources"]["budget_inr"], 80000.0)


class TestConfigurableThresholds(unittest.TestCase):
    """Tests that thresholds can be customized and transparently inspected."""

    def setUp(self):
        self.store = ActionStore()

    def test_raising_threshold_suppresses_action(self):
        """Raising heat_alert_threshold to 90.0 suppresses alert for heat risk 75.0."""
        ward = _make_mock_ward(ward_id="W1", heat_score=75.0, waterlogging_score=10.0, water_shortage_score=10.0)
        res = generate_rule_based_recommendations(
            climate_risk_data={"ranked_wards": [ward]},
            thresholds={"heat_alert_threshold": 90.0},
            store=self.store,
        )
        types = [a["action_type"] for a in res["recommendations"]]
        self.assertNotIn("heat_alert", types)

    def test_lowering_threshold_triggers_earlier_action(self):
        """Lowering drainage_cleaning_threshold to 25.0 triggers for score 30.0."""
        ward = _make_mock_ward(ward_id="W1", heat_score=10.0, waterlogging_score=30.0, water_shortage_score=10.0)
        res = generate_rule_based_recommendations(
            climate_risk_data={"ranked_wards": [ward]},
            thresholds={"drainage_cleaning_threshold": 25.0},
            store=self.store,
        )
        types = [a["action_type"] for a in res["recommendations"]]
        self.assertIn("drainage_cleaning", types)


class TestAdvisoryAndSafetyRules(unittest.TestCase):
    """Tests safety rules: status proposed, advisory notice, no physical claims."""

    def setUp(self):
        self.store = ActionStore()

    def test_all_generated_actions_have_proposed_status(self):
        """Recommendations are ALWAYS generated with status 'proposed'."""
        ward = _make_mock_ward(ward_id="W1", heat_score=75.0, waterlogging_score=60.0, water_shortage_score=55.0)
        res = generate_rule_based_recommendations(
            climate_risk_data={"ranked_wards": [ward]},
            store=self.store,
        )
        for a in res["recommendations"]:
            self.assertEqual(a["status"], "proposed")
            self.assertNotEqual(a["status"], "approved")
            self.assertNotEqual(a["status"], "completed")

    def test_human_approval_notice_always_present(self):
        """Top-level result includes HUMAN_APPROVAL_NOTICE."""
        res = generate_rule_based_recommendations(
            climate_risk_data={"ranked_wards": []},
            store=self.store,
        )
        self.assertEqual(res["advisory"], HUMAN_APPROVAL_NOTICE)


class TestFastAPIEndpoints(unittest.TestCase):
    """Tests the recommendations REST API endpoints."""

    def setUp(self):
        self.client = TestClient(app)

    def test_api_recommendations_rules_metadata(self):
        """GET /api/action-centre/recommendations/rules returns transparent rule definitions."""
        resp = self.client.get("/api/action-centre/recommendations/rules")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertIn("rules", data)
        self.assertIn("default_thresholds", data)
        self.assertIn("resource_estimates", data)
        self.assertIn("heat_alert_threshold", data["default_thresholds"])

    def test_api_generate_recommendations_endpoint(self):
        """POST /api/action-centre/recommendations returns valid recommendations."""
        payload = {
            "available_budget_inr": 200000.0,
            "available_crew": 20,
            "available_water_l": 15000.0,
            "persist_to_store": False,  # simulation mode
        }
        resp = self.client.post("/api/action-centre/recommendations", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertIn("recommendations", data)
        self.assertIn("resource_summary", data)
        self.assertIn("skipped_duplicates", data)

    def test_api_prioritized_actions_endpoint(self):
        """GET /api/action-centre/actions/prioritized returns prioritized actions queue."""
        resp = self.client.get("/api/action-centre/actions/prioritized?limit=10")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertIn("prioritized_actions", data)
        self.assertIn("total_actions", data)

    def test_api_ward_summary_endpoint(self):
        """GET /api/action-centre/actions/ward-summary returns ward-wise aggregation."""
        resp = self.client.get("/api/action-centre/actions/ward-summary")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertIn("ward_summaries", data)
        self.assertIn("total_wards_with_actions", data)

    def test_api_dashboard_resilience_fallback(self):
        """GET /api/action-centre/dashboard safely falls back even when invalid scenario is passed."""
        resp = self.client.get("/api/action-centre/dashboard?scenario_id=nonexistent_scenario_xyz")
        # Should NOT crash with 500
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertIn("data_freshness", data)
        self.assertIn("ward_action_summary", data)
        self.assertIn("prioritized_actions", data)


class TestWardWiseAndPrioritization(unittest.TestCase):
    """Tests for ward-wise aggregation, action prioritization queue, and freshness checking."""

    def setUp(self):
        self.store = ActionStore()

    def test_ward_wise_action_summary_aggregation(self):
        """Ward-wise summary groups actions, calculates active counts, and correlates with risk."""
        # Ward 1: 1 proposed, 1 approved, 1 completed
        self.store.create_action(ward_id="W1", ward_name="Danilimda", action_type="heat_alert", priority="high", reason="R1")
        a2 = self.store.create_action(ward_id="W1", ward_name="Danilimda", action_type="cooling_centre", priority="critical", reason="R2")
        self.store.update_status(a2["action_id"], "approved")
        a3 = self.store.create_action(ward_id="W1", ward_name="Danilimda", action_type="drinking_water_point", priority="medium", reason="R3")
        self.store.update_status(a3["action_id"], "approved")
        self.store.update_status(a3["action_id"], "in_progress")
        self.store.update_status(a3["action_id"], "completed")

        # Ward 2: 1 proposed
        self.store.create_action(ward_id="W2", ward_name="Behrampura", action_type="drainage_cleaning", priority="medium", reason="R4")

        mock_risk = {
            "ranked_wards": [
                {"id": "W1", "name": "Danilimda", "combined_risk_score": 82.5, "combined_risk_category": "CRITICAL"},
                {"id": "W2", "name": "Behrampura", "combined_risk_score": 65.0, "combined_risk_category": "HIGH"},
            ]
        }

        summaries = get_ward_wise_action_summary(store=self.store, climate_risk_data=mock_risk)
        self.assertEqual(len(summaries), 2)

        w1_summary = next(s for s in summaries if s["ward_id"] == "W1")
        self.assertEqual(w1_summary["total_actions"], 3)
        self.assertEqual(w1_summary["active_actions_count"], 2)  # proposed + approved (completed is resolved)
        self.assertEqual(w1_summary["highest_priority"], "critical")
        self.assertEqual(w1_summary["by_status"]["proposed"], 1)
        self.assertEqual(w1_summary["by_status"]["approved"], 1)
        self.assertEqual(w1_summary["by_status"]["completed"], 1)
        self.assertEqual(w1_summary["risk_profile"]["combined_risk_score"], 82.5)

    def test_prioritized_actions_ordering(self):
        """Actions are sorted by priority: critical > high > medium > low, then urgency, then risk score."""
        self.store.create_action(ward_id="W3", ward_name="Sabarmati", action_type="shade_canopy", priority="low", reason="Low", risk_score=20.0)
        self.store.create_action(ward_id="W1", ward_name="Danilimda", action_type="cooling_centre", priority="critical", reason="Crit", risk_score=85.0)
        self.store.create_action(ward_id="W2", ward_name="Behrampura", action_type="drainage_cleaning", priority="high", reason="High", risk_score=65.0)
        self.store.create_action(ward_id="W4", ward_name="Maninagar", action_type="mobile_pump", priority="critical", reason="Crit 2", risk_score=90.0)

        prioritized = get_prioritized_actions(store=self.store)
        self.assertEqual(len(prioritized), 4)

        # Top 2 must be critical priority, ordered by risk score (90.0 before 85.0)
        self.assertEqual(prioritized[0]["priority"], "critical")
        self.assertEqual(prioritized[0]["risk_score"], 90.0)
        self.assertEqual(prioritized[1]["priority"], "critical")
        self.assertEqual(prioritized[1]["risk_score"], 85.0)

        # 3rd is high, 4th is low
        self.assertEqual(prioritized[2]["priority"], "high")
        self.assertEqual(prioritized[3]["priority"], "low")

    def test_dashboard_includes_ward_summary_and_prioritized_actions(self):
        """build_action_centre_dashboard contains ward_action_summary and prioritized_actions keys."""
        self.store.create_action(ward_id="W1", ward_name="Danilimda", action_type="heat_alert", priority="high", reason="R1")
        dashboard = build_action_centre_dashboard(store=self.store)

        self.assertIn("ward_action_summary", dashboard)
        self.assertIn("prioritized_actions", dashboard)
        self.assertEqual(dashboard["ward_action_summary"]["total_wards_with_actions"], 1)
        self.assertEqual(len(dashboard["prioritized_actions"]), 1)

    def test_staleness_detection_fresh_vs_stale_vs_unavailable(self):
        """evaluate_risk_data_freshness marks FRESH, STALE, or UNAVAILABLE accurately."""
        # 1. Unavailable when None
        fresh_none = evaluate_risk_data_freshness(None)
        self.assertEqual(fresh_none["staleness_status"], "UNAVAILABLE")
        self.assertFalse(fresh_none["climate_risk_available"])

        # 2. Fresh when recent
        now_ts = datetime.now(timezone.utc).isoformat()
        fresh_recent = evaluate_risk_data_freshness({"timestamp": now_ts})
        self.assertEqual(fresh_recent["staleness_status"], "FRESH")
        self.assertFalse(fresh_recent["is_stale"])
        self.assertTrue(fresh_recent["climate_risk_available"])

        # 3. Stale when older than threshold
        old_ts = "2020-01-01T00:00:00+00:00"
        fresh_old = evaluate_risk_data_freshness({"timestamp": old_ts}, max_age_seconds=3600.0)
        self.assertEqual(fresh_old["staleness_status"], "STALE")
        self.assertTrue(fresh_old["is_stale"])


if __name__ == "__main__":
    unittest.main()

