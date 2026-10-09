"""
ClimateShield - Ward Risk Assessment & Monte Carlo Uncertainty Engine
Calculates explainable percentile risk scores (Risk = H x E x V) across Ahmedabad Wards
and performs 500 Monte Carlo simulation draws over index weights for rank stability analysis.
"""

import json
import os
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional

# Nominal IPCC Risk Dimension Weights
DEFAULT_WEIGHT_HAZARD = 0.40
DEFAULT_WEIGHT_EXPOSURE = 0.30
DEFAULT_WEIGHT_VULNERABILITY = 0.30

# Path to Ahmedabad Wards GeoJSON
GEOJSON_PATH = os.path.join(os.path.dirname(__file__), "data", "Ahmedabad_Wards.geojson")


def load_ward_geojson(filepath: str = GEOJSON_PATH) -> Dict[str, Any]:
    """Loads Ahmedabad Wards GeoJSON spatial feature collection."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"GeoJSON file not found at {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def _percentile_rank(values: np.ndarray) -> np.ndarray:
    """Computes normalized percentile rank [0.0, 1.0] for a 1D array of values."""
    if len(values) <= 1:
        return np.ones_like(values)
    ranks = pd.Series(values).rank(pct=True, method="average").values
    return ranks


def generate_synthetic_hev_indicators(features: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Generates deterministic IPCC indicator metrics (Hazard, Exposure, Vulnerability)
    for each ward feature based on feature properties and spatial IDs.
    """
    records = []
    np.random.seed(42)  # Deterministic seed for reproducible testing

    for idx, feat in enumerate(features):
        props = feat.get("properties", {})
        name = props.get("Name", props.get("NAME", f"Ward_{idx+1}"))
        
        # Hazard H: Microclimate heat exposure, urban heat island factor, WBGT offset
        # Hash name deterministically to create realistic variation per ward
        base_hash = sum(ord(c) for c in str(name))
        h_raw = 34.0 + (base_hash % 70) / 10.0 + np.sin(idx) * 1.5  # Temp range ~34°C - 42°C
        
        # Exposure E: Population density, outdoor laborer workforce ratio
        e_raw = 5000 + (base_hash * 37) % 25000 + (idx * 300)       # Density ~5k - 30k /km²
        
        # Vulnerability V: Slum household %, elderly/child ratio, low vegetation cover
        v_raw = 0.15 + ((base_hash * 13) % 70) / 100.0             # Vulnerability 15% - 85%

        records.append({
            "ward_index": idx,
            "ward_name": name,
            "raw_hazard": h_raw,
            "raw_exposure": e_raw,
            "raw_vulnerability": v_raw,
            "geometry": feat.get("geometry")
        })

    df = pd.DataFrame(records)

    # Compute normalized percentile scores [0.0 - 1.0] for H, E, V
    df["hazard_score"] = _percentile_rank(df["raw_hazard"].values)
    df["exposure_score"] = _percentile_rank(df["raw_exposure"].values)
    df["vulnerability_score"] = _percentile_rank(df["raw_vulnerability"].values)

    return df


