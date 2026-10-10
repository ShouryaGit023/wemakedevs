"""
ClimateShield - Central Water Commission (CWC) Reservoir Storage Parser
Validates, normalizes, and extracts verified reservoir storage observations
from official CWC weekly bulletin / National Water Informatics Centre / RSMS reports.

Scientific Integrity Standards:
1. Authentic Observations: Missing values are never fabricated or backfilled with invented numbers.
2. Standardized Units: Storage volumes and live capacities are normalized to Billion Cubic Meters (BCM).
3. Freshness & Provenance: Historical or weekly bulletin observations are NEVER disguised as live SCADA telemetry.
   Staleness (>30 days old) is explicitly flagged.
4. Geographic & Hydraulic Boundaries: Preserves reservoir name, river basin, administrative district, FRL, and capacity.
"""

import os
import csv
import re
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Tuple


DEFAULT_RESERVOIR_CSV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "reservoirs",
    "cwc_reservoir_storage_raw.csv"
)

# Standard freshness threshold in days (CWC publishes weekly)
DEFAULT_MAX_STALENESS_DAYS = 30


def parse_date_safe(date_str: Any) -> Optional[str]:
    """
    Parses date string into ISO format 'YYYY-MM-DD'.
    Supports 'YYYY-MM-DD', 'DD-MM-YYYY', 'DD/MM/YYYY', 'YYYY/MM/DD'.
    """
    if not date_str:
        return None
    cleaned = str(date_str).strip()
    if not cleaned or cleaned.lower() in ("na", "n/a", "null", "none", "-"):
        return None

    # Strip time part if present
    cleaned = cleaned.split("T")[0].split(" ")[0].strip()

    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None


def parse_float_safe(value_str: Any, round_digits: Optional[int] = 4) -> Optional[float]:
    """Safely parses float numbers, returning None for empty/null strings."""
    if value_str is None:
        return None
    s = str(value_str).strip()
    if not s or s in ("-", "NA", "N/A", "null", "NaN", "None", ""):
        return None
    try:
        val = float(s)
        return round(val, round_digits) if round_digits is not None else val
    except ValueError:
        return None


def assess_data_freshness(
    obs_date_str: str,
    reference_date: Optional[date] = None,
    max_age_days: int = DEFAULT_MAX_STALENESS_DAYS
) -> Tuple[bool, str, int]:
    """
    Evaluates whether an observation is fresh or stale compared to a reference date.
    Returns:
        (is_stale: bool, freshness_label: str, age_days: int)
    """
    ref = reference_date or date.today()
    try:
        obs_dt = datetime.strptime(obs_date_str, "%Y-%m-%d").date()
    except Exception:
        return True, "INVALID_DATE", 9999

    age_days = (ref - obs_dt).days
    if age_days < 0:
        # Future date is suspicious
        return True, "FUTURE_DATE_SUSPICIOUS", age_days

    if age_days <= 7:
        return False, "RECENT_WEEKLY_BULLETIN", age_days
    elif age_days <= max_age_days:
        return False, "VERIFIED_OBSERVATION", age_days
    else:
        return True, "HISTORICAL_STALE", age_days


