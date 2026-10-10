"""
ClimateShield - Central Ground Water Board (CGWB) Dataset Parser
Validates, normalizes, and extracts historical groundwater level observations
from official NWIC / CGWB manual quarterly monitoring CSV datasets.

Scientific Integrity Standards:
1. Authentic Observations: Missing values are never fabricated or backfilled with invented numbers.
2. Standardized Units: Water levels represent Depth to Water Level in Metres Below Ground Level (mbgl).
3. Observation Provenance: Tagged explicitly as 'REAL_MANUAL_CGWB' with historical observation dates.
4. Geographic Boundaries: Records preserve station, tehsil, block, district, and exact GPS coordinates.
"""

import os
import csv
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple


DEFAULT_CSV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "groundwater",
    "cgwb_groundwater_raw.csv"
)


def parse_observation_date(raw_time_str: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parses CGWB 'Data Acquisition Time' string like '30-05-2022 06:00' or '10-01-2021 00:00'.
    Returns:
        (iso_date: 'YYYY-MM-DD', iso_timestamp: 'YYYY-MM-DDTHH:MM:SS', season: 'PRE_MONSOON' | 'MONSOON' | 'POST_MONSOON' | 'WINTER')
    """
    if not raw_time_str or not raw_time_str.strip():
        return None, None, None

    cleaned = raw_time_str.strip()
    
    # Supported formats: 'DD-MM-YYYY HH:MM', 'DD-MM-YYYY', 'YYYY-MM-DD'
    dt = None
    for fmt in ("%d-%m-%Y %H:%M", "%d-%m-%Y %H:%M:%S", "%d-%m-%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(cleaned, fmt)
            break
        except ValueError:
            continue

    if not dt:
        return None, None, None

    iso_date = dt.strftime("%Y-%m-%d")
    iso_timestamp = dt.strftime("%Y-%m-%dT%H:%M:%S")

    # CGWB Indian Hydrological Quarterly Seasons:
    # Jan - Feb: Post-monsoon winter / Rabi season
    # May: Pre-monsoon summer (peak water table depletion)
    # Aug: South-West Monsoon recharge
    # Nov: Post-monsoon kharif withdrawal
    month = dt.month
    if month in (4, 5, 6):
        season = "PRE_MONSOON"
    elif month in (7, 8, 9):
        season = "MONSOON"
    elif month in (10, 11):
        season = "POST_MONSOON"
    else:
        season = "WINTER_RABI"

    return iso_date, iso_timestamp, season


def parse_float_safe(value_str: Any, round_digits: Optional[int] = None) -> Optional[float]:
    """Safely parses float numbers, returning None for empty/null strings."""
    if value_str is None:
        return None
    s = str(value_str).strip()
    if not s or s in ("-", "NA", "N/A", "null", "NaN", "None"):
        return None
    try:
        val = float(s)
        return round(val, round_digits) if round_digits is not None else val
    except ValueError:
        return None


def parse_coordinate(coord_str: Any, min_val: float, max_val: float) -> Optional[float]:
    """Validates and parses latitude or longitude coordinates, preserving GPS precision."""
    val = parse_float_safe(coord_str, round_digits=6)
    if val is None:
        return None
    if min_val <= val <= max_val:
        return val
    return None


class GroundwaterParser:
    """
    Validates, deduplicates, and normalizes CGWB / NWIC groundwater observation records.
    """

    def __init__(self, file_path: Optional[str] = None):
        self.file_path = file_path or DEFAULT_CSV_PATH

    def parse(self) -> Dict[str, Any]:
        """
        Parses the target CSV file and returns validation statistics and clean normalized records.
        """
        if not os.path.exists(self.file_path):
            return {
                "success": False,
                "error": f"Groundwater CSV file not found at: {self.file_path}",
                "total_rows_read": 0,
                "valid_records_count": 0,
                "valid_records": [],
                "rejected_rows_count": 0,
                "duplicate_count": 0,
                "stations_count": 0
            }

        valid_records: List[Dict[str, Any]] = []
        seen_keys = set()
        rejected_rows = []
        duplicate_count = 0
        total_rows_read = 0

        with open(self.file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            
            # Identify columns flexibly using alias heuristics
            headers = [h.strip() for h in (reader.fieldnames or [])]
            col_id = next((h for h in headers if h.lower() in ("_id", "id", "slno")), "SlNo")
            col_station = next((h for h in headers if "station" in h.lower()), "Station")
            col_agency = next((h for h in headers if "agency" in h.lower()), "Agency")
            col_state = next((h for h in headers if h.lower() == "state"), "State")
            col_district = next((h for h in headers if h.lower() == "district"), "District")
            col_tehsil = next((h for h in headers if h.lower() in ("tehsil", "taluka")), "Tehsil")
            col_block = next((h for h in headers if h.lower() == "block"), "Block")
            col_village = next((h for h in headers if h.lower() == "village"), "Village")
            col_lat = next((h for h in headers if "latitude" in h.lower() or "lat" in h.lower()), "Latitude")
            col_lon = next((h for h in headers if "longitude" in h.lower() or "lon" in h.lower()), "Longitude")
            col_time = next((h for h in headers if "acquisition" in h.lower() or "time" in h.lower() or "date" in h.lower()), "Data Acquisition Time")
            col_gwl = next((h for h in headers if "groundwater" in h.lower() or "water level" in h.lower() or "meter" in h.lower()), "Groundwater Level Quarterly Manual (meter)")

            for line_no, row in enumerate(reader, start=2):
                total_rows_read += 1

                station_raw = row.get(col_station, "").strip()
                if not station_raw:
                    rejected_rows.append({"line": line_no, "reason": "Missing station name"})
                    continue

                time_raw = row.get(col_time, "").strip()
                iso_date, iso_timestamp, season = parse_observation_date(time_raw)
                if not iso_date:
                    rejected_rows.append({"line": line_no, "station": station_raw, "reason": f"Invalid date: '{time_raw}'"})
                    continue

                # Deduplication key: station + timestamp
                dedup_key = f"{station_raw.lower()}::{time_raw.lower()}"
                if dedup_key in seen_keys:
                    duplicate_count += 1
                    continue
                seen_keys.add(dedup_key)

                # Geographic coordinates (Gujarat bounding box: ~20.0 to ~25.0 N, ~68.0 to ~75.0 E)
                lat = parse_coordinate(row.get(col_lat), min_val=15.0, max_val=35.0)
                lon = parse_coordinate(row.get(col_lon), min_val=65.0, max_val=85.0)

                # Water Level (meters below ground level - mbgl)
                gwl_raw = row.get(col_gwl, "")
                water_level_mbgl = parse_float_safe(gwl_raw)
                has_water_level = water_level_mbgl is not None

                record = {
                    "source_row_id": int(row.get(col_id, line_no - 1)) if row.get(col_id, "").isdigit() else (line_no - 1),
                    "station_name": station_raw,
                    "agency": row.get(col_agency, "CGWB").strip() or "CGWB",
                    "state": row.get(col_state, "Gujarat").strip() or "Gujarat",
                    "district": row.get(col_district, "").strip(),
                    "tehsil": row.get(col_tehsil, "").strip(),
                    "block": row.get(col_block, "").strip(),
                    "village": row.get(col_village, "").strip(),
                    "latitude": lat,
                    "longitude": lon,
                    "observation_date": iso_date,
                    "acquisition_timestamp": iso_timestamp or f"{iso_date}T00:00:00",
                    "quarter_season": season or "UNKNOWN",
                    "water_level_mbgl": water_level_mbgl,
                    "has_water_level": has_water_level,
                    "is_historical": True,
                    "provenance": "REAL_MANUAL_CGWB"
                }

                valid_records.append(record)

        unique_stations = len(set(r["station_name"] for r in valid_records))

        return {
            "success": True,
            "file_path": self.file_path,
            "total_rows_read": total_rows_read,
            "valid_records_count": len(valid_records),
            "rejected_rows_count": len(rejected_rows),
            "duplicate_count": duplicate_count,
            "stations_count": unique_stations,
            "sample_records": valid_records[:3],
            "valid_records": valid_records,
            "rejected_samples": rejected_rows[:5]
        }
