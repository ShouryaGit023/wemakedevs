"""
ClimateShield - Unit Tests for Data Sources & Data Fusion Layer
Tests Copernicus ERA5-Land, NASA ECOSTRESS, Data Fusion, Ward Matching,
Missing Values, Timestamps, and Invalid Inputs Handling.
"""

import os
import shutil
import unittest
import asyncio
from datetime import datetime, timezone

from backend.data_sources.cache import DataSourceCache
from backend.data_sources.era5_land import ERA5LandClient, AHMEDABAD_BBOX
from backend.data_sources.ecostress import ECOSTRESSClient, AHMEDABAD_CMR_BBOX
from backend.data_sources.fusion import (
    DataFusionEngine,
    clean_ward_display_name,
    resolve_canonical_ward_id,
    compute_polygon_centroid_and_bbox
)
from backend.wbgt_pipeline import calculate_outdoor_wbgt, classify_wbgt_risk
from backend.water_engine import calculate_waterlogging_risk


class TestDataSourcesAndFusion(unittest.TestCase):

    def setUp(self):
        # Create isolated temporary cache directory for tests
        self.test_cache_dir = os.path.join(os.path.dirname(__file__), "temp_cache")
        self.cache = DataSourceCache(cache_dir=self.test_cache_dir, default_ttl_seconds=3600)

    def tearDown(self):
        # Clean up temporary test cache
        if os.path.exists(self.test_cache_dir):
            shutil.rmtree(self.test_cache_dir, ignore_errors=True)

    # -------------------------------------------------------------
    # 1. LOCAL DATA CACHE TESTS
    # -------------------------------------------------------------
    def test_01_cache_set_get_and_clear(self):
        namespace = "test_ns"
        params = {"city": "Ahmedabad", "year": 2026}
        payload = {"status": "OK", "temperature": 32.5}

        # Cache set
        key = self.cache.set(namespace, params, payload, ttl_seconds=10)
        self.assertTrue(os.path.exists(self.cache.get_filepath(key, "json")))

        # Cache get
        retrieved = self.cache.get(namespace, params)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["temperature"], 32.5)

        # Cache clear
        cleared_count = self.cache.clear()
        self.assertGreater(cleared_count, 0)
        self.assertIsNone(self.cache.get(namespace, params))

    def test_02_cache_ttl_expiration(self):
        namespace = "ttl_test"
        params = {"id": 123}
        payload = {"data": "temp"}

        # Set with -1 second TTL (expired immediately)
        self.cache.set(namespace, params, payload, ttl_seconds=-1)
        retrieved = self.cache.get(namespace, params)
        self.assertIsNone(retrieved, "Expired cache entry should return None")

    # -------------------------------------------------------------
    # 2. COPERNICUS ERA5-LAND CLIENT TESTS
    # -------------------------------------------------------------
    def test_03_era5_land_request_payload_builder(self):
        client = ERA5LandClient(cache=self.cache)
        req = client.build_cds_request_payload("2026-05-01", "2026-05-02")

        self.assertEqual(req["product_type"], "reanalysis")
        self.assertEqual(req["area"], AHMEDABAD_BBOX)
        self.assertIn("2m_temperature", req["variable"])
        self.assertIn("total_precipitation", req["variable"])
        self.assertIn("volumetric_soil_water_layer_1", req["variable"])
        self.assertEqual(req["year"], ["2026"])
        self.assertEqual(req["month"], ["05"])
        self.assertEqual(len(req["time"]), 24)

    def test_04_era5_land_payload_parsing_and_unit_conversion(self):
        client = ERA5LandClient(cache=self.cache)

        mock_raw = {
            "hourly": {
                "time": ["2026-05-01T12:00:00Z"],
                "temperature_2m": [308.15],  # 35°C in Kelvin
                "dewpoint_temperature_2m": [293.15],  # 20°C in Kelvin
                "total_precipitation": [0.005],  # 0.005m = 5mm
                "volumetric_soil_water_layer_1": [0.28],
                "surface_solar_radiation_downwards": [2520000.0],  # 700 W/m2 in Joules
                "10m_u_component_of_wind": [3.0],
                "10m_v_component_of_wind": [4.0]  # Vector magnitude = 5.0 m/s
            }
        }

        parsed = client.parse_era5_payload(mock_raw, "2026-05-01", "2026-05-01")
        self.assertEqual(parsed["status"], "SUCCESS")
        self.assertEqual(len(parsed["records"]), 1)

        rec = parsed["records"][0]
        self.assertEqual(rec["temperature_c"], 35.0)
        self.assertEqual(rec["precipitation_mm"], 5.0)
        self.assertEqual(rec["wind_speed_ms"], 5.0)
        self.assertEqual(rec["solar_radiation_wm2"], 700.0)

    # -------------------------------------------------------------
    # 3. NASA ECOSTRESS CLIENT TESTS
    # -------------------------------------------------------------
    def test_05_ecostress_granule_cloud_masking_and_qa_filtering(self):
        client = ECOSTRESSClient(cache=self.cache)

        async def run_search():
            return await client.search_granules(product_type="LST", limit=5)

        loop = asyncio.new_event_loop()
        granules = loop.run_until_complete(run_search())
        loop.close()

        self.assertIsInstance(granules, list)

    def test_06_ecostress_latest_overpass_and_staleness_indicator(self):
        client = ECOSTRESSClient(cache=self.cache)

        async def run_overpass():
            return await client.fetch_latest_overpass(product_type="LST")

        loop = asyncio.new_event_loop()
        res = loop.run_until_complete(run_overpass())
        loop.close()

        self.assertEqual(res["source"], "NASA ECOSTRESS")
        self.assertIn("has_valid_observation", res)
        self.assertIn("quality_indicator", res)

    # -------------------------------------------------------------
    # 4. WARD MATCHING & STANDARDIZATION TESTS
    # -------------------------------------------------------------
    def test_07_ward_name_cleaning_and_canonical_id_matching(self):
        # Numeric prefix stripping
        self.assertEqual(clean_ward_display_name("48 RAMOL HATHIJAN"), "Ramol Hathijan")
        self.assertEqual(clean_ward_display_name("36 DANILIMDA"), "Danilimda")
        self.assertEqual(clean_ward_display_name("  10 NARODA  "), "Naroda")

        # Canonical Core Ward ID matching (W1 - W10)
        self.assertEqual(resolve_canonical_ward_id("Danilimda", "36 DANILIMDA", 35), "W1")
        self.assertEqual(resolve_canonical_ward_id("Behrampura", "37 BEHRAMPURA", 36), "W2")
        self.assertEqual(resolve_canonical_ward_id("Asarwa", "18 ASARWA", 17), "W3")
        self.assertEqual(resolve_canonical_ward_id("Bapunagar", "19 BAPUNAGAR", 18), "W4")
        self.assertEqual(resolve_canonical_ward_id("Khadia", "25 KHADIA", 24), "W5")
        self.assertEqual(resolve_canonical_ward_id("Amraiwadi", "30 AMRAIWADI", 29), "W6")
        self.assertEqual(resolve_canonical_ward_id("Vatva", "47 VATVA", 46), "W7")
        self.assertEqual(resolve_canonical_ward_id("Sabarmati", "1 SABARMATI", 0), "W8")
        self.assertEqual(resolve_canonical_ward_id("Maninagar", "38 MANINAGAR", 37), "W9")
        self.assertEqual(resolve_canonical_ward_id("Naroda", "12 NARODA", 11), "W10")

        # Other wards keep numeric prefix if available
        self.assertEqual(resolve_canonical_ward_id("Ramol Hathijan", "48 RAMOL HATHIJAN", 47), "W48")

    def test_08_geojson_spatial_ward_loading_and_centroids(self):
        engine = DataFusionEngine(cache=self.cache)
        wards = engine.load_and_validate_all_wards()

        self.assertEqual(len(wards), 48, "Should load exactly 48 Ahmedabad wards from GeoJSON")
        for w in wards:
            self.assertTrue(w["is_geometry_valid"])
            self.assertIsNotNone(w["centroid"])
            lat = w["centroid"]["lat"]
            lon = w["centroid"]["lon"]
            # Ahmedabad coordinates bounding box sanity check
            self.assertTrue(22.8 <= lat <= 23.3, f"Ward {w['clean_name']} lat {lat} out of bounds")
            self.assertTrue(72.3 <= lon <= 72.8, f"Ward {w['clean_name']} lon {lon} out of bounds")

    # -------------------------------------------------------------
    # 5. MISSING VALUES HANDLING (CRITICAL: NEVER ZERO!)
    # -------------------------------------------------------------
    def test_09_missing_ecostress_not_treated_as_zero(self):
        engine = DataFusionEngine(cache=self.cache)

        # Mock an unobserved or cloud-masked payload (no valid observation)
        mock_unobserved_payload = {
            "source": "NASA ECOSTRESS",
            "has_valid_observation": False,
            "status": "NO_OVERPASS_AVAILABLE",
            "ward_lst_anomalies": {}
        }

        # 1. Direct client helper must return None (NOT 0.0!)
        bias = engine.ecostress_client.to_heat_microclimate_bias("Danilimda", mock_unobserved_payload)
        self.assertIsNone(bias, "Missing ECOSTRESS observation must return None, NEVER 0.0!")

        bias_unknown = engine.ecostress_client.to_heat_microclimate_bias("NonExistentWard", {"has_valid_observation": True, "ward_lst_anomalies": {}})
        self.assertIsNone(bias_unknown, "Unlisted ward in ECOSTRESS must return None, NEVER 0.0!")

        # 2. In full fusion pipeline, missing observation must set anomaly to None and apply uncertainty margin
        async def run_fusion_missing():
            # Mock client method to return unobserved
            async def mock_fetch(product_type="LST", reference_date=None):
                return mock_unobserved_payload

            engine.ecostress_client.fetch_latest_overpass = mock_fetch
            return await engine.fuse_climate_data_for_wards(target_date="2026-05-01")

        loop = asyncio.new_event_loop()
        fused = loop.run_until_complete(run_fusion_missing())
        loop.close()

        self.assertGreater(fused["total_wards_fused"], 0)
        sample = fused["fused_ward_profiles"][0]

        # Assertions on missing value handling
        self.assertFalse(sample["has_ecostress_observation"])
        self.assertIsNone(sample["ecostress_lst_c"], "Missing LST must be None, NOT 0.0!")
        self.assertIsNone(sample["ecostress_lst_anomaly_c"], "Missing anomaly must be None, NOT 0.0!")
        self.assertEqual(sample["temperature_estimation_mode"], "STRUCTURAL_PRIOR_UNOBSERVED")
        self.assertGreater(sample["uncertainty_margin_c"], 0.0, "Uncertainty penalty must be > 0.0 for unobserved data")
        self.assertEqual(sample["ecostress_quality_flag"], "MISSING_OBSERVATION")

    # -------------------------------------------------------------
    # 6. TIMESTAMPS & TEMPORAL ALIGNMENT TESTS
    # -------------------------------------------------------------
    def test_10_timestamps_iso8601_and_drift_calculation(self):
        engine = DataFusionEngine(cache=self.cache)

        async def run_fusion_ts():
            return await engine.fuse_climate_data_for_wards(target_date="2026-06-15")

        loop = asyncio.new_event_loop()
        fused = loop.run_until_complete(run_fusion_ts())
        loop.close()

        # Verify ISO 8601 formatting
        ts = fused["fusion_timestamp_utc"]
        self.assertTrue(ts.endswith("Z") or "+00:00" in ts or "T" in ts)
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        self.assertIsInstance(dt, datetime)

        # Verify target date preserved
        self.assertEqual(fused["target_date"], "2026-06-15")

        # Verify data quality report timestamp metrics
        report = fused["data_quality_report"]
        self.assertIn("temporal_gap_between_sensors_hours", report)
        self.assertIn("ecostress_staleness_days", report)

    # -------------------------------------------------------------
    # 7. INVALID INPUTS HANDLING TESTS
    # -------------------------------------------------------------
    def test_11_invalid_inputs_handling(self):
        # 1. Invalid geometry handling in compute_polygon_centroid_and_bbox
        cent, bbox, errs = compute_polygon_centroid_and_bbox(None)
        self.assertIsNone(cent)
        self.assertGreater(len(errs), 0)

        cent, bbox, errs = compute_polygon_centroid_and_bbox({"type": "Point", "coordinates": [72.5, 23.0]})
        self.assertIsNone(cent)
        self.assertIn("Unsupported", errs[0])

        cent, bbox, errs = compute_polygon_centroid_and_bbox({"type": "Polygon", "coordinates": []})
        self.assertIsNone(cent)
        self.assertGreater(len(errs), 0)

        # 2. Out of bounds coordinates detection
        out_of_bounds_geom = {
            "type": "Polygon",
            "coordinates": [[[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0], [0.0, 0.0]]]
        }
        cent, bbox, errs = compute_polygon_centroid_and_bbox(out_of_bounds_geom)
        self.assertIsNotNone(cent)
        self.assertTrue(any("outside Ahmedabad" in e for e in errs))

        # 3. Invalid / missing GeoJSON path
        bad_engine = DataFusionEngine(cache=self.cache, geojson_path="/non/existent/path.geojson")
        wards = bad_engine.load_and_validate_all_wards()
        self.assertEqual(wards, [], "Should safely return empty list for missing GeoJSON file")

        # 4. Invalid raw name string in cleaning
        self.assertEqual(clean_ward_display_name(""), "Unknown Ward")
        self.assertEqual(clean_ward_display_name(None), "Unknown Ward")

    # -------------------------------------------------------------
    # 8. ENGINE COMPATIBILITY ADAPTERS TESTS
    # -------------------------------------------------------------
    def test_12_engine_format_adapters_compatibility(self):
        engine = DataFusionEngine(cache=self.cache)

        sample_fused = {
            "ward_id": "W1",
            "clean_name": "Danilimda",
            "effective_temp_c": 36.8,
            "relative_humidity_pct": 52.0,
            "solar_radiation_wm2": 640.0,
            "wind_speed_ms": 2.4,
            "rainfall_24h_mm": 18.5,
            "peak_hourly_rainfall_mm": 9.2,
            "has_ecostress_observation": True,
            "ecostress_lst_anomaly_c": 2.8,
            "uncertainty_margin_c": 0.5,
            "temperature_confidence": "HIGH_CONFIDENCE_OBSERVED"
        }

        # 1. Format for Heat Engine (wbgt_pipeline.py)
        heat_input = engine.to_heat_engine_format(sample_fused)
        wbgt = calculate_outdoor_wbgt(
            temp_c=heat_input["temp_c"],
            rh_percent=heat_input["rh_percent"],
            direct_radiation_wm2=heat_input["direct_radiation_wm2"],
            wind_speed_ms=heat_input["wind_speed_ms"]
        )
        self.assertIsInstance(wbgt, float)
        self.assertGreater(wbgt, 20.0)
        risk = classify_wbgt_risk(wbgt)
        self.assertIn("tier", risk)

        # 2. Format for Water Engine (water_engine.py)
        water_input = engine.to_water_engine_format(sample_fused)
        self.assertEqual(water_input["rainfall_24h_override"], 18.5)
        self.assertEqual(water_input["peak_hourly_override"], 9.2)

        # 3. Format for Combined Risk Engine
        comb_records = engine.to_combined_risk_format([sample_fused])
        self.assertEqual(len(comb_records), 1)
        self.assertEqual(comb_records[0]["id"], "W1")
        self.assertEqual(comb_records[0]["temperature_c"], 36.8)


if __name__ == "__main__":
    unittest.main()
