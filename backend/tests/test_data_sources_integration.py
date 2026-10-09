"""
ClimateShield - Integration Tests for Data Sources and Data Fusion Layer
Tests end-to-end integration between external data sources (Copernicus ERA5-Land, NASA ECOSTRESS),
Data Fusion Layer, Heat Engine, Water Engine, Combined Risk Engine, and Optimizer using MOCKED external responses.
No live credentials or internet connection required.
"""

import os
import shutil
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from backend.main import app
from backend.data_sources.cache import DataSourceCache
from backend.data_sources.era5_land import ERA5LandClient
from backend.data_sources.ecostress import ECOSTRESSClient
from backend.data_sources.fusion import DataFusionEngine
from backend.data_sources.service import DataSourcesService


class TestDataSourcesIntegration(unittest.TestCase):

    def setUp(self):
        self.test_cache_dir = os.path.join(os.path.dirname(__file__), "temp_integration_cache")
        self.cache = DataSourceCache(cache_dir=self.test_cache_dir, default_ttl_seconds=3600)
        self.client = TestClient(app)

        # Reusable mocked ERA5 payload
        self.mock_era5_payload = {
            "source": "Copernicus ERA5-Land Reanalysis",
            "status": "SUCCESS",
            "credentials_configured": True,
            "dataset": "reanalysis-era5-land",
            "bbox": [23.3, 72.3, 22.8, 72.8],
            "start_date": "2026-05-15",
            "end_date": "2026-05-15",
            "total_records": 24,
            "records": [
                {
                    "timestamp": f"2026-05-15T{h:02d}:00:00Z",
                    "temperature_c": 36.5 if 10 <= h <= 16 else 28.0,
                    "dewpoint_c": 21.0,
                    "relative_humidity_pct": 42.0,
                    "precipitation_mm": 2.5 if h == 14 else 0.0,
                    "soil_moisture_m3m3": 0.25,
                    "solar_radiation_wm2": 720.0 if 10 <= h <= 16 else 0.0,
                    "wind_speed_ms": 3.2
                }
                for h in range(24)
            ]
        }

        # Reusable mocked ECOSTRESS payload with valid observation
        self.mock_ecostress_valid_payload = {
            "source": "NASA ECOSTRESS",
            "status": "SUCCESS",
            "has_valid_observation": True,
            "granule_id": "ECOSTRESS_L2_LST_MOCK_12345",
            "product_type": "LST",
            "acquisition_timestamp": "2026-05-15T08:30:00Z",
            "cloud_cover_pct": 3.2,
            "quality_flag": "PASS",
            "quality_indicator": "HIGH_CONFIDENCE",
            "data_staleness_hours": 3.5,
            "data_staleness_days": 0.15,
            "spatial_resolution": "70m x 70m",
            "ward_lst_anomalies": {
                "Danilimda": 2.8,
                "Behrampura": 2.4,
                "Asarwa": 1.5,
                "Bapunagar": 2.1,
                "Khadia": 1.8,
                "Amraiwadi": 1.9,
                "Vatva": 2.3,
                "Sabarmati": -0.8,
                "Maninagar": -0.5,
                "Naroda": 1.2
            }
        }

        # Reusable mocked ECOSTRESS unobserved payload (e.g. cloud-covered or missing orbit)
        self.mock_ecostress_missing_payload = {
            "source": "NASA ECOSTRESS",
            "status": "NO_OVERPASS_AVAILABLE",
            "message": "No cloud-free ECOSTRESS overpass recorded for Ahmedabad within last 30 days.",
            "has_valid_observation": False,
            "data_staleness_days": 30.0,
            "quality_indicator": "MISSING_OBSERVATION",
            "product_type": "LST",
            "spatial_resolution": "70m",
            "ward_lst_anomalies": {}
        }

    def tearDown(self):
        if os.path.exists(self.test_cache_dir):
            shutil.rmtree(self.test_cache_dir, ignore_errors=True)

    # -------------------------------------------------------------
    # 1. MOCKED ERA5 & ECOSTRESS EXTRACTION
    # -------------------------------------------------------------
    def test_01_era5_mocked_fetch_and_parse(self):
        era5_client = ERA5LandClient(api_key="mock_cds_key", cache=self.cache)

        # Mock direct CDS HTTP execution
        raw_mock = {
            "hourly": {
                "time": ["2026-05-15T12:00:00Z"],
                "temperature_2m": [309.65],  # 36.5°C
                "dewpoint_temperature_2m": [294.15],
                "total_precipitation": [0.010],  # 10 mm
                "volumetric_soil_water_layer_1": [0.22],
                "surface_solar_radiation_downwards": [2592000.0],  # 720 W/m2
                "10m_u_component_of_wind": [2.0],
                "10m_v_component_of_wind": [2.5]
            }
        }

        with patch.object(era5_client, "_execute_cds_http_request", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = raw_mock

            import asyncio
            loop = asyncio.new_event_loop()
            res = loop.run_until_complete(era5_client.fetch_historical_climate("2026-05-15", "2026-05-15"))
            loop.close()

            self.assertEqual(res["status"], "SUCCESS")
            self.assertEqual(len(res["records"]), 1)
            rec = res["records"][0]
            self.assertEqual(rec["temperature_c"], 36.5)
            self.assertEqual(rec["precipitation_mm"], 10.0)
            self.assertEqual(rec["solar_radiation_wm2"], 720.0)

    def test_02_ecostress_mocked_cmr_search_and_qa_filter(self):
        ecostress_client = ECOSTRESSClient(bearer_token="mock_earthdata_token", cache=self.cache)

        mock_cmr_response = {
            "feed": {
                "entry": [
                    {
                        "id": "G12345",
                        "title": "ECOSTRESS_L2_LST_CloudFree",
                        "time_start": "2026-05-15T08:30:00Z",
                        "time_end": "2026-05-15T08:35:00Z",
                        "cloud_cover": 5.0
                    },
                    {
                        "id": "G12346",
                        "title": "ECOSTRESS_L2_LST_Cloudy",
                        "time_start": "2026-05-14T08:30:00Z",
                        "time_end": "2026-05-14T08:35:00Z",
                        "cloud_cover": 85.0
                    }
                ]
            }
        }

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_cmr_response
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp

            import asyncio
            loop = asyncio.new_event_loop()
            granules = loop.run_until_complete(ecostress_client.search_granules(product_type="LST", limit=5))
            loop.close()

            self.assertEqual(len(granules), 2)
            self.assertFalse(granules[0]["is_cloud_masked"])
            self.assertEqual(granules[0]["quality_flag"], "PASS")

            self.assertTrue(granules[1]["is_cloud_masked"])
            self.assertEqual(granules[1]["quality_flag"], "CLOUD_COVER_EXCEEDED")

    # -------------------------------------------------------------
    # 2. DATA FUSION WITH MOCKED SATELLITE RESPONSES
    # -------------------------------------------------------------
    def test_03_fused_ward_profiles_with_mocked_sources(self):
        era5_client = ERA5LandClient(cache=self.cache)
        ecostress_client = ECOSTRESSClient(cache=self.cache)

        era5_client.fetch_historical_climate = AsyncMock(return_value=self.mock_era5_payload)
        ecostress_client.fetch_latest_overpass = AsyncMock(return_value=self.mock_ecostress_valid_payload)

        fusion_engine = DataFusionEngine(era5_client=era5_client, ecostress_client=ecostress_client, cache=self.cache)

        import asyncio
        loop = asyncio.new_event_loop()
        fused = loop.run_until_complete(fusion_engine.fuse_climate_data_for_wards(target_date="2026-05-15"))
        loop.close()

        self.assertEqual(fused["total_wards_fused"], 48)
        report = fused["data_quality_report"]
        self.assertGreater(report["overall_quality_score_pct"], 70.0)

        # Check Danilimda: LST anomaly is 2.8°C, macro temp is 36.5°C -> effective temp is 39.3°C
        danilimda = next(w for w in fused["fused_ward_profiles"] if "Danilimda" in w["clean_name"])
        self.assertTrue(danilimda["has_ecostress_observation"])
        self.assertEqual(danilimda["ecostress_lst_anomaly_c"], 2.8)
        self.assertEqual(danilimda["effective_temp_c"], 39.3)
        self.assertEqual(danilimda["provenance"]["ecostress"]["spatial_resolution"], "70m_x_70m")

    # -------------------------------------------------------------
    # 3. CRITICAL: NEVER TREAT MISSING ECOSTRESS AS ZERO
    # -------------------------------------------------------------
    def test_04_missing_ecostress_not_treated_as_zero_in_service(self):
        era5_client = ERA5LandClient(cache=self.cache)
        ecostress_client = ECOSTRESSClient(cache=self.cache)

        era5_client.fetch_historical_climate = AsyncMock(return_value=self.mock_era5_payload)
        ecostress_client.fetch_latest_overpass = AsyncMock(return_value=self.mock_ecostress_missing_payload)

        service = DataSourcesService(
            cache=self.cache,
            era5_client=era5_client,
            ecostress_client=ecostress_client
        )

        import asyncio
        loop = asyncio.new_event_loop()
        fused = loop.run_until_complete(service.get_fused_ward_profiles(target_date="2026-05-15"))
        loop.close()

        for w in fused["fused_ward_profiles"]:
            self.assertFalse(w["has_ecostress_observation"])
            self.assertIsNone(w["ecostress_lst_anomaly_c"], "Must NOT be 0.0!")
            self.assertIsNone(w["ecostress_lst_c"], "Must NOT be 0.0!")
            self.assertEqual(w["temperature_estimation_mode"], "STRUCTURAL_PRIOR_UNOBSERVED")
            self.assertGreater(w["uncertainty_margin_c"], 0.0, "Must assign non-zero uncertainty penalty")

    # -------------------------------------------------------------
    # 4. END-TO-END ENGINE INTEGRATION WITH FUSED DATA
    # -------------------------------------------------------------
    def test_05_fused_heat_engine_integration(self):
        era5_client = ERA5LandClient(cache=self.cache)
        ecostress_client = ECOSTRESSClient(cache=self.cache)

        era5_client.fetch_historical_climate = AsyncMock(return_value=self.mock_era5_payload)
        ecostress_client.fetch_latest_overpass = AsyncMock(return_value=self.mock_ecostress_valid_payload)

        service = DataSourcesService(
            cache=self.cache,
            era5_client=era5_client,
            ecostress_client=ecostress_client
        )

        import asyncio
        loop = asyncio.new_event_loop()
        heat_eval = loop.run_until_complete(service.evaluate_fused_heat_risk(target_date="2026-05-15"))
        loop.close()

        self.assertEqual(heat_eval["total_wards_evaluated"], 48)
        self.assertGreater(heat_eval["citywide_mean_wbgt_c"], 25.0)

        ward_sample = heat_eval["wards_heat_risk"][0]
        self.assertIn("calculated_wbgt_c", ward_sample)
        self.assertIn("hazard_tier", ward_sample)
        self.assertIn("uncertainty_margin_c", ward_sample)

    def test_06_fused_climate_risk_integration(self):
        era5_client = ERA5LandClient(cache=self.cache)
        ecostress_client = ECOSTRESSClient(cache=self.cache)

        era5_client.fetch_historical_climate = AsyncMock(return_value=self.mock_era5_payload)
        ecostress_client.fetch_latest_overpass = AsyncMock(return_value=self.mock_ecostress_valid_payload)

        service = DataSourcesService(
            cache=self.cache,
            era5_client=era5_client,
            ecostress_client=ecostress_client
        )

        import asyncio
        loop = asyncio.new_event_loop()
        climate_eval = loop.run_until_complete(service.evaluate_fused_climate_risk(
            target_date="2026-05-15",
            weight_heat=0.6,
            weight_water=0.4,
            scoring_mode="COMPOUND_SYNERGY"
        ))
        loop.close()

        self.assertEqual(climate_eval["city"], "Ahmedabad")
        self.assertEqual(climate_eval["city_wide_summary"]["total_wards_assessed"], 48)
        self.assertIn("satellite_fusion_metadata", climate_eval)
        self.assertGreater(len(climate_eval["ranked_wards"]), 0)

    def test_07_fused_optimizer_integration(self):
        era5_client = ERA5LandClient(cache=self.cache)
        ecostress_client = ECOSTRESSClient(cache=self.cache)

        era5_client.fetch_historical_climate = AsyncMock(return_value=self.mock_era5_payload)
        ecostress_client.fetch_latest_overpass = AsyncMock(return_value=self.mock_ecostress_valid_payload)

        service = DataSourcesService(
            cache=self.cache,
            era5_client=era5_client,
            ecostress_client=ecostress_client
        )

        import asyncio
        loop = asyncio.new_event_loop()
        opt_plan = loop.run_until_complete(service.optimize_fused_climate_resources(
            target_date="2026-05-15",
            total_budget_inr=600000.0,
            total_crew_members=45,
            total_water_cap_l=35000.0,
            equity_slider=0.7
        ))
        loop.close()

        plan = opt_plan["optimization_plan"]
        self.assertIn("status", plan)
        self.assertIn("ward_allocations", plan)
        self.assertIn("summary", plan)
        self.assertLessEqual(plan["summary"]["budget"]["allocated_inr"], 600000.0)


    # -------------------------------------------------------------
    # 5. FASTAPI REST ENDPOINTS INTEGRATION
    # -------------------------------------------------------------
    def test_08_fastapi_rest_endpoints_integration(self):
        # 1. Test GET /api/data-sources/era5
        resp_era5 = self.client.get("/api/data-sources/era5")
        self.assertEqual(resp_era5.status_code, 200)
        self.assertIn("source", resp_era5.json())

        # 2. Test GET /api/data-sources/ecostress
        resp_eco = self.client.get("/api/data-sources/ecostress")
        self.assertEqual(resp_eco.status_code, 200)
        self.assertIn("source", resp_eco.json())

        # 3. Test GET /api/data-sources/fusion
        resp_fusion = self.client.get("/api/data-sources/fusion")
        self.assertEqual(resp_fusion.status_code, 200)
        self.assertIn("fused_ward_profiles", resp_fusion.json())

        # 4. Test GET /api/data-sources/fused-heat-risk
        resp_heat = self.client.get("/api/data-sources/fused-heat-risk")
        self.assertEqual(resp_heat.status_code, 200)
        self.assertIn("wards_heat_risk", resp_heat.json())

        # 5. Test GET /api/data-sources/fused-climate-risk
        resp_climate = self.client.get("/api/data-sources/fused-climate-risk")
        self.assertEqual(resp_climate.status_code, 200)
        self.assertIn("ranked_wards", resp_climate.json())

        # 6. Test POST /api/data-sources/optimize-fused
        resp_opt = self.client.post("/api/data-sources/optimize-fused", json={
            "total_budget_inr": 500000.0,
            "total_crew_members": 40,
            "total_water_cap_l": 30000.0,
            "equity_slider": 0.5
        })
        self.assertEqual(resp_opt.status_code, 200)
        self.assertIn("optimization_plan", resp_opt.json())

    # -------------------------------------------------------------
    # 6. SAFETY ON UNCONFIGURED / NETWORK ERROR CONDITIONS
    # -------------------------------------------------------------
    def test_09_safety_on_unconfigured_credentials_and_network_errors(self):
        # Without credentials, ERA5 client must safely return status without unhandled exceptions
        clean_client = ERA5LandClient(api_key=None, cache=self.cache)

        import asyncio
        loop = asyncio.new_event_loop()
        res = loop.run_until_complete(clean_client.fetch_historical_climate("2026-05-15", "2026-05-15"))
        loop.close()

        self.assertEqual(res["status"], "UNCONFIGURED_CREDENTIALS")
        self.assertFalse(res["credentials_configured"])
        self.assertEqual(res["records"], [])


if __name__ == "__main__":
    unittest.main()
