"""
ClimateShield - Open-Meteo WBGT Pipeline for Ahmedabad
Calculates Wet Bulb Globe Temperature (WBGT) and heat hazard classification.
"""

import math
from typing import Dict, List, Any, Optional
import httpx

# Ahmedabad Location Constants
AHMEDABAD_LAT = 23.0225
AHMEDABAD_LON = 72.5714
AHMEDABAD_TIMEZONE = "Asia/Kolkata"

# Ahmedabad Wards with baseline vulnerability indexes (0.0 - 1.0)
AHMEDABAD_WARDS = [
    {"id": "W1", "name": "Danilimda", "slum_density": 0.85, "outdoor_labor_ratio": 0.75, "elderly_ratio": 0.20, "baseline_heat_risk": 0.92},
    {"id": "W2", "name": "Behrampura", "slum_density": 0.80, "outdoor_labor_ratio": 0.70, "elderly_ratio": 0.18, "baseline_heat_risk": 0.88},
    {"id": "W3", "name": "Asarwa", "slum_density": 0.65, "outdoor_labor_ratio": 0.60, "elderly_ratio": 0.25, "baseline_heat_risk": 0.78},
    {"id": "W4", "name": "Bapunagar", "slum_density": 0.75, "outdoor_labor_ratio": 0.65, "elderly_ratio": 0.22, "baseline_heat_risk": 0.84},
    {"id": "W5", "name": "Khadia (Old City)", "slum_density": 0.40, "outdoor_labor_ratio": 0.45, "elderly_ratio": 0.35, "baseline_heat_risk": 0.72},
    {"id": "W6", "name": "Amraiwadi", "slum_density": 0.70, "outdoor_labor_ratio": 0.68, "elderly_ratio": 0.19, "baseline_heat_risk": 0.81},
    {"id": "W7", "name": "Vatva", "slum_density": 0.78, "outdoor_labor_ratio": 0.72, "elderly_ratio": 0.17, "baseline_heat_risk": 0.86},
    {"id": "W8", "name": "Sabarmati", "slum_density": 0.35, "outdoor_labor_ratio": 0.35, "elderly_ratio": 0.28, "baseline_heat_risk": 0.55},
    {"id": "W9", "name": "Maninagar", "slum_density": 0.30, "outdoor_labor_ratio": 0.30, "elderly_ratio": 0.30, "baseline_heat_risk": 0.50},
    {"id": "W10", "name": "Naroda", "slum_density": 0.60, "outdoor_labor_ratio": 0.58, "elderly_ratio": 0.21, "baseline_heat_risk": 0.70}
]


def calculate_vapor_pressure(temp_c: float, rh_percent: float) -> float:
    """Calculates actual vapor pressure (hPa/mbar) from dry-bulb temp and RH."""
    es = 6.105 * math.exp((17.27 * temp_c) / (237.7 + temp_c))
    return (rh_percent / 100.0) * es


def calculate_stull_natural_wet_bulb(temp_c: float, rh_percent: float) -> float:
    """
    Stull (2011) empirical formula for Natural Wet Bulb Temperature (Tnw) in °C.
    Valid for T between -20°C and 50°C, RH between 5% and 99%.
    """
    t = temp_c
    rh = rh_percent
    
    tnw = (
        t * math.atan(0.151977 * math.sqrt(rh + 8.313659))
        + math.atan(t + rh)
        - math.atan(rh - 1.676331)
        + 0.00391838 * (rh ** 1.5) * math.atan(0.023101 * rh)
        - 4.686035
    )
    return tnw


def calculate_swbgt(temp_c: float, rh_percent: float) -> float:
    """
    Simplified Wet Bulb Globe Temperature (sWBGT) formula (Australian BOM / ISO).
    sWBGT = 0.567 * T + 0.393 * e + 3.94
    """
    e = calculate_vapor_pressure(temp_c, rh_percent)
    return 0.567 * temp_c + 0.393 * e + 3.94


def calculate_outdoor_wbgt(
    temp_c: float,
    rh_percent: float,
    direct_radiation_wm2: float = 0.0,
    wind_speed_ms: float = 1.0
) -> float:
    """
    Calculates outdoor WBGT (°C) incorporating solar radiation and wind speed effects.
    Formula: WBGT = 0.7 * Tnw + 0.2 * Tg + 0.1 * Ta
    Where:
    - Tnw: Natural wet bulb temperature (Stull 2011)
    - Tg: Globe temperature (approximated: Ta + 0.0149 * SolarRad - 0.057 * WindSpeed)
    - Ta: Ambient dry bulb temperature
    """
    tnw = calculate_stull_natural_wet_bulb(temp_c, rh_percent)
    # Globe temperature approximation
    tg = temp_c + (0.0149 * direct_radiation_wm2) - (0.057 * max(0.5, wind_speed_ms))
    
    wbgt = (0.7 * tnw) + (0.2 * tg) + (0.1 * temp_c)
    return round(wbgt, 2)


