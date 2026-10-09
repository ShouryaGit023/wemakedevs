"""
ClimateShield - Copernicus ERA5-Land Reanalysis Data Source
Fetches and parses historical reanalysis climate data from the Copernicus Climate Data Store (CDS).

Dataset: reanalysis-era5-land
Target Area: Ahmedabad, Gujarat, India (Bounding Box: [North: 23.3, West: 72.3, South: 22.8, East: 72.8])
Variables:
- 2 m temperature (2m_temperature) -> converted from K to °C
- 2 m dewpoint temperature (2m_dewpoint_temperature) -> converted from K to °C, used to derive Relative Humidity (%)
- Total precipitation (total_precipitation) -> converted from m to mm
- Soil water layer 1 (volumetric_soil_water_layer_1) -> m3/m3 (0-7cm)
- Surface solar radiation downwards (surface_solar_radiation_downwards) -> converted to W/m2
- 10 m wind u & v components (10m_u_component_of_wind, 10m_v_component_of_wind) -> wind speed vector magnitude (m/s)

Environment Variables Required:
- CDSAPI_KEY: Copernicus CDS API Personal Access Token / UID:API key
- CDSAPI_URL: (Optional) CDS API endpoint (default: https://cds.climate.copernicus.eu/api/v2 or https://cds-beta.climate.copernicus.eu/api/v1)
"""

import os
import math
import json
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union

import httpx

from backend.data_sources.cache import DataSourceCache

logger = logging.getLogger("climateshield.era5_land")

# Geographic Constants for Ahmedabad Bounding Box [North, West, South, East]
AHMEDABAD_BBOX = [23.3, 72.3, 22.8, 72.8]
AHMEDABAD_CENTER_LAT = 23.0225
AHMEDABAD_CENTER_LON = 72.5714

# Copernicus Dataset Name
ERA5_LAND_DATASET = "reanalysis-era5-land"

# Standard ERA5-Land Variables Mapping
ERA5_VARIABLES = [
    "2m_temperature",
    "2m_dewpoint_temperature",
    "total_precipitation",
    "volumetric_soil_water_layer_1",
    "surface_solar_radiation_downwards",
    "10m_u_component_of_wind",
    "10m_v_component_of_wind"
]


