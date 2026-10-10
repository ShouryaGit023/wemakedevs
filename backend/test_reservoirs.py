"""
ClimateShield - Unit and Integration Tests for Reservoir Storage Integration
Tests CSV import, data validation, malformed records rejection, deduplication,
stale data detection, database operations, water engine integration, and FastAPI endpoints.
"""

import unittest
import os
import tempfile
import csv
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient

from backend.data_sources.reservoir_parser import (
    ReservoirParser,
    parse_date_safe,
    parse_float_safe,
    assess_data_freshness
)
from backend.database import (
    get_db_connection,
    insert_reservoir_observations,
    get_reservoir_observations,
    get_latest_reservoir_observations,
    get_ahmedabad_bulk_reservoir_summary,
    seed_reservoir_data
)
from backend.main import app
from backend.water_engine import (
    assess_citywide_water_risk,
    calculate_water_shortage_risk,
    DEMONSTRATION_SCENARIOS
)


class TestReservoirParser(unittest.TestCase):
    """Unit tests for the CWC CSV parsing and validation engine."""

    def test_date_and_float_parsing(self):
        self.assertEqual(parse_date_safe("2026-10-01"), "2026-10-01")
        self.assertEqual(parse_date_safe("01-10-2026"), "2026-10-01")
        self.assertEqual(parse_date_safe("01/10/2026"), "2026-10-01")
        self.assertIsNone(parse_date_safe("not-a-date"))
        self.assertIsNone(parse_date_safe(""))
        self.assertIsNone(parse_date_safe("NA"))

        self.assertEqual(parse_float_safe("5.760"), 5.760)
        self.assertEqual(parse_float_safe("0.612"), 0.612)
        self.assertIsNone(parse_float_safe(""))
        self.assertIsNone(parse_float_safe("NA"))
        self.assertIsNone(parse_float_safe("-"))

    def test_stale_data_detection(self):
        today = date(2026, 10, 10)

        # 1. Fresh observation (9 days old -> within 30 days)
        is_stale, tier, age = assess_data_freshness("2026-10-01", reference_date=today, max_age_days=30)
        self.assertFalse(is_stale)
        self.assertEqual(age, 9)
        self.assertEqual(tier, "VERIFIED_OBSERVATION")

        # 2. Fresh weekly observation (3 days old -> recent weekly)
        is_stale, tier, age = assess_data_freshness("2026-10-07", reference_date=today, max_age_days=30)
        self.assertFalse(is_stale)
        self.assertEqual(tier, "RECENT_WEEKLY_BULLETIN")

        # 3. Stale / Historical observation (135 days old -> stale)
        is_stale, tier, age = assess_data_freshness("2026-05-28", reference_date=today, max_age_days=30)
        self.assertTrue(is_stale)
        self.assertEqual(tier, "HISTORICAL_STALE")
        self.assertGreater(age, 30)

        # 4. Invalid date string
        is_stale, tier, _ = assess_data_freshness("invalid-date", reference_date=today)
        self.assertTrue(is_stale)
        self.assertEqual(tier, "INVALID_DATE")

    def test_valid_and_malformed_csv_parsing(self):
        """Test with temporary CSV containing valid, missing, duplicate, and malformed rows."""
        sample_rows = [
            # Header
            ["Reservoir Name", "State", "Basin", "District", "FRL (m)", "Live Capacity at FRL (BCM)", "Current Live Storage (BCM)", "Current Storage (%)", "Observation Date", "Source"],
            # 1. Valid Sardar Sarovar
            ["Sardar Sarovar", "Gujarat", "Narmada", "Narmada", "138.68", "5.760", "5.689", "98.77", "2026-10-01", "CWC Bulletin"],
            # 2. Valid Dharoi (percentage calculated automatically)
            ["Dharoi", "Gujarat", "Sabarmati", "Mehsana", "189.59", "0.776", "0.612", "", "2026-10-01", "CWC Bulletin"],
            # 3. Duplicate row (same reservoir + date)
            ["Sardar Sarovar", "Gujarat", "Narmada", "Narmada", "138.68", "5.760", "5.689", "98.77", "2026-10-01", "CWC Bulletin"],
            # 4. Missing reservoir name (must be rejected)
            ["", "Gujarat", "Narmada", "Narmada", "138.68", "5.760", "5.000", "86.8", "2026-10-01", "CWC Bulletin"],
            # 5. Invalid date (must be rejected)
            ["Ukai", "Gujarat", "Tapi", "Tapi", "105.16", "6.615", "5.820", "87.98", "corrupt-date", "CWC Bulletin"],
            # 6. Negative storage volume (must be rejected)
            ["Kadana", "Gujarat", "Mahi", "Mahisagar", "127.71", "1.249", "-0.500", "0.0", "2026-10-01", "CWC Bulletin"],
            # 7. Negative capacity (must be rejected)
            ["Dantiwada", "Gujarat", "Banas", "Banaskantha", "184.10", "-0.404", "0.200", "50.0", "2026-10-01", "CWC Bulletin"]
        ]

        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".csv", newline="", encoding="utf-8") as tf:
            writer = csv.writer(tf)
            writer.writerows(sample_rows)
            temp_path = tf.name

        try:
            parser = ReservoirParser(temp_path, reference_date=date(2026, 10, 10))
            res = parser.parse()

            self.assertTrue(res["success"])
            self.assertEqual(res["total_rows_read"], 7)
            self.assertEqual(res["duplicate_count"], 1)
            self.assertEqual(res["rejected_rows_count"], 4)
            self.assertEqual(res["valid_records_count"], 2)

            # Check Sardar Sarovar
            sardar = next(r for r in res["valid_records"] if r["reservoir_name"] == "Sardar Sarovar")
            self.assertEqual(sardar["total_capacity_bcm"], 5.760)
            self.assertEqual(sardar["current_live_storage_bcm"], 5.689)
            self.assertEqual(sardar["storage_percentage"], 98.77)
            self.assertFalse(sardar["is_live"])  # Never presented as live telemetry

            # Check Dharoi with auto-calculated percentage: (0.612 / 0.776) * 100 = 78.87%
            dharoi = next(r for r in res["valid_records"] if r["reservoir_name"] == "Dharoi")
            self.assertAlmostEqual(dharoi["storage_percentage"], 78.87, places=1)
            self.assertFalse(dharoi["is_live"])
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_missing_file_handling(self):
        parser = ReservoirParser("non_existent_reservoir_report_xyz.csv")
        res = parser.parse()
        self.assertFalse(res["success"])
        self.assertEqual(res["valid_records_count"], 0)


