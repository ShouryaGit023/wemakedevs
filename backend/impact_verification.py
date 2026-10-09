"""
ClimateShield - Core Impact Verification Engine
Evaluates and reports observed physical and operational changes associated with
climate interventions by comparing baseline conditions with follow-up observations.

Scientific Principles & Governance Safeguards:
=============================================
1. Non-Fabrication of Physical Metrics:
   Physical changes (e.g. temperature reductions, flood depth drop, water supplied)
   are NEVER derived or synthesized from abstract risk scores alone. They require
   real empirical observations or explicitly labeled synthetic demonstration inputs.

2. Empirical Observation Provenance:
   Every observation carries an unambiguous source classification:
     - MEASURED: Direct in-situ sensor / IoT hardware telemetry.
     - EXTERNAL_OBSERVATION: Municipal surveillance records, IMD alerts, hospital records.
     - ESTIMATED: Modeled physical proxies or satellite-derived estimates.
     - SYNTHETIC_DEMO: Synthetic demonstration data explicitly generated for
       dry-run testing when field telemetry is unavailable.

3. Attribution Caution (Correlation != Causation):
   Observational differences between baseline and follow-up windows do not prove
   counterfactual causation. Observed shifts may be influenced by synoptic weather
   transitions, diurnal solar fluctuations, rainfall cessation, or unmodeled
   concurrent municipal operations.

4. Strict Compatibility & Aggregation Rules:
   Observations are aggregated only when their indicators, measurement units,
   spatial locations, and temporal periods are compatible. Mismatched units
   or locations return explicit incompatibility statuses without silent coercion.

5. Mathematical Integrity:
   - Percentage change is calculated only when the baseline is non-zero.
     A baseline of 0.0 results in an undefined percentage change with an explicit warning.
   - Interval-scale measurements (such as degrees Celsius) are noted so that
     absolute physical differences are prioritized over percentage calculations.
   - Bidirectional indicators: Both decrease-beneficial (e.g., WBGT, flood depth)
     and increase-beneficial (e.g., water delivered, supply duration) are supported.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import math
import re
from typing import Dict, List, Any, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# CONSTANTS & ENUMS
# ---------------------------------------------------------------------------

class SourceType:
    MEASURED = "MEASURED"
    EXTERNAL_OBSERVATION = "EXTERNAL_OBSERVATION"
    ESTIMATED = "ESTIMATED"
    SYNTHETIC_DEMO = "SYNTHETIC_DEMO"


class QualityStatus:
    VERIFIED = "VERIFIED"
    PROVISIONAL = "PROVISIONAL"
    ESTIMATED = "ESTIMATED"
    SUSPECT = "SUSPECT"
    INVALID = "INVALID"
    MISSING_BASELINE = "MISSING_BASELINE"
    MISSING_FOLLOW_UP = "MISSING_FOLLOW_UP"
    INCOMPATIBLE_UNITS = "INCOMPATIBLE_UNITS"
    INCOMPATIBLE_LOCATIONS = "INCOMPATIBLE_LOCATIONS"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    SYNTHETIC_DEMO = "SYNTHETIC_DEMO"


class Direction:
    DECREASE_IS_BENEFICIAL = "DECREASE_IS_BENEFICIAL"
    INCREASE_IS_BENEFICIAL = "INCREASE_IS_BENEFICIAL"


ATTRIBUTION_DISCLAIMER = (
    "Observational before-and-after differences reflect empirical conditions during the "
    "observation windows and do not establish counterfactual causation. Observed changes "
    "may be influenced by synoptic meteorological shifts, diurnal cycles, precipitation variations, "
    "or concurrent municipal operations. Physical outcomes are never inferred from risk scores alone."
)

DEMONSTRATION_DATA_NOTICE = (
    "DEMONSTRATION ONLY: Synthetic observations were generated to evaluate verification logic. "
    "These do not represent actual field telemetry or confirmed physical interventions."
)


# ---------------------------------------------------------------------------
# INDICATOR REGISTRY & UNIT NORMALIZATION
# ---------------------------------------------------------------------------

# Unit conversion factors to canonical unit
UNIT_CONVERSION_MAP: Dict[str, Dict[str, float]] = {
    "celsius": {
        "°c": 1.0, "c": 1.0, "degc": 1.0, "celsius": 1.0
    },
    "cm": {
        "cm": 1.0, "centimeters": 1.0,
        "m": 100.0, "meters": 100.0,
        "mm": 0.1, "millimeters": 0.1
    },
    "sq_m": {
        "sq_m": 1.0, "m2": 1.0, "sqm": 1.0,
        "sq_km": 1_000_000.0, "km2": 1_000_000.0,
        "ha": 10_000.0, "hectares": 10_000.0
    },
    "hours": {
        "hours": 1.0, "hrs": 1.0, "h": 1.0, "hour": 1.0,
        "minutes": 1.0 / 60.0, "mins": 1.0 / 60.0, "min": 1.0 / 60.0,
        "days": 24.0, "d": 24.0
    },
    "liters": {
        "liters": 1.0, "l": 1.0, "ltr": 1.0, "litres": 1.0,
        "kl": 1_000.0, "kiloliters": 1_000.0,
        "m3": 1_000.0, "cubic_meters": 1_000.0
    },
    "count": {
        "count": 1.0, "number": 1.0, "cases": 1.0, "admissions": 1.0,
        "calls": 1.0, "complaints": 1.0, "trips": 1.0
    }
}


INDICATOR_REGISTRY: Dict[str, Dict[str, Any]] = {
    # --- HEAT INDICATORS ---
    "ambient_temperature": {
        "canonical_name": "ambient_temperature",
        "display_name": "Ambient Air Temperature",
        "hazard_category": "heat",
        "canonical_unit": "celsius",
        "beneficial_direction": Direction.DECREASE_IS_BENEFICIAL,
        "valid_range": (-10.0, 60.0),
        "is_interval_scale": True,
        "aliases": ["temperature", "air_temp", "temp_c", "t_ambient"]
    },
    "wbgt": {
        "canonical_name": "wbgt",
        "display_name": "Wet Bulb Globe Temperature",
        "hazard_category": "heat",
        "canonical_unit": "celsius",
        "beneficial_direction": Direction.DECREASE_IS_BENEFICIAL,
        "valid_range": (-5.0, 55.0),
        "is_interval_scale": True,
        "aliases": ["wbgt_c", "heat_index", "apparent_temperature", "wet_bulb_globe_temp"]
    },
    "surface_temperature": {
        "canonical_name": "surface_temperature",
        "display_name": "Land Surface Temperature",
        "hazard_category": "heat",
        "canonical_unit": "celsius",
        "beneficial_direction": Direction.DECREASE_IS_BENEFICIAL,
        "valid_range": (-10.0, 80.0),
        "is_interval_scale": True,
        "aliases": ["lst", "lst_c", "surface_temp", "cool_roof_temp"]
    },
    "hospital_heat_admissions": {
        "canonical_name": "hospital_heat_admissions",
        "display_name": "Hospital Heat Illness Admissions",
        "hazard_category": "heat",
        "canonical_unit": "count",
        "beneficial_direction": Direction.DECREASE_IS_BENEFICIAL,
        "valid_range": (0, 50000),
        "is_interval_scale": False,
        "aliases": ["heat_admissions", "hospital_admissions", "heatstroke_cases"]
    },
    "emergency_108_calls": {
        "canonical_name": "emergency_108_calls",
        "display_name": "108 Heat/Emergency Distress Calls",
        "hazard_category": "heat",
        "canonical_unit": "count",
        "beneficial_direction": Direction.DECREASE_IS_BENEFICIAL,
        "valid_range": (0, 100000),
        "is_interval_scale": False,
        "aliases": ["emergency_calls", "108_calls", "ems_calls"]
    },

    # --- WATERLOGGING & FLOOD INDICATORS ---
    "flood_water_depth": {
        "canonical_name": "flood_water_depth",
        "display_name": "Inundation / Flood Water Depth",
        "hazard_category": "waterlogging",
        "canonical_unit": "cm",
        "beneficial_direction": Direction.DECREASE_IS_BENEFICIAL,
        "valid_range": (0.0, 1000.0),
        "is_interval_scale": False,
        "aliases": ["water_depth", "flood_depth", "inundation_depth", "submergence_depth"]
    },
    "flooded_area": {
        "canonical_name": "flooded_area",
        "display_name": "Inundated Surface Area",
        "hazard_category": "waterlogging",
        "canonical_unit": "sq_m",
        "beneficial_direction": Direction.DECREASE_IS_BENEFICIAL,
        "valid_range": (0.0, 1e9),
        "is_interval_scale": False,
        "aliases": ["flood_extent", "submerged_area", "inundated_area"]
    },
    "waterlogging_duration": {
        "canonical_name": "waterlogging_duration",
        "display_name": "Waterlogging Submergence Duration",
        "hazard_category": "waterlogging",
        "canonical_unit": "hours",
        "beneficial_direction": Direction.DECREASE_IS_BENEFICIAL,
        "valid_range": (0.0, 720.0),
        "is_interval_scale": False,
        "aliases": ["drainage_time", "flood_duration", "submergence_hours"]
    },
    "drainage_flow_rate": {
        "canonical_name": "drainage_flow_rate",
        "display_name": "Drainage Discharge Flow Rate",
        "hazard_category": "waterlogging",
        "canonical_unit": "liters",  # Liters per second or total discharge
        "beneficial_direction": Direction.INCREASE_IS_BENEFICIAL,
        "valid_range": (0.0, 1e8),
        "is_interval_scale": False,
        "aliases": ["discharge_rate", "pump_discharge", "drainage_capacity"]
    },

    # --- WATER SHORTAGE & POTABLE SUPPLY INDICATORS ---
    "water_availability": {
        "canonical_name": "water_availability",
        "display_name": "Potable Water Volume Available",
        "hazard_category": "water_shortage",
        "canonical_unit": "liters",
        "beneficial_direction": Direction.INCREASE_IS_BENEFICIAL,
        "valid_range": (0.0, 1e9),
        "is_interval_scale": False,
        "aliases": ["water_volume", "potable_water", "storage_level"]
    },
    "supply_duration": {
        "canonical_name": "supply_duration",
        "display_name": "Piped/Supplied Water Duration",
        "hazard_category": "water_shortage",
        "canonical_unit": "hours",
        "beneficial_direction": Direction.INCREASE_IS_BENEFICIAL,
        "valid_range": (0.0, 168.0),
        "is_interval_scale": False,
        "aliases": ["piped_supply_hours", "water_supply_time", "supply_hours"]
    },
    "water_delivered": {
        "canonical_name": "water_delivered",
        "display_name": "Total Water Volume Delivered",
        "hazard_category": "water_shortage",
        "canonical_unit": "liters",
        "beneficial_direction": Direction.INCREASE_IS_BENEFICIAL,
        "valid_range": (0.0, 1e9),
        "is_interval_scale": False,
        "aliases": ["tanker_water_delivered", "volume_delivered", "liters_supplied"]
    },
    "water_scarcity_complaints": {
        "canonical_name": "water_scarcity_complaints",
        "display_name": "Civic Water Scarcity Grievance Complaints",
        "hazard_category": "water_shortage",
        "canonical_unit": "count",
        "beneficial_direction": Direction.DECREASE_IS_BENEFICIAL,
        "valid_range": (0, 100000),
        "is_interval_scale": False,
        "aliases": ["water_complaints", "scarcity_complaints", "civic_complaints"]
    },
    "tanker_trips_completed": {
        "canonical_name": "tanker_trips_completed",
        "display_name": "Emergency Tanker Trips Completed",
        "hazard_category": "water_shortage",
        "canonical_unit": "count",
        "beneficial_direction": Direction.INCREASE_IS_BENEFICIAL,
        "valid_range": (0, 10000),
        "is_interval_scale": False,
        "aliases": ["tanker_trips", "water_trips", "distribution_runs"]
    }
}


def resolve_canonical_indicator(name: str) -> Optional[str]:
    """Resolves an indicator name or alias to its canonical key."""
    if not name or not isinstance(name, str):
        return None
    cleaned = name.strip().lower().replace("-", "_").replace(" ", "_")
    if cleaned in INDICATOR_REGISTRY:
        return cleaned
    for canonical_key, info in INDICATOR_REGISTRY.items():
        if cleaned in [alias.lower() for alias in info.get("aliases", [])]:
            return canonical_key
    return None


def normalize_unit_string(unit: str) -> str:
    """Standardizes unit strings (e.g., '°C' -> 'celsius', 'm' -> 'm', etc.)."""
    if not unit or not isinstance(unit, str):
        return ""
    u = unit.strip().lower()
    if u in ["°c", "c", "degc", "degrees_celsius", "celsius"]:
        return "celsius"
    if u in ["cm", "centimeters", "centimeter"]:
        return "cm"
    if u in ["m", "meters", "meter"]:
        return "m"
    if u in ["mm", "millimeters", "millimeter"]:
        return "mm"
    if u in ["l", "liters", "litres", "ltr"]:
        return "liters"
    if u in ["kl", "kiloliters", "kilolitres"]:
        return "kl"
    if u in ["m3", "cubic_meters", "cumec"]:
        return "m3"
    if u in ["h", "hr", "hrs", "hours", "hour"]:
        return "hours"
    if u in ["min", "mins", "minutes", "minute"]:
        return "minutes"
    if u in ["count", "number", "trips", "cases", "calls", "complaints"]:
        return "count"
    return u


def convert_value_to_canonical(value: float, from_unit: str, canonical_unit: str) -> Tuple[Optional[float], bool]:
    """
    Converts a value from an input unit to the canonical unit.
    Returns (converted_value, success).
    """
    u_from = normalize_unit_string(from_unit)
    u_canon = normalize_unit_string(canonical_unit)

    if u_from == u_canon:
        return value, True

    if u_canon in UNIT_CONVERSION_MAP and u_from in UNIT_CONVERSION_MAP[u_canon]:
        factor = UNIT_CONVERSION_MAP[u_canon][u_from]
        return value * factor, True

    return None, False


# ---------------------------------------------------------------------------
# DATA STRUCTURES
# ---------------------------------------------------------------------------

@dataclass
class Observation:
    """Represents a single empirical observation or record."""
    indicator: str
    value: float
    unit: str
    timestamp: str
    period: str = "BASELINE"  # "BASELINE" or "FOLLOW_UP"
    ward_id: Optional[str] = None
    source_type: str = SourceType.MEASURED
    source_name: Optional[str] = None
    location_tag: Optional[str] = None
    quality_status: str = QualityStatus.VERIFIED
    observation_id: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ObservationAggregate:
    """Aggregated observation summary for a specific indicator and period."""
    indicator: str
    canonical_indicator: str
    period: str
    unit: str
    mean_value: float
    median_value: float
    min_value: float
    max_value: float
    observation_count: int
    timestamps: List[str]
    source_types: List[str]
    source_names: List[str]
    quality_statuses: List[str]
    is_synthetic: bool
    location_tags: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class IndicatorImpactResult:
    """Verification results for a single indicator."""
    indicator: str
    canonical_indicator: str
    hazard_category: str
    beneficial_direction: str
    baseline_value: Optional[float]
    follow_up_value: Optional[float]
    unit: Optional[str]
    difference: Optional[float]
    percentage_change: Optional[float]
    is_improvement: Optional[bool]
    improvement_magnitude: Optional[float]
    baseline_observation_count: int
    follow_up_observation_count: int
    baseline_timestamps: List[str]
    follow_up_timestamps: List[str]
    source_types: List[str]
    is_synthetic: bool
    quality_status: str
    notes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InterventionImpactAssessment:
    """Complete structured impact assessment across all evaluated indicators."""
    assessment_id: str
    intervention_id: str
    ward_id: str
    intervention_type: str
    baseline_period: Dict[str, Any]
    follow_up_period: Dict[str, Any]
    indicators_assessed: List[str]
    results_by_indicator: Dict[str, Any]
    overall_quality_status: str
    overall_is_synthetic: bool
    attribution_disclaimer: str
    summary: Dict[str, Any]
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


# ---------------------------------------------------------------------------
# VALIDATION & AGGREGATION LOGIC
# ---------------------------------------------------------------------------

def validate_observation(
    obs: Union[Observation, Dict[str, Any]]
) -> Tuple[Optional[Observation], Optional[str]]:
    """
    Validates an observation object or dict for required fields, physical bounds,
    and valid numeric values.
    Returns (normalized_observation, error_message).
    """
    if isinstance(obs, dict):
        indicator = obs.get("indicator")
        value = obs.get("value")
        unit = obs.get("unit")
        timestamp = obs.get("timestamp")
        period = (obs.get("period") or "BASELINE").strip().upper()
        ward_id = obs.get("ward_id")
        source_type = obs.get("source_type", SourceType.MEASURED)
        source_name = obs.get("source_name")
        location_tag = obs.get("location_tag")
        quality_status = obs.get("quality_status", QualityStatus.VERIFIED)
        obs_id = obs.get("observation_id")
        notes = obs.get("notes")
    elif isinstance(obs, Observation):
        indicator = obs.indicator
        value = obs.value
        unit = obs.unit
        timestamp = obs.timestamp
        period = (obs.period or "BASELINE").strip().upper()
        ward_id = obs.ward_id
        source_type = obs.source_type
        source_name = obs.source_name
        location_tag = obs.location_tag
        quality_status = obs.quality_status
        obs_id = obs.observation_id
        notes = obs.notes
    else:
        return None, "Observation must be an Observation instance or dictionary."

    # Validate essential fields
    if not indicator or not isinstance(indicator, str):
        return None, "Missing or invalid 'indicator' field."
    if value is None:
        return None, "Missing 'value' field."
    try:
        f_val = float(value)
        if math.isnan(f_val) or math.isinf(f_val):
            return None, "Observation value is NaN or Infinite."
    except (ValueError, TypeError):
        return None, f"Observation value '{value}' cannot be converted to float."

    if not unit or not isinstance(unit, str):
        return None, "Missing or invalid 'unit' field."
    if not timestamp or not isinstance(timestamp, str):
        return None, "Missing or invalid 'timestamp' field."

    if period not in ["BASELINE", "FOLLOW_UP"]:
        return None, f"Invalid period '{period}'. Must be 'BASELINE' or 'FOLLOW_UP'."

    # Resolve indicator to canonical
    canon_ind = resolve_canonical_indicator(indicator)
    if not canon_ind:
        # Unknown indicator: allowed, but canonical properties will be generic
        canon_ind = indicator.strip().lower()
        canon_unit = normalize_unit_string(unit)
        norm_val = f_val
    else:
        ind_info = INDICATOR_REGISTRY[canon_ind]
        canon_unit = ind_info["canonical_unit"]
        norm_val, success = convert_value_to_canonical(f_val, unit, canon_unit)
        if not success:
            # Cannot convert provided unit to canonical unit
            return None, f"Incompatible unit '{unit}' for indicator '{indicator}'. Expected convertible to '{canon_unit}'."

        # Physical bound validation
        valid_min, valid_max = ind_info["valid_range"]
        if norm_val < valid_min or norm_val > valid_max:
            return None, (
                f"Value {norm_val} {canon_unit} exceeds physical plausibility bounds "
                f"[{valid_min}, {valid_max}] for indicator '{canon_ind}'."
            )

    norm_obs = Observation(
        indicator=indicator,
        value=norm_val,
        unit=canon_unit,
        timestamp=str(timestamp).strip(),
        period=period,
        ward_id=str(ward_id).strip() if ward_id else None,
        source_type=str(source_type).strip().upper(),
        source_name=str(source_name).strip() if source_name else None,
        location_tag=str(location_tag).strip() if location_tag else None,
        quality_status=str(quality_status).strip().upper(),
        observation_id=str(obs_id).strip() if obs_id else None,
        notes=str(notes).strip() if notes else None
    )
    return norm_obs, None


def aggregate_observations(
    observations: List[Union[Observation, Dict[str, Any]]],
    period: str,
    target_ward_id: Optional[str] = None
) -> Tuple[Optional[ObservationAggregate], Optional[str]]:
    """
    Aggregates multiple observations for a single period and single indicator.
    Enforces compatibility across units, locations, and measurement period.
    Returns (ObservationAggregate, error_message).
    """
    if not observations:
        return None, "NO_OBSERVATIONS: Observation list is empty."

    norm_list: List[Observation] = []
    for idx, raw_obs in enumerate(observations):
        norm_obs, err = validate_observation(raw_obs)
        if err:
            return None, f"INVALID_OBSERVATION at index {idx}: {err}"
        norm_list.append(norm_obs)

    # Filter to requested period
    period_upper = period.strip().upper()
    filtered = [o for o in norm_list if o.period == period_upper]
    if not filtered:
        return None, f"NO_DATA_FOR_PERIOD: No observations found for period '{period_upper}'."

    # Verify indicator consistency
    canonical_indicators = {
        resolve_canonical_indicator(o.indicator) or o.indicator.lower()
        for o in filtered
    }
    if len(canonical_indicators) > 1:
        return None, (
            f"INCOMPATIBLE_INDICATORS: Cannot aggregate heterogeneous indicators: {list(canonical_indicators)}"
        )
    canon_ind = list(canonical_indicators)[0]

    # Verify unit consistency
    units = {o.unit for o in filtered}
    if len(units) > 1:
        return None, f"INCOMPATIBLE_UNITS: Cannot aggregate disparate units: {list(units)}"
    common_unit = list(units)[0]

    # Verify ward location compatibility
    if target_ward_id:
        for o in filtered:
            if o.ward_id and o.ward_id.upper() != target_ward_id.upper():
                return None, (
                    f"INCOMPATIBLE_LOCATIONS: Observation ward '{o.ward_id}' does not match target ward '{target_ward_id}'."
                )

    # Compute statistics
    values = sorted([o.value for o in filtered])
    n = len(values)
    mean_val = round(sum(values) / n, 4)
    if n % 2 == 1:
        median_val = values[n // 2]
    else:
        median_val = round((values[n // 2 - 1] + values[n // 2]) / 2.0, 4)

    timestamps = sorted([o.timestamp for o in filtered])
    source_types = sorted(list({o.source_type for o in filtered}))
    source_names = sorted(list({o.source_name for o in filtered if o.source_name}))
    quality_statuses = sorted(list({o.quality_status for o in filtered}))
    location_tags = sorted(list({o.location_tag for o in filtered if o.location_tag}))
    is_synthetic = any(
        o.source_type == SourceType.SYNTHETIC_DEMO or o.quality_status == QualityStatus.SYNTHETIC_DEMO
        for o in filtered
    )

    agg = ObservationAggregate(
        indicator=filtered[0].indicator,
        canonical_indicator=canon_ind,
        period=period_upper,
        unit=common_unit,
        mean_value=mean_val,
        median_value=median_val,
        min_value=values[0],
        max_value=values[-1],
        observation_count=n,
        timestamps=timestamps,
        source_types=source_types,
        source_names=source_names,
        quality_statuses=quality_statuses,
        is_synthetic=is_synthetic,
        location_tags=location_tags
    )
    return agg, None


# ---------------------------------------------------------------------------
# CORE CHANGE & IMPACT CALCULATION
# ---------------------------------------------------------------------------

def calculate_indicator_change(
    baseline_agg: Optional[ObservationAggregate],
    follow_up_agg: Optional[ObservationAggregate],
    indicator_key: str
) -> IndicatorImpactResult:
    """
    Computes absolute difference, percentage change, and beneficial direction
    between baseline and follow-up aggregates for a given indicator.
    Handles missing data, zero baselines, invalid numbers, and incompatible units.
    """
    canon_key = resolve_canonical_indicator(indicator_key) or indicator_key.strip().lower()
    ind_info = INDICATOR_REGISTRY.get(canon_key, {
        "canonical_name": canon_key,
        "hazard_category": "cross_cutting",
        "canonical_unit": baseline_agg.unit if baseline_agg else (follow_up_agg.unit if follow_up_agg else "unknown"),
        "beneficial_direction": Direction.DECREASE_IS_BENEFICIAL,
        "is_interval_scale": False
    })

    hazard_category = ind_info.get("hazard_category", "cross_cutting")
    beneficial_dir = ind_info.get("beneficial_direction", Direction.DECREASE_IS_BENEFICIAL)
    is_interval_scale = ind_info.get("is_interval_scale", False)
    notes: List[str] = []

    # Case 1: Missing Baseline
    if baseline_agg is None and follow_up_agg is not None:
        notes.append("MISSING_BASELINE: No valid baseline measurements available for comparison.")
        return IndicatorImpactResult(
            indicator=indicator_key,
            canonical_indicator=canon_key,
            hazard_category=hazard_category,
            beneficial_direction=beneficial_dir,
            baseline_value=None,
            follow_up_value=follow_up_agg.mean_value,
            unit=follow_up_agg.unit,
            difference=None,
            percentage_change=None,
            is_improvement=None,
            improvement_magnitude=None,
            baseline_observation_count=0,
            follow_up_observation_count=follow_up_agg.observation_count,
            baseline_timestamps=[],
            follow_up_timestamps=follow_up_agg.timestamps,
            source_types=follow_up_agg.source_types,
            is_synthetic=follow_up_agg.is_synthetic,
            quality_status=QualityStatus.MISSING_BASELINE,
            notes=notes
        )

    # Case 2: Missing Follow-up
    if baseline_agg is not None and follow_up_agg is None:
        notes.append("MISSING_FOLLOW_UP: No valid follow-up measurements available for comparison.")
        return IndicatorImpactResult(
            indicator=indicator_key,
            canonical_indicator=canon_key,
            hazard_category=hazard_category,
            beneficial_direction=beneficial_dir,
            baseline_value=baseline_agg.mean_value,
            follow_up_value=None,
            unit=baseline_agg.unit,
            difference=None,
            percentage_change=None,
            is_improvement=None,
            improvement_magnitude=None,
            baseline_observation_count=baseline_agg.observation_count,
            follow_up_observation_count=0,
            baseline_timestamps=baseline_agg.timestamps,
            follow_up_timestamps=[],
            source_types=baseline_agg.source_types,
            is_synthetic=baseline_agg.is_synthetic,
            quality_status=QualityStatus.MISSING_FOLLOW_UP,
            notes=notes
        )

    # Case 3: Missing Both
    if baseline_agg is None and follow_up_agg is None:
        notes.append("INSUFFICIENT_DATA: Neither baseline nor follow-up observations provided.")
        return IndicatorImpactResult(
            indicator=indicator_key,
            canonical_indicator=canon_key,
            hazard_category=hazard_category,
            beneficial_direction=beneficial_dir,
            baseline_value=None,
            follow_up_value=None,
            unit=None,
            difference=None,
            percentage_change=None,
            is_improvement=None,
            improvement_magnitude=None,
            baseline_observation_count=0,
            follow_up_observation_count=0,
            baseline_timestamps=[],
            follow_up_timestamps=[],
            source_types=[],
            is_synthetic=False,
            quality_status=QualityStatus.INSUFFICIENT_DATA,
            notes=notes
        )

    # Both aggregates exist: verify unit compatibility
    if baseline_agg.unit != follow_up_agg.unit:
        notes.append(
            f"INCOMPATIBLE_UNITS: Baseline unit '{baseline_agg.unit}' does not match "
            f"follow-up unit '{follow_up_agg.unit}'."
        )
        return IndicatorImpactResult(
            indicator=indicator_key,
            canonical_indicator=canon_key,
            hazard_category=hazard_category,
            beneficial_direction=beneficial_dir,
            baseline_value=baseline_agg.mean_value,
            follow_up_value=follow_up_agg.mean_value,
            unit=f"{baseline_agg.unit}_vs_{follow_up_agg.unit}",
            difference=None,
            percentage_change=None,
            is_improvement=None,
            improvement_magnitude=None,
            baseline_observation_count=baseline_agg.observation_count,
            follow_up_observation_count=follow_up_agg.observation_count,
            baseline_timestamps=baseline_agg.timestamps,
            follow_up_timestamps=follow_up_agg.timestamps,
            source_types=sorted(list(set(baseline_agg.source_types + follow_up_agg.source_types))),
            is_synthetic=baseline_agg.is_synthetic or follow_up_agg.is_synthetic,
            quality_status=QualityStatus.INCOMPATIBLE_UNITS,
            notes=notes
        )

    b_val = baseline_agg.mean_value
    f_val = follow_up_agg.mean_value
    common_unit = baseline_agg.unit

    diff = round(f_val - b_val, 4)

    # Percentage change calculation
    pct_change: Optional[float] = None
    if b_val != 0.0:
        pct_change = round(((f_val - b_val) / abs(b_val)) * 100.0, 2)
    else:
        notes.append(
            "ZERO_BASELINE_PERCENTAGE_UNDEFINED: Percentage change is mathematically "
            "undefined when baseline value is zero. Absolute difference is reported."
        )

    if is_interval_scale:
        notes.append(
            f"INTERVAL_SCALE_NOTE: {canon_key.title()} is measured on an interval scale ({common_unit}). "
            "Absolute difference is the physically meaningful metric; percentage change is mathematically "
            "relative to the arbitrary zero scale."
        )

    # Directional improvement evaluation
    is_improvement: Optional[bool] = None
    improvement_magnitude: Optional[float] = None

    if diff == 0.0:
        is_improvement = False
        improvement_magnitude = 0.0
        notes.append("NO_CHANGE: Observation showed identical baseline and follow-up values.")
    elif beneficial_dir == Direction.DECREASE_IS_BENEFICIAL:
        if diff < 0:
            is_improvement = True
            improvement_magnitude = abs(diff)
        else:
            is_improvement = False
            improvement_magnitude = 0.0
            notes.append(f"UNFAVORABLE_CHANGE: Indicator increased by {diff} {common_unit} (decrease is beneficial).")
    elif beneficial_dir == Direction.INCREASE_IS_BENEFICIAL:
        if diff > 0:
            is_improvement = True
            improvement_magnitude = diff
        else:
            is_improvement = False
            improvement_magnitude = 0.0
            notes.append(f"UNFAVORABLE_CHANGE: Indicator decreased by {abs(diff)} {common_unit} (increase is beneficial).")

    # Combine sources and synthetic flags
    all_sources = sorted(list(set(baseline_agg.source_types + follow_up_agg.source_types)))
    is_synthetic = baseline_agg.is_synthetic or follow_up_agg.is_synthetic

    if is_synthetic:
        notes.append(DEMONSTRATION_DATA_NOTICE)
        quality_status = QualityStatus.SYNTHETIC_DEMO
    else:
        # Determine aggregate quality status
        all_qualities = set(baseline_agg.quality_statuses + follow_up_agg.quality_statuses)
        if QualityStatus.SUSPECT in all_qualities:
            quality_status = QualityStatus.SUSPECT
        elif QualityStatus.PROVISIONAL in all_qualities:
            quality_status = QualityStatus.PROVISIONAL
        elif QualityStatus.ESTIMATED in all_qualities:
            quality_status = QualityStatus.ESTIMATED
        else:
            quality_status = QualityStatus.VERIFIED

    return IndicatorImpactResult(
        indicator=indicator_key,
        canonical_indicator=canon_key,
        hazard_category=hazard_category,
        beneficial_direction=beneficial_dir,
        baseline_value=b_val,
        follow_up_value=f_val,
        unit=common_unit,
        difference=diff,
        percentage_change=pct_change,
        is_improvement=is_improvement,
        improvement_magnitude=improvement_magnitude,
        baseline_observation_count=baseline_agg.observation_count,
        follow_up_observation_count=follow_up_agg.observation_count,
        baseline_timestamps=baseline_agg.timestamps,
        follow_up_timestamps=follow_up_agg.timestamps,
        source_types=all_sources,
        is_synthetic=is_synthetic,
        quality_status=quality_status,
        notes=notes
    )


# ---------------------------------------------------------------------------
# STRUCTURED INTERVENTION IMPACT ASSESSMENT
# ---------------------------------------------------------------------------

def assess_intervention_impact(
    intervention_id: str,
    ward_id: str,
    intervention_type: str,
    observations: List[Union[Observation, Dict[str, Any]]],
    baseline_period: Optional[Dict[str, Any]] = None,
    follow_up_period: Optional[Dict[str, Any]] = None,
    assessment_id: Optional[str] = None
) -> InterventionImpactAssessment:
    """
    Executes a structured impact assessment for an intervention in a given ward.
    Groups observations by canonical indicator, aggregates compatible measurements,
    computes before-and-after differences, and builds an auditable verification report.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    clean_aid = assessment_id or f"VIA_{ward_id}_{intervention_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    base_period = baseline_period or {"description": "Pre-intervention baseline window"}
    post_period = follow_up_period or {"description": "Post-intervention follow-up window"}

    # Validate and group observations by canonical indicator
    grouped_by_indicator: Dict[str, Dict[str, List[Observation]]] = {}
    validation_errors: List[str] = []

    for idx, obs in enumerate(observations or []):
        norm_obs, err = validate_observation(obs)
        if err:
            validation_errors.append(f"Observation #{idx}: {err}")
            continue

        canon_ind = resolve_canonical_indicator(norm_obs.indicator) or norm_obs.indicator.lower()
        if canon_ind not in grouped_by_indicator:
            grouped_by_indicator[canon_ind] = {"BASELINE": [], "FOLLOW_UP": []}

        period_key = norm_obs.period
        grouped_by_indicator[canon_ind][period_key].append(norm_obs)

    results_by_indicator: Dict[str, IndicatorImpactResult] = {}
    overall_is_synthetic = False
    quality_statuses: List[str] = []

    if not grouped_by_indicator:
        # No valid observations at all
        overall_quality_status = QualityStatus.INSUFFICIENT_DATA
    else:
        for canon_ind, period_groups in grouped_by_indicator.items():
            base_obs_list = period_groups["BASELINE"]
            post_obs_list = period_groups["FOLLOW_UP"]

            base_agg, base_err = aggregate_observations(base_obs_list, "BASELINE", target_ward_id=ward_id) if base_obs_list else (None, "NO_BASELINE_DATA")
            post_agg, post_err = aggregate_observations(post_obs_list, "FOLLOW_UP", target_ward_id=ward_id) if post_obs_list else (None, "NO_FOLLOW_UP_DATA")

            ind_res = calculate_indicator_change(base_agg, post_agg, canon_ind)

            if base_err and not ind_res.baseline_value:
                ind_res.notes.append(f"Baseline grouping notice: {base_err}")
            if post_err and not ind_res.follow_up_value:
                ind_res.notes.append(f"Follow-up grouping notice: {post_err}")

            if ind_res.is_synthetic:
                overall_is_synthetic = True

            quality_statuses.append(ind_res.quality_status)
            results_by_indicator[canon_ind] = ind_res

        # Determine overall quality status
        if QualityStatus.INCOMPATIBLE_UNITS in quality_statuses:
            overall_quality_status = QualityStatus.INCOMPATIBLE_UNITS
        elif QualityStatus.SUSPECT in quality_statuses:
            overall_quality_status = QualityStatus.SUSPECT
        elif overall_is_synthetic:
            overall_quality_status = QualityStatus.SYNTHETIC_DEMO
        elif all(qs == QualityStatus.VERIFIED for qs in quality_statuses):
            overall_quality_status = QualityStatus.VERIFIED
        else:
            overall_quality_status = quality_statuses[0] if quality_statuses else QualityStatus.PROVISIONAL

    # Compile high-level summary
    improved_indicators = [
        k for k, v in results_by_indicator.items() if v.is_improvement is True
    ]
    unimproved_indicators = [
        k for k, v in results_by_indicator.items() if v.is_improvement is False and v.difference != 0.0
    ]
    neutral_indicators = [
        k for k, v in results_by_indicator.items() if v.difference == 0.0
    ]

    summary = {
        "total_indicators_assessed": len(results_by_indicator),
        "improved_indicators_count": len(improved_indicators),
        "improved_indicators": improved_indicators,
        "unimproved_indicators_count": len(unimproved_indicators),
        "unimproved_indicators": unimproved_indicators,
        "neutral_indicators_count": len(neutral_indicators),
        "validation_errors": validation_errors,
        "is_partially_evaluated": any(
            v.quality_status in [QualityStatus.MISSING_BASELINE, QualityStatus.MISSING_FOLLOW_UP]
            for v in results_by_indicator.values()
        )
    }

    # Convert results to dicts for clean serialization
    serialized_results = {k: v.to_dict() for k, v in results_by_indicator.items()}

    return InterventionImpactAssessment(
        assessment_id=clean_aid,
        intervention_id=intervention_id,
        ward_id=ward_id,
        intervention_type=intervention_type,
        baseline_period=base_period,
        follow_up_period=post_period,
        indicators_assessed=list(results_by_indicator.keys()),
        results_by_indicator=serialized_results,
        overall_quality_status=overall_quality_status,
        overall_is_synthetic=overall_is_synthetic,
        attribution_disclaimer=ATTRIBUTION_DISCLAIMER,
        summary=summary,
        created_at=now_iso
    )


