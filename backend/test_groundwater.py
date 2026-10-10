"""
ClimateShield - Unit Tests for Groundwater Integration Module
Tests validation, normalization, deduplication, missing value preservation,
database operations, trend calculations, and FastAPI endpoints.
"""

import unittest
import os
import tempfile
import csv
from datetime import datetime
from fastapi.testclient import TestClient

from backend.data_sources.groundwater_parser import (
    GroundwaterParser,
    parse_observation_date,
    parse_float_safe,
    parse_coordinate
)
from backend.database import (
    get_db_connection,
    insert_groundwater_observations,
    get_groundwater_stations,
    get_groundwater_observations,
    get_groundwater_trends
)
from backend.main import app
from backend.water_engine import (
    get_ward_groundwater_context,
    assess_citywide_water_risk
)


class TestGroundwaterParser(unittest.TestCase):
    """Unit tests for the raw CSV parsing and normalization engine."""

    def test_date_parsing_and_seasons(self):
        # Pre-monsoon summer (May)
        d, ts, s = parse_observation_date("30-05-2022 06:00")
        self.assertEqual(d, "2022-05-30")
        self.assertEqual(ts, "2022-05-30T06:00:00")
        self.assertEqual(s, "PRE_MONSOON")

        # Monsoon (August)
        d, ts, s = parse_observation_date("31-08-2021 06:00")
        self.assertEqual(d, "2021-08-31")
        self.assertEqual(s, "MONSOON")

        # Post-monsoon (November)
        d, ts, s = parse_observation_date("30-11-2021 06:00")
        self.assertEqual(d, "2021-11-30")
        self.assertEqual(s, "POST_MONSOON")

        # Winter / Rabi (January)
        d, ts, s = parse_observation_date("10-01-2021 00:00")
        self.assertEqual(d, "2021-01-10")
        self.assertEqual(s, "WINTER_RABI")

        # Invalid date strings
        d_bad, ts_bad, s_bad = parse_observation_date("invalid_date_format")
        self.assertIsNone(d_bad)
        self.assertIsNone(ts_bad)
        self.assertIsNone(s_bad)

        # Empty string
        d_empty, _, _ = parse_observation_date("")
        self.assertIsNone(d_empty)

    def test_safe_float_and_coordinates(self):
        self.assertEqual(parse_float_safe("8.58"), 8.58)
        self.assertEqual(parse_float_safe("-1.04"), -1.04)  # Artesian well
        self.assertIsNone(parse_float_safe(""))
        self.assertIsNone(parse_float_safe("NA"))
        self.assertIsNone(parse_float_safe("-"))

        # Valid coordinates
        self.assertEqual(parse_coordinate("23.0225", 15.0, 35.0), 23.0225)
        self.assertEqual(parse_coordinate("72.5714", 65.0, 85.0), 72.5714)

        # Out-of-bounds coordinates
        self.assertIsNone(parse_coordinate("99.99", 15.0, 35.0))
        self.assertIsNone(parse_coordinate("corrupt_coord", 15.0, 35.0))

    def test_parser_with_sample_dataset(self):
        """Test with temporary CSV containing valid, missing, duplicate, and corrupt rows."""
        sample_rows = [
            # Header
            ["_id", "SlNo", "Station", "Agency", "State", "District", "Tehsil", "Block", "Village", "Latitude", "Longitude", "Data Acquisition Time", "Groundwater Level Quarterly Manual (meter)"],
            # 1. Valid row
            ["1", "1", "Vatwa Pz-I", "CGWB", "Gujarat", "Ahmedabad", "DASKROI", "DASKROI", "Vatwa", "22.953", "72.615", "30-08-2022 06:00", "26.29"],
            # 2. Valid duplicate (same station + time)
            ["2", "2", "Vatwa Pz-I", "CGWB", "Gujarat", "Ahmedabad", "DASKROI", "DASKROI", "Vatwa", "22.953", "72.615", "30-08-2022 06:00", "26.29"],
            # 3. Valid row with missing water level (must NOT be fabricated)
            ["3", "3", "Sola(HC)_Pz_I", "CGWB", "Gujarat", "Ahmedabad", "DASKROI", "DASKROI", "Sola", "23.081", "72.513", "30-05-2023 10:00", ""],
            # 4. Invalid date row (must be rejected)
            ["4", "4", "Bad Date Station", "CGWB", "Gujarat", "Ahmedabad", "DASKROI", "DASKROI", "Test", "23.00", "72.50", "corrupt-date", "15.0"],
            # 5. Missing station name (must be rejected)
            ["5", "5", "", "CGWB", "Gujarat", "Ahmedabad", "DASKROI", "DASKROI", "Test", "23.00", "72.50", "10-01-2021 00:00", "15.0"],
        ]

        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv", newline="", encoding="utf-8") as tf:
            writer = csv.writer(tf)
            writer.writerows(sample_rows)
            temp_path = tf.name

        try:
            parser = GroundwaterParser(temp_path)
            res = parser.parse()

            self.assertTrue(res["success"])
            self.assertEqual(res["total_rows_read"], 5)
            self.assertEqual(res["duplicate_count"], 1)
            self.assertEqual(res["rejected_rows_count"], 2)
            self.assertEqual(res["valid_records_count"], 2)

            # Check that missing water level is preserved as None (not fabricated)
            sola_rec = next(r for r in res["valid_records"] if r["station_name"] == "Sola(HC)_Pz_I")
            self.assertIsNone(sola_rec["water_level_mbgl"])
            self.assertFalse(sola_rec["has_water_level"])
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_parser_missing_file_handling(self):
        parser = GroundwaterParser("non_existent_file_path_12345.csv")
        res = parser.parse()
        self.assertFalse(res["success"])
        self.assertEqual(res["valid_records_count"], 0)


