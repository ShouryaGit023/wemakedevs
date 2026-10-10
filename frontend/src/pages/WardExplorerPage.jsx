import React, { useState, useEffect, useCallback } from 'react';
import AhmedabadVectorMap from '../components/AhmedabadVectorMap';
import { ClimateShieldAPI } from '../services/api';

export default function WardExplorerPage({ onInspectWard, selectedZone = 'All 7 Zones' }) {
  const [wardsList, setWardsList] = useState([]);
  const [selectedWard, setSelectedWard] = useState(null);
  const [searchFilter, setSearchFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchWardsData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const rankingsRes = await ClimateShieldAPI.getClimateRiskRankings();
      const list = rankingsRes?.rankings || [];
      setWardsList(list);
      if (list.length > 0) {
        setSelectedWard(list[0]);
      }
    } catch (err) {
      console.error('Failed to load wards in WardExplorer:', err);
      setError(err.message || 'Failed to load ward data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchWardsData();
  }, [fetchWardsData]);

  const filteredWards = wardsList.filter((w) => {
    const q = searchFilter.toLowerCase();
    const matchesSearch =
      !searchFilter ||
      (w.name && w.name.toLowerCase().includes(q)) ||
      (w.official_name && w.official_name.toLowerCase().includes(q)) ||
      (w.id && w.id.toLowerCase().includes(q));

    const matchesZone =
      !selectedZone ||
      selectedZone === 'All 7 Zones' ||
      (w.official_name && w.official_name.toLowerCase().includes(selectedZone.toLowerCase()));

    return matchesSearch && matchesZone;
  });

  const activeWard = selectedWard || wardsList[0] || {
    id: 'W1',
    name: 'Danilimda',
    combined_risk_score: 45,
    combined_risk_category: 'MODERATE',
    official_name: '36 DANILIMDA',
  };

  const activeScore = Math.round(activeWard.combined_risk_score ?? activeWard.composite_score ?? 50);
  const activeWbgt = activeWard.heat_risk?.effective_wbgt_c ?? activeWard.heat_risk?.score ?? 28.1;
  const activeWaterlogging = activeWard.water_risk?.waterlogging_score != null 
    ? `${Math.round(activeWard.water_risk.waterlogging_score)}/100` 
    : '38/100';
  const activeShortage = activeWard.water_risk?.water_shortage_score != null 
    ? `${Math.round(activeWard.water_risk.water_shortage_score)}/100` 
    : '19/100';
  const activeHeat = activeWard.heat_risk?.score ? `${Math.round(activeWard.heat_risk.score)}/100 Heat Index` : 'Elevated Heat Risk';

  const gwContext = activeWard.water_risk?.groundwater_context;

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-2 border-b border-outline-variant">
        <div>
          <div className="flex items-center gap-2 font-mono text-[10px] text-outline mb-0.5 uppercase tracking-wider">
            <span>AMC Command Center</span>
            <span>/</span>
            <span className="text-primary font-bold">Ward Explorer</span>
          </div>
          <h1 className="text-headline-md font-headline-md text-primary font-bold">
            Ahmedabad Ward Multi-Hazard Explorer
          </h1>
        </div>

        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Search all 48 wards..."
            value={searchFilter}
            onChange={(e) => setSearchFilter(e.target.value)}
            className="h-9 px-3 text-xs bg-white border border-outline-variant rounded-lg w-56 focus:outline-none focus:border-primary"
          />
        </div>
      </div>

      {loading && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center gap-2 text-xs text-primary font-mono animate-pulse">
          <span className="material-symbols-outlined text-[18px] animate-spin">sync</span>
          <span>Loading spatial multi-hazard risk models and hydrogeology telemetry...</span>
        </div>
      )}

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-xl flex items-center justify-between text-xs text-error">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px]">error</span>
            <span className="font-mono">{error}</span>
          </div>
          <button
            onClick={fetchWardsData}
            className="px-3 py-1 bg-white border border-red-300 rounded font-mono font-bold hover:bg-red-50 cursor-pointer"
          >
            Retry
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        <div className="xl:col-span-8">
          <AhmedabadVectorMap 
            liveWards={wardsList}
            onInspectWard={onInspectWard}
            onSelectWard={(w) => {
              const found = wardsList.find(x => 
                (x.name && x.name.toLowerCase() === w.name.toLowerCase()) ||
                (x.id && x.id.toLowerCase() === w.id?.toLowerCase())
              );
              if (found) setSelectedWard(found);
            }}
          />
        </div>

        <div className="xl:col-span-4 bg-surface-container-lowest rounded-xl border border-outline-variant p-4 shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-2 border-b">
            <h3 className="font-bold text-sm text-primary">Ward Dossier Preview</h3>
            <span className={`font-mono text-[10px] px-2 py-0.5 rounded font-bold ${
              activeScore >= 70 ? 'bg-error-container text-on-error-container' : 'bg-amber-100 text-amber-800'
            }`}>
              {activeWard.combined_risk_category || 'RISK'} {activeScore}/100
            </span>
          </div>

          <div>
            <div className="text-lg font-bold text-on-surface">
              {activeWard.name} ({activeWard.id || activeWard.ward_id})
            </div>
            <div className="text-xs font-mono text-outline">
              {activeWard.official_name || 'Ahmedabad Municipal Ward'} • Rank #{activeWard.rank || 1}
            </div>
          </div>

          {/* Separated Hazard Scores */}
          <div className="space-y-2 text-xs">
            <div className="p-2.5 rounded-lg bg-surface-bright border flex justify-between items-center">
              <div>
                <span className="text-outline block font-medium">Thermal / Heat Hazard</span>
                <span className="text-[10px] text-outline font-mono">WBGT {activeWbgt}°C</span>
              </div>
              <span className="font-bold font-mono text-error">{activeHeat}</span>
            </div>

            <div className="p-2.5 rounded-lg bg-surface-bright border flex justify-between items-center">
              <div>
                <span className="text-outline block font-medium">Waterlogging (Pluvial Flood)</span>
                <span className="text-[10px] text-outline font-mono">Monsoon surface runoff</span>
              </div>
              <span className="font-bold font-mono text-[#0284C7]">{activeWaterlogging}</span>
            </div>

            <div className="p-2.5 rounded-lg bg-surface-bright border flex justify-between items-center">
              <div>
                <span className="text-outline block font-medium">Water-Shortage Deficit</span>
                <span className="text-[10px] text-outline font-mono">Bulk reserves & supply</span>
              </div>
              <span className="font-bold font-mono text-amber-700">{activeShortage}</span>
            </div>

            <div className="p-2.5 rounded-lg bg-surface-bright border flex justify-between items-center">
              <span className="text-outline font-medium">Compound Hazard Synergy</span>
              <span className={`font-bold font-mono text-[11px] px-2 py-0.5 rounded ${
                activeWard.compound_hazard?.compound_synergy_active 
                  ? 'bg-red-100 text-red-800' 
                  : 'bg-slate-100 text-slate-700'
              }`}>
                {activeWard.compound_hazard?.compound_synergy_active ? 'Dual-Hazard Hotspot' : 'Standard Baseline'}
              </span>
            </div>
          </div>

          {/* Groundwater Status Block with strict provenance */}
          <div className="p-3 rounded-lg border border-outline-variant bg-[#F8FAF8] space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-primary flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[15px] text-[#0284C7]">water_drop</span>
                Groundwater Table
              </span>
              {gwContext?.has_proximate_station ? (
                <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-blue-100 text-blue-900 font-bold border border-blue-200">
                  CGWB OBSERVATION — HISTORICAL
                </span>
              ) : gwContext?.district_average_depth_mbgl ? (
                <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-800 font-bold border border-slate-200">
                  DISTRICT BASELINE (ESTIMATE)
                </span>
              ) : (
                <span className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-600 font-bold border">
                  UNAVAILABLE
                </span>
              )}
            </div>

            {gwContext?.has_proximate_station ? (
              <div className="space-y-1 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-outline text-[11px]">Station: {gwContext.station_name}</span>
                  <span className="font-mono font-bold text-on-surface">
                    {gwContext.water_level_mbgl != null ? `${gwContext.water_level_mbgl} mbgl` : 'N/A'}
                  </span>
                </div>
                <div className="flex items-center justify-between text-[10px] text-outline font-mono">
                  <span>Stress: {gwContext.aquifer_stress_tier?.replace(/_/g, ' ') || 'MODERATE'}</span>
                  <span>{gwContext.observation_date ? `Date: ${gwContext.observation_date}` : 'CGWB In-Situ'}</span>
                </div>
                <p className="text-[10px] text-slate-500 italic leading-tight pt-0.5">
                  In-situ piezometer observation; unconfined aquifer depth.
                </p>
              </div>
            ) : gwContext?.district_average_depth_mbgl ? (
              <div className="space-y-1 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-outline text-[11px]">Ahmedabad District Mean:</span>
                  <span className="font-mono font-bold text-on-surface">
                    {gwContext.district_average_depth_mbgl} mbgl
                  </span>
                </div>
                <div className="flex items-center justify-between text-[10px] text-outline font-mono">
                  <span>Tier: {gwContext.aquifer_stress_tier?.replace(/_/g, ' ') || 'HIGH AQUIFER STRESS'}</span>
                  <span>CGWB 37-Well Baseline</span>
                </div>
                <p className="text-[10px] text-slate-500 italic leading-tight pt-0.5">
                  No dedicated piezometer in ward boundary. Regional aquifer baseline applied.
                </p>
              </div>
            ) : (
              <p className="text-[11px] text-outline italic">
                No verified in-situ groundwater measurement available for this ward.
              </p>
            )}
          </div>

          <button
            onClick={() => onInspectWard && onInspectWard(activeWard)}
            className="w-full py-2 bg-primary-container text-white rounded-lg text-xs font-semibold hover:bg-[#1B5742] transition-colors cursor-pointer"
          >
            Open Comprehensive Ward Dossier
          </button>
        </div>
      </div>
    </div>
  );
}
