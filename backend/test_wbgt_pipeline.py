"""
ClimateShield - WBGT Pipeline Automated Test Suite
Verifies Open-Meteo API integration, WBGT physics formulas, and Ward Hazard Indexing.
"""

import json
import asyncio
import os
import sys

# Ensure backend module is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from backend.wbgt_pipeline import (
    fetch_open_meteo_weather,
    process_wbgt_forecast,
    calculate_stull_natural_wet_bulb,
    calculate_swbgt,
    calculate_outdoor_wbgt,
    classify_wbgt_risk,
    get_ward_wbgt_risk,
    AHMEDABAD_LAT,
    AHMEDABAD_LON
)


async def run_wbgt_tests():
    print("==================================================")
    print("🌡️  CLIMATESHIELD - WBGT PIPELINE INTEGRATION TEST")
    print("==================================================")
    print(f"Target City: Ahmedabad, Gujarat, India")
    print(f"Coordinates: Latitude {AHMEDABAD_LAT}, Longitude {AHMEDABAD_LON}")
    print("--------------------------------------------------")

    # 1. Physics Formula Unit Tests
    print("\n[TEST 1] Physics Formula Validation")
    test_temp = 38.0  # 38°C dry bulb
    test_rh = 30.0    # 30% RH
    test_rad = 800.0  # 800 W/m² solar radiation
    test_wind = 2.0   # 2 m/s wind speed

    tnw = calculate_stull_natural_wet_bulb(test_temp, test_rh)
    swbgt = calculate_swbgt(test_temp, test_rh)
    wbgt_outdoor = calculate_outdoor_wbgt(test_temp, test_rh, test_rad, test_wind)
    risk = classify_wbgt_risk(wbgt_outdoor)

    print(f"  Dry-Bulb Temp : {test_temp}°C")
    print(f"  Rel Humidity  : {test_rh}%")
    print(f"  Solar Irradiance: {test_rad} W/m²")
    print(f"  Stull Wet-Bulb: {tnw:.2f}°C")
    print(f"  Simplified WBGT: {swbgt:.2f}°C")
    print(f"  Outdoor WBGT  : {wbgt_outdoor:.2f}°C")
    print(f"  Risk Tier     : {risk['tier']} (Color: {risk['color']})")

    assert 20.0 <= tnw <= 30.0, "Stull wet bulb out of expected bounds"
    assert wbgt_outdoor > tnw, "Outdoor WBGT should incorporate solar radiation"
    print("  ✅ Physics unit tests PASSED")

    # 2. Open-Meteo API Live Fetch Test
    print("\n[TEST 2] Fetching Live Forecast from Open-Meteo API...")
    raw_weather = await fetch_open_meteo_weather()
    assert "hourly" in raw_weather, "Open-Meteo payload missing 'hourly' key"
    assert "temperature_2m" in raw_weather["hourly"], "Missing temperature_2m array"

    forecast_series = process_wbgt_forecast(raw_weather)
    print(f"  Received {len(forecast_series)} hourly forecast data points.")
    assert len(forecast_series) >= 24, "Expected at least 24 forecast hours"

    # Peak Heat Sample
    peak_sample = max(forecast_series, key=lambda x: x["wbgt_outdoor_c"])
    print(f"\n  Peak Heat Hour Forecast:")
    print(f"    Timestamp     : {peak_sample['timestamp']}")
    print(f"    Air Temp      : {peak_sample['temperature_c']}°C")
    print(f"    Humidity      : {peak_sample['relative_humidity']}%")
    print(f"    Solar Rad     : {peak_sample['solar_radiation_wm2']} W/m²")
    print(f"    Outdoor WBGT  : {peak_sample['wbgt_outdoor_c']}°C")
    print(f"    Risk Category : {peak_sample['risk']['tier']} - {peak_sample['risk']['action']}")
    print("  ✅ Live Open-Meteo fetch PASSED")

    # 3. Ward Hazard Assessment
    print("\n[TEST 3] Ward-Level Dynamic Risk Indexing")
    ward_risks = get_ward_wbgt_risk(peak_sample["wbgt_outdoor_c"])
    print(f"  Assessed {len(ward_risks)} Ahmedabad Wards:")

    for ward in ward_risks:
        print(f"    • {ward['name']:<20} | Base Vuln: {ward['vulnerability_score']:.2f} | Eff WBGT: {ward['effective_wbgt_c']}°C [{ward['current_risk_level']}]")

    assert len(ward_risks) == 10, "Expected 10 Ahmedabad wards"
    print("  ✅ Ward risk indexing PASSED")

    # 4. Save test results JSON to backend/data/
    output_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "wbgt_test_results.json")

    test_data = {
        "city": "Ahmedabad",
        "coordinates": {"lat": AHMEDABAD_LAT, "lon": AHMEDABAD_LON},
        "test_status": "PASSED",
        "peak_forecast_sample": peak_sample,
        "ward_risk_assessments": ward_risks
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(test_data, f, indent=2)

    print(f"\n📁 Saved verified WBGT test output to: {output_path}")
    print("==================================================")
    print("🎉 ALL WBGT PIPELINE TESTS PASSED SUCCESSFULLY!")
    print("==================================================")


if __name__ == "__main__":
    asyncio.run(run_wbgt_tests())
