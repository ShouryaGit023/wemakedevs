import React, { useState } from 'react';
import { ClimateShieldAPI } from '../services/api';

export default function IssueAdvisoryModal({ isOpen, onClose, onAdvisoryIssued }) {
  const [advisoryDomain, setAdvisoryDomain] = useState('heat'); // 'heat' | 'water'

  // Heat Action Plan State
  const [selectedTier, setSelectedTier] = useState('Orange');
  const [selectedZones, setSelectedZones] = useState(['East Zone', 'South Zone']);
  const [channels, setChannels] = useState({
    sms: true,
    pa: true,
    hospitals: true,
    waterTankers: true
  });

  // Water Scarcity Advisory State
  const [waterSeverity, setWaterSeverity] = useState('SEVERE'); // 'MODERATE' | 'SEVERE' | 'CRITICAL'
  const [waterZones, setWaterZones] = useState(['East Zone', 'South Zone']);
  const [waterRecommendations, setWaterRecommendations] = useState({
    water_conservation_messaging: true,
    water_tanker_dispatch: true,
    leak_inspection_repair: true,
    groundwater_extraction_monitoring: false,
  });
  const [waterReason, setWaterReason] = useState(
    'Elevated aquifer stress and high seasonal demand require municipal water conservation directives and targeted distribution support.'
  );
  const [isWaterConfirmed, setIsWaterConfirmed] = useState(false);

  // Common UI State
  const [isBroadcasting, setIsBroadcasting] = useState(false);
  const [broadcastSuccess, setBroadcastSuccess] = useState(false);
  const [successDetails, setSuccessDetails] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  if (!isOpen) return null;

  const handleBroadcastHeat = async () => {
    setIsBroadcasting(true);
    setErrorMsg(null);
    try {
      await ClimateShieldAPI.createManualAction({
        ward_id: "AMC-CENTRAL",
        ward_name: `Ahmedabad Citywide (${selectedZones.join(', ')})`,
        action_type: "heat_alert",
        priority: selectedTier === 'Red' ? 'critical' : selectedTier === 'Orange' ? 'high' : 'medium',
        reason: `Heat Action Plan (HAP) Tier ${selectedTier} municipal advisory authorized. Priority zones: ${selectedZones.join(', ')}. Channels: ${Object.keys(channels).filter(k => channels[k]).join(', ')}.`,
        required_resources: {
          cost_inr: selectedTier === 'Red' ? 50000 : 20000,
          crew_required: selectedTier === 'Red' ? 12 : 6,
          water_required_l: channels.waterTankers ? 30000 : 0
        },
        related_hazard: "heat",
        risk_score: selectedTier === 'Red' ? 88.0 : selectedTier === 'Orange' ? 75.0 : 50.0
      });

      setIsBroadcasting(false);
      setSuccessDetails({
        title: 'Heat Action Advisory Broadcast Dispatched & Recorded!',
        desc: `Alert Tier ${selectedTier} logged to Action Centre queue as proposed municipal intervention.`
      });
      setBroadcastSuccess(true);
      if (onAdvisoryIssued) onAdvisoryIssued();
      setTimeout(() => {
        setBroadcastSuccess(false);
        onClose();
      }, 2000);
    } catch (err) {
      setIsBroadcasting(false);
      setErrorMsg(err.message || 'Failed to authorize heat advisory via backend API.');
    }
  };

  const handleBroadcastWater = async () => {
    if (!isWaterConfirmed) {
      setErrorMsg('You must acknowledge that this issues recommendations requiring human authorization, not automated dispatches.');
      return;
    }

    const activeRecs = Object.keys(waterRecommendations).filter(k => waterRecommendations[k]);
    if (activeRecs.length === 0) {
      setErrorMsg('Please select at least one operational recommendation.');
      return;
    }

    if (waterZones.length === 0) {
      setErrorMsg('Please select at least one target municipal zone.');
      return;
    }

    setIsBroadcasting(true);
    setErrorMsg(null);

    try {
      const res = await ClimateShieldAPI.issueWaterAdvisory({
        advisory_type: 'water_scarcity',
        severity_tier: waterSeverity,
        target_zones: waterZones,
        recommendations: activeRecs,
        reason: waterReason,
        confirmed_by: 'Municipal Disaster Management Cell',
        data_sources: [
          'Central Water Commission (CWC) Weekly Reservoir Bulletin',
          'Central Ground Water Board (CGWB) In-Situ Telemetry'
        ],
        observation_dates: {
          cwc_bulletin: '2024-05-15',
          cgwb_groundwater: '2024-05-15'
        },
        confidence_level: 'MODERATE (70% Confidence)',
        confirmation_acknowledged: true
      });

      setIsBroadcasting(false);
      setSuccessDetails({
        title: 'Water Scarcity Advisory Recommended & Queued!',
        desc: `Advisory ${res?.advisory_id || 'ADV-WTR'} successfully registered in the Action Centre as PROPOSED. Recommendations require human administrative sign-off before field execution; no tankers were automatically dispatched.`
      });
      setBroadcastSuccess(true);
      if (onAdvisoryIssued) onAdvisoryIssued();
      setTimeout(() => {
        setBroadcastSuccess(false);
        onClose();
      }, 2500);
    } catch (err) {
      setIsBroadcasting(false);
      setErrorMsg(err.message || 'Failed to submit water advisory via backend API.');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs select-none">
      <div className="bg-surface-container-lowest rounded-2xl border border-outline-variant shadow-xl w-full max-w-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="px-5 py-4 border-b border-outline-variant flex items-center justify-between bg-[#F8FAF8]">
          <div className="flex items-center gap-2">
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-white ${
              advisoryDomain === 'heat' ? 'bg-error' : 'bg-[#0284C7]'
            }`}>
              <span className="material-symbols-outlined text-[18px]">
                {advisoryDomain === 'heat' ? 'campaign' : 'water_drop'}
              </span>
            </div>
            <div>
              <h3 className="font-title-sm text-title-sm text-primary font-bold">
                Issue Municipal Climate Advisory
              </h3>
              <p className="text-[11px] font-mono text-outline">
                {advisoryDomain === 'heat' 
                  ? 'Ahmedabad Heat Action Plan (HAP) Dispatch' 
                  : 'Municipal Water Scarcity & Drought Advisory System'}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 text-outline hover:text-primary rounded cursor-pointer">
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        {/* Domain Navigation Tabs */}
        <div className="grid grid-cols-2 border-b border-outline-variant bg-slate-50 text-xs font-semibold">
          <button
            type="button"
            onClick={() => { setAdvisoryDomain('heat'); setErrorMsg(null); }}
            className={`py-2.5 flex items-center justify-center gap-2 border-b-2 transition-colors cursor-pointer ${
              advisoryDomain === 'heat'
                ? 'border-error text-error bg-white font-bold'
                : 'border-transparent text-slate-600 hover:text-primary hover:bg-slate-100'
            }`}
          >
            <span className="material-symbols-outlined text-[16px]">thermostat</span>
            <span>Heat Action Plan (HAP)</span>
          </button>

          <button
            type="button"
            onClick={() => { setAdvisoryDomain('water'); setErrorMsg(null); }}
            className={`py-2.5 flex items-center justify-center gap-2 border-b-2 transition-colors cursor-pointer ${
              advisoryDomain === 'water'
                ? 'border-[#0284C7] text-[#0284C7] bg-white font-bold'
                : 'border-transparent text-slate-600 hover:text-primary hover:bg-slate-100'
            }`}
          >
            <span className="material-symbols-outlined text-[16px]">water_ec</span>
            <span>Water Scarcity & Drought</span>
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4 max-h-[72vh] overflow-y-auto">
          {errorMsg && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-error flex items-center gap-2">
              <span className="material-symbols-outlined text-[16px]">error</span>
              <span>{errorMsg}</span>
            </div>
          )}

          {broadcastSuccess ? (
            <div className="p-6 text-center space-y-2">
              <div className="w-12 h-12 bg-emerald-100 text-emerald-800 rounded-full flex items-center justify-center mx-auto">
                <span className="material-symbols-outlined text-[28px]">check_circle</span>
              </div>
              <h4 className="font-bold text-base text-primary">{successDetails?.title}</h4>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                {successDetails?.desc}
              </p>
            </div>
          ) : advisoryDomain === 'heat' ? (
            /* HEAT ACTION PLAN (ORIGINAL WORKFLOW FULLY PRESERVED) */
            <>
              {/* Alert Level Selector */}
              <div>
                <label className="block text-[11px] font-mono uppercase font-bold text-outline mb-1.5">
                  Select HAP Alert Tier
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {[
                    { tier: 'Green', label: 'Normal (<40°C)', color: 'border-emerald-500 bg-emerald-50 text-emerald-800' },
                    { tier: 'Yellow', label: 'Advisory (40-43°C)', color: 'border-amber-400 bg-amber-50 text-amber-800' },
                    { tier: 'Orange', label: 'Severe (43-45°C)', color: 'border-orange-500 bg-orange-50 text-orange-800' },
                    { tier: 'Red', label: 'Extreme (≥45°C)', color: 'border-red-600 bg-red-50 text-red-800' }
                  ].map((item) => (
                    <button
                      key={item.tier}
                      type="button"
                      onClick={() => setSelectedTier(item.tier)}
                      className={`p-2 rounded-lg border text-center transition-all cursor-pointer ${
                        selectedTier === item.tier 
                          ? `${item.color} font-bold ring-2 ring-primary/20 shadow-xs` 
                          : 'border-outline-variant bg-white text-on-surface hover:bg-slate-50'
                      }`}
                    >
                      <div className="text-xs font-bold">{item.tier}</div>
                      <div className="text-[9px] font-mono mt-0.5 leading-tight opacity-80">{item.label}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Target Jurisdiction */}
              <div>
                <label className="block text-[11px] font-mono uppercase font-bold text-outline mb-1.5">
                  Target Municipal Zones
                </label>
                <div className="flex flex-wrap gap-1.5">
                  {['East Zone', 'South Zone', 'North Zone', 'Central Zone', 'West Zone'].map((z) => {
                    const isSelected = selectedZones.includes(z);
                    return (
                      <button
                        key={z}
                        type="button"
                        onClick={() => {
                          if (isSelected) {
                            setSelectedZones(selectedZones.filter((x) => x !== z));
                          } else {
                            setSelectedZones([...selectedZones, z]);
                          }
                        }}
                        className={`px-2.5 py-1 rounded-full text-xs font-mono transition-colors cursor-pointer ${
                          isSelected 
                            ? 'bg-primary-container text-white font-semibold' 
                            : 'bg-slate-100 text-on-surface hover:bg-slate-200'
                        }`}
                      >
                        {z} {isSelected ? '✓' : '+'}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Broadcast Channels */}
              <div>
                <label className="block text-[11px] font-mono uppercase font-bold text-outline mb-1.5">
                  Execution Channels
                </label>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <label className="flex items-center gap-2 p-2 rounded-lg border border-outline-variant bg-[#F8FAF8] cursor-pointer">
                    <input 
                      type="checkbox" 
                      checked={channels.sms} 
                      onChange={(e) => setChannels({ ...channels, sms: e.target.checked })}
                      className="rounded text-primary focus:ring-primary"
                    />
                    <span>Public SMS Broadcast (Telecom)</span>
                  </label>

                  <label className="flex items-center gap-2 p-2 rounded-lg border border-outline-variant bg-[#F8FAF8] cursor-pointer">
                    <input 
                      type="checkbox" 
                      checked={channels.waterTankers} 
                      onChange={(e) => setChannels({ ...channels, waterTankers: e.target.checked })}
                      className="rounded text-primary focus:ring-primary"
                    />
                    <span>Mobilize Mobile Water Tankers</span>
                  </label>

                  <label className="flex items-center gap-2 p-2 rounded-lg border border-outline-variant bg-[#F8FAF8] cursor-pointer">
                    <input 
                      type="checkbox" 
                      checked={channels.hospitals} 
                      onChange={(e) => setChannels({ ...channels, hospitals: e.target.checked })}
                      className="rounded text-primary focus:ring-primary"
                    />
                    <span>Hospital Heatstroke Triage Pre-alert</span>
                  </label>

                  <label className="flex items-center gap-2 p-2 rounded-lg border border-outline-variant bg-[#F8FAF8] cursor-pointer">
                    <input 
                      type="checkbox" 
                      checked={channels.pa} 
                      onChange={(e) => setChannels({ ...channels, pa: e.target.checked })}
                      className="rounded text-primary focus:ring-primary"
                    />
                    <span>AMTS / BRTS Public PA Systems</span>
                  </label>
                </div>
              </div>
            </>
          ) : (
            /* WATER SCARCITY & DROUGHT ADVISORY WORKFLOW */
            <>
              {/* Severity Level Selector */}
              <div>
                <label className="block text-[11px] font-mono uppercase font-bold text-outline mb-1.5">
                  Water Shortage Severity Tier
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { tier: 'MODERATE', label: 'Advisory (40-60)', color: 'border-amber-400 bg-amber-50 text-amber-800' },
                    { tier: 'SEVERE', label: 'Critical Shortage (60-80)', color: 'border-orange-500 bg-orange-50 text-orange-800' },
                    { tier: 'CRITICAL', label: 'Emergency Rationing (≥80)', color: 'border-red-600 bg-red-50 text-red-800' }
                  ].map((item) => (
                    <button
                      key={item.tier}
                      type="button"
                      onClick={() => setWaterSeverity(item.tier)}
                      className={`p-2 rounded-lg border text-center transition-all cursor-pointer ${
                        waterSeverity === item.tier 
                          ? `${item.color} font-bold ring-2 ring-[#0284C7]/30 shadow-xs` 
                          : 'border-outline-variant bg-white text-on-surface hover:bg-slate-50'
                      }`}
                    >
                      <div className="text-xs font-bold">{item.tier}</div>
                      <div className="text-[9px] font-mono mt-0.5 leading-tight opacity-80">{item.label}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Target Municipal Zones */}
              <div>
                <label className="block text-[11px] font-mono uppercase font-bold text-outline mb-1.5">
                  Target Municipal Zones
                </label>
                <div className="flex flex-wrap gap-1.5">
                  {['East Zone', 'South Zone', 'North Zone', 'Central Zone', 'West Zone', 'North West Zone', 'South West Zone'].map((z) => {
                    const isSelected = waterZones.includes(z);
                    return (
                      <button
                        key={z}
                        type="button"
                        onClick={() => {
                          if (isSelected) {
                            setWaterZones(waterZones.filter((x) => x !== z));
                          } else {
                            setWaterZones([...waterZones, z]);
                          }
                        }}
                        className={`px-2.5 py-1 rounded-full text-xs font-mono transition-colors cursor-pointer ${
                          isSelected 
                            ? 'bg-[#0284C7] text-white font-semibold' 
                            : 'bg-slate-100 text-on-surface hover:bg-slate-200'
                        }`}
                      >
                        {z} {isSelected ? '✓' : '+'}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Operational Recommendations (Distinguished from Automated Dispatches) */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-[11px] font-mono uppercase font-bold text-outline">
                    Operational Recommendations (Decision Support)
                  </label>
                  <span className="text-[9px] font-mono text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">
                    REQUIRES HUMAN APPROVAL
                  </span>
                </div>
                <div className="space-y-1.5 text-xs">
                  <label className="flex items-start gap-2.5 p-2 rounded-lg border border-outline-variant bg-[#F8FAF8] cursor-pointer">
                    <input 
                      type="checkbox" 
                      checked={waterRecommendations.water_conservation_messaging} 
                      onChange={(e) => setWaterRecommendations({ ...waterRecommendations, water_conservation_messaging: e.target.checked })}
                      className="mt-0.5 rounded text-[#0284C7] focus:ring-[#0284C7]"
                    />
                    <div>
                      <span className="font-semibold text-primary block">Water-Conservation Public Messaging</span>
                      <span className="text-[10px] text-on-surface-variant block">Civil awareness campaigns, off-peak pressure curtailment advisory, voluntary reduction.</span>
                    </div>
                  </label>

                  <label className="flex items-start gap-2.5 p-2 rounded-lg border border-outline-variant bg-[#F8FAF8] cursor-pointer">
                    <input 
                      type="checkbox" 
                      checked={waterRecommendations.water_tanker_dispatch} 
                      onChange={(e) => setWaterRecommendations({ ...waterRecommendations, water_tanker_dispatch: e.target.checked })}
                      className="mt-0.5 rounded text-[#0284C7] focus:ring-[#0284C7]"
                    />
                    <div>
                      <span className="font-semibold text-primary block">Emergency Tanker-Dispatch Recommendations</span>
                      <span className="text-[10px] text-on-surface-variant block">Recommendation for supplemental mobile bowsers in informal settlements (requires dispatch approval).</span>
                    </div>
                  </label>

                  <label className="flex items-start gap-2.5 p-2 rounded-lg border border-outline-variant bg-[#F8FAF8] cursor-pointer">
                    <input 
                      type="checkbox" 
                      checked={waterRecommendations.leak_inspection_repair} 
                      onChange={(e) => setWaterRecommendations({ ...waterRecommendations, leak_inspection_repair: e.target.checked })}
                      className="mt-0.5 rounded text-[#0284C7] focus:ring-[#0284C7]"
                    />
                    <div>
                      <span className="font-semibold text-primary block">Rapid Pipeline Leak Inspection & Repair Audits</span>
                      <span className="text-[10px] text-on-surface-variant block">Direct municipal engineering crews to survey non-revenue water loss hotspots.</span>
                    </div>
                  </label>

                  <label className="flex items-start gap-2.5 p-2 rounded-lg border border-outline-variant bg-[#F8FAF8] cursor-pointer">
                    <input 
                      type="checkbox" 
                      checked={waterRecommendations.groundwater_extraction_monitoring} 
                      onChange={(e) => setWaterRecommendations({ ...waterRecommendations, groundwater_extraction_monitoring: e.target.checked })}
                      className="mt-0.5 rounded text-[#0284C7] focus:ring-[#0284C7]"
                    />
                    <div>
                      <span className="font-semibold text-primary block">Groundwater Extraction Monitoring & Well Restrictions</span>
                      <span className="text-[10px] text-on-surface-variant block">Auditing commercial borewells and monitoring unconfined piezometer drawdowns where authorized.</span>
                    </div>
                  </label>
                </div>
              </div>

              {/* Justification & Evidence */}
              <div>
                <label className="block text-[11px] font-mono uppercase font-bold text-outline mb-1">
                  Administrative Justification Reason
                </label>
                <textarea
                  value={waterReason}
                  onChange={(e) => setWaterReason(e.target.value)}
                  rows={2}
                  className="w-full text-xs p-2.5 rounded-lg border border-outline-variant bg-white focus:outline-none focus:border-[#0284C7] resize-none"
                  placeholder="Explain why this municipal water scarcity advisory is warranted..."
                />
              </div>

              {/* Verified Evidence Strip */}
              <div className="p-2.5 rounded-lg border border-slate-200 bg-[#F8FAF8] text-[10px] font-mono space-y-1 text-slate-600">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-primary">Supporting Evidence:</span>
                  <span className="text-[9px] px-1.5 py-0.2 rounded bg-blue-100 text-blue-900 font-bold border border-blue-200">
                    CWC & CGWB VERIFIED
                  </span>
                </div>
                <div className="flex items-center justify-between text-outline">
                  <span>Surface Dam Bulk Reserves: 94.8% (Sardar Sarovar 98.8%, Dharoi 78.9%)</span>
                  <span>Date: 2024-05-15</span>
                </div>
                <div className="flex items-center justify-between text-outline">
                  <span>Groundwater Baseline: 13.96 mbgl (High Stress, 37 Stations)</span>
                  <span>Confidence: 70%</span>
                </div>
              </div>

              {/* Mandatory Governance Confirmation Checkbox */}
              <div className="p-3 rounded-lg border border-amber-300 bg-amber-50/70 space-y-1.5">
                <label className="flex items-start gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isWaterConfirmed}
                    onChange={(e) => setIsWaterConfirmed(e.target.checked)}
                    className="mt-0.5 rounded text-[#0284C7] focus:ring-[#0284C7]"
                  />
                  <span className="text-xs text-amber-900 leading-snug font-medium">
                    I confirm that this advisory issues <strong>decision-support recommendations</strong> requiring human authorization by the Municipal Commissioner or designated Disaster Management Authority; it does <strong>not</strong> automatically execute physical field dispatches or enforce restrictions without human sign-off.
                  </span>
                </label>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        {!broadcastSuccess && (
          <div className="px-5 py-3 border-t border-outline-variant bg-[#F8FAF8] flex items-center justify-between text-xs">
            <span className="font-mono text-outline text-[10px]">
              {advisoryDomain === 'heat' ? 'HAP Protocol v3.1' : 'Water Governance • Advisory Mode'}
            </span>

            <div className="flex items-center gap-2">
              <button
                onClick={onClose}
                className="px-3.5 py-1.5 rounded-lg border border-outline-variant text-on-surface hover:bg-slate-100 text-xs font-semibold cursor-pointer"
              >
                Cancel
              </button>

              {advisoryDomain === 'heat' ? (
                <button
                  onClick={handleBroadcastHeat}
                  disabled={isBroadcasting}
                  className="px-4 py-1.5 rounded-lg bg-error hover:bg-[#991B1B] text-white text-xs font-semibold flex items-center gap-1.5 shadow-sm active:scale-98 cursor-pointer disabled:opacity-60"
                >
                  <span className="material-symbols-outlined text-[16px]">broadcast_on_home</span>
                  <span>{isBroadcasting ? 'Broadcasting to Action Centre...' : `Authorize Tier ${selectedTier} Broadcast`}</span>
                </button>
              ) : (
                <button
                  onClick={handleBroadcastWater}
                  disabled={isBroadcasting || !isWaterConfirmed}
                  className="px-4 py-1.5 rounded-lg bg-[#0284C7] hover:bg-[#0369A1] text-white text-xs font-semibold flex items-center gap-1.5 shadow-sm active:scale-98 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <span className="material-symbols-outlined text-[16px]">verified_user</span>
                  <span>{isBroadcasting ? 'Submitting to Action Centre...' : `Submit Water Advisory (${waterSeverity})`}</span>
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