def classify_wbgt_risk(wbgt_c: float) -> Dict[str, Any]:
    """Classifies WBGT value into risk tiers according to Heat Health Action Standards."""
    if wbgt_c < 26.0:
        return {
            "tier": "LOW",
            "color": "#10B981",  # Green
            "action": "Normal activities. Ensure basic hydration.",
            "risk_score": 0.2
        }
    elif wbgt_c < 29.0:
        return {
            "tier": "MODERATE",
            "color": "#F59E0B",  # Yellow
            "action": "Caution for outdoor workers and elderly. Provide shaded rest areas.",
            "risk_score": 0.45
        }
    elif wbgt_c < 31.0:
        return {
            "tier": "HIGH",
            "color": "#F97316",  # Orange
            "action": "High heat stress. Enforce mandatory 15-min rest breaks per hour.",
            "risk_score": 0.7
        }
    elif wbgt_c < 33.0:
        return {
            "tier": "EXTREME",
            "color": "#EF4444",  # Red
            "action": "Extreme danger! Deploy emergency cooling shelters and hydration kiosks.",
            "risk_score": 0.9
        }
    else:
        return {
            "tier": "CRITICAL",
            "color": "#7F1D1D",  # Dark Red/Purple
            "action": "CRITICAL EMERGENCY! Cancel non-essential outdoor work. Water tanker dispatch required.",
            "risk_score": 1.0
        }


async def fetch_open_meteo_weather(
    lat: float = AHMEDABAD_LAT,
    lon: float = AHMEDABAD_LON
) -> Dict[str, Any]:
    """Fetches hourly weather forecast from Open-Meteo API for Ahmedabad."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "dew_point_2m",
            "apparent_temperature",
            "direct_normal_irradiance",
            "wind_speed_10m"
        ],
        "timezone": AHMEDABAD_TIMEZONE,
        "forecast_days": 2
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()


def process_wbgt_forecast(raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Processes Open-Meteo API raw response into structured hourly WBGT series."""
    hourly = raw_data.get("hourly", {})
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    rhs = hourly.get("relative_humidity_2m", [])
    rads = hourly.get("direct_normal_irradiance", [])
    winds = hourly.get("wind_speed_10m", [])
    
    results = []
    for i in range(len(times)):
        t_c = temps[i]
        rh = rhs[i]
        rad = rads[i] if i < len(rads) and rads[i] is not None else 0.0
        wind = winds[i] if i < len(winds) and winds[i] is not None else 1.0
        
        swbgt = calculate_swbgt(t_c, rh)
        wbgt_outdoor = calculate_outdoor_wbgt(t_c, rh, rad, wind)
        classification = classify_wbgt_risk(wbgt_outdoor)
        
        results.append({
            "timestamp": times[i],
            "temperature_c": t_c,
            "relative_humidity": rh,
            "solar_radiation_wm2": rad,
            "wind_speed_ms": wind,
            "swbgt_c": round(swbgt, 2),
            "wbgt_outdoor_c": wbgt_outdoor,
            "risk": classification
        })
        
    return results


def get_ward_wbgt_risk(current_wbgt: float) -> List[Dict[str, Any]]:
    """Calculates ward-specific dynamic risk scores based on citywide WBGT and ward vulnerability."""
    ward_results = []
    for ward in AHMEDABAD_WARDS:
        # Dynamic heat hazard scaled by ward baseline vulnerability
        effective_heat_risk = current_wbgt * (0.75 + 0.25 * ward["baseline_heat_risk"])
        classified = classify_wbgt_risk(effective_heat_risk)
        
        ward_results.append({
            **ward,
            "effective_wbgt_c": round(effective_heat_risk, 2),
            "current_risk_level": classified["tier"],
            "risk_color": classified["color"],
            "vulnerability_score": round(ward["baseline_heat_risk"], 2)
        })
    return ward_results


# Synchronous fallback runner for quick script tests
def fetch_and_process_sync() -> List[Dict[str, Any]]:
    import requests
    url = f"https://api.open-meteo.com/v1/forecast?latitude={AHMEDABAD_LAT}&longitude={AHMEDABAD_LON}&hourly=temperature_2m,relative_humidity_2m,direct_normal_irradiance,wind_speed_10m&timezone={AHMEDABAD_TIMEZONE}&forecast_days=1"
    resp = requests.get(url, timeout=10)
    return process_wbgt_forecast(resp.json())


if __name__ == "__main__":
    print("Testing Open-Meteo WBGT Pipeline for Ahmedabad...")
    data = fetch_and_process_sync()
    print(f"Fetched {len(data)} hourly data points.")
    if data:
        sample = data[14]  # 2 PM sample
        print(f"Sample at {sample['timestamp']}:")
        print(f"  Temp: {sample['temperature_c']}°C | RH: {sample['relative_humidity']}% | Radiation: {sample['solar_radiation_wm2']} W/m²")
        print(f"  WBGT (Outdoor): {sample['wbgt_outdoor_c']}°C")
        print(f"  Risk Tier: {sample['risk']['tier']} - {sample['risk']['action']}")