def calculate_ward_risk_and_monte_carlo(
    n_simulations: int = 500,
    w_h: float = DEFAULT_WEIGHT_HAZARD,
    w_e: float = DEFAULT_WEIGHT_EXPOSURE,
    w_v: float = DEFAULT_WEIGHT_VULNERABILITY,
    geojson_path: str = GEOJSON_PATH
) -> List[Dict[str, Any]]:
    """
    Calculates explainable percentile risk scores (H x E x V & Weighted Composite)
    and executes Monte Carlo draws over index weights to assess rank stability.

    Returns JSON-serializable list of ward risk records for map frontends.
    """
    geojson = load_ward_geojson(geojson_path)
    features = geojson.get("features", [])
    df = generate_synthetic_hev_indicators(features)

    # 1. Nominal Composite Risk Score (Multiplicative & Weighted Percentile)
    # Multiplicative IPCC formula: R = H * E * V
    df["multiplicative_risk"] = df["hazard_score"] * df["exposure_score"] * df["vulnerability_score"]
    
    # Weighted Linear Combination: R_weighted = w_h * H + w_e * E + w_v * V
    norm_w_sum = w_h + w_e + w_v
    w_h_norm, w_e_norm, w_v_norm = w_h / norm_w_sum, w_e / norm_w_sum, w_v / norm_w_sum

    df["composite_raw"] = (
        w_h_norm * df["hazard_score"] +
        w_e_norm * df["exposure_score"] +
        w_v_norm * df["vulnerability_score"]
    )
    
    # Final Percentile Risk Score (0 - 100)
    df["risk_percentile"] = (_percentile_rank(df["composite_raw"].values) * 100).round(1)
    
    # Nominal Rank (1 = Highest Risk, N = Lowest Risk)
    df["nominal_rank"] = df["composite_raw"].rank(ascending=False, method="min").astype(int)

    # 2. Monte Carlo Simulation (500 Draws over Weights)
    # Draw weights using Dirichlet distribution centered around nominal weights
    alpha_params = np.array([w_h_norm, w_e_norm, w_v_norm]) * 20.0  # Concentration = 20
    np.random.seed(100)
    weight_draws = np.random.dirichlet(alpha_params, size=n_simulations)  # Shape: (500, 3)

    # Matrix multiplication: Wards (N) x Draws (500)
    # Matrix H_E_V shape: (N, 3)
    hev_matrix = df[["hazard_score", "exposure_score", "vulnerability_score"]].values
    sim_scores = np.dot(hev_matrix, weight_draws.T)  # Shape: (N, 500)

    # Calculate ranks for each simulation draw (1 = highest risk)
    # Rank along axis 0 (wards) for each column (simulation draw)
    # Scipy / pandas rank per column
    sim_ranks = np.zeros_like(sim_scores)
    for col in range(n_simulations):
        # descending rank: highest score gets rank 1
        sim_ranks[:, col] = pd.Series(-sim_scores[:, col]).rank(method="min").values

    # 3. Compute Rank Uncertainty Statistics
    mean_ranks = np.mean(sim_ranks, axis=1)
    median_ranks = np.median(sim_ranks, axis=1)
    p05_ranks = np.percentile(sim_ranks, 5, axis=1)
    p95_ranks = np.percentile(sim_ranks, 95, axis=1)
    std_ranks = np.std(sim_ranks, axis=1)

    df["mc_mean_rank"] = np.round(mean_ranks, 1)
    df["mc_median_rank"] = np.round(median_ranks, 1)
    df["mc_rank_p05"] = np.round(p05_ranks, 1)
    df["mc_rank_p95"] = np.round(p95_ranks, 1)
    df["mc_rank_std"] = np.round(std_ranks, 2)
    df["rank_uncertainty_range"] = np.round(p95_ranks - p05_ranks, 1)

    # Stability Category Classification
    def categorize_stability(range_val):
        if range_val <= 3.0:
            return "HIGHLY_STABLE"
        elif range_val <= 7.0:
            return "MODERATE_CONFIDENCE"
        else:
            return "HIGH_UNCERTAINTY"

    df["rank_stability_category"] = df["rank_uncertainty_range"].apply(categorize_stability)

    # Risk Tier Classification
    def classify_risk_tier(pct):
        if pct >= 80.0:
            return {"tier": "CRITICAL", "color": "#7F1D1D", "label": "Top 20% Extreme Risk"}
        elif pct >= 60.0:
            return {"tier": "HIGH", "color": "#EF4444", "label": "High Heat Risk Zone"}
        elif pct >= 40.0:
            return {"tier": "MODERATE", "color": "#F59E0B", "label": "Moderate Vulnerability"}
        else:
            return {"tier": "LOW", "color": "#10B981", "label": "Relatively Low Heat Risk"}

    # 4. Construct JSON Response Array for Map Frontend
    results = []
    for idx, row in df.iterrows():
        tier_info = classify_risk_tier(row["risk_percentile"])
        
        results.append({
            "ward_id": f"WARD_{row['ward_index'] + 1:02d}",
            "ward_name": row["ward_name"],
            "risk_percentile": row["risk_percentile"],
            "risk_tier": tier_info["tier"],
            "risk_color": tier_info["color"],
            "tier_description": tier_info["label"],
            "ipcc_components": {
                "hazard_score": round(float(row["hazard_score"]), 3),
                "exposure_score": round(float(row["exposure_score"]), 3),
                "vulnerability_score": round(float(row["vulnerability_score"]), 3),
                "multiplicative_index": round(float(row["multiplicative_risk"]), 3),
                "raw_temperature_c": round(float(row["raw_hazard"]), 1),
                "raw_density_sqkm": int(row["raw_exposure"]),
                "raw_vulnerability_pct": round(float(row["raw_vulnerability"]) * 100, 1)
            },
            "monte_carlo_stability": {
                "nominal_rank": int(row["nominal_rank"]),
                "mean_rank": float(row["mc_mean_rank"]),
                "median_rank": float(row["mc_median_rank"]),
                "rank_5th_percentile": float(row["mc_rank_p05"]),
                "rank_95th_percentile": float(row["mc_rank_p95"]),
                "rank_std_dev": float(row["mc_rank_std"]),
                "uncertainty_band_width": float(row["rank_uncertainty_range"]),
                "stability_category": row["rank_stability_category"]
            },
            "geometry": row["geometry"]
        })

    # Sort results by composite risk percentile descending (highest risk first)
    results.sort(key=lambda x: x["risk_percentile"], reverse=True)
    return results


if __name__ == "__main__":
    print("Testing Monte Carlo Ward Risk Engine...")
    output = calculate_ward_risk_and_monte_carlo(n_simulations=500)
    print(f"Calculated risk & 500 Monte Carlo draws for {len(output)} wards.")
    top_ward = output[0]
    print(f"\nTop Risk Ward: {top_ward['ward_name']}")
    print(f"  Risk Percentile: {top_ward['risk_percentile']}% ({top_ward['risk_tier']})")
    print(f"  IPCC Scores    : H={top_ward['ipcc_components']['hazard_score']} | E={top_ward['ipcc_components']['exposure_score']} | V={top_ward['ipcc_components']['vulnerability_score']}")
    print(f"  Rank Stability : Nominal Rank #{top_ward['monte_carlo_stability']['nominal_rank']} | 90% CI: [{top_ward['monte_carlo_stability']['rank_5th_percentile']} - {top_ward['monte_carlo_stability']['rank_95th_percentile']}] ({top_ward['monte_carlo_stability']['stability_category']})")
