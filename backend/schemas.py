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


# -------------------------------------------------------------
# IMPACT ASSESSMENT SCHEMAS
# -------------------------------------------------------------

class IndicatorDetailSchema(BaseModel):
    indicator: str = Field(..., description="Canonical or raw indicator name")
    baseline_value: Optional[float] = Field(None, description="Pre-intervention baseline value")
    follow_up_value: Optional[float] = Field(None, description="Post-intervention follow-up value")
    unit: str = Field(..., description="Measurement unit (e.g. celsius, cm, hours, liters, count)")
    difference: Optional[float] = Field(None, description="Absolute change (follow_up - baseline)")
    percentage_change: Optional[float] = Field(None, description="Percentage change if baseline != 0")
    beneficial_direction: str = Field("DECREASE_IS_BENEFICIAL", description="DECREASE_IS_BENEFICIAL or INCREASE_IS_BENEFICIAL")
    is_improvement: Optional[bool] = Field(None, description="True if change was in the beneficial direction")
    baseline_timestamps: List[str] = Field(default_factory=list, description="Timestamps of baseline observations")
    follow_up_timestamps: List[str] = Field(default_factory=list, description="Timestamps of follow-up observations")
    source_types: List[str] = Field(default_factory=list, description="MEASURED, EXTERNAL_OBSERVATION, ESTIMATED, or SYNTHETIC_DEMO")
    quality_status: str = Field("VERIFIED", description="Data quality classification")
    notes: List[str] = Field(default_factory=list, description="Auditing notes and interval scale warnings")


class ImpactAssessmentCreate(BaseModel):
    assessment_id: str = Field(..., description="Unique assessment identifier")
    intervention_id: str = Field(..., description="Identifier of the intervention evaluated")
    ward_id: str = Field(..., description="Ward identifier (e.g. W1 to W10)")
    intervention_type: str = Field(..., description="Type of intervention evaluated")
    execution_status: str = Field("COMPLETED", description="Execution status: COMPLETED, DEPLOYED, OBSERVED, or SYNTHETIC_DEMO")
    verification_status: str = Field("VERIFIED", description="Verification outcome status")
    provenance_mode: str = Field("MEASURED", description="Overall provenance mode")
    is_synthetic: bool = Field(False, description="Whether assessment uses synthetic demonstration data")
    baseline_period: Dict[str, Any] = Field(default_factory=dict, description="Baseline observation window metadata")
    follow_up_period: Dict[str, Any] = Field(default_factory=dict, description="Follow-up observation window metadata")
    indicators: Dict[str, IndicatorDetailSchema] = Field(..., description="Indicator details keyed by indicator name")
    data_quality_warnings: List[str] = Field(default_factory=list, description="Data quality warnings or notices")
    attribution_disclaimer: Optional[str] = Field(None, description="Scientific attribution caveat")
    summary: Dict[str, Any] = Field(default_factory=dict, description="High-level counts and summary flags")


class ImpactAssessmentResponse(BaseModel):
    assessment_id: str
    intervention_id: str
    ward_id: str
    intervention_type: str
    execution_status: str
    verification_status: str
    provenance_mode: str
    is_synthetic: bool
    baseline_period: Dict[str, Any]
    follow_up_period: Dict[str, Any]
    indicators: Dict[str, Any]
    calculated_changes: Dict[str, Any]
    data_quality_warnings: List[str]
    attribution_disclaimer: str
    summary: Dict[str, Any]
    version: int
    created_at: str
    updated_at: str


class ImpactAssessmentHistoryRecord(BaseModel):
    history_id: int
    assessment_id: str
    version: int
    snapshot: Dict[str, Any]
    archived_at: str
    change_reason: Optional[str] = None