class TestGroundwaterDatabaseAndAPI(unittest.TestCase):
    """Integration tests for SQLite storage, trend analytics, and API endpoints."""

    def setUp(self):
        self.client = TestClient(app)

    def test_database_table_exists(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='groundwater_observations';")
        self.assertIsNotNone(cursor.fetchone())
        conn.close()

    def test_stations_retrieval(self):
        stations = get_groundwater_stations(district="Ahmedabad")
        self.assertIsInstance(stations, list)
        self.assertGreaterEqual(len(stations), 30)

        station_names = [s["station_name"] for s in stations]
        self.assertIn("Vatwa Pz-I", station_names)
        self.assertIn("Bopal_Pz_I", station_names)

        vatwa = next(s for s in stations if s["station_name"] == "Vatwa Pz-I")
        self.assertIsNotNone(vatwa["latitude"])
        self.assertIsNotNone(vatwa["longitude"])
        self.assertIsNotNone(vatwa["latest_water_level_mbgl"])

    def test_observations_history(self):
        obs = get_groundwater_observations(district="Ahmedabad", limit=20)
        self.assertIsInstance(obs, list)
        self.assertGreater(len(obs), 0)

        first = obs[0]
        self.assertIn("station_name", first)
        self.assertIn("observation_date", first)
        self.assertIn("quarter_season", first)
        self.assertEqual(first["provenance"], "REAL_MANUAL_CGWB")

    def test_trends_calculation(self):
        trends = get_groundwater_trends(district="Ahmedabad")
        self.assertEqual(trends["status"], "SUCCESS")
        self.assertIn("statistics", trends)
        self.assertIn("aquifer_stress_assessment", trends)
        self.assertIn("seasonal_averages_mbgl", trends)
        self.assertIn("annual_trend_series", trends)

        stats = trends["statistics"]
        self.assertGreater(stats["total_observations"], 50)
        self.assertGreater(stats["average_depth_mbgl"], 5.0)

    def test_api_stations_endpoint(self):
        resp = self.client.get("/api/water/groundwater/stations?district=Ahmedabad")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertGreater(data["total_stations"], 30)
        self.assertIsInstance(data["stations"], list)

    def test_api_observations_endpoint(self):
        resp = self.client.get("/api/water/groundwater/observations?district=Ahmedabad&limit=10")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertLessEqual(len(data["observations"]), 10)

    def test_api_trends_endpoint(self):
        resp = self.client.get("/api/water/groundwater/trends?district=Ahmedabad")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertIn("aquifer_stress_assessment", data)

    def test_api_summary_endpoint(self):
        resp = self.client.get("/api/water/groundwater/summary")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["city"], "Ahmedabad")
        self.assertIsNotNone(data["average_depth_mbgl"])

    def test_ward_groundwater_context_scientific_distinction(self):
        # 1. Ward with proximate piezometer: Vatva
        vatva_ctx = get_ward_groundwater_context("Vatva")
        self.assertTrue(vatva_ctx["has_proximate_station"])
        self.assertEqual(vatva_ctx["station_name"], "Vatwa Pz-I")
        self.assertEqual(vatva_ctx["proximity_type"], "PROXIMATE_IN_SITU_PIEZOMETER")
        self.assertIsNotNone(vatva_ctx["water_level_mbgl"])

        # 2. Ward without proximate piezometer: Behrampura
        behrampura_ctx = get_ward_groundwater_context("Behrampura")
        self.assertFalse(behrampura_ctx["has_proximate_station"])
        self.assertEqual(behrampura_ctx["proximity_type"], "DISTRICT_AQUIFER_BASELINE")
        self.assertIn("Ahmedabad district-wide", behrampura_ctx["spatial_disclaimer"])

    def test_water_risk_engine_integration(self):
        import asyncio
        data = asyncio.run(assess_citywide_water_risk())
        self.assertIn("regional_groundwater_resilience", data)
        self.assertIn("district_average_water_table_mbgl", data["current_water_status"])

        # Ensure each ward retains honest groundwater context
        for w in data["ward_water_risks"][:5]:
            self.assertIn("groundwater_context", w)
            self.assertIn("spatial_disclaimer", w["groundwater_context"])

    def test_groundwater_stress_affects_shortage_risk_score(self):
        """Proves that changing groundwater stress directly changes the numerical water shortage risk score."""
        from backend.water_engine import calculate_water_shortage_risk

        # Identical baseline parameters
        supply = 120.0
        reservoir = 85.0
        slum = 0.5
        pipe = 75.0

        # Scenario A: Shallow, resilient water table
        gw_low_stress = {
            "has_proximate_station": True,
            "station_name": "Resilient Pz-1",
            "water_level_mbgl": 4.5,
            "annual_decline_rate_m_per_year": 0.0,
            "seasonal_recharge_potential_m": 4.8,
            "aquifer_stress_tier": "SHALLOW_WATER_TABLE",
            "is_historical": True,
            "is_stale": True
        }

        # Scenario B: Severely depleted, falling aquifer
        gw_high_stress = {
            "has_proximate_station": True,
            "station_name": "Depleted Pz-2",
            "water_level_mbgl": 32.5,
            "annual_decline_rate_m_per_year": 2.1,
            "seasonal_recharge_potential_m": 0.4,
            "aquifer_stress_tier": "CRITICAL_AQUIFER_DEPLETION",
            "is_historical": True,
            "is_stale": True
        }

        res_low = calculate_water_shortage_risk(
            supply_lpcd=supply,
            reservoir_storage_pct=reservoir,
            slum_density=slum,
            pipe_coverage_pct=pipe,
            groundwater_context=gw_low_stress
        )

        res_high = calculate_water_shortage_risk(
            supply_lpcd=supply,
            reservoir_storage_pct=reservoir,
            slum_density=slum,
            pipe_coverage_pct=pipe,
            groundwater_context=gw_high_stress
        )

        # 1. Prove high stress yields strictly higher final shortage score
        self.assertGreater(
            res_high["score"],
            res_low["score"],
            f"Expected high groundwater stress score ({res_high['score']}) > low stress score ({res_low['score']})"
        )

        # 2. Prove groundwater_stress_pts is distinctly visible in contributing factors
        pts_low = res_low["contributing_factors"]["groundwater_stress_pts"]
        pts_high = res_high["contributing_factors"]["groundwater_stress_pts"]
        self.assertGreater(pts_high, pts_low)
        self.assertGreaterEqual(pts_high, 9.0)
        self.assertLessEqual(pts_low, 3.0)

        # 3. Prove other factor points remain completely identical (no confounding)
        self.assertEqual(
            res_low["contributing_factors"]["per_capita_deficit_pts"],
            res_high["contributing_factors"]["per_capita_deficit_pts"]
        )
        self.assertEqual(
            res_low["contributing_factors"]["reservoir_depletion_pts"],
            res_high["contributing_factors"]["reservoir_depletion_pts"]
        )
        self.assertEqual(
            res_low["contributing_factors"]["distribution_vulnerability_pts"],
            res_high["contributing_factors"]["distribution_vulnerability_pts"]
        )

    def test_groundwater_direction_of_change_trend_impact(self):
        """Proves that direction of change (falling table vs recovering table) affects score at equal depth."""
        from backend.water_engine import calculate_water_shortage_risk

        depth = 20.0  # Equal 20 mbgl depth

        # Declining water table (depth increasing deeper at +1.8 m/yr)
        gw_declining = {
            "has_proximate_station": True,
            "station_name": "Declining Pz",
            "water_level_mbgl": depth,
            "annual_decline_rate_m_per_year": 1.8,
            "seasonal_recharge_potential_m": 2.0,
            "aquifer_stress_tier": "HIGH_AQUIFER_STRESS"
        }

        # Recovering water table (depth decreasing / table rising at -1.2 m/yr)
        gw_recovering = {
            "has_proximate_station": True,
            "station_name": "Recovering Pz",
            "water_level_mbgl": depth,
            "annual_decline_rate_m_per_year": -1.2,
            "seasonal_recharge_potential_m": 2.0,
            "aquifer_stress_tier": "MODERATE_WATER_TABLE"
        }

        res_dec = calculate_water_shortage_risk(supply_lpcd=120.0, reservoir_storage_pct=85.0, groundwater_context=gw_declining)
        res_rec = calculate_water_shortage_risk(supply_lpcd=120.0, reservoir_storage_pct=85.0, groundwater_context=gw_recovering)

        self.assertGreater(
            res_dec["score"],
            res_rec["score"],
            "Declining water table must yield higher shortage risk than recovering water table at identical depth"
        )
        self.assertGreater(
            res_dec["contributing_factors"]["groundwater_stress_pts"],
            res_rec["contributing_factors"]["groundwater_stress_pts"]
        )

    def test_missing_groundwater_handled_safely(self):
        """Proves that missing groundwater context defaults to bounded baseline proxy and is flagged as estimate."""
        from backend.water_engine import calculate_water_shortage_risk

        res = calculate_water_shortage_risk(supply_lpcd=120.0, reservoir_storage_pct=85.0, groundwater_context=None)

        self.assertFalse(res["has_measured_groundwater_data"])
        self.assertTrue(res["is_groundwater_estimate"])
        self.assertEqual(res["groundwater_stress_details"]["evaluation_basis"], "UNOBSERVED_REGIONAL_PRIOR")
        self.assertEqual(res["contributing_factors"]["groundwater_stress_pts"], 3.0)
        self.assertTrue(0.0 <= res["score"] <= 100.0)

    def test_stale_groundwater_reported_as_historical(self):
        """Proves that historical bulletin data is tagged with staleness and never claimed as live."""
        from backend.water_engine import calculate_water_shortage_risk

        gw_ctx = {
            "has_proximate_station": True,
            "station_name": "Historical Pz-1",
            "water_level_mbgl": 22.0,
            "annual_decline_rate_m_per_year": 0.4,
            "is_stale": True,
            "is_historical": True,
            "freshness_label": "CGWB Historical Bulletin"
        }

        res = calculate_water_shortage_risk(supply_lpcd=120.0, reservoir_storage_pct=85.0, groundwater_context=gw_ctx)
        self.assertTrue(res["groundwater_stress_details"]["is_stale"])
        self.assertIn("Historical", res["groundwater_stress_details"]["freshness_label"])


if __name__ == "__main__":
    unittest.main()