# ---------------------------------------------------------------------------
# SYNTHETIC DEMONSTRATION DATA GENERATOR
# ---------------------------------------------------------------------------

def generate_synthetic_demonstration_data(
    intervention_id: str,
    ward_id: str,
    intervention_type: str,
    hazard_type: str = "heat"
) -> Dict[str, Any]:
    """
    Generates realistic, physically plausible synthetic observation datasets for demonstration
    and algorithmic verification when real field telemetry is unavailable.
    All records are strictly tagged with SourceType.SYNTHETIC_DEMO and prominent disclaimers.
    """
    hazard_clean = hazard_type.strip().lower()

    base_period = {
        "start": "2026-05-10T08:00:00Z",
        "end": "2026-05-12T18:00:00Z",
        "description": "Pre-deployment municipal monitoring baseline"
    }
    follow_up_period = {
        "start": "2026-05-15T08:00:00Z",
        "end": "2026-05-17T18:00:00Z",
        "description": "Post-deployment operational observation window"
    }

    observations: List[Dict[str, Any]] = []

    if hazard_clean == "heat":
        # Realistic heat baseline vs follow-up
        observations.extend([
            # Baseline Heat Observations
            {
                "indicator": "ambient_temperature",
                "value": 43.8,
                "unit": "°C",
                "timestamp": "2026-05-11T14:00:00Z",
                "period": "BASELINE",
                "ward_id": ward_id,
                "source_type": SourceType.SYNTHETIC_DEMO,
                "source_name": "SYNTHETIC_WEATHER_STATION_SIM",
                "location_tag": "Urban Labor Corridor",
                "quality_status": QualityStatus.SYNTHETIC_DEMO,
                "observation_id": f"SYN_BASE_TEMP_{ward_id}_1"
            },
            {
                "indicator": "ambient_temperature",
                "value": 44.2,
                "unit": "°C",
                "timestamp": "2026-05-12T14:30:00Z",
                "period": "BASELINE",
                "ward_id": ward_id,
                "source_type": SourceType.SYNTHETIC_DEMO,
                "source_name": "SYNTHETIC_WEATHER_STATION_SIM",
                "location_tag": "Urban Labor Corridor",
                "quality_status": QualityStatus.SYNTHETIC_DEMO,
                "observation_id": f"SYN_BASE_TEMP_{ward_id}_2"
            },
            {
                "indicator": "wbgt",
                "value": 34.6,
                "unit": "°C",
                "timestamp": "2026-05-11T15:00:00Z",
                "period": "BASELINE",
                "ward_id": ward_id,
                "source_type": SourceType.SYNTHETIC_DEMO,
                "source_name": "SYNTHETIC_HEAT_STRESS_MODEL",
                "quality_status": QualityStatus.SYNTHETIC_DEMO,
                "observation_id": f"SYN_BASE_WBGT_{ward_id}_1"
            },
            {
                "indicator": "hospital_heat_admissions",
                "value": 16.0,
                "unit": "count",
                "timestamp": "2026-05-12T20:00:00Z",
                "period": "BASELINE",
                "ward_id": ward_id,
                "source_type": SourceType.SYNTHETIC_DEMO,
                "source_name": "SYNTHETIC_CIVIC_HOSPITAL_SURVEILLANCE",
                "quality_status": QualityStatus.SYNTHETIC_DEMO,
                "observation_id": f"SYN_BASE_HOSP_{ward_id}_1"
            },

            # Follow-up Heat Observations (e.g. after shade canopy or cooling shelter deployment)
            {
                "indicator": "ambient_temperature",
                "value": 41.5,
                "unit": "°C",
                "timestamp": "2026-05-16T14:00:00Z",
                "period": "FOLLOW_UP",
                "ward_id": ward_id,
                "source_type": SourceType.SYNTHETIC_DEMO,
                "source_name": "SYNTHETIC_WEATHER_STATION_SIM",
                "location_tag": "Urban Labor Corridor",
                "quality_status": QualityStatus.SYNTHETIC_DEMO,
                "observation_id": f"SYN_POST_TEMP_{ward_id}_1"
            },
            {
                "indicator": "wbgt",
                "value": 32.8,
                "unit": "°C",
                "timestamp": "2026-05-16T15:00:00Z",
                "period": "FOLLOW_UP",
                "ward_id": ward_id,
                "source_type": SourceType.SYNTHETIC_DEMO,
                "source_name": "SYNTHETIC_HEAT_STRESS_MODEL",
                "quality_status": QualityStatus.SYNTHETIC_DEMO,
                "observation_id": f"SYN_POST_WBGT_{ward_id}_1"
            },
            {
                "indicator": "hospital_heat_admissions",
                "value": 9.0,
                "unit": "count",
                "timestamp": "2026-05-17T20:00:00Z",
                "period": "FOLLOW_UP",
                "ward_id": ward_id,
                "source_type": SourceType.SYNTHETIC_DEMO,
                "source_name": "SYNTHETIC_CIVIC_HOSPITAL_SURVEILLANCE",
                "quality_status": QualityStatus.SYNTHETIC_DEMO,
                "observation_id": f"SYN_POST_HOSP_{ward_id}_1"
            }
        ])

    elif hazard_clean in ["flood", "waterlogging"]:
        # Realistic waterlogging baseline vs follow-up
        observations.extend([
            # Baseline Inundation Observations
            {
                "indicator": "flood_water_depth",
                "value": 68.0,
                "unit": "cm",
                "timestamp": "2026-07-15T09:00:00Z",
                "period": "BASELINE",
                "ward_id": ward_id,
                "source_type": SourceType.SYNTHETIC_DEMO,
                "source_name": "SYNTHETIC_ULTRASONIC_INUNDATION_SENSOR",
                "location_tag": "Underpass Intersection",
                "quality_status": QualityStatus.SYNTHETIC_DEMO,
                "observation_id": f"SYN_BASE_DEPTH_{ward_id}_1"
            },
            {
                "indicator": "waterlogging_duration",
                "value": 7.5,
                "unit": "hours",
                "timestamp": "2026-07-15T18:00:00Z",
                "period": "BASELINE",
                "ward_id": ward_id,
                "source_type": SourceType.SYNTHETIC_DEMO,
                "source_name": "SYNTHETIC_TRAFFIC_POLICE_LOG",
                "location_tag": "Underpass Intersection",
                "quality_status": QualityStatus.SYNTHETIC_DEMO,
                "observation_id": f"SYN_BASE_DUR_{ward_id}_1"
            },
            # Follow-up Inundation Observations (e.g. after culvert desilting & dewatering pumps)
            {
                "indicator": "flood_water_depth",
                "value": 14.5,
                "unit": "cm",
                "timestamp": "2026-07-16T10:00:00Z",
                "period": "FOLLOW_UP",
                "ward_id": ward_id,
                "source_type": SourceType.SYNTHETIC_DEMO,
                "source_name": "SYNTHETIC_ULTRASONIC_INUNDATION_SENSOR",
                "location_tag": "Underpass Intersection",
                "quality_status": QualityStatus.SYNTHETIC_DEMO,
                "observation_id": f"SYN_POST_DEPTH_{ward_id}_1"
            },
            {
                "indicator": "waterlogging_duration",
                "value": 1.8,
                "unit": "hours",
                "timestamp": "2026-07-16T14:00:00Z",
                "period": "FOLLOW_UP",
                "ward_id": ward_id,
                "source_type": SourceType.SYNTHETIC_DEMO,
                "source_name": "SYNTHETIC_TRAFFIC_POLICE_LOG",
                "location_tag": "Underpass Intersection",
                "quality_status": QualityStatus.SYNTHETIC_DEMO,
                "observation_id": f"SYN_POST_DUR_{ward_id}_1"
            }
        ])

    elif hazard_clean in ["water_shortage", "water", "shortage"]:
        # Realistic potable water supply baseline vs follow-up
        observations.extend([
            # Baseline Potable Water Scarcity
            {
                "indicator": "water_delivered",
                "value": 15000.0,
                "unit": "liters",
                "timestamp": "2026-05-18T10:00:00Z",
                "period": "BASELINE",
                "ward_id": ward_id,
                "source_type": SourceType.SYNTHETIC_DEMO,
                "source_name": "SYNTHETIC_CIVIC_WATER_LOG",
                "quality_status": QualityStatus.SYNTHETIC_DEMO,
                "observation_id": f"SYN_BASE_DELIV_{ward_id}_1"
            },
            {
                "indicator": "supply_duration",
                "value": 1.2,
                "unit": "hours",
                "timestamp": "2026-05-18T12:00:00Z",
                "period": "BASELINE",
                "ward_id": ward_id,
                "source_type": SourceType.SYNTHETIC_DEMO,
                "source_name": "SYNTHETIC_CIVIC_WATER_LOG",
                "quality_status": QualityStatus.SYNTHETIC_DEMO,
                "observation_id": f"SYN_BASE_SUPP_{ward_id}_1"
            },
            {
                "indicator": "water_scarcity_complaints",
                "value": 32.0,
                "unit": "count",
                "timestamp": "2026-05-18T20:00:00Z",
                "period": "BASELINE",
                "ward_id": ward_id,
                "source_type": SourceType.SYNTHETIC_DEMO,
                "source_name": "SYNTHETIC_CIVIC_HELPLINE_LOG",
                "quality_status": QualityStatus.SYNTHETIC_DEMO,
                "observation_id": f"SYN_BASE_COMPL_{ward_id}_1"
            },
            # Follow-up Potable Water (e.g. after tanker dispatch & kiosk setup)
            {
                "indicator": "water_delivered",
                "value": 45000.0,
                "unit": "liters",
                "timestamp": "2026-05-20T10:00:00Z",
                "period": "FOLLOW_UP",
                "ward_id": ward_id,
                "source_type": SourceType.SYNTHETIC_DEMO,
                "source_name": "SYNTHETIC_CIVIC_WATER_LOG",
                "quality_status": QualityStatus.SYNTHETIC_DEMO,
                "observation_id": f"SYN_POST_DELIV_{ward_id}_1"
            },
            {
                "indicator": "supply_duration",
                "value": 3.8,
                "unit": "hours",
                "timestamp": "2026-05-20T12:00:00Z",
                "period": "FOLLOW_UP",
                "ward_id": ward_id,
                "source_type": SourceType.SYNTHETIC_DEMO,
                "source_name": "SYNTHETIC_CIVIC_WATER_LOG",
                "quality_status": QualityStatus.SYNTHETIC_DEMO,
                "observation_id": f"SYN_POST_SUPP_{ward_id}_1"
            },
            {
                "indicator": "water_scarcity_complaints",
                "value": 9.0,
                "unit": "count",
                "timestamp": "2026-05-20T20:00:00Z",
                "period": "FOLLOW_UP",
                "ward_id": ward_id,
                "source_type": SourceType.SYNTHETIC_DEMO,
                "source_name": "SYNTHETIC_CIVIC_HELPLINE_LOG",
                "quality_status": QualityStatus.SYNTHETIC_DEMO,
                "observation_id": f"SYN_POST_COMPL_{ward_id}_1"
            }
        ])

    return {
        "intervention_id": intervention_id,
        "ward_id": ward_id,
        "intervention_type": intervention_type,
        "baseline_period": base_period,
        "follow_up_period": follow_up_period,
        "is_synthetic": True,
        "demonstration_notice": DEMONSTRATION_DATA_NOTICE,
        "observations": observations
    }