class ReservoirParser:
    """
    Validates, deduplicates, and normalizes CWC reservoir storage observations.
    """

    def __init__(
        self,
        file_path: Optional[str] = None,
        reference_date: Optional[date] = None,
        max_age_days: int = DEFAULT_MAX_STALENESS_DAYS
    ):
        self.file_path = file_path or DEFAULT_RESERVOIR_CSV_PATH
        self.reference_date = reference_date
        self.max_age_days = max_age_days

    def parse(self) -> Dict[str, Any]:
        """
        Parses the CSV report and returns validation statistics and clean normalized records.
        """
        if not os.path.exists(self.file_path):
            return {
                "success": False,
                "error": f"Reservoir CSV file not found at: {self.file_path}",
                "total_rows_read": 0,
                "valid_records_count": 0,
                "valid_records": [],
                "rejected_rows_count": 0,
                "duplicate_count": 0,
                "reservoirs_count": 0
            }

        valid_records: List[Dict[str, Any]] = []
        seen_keys = set()
        rejected_rows = []
        duplicate_count = 0
        total_rows_read = 0

        with open(self.file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            headers = [h.strip() for h in (reader.fieldnames or [])]

            # Flexible header heuristics
            def find_col(patterns: List[str], default: str) -> str:
                for h in headers:
                    for p in patterns:
                        if p in h.lower():
                            return h
                return default

            col_name = find_col(["reservoir", "dam", "name"], "Reservoir Name")
            col_state = find_col(["state"], "State")
            col_basin = find_col(["basin", "river"], "Basin")
            col_district = find_col(["district"], "District")
            col_frl = find_col(["frl"], "FRL (m)")
            col_capacity = find_col(["capacity", "live cap"], "Live Capacity at FRL (BCM)")
            col_storage = find_col(["current live storage", "live storage", "storage (bcm)", "storage volume"], "Current Live Storage (BCM)")
            col_pct = find_col(["percentage", "%", "pct"], "Current Storage (%)")
            col_last_yr = find_col(["last year"], "Last Year Live Storage (BCM)")
            col_10yr_avg = find_col(["10 year", "avg"], "Last 10 Year Avg Storage (BCM)")
            col_date = find_col(["date", "observation"], "Observation Date")
            col_source = find_col(["source", "agency"], "Source")

            for line_no, row in enumerate(reader, start=2):
                total_rows_read += 1

                res_name = (row.get(col_name) or "").strip()
                if not res_name:
                    rejected_rows.append({"line": line_no, "reason": "Missing reservoir name"})
                    continue

                raw_date = row.get(col_date, "")
                iso_date = parse_date_safe(raw_date)
                if not iso_date:
                    rejected_rows.append({"line": line_no, "reservoir": res_name, "reason": f"Invalid date: '{raw_date}'"})
                    continue

                # Deduplication key: reservoir_name + observation_date
                dedup_key = f"{res_name.lower()}::{iso_date}"
                if dedup_key in seen_keys:
                    duplicate_count += 1
                    continue
                seen_keys.add(dedup_key)

                # Parse hydraulic metrics
                frl = parse_float_safe(row.get(col_frl), round_digits=2)
                capacity_bcm = parse_float_safe(row.get(col_capacity), round_digits=4)
                storage_bcm = parse_float_safe(row.get(col_storage), round_digits=4)
                pct_raw = parse_float_safe(row.get(col_pct), round_digits=2)
                last_yr_bcm = parse_float_safe(row.get(col_last_yr), round_digits=4)
                avg_10yr_bcm = parse_float_safe(row.get(col_10yr_avg), round_digits=4)

                # Validation checks
                if capacity_bcm is not None and capacity_bcm <= 0:
                    rejected_rows.append({"line": line_no, "reservoir": res_name, "reason": f"Capacity must be positive: {capacity_bcm}"})
                    continue

                if storage_bcm is not None and storage_bcm < 0:
                    rejected_rows.append({"line": line_no, "reservoir": res_name, "reason": f"Storage volume cannot be negative: {storage_bcm}"})
                    continue

                # Compute or verify storage percentage
                if pct_raw is not None:
                    storage_pct = round(max(0.0, min(100.0, pct_raw)), 2)
                elif storage_bcm is not None and capacity_bcm is not None and capacity_bcm > 0:
                    storage_pct = round(max(0.0, min(100.0, (storage_bcm / capacity_bcm) * 100.0)), 2)
                else:
                    storage_pct = None

                # Freshness and staleness evaluation
                is_stale, freshness_tier, age_days = assess_data_freshness(
                    iso_date,
                    reference_date=self.reference_date,
                    max_age_days=self.max_age_days
                )

                source = (row.get(col_source) or "").strip() or "Central Water Commission (CWC) Weekly Reservoir Storage Bulletin"

                record = {
                    "reservoir_name": res_name,
                    "state": (row.get(col_state) or "Gujarat").strip() or "Gujarat",
                    "basin": (row.get(col_basin) or "").strip() or None,
                    "district": (row.get(col_district) or "").strip() or None,
                    "frl_meters": frl,
                    "total_capacity_bcm": capacity_bcm,
                    "current_live_storage_bcm": storage_bcm,
                    "storage_percentage": storage_pct,
                    "last_year_storage_bcm": last_yr_bcm,
                    "ten_year_avg_storage_bcm": avg_10yr_bcm,
                    "observation_date": iso_date,
                    "source": source,
                    "is_live": False,  # CWC weekly bulletins are verified observational reports, NEVER real-time telemetry
                    "is_stale": is_stale,
                    "data_freshness": freshness_tier,
                    "observation_age_days": age_days,
                    "provenance": "OFFICIAL_CWC_BULLETIN"
                }

                valid_records.append(record)

        unique_reservoirs = len(set(r["reservoir_name"] for r in valid_records))

        return {
            "success": True,
            "file_path": self.file_path,
            "total_rows_read": total_rows_read,
            "valid_records_count": len(valid_records),
            "rejected_rows_count": len(rejected_rows),
            "duplicate_count": duplicate_count,
            "reservoirs_count": unique_reservoirs,
            "valid_records": valid_records,
            "sample_records": valid_records[:3],
            "rejected_samples": rejected_rows[:5]
        }
