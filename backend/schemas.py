"""
ClimateShield - Pydantic Data Schemas for Phase 0 Baseline & Outcome Ingestion
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional


class OutcomeRecordCreate(BaseModel):
    record_date: str = Field(..., example="2026-05-15", description="Date of record in YYYY-MM-DD")
    ward_id: str = Field(..., example="W1", description="Ward identifier (e.g. W1 to W10)")
    hospital_heat_admissions: int = Field(0, ge=0, description="Count of emergency/inpatient heat illness cases")
    mortality_count: int = Field(0, ge=0, description="Registered mortality count for the day")
    emergency_108_calls: int = Field(0, ge=0, description="GVK EMRI 108 heat-related calls")
    water_scarcity_complaints: int = Field(0, ge=0, description="Complaints received by civic cell")
    reported_by: Optional[str] = Field("AMC_HEALTH_SURVEILLANCE", description="Source agency or reporting unit")


class OutcomeRecordResponse(BaseModel):
    id: int
    record_date: str
    ward_id: str
    ward_name: Optional[str] = None
    hospital_heat_admissions: int
    mortality_count: int
    emergency_108_calls: int
    water_scarcity_complaints: int
    reported_by: str
    created_at: str


class WardBaselineSchema(BaseModel):
    id: str
    name: str
    slum_density: float
    outdoor_labor_ratio: float
    elderly_ratio: float
    baseline_heat_risk: float
    population: int
    area_sq_km: float


class MunicipalPartnerInfo(BaseModel):
    pilot_city: str
    state: str
    country: str
    coordinates: Dict[str, float]
    governance_counterparts: List[Dict[str, str]]
    status: str
