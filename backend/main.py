"""
ClimateShield - FastAPI Decision Support System Server
Exposes Heat Action APIs, Open-Meteo WBGT forecasting, and Optimization endpoints.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional

from backend.wbgt_pipeline import (
    fetch_open_meteo_weather,
    process_wbgt_forecast,
    get_ward_wbgt_risk,
    AHMEDABAD_WARDS
)
from backend.optimizer import solve_resource_allocation

app = FastAPI(
    title="ClimateShield API - Ahmedabad Heat Decision Support",
    description="Closed-loop decision support system for heatwave management, WBGT forecasting, and equitable resource allocation.",
    version="1.0.0"
)

# Enable CORS for React Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class OptimizationRequest(BaseModel):
    total_budget_inr: float = Field(500000.0, ge=10000, le=10000000, description="Total monetary budget in INR")
    total_crew_members: int = Field(40, ge=1, le=500, description="Total available deployment personnel")
    total_water_cap_l: float = Field(30000.0, ge=1000, le=500000, description="Daily water cap limit in Liters")
    equity_slider: float = Field(0.5, ge=0.0, le=1.0, description="Equity priority slider (0.0 = pure efficiency, 1.0 = maximum equity)")


@app.get("/")
def read_root():
    return {
        "system": "ClimateShield Decision Support System",
        "target_city": "Ahmedabad, Gujarat, India",
        "status": "OPERATIONAL",
        "endpoints": [
            "/api/weather/wbgt",
            "/api/wards",
            "/api/optimize"
        ]
    }


@app.get("/api/weather/wbgt")
async def get_wbgt_weather(lat: float = 23.0225, lon: float = 72.5714):
    """
    Fetches Open-Meteo hourly weather for Ahmedabad and calculates Wet Bulb Globe Temperature (WBGT).
    """
    try:
        raw_weather = await fetch_open_meteo_weather(lat, lon)
        forecast_hourly = process_wbgt_forecast(raw_weather)
        
        # Calculate current outdoor WBGT (using peak afternoon or current hour)
        current_sample = forecast_hourly[14] if len(forecast_hourly) > 14 else forecast_hourly[0]
        ward_risks = get_ward_wbgt_risk(current_sample["wbgt_outdoor_c"])
        
        return {
            "city": "Ahmedabad",
            "coordinates": {"lat": lat, "lon": lon},
            "current_heat_status": {
                "timestamp": current_sample["timestamp"],
                "temperature_c": current_sample["temperature_c"],
                "relative_humidity": current_sample["relative_humidity"],
                "solar_radiation_wm2": current_sample["solar_radiation_wm2"],
                "wbgt_outdoor_c": current_sample["wbgt_outdoor_c"],
                "hazard_level": current_sample["risk"]["tier"],
                "action_recommendation": current_sample["risk"]["action"]
            },
            "hourly_forecast": forecast_hourly[:24],
            "ward_heat_risks": ward_risks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching WBGT weather data: {str(e)}")


@app.get("/api/wards")
def get_ahmedabad_wards():
    """Returns baseline vulnerability indicators for Ahmedabad Wards."""
    return {"wards": AHMEDABAD_WARDS}


@app.post("/api/optimize")
def run_optimization(req: OptimizationRequest):
    """
    Runs Knapsack Resource Allocation Optimization under budget, crew, water constraints and equity slider controls.
    """
    try:
        result = solve_resource_allocation(
            total_budget_inr=req.total_budget_inr,
            total_crew_members=req.total_crew_members,
            total_water_cap_l=req.total_water_cap_l,
            equity_slider=req.equity_slider
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization solver error: {str(e)}")
