"""
ClimateShield - Data Sources & Fusion Service Layer
Provides clean, high-level functions connecting external data sources (ERA5-Land, ECOSTRESS)
and the Data Fusion layer to the existing Heat, Water, Combined Risk, and Optimization engines.

CRITICAL: Does NOT modify any existing engine internals.
Safely handles missing credentials, network errors, and unobserved data with explicit quality reporting.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from backend.data_sources.cache import DataSourceCache
from backend.data_sources.era5_land import ERA5LandClient
from backend.data_sources.ecostress import ECOSTRESSClient
from backend.data_sources.fusion import DataFusionEngine

# Import existing engines without modifying them
from backend.wbgt_pipeline import calculate_outdoor_wbgt, classify_wbgt_risk
from backend.water_engine import assess_citywide_water_risk
from backend.combined_risk_engine import evaluate_combined_climate_risk
from backend.optimizer import optimize_from_combined_climate_results

logger = logging.getLogger("climateshield.data_sources.service")


class DataSourcesService:
    """
    Service integrating ERA5-Land and NASA ECOSTRESS data into ClimateShield decision pipelines.
    """

    def __init__(
        self,
        cache: Optional[DataSourceCache] = None,
        era5_client: Optional[ERA5LandClient] = None,
        ecostress_client: Optional[ECOSTRESSClient] = None,
        fusion_engine: Optional[DataFusionEngine] = None
    ):
        self.cache = cache or DataSourceCache()
        self.era5_client = era5_client or ERA5LandClient(cache=self.cache)
        self.ecostress_client = ecostress_client or ECOSTRESSClient(cache=self.cache)
        self.fusion_engine = fusion_engine or DataFusionEngine(
            era5_client=self.era5_client,
            ecostress_client=self.ecostress_client,
            cache=self.cache
        )

    async def get_era5_data(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Safely retrieves Copernicus ERA5-Land historical climate reanalysis.
        Handles missing credentials or API downtime with structured status information.
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        s_date = start_date or today
        e_date = end_date or today
        return await self.era5_client.fetch_historical_climate(s_date, e_date, force_refresh=force_refresh)

    async def get_ecostress_data(
        self,
        product_type: str = "LST",
        reference_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Safely retrieves NASA ECOSTRESS thermal infrared LST or ET observation.
        Handles orbital revisit gaps and cloud cover without fabricating data.
        """
        return await self.ecostress_client.fetch_latest_overpass(product_type=product_type, reference_date=reference_date)

    async def get_fused_ward_profiles(
        self,
        target_date: Optional[str] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Produces multi-sensor fused ward profiles across all 48 Ahmedabad wards.
        Preserves provenance, quality flags, and units while preventing zero-fabrication.
        """
        return await self.fusion_engine.fuse_climate_data_for_wards(
            target_date=target_date,
            force_refresh=force_refresh
        )

    async def evaluate_fused_heat_risk(
        self,
        target_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluates Heat Engine (wbgt_pipeline.py) across all 48 wards using fused satellite data.
        Each ward uses effective temperature incorporating ECOSTRESS LST anomalies or structural priors.
        """
        fused_result = await self.get_fused_ward_profiles(target_date=target_date)
        ward_profiles = fused_result.get("fused_ward_profiles", [])

        evaluated_wards = []
        city_wbgt_samples = []

        for wp in ward_profiles:
            heat_inputs = self.fusion_engine.to_heat_engine_format(wp)
            wbgt_val = calculate_outdoor_wbgt(
                temp_c=heat_inputs["temp_c"],
                rh_percent=heat_inputs["rh_percent"],
                direct_radiation_wm2=heat_inputs["direct_radiation_wm2"],
                wind_speed_ms=heat_inputs["wind_speed_ms"]
            )
            classification = classify_wbgt_risk(wbgt_val)
            city_wbgt_samples.append(wbgt_val)

            evaluated_wards.append({
                "ward_id": wp["ward_id"],
                "ward_name": wp["clean_name"],
                "raw_name": wp["raw_name"],
                "effective_temp_c": wp["effective_temp_c"],
                "relative_humidity_pct": wp["relative_humidity_pct"],
                "solar_radiation_wm2": wp["solar_radiation_wm2"],
                "wind_speed_ms": wp["wind_speed_ms"],
                "calculated_wbgt_c": wbgt_val,
                "hazard_tier": classification["tier"],
                "risk_color": classification["color"],
                "action_recommendation": classification["action"],
                "risk_score": classification["risk_score"],
                "uncertainty_margin_c": wp["uncertainty_margin_c"],
                "has_satellite_observation": wp["has_ecostress_observation"],
                "data_quality_confidence": wp["temperature_confidence"],
                "provenance": wp["provenance"]
            })

        avg_wbgt = round(sum(city_wbgt_samples) / max(1, len(city_wbgt_samples)), 2)

        return {
            "evaluation_engine": "ClimateShield Heat Engine (wbgt_pipeline.py)",
            "data_source": "Copernicus ERA5-Land + NASA ECOSTRESS Fused Layer",
            "target_date": fused_result.get("target_date"),
            "citywide_mean_wbgt_c": avg_wbgt,
            "total_wards_evaluated": len(evaluated_wards),
            "data_quality_report": fused_result.get("data_quality_report"),
            "wards_heat_risk": evaluated_wards
        }

    async def evaluate_fused_climate_risk(
        self,
        target_date: Optional[str] = None,
        weight_heat: float = 0.5,
        weight_water: float = 0.5,
        scoring_mode: str = "COMPOUND_SYNERGY",
        synergy_multiplier: float = 0.15
    ) -> Dict[str, Any]:
        """
        Evaluates Combined Climate Risk Engine (combined_risk_engine.py) using fused satellite data.
        Feeds fused city WBGT and 24h precipitation into the existing combined risk evaluation pipeline.
        """
        fused_heat = await self.evaluate_fused_heat_risk(target_date=target_date)
        city_fused_wbgt = fused_heat.get("citywide_mean_wbgt_c", 32.5)

        fused_profiles = await self.get_fused_ward_profiles(target_date=target_date)
        ward_profiles = fused_profiles.get("fused_ward_profiles", [])
        rain_24h = ward_profiles[0].get("rainfall_24h_mm", 0.0) if ward_profiles else 0.0
        peak_1h = ward_profiles[0].get("peak_hourly_rainfall_mm", 0.0) if ward_profiles else 0.0

        # Run Combined Risk Engine with fused meteorological parameters
        combined_results = await evaluate_combined_climate_risk(
            weight_heat=weight_heat,
            weight_water=weight_water,
            scoring_mode=scoring_mode,
            synergy_multiplier=synergy_multiplier,
            heat_wbgt_override=city_fused_wbgt,
            rainfall_24h_override=rain_24h,
            peak_hourly_override=peak_1h
        )

        # Annotate with satellite provenance and quality report
        combined_results["satellite_fusion_metadata"] = {
            "source": "Copernicus ERA5-Land + NASA ECOSTRESS Fused Layer",
            "target_date": fused_profiles.get("target_date"),
            "data_quality_report": fused_profiles.get("data_quality_report"),
            "data_sources_status": fused_profiles.get("data_sources_status")
        }

        return combined_results

    async def optimize_fused_climate_resources(
        self,
        target_date: Optional[str] = None,
        total_budget_inr: float = 500000.0,
        total_crew_members: int = 40,
        total_water_cap_l: float = 30000.0,
        equity_slider: float = 0.5,
        weight_heat: float = 0.5,
        weight_water: float = 0.5,
        scoring_mode: str = "COMPOUND_SYNERGY"
    ) -> Dict[str, Any]:
        """
        Runs the Optimizer (optimizer.py) using the fused satellite climate risk assessment.
        Ensures end-to-end integration: Satellites -> Fusion -> Risk Engine -> ILP Knapsack Optimizer.
        """
        climate_eval = await self.evaluate_fused_climate_risk(
            target_date=target_date,
            weight_heat=weight_heat,
            weight_water=weight_water,
            scoring_mode=scoring_mode
        )

        plan = optimize_from_combined_climate_results(
            combined_climate_results=climate_eval,
            total_budget_inr=total_budget_inr,
            total_crew_members=total_crew_members,
            total_water_cap_l=total_water_cap_l,
            equity_slider=equity_slider
        )

        return {
            "data_source": "Copernicus ERA5-Land + NASA ECOSTRESS Fused Layer",
            "target_date": climate_eval.get("satellite_fusion_metadata", {}).get("target_date"),
            "data_quality_report": climate_eval.get("satellite_fusion_metadata", {}).get("data_quality_report"),
            "optimization_plan": plan
        }
