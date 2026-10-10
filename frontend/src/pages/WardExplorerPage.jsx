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
  const activeWater = activeWard.water_risk?.waterlogging_score ? `${Math.round(activeWard.water_risk.waterlogging_score)}% Surcharge` : '38% Pluvial Risk';
  const activeHeat = activeWard.heat_risk?.score ? `${Math.round(activeWard.heat_risk.score)}/100 Heat Index` : 'Elevated Heat Risk';

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

          <div className="space-y-2 text-xs">
            <div className="p-2.5 rounded-lg bg-surface-bright border flex justify-between">
              <span className="text-outline">Thermal / Heat Hazard</span>
              <span className="font-bold font-mono text-error">{activeHeat}</span>
            </div>
            <div className="p-2.5 rounded-lg bg-surface-bright border flex justify-between">
              <span className="text-outline">Wet-Bulb Globe (WBGT)</span>
              <span className="font-bold font-mono text-error">{activeWbgt}°C</span>
            </div>
            <div className="p-2.5 rounded-lg bg-surface-bright border flex justify-between">
              <span className="text-outline">Waterlogging Surcharge</span>
              <span className="font-bold font-mono text-[#0284C7]">{activeWater}</span>
            </div>
            <div className="p-2.5 rounded-lg bg-surface-bright border flex justify-between">
              <span className="text-outline">Synergy Active</span>
              <span className="font-bold font-mono text-amber-700">
                {activeWard.compound_hazard?.compound_synergy_active ? 'Dual-Hazard Hotspot' : 'Standard Baseline'}
              </span>
            </div>
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