class TestReservoirDatabaseAndAPI(unittest.TestCase):
    """Integration tests for SQLite storage, staleness checks, and FastAPI endpoints."""

    def setUp(self):
        self.client = TestClient(app)

    def test_database_table_exists(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reservoir_observations';")
        self.assertIsNotNone(cursor.fetchone())
        conn.close()

    def test_seeded_reservoirs_present(self):
        records = get_latest_reservoir_observations()
        self.assertIsInstance(records, list)
        self.assertGreaterEqual(len(records), 2)

        names = [r["reservoir_name"] for r in records]
        self.assertIn("Sardar Sarovar", names)
        self.assertIn("Dharoi", names)

    def test_latest_reservoirs_retrieval(self):
        records = get_latest_reservoir_observations(reservoir_names=["Sardar Sarovar", "Dharoi"])
        self.assertEqual(len(records), 2)

        sardar = next(r for r in records if r["reservoir_name"] == "Sardar Sarovar")
        self.assertEqual(sardar["total_capacity_bcm"], 5.760)
        self.assertGreater(sardar["current_live_storage_bcm"], 2.0)
        self.assertEqual(sardar["is_live"], 0)  # Never presented as live

        dharoi = next(r for r in records if r["reservoir_name"] == "Dharoi")
        self.assertEqual(dharoi["total_capacity_bcm"], 0.776)
        self.assertGreater(dharoi["current_live_storage_bcm"], 0.1)
        self.assertEqual(dharoi["is_live"], 0)

    def test_ahmedabad_bulk_summary_calculation(self):
        summary = get_ahmedabad_bulk_reservoir_summary()
        self.assertEqual(summary["status"], "SUCCESS")
        self.assertEqual(summary["city"], "Ahmedabad")
        self.assertIsNotNone(summary["composite_storage_pct"])
        self.assertFalse(summary["is_live"])  # Never presented as live
        self.assertIn("reservoirs", summary)
        self.assertIn("sardar_sarovar", summary["reservoirs"])
        self.assertIn("dharoi", summary["reservoirs"])
        self.assertEqual(summary["provenance"], "OFFICIAL_CWC_BULLETIN")

    def test_stale_data_is_never_reported_as_live(self):
        # Setting max_age_days=0 forces any observation to be flagged as stale
        summary = get_ahmedabad_bulk_reservoir_summary(max_age_days=0)
        self.assertTrue(summary["is_stale"])
        self.assertEqual(summary["data_freshness"], "HISTORICAL_STALE")
        self.assertFalse(summary["is_live"])

    def test_missing_reservoir_fallback(self):
        # Querying with a non-existent reservoir name should gracefully return other or unavailable
        missing_records = get_latest_reservoir_observations(reservoir_names=["NonExistentReservoir"])
        self.assertEqual(len(missing_records), 0)

    def test_api_reservoirs_endpoint(self):
        resp = self.client.get("/api/water/reservoirs")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertGreaterEqual(data["total_reservoirs"], 2)
        names = [r["reservoir_name"] for r in data["reservoirs"]]
        self.assertIn("Sardar Sarovar", names)
        self.assertIn("Dharoi", names)

    def test_api_reservoirs_observations_history(self):
        resp = self.client.get("/api/water/reservoirs/observations?reservoir_name=Sardar+Sarovar&limit=5")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertGreater(data["count"], 0)
        first = data["observations"][0]
        self.assertEqual(first["reservoir_name"], "Sardar Sarovar")
        self.assertIn("observation_date", first)
        self.assertIn("current_live_storage_bcm", first)

    def test_api_reservoirs_summary_endpoint(self):
        resp = self.client.get("/api/water/reservoirs/summary")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["city"], "Ahmedabad")
        self.assertIsNotNone(data["composite_storage_pct"])
        self.assertFalse(data["is_live"])  # Never presented as live


