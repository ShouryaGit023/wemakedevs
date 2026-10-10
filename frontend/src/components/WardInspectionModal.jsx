import React from 'react';

export default function WardInspectionModal({ ward, isOpen, onClose }) {
  if (!isOpen || !ward) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs select-none">
      <div className="bg-surface-container-lowest rounded-2xl border border-outline-variant shadow-xl w-full max-w-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="px-6 py-4 border-b border-outline-variant flex items-center justify-between bg-[#F8FAF8]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary-container text-white flex items-center justify-center font-bold">
              <span className="material-symbols-outlined text-[22px]">apartment</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-headline-sm text-headline-sm text-primary font-bold">
                  {ward.name} Ward
                </h3>
                <span className="px-2 py-0.5 rounded text-xs font-mono font-semibold bg-slate-100 text-slate-800 border">
                  {ward.ward_id || ward.id || 'AMC-E-04'}
                </span>
                <span className={`px-2 py-0.5 rounded text-xs font-mono font-bold ${
                  (ward.composite_score || ward.score) >= 80 ? 'bg-error-container text-on-error-container' : 'bg-amber-100 text-amber-800'
                }`}>
                  RISK {ward.composite_score || ward.score || 88}/100
                </span>
              </div>
              <p className="text-xs font-mono text-outline mt-0.5">
                Jurisdiction: {ward.zone || 'East Zone'} • Municipal Health Ward Unit
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 text-outline hover:text-primary rounded cursor-pointer">
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5 max-h-[75vh] overflow-y-auto">
          {/* Key Vulnerability Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3 bg-surface-bright rounded-xl border border-slate-200">
              <span className="text-[10px] font-mono uppercase text-outline block">Population</span>
              <span className="text-base font-bold font-mono text-on-surface">{ward.population || '172,400'}</span>
              <span className="text-[10px] text-on-surface-variant block mt-0.5">Census Agglomeration</span>
            </div>

            <div className="p-3 bg-surface-bright rounded-xl border border-slate-200">
              <span className="text-[10px] font-mono uppercase text-outline block">Wet-Bulb (WBGT)</span>
              <span className="text-base font-bold font-mono text-error">{ward.wbgt || '31.8'}°C</span>
              <span className="text-[10px] text-error font-medium block mt-0.5">Extreme Danger Threshold</span>
            </div>

            <div className="p-3 bg-surface-bright rounded-xl border border-slate-200">
              <span className="text-[10px] font-mono uppercase text-outline block">Waterlogging Stress</span>
              <span className="text-base font-bold font-mono text-[#0284C7]">{ward.water_deficit || '-22%'}</span>
              <span className="text-[10px] text-on-surface-variant block mt-0.5">Drainage Deficit</span>
            </div>

            <div className="p-3 bg-surface-bright rounded-xl border border-slate-200">
              <span className="text-[10px] font-mono uppercase text-outline block">Cooling Centers</span>
              <span className="text-base font-bold font-mono text-primary">{ward.cooling_centers || 3} Active</span>
              <span className="text-[10px] text-emerald-700 font-medium block mt-0.5">Operational Shelters</span>
            </div>
          </div>

          {/* Primary Hazard Analysis */}
          <div className="p-4 rounded-xl border border-outline-variant bg-[#F8FAF8] space-y-2">
            <div className="flex items-center gap-2 text-xs font-bold text-primary">
              <span className="material-symbols-outlined text-[16px] text-error">warning</span>
              <span>Compound Hazard & Urban Topology Profile</span>
            </div>
            <p className="text-xs text-on-surface-variant leading-relaxed">
              {ward.primary_factor || 'Severe Urban Heat Island effect intensified by tin/asbestos roof settlement density, coupled with Kharicut Canal inundation risk during peak monsoon.'}
            </p>
            <div className="text-[11px] font-mono text-outline pt-1 flex items-center justify-between">
              <span>Sensor Feed: AMC IoT Station #GT-09</span>
              <span>LST Peak: 47.4°C max recorded</span>
            </div>
          </div>

          {/* Active Field Recommendations */}
          <div>
            <h4 className="font-mono text-[11px] uppercase font-bold text-outline mb-2">
              Recommended Municipal Priority Interventions
            </h4>
            <div className="space-y-2 text-xs">
              <div className="p-2.5 rounded-lg border border-emerald-200 bg-emerald-50/50 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-600"></span>
                  <span className="font-semibold text-primary">High-Albedo Cool Roof Coating</span>
                  <span className="text-outline font-mono text-[10px]">(Target: 1,400 m²)</span>
                </div>
                <span className="font-mono text-emerald-800 font-bold text-[11px]">Est. Δ -5.4°C drop</span>
              </div>

              <div className="p-2.5 rounded-lg border border-blue-200 bg-blue-50/50 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-blue-600"></span>
                  <span className="font-semibold text-primary">Mobile Drinking Water Bowsers & Hydration Points</span>
                  <span className="text-outline font-mono text-[10px]">(Capacity: 20,000L)</span>
                </div>
                <span className="font-mono text-blue-800 font-bold text-[11px]">2 Units Deployed</span>
              </div>

              <div className="p-2.5 rounded-lg border border-amber-200 bg-amber-50/50 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-amber-600"></span>
                  <span className="font-semibold text-primary">Pop-up Shaded Canopies at Transit Corridors</span>
                  <span className="text-outline font-mono text-[10px]">(AMTS Hub)</span>
                </div>
                <span className="font-mono text-amber-800 font-bold text-[11px]">In Progress</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-outline-variant bg-[#F8FAF8] flex items-center justify-between text-xs">
          <span className="font-mono text-outline text-[11px]">AMC Telemetry v4.2 • Live Sync</span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => alert(`Exporting official PDF situation dossier for ${ward.name || 'Ward'}...`)}
              className="px-3 py-1.5 rounded-lg border border-outline-variant text-primary hover:bg-slate-100 font-semibold cursor-pointer"
            >
              Export Dossier (PDF)
            </button>
            <button
              onClick={onClose}
              className="px-4 py-1.5 rounded-lg bg-primary-container text-white font-semibold hover:bg-[#1B5742] cursor-pointer"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
