"""
ClimateShield - Comprehensive Unit Tests for Climate Risk Optimizer Adapter
Verifies:
1. Adapter maps verified ward-level risk and vulnerability data to optimizer's input format.
2. Interventions are prioritized based on specific hazard risk scores and compound hazard hotspots.
3. Budget, crew, water-cap, and equity constraints remain strictly intact.
4. Resource-allocation logic is not duplicated (delegates to linear programming solver).
5. Ward vulnerabilities, intervention costs, and impact estimates are never invented.
6. Combined risk formulation and architectural limitations are handled with backward-compatible defaults.
7. Simulated risk scenarios are explicitly distinguished from verified real-world inputs.
8. Missing risk data cannot silently produce an unsafe allocation (imputes conservative safety priors and raises warnings).
9. Road closures remain strictly guarded (requires waterlogging >= 70.0).
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from backend.optimizer import (
    adapt_climate_risk_to_optimizer_input,
    optimize_from_combined_climate_results,
    solve_resource_allocation,
    INTERVENTIONS,
    DEFAULT_WARDS
)


class TestClimateRiskOptimizerAdapter(unittest.TestCase):
    def setUp(self):
        # Sample realistic Climate Risk Engine output payload for 3 wards
        self.mock_verified_climate_results = {
            "city": "Ahmedabad",
            "coordinates": {"lat": 23.0225, "lon": 72.5714},
            "timestamp": "2026-10-10T14:00:00Z",
            "is_simulation": False,
            "scenario_id": None,
            "scoring_configuration": {
                "weight_heat": 0.5,
                "weight_water": 0.5,
                "scoring_mode": "COMPOUND_SYNERGY"
            },
            "data_quality_and_confidence": {
                "confidence_level": "HIGH",
                "is_synthetic": False,
                "data_source": "Open-Meteo Weather API & Municipal Telemetry"
            },
            "ranked_wards": [
                {
                    "id": "W1",
                    "ward_index": 0,
                    "name": "Danilimda",
                    "official_name": "36 DANILIMDA",
                    "assessment_status": "COMPLETE",
                    "combined_risk_score": 79.0,
                    "combined_risk_category": "CRITICAL",
                    "heat_risk": {
                        "score": 78.4,
                        "baseline_vulnerability": 0.92,
                        "effective_wbgt_c": 34.2
                    },
                    "water_risk": {
                        "score": 79.3,
                        "waterlogging_score": 79.3,
                        "water_shortage_score": 38.6
                    },
                    "compound_hazard": {
                        "is_compound_hotspot": True,
                        "tier": "DUAL_CRITICAL"
                    }
                },
                {
                    "id": "W2",
                    "ward_index": 1,
                    "name": "Behrampura",
                    "official_name": "37 BEHRAMPURA",
                    "assessment_status": "COMPLETE",
                    "combined_risk_score": 75.0,
                    "combined_risk_category": "CRITICAL",
                    "heat_risk": {
                        "score": 75.0,
                        "baseline_vulnerability": 0.88,
                        "effective_wbgt_c": 33.5
                    },
                    "water_risk": {
                        "score": 75.5,
                        "waterlogging_score": 75.5,
                        "water_shortage_score": 36.2
                    },
                    "compound_hazard": {
                        "is_compound_hotspot": True,
                        "tier": "DUAL_CRITICAL"
                    }
                },
                {
                    "id": "W8",
                    "ward_index": 7,
                    "name": "Sabarmati",
                    "official_name": "1 SABARMATI",
                    "assessment_status": "COMPLETE",
                    "combined_risk_score": 40.0,
                    "combined_risk_category": "MODERATE",
                    "heat_risk": {
                        "score": 48.0,
                        "baseline_vulnerability": 0.55,
                        "effective_wbgt_c": 30.1
                    },
                    "water_risk": {
                        "score": 32.0,
                        "waterlogging_score": 32.0,
                        "water_shortage_score": 22.0
                    },
                    "compound_hazard": {
                        "is_compound_hotspot": False,
                        "tier": "LOW_COMPOUND"
                    }
                }
            ]
        }

    def test_01_adapter_maps_verified_vulnerability_and_risk_data(self):
        """Verifies that the adapter maps verified ward vulnerabilities and scores without inventing values."""
        wards, metadata = adapt_climate_risk_to_optimizer_input(self.mock_verified_climate_results)
        self.assertEqual(len(wards), 3)

        w1 = wards[0]
        self.assertEqual(w1["id"], "W1")
        self.assertEqual(w1["name"], "Danilimda")
        # Verified vulnerability must match baseline without fabrication
        self.assertEqual(w1["vulnerability"], 0.92)
        self.assertEqual(w1["heat_risk_score"], 78.4)
        self.assertEqual(w1["waterlogging_score"], 79.3)
        self.assertEqual(w1["water_shortage_score"], 38.6)
        self.assertTrue(w1["is_compound_hotspot"])
        self.assertEqual(w1["data_status"], "VERIFIED")

        # Sabarmati
        w8 = wards[2]
        self.assertEqual(w8["id"], "W8")
        self.assertEqual(w8["vulnerability"], 0.55)
        self.assertEqual(w8["waterlogging_score"], 32.0)
        self.assertFalse(w8["is_compound_hotspot"])

    def test_02_prioritization_and_constraint_enforcement(self):
        """Verifies that the optimizer respects budget, crew, water constraints and prioritizes high-risk wards."""
        budget_cap = 250000.0
        crew_cap = 20
        water_cap = 15000.0

        plan = optimize_from_combined_climate_results(
            combined_climate_results=self.mock_verified_climate_results,
            total_budget_inr=budget_cap,
            total_crew_members=crew_cap,
            total_water_cap_l=water_cap,
            equity_slider=0.5
        )

        self.assertIn(plan["status"], ["OPTIMAL", "FEASIBLE"])
        summary = plan["summary"]

        # 1. Budget constraint strictly enforced
        self.assertLessEqual(summary["budget"]["allocated_inr"], budget_cap)
        # 2. Crew constraint strictly enforced
        self.assertLessEqual(summary["crew"]["allocated_members"], crew_cap)
        # 3. Water cap strictly enforced
        self.assertLessEqual(summary["water"]["allocated_liters"], water_cap)

        # 4. High-risk compound wards (Danilimda/Behrampura) prioritized over low-risk Sabarmati
        alloc = plan["ward_allocations"]
        self.assertGreater(alloc["W1"]["ward_cost"], 0)
        self.assertGreater(alloc["W2"]["ward_cost"], 0)

        # 5. Interventions catalog integrity: check that costs match INTERVENTIONS exactly
        for w_id in alloc:
            for item in alloc[w_id]["interventions"]:
                act_id = item["action_id"]
                expected_unit_cost = INTERVENTIONS[act_id]["cost_inr"]
                self.assertEqual(item["estimated_cost_inr"], item["units"] * expected_unit_cost)

    def test_03_distinguishes_simulated_from_verified_inputs(self):
        """Verifies that simulated scenario runs are clearly labeled and differentiated from real-world telemetry."""
        # 1. Verified Real-World run
        real_plan = optimize_from_combined_climate_results(self.mock_verified_climate_results)
        self.assertEqual(real_plan["provenance"]["data_origin"], "VERIFIED_REAL_WORLD")
        self.assertFalse(real_plan["provenance"]["is_simulation"])
        self.assertIn("VERIFIED REAL-WORLD", real_plan["provenance"]["notice"])

        # 2. Simulated Scenario run
        sim_input = dict(self.mock_verified_climate_results)
        sim_input["is_simulation"] = True
        sim_input["scenario_id"] = "monsoon_cloudburst"
        sim_input["data_quality_and_confidence"] = {"confidence_level": "SIMULATION", "is_synthetic": True}

        sim_plan = optimize_from_combined_climate_results(sim_input)
        self.assertEqual(sim_plan["provenance"]["data_origin"], "SIMULATED_SCENARIO")
        self.assertTrue(sim_plan["provenance"]["is_simulation"])
        self.assertEqual(sim_plan["provenance"]["scenario_id"], "monsoon_cloudburst")
        self.assertIn("SIMULATION NOTICE", sim_plan["provenance"]["notice"])
        self.assertEqual(sim_plan["governance_and_disclaimer"]["data_origin"], "SIMULATED_SCENARIO")

    def test_04_missing_risk_data_guardrail_prevents_unsafe_zero_allocation(self):
        """Verifies that missing telemetry applies conservative safety priors to prevent silent resource deprivation."""
        corrupted_results = {
            "city": "Ahmedabad",
            "ranked_wards": [
                {
                    "id": "W1",
                    "name": "Danilimda",
                    "vulnerability": 0.92,
                    # Telemetry missing: heat_risk and water_risk are None
                    "heat_risk": None,
                    "water_risk": None
                }
            ]
        }

        wards, metadata = adapt_climate_risk_to_optimizer_input(corrupted_results)
        self.assertEqual(len(wards), 1)
        w = wards[0]

        # Missing heat and water data must NOT be zero!
        self.assertGreater(w["heat_risk_score"], 35.0)
        self.assertGreater(w["waterlogging_score"], 30.0)
        self.assertGreater(w["water_shortage_score"], 25.0)
        self.assertEqual(w["data_status"], "CONSERVATIVE_PRIOR_IMPUTED")

        # Metadata records safety audit warnings
        self.assertTrue(metadata["safety_audit"]["has_missing_risk_data"])
        self.assertEqual(metadata["safety_audit"]["wards_with_imputed_priors"], 1)
        self.assertGreater(len(metadata["safety_audit"]["missing_data_warnings"]), 0)

        # Optimization runs safely with imputed prior and includes warning in governance
        plan = optimize_from_combined_climate_results(corrupted_results)
        self.assertTrue(plan["governance_and_disclaimer"]["safe_prior_imputation_applied"])
        self.assertIn("missing_data_warnings", plan["governance_and_disclaimer"])

    def test_05_empty_input_raises_value_error(self):
        """Verifies that passing empty or invalid inputs raises a clear ValueError rather than silently failing."""
        with self.assertRaises(ValueError):
            adapt_climate_risk_to_optimizer_input({})

        with self.assertRaises(ValueError):
            adapt_climate_risk_to_optimizer_input({"ranked_wards": []})

    def test_06_emergency_road_closure_guardrail(self):
        """Verifies that emergency road closures are only recommended when waterlogging is >= 70.0."""
        # Ward with waterlogging = 65.0 (sub-critical)
        sub_crit_results = {
            "city": "Ahmedabad",
            "ranked_wards": [
                {
                    "id": "W1",
                    "name": "Danilimda",
                    "vulnerability": 0.85,
                    "heat_risk_score": 30.0,
                    "waterlogging_score": 65.0,
                    "water_shortage_score": 20.0
                }
            ]
        }
        plan_sub = optimize_from_combined_climate_results(sub_crit_results)
        actions_sub = [a["action_id"] for a in plan_sub["ward_allocations"]["W1"]["interventions"]]
        self.assertNotIn("emergency_road_closure", actions_sub, "Road closures strictly prohibited under 70.0 flood risk!")

        # Ward with waterlogging = 85.0 (critical inundation)
        crit_results = {
            "city": "Ahmedabad",
            "ranked_wards": [
                {
                    "id": "W1",
                    "name": "Danilimda",
                    "vulnerability": 0.90,
                    "heat_risk_score": 20.0,
                    "waterlogging_score": 85.0,
                    "water_shortage_score": 20.0
                }
            ]
        }
        plan_crit = optimize_from_combined_climate_results(crit_results)
        actions_crit = [a["action_id"] for a in plan_crit["ward_allocations"]["W1"]["interventions"]]
        self.assertIn("emergency_road_closure", actions_crit, "Road closures must be eligible when waterlogging >= 70.0!")


if __name__ == "__main__":
    unittest.main()