class TestWaterEngineReservoirIntegration(unittest.TestCase):
    """Integration tests verifying connection between reservoir observations and water shortage risk."""

    def test_water_shortage_risk_calculation(self):
        # 1. Deficit scenario with low reservoir (25%)
        res_stressed = calculate_water_shortage_risk(supply_lpcd=80.0, reservoir_storage_pct=25.0)
        self.assertTrue(res_stressed["has_measured_reservoir_data"])
        self.assertGreater(res_stressed["contributing_factors"]["reservoir_depletion_pts"], 15.0)

        # 2. Abundant scenario with full reservoir (98%)
        res_safe = calculate_water_shortage_risk(supply_lpcd=140.0, reservoir_storage_pct=98.0)
        self.assertTrue(res_safe["has_measured_reservoir_data"])
        self.assertLess(res_safe["contributing_factors"]["reservoir_depletion_pts"], 2.0)

    def test_citywide_water_risk_uses_verified_reservoir_data(self):
        import asyncio
        data = asyncio.run(assess_citywide_water_risk())

        self.assertIn("bulk_reservoir_summary", data)
        self.assertIn("bulk_reservoir_storage_pct", data["current_water_status"])
        self.assertIsNotNone(data["current_water_status"]["bulk_reservoir_storage_pct"])
        self.assertFalse(data["current_water_status"]["bulk_reservoir_is_live"])  # Never presented as live

        # Confidence indicator includes verified reservoir bulletin
        self.assertIn("cwc_verified_bulk_reservoir_bulletin", data["data_quality"]["measured_parameters"])
        self.assertIn("Central Water Commission (CWC)", data["data_quality"]["disclaimer"])

    def test_simulation_scenarios_remain_separate_and_labelled(self):
        import asyncio
        # Run summer drought scarcity scenario
        data = asyncio.run(assess_citywide_water_risk(scenario_id="summer_drought_scarcity"))

        self.assertTrue(data["scenario"]["is_synthetic"])
        self.assertEqual(data["scenario"]["label"], "SIMULATED")
        self.assertEqual(data["scenario"]["provenance"], "SIMULATED")
        self.assertEqual(data["current_water_status"]["bulk_reservoir_provenance"], "SIMULATED")
        self.assertEqual(data["current_water_status"]["bulk_reservoir_freshness"], "SIMULATED")
        self.assertFalse(data["current_water_status"]["bulk_reservoir_is_live"])

    def test_manual_override_takes_precedence(self):
        import asyncio
        custom_pct = 42.5
        data = asyncio.run(assess_citywide_water_risk(reservoir_storage_override=custom_pct))
        self.assertEqual(data["current_water_status"]["observed_reservoir_storage_pct"], custom_pct)
        self.assertEqual(data["current_water_status"]["bulk_reservoir_storage_pct"], custom_pct)
        self.assertEqual(data["current_water_status"]["bulk_reservoir_provenance"], "USER_OVERRIDE")

    def test_groundwater_integration_preserved(self):
        # Ensure groundwater functionality remains 100% operational
        import asyncio
        data = asyncio.run(assess_citywide_water_risk())
        self.assertIn("regional_groundwater_resilience", data)
        self.assertIn("district_average_water_table_mbgl", data["current_water_status"])
        self.assertIn("groundwater_context", data["ward_water_risks"][0])


if __name__ == "__main__":
    unittest.main()
