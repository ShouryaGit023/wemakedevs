"""
ClimateShield - Unit Tests for Climate Risk FastAPI Endpoints
Tests:
1. GET /api/climate-risk (Citywide combined risk assessment with query overrides)
2. GET /api/climate-risk/wards/{ward_id} (Single ward profile by canonical ID, index, or name; 404 for missing)
3. GET /api/climate-risk/rankings (Ranked wards, executive limit, compound_only filter, dual-hazard priorities)
4. Parameter validation (422 for invalid scoring modes, negative weights, out-of-range bounds)
5. Backward compatibility (/api/climate/combined-risk GET and POST)
All external meteorological and hydrological dependencies are mocked for 100% offline execution.
"""

import os
import sys
import unittest
from unittest.mock import patch, AsyncMock

# Ensure workspace root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi.testclient import TestClient
from backend.main import app

MOCK_WEATHER = {
    "latitude": 23.0225,
    "longitude": 72.5714,
    "hourly": {
        "time": [f"2026-10-10T{h:02d}:00" for h in range(24)],
        "temperature_2m": [38.0 for _ in range(24)],
        "relative_humidity_2m": [35.0 for _ in range(24)],
        "direct_normal_irradiance": [800.0 for _ in range(24)],
        "wind_speed_10m": [2.0 for _ in range(24)],
        "precipitation": [0.0 for _ in range(24)],
        "precipitation_probability": [0 for _ in range(24)]
    }
}

MOCK_WATER_CITYWIDE = {
    "city": "Ahmedabad",
    "timestamp": "2026-10-10T14:00:00Z",
    "data_source": "Mock Water Model",
    "data_quality": {
        "confidence_level": "MODERATE",
        "confidence_score_pct": 50,
        "is_synthetic": False,
        "measured_parameters": [],
        "unmeasured_parameters": ["ward_potable_supply_telemetry"]
    },
    "ward_water_risks": [
        {
            "id": f"W{i+1}",
            "ward_index": i,
            "name": f"Ward_{i+1}",
            "ward_name": f"Ward_{i+1}",
            "official_name": f"{i+1} WARD_{i+1}",
            "risk_score": 45.0 + (i % 35),
            "composite_water_risk_score": 45.0 + (i % 35),
            "risk_category": "HIGH" if (45 + i % 35) > 50 else "MODERATE",
            "risk_color": "#F97316" if (45 + i % 35) > 50 else "#F59E0B",
            "contributing_factors": {
                "waterlogging": {"score": 55.0, "category": "HIGH"},
                "water_shortage": {"score": 40.0, "category": "MODERATE"}
            }
        }
        for i in range(48)
    ]
}