# ---------------------------------------------------------------------------
# PERSISTENCE & DATA STORAGE INTEGRATION
# ---------------------------------------------------------------------------

class ExecutionStatus:
    COMPLETED = "COMPLETED"
    DEPLOYED = "DEPLOYED"
    OBSERVED = "OBSERVED"
    IN_PROGRESS = "IN_PROGRESS"
    SYNTHETIC_DEMO = "SYNTHETIC_DEMO"


VALID_EXECUTION_STATUSES = {
    ExecutionStatus.COMPLETED,
    ExecutionStatus.DEPLOYED,
    ExecutionStatus.OBSERVED,
    ExecutionStatus.IN_PROGRESS,
    ExecutionStatus.SYNTHETIC_DEMO
}

INVALID_EXECUTION_STATUSES = {
    "RECOMMENDED",
    "PENDING_HUMAN_APPROVAL",
    "PROPOSED",
    "RECOMMENDATION"
}


def validate_assessment_for_persistence(assessment_data: Dict[str, Any]) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Validates required fields, data types, execution status, and unit consistency
    prior to recording an assessment into persistent storage.
    """
    if not isinstance(assessment_data, dict):
        return {}, "Assessment payload must be a dictionary."

    # Validate required identification fields
    aid = assessment_data.get("assessment_id")
    if not aid or not isinstance(aid, str) or not aid.strip():
        return {}, "Missing or invalid 'assessment_id': must be a non-empty string."

    iid = assessment_data.get("intervention_id")
    if not iid or not isinstance(iid, str) or not iid.strip():
        return {}, "Missing or invalid 'intervention_id': must be a non-empty string."

    wid = assessment_data.get("ward_id")
    if not wid or not isinstance(wid, str) or not wid.strip():
        return {}, "Missing or invalid 'ward_id': must be a non-empty string."

    itype = assessment_data.get("intervention_type")
    if not itype or not isinstance(itype, str) or not itype.strip():
        return {}, "Missing or invalid 'intervention_type': must be a non-empty string."

    # Enforce Requirement 5: Do not assume an intervention was completed merely because it was recommended.
    exec_status = str(assessment_data.get("execution_status", ExecutionStatus.COMPLETED)).strip().upper()
    if exec_status in INVALID_EXECUTION_STATUSES:
        return {}, (
            f"UNCOMPLETED_INTERVENTION: Cannot verify an intervention with execution status '{exec_status}'. "
            "Impact verification requires an executed, deployed, or observed intervention. "
            "Recommended interventions without field deployment cannot be verified."
        )

    if exec_status not in VALID_EXECUTION_STATUSES:
        return {}, f"Invalid execution_status '{exec_status}'. Must be one of: {sorted(list(VALID_EXECUTION_STATUSES))}."

    # Enforce Requirement 2: Use consistent units for comparisons.
    indicators_dict = assessment_data.get("indicators") or assessment_data.get("results_by_indicator") or {}
    if not indicators_dict or not isinstance(indicators_dict, dict):
        return {}, "Missing or invalid indicator results: assessment must contain evaluated indicators."

    for ind_name, ind_data in indicators_dict.items():
        if isinstance(ind_data, dict):
            unit = ind_data.get("unit")
            if not unit:
                return {}, f"Indicator '{ind_name}' is missing a required measurement unit."

            # If indicator name is known, check canonical unit compatibility
            canon = resolve_canonical_indicator(ind_name)
            if canon:
                canon_unit = INDICATOR_REGISTRY[canon]["canonical_unit"]
                norm_u = normalize_unit_string(unit)
                # Check if unit is either canonical or convertible
                if norm_u != canon_unit:
                    _, convertible = convert_value_to_canonical(1.0, unit, canon_unit)
                    if not convertible:
                        return {}, (
                            f"Inconsistent unit '{unit}' for indicator '{ind_name}'. "
                            f"Expected unit convertible to '{canon_unit}'."
                        )

    # Clean standardized payload
    cleaned = dict(assessment_data)
    cleaned["assessment_id"] = aid.strip()
    cleaned["intervention_id"] = iid.strip()
    cleaned["ward_id"] = wid.strip().upper()
    cleaned["intervention_type"] = itype.strip()
    cleaned["execution_status"] = exec_status
    cleaned["verification_status"] = str(assessment_data.get("verification_status", QualityStatus.VERIFIED)).strip().upper()
    cleaned["provenance_mode"] = str(assessment_data.get("provenance_mode", SourceType.MEASURED)).strip().upper()
    cleaned["is_synthetic"] = bool(assessment_data.get("is_synthetic", False))
    cleaned["baseline_period"] = assessment_data.get("baseline_period") or {}
    cleaned["follow_up_period"] = assessment_data.get("follow_up_period") or {}
    cleaned["indicators"] = indicators_dict
    cleaned["data_quality_warnings"] = assessment_data.get("data_quality_warnings") or []
    cleaned["attribution_disclaimer"] = assessment_data.get("attribution_disclaimer") or ATTRIBUTION_DISCLAIMER
    cleaned["summary"] = assessment_data.get("summary") or {}

    return cleaned, None


def record_impact_assessment(
    assessment: Union[InterventionImpactAssessment, Dict[str, Any]],
    execution_status: str = ExecutionStatus.COMPLETED,
    allow_update: bool = False,
    change_reason: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validates and persists an impact assessment into the baseline SQLite database.
    - Idempotent on identical re-saves.
    - Prevents accidental duplicates and silent overwrites.
    - Archives previous version to impact_assessment_history when allow_update=True.
    - Rejects uncompleted/recommended interventions.
    """
    from backend.database import save_impact_assessment_record

    raw_dict = assessment.to_dict() if isinstance(assessment, InterventionImpactAssessment) else dict(assessment)
    if "execution_status" not in raw_dict:
        raw_dict["execution_status"] = execution_status

    # Map results_by_indicator to indicators if needed
    if "results_by_indicator" in raw_dict and "indicators" not in raw_dict:
        raw_dict["indicators"] = raw_dict["results_by_indicator"]

    validated_payload, err = validate_assessment_for_persistence(raw_dict)
    if err:
        raise ValueError(f"Assessment validation failed: {err}")

    return save_impact_assessment_record(
        validated_payload,
        allow_update=allow_update,
        change_reason=change_reason
    )


