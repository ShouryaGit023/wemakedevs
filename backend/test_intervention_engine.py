"""
Unit and Integration Tests for ClimateShield Intervention Engine
Verifies candidate generation, multi-criteria ranking, resource-constrained optimization,
existing intervention handling, road closure safety gates, and FastAPI endpoints.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi.testclient import TestClient
from backend.main import app
from backend.intervention_engine import (
    InterventionEngine,
    generate_intervention_recommendations,
    INTERVENTIONS_CATALOG,
    PROVENANCE_LABELS
)


class TestInterventionEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = InterventionEngine()
        cls.client = TestClient(app)
        cls.test_wards = [
            {
                "id": "W1",
                "name": "Danilimda",
                "vulnerability": 0.92,
                "population": 120000,
                "heat_risk_score": 82.0,
                "waterlogging_score": 78.5,
                "water_shortage_score": 38.0,
                "is_compound_hotspot": True
            },
            {
                "id": "W2",
                "name": "Behrampura",
                "vulnerability": 0.85,
                "population": 95000,
                "heat_risk_score": 42.0,
                "waterlogging_score": 45.0,
                "water_shortage_score": 65.0,
                "is_compound_hotspot": False
            },
            {
                "id": "W3",
                "name": "Sabarmati",
                "vulnerability": 0.40,
                "population": 70000,
                "heat_risk_score": 30.0,
                "waterlogging_score": 25.0,
                "water_shortage_score": 20.0,
                "is_compound_hotspot": False
            }
        ]

    def test_01_catalog_structure_and_provenance(self):
        """Verifies intervention catalog integrity, costs, and provenance labels."""
        self.assertGreaterEqual(len(INTERVENTIONS_CATALOG), 10)
        for act_id, det in INTERVENTIONS_CATALOG.items():
            self.assertIn("unit_cost_inr", det)
            self.assertIn("crew_required", det)
            self.assertIn("water_required_l", det)
            self.assertIn("category", det)
            self.assertIn(det["category"], ["heat", "waterlogging", "water_shortage"])
            self.assertIn("trigger_threshold", det)
            self.assertIn("reason_template", det)

        # Check provenance dictionary
        self.assertIn("MEASURED_INPUT", PROVENANCE_LABELS)
        self.assertIn("ESTIMATED_IMPACT", PROVENANCE_LABELS)
        self.assertIn("DEMONSTRATION_ASSUMPTION", PROVENANCE_LABELS)

    def test_02_candidate_generation_and_threshold_gating(self):
        """Verifies candidate generation triggers only when hazard meets threshold."""
        candidates = self.engine.generate_candidate_interventions(self.test_wards)
        self.assertTrue(len(candidates) > 0)

        # W1 has heat=82.0 (>=45), waterlogging=78.5 (>=70) -> Should have cooling centers and road closure
        w1_actions = [c["action_id"] for c in candidates if c["ward_id"] == "W1"]
        self.assertIn("cooling_center", w1_actions)
        self.assertIn("road_closure_recommendation", w1_actions)

        # W2 has heat=42.0 (<45), waterlogging=45.0 (<70) -> NO cooling center (needs 45), NO road closure (needs 70)
        w2_actions = [c["action_id"] for c in candidates if c["ward_id"] == "W2"]
        self.assertNotIn("cooling_center", w2_actions)
        self.assertNotIn("road_closure_recommendation", w2_actions)
        # But W2 has water_shortage=65.0 -> Should have tanker allocation and drinking water distribution
        self.assertIn("water_tanker_allocation", w2_actions)
        self.assertIn("drinking_water_distribution", w2_actions)

        # W3 has low risks across all hazards -> Should have 0 candidates
        w3_actions = [c["action_id"] for c in candidates if c["ward_id"] == "W3"]
        self.assertEqual(len(w3_actions), 0)

    def test_03_road_closure_strict_safety_threshold(self):
        """Verifies road closures are strictly blocked when flood score < 70.0."""
        borderline_ward = [{
            "id": "W_SUB",
            "name": "Submergence Test Ward",
            "vulnerability": 0.8,
            "population": 50000,
            "heat_risk_score": 20.0,
            "waterlogging_score": 69.5,  # Just below 70.0
            "water_shortage_score": 10.0
        }]
        cands = self.engine.generate_candidate_interventions(borderline_ward)
        c_actions = [c["action_id"] for c in cands]
        self.assertNotIn("road_closure_recommendation", c_actions, "Road closures must not trigger below 70.0")

    def test_04_existing_interventions_deduction(self):
        """Verifies already deployed interventions are deducted and not duplicated."""
        # W1 max cooling centers is 2. If 2 are already deployed, remaining should be 0 (omitted from candidates).
        existing = [
            {"ward_id": "W1", "action_id": "cooling_center", "units": 2}
        ]
        candidates = self.engine.generate_candidate_interventions(self.test_wards, existing_interventions=existing)
        w1_cooling = [c for c in candidates if c["ward_id"] == "W1" and c["action_id"] == "cooling_center"]
        self.assertEqual(len(w1_cooling), 0, "Ward at max capacity for cooling centers must not receive duplicate candidate")

        # If 1 is already deployed, 1 should remain
        existing_partial = [
            {"ward_id": "W1", "action_id": "cooling_center", "units": 1}
        ]
        cands_partial = self.engine.generate_candidate_interventions(self.test_wards, existing_interventions=existing_partial)
        w1_cooling_partial = [c for c in cands_partial if c["ward_id"] == "W1" and c["action_id"] == "cooling_center"]
        self.assertEqual(len(w1_cooling_partial), 1)
        self.assertEqual(w1_cooling_partial[0]["max_units_deployable"], 1)
        self.assertEqual(w1_cooling_partial[0]["already_deployed_units"], 1)

    def test_05_multi_criteria_ranking(self):
        """Verifies candidate ranking sorts actions by composite score and provides explanations."""
        candidates = self.engine.generate_candidate_interventions(self.test_wards)
        ranked = self.engine.rank_candidate_interventions(candidates, equity_slider=0.7)

        self.assertGreater(len(ranked), 0)
        # Check ranks are sequential 1, 2, ...
        ranks = [r["priority_rank"] for r in ranked]
        self.assertEqual(ranks, list(range(1, len(ranked) + 1)))

        # Check descending scores
        scores = [r["composite_priority_score"] for r in ranked]
        self.assertEqual(scores, sorted(scores, reverse=True))

        # Check explanation contains ward name and expected points
        first = ranked[0]
        self.assertIn(first["ward_name"], first["explanation"])
        self.assertIn("risk reduction points", first["explanation"])

    def test_06_resource_constrained_optimization(self):
        """Verifies optimization strictly enforces budget, crew, water, and capacity limits."""
        budget_cap = 200000.0
        crew_cap = 15
        water_cap = 10000.0

        res = self.engine.optimize_interventions(
            wards=self.test_wards,
            total_budget_inr=budget_cap,
            total_crew_members=crew_cap,
            total_water_cap_l=water_cap,
            equity_slider=0.5
        )

        res_sum = res["resource_summary"]
        self.assertLessEqual(res_sum["budget"]["allocated_inr"], budget_cap)
        self.assertLessEqual(res_sum["crew"]["allocated_members"], crew_cap)
        self.assertLessEqual(res_sum["water"]["allocated_liters"], water_cap)

        # Check human approval status on all recommendations
        for rec in res["ranked_recommendations"]:
            self.assertEqual(rec["approval_status"], "PENDING_HUMAN_APPROVAL")
            self.assertTrue(rec["requires_human_signoff"])
            self.assertIn("data_provenance", rec)

    def test_07_global_intervention_capacity_limit(self):
        """Verifies global intervention capacity cap prevents allocating beyond fleet size."""
        # Restrict water tankers to max 1 citywide
        cap_limits = {"water_tanker_allocation": 1}
        res = self.engine.optimize_interventions(
            wards=self.test_wards,
            total_budget_inr=1000000.0,
            total_crew_members=100,
            total_water_cap_l=50000.0,
            intervention_capacity_limits=cap_limits
        )
        tankers_allocated = sum(
            r["units_allocated"] for r in res["ranked_recommendations"]
            if r["action_id"] == "water_tanker_allocation"
        )
        self.assertLessEqual(tankers_allocated, 1)

    def test_08_fastapi_endpoints(self):
        """Verifies /api/interventions/catalog and /api/interventions/recommend endpoints."""
        # 1. Catalog endpoint
        r_cat = self.client.get("/api/interventions/catalog")
        self.assertEqual(r_cat.status_code, 200)
        cat_data = r_cat.json()
        self.assertEqual(cat_data["status"], "SUCCESS")
        self.assertIn("provenance_labels", cat_data)
        self.assertGreaterEqual(cat_data["total_interventions"], 10)

        # 2. Recommend endpoint
        payload = {
            "total_budget_inr": 350000.0,
            "total_crew_members": 25,
            "total_water_cap_l": 20000.0,
            "equity_slider": 0.6,
            "wards": self.test_wards,
            "existing_interventions": [
                {"ward_id": "W1", "action_id": "cooling_center", "units": 1}
            ]
        }
        r_rec = self.client.post("/api/interventions/recommend", json=payload)
        self.assertEqual(r_rec.status_code, 200)
        rec_data = r_rec.json()
        self.assertEqual(rec_data["status"], "OPTIMAL")
        self.assertIn("resource_summary", rec_data)
        self.assertIn("ranked_recommendations", rec_data)
        self.assertIn("ward_allocations", rec_data)
        self.assertEqual(rec_data["existing_interventions_accounted_for"], 1)

        # 3. Validation error on bad payload (budget below minimum)
        r_bad = self.client.post("/api/interventions/recommend", json={"total_budget_inr": -500.0})
        self.assertEqual(r_bad.status_code, 422)

        # 4. Ranked interventions endpoint across all wards
        r_ranked = self.client.get("/api/interventions/ranked?scenario_id=dry_baseline")
        self.assertEqual(r_ranked.status_code, 200)
        ranked_json = r_ranked.json()
        self.assertEqual(ranked_json["status"], "SUCCESS")
        self.assertGreater(ranked_json["total_ranked_interventions"], 0)

        # 5. Ward-specific interventions endpoint
        r_ward = self.client.get("/api/interventions/wards/Danilimda?scenario_id=dry_baseline")
        self.assertEqual(r_ward.status_code, 200)
        ward_json = r_ward.json()
        self.assertEqual(ward_json["status"], "SUCCESS")
        self.assertIn("interventions", ward_json)

        # 6. Non-existent ward lookup triggers 404
        r_w404 = self.client.get("/api/interventions/wards/non_existent_ward_999")
        self.assertEqual(r_w404.status_code, 404)

    def test_09_all_candidate_intervention_fields_represented(self):
        """Verifies all 11 required explainability fields are present in candidate interventions."""
        cands = self.engine.generate_candidate_interventions(self.test_wards)
        self.assertGreater(len(cands), 0)
        sample = cands[0]

        # 1. Intervention ID and type
        self.assertIn("intervention_id", sample)
        self.assertIn("intervention_type", sample)

        # 2. Target ward
        self.assertIn("target_ward", sample)
        self.assertIn("ward_id", sample["target_ward"])
        self.assertIn("ward_name", sample["target_ward"])

        # 3. Related hazard
        self.assertIn("related_hazard", sample)
        self.assertIn(sample["related_hazard"], ["heat", "flood/waterlogging", "water_shortage", "multi_hazard"])

        # 4. Estimated cost and cost assumptions
        self.assertIn("estimated_cost", sample)
        self.assertIn("unit_cost_inr", sample["estimated_cost"])
        self.assertIn("cost_assumptions", sample["estimated_cost"])

        # 5. Required staff, equipment, water, or capacity
        self.assertIn("required_resources", sample)
        self.assertIn("staff_personnel", sample["required_resources"])
        self.assertIn("equipment", sample["required_resources"])
        self.assertIn("water_liters", sample["required_resources"])

        # 6. Expected impact range with evidence
        self.assertIn("expected_impact_range", sample)
        self.assertIn("min_risk_reduction", sample["expected_impact_range"])
        self.assertIn("expected_risk_reduction", sample["expected_impact_range"])
        self.assertIn("max_risk_reduction", sample["expected_impact_range"])
        self.assertIn("evidence_note", sample["expected_impact_range"])

        # 7. Estimated number of people reached
        self.assertIn("estimated_people_reached", sample)
        self.assertIn("estimated_count", sample["estimated_people_reached"])
        self.assertIn("basis", sample["estimated_people_reached"])

        # 8. Lead time and urgency
        self.assertIn("lead_time_and_urgency", sample)
        self.assertIn("lead_time", sample["lead_time_and_urgency"])
        self.assertIn("urgency", sample["lead_time_and_urgency"])

        # 9. Reason for recommendation
        self.assertIn("reason_template", sample)

        # 10. Data quality and uncertainty
        self.assertIn("data_quality_and_uncertainty", sample)
        self.assertIn("confidence_level", sample["data_quality_and_uncertainty"])
        self.assertIn("uncertainty_interval", sample["data_quality_and_uncertainty"])

    def test_10_anti_double_counting_submodular_diminishing_returns(self):
        """Verifies submodular diminishing returns prevent double-counting when multiple actions address the same hazard."""
        flood_ward = [{
            "id": "W_FLOOD",
            "name": "Flood Hotspot",
            "vulnerability": 0.9,
            "population": 100000,
            "heat_risk_score": 10.0,
            "waterlogging_score": 75.0,
            "water_shortage_score": 10.0
        }]
        res = self.engine.optimize_interventions(
            wards=flood_ward,
            total_budget_inr=500000.0,
            total_crew_members=40,
            total_water_cap_l=30000.0
        )
        ward_alloc = res["ward_allocations"]["W_FLOOD"]
        # Cumulative risk reduction for this ward cannot exceed the actual waterlogging risk score (75.0)
        self.assertLessEqual(ward_alloc["total_risk_reduction"], 75.0)

    def test_11_equity_slider_preference_and_tradeoff_analysis(self):
        """Verifies equity preference shifts resources and tradeoff analysis measures efficiency opportunity cost."""
        res_tradeoff = self.engine.optimize_interventions(
            wards=self.test_wards,
            total_budget_inr=300000.0,
            total_crew_members=25,
            total_water_cap_l=20000.0,
            equity_slider=0.8,
            include_tradeoff_analysis=True
        )
        self.assertIn("tradeoff_analysis", res_tradeoff)
        ta = res_tradeoff["tradeoff_analysis"]
        self.assertIn("efficiency_benchmark_risk_reduction", ta)
        self.assertIn("maximum_equity_benchmark_risk_reduction", ta)
        self.assertIn("opportunity_cost_risk_reduction_points", ta)
        self.assertIn("high_vulnerability_wards_served", ta)
        self.assertIn("tradeoff_explanation", ta)
        # Efficiency benchmark risk reduction >= maximum equity risk reduction
        self.assertGreaterEqual(ta["efficiency_benchmark_risk_reduction"], ta["maximum_equity_benchmark_risk_reduction"])

    def test_12_combined_hazard_compound_hotspot_priority_boost(self):
        """Verifies compound hotspots receive urgency and priority elevation."""
        dual_hazard_ward = [{
            "id": "W_COMPOUND",
            "name": "Compound Crisis Ward",
            "vulnerability": 0.85,
            "population": 100000,
            "heat_risk_score": 65.0,
            "waterlogging_score": 65.0,
            "water_shortage_score": 30.0,
            "is_compound_hotspot": True
        }]
        single_hazard_ward = [{
            "id": "W_SINGLE",
            "name": "Single Heat Ward",
            "vulnerability": 0.85,
            "population": 100000,
            "heat_risk_score": 65.0,
            "waterlogging_score": 20.0,
            "water_shortage_score": 20.0,
            "is_compound_hotspot": False
        }]
        cands_dual = self.engine.generate_candidate_interventions(dual_hazard_ward)
        cands_single = self.engine.generate_candidate_interventions(single_hazard_ward)
        ranked_dual = self.engine.rank_candidate_interventions(cands_dual)
        ranked_single = self.engine.rank_candidate_interventions(cands_single)

        dual_cooling = next(c for c in ranked_dual if c["action_id"] == "cooling_center")
        single_cooling = next(c for c in ranked_single if c["action_id"] == "cooling_center")

        # Compound cooling center gets compound urgency multiplier boost
        self.assertGreater(dual_cooling["urgency_score"], single_cooling["urgency_score"])
        self.assertGreater(dual_cooling["priority_score"], single_cooling["priority_score"])

    def test_13_missing_water_data_hydrology_prior(self):
        """Verifies that missing water data is not treated as zero and uses conservative hydrology prior."""
        ward_no_water = [{
            "id": "W_MISSING_WATER",
            "name": "Missing Water Ward",
            "vulnerability": 0.85,
            "heat_risk_score": 50.0
            # Note: No water_risk or water_risk_score provided!
        }]
        norm = self.engine._normalize_ward_record(ward_no_water[0])
        self.assertGreater(norm["water_risk_score"], 0.0, "Missing water risk must have non-zero prior")
        self.assertGreater(norm["waterlogging_score"], 0.0, "Missing waterlogging risk must have non-zero prior")
        self.assertGreater(norm["water_shortage_score"], 0.0, "Missing shortage risk must have non-zero prior")
        self.assertIn("HYDROLOGY_PRIOR", norm["data_provenance"])

        cands = self.engine.generate_candidate_interventions(ward_no_water)
        water_cands = [c for c in cands if c["category"] in ["waterlogging", "water_shortage"]]
        self.assertGreater(len(water_cands), 0, "Missing water data must trigger baseline interventions via conservative prior")
        for wc in water_cands:
            self.assertGreater(wc["hazard_score"], 0.0, "Hazard score must not be 0.0 for missing water data")

    def test_14_infeasible_allocation_handling(self):
        """Verifies that infeasible allocations (e.g. budget too low) return structured CONSTRAINED status."""
        low_budget_ward = [{
            "id": "W1",
            "name": "Danilimda",
            "vulnerability": 0.9,
            "heat_risk_score": 80.0,
            "waterlogging_score": 75.0,
            "water_shortage_score": 50.0
        }]
        # Budget is 5000 INR, but lowest intervention cost is 12000 INR
        res = self.engine.optimize_interventions(
            wards=low_budget_ward,
            total_budget_inr=5000.0,
            total_crew_members=2,
            total_water_cap_l=1000.0
        )
        self.assertEqual(res["status"], "CONSTRAINED_NO_ALLOCATION")
        self.assertFalse(res["is_feasible"])
        self.assertIsNotNone(res["infeasibility_notes"])
        self.assertEqual(len(res["ranked_recommendations"]), 0)

    def test_15_what_if_budget_expansion_and_contraction(self):
        """Verifies what-if simulator recalculates allocations and tracks deltas under budget changes."""
        sim = self.engine.simulate_what_if_scenario(
            wards=self.test_wards,
            baseline_budget_inr=200000.0,
            simulated_budget_inr=500000.0,
            baseline_crew_members=30,
            simulated_crew_members=30,
            baseline_water_cap_l=20000.0,
            simulated_water_cap_l=20000.0,
            baseline_equity_slider=0.5,
            simulated_equity_slider=0.5
        )
        self.assertEqual(sim["status"], "SUCCESS")
        deltas = sim["metric_deltas"]
        # Expanding budget from 200k to 500k should increase or maintain risk reduction
        self.assertGreaterEqual(deltas["budget_allocated_delta_inr"], 0.0)
        self.assertGreaterEqual(deltas["risk_reduction_delta_points"], 0.0)
        self.assertIn("parameter_comparison", sim)
        self.assertIn("uncertainty_ranges", sim)
        self.assertIn("tradeoff_narrative", sim)
        self.assertTrue(len(sim["tradeoff_narrative"]) > 0)

    def test_16_what_if_equity_preference_shift(self):
        """Verifies shifting equity preference redirects resources towards high-vulnerability wards."""
        sim_equity = self.engine.simulate_what_if_scenario(
            wards=self.test_wards,
            baseline_budget_inr=300000.0,
            simulated_budget_inr=300000.0,
            baseline_crew_members=25,
            simulated_crew_members=25,
            baseline_water_cap_l=20000.0,
            simulated_water_cap_l=20000.0,
            baseline_equity_slider=0.1,  # Low equity / efficiency focus
            simulated_equity_slider=0.9   # High equity / vulnerable focus
        )
        self.assertEqual(sim_equity["status"], "SUCCESS")
        self.assertIn("priority_shifts", sim_equity)
        shifts = sim_equity["priority_shifts"]
        self.assertIn("wards_gaining_resources", shifts)
        self.assertIn("tradeoff_narrative", sim_equity)

    def test_17_what_if_insufficient_resources_bottleneck(self):
        """Verifies what-if simulator handles severe resource reductions and bottleneck drops."""
        sim_bottleneck = self.engine.simulate_what_if_scenario(
            wards=self.test_wards,
            baseline_budget_inr=400000.0,
            simulated_budget_inr=15000.0,   # Slashed to barely 1 action
            baseline_crew_members=30,
            simulated_crew_members=2,       # Slashed crew
            baseline_water_cap_l=25000.0,
            simulated_water_cap_l=1000.0,
            baseline_equity_slider=0.5,
            simulated_equity_slider=0.5
        )
        self.assertEqual(sim_bottleneck["status"], "SUCCESS")
        deltas = sim_bottleneck["metric_deltas"]
        # Budget and risk reduction should drop
        self.assertLess(deltas["budget_allocated_delta_inr"], 0.0)
        self.assertLess(deltas["risk_reduction_delta_points"], 0.0)
        # Should record actions removed
        self.assertGreater(len(sim_bottleneck["intervention_changes"]["actions_removed"]), 0)

    def test_18_what_if_api_endpoint(self):
        """Verifies POST /api/interventions/simulate API endpoint returns complete comparison."""
        payload = {
            "baseline_budget_inr": 300000.0,
            "simulated_budget_inr": 450000.0,
            "baseline_crew_members": 20,
            "simulated_crew_members": 35,
            "baseline_water_cap_l": 15000.0,
            "simulated_water_cap_l": 25000.0,
            "baseline_equity_slider": 0.3,
            "simulated_equity_slider": 0.7,
            "wards": self.test_wards
        }
        r = self.client.post("/api/interventions/simulate", json=payload)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["simulation_mode"], "WHAT_IF_COMPARATIVE_ANALYSIS")
        self.assertIn("metric_deltas", data)
        self.assertIn("parameter_comparison", data)
        self.assertIn("priority_shifts", data)
        self.assertIn("uncertainty_ranges", data)
        self.assertIn("tradeoff_narrative", data)


if __name__ == "__main__":
    unittest.main()

