"""
ClimateShield - FastAPI Decision Support System Server
Exposes Heat Action APIs, Open-Meteo WBGT forecasting, and Optimization endpoints.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
import time

from backend.wbgt_pipeline import (
    fetch_open_meteo_weather,
    process_wbgt_forecast,
    get_ward_wbgt_risk,
    AHMEDABAD_WARDS
)
from backend.optimizer import (
    solve_resource_allocation,
    optimize_from_combined_climate_results,
    RISK_CATEGORY_INTERVENTION_MAP,
    INTERVENTIONS
)
from backend.water_engine import (
    assess_citywide_water_risk,
    get_single_ward_water_risk,
    DEMONSTRATION_SCENARIOS,
    calculate_waterlogging_risk,
    calculate_water_shortage_risk,
    AHMEDABAD_LAT,
    AHMEDABAD_LON
)
from backend.climate_risk_engine import (
    evaluate_combined_climate_risk,
    SCORING_MODES,
    validate_and_normalize_weights
)
from backend.intervention_engine import (
    generate_intervention_recommendations,
    run_what_if_simulation,
    INTERVENTIONS_CATALOG,
    PROVENANCE_LABELS
)
from backend.data_sources import (
    ERA5LandClient,
    ECOSTRESSClient,
    DataFusionEngine,
    DataSourcesService
)
from backend.action_centre import (
    get_action_store,
    generate_actions_from_climate_risk,
    generate_actions_from_interventions,
    generate_rule_based_recommendations,
    build_action_centre_dashboard,
    get_prioritized_actions,
    get_ward_wise_action_summary,
    evaluate_risk_data_freshness,
    DEFAULT_RECOMMENDATION_THRESHOLDS,
    RULE_DEFINITIONS,
    ACTION_RESOURCE_ESTIMATES,
    ACTION_TYPES,
    VALID_STATUSES,
    HUMAN_APPROVAL_NOTICE as ACTION_CENTRE_ADVISORY,
)

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
    wards: Optional[List[Dict[str, Any]]] = Field(None, description="Optional custom ward risk assessments to optimize")


@app.get("/")
def read_root():
    return {
        "system": "ClimateShield Decision Support System",
        "target_city": "Ahmedabad, Gujarat, India",
        "status": "OPERATIONAL",
        "endpoints": [
            "/api/weather/wbgt",
            "/api/wards",
            "/api/wards/geojson",
            "/api/risk/monte-carlo",
            "/api/optimize",
            "/api/optimize/climate",
            "/api/optimize/interventions",
            "/api/water/wards",
            "/api/water/wards/{ward_id}",
            "/api/water/risk",
            "/api/water/scenarios",
            "/api/water/assess",
            "/api/climate/combined-risk",
            "/api/interventions/catalog",
            "/api/interventions/recommend",
            "/api/interventions/ranked",
            "/api/interventions/wards/{ward_id}",
            "/api/interventions/simulate",
            "/api/data-sources/era5",
            "/api/data-sources/ecostress",
            "/api/data-sources/fusion",
            "/api/action-centre/dashboard",
            "/api/action-centre/actions",
            "/api/action-centre/actions/{action_id}",
            "/api/action-centre/actions/{action_id}/status",
            "/api/action-centre/generate-from-risk",
            "/api/action-centre/generate-from-interventions"
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


@app.get("/api/wards/geojson")
def get_ahmedabad_wards_geojson():
    """Returns official Ahmedabad Wards GeoJSON spatial boundary data."""
    import json
    import os
    geojson_path = os.path.join(os.path.dirname(__file__), "data", "Ahmedabad_Wards.geojson")
    if not os.path.exists(geojson_path):
        raise HTTPException(status_code=404, detail="GeoJSON boundary file not found")
    with open(geojson_path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get("/api/risk/monte-carlo")
def get_ward_risk_monte_carlo(
    simulations: int = Query(500, ge=50, le=2000, description="Number of Monte Carlo weight sensitivity draws"),
    weight_hazard: float = Query(0.40, ge=0.0, le=1.0),
    weight_exposure: float = Query(0.30, ge=0.0, le=1.0),
    weight_vulnerability: float = Query(0.30, ge=0.0, le=1.0)
):
    """
    Calculates explainable IPCC percentile risk scores (Risk = H x E x V) for each ward,
    and runs Monte Carlo draws over index weights to generate uncertainty bands (rank stability).
    """
    try:
        from backend.risk_monte_carlo import calculate_ward_risk_and_monte_carlo
        results = calculate_ward_risk_and_monte_carlo(
            n_simulations=simulations,
            w_h=weight_hazard,
            w_e=weight_exposure,
            w_v=weight_vulnerability
        )
        return {
            "city": "Ahmedabad",
            "total_wards": len(results),
            "monte_carlo_draws": simulations,
            "nominal_weights": {
                "hazard": weight_hazard,
                "exposure": weight_exposure,
                "vulnerability": weight_vulnerability
            },
            "wards_risk": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing Monte Carlo Risk Engine: {str(e)}")




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
            equity_slider=req.equity_slider,
            wards=req.wards
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization solver error: {str(e)}")


class ClimateOptimizationRequest(BaseModel):
    total_budget_inr: float = Field(500000.0, ge=10000, le=10000000, description="Total monetary budget in INR")
    total_crew_members: int = Field(40, ge=1, le=500, description="Total available deployment personnel")
    total_water_cap_l: float = Field(30000.0, ge=1000, le=500000, description="Daily water cap limit in Liters")
    equity_slider: float = Field(0.5, ge=0.0, le=1.0, description="Equity priority slider (0.0 to 1.0)")
    scenario_id: Optional[str] = Field(None, description="Optional preset demo scenario ID (compound_hazard, monsoon_cloudburst, summer_drought_scarcity)")
    heat_wbgt: Optional[float] = Field(None, ge=15.0, le=45.0, description="Optional custom outdoor WBGT in °C")
    weight_heat: float = Field(0.5, ge=0.0, le=1.0)
    weight_water: float = Field(0.5, ge=0.0, le=1.0)
    scoring_mode: str = Field("COMPOUND_SYNERGY")


@app.get("/api/optimize/interventions")
def get_interventions_catalog():
    """
    Returns documentation of all available interventions mapped by risk category (Heat, Waterlogging, Shortage),
    with assumed municipal costs, required resources, simulated benefits, and justification templates.
    """
    return {
        "status": "SUCCESS",
        "total_interventions": len(INTERVENTIONS),
        "risk_category_mappings": RISK_CATEGORY_INTERVENTION_MAP,
        "interventions": INTERVENTIONS
    }


@app.post("/api/optimize/climate")
async def run_climate_optimization(req: ClimateOptimizationRequest):
    """
    Directly connects Combined Multi-Hazard Climate Risk outputs (Heat + Water) to the Resource Optimizer.
    Evaluates all 48 wards and produces an explainable, hazard-matched dispatch plan pending human sign-off.
    """
    try:
        climate_results = await evaluate_combined_climate_risk(
            weight_heat=req.weight_heat,
            weight_water=req.weight_water,
            scoring_mode=req.scoring_mode,
            scenario_id=req.scenario_id,
            heat_wbgt_override=req.heat_wbgt
        )
        optimization_plan = optimize_from_combined_climate_results(
            combined_climate_results=climate_results,
            total_budget_inr=req.total_budget_inr,
            total_crew_members=req.total_crew_members,
            total_water_cap_l=req.total_water_cap_l,
            equity_slider=req.equity_slider
        )
        return {
            "climate_scenario": req.scenario_id or "LIVE_METEOROLOGY",
            "scoring_mode": req.scoring_mode,
            "optimization_plan": optimization_plan
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Climate optimization error: {str(e)}")


# -------------------------------------------------------------
# INTERVENTION ENGINE ENDPOINTS & CACHING (Heat + Water Integration)
# -------------------------------------------------------------

# In-memory cache for Combined Climate Risk to avoid redundant external API calls (Requirement 9)
_CLIMATE_ASSESSMENT_CACHE: Dict[str, Any] = {
    "timestamp": 0.0,
    "ttl_seconds": 300.0,  # 5 minutes cache TTL
    "data": None,
    "scenario_id": None
}


async def get_cached_or_fresh_combined_climate_risk(
    scenario_id: Optional[str] = None,
    heat_wbgt_override: Optional[float] = None,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """Retrieves cached climate evaluation or triggers fresh calculation if expired."""
    now = time.time()
    is_cached = (
        not force_refresh and
        _CLIMATE_ASSESSMENT_CACHE["data"] is not None and
        _CLIMATE_ASSESSMENT_CACHE["scenario_id"] == scenario_id and
        heat_wbgt_override is None and
        (now - _CLIMATE_ASSESSMENT_CACHE["timestamp"]) < _CLIMATE_ASSESSMENT_CACHE["ttl_seconds"]
    )
    if is_cached:
        return _CLIMATE_ASSESSMENT_CACHE["data"]

    fresh = await evaluate_combined_climate_risk(
        scenario_id=scenario_id,
        heat_wbgt_override=heat_wbgt_override
    )
    if heat_wbgt_override is None:
        _CLIMATE_ASSESSMENT_CACHE["data"] = fresh
        _CLIMATE_ASSESSMENT_CACHE["timestamp"] = now
        _CLIMATE_ASSESSMENT_CACHE["scenario_id"] = scenario_id
    return fresh


class InterventionRequest(BaseModel):
    total_budget_inr: float = Field(500000.0, ge=5000, le=100000000, description="Total monetary budget in INR")
    total_crew_members: int = Field(40, ge=0, le=1000, description="Total available personnel/staff")
    total_water_cap_l: float = Field(30000.0, ge=0, le=1000000, description="Daily water cap limit in Liters")
    equity_slider: float = Field(0.5, ge=0.0, le=1.0, description="Equity priority slider (0.0 = pure efficiency, 1.0 = maximum equity)")
    wards: Optional[List[Dict[str, Any]]] = Field(None, description="Optional custom ward risk assessments to optimize")
    scenario_id: Optional[str] = Field(None, description="Optional climate demo scenario ID (monsoon_cloudburst, summer_drought_scarcity, dry_baseline, compound_hazard)")
    heat_wbgt: Optional[float] = Field(None, ge=15.0, le=45.0, description="Optional custom outdoor WBGT in °C")
    intervention_capacity_limits: Optional[Dict[str, int]] = Field(None, description="Optional citywide capacity limits per intervention ID")
    existing_interventions: Optional[List[Dict[str, Any]]] = Field(None, description="Optional preexisting active interventions by ward")
    include_tradeoff_analysis: bool = Field(True, description="Whether to compute efficiency vs. equity trade-off benchmark comparison")


@app.get("/api/interventions/catalog")
def get_intervention_engine_catalog():
    """
    Returns full multi-hazard interventions catalog across Heat, Waterlogging, and Water Shortage,
    including unit costs, resource footprints, feasibility scores, trigger thresholds, and data provenance labels.
    """
    return {
        "status": "SUCCESS",
        "provenance_labels": PROVENANCE_LABELS,
        "total_interventions": len(INTERVENTIONS_CATALOG),
        "interventions": INTERVENTIONS_CATALOG
    }


@app.post("/api/interventions/recommend")
async def recommend_interventions(req: InterventionRequest):
    """
    Generates, ranks, and optimizes hazard-matched interventions under budget, crew, water,
    and intervention capacity limits. Directly accounts for preexisting active interventions,
    prevents double-counting with submodular diminishing returns, and evaluates efficiency vs. equity trade-offs.
    """
    try:
        # If user did not provide custom ward risks, pull from cached/live combined climate evaluation
        if req.wards:
            wards_to_use = req.wards
        else:
            climate_data = await get_cached_or_fresh_combined_climate_risk(
                scenario_id=req.scenario_id,
                heat_wbgt_override=req.heat_wbgt
            )
            wards_to_use = climate_data.get("ranked_wards", climate_data.get("wards", []))

        plan = generate_intervention_recommendations(
            wards=wards_to_use,
            total_budget_inr=req.total_budget_inr,
            total_crew_members=req.total_crew_members,
            total_water_cap_l=req.total_water_cap_l,
            equity_slider=req.equity_slider,
            intervention_capacity_limits=req.intervention_capacity_limits,
            existing_interventions=req.existing_interventions,
            include_tradeoff_analysis=req.include_tradeoff_analysis
        )
        return plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Intervention Engine execution failed: {str(e)}")


@app.get("/api/interventions/ranked")
async def get_ranked_interventions_endpoint(
    ward_id: Optional[str] = Query(None, description="Filter for specific ward (e.g. 'W1', 'Danilimda')"),
    hazard: Optional[str] = Query(None, description="Filter by hazard: 'heat', 'flood/waterlogging', 'water_shortage'"),
    equity_slider: float = Query(0.5, ge=0.0, le=1.0, description="Equity slider parameter (0.0 to 1.0)"),
    scenario_id: Optional[str] = Query(None, description="Optional climate demo scenario ID")
):
    """
    Retrieves ranked candidate interventions across all 48 wards or filtered by ward or hazard,
    including priority scores, expected impact ranges, people reached, lead times, and rationales.
    """
    try:
        from backend.intervention_engine import default_engine
        climate_data = await get_cached_or_fresh_combined_climate_risk(scenario_id=scenario_id)
        wards_to_use = climate_data.get("ranked_wards", climate_data.get("wards", []))
        candidates = default_engine.generate_candidate_interventions(wards_to_use)
        ranked = default_engine.rank_candidate_interventions(candidates, equity_slider=equity_slider)

        if ward_id:
            clean_wid = ward_id.strip().lower()
            ranked = [
                c for c in ranked
                if clean_wid in c["target_ward"]["ward_id"].lower()
                or clean_wid in c["target_ward"]["ward_name"].lower()
            ]
        if hazard:
            clean_h = hazard.strip().lower()
            ranked = [c for c in ranked if clean_h in c["related_hazard"].lower() or clean_h in c["category"].lower()]

        return {
            "status": "SUCCESS",
            "target_ward_filter": ward_id or "ALL",
            "hazard_filter": hazard or "ALL",
            "equity_slider": equity_slider,
            "total_ranked_interventions": len(ranked),
            "ranked_interventions": ranked
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve ranked interventions: {str(e)}")


@app.get("/api/interventions/wards/{ward_id}")
async def get_ward_ranked_interventions(
    ward_id: str,
    equity_slider: float = Query(0.5, ge=0.0, le=1.0, description="Equity slider parameter"),
    scenario_id: Optional[str] = Query(None, description="Optional demo scenario ID")
):
    """
    Retrieves complete candidate interventions profile specifically for a single selected ward.
    """
    try:
        from backend.intervention_engine import default_engine
        climate_data = await get_cached_or_fresh_combined_climate_risk(scenario_id=scenario_id)
        wards_to_use = climate_data.get("ranked_wards", climate_data.get("wards", []))

        clean_wid = ward_id.strip().lower()
        matched_wards = [
            w for w in wards_to_use
            if clean_wid == str(w.get("id", "")).lower()
            or clean_wid in str(w.get("name", "")).lower()
            or clean_wid in str(w.get("official_name", "")).lower()
        ]
        if not matched_wards:
            raise HTTPException(
                status_code=404,
                detail=f"Ward '{ward_id}' not found in Ahmedabad administrative wards database. Try using valid ID (e.g. W1-W48) or name (e.g. Danilimda, Vatva)."
            )

        target_ward = matched_wards[0]
        candidates = default_engine.generate_candidate_interventions([target_ward])
        ranked = default_engine.rank_candidate_interventions(candidates, equity_slider=equity_slider)

        return {
            "status": "SUCCESS",
            "ward_id": target_ward.get("id", ward_id),
            "ward_name": target_ward.get("name", ""),
            "equity_slider": equity_slider,
            "candidate_interventions_count": len(ranked),
            "interventions": ranked
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving interventions for ward '{ward_id}': {str(e)}")


class WhatIfSimulationRequest(BaseModel):
    # Simulated scenario parameters (user-controllable)
    simulated_budget_inr: float = Field(500000.0, ge=5000, le=100000000, description="Simulated monetary budget in INR")
    simulated_crew_members: int = Field(40, ge=0, le=1000, description="Simulated response teams / personnel count")
    simulated_water_cap_l: float = Field(30000.0, ge=0, le=1000000, description="Simulated daily water cap limit in Liters")
    simulated_equity_slider: float = Field(0.5, ge=0.0, le=1.0, description="Simulated equity preference slider (0.0 = efficiency, 1.0 = maximum equity)")
    simulated_capacity_limits: Optional[Dict[str, int]] = Field(None, description="Optional simulated fleet capacity limits per intervention")

    # Baseline scenario parameters (default to standard municipal parameters)
    baseline_budget_inr: float = Field(500000.0, ge=5000, le=100000000, description="Baseline comparison budget in INR")
    baseline_crew_members: int = Field(40, ge=0, le=1000, description="Baseline comparison response teams count")
    baseline_water_cap_l: float = Field(30000.0, ge=0, le=1000000, description="Baseline comparison water cap limit in Liters")
    baseline_equity_slider: float = Field(0.5, ge=0.0, le=1.0, description="Baseline comparison equity slider")
    baseline_capacity_limits: Optional[Dict[str, int]] = Field(None, description="Optional baseline capacity limits")

    # Optional inputs
    wards: Optional[List[Dict[str, Any]]] = Field(None, description="Optional custom ward risk assessments to simulate")
    scenario_id: Optional[str] = Field(None, description="Optional climate demo scenario ID")
    heat_wbgt: Optional[float] = Field(None, ge=15.0, le=45.0, description="Optional custom outdoor WBGT in °C")
    existing_interventions: Optional[List[Dict[str, Any]]] = Field(None, description="Optional preexisting active interventions by ward")


@app.post("/api/interventions/simulate")
async def simulate_what_if_interventions(req: WhatIfSimulationRequest):
    """
    Lightweight What-If Simulator:
    Recalculates recommended interventions when users modify budget, response teams,
    water caps, equity preference, or intervention capacity limits.
    Compares baseline vs. simulated allocations, displays priority shifts (wards gaining/losing),
    shows impact uncertainty ranges, and provides explainable trade-off narratives.
    """
    try:
        if req.wards:
            wards_to_use = req.wards
        else:
            climate_data = await get_cached_or_fresh_combined_climate_risk(
                scenario_id=req.scenario_id,
                heat_wbgt_override=req.heat_wbgt
            )
            wards_to_use = climate_data.get("ranked_wards", climate_data.get("wards", []))

        result = run_what_if_simulation(
            wards=wards_to_use,
            simulated_budget_inr=req.simulated_budget_inr,
            simulated_crew_members=req.simulated_crew_members,
            simulated_water_cap_l=req.simulated_water_cap_l,
            simulated_equity_slider=req.simulated_equity_slider,
            simulated_capacity_limits=req.simulated_capacity_limits,
            baseline_budget_inr=req.baseline_budget_inr,
            baseline_crew_members=req.baseline_crew_members,
            baseline_water_cap_l=req.baseline_water_cap_l,
            baseline_equity_slider=req.baseline_equity_slider,
            baseline_capacity_limits=req.baseline_capacity_limits,
            existing_interventions=req.existing_interventions
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"What-If Simulator error: {str(e)}")


# -------------------------------------------------------------
# WATER RISK ENGINE ENDPOINTS
# -------------------------------------------------------------

class WaterAssessmentRequest(BaseModel):
    scenario_id: Optional[str] = Field(None, description="Preset demonstration scenario ID (e.g., monsoon_cloudburst, summer_drought_scarcity)")
    rainfall_24h_mm: Optional[float] = Field(None, ge=0.0, le=500.0, description="Optional custom 24-hour rainfall in mm")
    peak_hourly_rainfall_mm: Optional[float] = Field(None, ge=0.0, le=200.0, description="Optional custom peak 1-hour rainfall in mm/hr")
    supply_lpcd: Optional[float] = Field(None, ge=10.0, le=300.0, description="Observed/simulated potable supply in Liters Per Capita per Day")
    reservoir_storage_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Observed/simulated bulk reservoir storage percentage")


@app.get("/api/water/scenarios")
def get_water_scenarios():
    """Returns curated synthetic demonstration scenarios for disaster stress-testing."""
    return {
        "status": "SUCCESS",
        "description": "Pre-configured synthetic scenarios for water risk stress-testing. Clearly labelled as demonstration inputs.",
        "scenarios": DEMONSTRATION_SCENARIOS
    }


@app.get("/api/water/wards")
async def get_all_wards_water_risk(
    scenario_id: Optional[str] = Query(None, description="Optional preset demo scenario: dry_baseline, monsoon_cloudburst, summer_drought_scarcity, compound_hazard"),
    rainfall_24h_mm: Optional[float] = Query(None, ge=0.0, le=500.0, description="Optional custom 24-hour rainfall in mm"),
    peak_hourly_rainfall_mm: Optional[float] = Query(None, ge=0.0, le=200.0, description="Optional custom peak 1-hour rainfall in mm/hr"),
    supply_lpcd: Optional[float] = Query(None, ge=10.0, le=300.0, description="Optional observed supply in Liters Per Capita per Day"),
    reservoir_storage_pct: Optional[float] = Query(None, ge=0.0, le=100.0, description="Optional observed bulk reservoir storage percentage"),
    lat: float = Query(23.0225, ge=-90.0, le=90.0, description="Latitude for Open-Meteo weather"),
    lon: float = Query(72.5714, ge=-180.0, le=180.0, description="Longitude for Open-Meteo weather")
):
    """
    Calculates urban water risk across all available Ahmedabad wards.
    Returns city status, data quality indicators, and ward-by-ward risk scores with explainable factor breakdowns.
    """
    try:
        results = await assess_citywide_water_risk(
            scenario_id=scenario_id,
            supply_lpcd_override=supply_lpcd,
            reservoir_storage_override=reservoir_storage_pct,
            rainfall_24h_override=rainfall_24h_mm,
            peak_hourly_override=peak_hourly_rainfall_mm,
            lat=lat,
            lon=lon
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate citywide water risk: {str(e)}")


@app.get("/api/water/wards/{ward_id}")
async def get_single_ward_water_risk_endpoint(
    ward_id: str,
    scenario_id: Optional[str] = Query(None, description="Optional preset demo scenario: dry_baseline, monsoon_cloudburst, summer_drought_scarcity, compound_hazard"),
    rainfall_24h_mm: Optional[float] = Query(None, ge=0.0, le=500.0, description="Optional custom 24-hour rainfall in mm"),
    peak_hourly_rainfall_mm: Optional[float] = Query(None, ge=0.0, le=200.0, description="Optional custom peak 1-hour rainfall in mm/hr"),
    supply_lpcd: Optional[float] = Query(None, ge=10.0, le=300.0, description="Optional observed supply in LPCD"),
    reservoir_storage_pct: Optional[float] = Query(None, ge=0.0, le=100.0, description="Optional observed reservoir storage percentage")
):
    """
    Retrieves the complete water risk profile for a selected ward.
    Accepts ward ID (e.g., 'W1', 'W7', '36') or ward Name (e.g., 'Danilimda', 'Vatva', '36 DANILIMDA').
    """
    try:
        ward_data = await get_single_ward_water_risk(
            ward_identifier=ward_id,
            scenario_id=scenario_id,
            supply_lpcd_override=supply_lpcd,
            reservoir_storage_override=reservoir_storage_pct,
            rainfall_24h_override=rainfall_24h_mm,
            peak_hourly_override=peak_hourly_rainfall_mm
        )
        if not ward_data:
            raise HTTPException(
                status_code=404,
                detail=f"Ward '{ward_id}' not found in Ahmedabad administrative wards database. Try using a valid ward ID (e.g., W1-W10, W1-W48) or ward name (e.g., Danilimda, Vatva, Maninagar)."
            )
        return ward_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error evaluating water risk for ward '{ward_id}': {str(e)}")


@app.get("/api/water/risk")
async def get_citywide_water_risk(
    scenario_id: Optional[str] = Query(None, description="Optional demo scenario ID: dry_baseline, monsoon_cloudburst, summer_drought_scarcity, compound_hazard"),
    rainfall_24h_mm: Optional[float] = Query(None, ge=0.0, le=500.0, description="Optional custom 24-hour rainfall in mm"),
    peak_hourly_rainfall_mm: Optional[float] = Query(None, ge=0.0, le=200.0, description="Optional custom peak 1-hour rainfall in mm/hr"),
    supply_lpcd: Optional[float] = Query(None, ge=10.0, le=300.0, description="Optional observed supply in Liters Per Capita per Day"),
    reservoir_storage_pct: Optional[float] = Query(None, ge=0.0, le=100.0, description="Optional observed reservoir storage percentage"),
    lat: float = Query(23.0225, ge=-90.0, le=90.0),
    lon: float = Query(72.5714, ge=-180.0, le=180.0)
):
    """
    Evaluates ward-level waterlogging/pluvial flood risk and water shortage risk (0-100 scale).
    Uses live Open-Meteo precipitation unless a synthetic demonstration scenario or custom override is selected.
    Includes data quality indicator and explainable contributing factor breakdowns.
    """
    try:
        results = await assess_citywide_water_risk(
            scenario_id=scenario_id,
            supply_lpcd_override=supply_lpcd,
            reservoir_storage_override=reservoir_storage_pct,
            rainfall_24h_override=rainfall_24h_mm,
            peak_hourly_override=peak_hourly_rainfall_mm,
            lat=lat,
            lon=lon
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Water Risk Engine calculation failed: {str(e)}")


@app.post("/api/water/assess")
@app.post("/api/water/calculate")
async def assess_custom_water_risk(req: WaterAssessmentRequest):
    """
    Custom scenario evaluation allowing parameter overrides for what-if simulation planning.
    """
    try:
        results = await assess_citywide_water_risk(
            scenario_id=req.scenario_id,
            supply_lpcd_override=req.supply_lpcd,
            reservoir_storage_override=req.reservoir_storage_pct,
            rainfall_24h_override=req.rainfall_24h_mm,
            peak_hourly_override=req.peak_hourly_rainfall_mm
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Custom Water Risk assessment failed: {str(e)}")


# -------------------------------------------------------------
# COMBINED CLIMATE RISK ENGINE ENDPOINTS (HEAT + WATER)
# -------------------------------------------------------------

class CombinedClimateRiskRequest(BaseModel):
    weight_heat: float = Field(0.5, ge=0.0, le=1.0, description="Configurable relative weight for Heat Risk")
    weight_water: float = Field(0.5, ge=0.0, le=1.0, description="Configurable relative weight for Water Risk")
    scoring_mode: str = Field("COMPOUND_SYNERGY", description="Scoring mode: COMPOUND_SYNERGY | WEIGHTED_AVERAGE | WORST_CASE_PEAK")
    synergy_multiplier: float = Field(0.15, ge=0.0, le=1.0, description="Compound hazard amplification factor")
    scenario_id: Optional[str] = Field(None, description="Optional preset demo scenario ID")
    heat_wbgt: Optional[float] = Field(None, ge=15.0, le=45.0, description="Optional custom outdoor WBGT in °C")
    supply_lpcd: Optional[float] = Field(None, ge=10.0, le=300.0, description="Optional observed potable supply in LPCD")
    reservoir_storage_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Optional observed reservoir storage percentage")
    rainfall_24h_mm: Optional[float] = Field(None, ge=0.0, le=500.0, description="Optional custom 24-hr rainfall in mm")
    peak_hourly_rainfall_mm: Optional[float] = Field(None, ge=0.0, le=200.0, description="Optional custom peak 1-hr rainfall in mm/hr")


@app.get("/api/climate-risk")
@app.get("/api/climate/combined-risk")
async def get_combined_climate_risk(
    weight_heat: float = Query(0.5, ge=0.0, le=1.0, description="Configurable weight for Heat Risk (0.0 to 1.0)"),
    weight_water: float = Query(0.5, ge=0.0, le=1.0, description="Configurable weight for Water Risk (0.0 to 1.0)"),
    scoring_mode: str = Query("COMPOUND_SYNERGY", description="Scoring mode: COMPOUND_SYNERGY, WEIGHTED_AVERAGE, WORST_CASE_PEAK"),
    synergy_multiplier: float = Query(0.15, ge=0.0, le=1.0, description="Compound synergy multiplier factor"),
    scenario_id: Optional[str] = Query(None, description="Optional preset demo scenario ID"),
    heat_wbgt: Optional[float] = Query(None, ge=15.0, le=45.0, description="Optional custom outdoor WBGT in °C"),
    supply_lpcd: Optional[float] = Query(None, ge=10.0, le=300.0, description="Optional observed supply in LPCD"),
    reservoir_storage_pct: Optional[float] = Query(None, ge=0.0, le=100.0, description="Optional observed reservoir storage percentage"),
    rainfall_24h_mm: Optional[float] = Query(None, ge=0.0, le=500.0, description="Optional custom 24-hour rainfall in mm"),
    peak_hourly_rainfall_mm: Optional[float] = Query(None, ge=0.0, le=200.0, description="Optional custom peak 1-hour rainfall in mm/hr"),
    lat: float = Query(23.0225, ge=-90.0, le=90.0),
    lon: float = Query(72.5714, ge=-180.0, le=180.0)
):
    """
    Evaluates combined multi-hazard climate risk integrating Heat and Water risk dimensions.
    Returns ranked wards, dual-hazard compound flags, explainable rationales, and explicit data quality indicators.
    """
    if scoring_mode not in SCORING_MODES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid scoring mode '{scoring_mode}'. Supported modes: {SCORING_MODES}"
        )
    if weight_heat + weight_water <= 0.0:
        raise HTTPException(
            status_code=422,
            detail="The sum of weight_heat and weight_water must be greater than zero."
        )
    try:
        results = await evaluate_combined_climate_risk(
            weight_heat=weight_heat,
            weight_water=weight_water,
            scoring_mode=scoring_mode,
            synergy_multiplier=synergy_multiplier,
            scenario_id=scenario_id,
            heat_wbgt_override=heat_wbgt,
            supply_lpcd_override=supply_lpcd,
            reservoir_storage_override=reservoir_storage_pct,
            rainfall_24h_override=rainfall_24h_mm,
            peak_hourly_override=peak_hourly_rainfall_mm,
            lat=lat,
            lon=lon
        )
        return results
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Combined Climate Risk evaluation failed: {str(e)}")


@app.get("/api/climate-risk/wards/{ward_id}")
async def get_single_ward_climate_risk(
    ward_id: str,
    weight_heat: float = Query(0.5, ge=0.0, le=1.0),
    weight_water: float = Query(0.5, ge=0.0, le=1.0),
    scoring_mode: str = Query("COMPOUND_SYNERGY"),
    synergy_multiplier: float = Query(0.15, ge=0.0, le=1.0),
    scenario_id: Optional[str] = Query(None),
    heat_wbgt: Optional[float] = Query(None, ge=15.0, le=45.0),
    supply_lpcd: Optional[float] = Query(None, ge=10.0, le=300.0),
    reservoir_storage_pct: Optional[float] = Query(None, ge=0.0, le=100.0),
    rainfall_24h_mm: Optional[float] = Query(None, ge=0.0, le=500.0),
    peak_hourly_rainfall_mm: Optional[float] = Query(None, ge=0.0, le=200.0)
):
    """
    Retrieves the detailed multi-hazard climate risk assessment for a specific ward.
    Accepts ward ID (e.g. 'W1', 'W7', '36'), numeric index (e.g. '0', '35'), or ward name (e.g. 'Danilimda', 'Vatva').
    """
    if scoring_mode not in SCORING_MODES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid scoring mode '{scoring_mode}'. Supported modes: {SCORING_MODES}"
        )
    try:
        results = await evaluate_combined_climate_risk(
            weight_heat=weight_heat,
            weight_water=weight_water,
            scoring_mode=scoring_mode,
            synergy_multiplier=synergy_multiplier,
            scenario_id=scenario_id,
            heat_wbgt_override=heat_wbgt,
            supply_lpcd_override=supply_lpcd,
            reservoir_storage_override=reservoir_storage_pct,
            rainfall_24h_override=rainfall_24h_mm,
            peak_hourly_override=peak_hourly_rainfall_mm
        )

        norm_target = ward_id.strip().lower()
        matched_ward = None

        # Strategy 1: Exact canonical ID match (e.g. 'w1')
        for w in results["ranked_wards"]:
            if str(w.get("id", "")).strip().lower() == norm_target:
                matched_ward = w
                break

        # Strategy 2: Numeric index or ward number match (e.g. '12' or '35')
        if not matched_ward:
            for w in results["ranked_wards"]:
                if str(w.get("ward_index", "")) == norm_target or str(w.get("ward_index", 0) + 1) == norm_target:
                    matched_ward = w
                    break

        # Strategy 3: Name substring match (e.g. 'danilimda' in 'Danilimda' or '36 DANILIMDA')
        if not matched_ward:
            for w in results["ranked_wards"]:
                if norm_target in w.get("name", "").lower() or norm_target in w.get("official_name", "").lower():
                    matched_ward = w
                    break

        if not matched_ward:
            raise HTTPException(
                status_code=404,
                detail=f"Ward '{ward_id}' not found in Climate Risk assessment. Please specify a valid ward ID (e.g. W1-W48) or ward name."
            )

        return {
            "city": results["city"],
            "coordinates": results["coordinates"],
            "timestamp": results["timestamp"],
            "scoring_configuration": results["scoring_configuration"],
            "data_quality_and_confidence": results["data_quality_and_confidence"],
            "ward": matched_ward
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error evaluating ward climate risk: {str(e)}")


@app.get("/api/climate-risk/rankings")
async def get_climate_risk_rankings(
    limit: Optional[int] = Query(None, ge=1, le=48, description="Max number of ranked wards to return"),
    compound_only: bool = Query(False, description="Filter for dual-hazard compound hotspots only"),
    weight_heat: float = Query(0.5, ge=0.0, le=1.0),
    weight_water: float = Query(0.5, ge=0.0, le=1.0),
    scoring_mode: str = Query("COMPOUND_SYNERGY"),
    synergy_multiplier: float = Query(0.15, ge=0.0, le=1.0),
    scenario_id: Optional[str] = Query(None),
    heat_wbgt: Optional[float] = Query(None, ge=15.0, le=45.0),
    supply_lpcd: Optional[float] = Query(None, ge=10.0, le=300.0),
    reservoir_storage_pct: Optional[float] = Query(None, ge=0.0, le=100.0),
    rainfall_24h_mm: Optional[float] = Query(None, ge=0.0, le=500.0),
    peak_hourly_rainfall_mm: Optional[float] = Query(None, ge=0.0, le=200.0)
):
    """
    Returns deterministically ranked wards and flags dual-hazard emergency priorities.
    Supports filtering by compound hotspots and limiting results for executive decision summaries.
    """
    if scoring_mode not in SCORING_MODES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid scoring mode '{scoring_mode}'. Supported modes: {SCORING_MODES}"
        )
    try:
        results = await evaluate_combined_climate_risk(
            weight_heat=weight_heat,
            weight_water=weight_water,
            scoring_mode=scoring_mode,
            synergy_multiplier=synergy_multiplier,
            scenario_id=scenario_id,
            heat_wbgt_override=heat_wbgt,
            supply_lpcd_override=supply_lpcd,
            reservoir_storage_override=reservoir_storage_pct,
            rainfall_24h_override=rainfall_24h_mm,
            peak_hourly_override=peak_hourly_rainfall_mm
        )

        wards = results["ranked_wards"]
        if compound_only:
            wards = [w for w in wards if w["compound_hazard"]["is_compound_hotspot"]]

        if limit is not None:
            wards = wards[:limit]

        dual_hazard_priorities = [
            w for w in wards
            if w["compound_hazard"]["tier"] in ["DUAL_CRITICAL", "DUAL_HIGH"]
        ]

        return {
            "city": results["city"],
            "timestamp": results["timestamp"],
            "scoring_configuration": results["scoring_configuration"],
            "total_ranked_wards": len(wards),
            "compound_hazard_hotspots_count": sum(1 for w in wards if w["compound_hazard"]["is_compound_hotspot"]),
            "rankings": wards,
            "dual_hazard_priorities": dual_hazard_priorities
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating climate risk rankings: {str(e)}")


@app.post("/api/climate-risk")
@app.post("/api/climate/combined-risk")
async def calculate_combined_climate_risk(req: CombinedClimateRiskRequest):
    """
    Parameterized POST endpoint for Combined Climate Risk evaluation and what-if simulation.
    """
    if req.scoring_mode not in SCORING_MODES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid scoring mode '{req.scoring_mode}'. Supported modes: {SCORING_MODES}"
        )
    if req.weight_heat + req.weight_water <= 0.0:
        raise HTTPException(
            status_code=422,
            detail="The sum of weight_heat and weight_water must be greater than zero."
        )
    try:
        results = await evaluate_combined_climate_risk(
            weight_heat=req.weight_heat,
            weight_water=req.weight_water,
            scoring_mode=req.scoring_mode,
            synergy_multiplier=req.synergy_multiplier,
            scenario_id=req.scenario_id,
            heat_wbgt_override=req.heat_wbgt,
            supply_lpcd_override=req.supply_lpcd,
            reservoir_storage_override=req.reservoir_storage_pct,
            rainfall_24h_override=req.rainfall_24h_mm,
            peak_hourly_override=req.peak_hourly_rainfall_mm
        )
        return results
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Combined Climate Risk simulation failed: {str(e)}")


# -------------------------------------------------------------
# EXTERNAL SATELLITE & REANALYSIS DATA SOURCES ENDPOINTS
# -------------------------------------------------------------

@app.get("/api/data-sources/era5")
async def get_era5_land_climate(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD), defaults to current date"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD), defaults to current date"),
    force_refresh: bool = Query(False, description="Force refresh cache")
):
    """
    Retrieves Copernicus ERA5-Land historical climate reanalysis dataset for Ahmedabad.
    Includes 2m air temp, dewpoint, total precipitation, soil moisture, solar radiation, and wind components.
    """
    try:
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        s_date = start_date or today
        e_date = end_date or today

        client = ERA5LandClient()
        data = await client.fetch_historical_climate(s_date, e_date, force_refresh=force_refresh)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ERA5-Land data fetch error: {str(e)}")


@app.get("/api/data-sources/ecostress")
async def get_ecostress_overpass(
    product_type: str = Query("LST", description="ECOSTRESS product: LST (Land Surface Temp) or ET (Evapotranspiration)"),
    reference_date: Optional[str] = Query(None, description="Reference date (YYYY-MM-DD)")
):
    """
    Retrieves NASA ECOSTRESS high-resolution (~70m) thermal satellite overpass data for Ahmedabad.
    Preserves acquisition timestamp, cloud mask, and quality flags.
    """
    try:
        client = ECOSTRESSClient()
        data = await client.fetch_latest_overpass(product_type=product_type, reference_date=reference_date)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ECOSTRESS data fetch error: {str(e)}")


@app.get("/api/data-sources/fusion")
async def get_fused_ward_climate(
    target_date: Optional[str] = Query(None, description="Target date (YYYY-MM-DD)")
):
    """
    Fuses Copernicus ERA5-Land macro-climate data and NASA ECOSTRESS thermal observations
    per administrative ward across Ahmedabad's 48 GeoJSON wards.
    """
    try:
        fusion_engine = DataFusionEngine()
        result = await fusion_engine.get_fused_ward_climate_profile(target_date=target_date)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data fusion error: {str(e)}")


@app.get("/api/data-sources/fused-heat-risk")
async def get_fused_heat_risk(
    target_date: Optional[str] = Query(None, description="Target date (YYYY-MM-DD)")
):
    """
    Evaluates Heat Engine (wbgt_pipeline.py) across all 48 wards using fused satellite data.
    Incorporates ECOSTRESS microclimate thermal LST anomalies with explicit uncertainty margins.
    """
    try:
        service = DataSourcesService()
        result = await service.evaluate_fused_heat_risk(target_date=target_date)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fused heat risk evaluation error: {str(e)}")


@app.get("/api/data-sources/fused-climate-risk")
async def get_fused_climate_risk(
    target_date: Optional[str] = Query(None, description="Target date (YYYY-MM-DD)"),
    weight_heat: float = Query(0.5, ge=0.0, le=1.0),
    weight_water: float = Query(0.5, ge=0.0, le=1.0),
    scoring_mode: str = Query("COMPOUND_SYNERGY"),
    synergy_multiplier: float = Query(0.15, ge=0.0, le=1.0)
):
    """
    Evaluates Combined Multi-Hazard Risk Engine (combined_risk_engine.py) using fused satellite data.
    Feeds fused heat and precipitation parameters directly into the compound risk engine.
    """
    try:
        service = DataSourcesService()
        result = await service.evaluate_fused_climate_risk(
            target_date=target_date,
            weight_heat=weight_heat,
            weight_water=weight_water,
            scoring_mode=scoring_mode,
            synergy_multiplier=synergy_multiplier
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fused combined climate risk error: {str(e)}")


class FusedOptimizationRequest(BaseModel):
    target_date: Optional[str] = Field(None, description="Target date (YYYY-MM-DD)")
    total_budget_inr: float = Field(500000.0, ge=10000, le=10000000)
    total_crew_members: int = Field(40, ge=1, le=500)
    total_water_cap_l: float = Field(30000.0, ge=1000, le=500000)
    equity_slider: float = Field(0.5, ge=0.0, le=1.0)
    weight_heat: float = Field(0.5, ge=0.0, le=1.0)
    weight_water: float = Field(0.5, ge=0.0, le=1.0)
    scoring_mode: str = Field("COMPOUND_SYNERGY")


@app.post("/api/data-sources/optimize-fused")
async def optimize_from_fused_data(req: FusedOptimizationRequest):
    """
    Runs Optimizer on fused multi-hazard climate risk assessment derived from ERA5-Land and ECOSTRESS data.
    """
    try:
        service = DataSourcesService()
        plan = await service.optimize_fused_climate_resources(
            target_date=req.target_date,
            total_budget_inr=req.total_budget_inr,
            total_crew_members=req.total_crew_members,
            total_water_cap_l=req.total_water_cap_l,
            equity_slider=req.equity_slider,
            weight_heat=req.weight_heat,
            weight_water=req.weight_water,
            scoring_mode=req.scoring_mode
        )
        return plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fused optimization error: {str(e)}")


# -------------------------------------------------------------
# ACTION CENTRE ENDPOINTS
# -------------------------------------------------------------

class ActionStatusUpdateRequest(BaseModel):
    new_status: str = Field(..., description=f"Target status. Must be one of: {VALID_STATUSES}")
    changed_by: str = Field("operator", description="Identity of the person/system making the change")
    notes: Optional[str] = Field(None, description="Optional notes about the status change")


class ManualActionRequest(BaseModel):
    ward_id: str = Field(..., description="Ward identifier (e.g. W1, W7)")
    ward_name: str = Field("", description="Ward display name")
    action_type: str = Field(..., description=f"Action type. Must be one of: {ACTION_TYPES}")
    priority: str = Field("medium", description="Priority level: critical, high, medium, low")
    reason: str = Field(..., description="Why this action is recommended")
    required_resources: Optional[Dict[str, Any]] = Field(None, description="Resource requirements")
    related_hazard: Optional[str] = Field(None, description="Related hazard: heat, waterlogging, water_shortage")
    risk_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Associated risk score 0-100")


class RecommendationRequest(BaseModel):
    scenario_id: Optional[str] = Field(None, description="Optional climate demo scenario ID")
    available_budget_inr: Optional[float] = Field(None, ge=0.0, description="Municipal budget ceiling in INR")
    available_crew: Optional[int] = Field(None, ge=0, description="Available emergency staff / crew count")
    available_water_l: Optional[float] = Field(None, ge=0.0, description="Available emergency water cap in Liters")
    threshold_overrides: Optional[Dict[str, float]] = Field(None, description="Custom rule threshold overrides")
    persist_to_store: bool = Field(True, description="Whether to persist generated recommendations into the Action Store")
    enforce_resource_constraints: bool = Field(True, description="Whether to filter out actions exceeding available resources")


@app.get("/api/action-centre/dashboard")
async def get_action_centre_dashboard(
    scenario_id: Optional[str] = Query(None, description="Optional climate demo scenario ID"),
    force_refresh: bool = Query(False, description="Force fresh climate risk evaluation")
):
    """
    Returns the unified Action Centre dashboard:
    - High-risk Ahmedabad wards (combined score >= 50.0) with contributing heat & water factors.
    - Overall action summary by operational status (proposed, approved, in_progress, completed, cancelled).
    - Ward-wise action aggregation correlating active dispatches with risk profiles.
    - Prioritized action queue sorted by risk severity, urgency, and recency.
    - Data freshness & staleness indicator (safely falls back if risk engine is temporarily offline).
    """
    try:
        climate_data = await get_cached_or_fresh_combined_climate_risk(
            scenario_id=scenario_id,
            force_refresh=force_refresh
        )
        data_quality = climate_data.get("data_quality_and_confidence", None)
    except Exception as e:
        # Graceful fallback: Action Centre operates in decoupled store-only mode if risk engine is unavailable
        climate_data = None
        data_quality = {
            "status": "UNAVAILABLE",
            "warning": f"Risk assessment engine temporarily unavailable: {str(e)}",
            "fallback_mode": "STORE_ONLY",
        }

    dashboard = build_action_centre_dashboard(
        climate_risk_data=climate_data,
        data_quality=data_quality,
    )
    return dashboard


@app.get("/api/action-centre/actions/prioritized")
def list_prioritized_actions(
    ward_id: Optional[str] = Query(None, description="Optional filter by ward ID or name"),
    action_type: Optional[str] = Query(None, description="Optional filter by action type"),
    status: Optional[str] = Query(None, description="Optional filter by status"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of prioritized actions to return")
):
    """
    Returns an operational queue of actions sorted strictly by decision priority:
    1. Priority level: critical > high > medium > low
    2. Status urgency: in_progress > approved > proposed > completed > cancelled
    3. Associated risk score descending
    4. Creation recency
    """
    if status and status not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status filter '{status}'. Must be one of: {VALID_STATUSES}"
        )
    if action_type and action_type not in ACTION_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid action_type filter '{action_type}'. Must be one of: {ACTION_TYPES}"
        )

    store = get_action_store()
    actions = get_prioritized_actions(
        store=store,
        ward_id=ward_id,
        action_type=action_type,
        status=status,
        limit=limit,
    )
    return {
        "status": "SUCCESS",
        "total_actions": len(actions),
        "limit": limit,
        "filters_applied": {
            "ward_id": ward_id,
            "action_type": action_type,
            "status": status,
        },
        "prioritized_actions": actions,
        "advisory": ACTION_CENTRE_ADVISORY,
    }


@app.get("/api/action-centre/actions/ward-summary")
async def get_ward_action_summary_endpoint(
    scenario_id: Optional[str] = Query(None, description="Optional climate demo scenario ID to correlate risk scores")
):
    """
    Returns a ward-wise aggregation of all actions in the Action Centre.
    Correlates active actions with each ward's combined risk profile,
    reporting active action count, breakdown by status, and highest priority.
    """
    climate_data = None
    try:
        climate_data = await get_cached_or_fresh_combined_climate_risk(
            scenario_id=scenario_id
        )
    except Exception:
        climate_data = None

    store = get_action_store()
    summaries = get_ward_wise_action_summary(
        store=store,
        climate_risk_data=climate_data,
    )
    return {
        "status": "SUCCESS",
        "total_wards_with_actions": len(summaries),
        "ward_summaries": summaries,
        "climate_risk_correlated": climate_data is not None,
        "advisory": ACTION_CENTRE_ADVISORY,
    }


@app.get("/api/action-centre/actions")
def list_action_centre_actions(
    ward_id: Optional[str] = Query(None, description="Filter by ward ID or name"),
    action_type: Optional[str] = Query(None, description=f"Filter by action type"),
    status: Optional[str] = Query(None, description=f"Filter by status")
):
    """
    Lists all Action Centre actions with optional filters by ward, type, or status.
    """
    if status and status not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status filter '{status}'. Must be one of: {VALID_STATUSES}"
        )
    if action_type and action_type not in ACTION_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid action_type filter '{action_type}'. Must be one of: {ACTION_TYPES}"
        )

    store = get_action_store()
    actions = store.list_actions(ward_id=ward_id, action_type=action_type, status=status)
    return {
        "status": "SUCCESS",
        "total_actions": len(actions),
        "filters_applied": {
            "ward_id": ward_id,
            "action_type": action_type,
            "status": status,
        },
        "actions": actions,
        "advisory": ACTION_CENTRE_ADVISORY,
    }


@app.get("/api/action-centre/actions/{action_id}")
def get_action_centre_action(action_id: str):
    """
    Retrieves a single action record by its ID, including full status history.
    """
    store = get_action_store()
    action = store.get_action(action_id)
    if not action:
        raise HTTPException(
            status_code=404,
            detail=f"Action '{action_id}' not found in the Action Centre."
        )
    return {"status": "SUCCESS", "action": action}


@app.put("/api/action-centre/actions/{action_id}/status")
def update_action_status(action_id: str, req: ActionStatusUpdateRequest):
    """
    Updates the status of an existing action. Enforces valid state transitions:
    proposed → approved → in_progress → completed
    Any non-terminal state → cancelled
    """
    store = get_action_store()
    try:
        updated = store.update_status(
            action_id=action_id,
            new_status=req.new_status,
            changed_by=req.changed_by,
            notes=req.notes,
        )
        return {"status": "SUCCESS", "action": updated}
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Action '{action_id}' not found in the Action Centre."
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/api/action-centre/create")
def create_manual_action(req: ManualActionRequest):
    """
    Manually creates a new action record in the Action Centre.
    """
    store = get_action_store()
    try:
        action = store.create_action(
            ward_id=req.ward_id,
            ward_name=req.ward_name,
            action_type=req.action_type,
            priority=req.priority,
            reason=req.reason,
            required_resources=req.required_resources,
            related_hazard=req.related_hazard,
            risk_score=req.risk_score,
            source="manual",
        )
        return {"status": "SUCCESS", "action": action}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/api/action-centre/generate-from-risk")
async def generate_actions_from_risk_endpoint(
    scenario_id: Optional[str] = Query(None, description="Optional climate demo scenario ID")
):
    """
    Reads existing Combined Climate Risk Engine output and generates proposed
    heat-alert actions for high-risk wards. Does NOT recalculate risk.
    """
    try:
        climate_data = await get_cached_or_fresh_combined_climate_risk(
            scenario_id=scenario_id
        )
        result = generate_actions_from_climate_risk(climate_data)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate actions from climate risk: {str(e)}"
        )


@app.post("/api/action-centre/generate-from-interventions")
async def generate_actions_from_interventions_endpoint(
    scenario_id: Optional[str] = Query(None, description="Optional climate demo scenario ID"),
    total_budget_inr: float = Query(500000.0, ge=10000, le=10000000),
    total_crew_members: int = Query(40, ge=1, le=500),
    total_water_cap_l: float = Query(30000.0, ge=1000, le=500000),
    equity_slider: float = Query(0.5, ge=0.0, le=1.0)
):
    """
    Reads existing Intervention Engine output and creates trackable actions.
    Uses cached/fresh combined climate risk to produce the intervention plan,
    then converts dispatch items into Action Centre records.
    """
    try:
        climate_data = await get_cached_or_fresh_combined_climate_risk(
            scenario_id=scenario_id
        )
        wards_to_use = climate_data.get("ranked_wards", climate_data.get("wards", []))

        plan = generate_intervention_recommendations(
            wards=wards_to_use,
            total_budget_inr=total_budget_inr,
            total_crew_members=total_crew_members,
            total_water_cap_l=total_water_cap_l,
            equity_slider=equity_slider,
        )
        result = generate_actions_from_interventions(plan)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate actions from interventions: {str(e)}"
        )


@app.get("/api/action-centre/metadata")
def get_action_centre_metadata():
    """
    Returns Action Centre configuration metadata: supported action types,
    valid statuses, and status transition rules.
    """
    from backend.action_centre import VALID_STATUS_TRANSITIONS
    return {
        "status": "SUCCESS",
        "action_types": ACTION_TYPES,
        "valid_statuses": VALID_STATUSES,
        "status_transitions": {
            k: sorted(v) for k, v in VALID_STATUS_TRANSITIONS.items()
        },
        "advisory": ACTION_CENTRE_ADVISORY,
    }


@app.post("/api/action-centre/recommendations")
async def generate_recommendations_endpoint(req: Optional[RecommendationRequest] = None):
    """
    Generates transparent, explainable, rule-based recommendations for high-risk Ahmedabad wards.
    Reads existing risk engine outputs and Optimizer recommendations without recalculating risk.
    Enforces duplicate prevention and respects municipal staff/budget/water resource constraints.
    """
    if req is None:
        req = RecommendationRequest()

    try:
        climate_data = await get_cached_or_fresh_combined_climate_risk(
            scenario_id=req.scenario_id
        )

        resource_constraints = None
        if any(x is not None for x in (req.available_budget_inr, req.available_crew, req.available_water_l)):
            resource_constraints = {
                "available_budget_inr": req.available_budget_inr,
                "available_crew": req.available_crew,
                "available_water_l": req.available_water_l,
            }

        result = generate_rule_based_recommendations(
            climate_risk_data=climate_data,
            resource_constraints=resource_constraints,
            thresholds=req.threshold_overrides,
            create_in_store=req.persist_to_store,
            enforce_resource_constraints=req.enforce_resource_constraints,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate rule-based recommendations: {str(e)}"
        )


@app.get("/api/action-centre/recommendations/rules")
def get_recommendation_rules_metadata():
    """
    Returns active recommendation rule definitions, default thresholds,
    and standard municipal resource schedules.
    """
    return {
        "status": "SUCCESS",
        "rules": RULE_DEFINITIONS,
        "default_thresholds": DEFAULT_RECOMMENDATION_THRESHOLDS,
        "resource_estimates": ACTION_RESOURCE_ESTIMATES,
        "advisory": ACTION_CENTRE_ADVISORY,
    }