class TestClimateRiskEndpoints(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    @patch("backend.climate_risk_engine.fetch_open_meteo_weather", new_callable=AsyncMock)
    @patch("backend.climate_risk_engine.assess_citywide_water_risk", new_callable=AsyncMock)
    def test_01_get_climate_risk_citywide(self, mock_water, mock_weather):
        """Tests GET /api/climate-risk returns 48 ranked wards and required metadata."""
        mock_weather.return_value = MOCK_WEATHER
        mock_water.return_value = MOCK_WATER_CITYWIDE

        resp = self.client.get("/api/climate-risk?weight_heat=0.6&weight_water=0.4&scoring_mode=COMPOUND_SYNERGY")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["city"], "Ahmedabad")
        self.assertIn("ranked_wards", data)
        self.assertEqual(len(data["ranked_wards"]), 48)
        self.assertEqual(data["scoring_configuration"]["weight_heat"], 0.6)
        self.assertEqual(data["scoring_configuration"]["weight_water"], 0.4)
        self.assertIn("source_timestamps", data)
        self.assertIn("data_quality_and_confidence", data)

        # Check sample ward fields
        top_ward = data["ranked_wards"][0]
        self.assertIn("id", top_ward)
        self.assertIn("name", top_ward)
        self.assertIn("combined_risk_score", top_ward)
        self.assertIn("heat_risk", top_ward)
        self.assertIn("water_risk", top_ward)
        self.assertIn("compound_hazard", top_ward)
        self.assertIn("ranking_rationale", top_ward)

    @patch("backend.climate_risk_engine.fetch_open_meteo_weather", new_callable=AsyncMock)
    @patch("backend.climate_risk_engine.assess_citywide_water_risk", new_callable=AsyncMock)
    def test_02_get_single_ward_by_id_and_name(self, mock_water, mock_weather):
        """Tests GET /api/climate-risk/wards/{ward_id} by canonical ID, index, and name."""
        mock_weather.return_value = MOCK_WEATHER
        mock_water.return_value = MOCK_WATER_CITYWIDE

        # Test by canonical ID 'W1'
        r_id = self.client.get("/api/climate-risk/wards/W1")
        self.assertEqual(r_id.status_code, 200)
        data_id = r_id.json()
        self.assertEqual(data_id["ward"]["id"], "W1")
        self.assertIn("heat_risk", data_id["ward"])
        self.assertIn("water_risk", data_id["ward"])

        # Test by ward index '0'
        r_idx = self.client.get("/api/climate-risk/wards/0")
        self.assertEqual(r_idx.status_code, 200)
        self.assertEqual(r_idx.json()["ward"]["ward_index"], 0)

        # Test 404 for unknown ward
        r_404 = self.client.get("/api/climate-risk/wards/non_existent_ward_9999")
        self.assertEqual(r_404.status_code, 404)
        self.assertIn("not found", r_404.json()["detail"].lower())

    @patch("backend.climate_risk_engine.fetch_open_meteo_weather", new_callable=AsyncMock)
    @patch("backend.climate_risk_engine.assess_citywide_water_risk", new_callable=AsyncMock)
    def test_03_get_rankings_with_filters(self, mock_water, mock_weather):
        """Tests GET /api/climate-risk/rankings with limit and compound_only filters."""
        mock_weather.return_value = MOCK_WEATHER
        mock_water.return_value = MOCK_WATER_CITYWIDE

        # Full rankings
        r_all = self.client.get("/api/climate-risk/rankings")
        self.assertEqual(r_all.status_code, 200)
        d_all = r_all.json()
        self.assertEqual(d_all["total_ranked_wards"], 48)
        self.assertIn("dual_hazard_priorities", d_all)

        # Limit filter (e.g. top 5 for executive brief)
        r_top5 = self.client.get("/api/climate-risk/rankings?limit=5")
        self.assertEqual(r_top5.status_code, 200)
        d_top5 = r_top5.json()
        self.assertEqual(len(d_top5["rankings"]), 5)
        self.assertEqual(d_top5["rankings"][0]["rank"], 1)

        # Compound hotspots only
        r_comp = self.client.get("/api/climate-risk/rankings?compound_only=true")
        self.assertEqual(r_comp.status_code, 200)
        d_comp = r_comp.json()
        for w in d_comp["rankings"]:
            self.assertTrue(w["compound_hazard"]["is_compound_hotspot"])

    def test_04_query_parameter_validation_errors(self):
        """Tests that invalid parameters return HTTP 422 Unprocessable Entity."""
        # Invalid scoring mode
        r_mode = self.client.get("/api/climate-risk?scoring_mode=NON_EXISTENT_MODE")
        self.assertEqual(r_mode.status_code, 422)
        self.assertIn("Invalid scoring mode", r_mode.json()["detail"])

        # Out-of-bounds weight (> 1.0)
        r_bound = self.client.get("/api/climate-risk?weight_heat=999.0")
        self.assertEqual(r_bound.status_code, 422)

        # Sum of weights equals zero
        r_zero = self.client.get("/api/climate-risk?weight_heat=0.0&weight_water=0.0")
        self.assertEqual(r_zero.status_code, 422)

        # Rankings limit out of range
        r_lim = self.client.get("/api/climate-risk/rankings?limit=999")
        self.assertEqual(r_lim.status_code, 422)

    @patch("backend.climate_risk_engine.fetch_open_meteo_weather", new_callable=AsyncMock)
    @patch("backend.climate_risk_engine.assess_citywide_water_risk", new_callable=AsyncMock)
    def test_05_backward_compatibility_endpoints(self, mock_water, mock_weather):
        """Verifies that legacy /api/climate/combined-risk GET and POST remain 100% functional."""
        mock_weather.return_value = MOCK_WEATHER
        mock_water.return_value = MOCK_WATER_CITYWIDE

        # Legacy GET endpoint
        r_get = self.client.get("/api/climate/combined-risk")
        self.assertEqual(r_get.status_code, 200)
        self.assertEqual(len(r_get.json()["ranked_wards"]), 48)

        # POST endpoint (/api/climate-risk)
        r_post = self.client.post("/api/climate-risk", json={
            "weight_heat": 0.5,
            "weight_water": 0.5,
            "scoring_mode": "COMPOUND_SYNERGY",
            "heat_wbgt": 34.0
        })
        self.assertEqual(r_post.status_code, 200)
        self.assertIn("ranked_wards", r_post.json())

        # Legacy POST endpoint (/api/climate/combined-risk)
        r_legacy_post = self.client.post("/api/climate/combined-risk", json={
            "weight_heat": 0.5,
            "weight_water": 0.5,
            "scoring_mode": "WEIGHTED_AVERAGE"
        })
        self.assertEqual(r_legacy_post.status_code, 200)


if __name__ == "__main__":
    unittest.main()
