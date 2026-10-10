"""
ClimateShield - Amazon Bedrock Integration Verification Test Suite
Validates the Bedrock service, fallback handling, multi-language support (English, Gujarati, Hindi),
and FastAPI /api/bedrock/advisory and /api/bedrock/status endpoints.
"""

import sys
import os
import unittest
from fastapi.testclient import TestClient

# Ensure root directory is on python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.main import app
from backend.bedrock_service import (
    generate_heat_advisory_with_bedrock,
    generate_fallback_advisory,
    _build_advisory_prompt,
    BOTO3_AVAILABLE,
    DEFAULT_BEDROCK_MODEL
)


class TestBedrockIntegration(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.sample_ward_summaries = [
            {"ward_id": "W1", "name": "Danilimda", "effective_wbgt": 33.4, "risk_category": "CRITICAL"},
            {"ward_id": "W2", "name": "Behrampura", "effective_wbgt": 32.8, "risk_category": "EXTREME"},
            {"ward_id": "W7", "name": "Vatva", "effective_wbgt": 31.9, "risk_category": "HIGH"}
        ]
        self.sample_interventions = [
            {"intervention_id": "INT-01", "intervention_type": "Hydration Kiosk", "ward_id": "W1", "quantity": 12},
            {"intervention_id": "INT-02", "intervention_type": "Cool Roof Application", "ward_id": "W2", "quantity": 30},
            {"intervention_id": "INT-03", "intervention_type": "Emergency Water Tanker", "ward_id": "W1", "quantity": 5}
        ]

    def test_prompt_construction(self):
        prompt_en = _build_advisory_prompt(
            city_name="Ahmedabad",
            max_hazard_level="CRITICAL",
            peak_wbgt=33.4,
            ward_summaries=self.sample_ward_summaries,
            allocated_interventions=self.sample_interventions,
            budget_used=500000.0,
            equity_score=0.92,
            language="en"
        )
        self.assertIn("Ahmedabad", prompt_en)
        self.assertIn("Danilimda", prompt_en)
        self.assertIn("Respond in English", prompt_en)

        prompt_gu = _build_advisory_prompt(
            city_name="Ahmedabad",
            max_hazard_level="CRITICAL",
            peak_wbgt=33.4,
            ward_summaries=self.sample_ward_summaries,
            allocated_interventions=self.sample_interventions,
            budget_used=500000.0,
            equity_score=0.92,
            language="gu"
        )
        self.assertIn("Gujarati", prompt_gu)

    def test_fallback_generator_languages(self):
        # English fallback
        en_res = generate_fallback_advisory(
            city_name="Ahmedabad",
            max_hazard_level="CRITICAL",
            peak_wbgt=33.4,
            ward_summaries=self.sample_ward_summaries,
            allocated_interventions=self.sample_interventions,
            budget_used=500000.0,
            equity_score=0.92,
            language="en"
        )
        self.assertEqual(en_res["status"], "SUCCESS_FALLBACK")
        self.assertIn("Ahmedabad", en_res["executive_summary"])
        self.assertTrue(len(en_res["priority_directives"]) >= 3)
        self.assertIn("HEAT ADVISORY", en_res["citizen_broadcast_alert"])

        # Gujarati fallback
        gu_res = generate_fallback_advisory(
            city_name="Ahmedabad",
            max_hazard_level="CRITICAL",
            peak_wbgt=33.4,
            ward_summaries=self.sample_ward_summaries,
            allocated_interventions=self.sample_interventions,
            budget_used=500000.0,
            equity_score=0.92,
            language="gu"
        )
        self.assertEqual(gu_res["language"], "gu")
        self.assertIn("અમદાવાદ", gu_res["executive_summary"])

        # Hindi fallback
        hi_res = generate_fallback_advisory(
            city_name="Ahmedabad",
            max_hazard_level="CRITICAL",
            peak_wbgt=33.4,
            ward_summaries=self.sample_ward_summaries,
            allocated_interventions=self.sample_interventions,
            budget_used=500000.0,
            equity_score=0.92,
            language="hi"
        )
        self.assertEqual(hi_res["language"], "hi")
        self.assertIn("अहमदाबाद", hi_res["executive_summary"])

    def test_fastapi_status_endpoint(self):
        resp = self.client.get("/api/bedrock/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["service"], "Amazon Bedrock")
        self.assertTrue(data["boto3_installed"])
        self.assertIn("en", data["supported_languages"])
        self.assertIn("gu", data["supported_languages"])
        self.assertIn("hi", data["supported_languages"])

    def test_fastapi_advisory_endpoint(self):
        payload = {
            "city_name": "Ahmedabad",
            "max_hazard_level": "EXTREME",
            "peak_wbgt": 32.5,
            "ward_summaries": self.sample_ward_summaries,
            "allocated_interventions": self.sample_interventions,
            "budget_used": 420000.0,
            "equity_score": 0.89,
            "target_audience": "MUNICIPAL_OFFICERS",
            "language": "en"
        }
        resp = self.client.post("/api/bedrock/advisory", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn(data["status"], ["SUCCESS", "SUCCESS_FALLBACK"])
        self.assertIn("bedrock_metadata", data)


if __name__ == "__main__":
    unittest.main()
