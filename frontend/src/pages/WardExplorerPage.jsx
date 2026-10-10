import React, { useState } from 'react';
import AhmedabadVectorMap from '../components/AhmedabadVectorMap';
import { TOP_RISK_WARDS } from '../data/mockData';

export default function WardExplorerPage({ onInspectWard }) {
  const [selectedWard, setSelectedWard] = useState(TOP_RISK_WARDS[0]);
  const [searchFilter, setSearchFilter] = useState('');

  const filteredWards = TOP_RISK_WARDS.filter(w => 
    w.name.toLowerCase().includes(searchFilter.toLowerCase()) ||
    w.zone.toLowerCase().includes(searchFilter.toLowerCase()) ||
    w.ward_id.toLowerCase().includes(searchFilter.toLowerCase())
  );

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

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        <div className="xl:col-span-8">
          <AhmedabadVectorMap 
            onInspectWard={onInspectWard}
            onSelectWard={(w) => {
              const found = TOP_RISK_WARDS.find(x => x.name.toLowerCase() === w.name.toLowerCase());
              if (found) setSelectedWard(found);
            }}
          />
        </div>

        <div className="xl:col-span-4 bg-surface-container-lowest rounded-xl border border-outline-variant p-4 shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-2 border-b">
            <h3 className="font-bold text-sm text-primary">Ward Dossier Preview</h3>
            <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-error-container text-on-error-container font-bold">
              {selectedWard.status} {selectedWard.composite_score}/100
            </span>
          </div>

          <div>
            <div className="text-lg font-bold text-on-surface">{selectedWard.name} ({selectedWard.ward_id})</div>
            <div className="text-xs font-mono text-outline">{selectedWard.zone} • Population: {selectedWard.population?.toLocaleString()}</div>
          </div>

          <div className="space-y-2 text-xs">
            <div className="p-2.5 rounded-lg bg-surface-bright border flex justify-between">
              <span className="text-outline">Dry Bulb / LST</span>
              <span className="font-bold font-mono text-error">{selectedWard.dry_bulb}°C Max</span>
            </div>
            <div className="p-2.5 rounded-lg bg-surface-bright border flex justify-between">
              <span className="text-outline">Wet-Bulb Globe (WBGT)</span>
              <span className="font-bold font-mono text-error">{selectedWard.wbgt}°C (Alert)</span>
            </div>
            <div className="p-2.5 rounded-lg bg-surface-bright border flex justify-between">
              <span className="text-outline">Potable Water Deficit</span>
              <span className="font-bold font-mono text-[#0284C7]">{selectedWard.water_deficit}</span>
            </div>
            <div className="p-2.5 rounded-lg bg-surface-bright border flex justify-between">
              <span className="text-outline">Cool Roof Coverage Gap</span>
              <span className="font-bold font-mono text-amber-700">{selectedWard.cool_roof_deficit} Deficit</span>
            </div>
          </div>

          <button
            onClick={() => onInspectWard(selectedWard)}
            className="w-full py-2 bg-primary-container text-white rounded-lg text-xs font-semibold hover:bg-[#1B5742] transition-colors cursor-pointer"
          >
            Open Comprehensive Ward Dossier
          </button>
        </div>
      </div>
    </div>
  );
}
