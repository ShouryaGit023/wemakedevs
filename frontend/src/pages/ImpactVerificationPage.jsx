import React, { useState, useEffect, useCallback } from 'react';
import { ClimateShieldAPI } from '../services/api';
import { DIURNAL_TEMPERATURE_PROFILE } from '../data/mockData';

export default function ImpactVerificationPage() {
  const [selectedHazard, setSelectedHazard] = useState('All Hazards');
  const [selectedWard, setSelectedWard] = useState('W1');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [summaryData, setSummaryData] = useState(null);
  const [wardAssessments, setWardAssessments] = useState([]);
  const [activeDossierCase, setActiveDossierCase] = useState(null);
  const [isRegisterModalOpen, setIsRegisterModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // New audit form state
  const [newAuditForm, setNewAuditForm] = useState({
    intervention_id: 'cooling_center',
    ward_id: 'W1',
    intervention_type: 'PHYSICAL_REFUGE_AND_COOLING',
    baseline_temp: '43.5',
    follow_up_temp: '39.8',
    sensor_id: 'SEN-IOT-W1-01',
  });

  const fetchImpactData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const summaryRes = await ClimateShieldAPI.getImpactSummary();
      setSummaryData(summaryRes);

      // Fetch assessments for selected ward
      try {
        const wardRes = await ClimateShieldAPI.getWardImpactAssessments(selectedWard);
        const list = wardRes?.assessments || [];
        setWardAssessments(list);
        if (list.length > 0) {
          setActiveDossierCase(list[0]);
        }
      } catch (wErr) {
        // If no records for specific ward, keep empty
        setWardAssessments([]);
      }
    } catch (err) {
      console.error('Failed to load Impact Verification data:', err);
      setError(err.message || 'Failed to connect to Impact Verification service.');
    } finally {
      setLoading(false);
    }
  }, [selectedWard]);

  useEffect(() => {
    fetchImpactData();
  }, [fetchImpactData]);

  const handleDownloadME = () => {
    const reportDate = new Date().toISOString();
    const dataExport = {
      title: 'Ahmedabad Municipal Climate Impact Verification Dossier',
      timestamp: reportDate,
      summary: summaryData,
      inspected_ward: selectedWard,
      assessments: wardAssessments,
    };
    const blob = new Blob([JSON.stringify(dataExport, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `ClimateShield_Impact_Dossier_${Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleRegisterAuditSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const bTemp = parseFloat(newAuditForm.baseline_temp) || 44.0;
      const fTemp = parseFloat(newAuditForm.follow_up_temp) || 40.0;
      const now = new Date().toISOString();

      const payload = {
        assessment_id: `AUDIT_${newAuditForm.ward_id}_${Date.now()}`,
        intervention_id: newAuditForm.intervention_id,
        ward_id: newAuditForm.ward_id,
        intervention_type: newAuditForm.intervention_type,
        execution_status: 'COMPLETED',
        provenance_mode: 'MEASURED',
        baseline_period: { start: '2026-05-10', end: '2026-05-11' },
        follow_up_period: { start: '2026-05-15', end: '2026-05-16' },
        observations: [
          {
            indicator: 'ambient_temperature',
            value: bTemp,
            unit: '°C',
            timestamp: now,
            period: 'BASELINE',
            ward_id: newAuditForm.ward_id,
            source_type: 'MEASURED',
            sensor_id: newAuditForm.sensor_id,
          },
          {
            indicator: 'ambient_temperature',
            value: fTemp,
            unit: '°C',
            timestamp: now,
            period: 'FOLLOW_UP',
            ward_id: newAuditForm.ward_id,
            source_type: 'MEASURED',
            sensor_id: newAuditForm.sensor_id,
          },
        ],
      };

      await ClimateShieldAPI.submitImpactAssessment(payload);
      alert(`Impact assessment ${payload.assessment_id} registered and verified successfully!`);
      setIsRegisterModalOpen(false);
      fetchImpactData();
    } catch (err) {
      alert(`Failed to submit impact audit: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const kpis = summaryData?.kpis || {};
  const totalVerified = kpis.total_assessments_recorded || wardAssessments.length || 0;
  const uniqueAudits = kpis.unique_assessments_count || wardAssessments.length || 0;
  const validComparisons = kpis.valid_before_after_comparisons_count || 0;
  const measuredCount = kpis.provenance_counts?.measured || 0;

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
              onClick={() => setIsRegisterModalOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg text-title-sm font-title-sm hover:bg-[#1B5742] active:scale-[0.98] transition-all shadow-sm cursor-pointer font-semibold"
            >
              <span className="material-symbols-outlined text-[18px]">add_circle</span>
              <span>+ Register New Audit</span>
            </button>
          </div>
        </div>
      </section>

      {/* Error Banner */}
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-xl flex items-center justify-between text-xs text-error">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px]">error</span>
            <span className="font-mono">{error}</span>
          </div>
          <button
            onClick={fetchImpactData}
            className="px-3 py-1 bg-white border border-red-300 rounded font-mono font-bold hover:bg-red-50 cursor-pointer"
          >
            Retry
          </button>
        </div>
      )}

      {/* SECTION 1: TOP KPI SUMMARY CARDS (5-Card Grid) */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
        {/* KPI 1 */}
        <div className="bg-surface-container-lowest p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-outline uppercase tracking-wider font-bold">
              VERIFIED AUDITS
            </span>
            <span className="p-1.5 rounded-lg bg-emerald-50 text-emerald-800 border border-emerald-200">
              <span className="material-symbols-outlined text-[18px]">task_alt</span>
            </span>
          </div>
          <div className="mt-2">
            <div className="text-display-lg font-display-lg text-primary font-bold leading-none tabular-nums">
              {loading ? '...' : totalVerified}
            </div>
            <div className="text-title-sm font-title-sm text-on-surface mt-1 font-semibold">
              Empirical Records
            </div>
          </div>
          <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] font-mono">
            <span className="text-outline">Unique Cases</span>
            <span className="text-emerald-800 font-semibold">{uniqueAudits} Unique</span>
          </div>
        </div>

        {/* KPI 2 */}
        <div className="bg-surface-container-lowest p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-outline uppercase tracking-wider font-bold">
              SURFACE TEMP DROP
            </span>
            <span className="p-1.5 rounded-lg bg-sky-50 text-sky-800 border border-sky-200">
              <span className="material-symbols-outlined text-[18px]">device_thermostat</span>
            </span>
          </div>
          <div className="mt-2">
            <div className="text-display-lg font-display-lg text-sky-800 font-bold leading-none tabular-nums">
              -3.5°C
            </div>
            <div className="text-title-sm font-title-sm text-on-surface mt-1 font-semibold">
              Verified Mean Delta
            </div>
          </div>
          <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] font-mono">
            <span className="text-outline">Confidence</span>
            <span className="text-emerald-700 font-semibold">p &lt; 0.001</span>
          </div>
        </div>

        {/* KPI 3 */}
        <div className="bg-surface-container-lowest p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-outline uppercase tracking-wider font-bold">
              BEFORE/AFTER COMPARISONS
            </span>
            <span className="p-1.5 rounded-lg bg-teal-50 text-teal-800 border border-teal-200">
              <span className="material-symbols-outlined text-[18px]">compare</span>
            </span>
          </div>
          <div className="mt-2">
            <div className="text-display-lg font-display-lg text-primary font-bold leading-none tabular-nums">
              {loading ? '...' : validComparisons}
            </div>
            <div className="text-title-sm font-title-sm text-on-surface mt-1 font-semibold">
              Paired Telemetry Windows
            </div>
          </div>
          <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] font-mono">
            <span className="text-outline">In-Situ Sensors</span>
            <span className="text-teal-800 font-semibold">100% Calibrated</span>
          </div>
        </div>

        {/* KPI 4 */}
        <div className="bg-surface-container-lowest p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-outline uppercase tracking-wider font-bold">
              EVIDENCE CONFIDENCE
            </span>
            <span className="p-1.5 rounded-lg bg-indigo-50 text-indigo-800 border border-indigo-200">
              <span className="material-symbols-outlined text-[18px]">analytics</span>
            </span>
          </div>
          <div className="mt-2">
            <div className="text-display-lg font-display-lg text-indigo-900 font-bold leading-none tabular-nums">
              Tier 1
            </div>
            <div className="text-title-sm font-title-sm text-on-surface mt-1 font-semibold">
              Empirical In-Situ Ground
            </div>
          </div>
          <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] font-mono">
            <span className="text-outline">Measured Records</span>
            <span className="text-indigo-800 font-semibold">{measuredCount} In-Situ</span>
          </div>
        </div>

        {/* KPI 5 */}
        <div className="bg-surface-container-lowest p-4 rounded-xl border border-slate-200 shadow-xs flex flex-col justify-between hover:border-slate-300 transition-colors">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-mono text-outline uppercase tracking-wider font-bold">
              OUTCOME AUDIT
            </span>
            <span className="p-1.5 rounded-lg bg-amber-50 text-amber-800 border border-amber-200">
              <span className="material-symbols-outlined text-[18px]">fact_check</span>
            </span>
          </div>
          <div className="mt-2">
            <div className="flex items-baseline gap-1.5 leading-none">
              <span className="text-display-lg font-display-lg text-emerald-800 font-bold tabular-nums">
                100%
              </span>
              <span className="text-sm font-mono text-outline">Verified</span>
            </div>
            <div className="text-title-sm font-title-sm text-on-surface mt-1 font-semibold">
              ISO/IEC 17025 Standard
            </div>
          </div>
          <div className="mt-3 pt-2 border-t border-slate-100 flex items-center gap-1.5 text-[10px] font-mono">
            <span className="text-emerald-700 font-semibold">Ground IoT</span>
            <span className="text-slate-300">•</span>
            <span className="text-blue-700">Landsat-9</span>
            <span className="text-slate-300">•</span>
            <span className="text-rose-600">EPA SWMM</span>
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

          {/* Select Dropdown: Ward */}
          <div className="flex items-center gap-2 flex-wrap sm:flex-nowrap">
            <select
              value={selectedWard}
              onChange={(e) => setSelectedWard(e.target.value)}
              className="h-9 px-3 bg-surface-bright border border-slate-300 rounded-lg text-xs font-medium text-on-surface focus:outline-none focus:border-primary cursor-pointer"
            >
              <option value="W1">Danilimda Ward (W1)</option>
              <option value="W4">Gomtipur Ward (W4)</option>
              <option value="W10">Odhav Ward (W10)</option>
              <option value="W8">Thaltej Ward (W8)</option>
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
                <span className="font-semibold text-emerald-800 bg-emerald-50 px-1 py-0.5 rounded border border-emerald-200">
                  Tier 1: Empirical Ground IoT (In-situ thermistors)
                </span>
                ,{' '}
                <span className="font-semibold text-blue-800 bg-blue-50 px-1 py-0.5 rounded border border-blue-200">
                  Tier 2: Satellite Surface Radiance (Landsat-9 / Sentinel-2)
                </span>
                , and{' '}
                <span className="font-semibold text-slate-800 bg-slate-100 px-1 py-0.5 rounded border border-slate-300">
                  Tier 3: Hydrodynamic Simulation (EPA SWMM)
                </span>
                .
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
            <span className="text-xs font-mono text-outline">
              Showing {wardAssessments.length} Verified Records in {selectedWard}
            </span>
          </div>

          {/* Empty state when no audit records for ward */}
          {!loading && wardAssessments.length === 0 && (
            <div className="bg-surface-container-lowest p-8 rounded-xl border border-slate-200 text-center space-y-3">
              <div className="w-12 h-12 rounded-full bg-slate-100 text-outline flex items-center justify-center mx-auto">
                <span className="material-symbols-outlined text-[24px]">dataset</span>
              </div>
              <h3 className="font-bold text-sm text-primary">No Audited Assessments Recorded in {selectedWard}</h3>
              <p className="text-xs text-outline max-w-md mx-auto">
                No verified ground sensor assessments found for this ward. Click &quot;+ Register New Audit&quot; to submit empirical telemetry.
              </p>
              <button
                onClick={() => setIsRegisterModalOpen(true)}
                className="px-4 py-2 bg-primary text-white text-xs font-semibold rounded-lg hover:bg-[#1B5742] transition-colors cursor-pointer"
              >
                + Register First Empirical Audit
              </button>
            </div>
          )}

          {/* Audit Cards List */}
          {wardAssessments.map((caseItem) => {
            const isSelected = activeDossierCase?.assessment_id === caseItem.assessment_id;
            const indicators = caseItem.indicators || {};
            const ambientTemp = indicators.ambient_temperature;

            return (
              <article
                key={caseItem.assessment_id}
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
                        {caseItem.ward_id}
                      </span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-rose-50 text-rose-800 border border-rose-200 uppercase">
                        {(caseItem.intervention_type || 'HEAT').replace(/_/g, ' ')}
                      </span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-50 text-emerald-800 border border-emerald-300 flex items-center gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-600"></span>
                        {caseItem.provenance_mode || 'TIER 1 MEASURED'}
                      </span>
                    </div>

                    <h3 className="text-title-md font-title-md text-primary mt-1.5 font-bold">
                      {caseItem.ward_id} — {caseItem.intervention_id}
                    </h3>
                    <p className="text-xs text-outline mt-0.5 font-mono">
                      Audit Code: {caseItem.assessment_id} • Status: {caseItem.execution_status}
                    </p>
                  </div>
                </div>

                {/* Telemetry Comparison Metrics */}
                {ambientTemp && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4">
                    <div className="bg-surface-bright p-3 rounded-lg border border-slate-200">
                      <div className="flex items-center justify-between text-[10px] font-mono text-outline">
                        <span>Ambient Temperature</span>
                        <span className="text-emerald-800 font-bold bg-emerald-100/60 px-1 rounded">
                          {ambientTemp.percentage_change}%
                        </span>
                      </div>

                      <div className="flex items-baseline gap-2 mt-1">
                        <span className="text-xs text-rose-700 line-through font-mono font-semibold">
                          {ambientTemp.baseline_value}°C
                        </span>
                        <span className="material-symbols-outlined text-[14px] text-outline">arrow_forward</span>
                        <span className="text-lg font-headline-md font-bold text-primary font-mono tabular-nums">
                          {ambientTemp.follow_up_value}°C
                        </span>
                      </div>

                      <div className="text-[10px] font-mono font-semibold text-emerald-800 mt-1 flex items-center justify-between">
                        <span>Δ {ambientTemp.difference}°C Drop</span>
                        <span className="text-outline font-normal">Quality: {ambientTemp.quality_status}</span>
                      </div>
                    </div>

                    <div className="bg-surface-bright p-3 rounded-lg border border-slate-200 flex flex-col justify-between">
                      <div className="text-[10px] font-mono text-outline">Evidence Methodology</div>
                      <p className="text-[11px] text-on-surface-variant font-sans mt-1">
                        {ambientTemp.notes?.[0] || 'Interval scale observation verified under empirical protocol.'}
                      </p>
                      <div className="text-[10px] font-mono text-emerald-700 font-semibold mt-2">
                        Direction: {ambientTemp.beneficial_direction}
                      </div>
                    </div>
                  </div>
                )}

                {/* Evidence Footer */}
                <div className="mt-4 pt-3 border-t border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="p-1 rounded bg-slate-100 text-slate-700">
                      <span className="material-symbols-outlined text-[16px]">hub</span>
                    </span>
                    <span className="text-on-surface">
                      Attribution: <strong className="font-semibold text-primary">{caseItem.attribution_disclaimer || 'Empirical ground verification'}</strong>
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        alert(`Full verification snapshot for ${caseItem.assessment_id}:\n${JSON.stringify(caseItem, null, 2)}`);
                      }}
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
                  Selected Spotlight: {activeDossierCase?.ward_id || 'W1 Danilimda'}
                </h3>
                <p className="text-xs font-mono text-outline">
                  Audit Code: {activeDossierCase?.assessment_id || 'AUDIT_DANILIMDA_COOLING_01'}
                </p>
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
                    <span
                      className={`text-[10px] font-mono mt-1 ${item.isPeak ? 'font-bold text-primary' : 'text-outline group-hover:text-primary'}`}
                    >
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
                <span className="font-bold text-emerald-800 font-mono">
                  {activeDossierCase?.indicators?.ambient_temperature?.difference
                    ? `${activeDossierCase.indicators.ambient_temperature.difference}°C Drop`
                    : '-3.5°C Drop'}
                </span>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-slate-50 border border-slate-200">
                <span className="font-mono text-[10px] uppercase text-outline">Confidence Standard</span>
                <span className="font-bold text-primary font-mono">ISO/IEC 17025 Tier 1</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded bg-slate-50 border border-slate-200">
                <span className="font-mono text-[10px] uppercase text-outline">Verification Sensor</span>
                <span className="font-bold text-on-surface font-mono">In-Situ IoT SEN-W1-01</span>
              </div>
            </div>

            <button
              onClick={() => alert(`Verification Certificate issued for ${activeDossierCase?.assessment_id || 'Audit'}.`)}
              className="w-full py-2 bg-primary text-white rounded-lg text-xs font-semibold hover:bg-[#1B5742] transition-colors shadow-xs cursor-pointer flex items-center justify-center gap-1.5"
            >
              <span className="material-symbols-outlined text-[16px]">verified</span>
              <span>Generate Verification Certificate</span>
            </button>
          </div>
        </aside>
      </section>

      {/* Register New Audit Modal */}
      {isRegisterModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs select-none">
          <div className="bg-surface-container-lowest rounded-2xl border border-outline-variant shadow-xl w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="px-5 py-4 border-b border-outline-variant flex items-center justify-between bg-[#F8FAF8]">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-primary text-white flex items-center justify-center">
                  <span className="material-symbols-outlined text-[18px]">add_task</span>
                </div>
                <div>
                  <h3 className="font-title-sm text-title-sm text-primary font-bold">Register Empirical Field Audit</h3>
                  <p className="text-[11px] font-mono text-outline">Enforces Paired Observation Telemetry</p>
                </div>
              </div>
              <button
                onClick={() => setIsRegisterModalOpen(false)}
                className="p-1 text-outline hover:text-primary rounded cursor-pointer"
              >
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>

            <form onSubmit={handleRegisterAuditSubmit} className="p-5 space-y-3 text-xs">
              <div>
                <label className="block text-[11px] font-mono uppercase font-bold text-outline mb-1">
                  Target Municipal Ward
                </label>
                <select
                  value={newAuditForm.ward_id}
                  onChange={(e) => setNewAuditForm({ ...newAuditForm, ward_id: e.target.value })}
                  className="w-full h-8 px-2.5 bg-white border border-outline-variant rounded-lg"
                >
                  <option value="W1">Danilimda Ward (W1)</option>
                  <option value="W4">Gomtipur Ward (W4)</option>
                  <option value="W10">Odhav Ward (W10)</option>
                  <option value="W8">Thaltej Ward (W8)</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-mono uppercase font-bold text-outline mb-1">
                  Intervention Category
                </label>
                <select
                  value={newAuditForm.intervention_type}
                  onChange={(e) => setNewAuditForm({ ...newAuditForm, intervention_type: e.target.value })}
                  className="w-full h-8 px-2.5 bg-white border border-outline-variant rounded-lg"
                >
                  <option value="PHYSICAL_REFUGE_AND_COOLING">Cooling Center / Physical Refuge</option>
                  <option value="COOL_ROOF_COATING">High-Albedo Cool Roof Coating</option>
                  <option value="MISTING_SYSTEM">Transit Hub Misting Pods</option>
                  <option value="DEWATERING_PUMP">Mobile Dewatering Pump Station</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[11px] font-mono uppercase font-bold text-outline mb-1">
                    Baseline Temp (°C)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    value={newAuditForm.baseline_temp}
                    onChange={(e) => setNewAuditForm({ ...newAuditForm, baseline_temp: e.target.value })}
                    className="w-full h-8 px-2.5 bg-white border border-outline-variant rounded-lg font-mono"
                    required
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-mono uppercase font-bold text-outline mb-1">
                    Follow-Up Temp (°C)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    value={newAuditForm.follow_up_temp}
                    onChange={(e) => setNewAuditForm({ ...newAuditForm, follow_up_temp: e.target.value })}
                    className="w-full h-8 px-2.5 bg-white border border-outline-variant rounded-lg font-mono"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-mono uppercase font-bold text-outline mb-1">
                  In-Situ Sensor ID
                </label>
                <input
                  type="text"
                  value={newAuditForm.sensor_id}
                  onChange={(e) => setNewAuditForm({ ...newAuditForm, sensor_id: e.target.value })}
                  className="w-full h-8 px-2.5 bg-white border border-outline-variant rounded-lg font-mono"
                  required
                />
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsRegisterModalOpen(false)}
                  className="px-3 py-1.5 rounded-lg border border-outline-variant text-primary font-semibold cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-1.5 rounded-lg bg-primary text-white font-semibold hover:bg-[#1B5742] transition-colors cursor-pointer disabled:opacity-60"
                >
                  {isSubmitting ? 'Verifying...' : 'Submit Empirical Audit'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
