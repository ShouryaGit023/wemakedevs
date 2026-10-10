"""
ClimateShield - Amazon Aurora Dataset Integration Test Suite
Validates:
- Aurora connection status detection and driver mode reporting
- DDL PostgreSQL schema generation for Amazon Aurora
- Dataset export payload structure and integrity across baseline tables
- Aurora dataset synchronization verification
- FastAPI REST endpoints: /api/aurora/status, /api/aurora/schema, /api/aurora/dataset, /api/aurora/sync
"""

import sys
import os
import unittest
from fastapi.testclient import TestClient

# Ensure root directory is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.main import app
from backend.aurora_service import aurora_manager, AuroraDatasetManager


class TestAuroraIntegration(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.mgr = AuroraDatasetManager()

    def test_aurora_connection_status(self):
        status = self.mgr.get_connection_status()
        self.assertEqual(status["service"], "Amazon Aurora (PostgreSQL / Serverless v2)")
        self.assertIn("adapter_mode", status)
        self.assertIn("supported_datasets", status)
        self.assertTrue(len(status["supported_datasets"]) >= 4)
        # Verify fallback behavior when AWS RDS instance is not live
        self.assertTrue(status["fallback_active"])

    def test_aurora_ddl_schema_structure(self):
        ddl = self.mgr.get_aurora_ddl_schema()
        self.assertIn("CREATE TABLE IF NOT EXISTS wards", ddl)
        self.assertIn("CREATE TABLE IF NOT EXISTS interventions", ddl)
        self.assertIn("CREATE TABLE IF NOT EXISTS outcome_records", ddl)
        self.assertIn("CREATE TABLE IF NOT EXISTS optimization_runs", ddl)
        self.assertIn("JSONB", ddl)
        self.assertIn("idx_outcome_records_ward_date", ddl)

    def test_export_dataset_payload(self):
        payload = self.mgr.export_dataset_payload()
        self.assertEqual(payload["status"], "SUCCESS")
        self.assertEqual(payload["target_system"], "Amazon Aurora PostgreSQL")
        self.assertIn("counts", payload)
        self.assertGreater(payload["counts"]["wards"], 0)
        self.assertGreater(payload["counts"]["interventions"], 0)
        self.assertIn("wards", payload["data"])
        self.assertIn("interventions", payload["data"])

    def test_sync_dataset_to_aurora(self):
        sync_result = self.mgr.sync_dataset_to_aurora()
        self.assertIn(sync_result["status"], ["SUCCESS_AURORA_SYNCED", "SUCCESS_LOCAL_VERIFIED"])
        self.assertIn("verified_records", sync_result) if "verified_records" in sync_result else self.assertIn("records_synced", sync_result)

    def test_fastapi_aurora_status_endpoint(self):
        resp = self.client.get("/api/aurora/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["service"], "Amazon Aurora (PostgreSQL / Serverless v2)")
        self.assertIn("fallback_active", data)

    def test_fastapi_aurora_schema_endpoint(self):
        resp = self.client.get("/api/aurora/schema")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("Amazon Aurora", data["engine"])
        self.assertIn("CREATE TABLE IF NOT EXISTS wards", data["ddl"])

    def test_fastapi_aurora_dataset_endpoint(self):
        resp = self.client.get("/api/aurora/dataset")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "SUCCESS")
        self.assertGreaterEqual(data["counts"]["wards"], 10)

    def test_fastapi_aurora_sync_endpoint(self):
        resp = self.client.post("/api/aurora/sync")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("status", data)
        self.assertIn("SUCCESS", data["status"])


if __name__ == "__main__":
    unittest.main()