def retrieve_impact_assessment(assessment_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a persisted impact assessment by ID."""
    from backend.database import get_impact_assessment_by_id
    if not assessment_id or not isinstance(assessment_id, str):
        return None
    return get_impact_assessment_by_id(assessment_id.strip())


def list_impact_assessments(
    ward_id: Optional[str] = None,
    intervention_id: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Retrieves persisted impact assessments with optional filtering."""
    from backend.database import get_all_impact_assessments
    return get_all_impact_assessments(ward_id=ward_id, intervention_id=intervention_id, limit=limit)


def retrieve_assessment_history(assessment_id: str) -> List[Dict[str, Any]]:
    """Retrieves all historical archived snapshots for an assessment ID."""
    from backend.database import get_impact_assessment_history
    if not assessment_id or not isinstance(assessment_id, str):
        return []
    return get_impact_assessment_history(assessment_id.strip())


def update_impact_assessment(
    assessment_id: str,
    updated_assessment: Union[InterventionImpactAssessment, Dict[str, Any]],
    change_reason: str = "Updated assessment data"
) -> Dict[str, Any]:
    """
    Explicitly updates an existing assessment, archiving the prior version to history.
    """
    payload = updated_assessment.to_dict() if isinstance(updated_assessment, InterventionImpactAssessment) else dict(updated_assessment)
    payload["assessment_id"] = assessment_id
    return record_impact_assessment(
        payload,
        allow_update=True,
        change_reason=change_reason
    )


# ---------------------------------------------------------------------------
# REPORTING & AGGREGATION ENGINE
# ---------------------------------------------------------------------------

def generate_impact_verification_summary(
    assessments: Optional[List[Dict[str, Any]]] = None,
    ward_id: Optional[str] = None,
    intervention_type: Optional[str] = None,
    hazard_category: Optional[str] = None,
    include_synthetic: bool = False
) -> Dict[str, Any]:
    """
    Generates a structured, auditable summary report of intervention impact assessments.
    
    Principles & Aggregation Rules:
    ==============================
    1. Deduplication: De-duplicates assessments by assessment_id (taking the latest version)
       to avoid double-counting repeated records.
    2. Segregation of Provenance: Strictly separates empirical measured/observed records
       from simulated demonstration records. Does not report simulated results as real-world impact.
    3. No Zero Imputation: Missing baseline or follow-up results are NEVER treated as zero.
       They are strictly excluded from aggregates to protect physical integrity.
    4. Unit Compatibility: Only aggregates indicators sharing canonical physical units.
    5. Explicit Aggregation: Specifies exact arithmetic methods (Pairwise arithmetic mean).
    6. Non-Causal Attribution: Carries prominent attribution caveats.
    """
    from backend.database import get_all_impact_assessments

    if assessments is None:
        raw_list = get_all_impact_assessments(ward_id=ward_id.strip().upper() if ward_id else None, limit=1000)
    else:
        raw_list = [dict(a) for a in assessments]

    raw_count = len(raw_list)

    # Empty dataset handling
    if raw_count == 0:
        return {
            "status": "EMPTY_DATASET",
            "message": "No impact assessment records found matching query criteria.",
            "kpis": {
                "total_assessments_recorded": 0,
                "unique_assessments_count": 0,
                "duplicate_records_pruned": 0,
                "valid_before_after_comparisons_count": 0,
                "incomplete_assessments_count": 0,
                "provenance_counts": {
                    "measured": 0,
                    "external_observation": 0,
                    "estimated": 0,
                    "simulated_demo": 0
                }
            },
            "incomplete_breakdown": {
                "missing_baseline": 0,
                "missing_follow_up": 0,
                "incompatible_units": 0,
                "insufficient_data": 0
            },
            "by_ward": {},
            "by_intervention_type": {},
            "by_indicator": {},
            "data_quality_warnings_summary": {},
            "source_information": {},
            "aggregation_method": "PAIRWISE_ARITHMETIC_MEAN_OF_VALID_RECORDS (Missing values strictly excluded; zero-imputation prohibited)",
            "data_integrity_mode": "INCLUDES_SIMULATED_DEMO" if include_synthetic else "REAL_WORLD_VERIFIED_ONLY",
            "causal_attribution_caveat": ATTRIBUTION_DISCLAIMER
        }

    # Step 1: De-duplication (pick highest version per assessment_id)
    deduped_map: Dict[str, Dict[str, Any]] = {}
    for r in raw_list:
        aid = str(r.get("assessment_id", "")).strip()
        if not aid:
            continue
        ver = int(r.get("version", 1))
        if aid not in deduped_map or ver > int(deduped_map[aid].get("version", 1)):
            deduped_map[aid] = r

    unique_records = list(deduped_map.values())
    unique_count = len(unique_records)
    duplicates_pruned = raw_count - unique_count

    # Step 2: Provenance Partitioning across all unique records
    provenance_counts = {
        "measured": 0,
        "external_observation": 0,
        "estimated": 0,
        "simulated_demo": 0
    }

    empirical_records: List[Dict[str, Any]] = []
    simulated_records: List[Dict[str, Any]] = []

    for r in unique_records:
        is_syn = bool(r.get("is_synthetic", False)) or (r.get("provenance_mode") == SourceType.SYNTHETIC_DEMO)
        mode = str(r.get("provenance_mode", SourceType.MEASURED)).strip().upper()

        if is_syn:
            provenance_counts["simulated_demo"] += 1
            simulated_records.append(r)
        elif mode == SourceType.MEASURED:
            provenance_counts["measured"] += 1
            empirical_records.append(r)
        elif mode == SourceType.EXTERNAL_OBSERVATION:
            provenance_counts["external_observation"] += 1
            empirical_records.append(r)
        elif mode == SourceType.ESTIMATED:
            provenance_counts["estimated"] += 1
            empirical_records.append(r)
        else:
            provenance_counts["measured"] += 1
            empirical_records.append(r)

    # Determine working dataset based on include_synthetic
    target_records = (empirical_records + simulated_records) if include_synthetic else empirical_records

    # Step 3: Optional query filtering
    filtered_records: List[Dict[str, Any]] = []
    for r in target_records:
        if ward_id and str(r.get("ward_id", "")).strip().upper() != ward_id.strip().upper():
            continue
        if intervention_type and str(r.get("intervention_type", "")).strip().lower() != intervention_type.strip().lower():
            continue
        filtered_records.append(r)

    # Step 4: Assessing Completeness
    valid_comparisons_count = 0
    incomplete_assessments_count = 0
    incomplete_breakdown = {
        "missing_baseline": 0,
        "missing_follow_up": 0,
        "incompatible_units": 0,
        "insufficient_data": 0
    }

    # Tracking structures for groupings
    indicator_pairs_map: Dict[str, List[Dict[str, Any]]] = {}
    ward_grouping: Dict[str, Dict[str, Any]] = {}
    intervention_grouping: Dict[str, Dict[str, Any]] = {}
    warnings_counter: Dict[str, int] = {}
    source_counter: Dict[str, int] = {}

    for rec in filtered_records:
        wid = str(rec.get("ward_id", "UNKNOWN")).upper()
        itype = str(rec.get("intervention_type", "UNKNOWN"))
        status = str(rec.get("verification_status", "")).upper()

        # Initialize ward grouping
        if wid not in ward_grouping:
            ward_grouping[wid] = {
                "ward_id": wid,
                "total_assessments": 0,
                "valid_comparisons": 0,
                "incomplete_assessments": 0,
                "interventions_evaluated": set(),
                "indicators_summary": {}
            }
        ward_grouping[wid]["total_assessments"] += 1
        ward_grouping[wid]["interventions_evaluated"].add(itype)

        # Initialize intervention type grouping
        if itype not in intervention_grouping:
            intervention_grouping[itype] = {
                "intervention_type": itype,
                "total_assessments": 0,
                "valid_comparisons": 0,
                "incomplete_assessments": 0,
                "wards_covered": set(),
                "indicators_summary": {}
            }
        intervention_grouping[itype]["total_assessments"] += 1
        intervention_grouping[itype]["wards_covered"].add(wid)

        # Collect warnings
        for w in rec.get("data_quality_warnings", []):
            warnings_counter[str(w)] = warnings_counter.get(str(w), 0) + 1

        indicators_dict = rec.get("indicators") or rec.get("results_by_indicator") or {}
        has_valid_pair = False
        record_incomplete_reason = None

        if not indicators_dict:
            record_incomplete_reason = "insufficient_data"

        for ind_name, ind_res in indicators_dict.items():
            if not isinstance(ind_res, dict):
                continue

            canon_key = resolve_canonical_indicator(ind_name) or ind_name.strip().lower()
            ind_info = INDICATOR_REGISTRY.get(canon_key, {})
            cat = ind_info.get("hazard_category", "cross_cutting")
            canon_u = ind_info.get("canonical_unit", ind_res.get("unit", ""))

            # Hazard filter if requested
            if hazard_category and cat.lower() != hazard_category.strip().lower():
                continue

            b_val = ind_res.get("baseline_value")
            f_val = ind_res.get("follow_up_value")
            diff = ind_res.get("difference")
            pct = ind_res.get("percentage_change")
            unit_raw = ind_res.get("unit", "")
            q_status = str(ind_res.get("quality_status", "")).upper()

            # Collect source information
            for st in ind_res.get("source_types", []):
                source_counter[st] = source_counter.get(st, 0) + 1

            # Check individual indicator completeness
            if q_status == QualityStatus.MISSING_BASELINE or (b_val is None and f_val is not None):
                if not record_incomplete_reason:
                    record_incomplete_reason = "missing_baseline"
                continue
            elif q_status == QualityStatus.MISSING_FOLLOW_UP or (b_val is not None and f_val is None):
                if not record_incomplete_reason:
                    record_incomplete_reason = "missing_follow_up"
                continue
            elif q_status == QualityStatus.INCOMPATIBLE_UNITS:
                if not record_incomplete_reason:
                    record_incomplete_reason = "incompatible_units"
                continue

            # Valid pair requires both values and diff
            if b_val is not None and f_val is not None and diff is not None:
                # Enforce unit compatibility: normalize to canonical unit if convertible
                b_norm, ok_b = convert_value_to_canonical(b_val, unit_raw, canon_u) if canon_u else (b_val, True)
                f_norm, ok_f = convert_value_to_canonical(f_val, unit_raw, canon_u) if canon_u else (f_val, True)
                diff_norm = round(f_norm - b_norm, 4) if (ok_b and ok_f) else diff

                if not ok_b or not ok_f:
                    if not record_incomplete_reason:
                        record_incomplete_reason = "incompatible_units"
                    continue

                has_valid_pair = True

                pair_record = {
                    "assessment_id": rec.get("assessment_id"),
                    "ward_id": wid,
                    "intervention_type": itype,
                    "baseline_value": b_norm,
                    "follow_up_value": f_norm,
                    "difference": diff_norm,
                    "percentage_change": pct,
                    "unit": canon_u or unit_raw,
                    "is_improvement": ind_res.get("is_improvement"),
                    "beneficial_direction": ind_info.get("beneficial_direction", Direction.DECREASE_IS_BENEFICIAL),
                    "hazard_category": cat
                }

                if canon_key not in indicator_pairs_map:
                    indicator_pairs_map[canon_key] = []
                indicator_pairs_map[canon_key].append(pair_record)

                # Track in ward grouping
                if canon_key not in ward_grouping[wid]["indicators_summary"]:
                    ward_grouping[wid]["indicators_summary"][canon_key] = {
                        "count": 0, "sum_diff": 0.0, "unit": canon_u or unit_raw, "improved_count": 0
                    }
                w_ind = ward_grouping[wid]["indicators_summary"][canon_key]
                w_ind["count"] += 1
                w_ind["sum_diff"] += diff_norm
                if ind_res.get("is_improvement") is True:
                    w_ind["improved_count"] += 1

                # Track in intervention grouping
                if canon_key not in intervention_grouping[itype]["indicators_summary"]:
                    intervention_grouping[itype]["indicators_summary"][canon_key] = {
                        "count": 0, "sum_diff": 0.0, "unit": canon_u or unit_raw, "improved_count": 0
                    }
                i_ind = intervention_grouping[itype]["indicators_summary"][canon_key]
                i_ind["count"] += 1
                i_ind["sum_diff"] += diff_norm
                if ind_res.get("is_improvement") is True:
                    i_ind["improved_count"] += 1

        if has_valid_pair:
            valid_comparisons_count += 1
            ward_grouping[wid]["valid_comparisons"] += 1
            intervention_grouping[itype]["valid_comparisons"] += 1
        else:
            incomplete_assessments_count += 1
            ward_grouping[wid]["incomplete_assessments"] += 1
            intervention_grouping[itype]["incomplete_assessments"] += 1
            if record_incomplete_reason:
                incomplete_breakdown[record_incomplete_reason] += 1
            else:
                incomplete_breakdown["insufficient_data"] += 1

    # Step 5: Compute indicator-level aggregate metrics
    by_indicator: Dict[str, Dict[str, Any]] = {}
    for canon_key, pairs in indicator_pairs_map.items():
        n = len(pairs)
        if n == 0:
            continue

        b_vals = [p["baseline_value"] for p in pairs]
        f_vals = [p["follow_up_value"] for p in pairs]
        d_vals = [p["difference"] for p in pairs]
        pct_vals = [p["percentage_change"] for p in pairs if p["percentage_change"] is not None]

        improved_c = sum(1 for p in pairs if p["is_improvement"] is True)
        unimproved_c = sum(1 for p in pairs if p["is_improvement"] is False and p["difference"] != 0.0)
        neutral_c = sum(1 for p in pairs if p["difference"] == 0.0)

        ind_info = INDICATOR_REGISTRY.get(canon_key, {})
        disp_name = ind_info.get("display_name", canon_key.replace("_", " ").title())
        h_cat = ind_info.get("hazard_category", "cross_cutting")
        u_name = pairs[0]["unit"]
        b_dir = pairs[0]["beneficial_direction"]

        by_indicator[canon_key] = {
            "canonical_indicator": canon_key,
            "display_name": disp_name,
            "hazard_category": h_cat,
            "unit": u_name,
            "aggregation_method": "PAIRWISE_ARITHMETIC_MEAN_OF_VALID_RECORDS",
            "sample_size": n,
            "baseline_aggregate_value": round(sum(b_vals) / n, 2),
            "follow_up_aggregate_value": round(sum(f_vals) / n, 2),
            "mean_absolute_difference": round(sum(d_vals) / n, 2),
            "mean_percentage_change": round(sum(pct_vals) / len(pct_vals), 2) if pct_vals else None,
            "min_baseline": min(b_vals),
            "max_baseline": max(b_vals),
            "min_follow_up": min(f_vals),
            "max_follow_up": max(f_vals),
            "beneficial_direction": b_dir,
            "improved_count": improved_c,
            "unimproved_count": unimproved_c,
            "neutral_count": neutral_c,
            "improvement_rate_pct": round((improved_c / n) * 100.0, 1) if n > 0 else 0.0
        }

    # Format ward grouping for JSON serialization
    formatted_by_ward: Dict[str, Dict[str, Any]] = {}
    for wid, wdata in ward_grouping.items():
        ind_summaries = {}
        for ik, iv in wdata["indicators_summary"].items():
            cnt = iv["count"]
            ind_summaries[ik] = {
                "sample_size": cnt,
                "mean_difference": round(iv["sum_diff"] / cnt, 2) if cnt > 0 else 0.0,
                "unit": iv["unit"],
                "improved_count": iv["improved_count"]
            }
        formatted_by_ward[wid] = {
            "ward_id": wid,
            "total_assessments": wdata["total_assessments"],
            "valid_comparisons": wdata["valid_comparisons"],
            "incomplete_assessments": wdata["incomplete_assessments"],
            "interventions_evaluated": sorted(list(wdata["interventions_evaluated"])),
            "indicators": ind_summaries
        }

    # Format intervention grouping for JSON serialization
    formatted_by_intervention: Dict[str, Dict[str, Any]] = {}
    for itype, idata in intervention_grouping.items():
        ind_summaries = {}
        for ik, iv in idata["indicators_summary"].items():
            cnt = iv["count"]
            ind_summaries[ik] = {
                "sample_size": cnt,
                "mean_difference": round(iv["sum_diff"] / cnt, 2) if cnt > 0 else 0.0,
                "unit": iv["unit"],
                "improved_count": iv["improved_count"]
            }
        formatted_by_intervention[itype] = {
            "intervention_type": itype,
            "total_assessments": idata["total_assessments"],
            "valid_comparisons": idata["valid_comparisons"],
            "incomplete_assessments": idata["incomplete_assessments"],
            "wards_covered": sorted(list(idata["wards_covered"])),
            "indicators": ind_summaries
        }

    return {
        "status": "SUCCESS",
        "data_integrity_mode": "INCLUDES_SIMULATED_DEMO" if include_synthetic else "REAL_WORLD_VERIFIED_ONLY",
        "data_integrity_notice": (
            "Real-world verified outcomes are strictly segregated from simulated demonstration records. "
            "Missing baseline or follow-up observations are never imputed as zero. "
            "Observational before-and-after differences do not imply direct counterfactual causation."
        ),
        "kpis": {
            "total_assessments_recorded": raw_count,
            "unique_assessments_count": unique_count,
            "duplicate_records_pruned": duplicates_pruned,
            "valid_before_after_comparisons_count": valid_comparisons_count,
            "incomplete_assessments_count": incomplete_assessments_count,
            "provenance_counts": provenance_counts
        },
        "incomplete_breakdown": incomplete_breakdown,
        "by_indicator": by_indicator,
        "by_ward": formatted_by_ward,
        "by_intervention_type": formatted_by_intervention,
        "data_quality_warnings_summary": warnings_counter,
        "source_information": source_counter,
        "aggregation_method": "PAIRWISE_ARITHMETIC_MEAN_OF_VALID_RECORDS (Missing values strictly excluded; zero-imputation prohibited)",
        "causal_attribution_caveat": ATTRIBUTION_DISCLAIMER
    }


# ---------------------------------------------------------------------------
# INTEGRATION BOUNDARIES: ACTION CENTRE & LEARNING LOOP
# ---------------------------------------------------------------------------

def validate_intervention_against_action_centre(
    intervention_id: str,
    action_centre_catalog: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Consumes intervention metadata from the Action Centre through its verified interface
    without modifying the Action Centre's implementation or workflow.
    """
    if action_centre_catalog is None:
        try:
            from backend.intervention_engine import INTERVENTIONS_CATALOG
            catalog = INTERVENTIONS_CATALOG
        except ImportError:
            catalog = {}
    else:
        catalog = action_centre_catalog

    entry = catalog.get(intervention_id)
    if not entry:
        return {
            "is_recognized": False,
            "intervention_id": intervention_id,
            "notice": f"Intervention '{intervention_id}' is not in Action Centre catalog."
        }

    return {
        "is_recognized": True,
        "intervention_id": intervention_id,
        "name": entry.get("name", intervention_id),
        "intervention_type": entry.get("intervention_type", "UNKNOWN"),
        "related_hazard": entry.get("related_hazard", "cross_cutting"),
        "base_risk_reduction": entry.get("base_risk_reduction", 0.0),
        "unit_cost_inr": entry.get("unit_cost_inr", 0.0),
        "crew_required": entry.get("crew_required", 0)
    }


def export_learning_loop_signals(
    ward_id: Optional[str] = None,
    intervention_id: Optional[str] = None,
    include_synthetic: bool = False
) -> List[Dict[str, Any]]:
    """
    Exposes verified empirical outcome signals through a clean, documented,
    read-only interface for downstream consumption by the Learning Loop.
    
    Principles:
    - Purely observational: provides observed delta and calibration weight.
    - Does NOT mutate models, weights, or risk scores directly.
    - Strictly segregates synthetic demonstration records from empirical signals.
    """
    from backend.database import get_all_impact_assessments

    records = get_all_impact_assessments(
        ward_id=ward_id.strip().upper() if ward_id else None,
        intervention_id=intervention_id.strip() if intervention_id else None,
        limit=500
    )

    signals: List[Dict[str, Any]] = []

    for r in records:
        is_syn = bool(r.get("is_synthetic", False)) or (r.get("provenance_mode") == SourceType.SYNTHETIC_DEMO)
        if is_syn and not include_synthetic:
            continue

        prov = str(r.get("provenance_mode", SourceType.MEASURED)).upper()
        # Set empirical calibration weight
        if prov == SourceType.MEASURED:
            calib_weight = 1.0
        elif prov == SourceType.EXTERNAL_OBSERVATION:
            calib_weight = 0.85
        elif prov == SourceType.ESTIMATED:
            calib_weight = 0.50
        else:
            calib_weight = 0.0  # Synthetic records have 0 calibration weight for real models

        indicators = r.get("indicators") or r.get("results_by_indicator") or {}
        for ind_name, ind_data in indicators.items():
            if not isinstance(ind_data, dict):
                continue
            diff = ind_data.get("difference")
            if diff is None:
                continue

            is_imp = ind_data.get("is_improvement")
            if is_imp is True:
                learning_feedback = "EFFECTIVE_EMPIRICAL_BENEFIT"
            elif diff == 0.0:
                learning_feedback = "NEUTRAL_NO_EMPIRICAL_SHIFT"
            else:
                learning_feedback = "UNDERPERFORMING_RESIDUAL_ALERT"

            signals.append({
                "assessment_id": r.get("assessment_id"),
                "ward_id": r.get("ward_id"),
                "intervention_id": r.get("intervention_id"),
                "intervention_type": r.get("intervention_type"),
                "indicator": ind_name,
                "canonical_unit": ind_data.get("unit"),
                "baseline_value": ind_data.get("baseline_value"),
                "follow_up_value": ind_data.get("follow_up_value"),
                "observed_absolute_difference": diff,
                "observed_percentage_change": ind_data.get("percentage_change"),
                "is_improvement": is_imp,
                "provenance_mode": prov,
                "is_synthetic": is_syn,
                "calibration_weight": calib_weight,
                "learning_feedback": learning_feedback,
                "created_at": r.get("created_at"),
                "updated_at": r.get("updated_at")
            })

    return signals