class ERA5LandClient:
    """
    Client for Copernicus ERA5-Land climate dataset retrieval and parsing.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        cache: Optional[DataSourceCache] = None
    ):
        # Read credentials from environment variables or .cdsapirc
        self.api_key = api_key or os.getenv("CDSAPI_KEY")
        self.api_url = api_url or os.getenv("CDSAPI_URL", "https://cds.climate.copernicus.eu/api/v2")
        self.cache = cache or DataSourceCache()

        # Check for ~/.cdsapirc file if env var is not set
        if not self.api_key:
            cdsapirc_path = os.path.expanduser("~/.cdsapirc")
            if os.path.exists(cdsapirc_path):
                try:
                    with open(cdsapirc_path, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.startswith("key:"):
                                self.api_key = line.split("key:", 1)[1].strip()
                            elif line.startswith("url:"):
                                self.api_url = line.split("url:", 1)[1].strip()
                except Exception as e:
                    logger.warning(f"Could not read ~/.cdsapirc: {e}")

    @property
    def is_configured(self) -> bool:
        """Returns True if CDS API credentials are provided in environment/config."""
        return bool(self.api_key)

    def build_cds_request_payload(
        self,
        start_date: Union[str, date],
        end_date: Union[str, date],
        variables: Optional[List[str]] = None,
        bbox: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Builds official CDS API request dictionary for ERA5-Land download.
        """
        if isinstance(start_date, str):
            dt_start = datetime.strptime(start_date, "%Y-%m-%d").date()
        else:
            dt_start = start_date

        if isinstance(end_date, str):
            dt_end = datetime.strptime(end_date, "%Y-%m-%d").date()
        else:
            dt_end = end_date

        vars_to_fetch = variables or ERA5_VARIABLES
        area_bbox = bbox or AHMEDABAD_BBOX

        # Generate list of years, months, days, times
        years = list(set([str((dt_start + timedelta(days=i)).year) for i in range((dt_end - dt_start).days + 1)]))
        months = list(set([f"{(dt_start + timedelta(days=i)).month:02d}" for i in range((dt_end - dt_start).days + 1)]))
        days = list(set([f"{(dt_start + timedelta(days=i)).day:02d}" for i in range((dt_end - dt_start).days + 1)]))
        times = [f"{h:02d}:00" for h in range(24)]

        return {
            "product_type": "reanalysis",
            "format": "netcdf",
            "variable": vars_to_fetch,
            "year": sorted(years),
            "month": sorted(months),
            "day": sorted(days),
            "time": times,
            "area": area_bbox,  # [North, West, South, East]
        }

    async def fetch_historical_climate(
        self,
        start_date: str,
        end_date: str,
        variables: Optional[List[str]] = None,
        bbox: Optional[List[float]] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Fetches ERA5-Land climate records for Ahmedabad.
        Uses local cache if available.
        """
        bbox_val = bbox or AHMEDABAD_BBOX
        vars_val = variables or ERA5_VARIABLES

        cache_params = {
            "start_date": start_date,
            "end_date": end_date,
            "variables": sorted(vars_val),
            "bbox": bbox_val
        }

        # Check local cache
        if not force_refresh:
            cached_data = self.cache.get("era5_land", cache_params)
            if cached_data:
                cached_data["cached"] = True
                return cached_data

        if not self.is_configured:
            # Operational status indicator when credentials are not configured
            return {
                "source": "Copernicus ERA5-Land Reanalysis",
                "status": "UNCONFIGURED_CREDENTIALS",
                "message": "Copernicus CDSAPI_KEY is not configured in environment variables. Set CDSAPI_KEY to fetch live ERA5-Land datasets.",
                "credentials_configured": False,
                "dataset": ERA5_LAND_DATASET,
                "bbox": bbox_val,
                "start_date": start_date,
                "end_date": end_date,
                "records": []
            }

        request_payload = self.build_cds_request_payload(start_date, end_date, vars_val, bbox_val)

        # Attempt download via CDS API HTTP endpoint or Python cdsapi library
        try:
            download_result = await self._execute_cds_http_request(request_payload)
            parsed = self.parse_era5_payload(download_result, start_date, end_date)
            parsed["cached"] = False
            self.cache.set("era5_land", cache_params, parsed, ttl_seconds=86400 * 7)
            return parsed
        except Exception as e:
            logger.error(f"Failed to fetch ERA5-Land data from CDS API: {e}")
            return {
                "source": "Copernicus ERA5-Land Reanalysis",
                "status": "API_ERROR",
                "message": f"Error contacting Copernicus CDS API: {str(e)}",
                "credentials_configured": True,
                "dataset": ERA5_LAND_DATASET,
                "bbox": bbox_val,
                "start_date": start_date,
                "end_date": end_date,
                "records": []
            }

    async def _execute_cds_http_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Submits request to Copernicus Climate Data Store REST API.
        """
        # CDS API auth header format: Basic auth or Bearer/Key depending on API v2/v1
        auth_header = {"Authorization": f"Bearer {self.api_key}"} if not ":" in self.api_key else None
        auth = tuple(self.api_key.split(":", 1)) if ":" in self.api_key else None

        url = f"{self.api_url.rstrip('/')}/resources/{ERA5_LAND_DATASET}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=auth_header, auth=auth)
            resp.raise_for_status()
            res_data = resp.json()
            return res_data

    def parse_era5_payload(
        self,
        raw_payload: Dict[str, Any],
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        Parses raw ERA5 payload into structured records with converted physical units.
        """
        # If payload contains direct time series or parsed data structure
        records = []
        if "records" in raw_payload:
            records = raw_payload["records"]
        elif "hourly" in raw_payload:
            # Format standard hourly arrays
            hourly = raw_payload["hourly"]
            times = hourly.get("time", [])
            t2m = hourly.get("temperature_2m", hourly.get("2m_temperature", []))
            d2m = hourly.get("dewpoint_temperature_2m", hourly.get("2m_dewpoint_temperature", []))
            tp = hourly.get("total_precipitation", [])
            swvl1 = hourly.get("volumetric_soil_water_layer_1", [])
            ssrd = hourly.get("surface_solar_radiation_downwards", [])
            u10 = hourly.get("10m_u_component_of_wind", [])
            v10 = hourly.get("10m_v_component_of_wind", [])

            for i in range(len(times)):
                temp_k = t2m[i] if i < len(t2m) and t2m[i] is not None else 303.15
                dew_k = d2m[i] if i < len(d2m) and d2m[i] is not None else 295.15

                # Unit Conversions
                temp_c = temp_k - 273.15 if temp_k > 200 else temp_k
                dew_c = dew_k - 273.15 if dew_k > 200 else dew_k
                rh = self.calculate_relative_humidity(temp_c, dew_c)

                precip_m = tp[i] if i < len(tp) and tp[i] is not None else 0.0
                precip_mm = precip_m * 1000.0 if precip_m < 10.0 else precip_m

                soil_moisture = swvl1[i] if i < len(swvl1) and swvl1[i] is not None else 0.25

                solar_j = ssrd[i] if i < len(ssrd) and ssrd[i] is not None else 0.0
                # Joules/m2 to W/m2 (hourly accumulation)
                solar_wm2 = solar_j / 3600.0 if solar_j > 1000.0 else solar_j

                u = u10[i] if i < len(u10) and u10[i] is not None else 0.0
                v = v10[i] if i < len(v10) and v10[i] is not None else 0.0
                wind_speed = math.sqrt(u ** 2 + v ** 2)

                records.append({
                    "timestamp": times[i],
                    "temperature_c": round(temp_c, 2),
                    "dewpoint_c": round(dew_c, 2),
                    "relative_humidity_pct": round(rh, 1),
                    "precipitation_mm": round(precip_mm, 2),
                    "soil_moisture_m3m3": round(soil_moisture, 3),
                    "solar_radiation_wm2": round(solar_wm2, 1),
                    "wind_speed_ms": round(wind_speed, 2)
                })

        return {
            "source": "Copernicus ERA5-Land Reanalysis",
            "status": "SUCCESS",
            "credentials_configured": True,
            "dataset": ERA5_LAND_DATASET,
            "bbox": AHMEDABAD_BBOX,
            "start_date": start_date,
            "end_date": end_date,
            "total_records": len(records),
            "records": records
        }

    @staticmethod
    def calculate_relative_humidity(temp_c: float, dewpoint_c: float) -> float:
        """Calculates relative humidity (%) from dry-bulb temp and dewpoint using August-Roche-Magnus equation."""
        e = 6.112 * math.exp((17.67 * dewpoint_c) / (dewpoint_c + 243.5))
        es = 6.112 * math.exp((17.67 * temp_c) / (temp_c + 243.5))
        rh = (e / es) * 100.0
        return max(0.0, min(100.0, rh))

    @staticmethod
    def to_wbgt_input(record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formats ERA5 record into exact dictionary needed by Heat Engine (wbgt_pipeline.py).
        """
        return {
            "temp_c": record.get("temperature_c", 30.0),
            "rh_percent": record.get("relative_humidity_pct", 50.0),
            "direct_radiation_wm2": record.get("solar_radiation_wm2", 0.0),
            "wind_speed_ms": record.get("wind_speed_ms", 1.0)
        }

    @staticmethod
    def to_waterlogging_input(records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Formats ERA5 records into exact precipitation parameters needed by Water Engine (water_engine.py).
        """
        if not records:
            return {
                "rainfall_24h_mm": 0.0,
                "peak_hourly_rainfall_mm": 0.0,
                "soil_moisture_m3m3": 0.25
            }

        precip_vals = [r.get("precipitation_mm", 0.0) for r in records[:24]]
        soil_vals = [r.get("soil_moisture_m3m3", 0.25) for r in records[:24]]

        return {
            "rainfall_24h_mm": round(sum(precip_vals), 2),
            "peak_hourly_rainfall_mm": round(max(precip_vals) if precip_vals else 0.0, 2),
            "soil_moisture_m3m3": round(sum(soil_vals) / len(soil_vals) if soil_vals else 0.25, 3)
        }
