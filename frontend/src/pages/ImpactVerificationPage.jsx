import React, { useState } from 'react';
import { 
  IMPACT_KPIS, 
  IMPACT_AUDIT_CASES, 
  DIURNAL_TEMPERATURE_PROFILE,
  AHMEDABAD_ZONES 
} from '../data/mockData';

export default function ImpactVerificationPage() {
  const [selectedHazard, setSelectedHazard] = useState('All Hazards');
  const [selectedWard, setSelectedWard] = useState('Gomtipur Ward (AMC-E-04)');
  const [selectedTier, setSelectedTier] = useState('All Confidence Tiers');
  const [auditCases, setAuditCases] = useState(IMPACT_AUDIT_CASES);
  const [activeDossierCase, setActiveDossierCase] = useState(IMPACT_AUDIT_CASES[0]);

  const handleDownloadME = () => {
    alert("Downloading comprehensive AMC Climate M&E Empirical Dossier (JSON / CSV / PDF)...");
  };

  const handleRegisterAudit = () => {
    alert("New Field Audit Registration Portal: Select intervention code and in-situ IoT node pair.");
  };

  return (
    <div className="space-y-5">
      {/* Breadcrumbs & Page Header */}
      <section className="flex flex-col gap-2">
        <div className="flex items-center gap-2 font-mono text-[10px] text-outline uppercase tracking-wider">
          <span>AMC Command Center</span>
          <span className="material-symbols-outlined text-[14px]">chevron_right</span>
          <span>ClimateShield</span>
          <span className="material-symbols-outlined text-[14px]">chevron_right</span>
          <span className="text-primary font-bold">Impact Verification</span>
        </div>

        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-2 border-b border-outline-variant/60">
          <div>
            <h1 className="text-headline-lg font-headline-lg text-primary tracking-tight font-bold">
              Impact Verification & Outcome Telemetry
            </h1>
            <p className="text-body-md font-body-md text-on-surface-variant mt-0.5 max-w-4xl">
              Empirical evaluation of climate interventions: baseline vs. follow-up telemetry, statistical significance, and municipal ROI audit.
            </p>
          </div>

          <div className="flex items-center gap-2.5 shrink-0">
            <button 
              onClick={handleDownloadME}
              className="inline-flex items-center gap-2 px-3.5 py-2 bg-surface-container-lowest border border-outline-variant text-primary rounded-lg text-title-sm font-title-sm hover:bg-surface-container-low transition-all shadow-xs cursor-pointer font-semibold"
            >
              <span className="material-symbols-outlined text-[18px]">download</span>
              <span>Download M&E Dossier</span>
            </button>

            <button 
              onClick={handleRegisterAudit}
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg text-title-sm font-title-sm hover:bg-[#1B5742] active:scale-[0.98] transition-all shadow-sm cursor-pointer font-semibold"
            >
              <span className="material-symbols-outlined text-[18px]">add_circle</span>
              <span>+ Register New Audit</span>
            </button>
          </div>
        </div>
      </section>

      {/* SECTION 1: TOP KPI SUMMARY CARDS (5-Card Grid) */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
        {/* KPI 1 */}
        <div className="bg-surface-container-lowest p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-outline uppercase tracking-wider font-bold">
              {IMPACT_KPIS.totalVerified.label}
            </span>
            <span className="p-1.5 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200">
              <span className="material-symbols-outlined text-[18px]">task_alt</span>
            </span>
          </div>
          <div className="mt-2">
            <div className="text-display-lg font-display-lg text-primary font-bold leading-none tabular-nums">
              {IMPACT_KPIS.totalVerified.value}
            </div>
            <div className="text-title-sm font-title-sm text-on-surface mt-1 font-semibold">
              {IMPACT_KPIS.totalVerified.subLabel}
            </div>
          </div>
          <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] font-mono">
            <span className="text-outline">{IMPACT_KPIS.totalVerified.footerLeft}</span>
            <span className="text-emerald-800 font-semibold">{IMPACT_KPIS.totalVerified.footerRight}</span>
          </div>
        </div>

        {/* KPI 2 */}
        <div className="bg-surface-container-lowest p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-outline uppercase tracking-wider font-bold">
              {IMPACT_KPIS.surfaceTempDrop.label}
            </span>
            <span className="p-1.5 rounded-lg bg-sky-50 text-sky-800 border border-sky-200">
              <span className="material-symbols-outlined text-[18px]">device_thermostat</span>
            </span>
          </div>
          <div className="mt-2">
            <div className="text-display-lg font-display-lg text-sky-800 font-bold leading-none tabular-nums">
              {IMPACT_KPIS.surfaceTempDrop.value}
            </div>
            <div className="text-title-sm font-title-sm text-on-surface mt-1 font-semibold">
              {IMPACT_KPIS.surfaceTempDrop.subLabel}
            </div>
          </div>
          <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] font-mono">
            <span className="text-outline">{IMPACT_KPIS.surfaceTempDrop.footerLeft}</span>
            <span className="text-emerald-700 font-semibold">{IMPACT_KPIS.surfaceTempDrop.footerRight}</span>
          </div>
        </div>

        {/* KPI 3 */}
        <div className="bg-surface-container-lowest p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-outline uppercase tracking-wider font-bold">
              {IMPACT_KPIS.runoffMitigation.label}
            </span>
            <span className="p-1.5 rounded-lg bg-teal-50 text-teal-800 border border-teal-200">
              <span className="material-symbols-outlined text-[18px]">water</span>
            </span>
          </div>
          <div className="mt-2">
            <div className="text-display-lg font-display-lg text-primary font-bold leading-none tabular-nums">
              {IMPACT_KPIS.runoffMitigation.value}
            </div>
            <div className="text-title-sm font-title-sm text-on-surface mt-1 font-semibold">
              {IMPACT_KPIS.runoffMitigation.subLabel}
            </div>
          </div>
          <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] font-mono">
            <span className="text-outline">{IMPACT_KPIS.runoffMitigation.footerLeft}</span>
            <span className="text-teal-800 font-semibold">{IMPACT_KPIS.runoffMitigation.footerRight}</span>
          </div>
        </div>

        {/* KPI 4 */}
        <div className="bg-surface-container-lowest p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-outline uppercase tracking-wider font-bold">
              {IMPACT_KPIS.evidenceConfidence.label}
            </span>
            <span className="p-1.5 rounded-lg bg-indigo-50 text-indigo-800 border border-indigo-200">
              <span className="material-symbols-outlined text-[18px]">analytics</span>
            </span>
          </div>
          <div className="mt-2">
            <div className="text-display-lg font-display-lg text-indigo-900 font-bold leading-none tabular-nums">
              {IMPACT_KPIS.evidenceConfidence.value}
            </div>
            <div className="text-title-sm font-title-sm text-on-surface mt-1 font-semibold">
              {IMPACT_KPIS.evidenceConfidence.subLabel}
            </div>
          </div>
          <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] font-mono">
            <span className="text-outline">{IMPACT_KPIS.evidenceConfidence.footerLeft}</span>
            <span className="text-indigo-800 font-semibold">{IMPACT_KPIS.evidenceConfidence.footerRight}</span>
          </div>
        </div>

        {/* KPI 5 */}
        <div className="bg-surface-container-lowest p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-outline uppercase tracking-wider font-bold">
              {IMPACT_KPIS.outcomeAudit.label}
            </span>
            <span className="p-1.5 rounded-lg bg-amber-50 text-amber-800 border border-amber-200">
              <span className="material-symbols-outlined text-[18px]">fact_check</span>
            </span>
          </div>
          <div className="mt-2">
            <div className="flex items-baseline gap-1.5 leading-none">
              <span className="text-display-lg font-display-lg text-emerald-800 font-bold tabular-nums">
                {IMPACT_KPIS.outcomeAudit.value}
              </span>
              <span className="text-sm font-mono text-outline">
                {IMPACT_KPIS.outcomeAudit.secondaryValue}
              </span>
            </div>
            <div className="text-title-sm font-title-sm text-on-surface mt-1 font-semibold">
              {IMPACT_KPIS.outcomeAudit.subLabel}
            </div>
          </div>
          <div className="mt-3 pt-2 border-t border-slate-100 flex items-center gap-1.5 text-[10px] font-mono">
            <span className="text-emerald-700 font-semibold">{IMPACT_KPIS.outcomeAudit.footerPill1}</span>
            <span className="text-slate-300">•</span>
            <span className="text-blue-700">{IMPACT_KPIS.outcomeAudit.footerPill2}</span>
            <span className="text-slate-300">•</span>
            <span className="text-rose-600">{IMPACT_KPIS.outcomeAudit.footerPill3}</span>
          </div>
        </div>
      </section>

      {/* SECTION 2: VERIFICATION FILTERS & METHODOLOGICAL BANNER */}
      <section className="flex flex-col gap-3">
        {/* Filter Toolbar */}
        <div className="bg-surface-container-lowest p-3 rounded-xl border border-slate-200 shadow-xs flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
          {/* Hazard Filter Tabs */}
          <div className="flex items-center gap-1 bg-surface-bright p-1 rounded-lg border border-slate-200 overflow-x-auto text-xs">
            {['All Hazards', 'Heatwave Interventions', 'Water Stress & Supply', 'Urban Flooding'].map((h) => (
              <button
                key={h}
                onClick={() => setSelectedHazard(h)}
                className={`px-3 py-1.5 rounded-md font-semibold transition-colors shrink-0 cursor-pointer ${
                  selectedHazard === h
                    ? 'bg-primary text-white shadow-xs'
                    : 'text-on-surface-variant hover:bg-slate-100'
                }`}
              >
                {h}
              </button>
            ))}
          </div>

          {/* Select Dropdowns: Ward, Evidence Tier, Status */}
          <div className="flex items-center gap-2 flex-wrap sm:flex-nowrap">
            <select
              value={selectedWard}
              onChange={(e) => setSelectedWard(e.target.value)}
              className="h-9 px-3 bg-surface-bright border border-slate-300 rounded-lg text-xs font-medium text-on-surface focus:outline-none focus:border-primary cursor-pointer"
            >
              <option>Gomtipur Ward (AMC-E-04)</option>
              <option>Danilimda Ward (AMC-S-14)</option>
              <option>Odhav Ward (AMC-E-08)</option>
              <option>Nikol Ward (AMC-E-02) [Control]</option>
              <option>All 48 Municipal Wards</option>
            </select>

            <select
              value={selectedTier}
              onChange={(e) => setSelectedTier(e.target.value)}
              className="h-9 px-3 bg-surface-bright border border-slate-300 rounded-lg text-xs font-medium text-on-surface focus:outline-none focus:border-primary cursor-pointer"
            >
              <option>All Confidence Tiers</option>
              <option>Tier 1 Empirical IoT (In-situ)</option>
              <option>Tier 2 Satellite Remote Sensing</option>
              <option>Tier 3 Calibrated Simulation</option>
            </select>
          </div>
        </div>

        {/* Methodological Rigor Banner */}
        <div className="bg-surface-container-lowest border-l-4 border-primary px-4 py-2.5 rounded-r-xl border-y border-r border-slate-200 text-xs flex items-center justify-between gap-3 shadow-2xs">
          <div className="flex items-center gap-2.5">
            <span className="material-symbols-outlined text-primary text-[20px]">info</span>
            <div>
              <span className="font-semibold text-primary">Methodological Rigor Note: </span>
              <span className="text-on-surface-variant">
                Strict segregation enforced between{' '}
                <span className="font-semibold text-emerald-800 bg-emerald-50 px-1 py-0.5 rounded border border-emerald-200">Tier 1: Empirical Ground IoT (In-situ thermistors)</span>,{' '}
                <span className="font-semibold text-blue-800 bg-blue-50 px-1 py-0.5 rounded border border-blue-200">Tier 2: Satellite Surface Radiance (Landsat-9 / Sentinel-2)</span>, and{' '}
                <span className="font-semibold text-slate-800 bg-slate-100 px-1 py-0.5 rounded border border-slate-300">Tier 3: Hydrodynamic Simulation (EPA SWMM)</span>.
              </span>
            </div>
          </div>
          <span className="text-[10px] font-mono text-outline tracking-wider uppercase shrink-0 hidden lg:inline font-semibold">
            ISO/IEC 17025 Compliant
          </span>
        </div>
      </section>

      {/* SECTION 3: BENTO GRID - TELEMETRY AUDIT CARDS (8 Cols) + SPOTLIGHT PANEL (4 Cols) */}
      <section className="grid grid-cols-1 xl:grid-cols-12 gap-5 items-start">
        {/* Left 8 Cols: Detailed Intervention Audit Cards */}
        <div className="xl:col-span-8 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-[20px]">biotech</span>
              <h2 className="text-headline-sm font-headline-sm text-primary font-bold">
                Verified Intervention Cases (Field Audits)
              </h2>
            </div>
            <span className="text-xs font-mono text-outline">Showing {auditCases.length} of 42 Records</span>
          </div>

          {/* Audit Cards List */}
          {auditCases.map((caseItem) => {
            const isSelected = activeDossierCase?.id === caseItem.id;
            return (
              <article
                key={caseItem.id}
                onClick={() => setActiveDossierCase(caseItem)}
                className={`
                  bg-surface-container-lowest rounded-xl p-5 shadow-xs relative overflow-hidden transition-all cursor-pointer
                  ${isSelected ? 'border-2 border-emerald-600/70 shadow-sm' : 'border border-slate-200 hover:border-slate-300'}
                `}
              >
                {/* Active Inspecting Ribbon */}
                {isSelected && (
                  <div className="absolute top-0 right-0 bg-primary text-white font-mono text-[9px] font-bold px-3 py-1 rounded-bl-lg flex items-center gap-1 shadow-2xs">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping"></span>
                    CURRENTLY INSPECTING
                  </div>
                )}

                {/* Card Header */}
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-3 pr-20">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-100 text-slate-800 border">
                        {caseItem.wardId}
                      </span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-rose-50 text-rose-800 border border-rose-200">
                        {caseItem.hazard}
                      </span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-50 text-emerald-800 border border-emerald-300 flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-600"></span>
                        {caseItem.confidenceTier}
                      </span>
                    </div>

                    <h3 className="text-title-md font-title-md text-primary mt-1.5 font-bold">
                      {caseItem.wardName} — {caseItem.title}
                    </h3>
                    <p className="text-xs text-outline mt-0.5 font-mono">
                      {caseItem.measurementWindow}
                    </p>
                  </div>
                </div>

                {/* Telemetry Comparison Metrics */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-4">
                  {caseItem.metrics.map((m, idx) => (
                    <div key={idx} className="bg-surface-bright p-3 rounded-lg border border-slate-200">
                      <div className="flex items-center justify-between text-[10px] font-mono text-outline">
                        <span>{m.title}</span>
                        <span className="text-emerald-800 font-bold bg-emerald-100/60 px-1 rounded">
                          {m.deltaPercent}
                        </span>
                      </div>

                      <div className="flex items-baseline gap-2 mt-1">
                        <span className="text-xs text-rose-700 line-through font-mono font-semibold">
                          {m.baseline}
                        </span>
                        <span className="material-symbols-outlined text-[14px] text-outline">arrow_forward</span>
                        <span className="text-lg font-headline-md font-bold text-primary font-mono tabular-nums">
                          {m.followUp}
                        </span>
                      </div>

                      <div className="text-[10px] font-mono font-semibold text-emerald-800 mt-1 flex items-center justify-between">
                        <span>{m.netDrop}</span>
                        <span className="text-outline font-normal">{m.sensor}</span>
                      </div>

                      {/* Mini Visual Rail */}
                      {m.rail1 && (
                        <div className="w-full bg-slate-200 h-1.5 rounded-full mt-2 overflow-hidden flex">
                          <div className="bg-emerald-600 h-full" style={{ width: m.rail1 }}></div>
                          <div className="bg-rose-400 h-full" style={{ width: m.rail2 }}></div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {/* Evidence Footer */}
                <div className="mt-4 pt-3 border-t border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="p-1 rounded bg-slate-100 text-slate-700">
                      <span className="material-symbols-outlined text-[16px]">hub</span>
                    </span>
                    <span className="text-on-surface">
                      Source: <strong className="font-semibold text-primary">{caseItem.source}</strong>
                      {caseItem.significance && (
                        <span className="ml-2 text-emerald-800 font-mono font-bold bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                          {caseItem.significance}
                        </span>
                      )}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <button 
                      onClick={(e) => { e.stopPropagation(); alert(`Time-Series telemetry graph inspected for ${caseItem.wardId}.`); }}
                      className="px-2.5 py-1 bg-surface-bright border border-slate-300 rounded text-xs font-semibold text-primary hover:bg-slate-100 transition-colors cursor-pointer"
                    >
                      Inspect Time-Series
                    </button>
                    <button 
                      onClick={(e) => { e.stopPropagation(); alert(`Full verification dossier downloaded for ${caseItem.wardId}.`); }}
                      className="px-3 py-1 bg-primary text-white rounded text-xs font-semibold hover:bg-[#1B5742] transition-colors shadow-xs cursor-pointer"
                    >
                      View Full Dossier
                    </button>
                  </div>
                </div>
              </article>
            );
          })}
        </div>

        {/* Right 4 Cols: Spotlight Dossier & Diurnal Temperature Profile Bar Chart */}
        <aside className="xl:col-span-4 flex flex-col gap-4">
          <div className="bg-surface-container-lowest border border-slate-200 rounded-xl p-5 shadow-xs flex flex-col gap-4">
            {/* Header */}
            <div className="flex items-start justify-between pb-3 border-b border-slate-200">
              <div>
                <span className="text-[10px] font-mono font-bold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                  DEEP-DIVE TELEMETRY
                </span>
                <h3 className="text-title-md font-title-md text-primary font-bold mt-1">
                  Selected Spotlight: {activeDossierCase?.wardName || 'Gomtipur'}
                </h3>
                <p className="text-xs font-mono text-outline">Audit Code: AMC-VER-2024-089A</p>
              </div>
              <span className="material-symbols-outlined text-primary text-[24px]">verified_user</span>
            </div>

            {/* Diurnal Temperature Delta Profile Chart */}
            <div className="bg-surface-bright p-3.5 rounded-lg border border-slate-200">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-bold text-on-surface">
                  24-Hour Diurnal Surface Temperature Profile
                </span>
                <span className="text-[10px] font-mono text-outline">Hourly Avg (°C)</span>
              </div>
              <p className="text-[11px] text-on-surface-variant mb-3">
                Comparing Uncoated Baseline vs. Coated Roofs. Maximum delta observed during 12:00 – 15:00 peak solar irradiance.
              </p>

              {/* Bar Chart Component */}
              <div className="flex items-end justify-between h-32 pt-4 px-1 border-b border-slate-300 gap-1.5">
                {DIURNAL_TEMPERATURE_PROFILE.map((item) => (
                  <div
                    key={item.hour}
                    className="flex flex-col items-center flex-1 h-full justify-end group cursor-pointer relative"
                    title={`${item.hour} - Baseline: ${item.baseline}°C, Coated: ${item.coated}°C`}
                  >
                    {item.isPeak && (
                      <span className="absolute -top-3 text-[9px] font-mono font-bold text-emerald-800 bg-emerald-100 px-1 rounded">
                        {item.delta}
                      </span>
                    )}
                    <div className="w-full flex items-end justify-center gap-0.5 h-full">
                      {/* Baseline Bar (Red-Orange) */}
                      <div 
                        className={`w-2.5 rounded-t-xs transition-all ${item.isPeak ? 'bg-rose-500' : 'bg-rose-300'}`}
                        style={{ height: `${item.baselinePct}%` }}
                      />
                      {/* Coated Bar (Emerald) */}
                      <div 
                        className={`w-2.5 rounded-t-xs transition-all ${item.isPeak ? 'bg-emerald-700' : 'bg-emerald-600'}`}
                        style={{ height: `${item.coatedPct}%` }}
                      />
                    </div>
                    <span className={`text-[10px] font-mono mt-1 ${item.isPeak ? 'font-bold text-primary' : 'text-outline group-hover:text-primary'}`}>
                      {item.hour}
                    </span>
                  </div>
                ))}
              </div>

              {/* Chart Legend */}
              <div className="flex items-center justify-between text-[10px] font-mono mt-2 px-1">
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1">
                    <span className="w-2.5 h-2.5 rounded-xs bg-rose-500"></span>
                    <span className="text-outline">Uncoated</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="w-2.5 h-2.5 rounded-xs bg-emerald-700"></span>
                    <span className="text-outline">Coated</span>
                  </div>
                </div>
                <span className="font-bold text-emerald-800">Peak Gap: 13:00 IST</span>
              </div>
            </div>

            {/* Audit Quality & Attribution Notes */}
            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between p-2 rounded bg-slate-50 border border-slate-200">
                <span className="font-mono text-[10px] uppercase text-outline">Thermal Delta</span>
                <span className="font-bold text-emerald-800 font-mono">-11.1°C Net Drop</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-slate-50 border border-slate-200">
                <span className="font-mono text-[10px] uppercase text-outline">P-Value Significance</span>
                <span className="font-bold text-primary font-mono">p &lt; 0.001 (High)</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-slate-50 border border-slate-200">
                <span className="font-mono text-[10px] uppercase text-outline">Verification Sensor</span>
                <span className="font-bold text-on-surface font-mono">In-Situ IoT GT-09</span>
              </div>
            </div>

            <button
              onClick={() => alert("Verification Certificate AMC-VER-2024-089A generated with digital signature.")}
              className="w-full py-2 bg-primary text-white rounded-lg text-xs font-semibold hover:bg-[#1B5742] transition-colors shadow-xs cursor-pointer flex items-center justify-center gap-1.5"
            >
              <span className="material-symbols-outlined text-[16px]">verified</span>
              <span>Generate Verification Certificate</span>
            </button>
          </div>
        </aside>
      </section>
    </div>
  );
}
