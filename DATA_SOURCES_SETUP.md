# ClimateShield - External Data Sources & Fusion Setup Guide

This document describes how to configure, authenticate, and query the **Copernicus ERA5-Land** and **NASA ECOSTRESS** data sources layer in ClimateShield.

---

## 1. Overview of Data Sources

| Data Source | Provider | Extracted Variables | Native Resolution | Primary Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Copernicus ERA5-Land** | Copernicus Climate Change Service (C3S) / ECMWF | `2m_temperature`, `2m_dewpoint_temperature`, `total_precipitation`, `volumetric_soil_water_layer_1`, `surface_solar_radiation_downwards`, `10m_u_wind`, `10m_v_wind` | ~9 km (0.1°) grid, Hourly | Macro-climate temperature, relative humidity, solar radiation, wind speed, and 24h precipitation. |
| **NASA ECOSTRESS** | NASA Land Processes Distributed Active Archive Center (LP DAAC) | `ECO2LST.001` (Land Surface Temperature & Emissivity), `ECO3ETPTJ.001` (Evapotranspiration & Evaporative Stress Index) | ~70 m spatial resolution, ISS orbit overpasses (1–5 day revisit) | High-resolution microclimate Land Surface Temperature (LST) anomaly per ward and drought stress indicator. |

---

## 2. Environment Variables Configuration

To authenticate with Copernicus CDS and NASA Earthdata, set the following environment variables in your environment or `.env` file:

```bash
# Copernicus Climate Data Store (CDS) Credentials
export CDSAPI_KEY="your-copernicus-cds-api-key"
export CDSAPI_URL="https://cds.climate.copernicus.eu/api/v2"  # Optional override

# NASA Earthdata Access Credentials
export EARTHDATA_BEARER_TOKEN="your-nasa-earthdata-bearer-token"
# OR Username & Password
export EARTHDATA_USERNAME="your-earthdata-username"
export EARTHDATA_PASSWORD="your-earthdata-password"
```

### Obtaining Credentials

