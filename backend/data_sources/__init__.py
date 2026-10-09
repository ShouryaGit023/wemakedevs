"""
ClimateShield - Data Sources & Fusion Package
Ingests external satellite and reanalysis data (Copernicus ERA5-Land, NASA ECOSTRESS)
and formats parameters for ClimateShield risk and optimization engines.
"""

from backend.data_sources.cache import DataSourceCache
from backend.data_sources.era5_land import ERA5LandClient
from backend.data_sources.ecostress import ECOSTRESSClient
from backend.data_sources.fusion import DataFusionEngine
from backend.data_sources.service import DataSourcesService

__all__ = [
    "DataSourceCache",
    "ERA5LandClient",
    "ECOSTRESSClient",
    "DataFusionEngine",
    "DataSourcesService"
]
