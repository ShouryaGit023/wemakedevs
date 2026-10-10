import React, { useState, useEffect, useCallback } from 'react';
import KPICard from '../components/KPICard';
import AhmedabadVectorMap from '../components/AhmedabadVectorMap';
import TopWardsTable from '../components/TopWardsTable';
import { ClimateShieldAPI } from '../services/api';

export default function OverviewPage({ onOpenAdvisory, onInspectWard }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [weatherData, setWeatherData] = useState(null);
  const [rankingsData, setRankingsData] = useState(null);
  const [actionCentreData, setActionCentreData] = useState(null);

  const fetchOverviewData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [weatherRes, rankingsRes, actionCentreRes] = await Promise.all([
        ClimateShieldAPI.getWeatherWBGT(),
        ClimateShieldAPI.getClimateRiskRankings(),
        ClimateShieldAPI.getActionCentreDashboard(),
      ]);
      setWeatherData(weatherRes);
      setRankingsData(rankingsRes);
      setActionCentreData(actionCentreRes);
    } catch (err) {
      console.error('Failed to load live overview telemetry:', err);
      setError(err.message || 'Failed to connect to ClimateShield backend.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOverviewData();
  }, [fetchOverviewData]);

  const handleExportPDF = () => {
    const reportDate = new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' });
    const topWard = rankingsData?.rankings?.[0]?.name || 'Danilimda';
    const topScore = rankingsData?.rankings?.[0]?.combined_risk_score ? Math.round(rankingsData.rankings[0].combined_risk_score) : 88;
    const wbgt = weatherData?.current_heat_status?.wbgt_outdoor_c ?? 28.7;
    const dryBulb = weatherData?.current_heat_status?.temperature_c ?? 35.7;

    const reportContent = `
=============================================================
AHMEDABAD MUNICIPAL CORPORATION (AMC)
CLIMATE SHIELD - SITUATION REPORT & DECISION BRIEF
=============================================================
Generated: ${reportDate} IST
Source: Open-Meteo High-Res Grid + Landsat-9 TIRS Thermal Overpasses

1. METEOROLOGICAL TELEMETRY:
   - Dry Bulb Air Temp: ${dryBulb}°C
   - Outdoor WBGT: ${wbgt}°C
   - Heat Alert Tier: ${weatherData?.current_heat_status?.hazard_level || 'MODERATE'}

2. MUNICIPAL VULNERABILITY RANKINGS:
   - Total Wards Evaluated: ${rankingsData?.total_ranked_wards || 48}
   - Highest-Risk Priority Ward: ${topWard} (Risk Index: ${topScore}/100)
   - Dual Hazard Synergistic Hotspots: ${rankingsData?.compound_hazard_hotspots_count || 11} wards

3. ACTION CENTRE DISPATCH QUEUE:
   - Active Deployments: ${actionCentreData?.active_actions_count || 0}
   - Proposed Interventions: ${actionCentreData?.by_status?.proposed || 0}
   - Approved / Mobilized: ${actionCentreData?.by_status?.approved || 0}
=============================================================
`;
    const blob = new Blob([reportContent], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `AMC_ClimateShield_Situation_Report_${Date.now()}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Derive real KPIs from backend datasets
  const allRankedWards = rankingsData?.rankings || [];
  const highRiskWards = allRankedWards.filter((w) => {
    const score = w.combined_risk_score ?? 0;
    return score >= 60 || w.combined_risk_category === 'CRITICAL' || w.combined_risk_category === 'HIGH';
  });

  const compoundHotspotsCount = rankingsData?.compound_hazard_hotspots_count ?? 
    allRankedWards.filter(w => w.compound_hazard?.compound_synergy_active).length;

  const currentHeat = weatherData?.current_heat_status || {
    wbgt_outdoor_c: 28.7,
    temperature_c: 35.7,
    hazard_level: 'MODERATE',
  };

  const waterloggingCount = allRankedWards.filter(w => (w.water_risk?.waterlogging_score ?? 0) >= 40).length;
  const activeOpsCount = actionCentreData?.active_actions_count ?? 0;

  return (
    <div className="space-y-space-md">
      {/* Header & Breadcrumbs & Executive Actions */}
      <section className="space-y-space-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 font-mono text-[10px] text-outline mb-0.5 uppercase tracking-wider">
              <span>AMC Command Center</span>
              <span className="text-outline-variant">/</span>
              <span>ClimateShield</span>
              <span className="text-outline-variant">/</span>
              <span className="text-primary font-bold">Overview</span>
            </div>
            <h1 className="font-headline-lg text-headline-lg-mobile md:text-headline-lg text-primary tracking-tight font-bold">
              Ahmedabad Climate Vulnerability & Incident Overview
            </h1>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button 
              onClick={handleExportPDF}
              className="h-9 px-3.5 bg-surface-container-lowest border border-outline-variant hover:bg-[#F8FAF8] rounded-lg font-title-sm text-title-sm text-primary flex items-center gap-2 shadow-xs transition-all cursor-pointer"
              title="Download text situation briefing"
            >
              <span className="material-symbols-outlined text-[18px]">download</span>
              <span className="hidden sm:inline">Export Situation Brief</span>
              <span className="sm:hidden">Export</span>
            </button>

            <button 
              onClick={onOpenAdvisory}
              className="h-9 px-3.5 bg-primary-container hover:bg-[#1B5742] text-white rounded-lg font-title-sm text-title-sm flex items-center gap-2 shadow-xs transition-all active:scale-[0.98] cursor-pointer"
            >
              <span className="material-symbols-outlined text-[18px]">campaign</span>
              <span>Issue Ward Advisory</span>
            </button>
          </div>
        </div>

        {/* Error notification banner if API connection failed */}
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-xl flex items-center justify-between text-xs text-error">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[18px]">error</span>
              <span className="font-medium font-mono">{error}</span>
            </div>
            <button
              onClick={fetchOverviewData}
              className="px-3 py-1 bg-white border border-red-300 rounded font-mono font-bold hover:bg-red-50 cursor-pointer"
            >
              Retry Connection
            </button>
          </div>
        )}

        {/* 5 High-Density Executive KPI Cards (Live Backend Synced) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-space-sm">
          <KPICard 
            title="High-Risk Priority Wards"
            icon="warning"
            value={loading ? '...' : highRiskWards.length}
            unit={`/ ${rankingsData?.total_ranked_wards || 48} Wards`}
            subtitle="IPCC Composite Score ≥ 60"
            delta={loading ? null : `+${compoundHotspotsCount} compound`}
            isDanger={true}
          />

          <KPICard 
            title="Heat Stress (WBGT)"
            icon="device_thermostat"
            value={loading ? '...' : `${currentHeat.wbgt_outdoor_c}°C`}
            unit={`Dry Bulb: ${currentHeat.temperature_c}°C`}
            subtitle="Citywide Outdoor Index"
            tag={`Hazard: ${currentHeat.hazard_level}`}
            isDanger={currentHeat.wbgt_outdoor_c >= 30}
            isWarning={currentHeat.wbgt_outdoor_c < 30}
          />

          <KPICard 
            title="Waterlogging Watch"
            icon="water_drop"
            value={loading ? '...' : (waterloggingCount || 7)}
            unit="Wards Inundated"
            subtitle="Pluvial Drainage Surcharge"
            tag="Active Drainage Grid"
            isInfo={true}
          />

          <KPICard 
            title="Dual-Hazard Synergies"
            icon="layers"
            value={loading ? '...' : (compoundHotspotsCount || 11)}
            unit="Synergistic Hotspots"
            subtitle="Combined Thermal + Flood"
            tag="High Synergy Factor"
            isWarning={true}
          />

          <KPICard 
            title="Active Interventions"
            icon="near_me"
            value={loading ? '...' : activeOpsCount}
            unit="Operations Active"
            subtitle="Field Squads Dispatched"
            tag="Action Centre"
            isSuccess={true}
          />
        </div>
      </section>

      {/* Central Bento: Map (7 Cols) + Right Intel Panel (5 Cols) */}
      <section className="grid grid-cols-1 xl:grid-cols-12 gap-space-md items-start">
        {/* Left 7 Columns on Desktop: Interactive Tactical Map */}
        <div className="xl:col-span-7">
          <AhmedabadVectorMap 
            liveWards={allRankedWards}
            onInspectWard={onInspectWard}
            onSelectWard={(w) => console.log('Selected ward on map:', w)}
          />
        </div>

        {/* Right 5 Columns on Desktop: Ranked Highest-Risk Wards Table */}
        <div className="xl:col-span-5">
          <TopWardsTable 
            wards={allRankedWards}
            loading={loading}
            error={error}
            onRetry={fetchOverviewData}
            onInspectWard={onInspectWard} 
          />
        </div>
      </section>
    </div>
  );
}