#### Copernicus CDS Key:
1. Register at [Copernicus Climate Data Store](https://cds.climate.copernicus.eu/).
2. Go to your User Profile page to copy your Personal Access Token (`UID:API-Key`).
3. Set `CDSAPI_KEY` or place it in `~/.cdsapirc`:
   ```ini
   url: https://cds.climate.copernicus.eu/api/v2
   key: <UID>:<API-KEY>
   ```

#### NASA Earthdata Token:
1. Create a free account at [NASA Earthdata Login](https://urs.earthdata.nasa.gov/).
2. Generate a Personal Access Token under *Generate Token*.
3. Set `EARTHDATA_BEARER_TOKEN` or `EARTHDATA_USERNAME` / `EARTHDATA_PASSWORD`.

---

## 3. Data Sources Architecture

```
backend/data_sources/
├── __init__.py          # Data Sources package exports
├── cache.py             # Local disk cache manager (SHA-256 keying, TTL expiration)
├── era5_land.py         # Copernicus CDS API client, NetCDF/JSON parser & unit converter
├── ecostress.py         # NASA CMR API client, cloud mask/QA filter & staleness handler
└── fusion.py            # Ward spatial fusion engine mapping data to Ahmedabad_Wards.geojson
```

---

## 4. API Endpoints Reference

ClimateShield exposes the following endpoints for fetching and inspecting external dataset feeds:

### 1. Copernicus ERA5-Land Endpoint
* **Endpoint**: `GET /api/data-sources/era5`
* **Query Parameters**:
  * `start_date` (optional): `YYYY-MM-DD`
  * `end_date` (optional): `YYYY-MM-DD`
  * `force_refresh` (optional): `true`/`false`
* **Response Payload Example**:
  ```json
  {
    "source": "Copernicus ERA5-Land Reanalysis",
    "status": "SUCCESS",
    "credentials_configured": true,
    "bbox": [23.3, 72.3, 22.8, 72.8],
    "records": [
      {
        "timestamp": "2026-05-01T12:00:00Z",
        "temperature_c": 35.0,
        "dewpoint_c": 20.0,
        "relative_humidity_pct": 41.2,
        "precipitation_mm": 0.0,
        "soil_moisture_m3m3": 0.28,
        "solar_radiation_wm2": 700.0,
        "wind_speed_ms": 5.0
      }
    ]
  }
  ```

### 2. NASA ECOSTRESS Satellite Overpass Endpoint
* **Endpoint**: `GET /api/data-sources/ecostress`
* **Query Parameters**:
  * `product_type`: `LST` or `ET`
  * `reference_date` (optional): `YYYY-MM-DD`
* **Response Payload Example**:
  ```json
  {
    "source": "NASA ECOSTRESS",
    "status": "SUCCESS",
    "has_valid_observation": true,
    "product_type": "LST",
    "acquisition_timestamp": "2026-05-01T08:14:22Z",
    "cloud_cover_pct": 2.5,
    "quality_indicator": "HIGH_CONFIDENCE",
    "data_staleness_days": 0.3,
    "spatial_resolution": "70m x 70m",
    "ward_lst_anomalies": {
      "Danilimda": 2.8,
      "Behrampura": 2.4,
      "Sabarmati": -0.8
    }
  }
  ```

### 3. Fused Ward Climate Profile Endpoint
* **Endpoint**: `GET /api/data-sources/fusion`
* **Query Parameters**:
  * `target_date` (optional): `YYYY-MM-DD`
* **Response**: Spatial overlay of ERA5-Land macro-climate + ECOSTRESS thermal observations across all 48 Ahmedabad wards in [`Ahmedabad_Wards.geojson`](file:///c:/Users/shram/wemakedevs/backend/data/Ahmedabad_Wards.geojson).

---

## 5. Data Fusion & Missing Values Principles

1. **Ward Standardization**:
   * Standardizes ward names (stripping numeric prefixes, e.g. `48 RAMOL HATHIJAN` -> `Ramol Hathijan`).
   * Maps canonical IDs: core Ahmedabad Heat Action Plan wards are assigned `W1`–`W10` (`Danilimda` -> `W1`, `Behrampura` -> `W2`, `Asarwa` -> `W3`, `Bapunagar` -> `W4`, `Khadia` -> `W5`, `Amraiwadi` -> `W6`, `Vatva` -> `W7`, `Sabarmati` -> `W8`, `Maninagar` -> `W9`, `Naroda` -> `W10`).
   * Validates spatial polygons and centroids within the Ahmedabad bounding box ($22.8^\circ - 23.3^\circ\text{ N}, 72.3^\circ - 72.8^\circ\text{ E}$).

2. **Strict Missing Observation Policy (NEVER ZERO)**:
   * **Rule**: Missing NASA ECOSTRESS observations due to orbital gaps or cloud cover are **NEVER treated as $0.0^\circ\text{C}$**.
   * Setting a missing thermal anomaly to 0.0 would falsely report that the ward is at exact city average temperature with zero microclimate effect.
   * Instead:
     * `ecostress_lst_c` = `None`
     * `ecostress_lst_anomaly_c` = `None`
     * `has_ecostress_observation` = `False`
     * `ecostress_quality_flag` = `"MISSING_OBSERVATION"`
     * `temperature_estimation_mode` = `"STRUCTURAL_PRIOR_UNOBSERVED"`
     * An explicit **uncertainty penalty** (`uncertainty_margin_c` = $1.8^\circ\text{C}$) and structural vulnerability prior are applied so decision-makers know the metric is estimated rather than observed.

3. **Engine Compatibility**:
   * Provides formatting adapters: `to_heat_engine_format()`, `to_water_engine_format()`, and `to_combined_risk_format()`.
   * Preserves all existing engine algorithms without modification.

---

## 6. Running Tests

To verify the Data Sources layer and Data Fusion module, run:

```bash
python -m unittest backend/tests/test_data_sources.py
```

To run the complete suite including existing engines:

```bash
python backend/run_all_tests.py
```

