import React, { useState, useEffect, useCallback } from 'react';
import { ClimateShieldAPI } from '../services/api';

export default function InterventionDetailModal({ isOpen, action, onClose, onActionUpdated, initialTab = 'details' }) {
  const [detailData, setDetailData] = useState(action || null);
  const [isLoadingFresh, setIsLoadingFresh] = useState(false);
  const [fetchError, setFetchError] = useState(null);

  // Tabs: 'details' | 'verification' | 'audit'
  const [activeTab, setActiveTab] = useState(initialTab);
  
  // Verification State
  const [verificationReport, setVerificationReport] = useState(null);
  const [isVerifying, setIsVerifying] = useState(false);
  const [verifyError, setVerifyError] = useState(null);
  const [verifySuccessToast, setVerifySuccessToast] = useState(false);

  // Audit Trail State
  const [auditEvents, setAuditEvents] = useState([]);
  const [isLoadingAudit, setIsLoadingAudit] = useState(false);

  // Decision Workflow State
  const [decisionMode, setDecisionMode] = useState(null); // null | 'reject' | 'block' | 'changes_requested' | 'unblock'
  const [decisionReason, setDecisionReason] = useState('');
  const [decisionAuthority, setDecisionAuthority] = useState('Municipal Incident Commander');
  const [isSubmittingDecision, setIsSubmittingDecision] = useState(false);
  const [decisionError, setDecisionError] = useState(null);
  const [decisionSuccessMsg, setDecisionSuccessMsg] = useState(null);

  const fetchAuditTrail = useCallback(async (actionId) => {
    if (!actionId) return;
    setIsLoadingAudit(true);
    try {
      const res = await ClimateShieldAPI.getActionAuditTrail(actionId);
      if (res?.audit_trail) {
        setAuditEvents(res.audit_trail);
      }
    } catch (err) {
      console.warn('Could not load action audit events:', err);
    } finally {
      setIsLoadingAudit(false);
    }
  }, []);

  useEffect(() => {
    if (!isOpen || !action?.action_id) {
      setDetailData(action || null);
      setVerificationReport(action?.latest_verification || null);
      setAuditEvents([]);
      setFetchError(null);
      setVerifyError(null);
      setDecisionMode(null);
      setDecisionReason('');
      setDecisionError(null);
      setDecisionSuccessMsg(null);
      setActiveTab(initialTab || 'details');
      return;
    }

    setDetailData(action);
    setVerificationReport(action?.latest_verification || null);
    setFetchError(null);
    setVerifyError(null);
    setDecisionMode(null);
    setDecisionReason('');
    setDecisionError(null);
    setDecisionSuccessMsg(null);
    setActiveTab(initialTab || 'details');

    let isMounted = true;
    setIsLoadingFresh(true);

    // 1. Fetch fresh action details
    ClimateShieldAPI.getActionById(action.action_id)
      .then((res) => {
        if (isMounted && res?.action) {
          setDetailData(res.action);
          if (res.action.latest_verification) {
            setVerificationReport(res.action.latest_verification);
          }
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.warn('Could not fetch fresh single action details:', err);
          setFetchError(err.message || 'Unable to sync fresh telemetry from backend store.');
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoadingFresh(false);
        }
      });

    // 2. Fetch latest verification report
    ClimateShieldAPI.getActionVerification(action.action_id)
      .then((res) => {
        if (isMounted && res?.verification) {
          setVerificationReport(res.verification);
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.warn('Could not fetch verification report:', err);
        }
      });

    // 3. Fetch relational audit trail
    fetchAuditTrail(action.action_id);

    return () => {
      isMounted = false;
    };
  }, [isOpen, action, initialTab, fetchAuditTrail]);

  if (!isOpen || !detailData) return null;

  const currentStatus = (detailData.status || 'proposed').toLowerCase();
  const priority = (detailData.priority || 'medium').toLowerCase();
  const resources = detailData.required_resources || {};
  const history = Array.isArray(detailData.status_history) ? detailData.status_history : [];

  const formatDateTime = (isoString) => {
    if (!isoString) return 'Unavailable';
    try {
      const d = new Date(isoString);
      return isNaN(d.getTime()) ? isoString : d.toLocaleString();
    } catch {
      return isoString;
    }
  };

  const formatActionTypeName = (type) => {
    if (!type) return 'Intervention Action';
    return type
      .split('_')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');
  };

  const handleRunVerification = async () => {
    if (!detailData?.action_id) return;
    setIsVerifying(true);
    setVerifyError(null);
    try {
      const res = await ClimateShieldAPI.verifyActionEvidence(detailData.action_id, {
        verified_by: decisionAuthority || 'Municipal Incident Commander',
        notes: 'Operational evidence checklist audit triggered from Command Desk.',
      });
      if (res?.verification) {
        setVerificationReport(res.verification);
        setVerifySuccessToast(true);
        setActiveTab('verification');
        fetchAuditTrail(detailData.action_id);
        if (onActionUpdated) {
          onActionUpdated({
            ...detailData,
            latest_verification: res.verification,
          });
        }
        setTimeout(() => setVerifySuccessToast(false), 3500);
      }
    } catch (err) {
      console.error('Verification failed:', err);
      setVerifyError(err.message || 'Failed to complete evidence verification.');
    } finally {
      setIsVerifying(false);
    }
  };

  const handleExecuteDecision = async (decisionType, explicitReason = null) => {
    if (!detailData?.action_id) return;
    setIsSubmittingDecision(true);
    setDecisionError(null);

    const reasonToUse = (explicitReason !== null ? explicitReason : decisionReason).trim();

    // Enforce reasons for rejection, blocking, and changes requested
    if (['reject', 'block', 'hold', 'changes_requested'].includes(decisionType) && !reasonToUse) {
      setDecisionError(`A mandatory operational justification reason is required to ${decisionType} this action.`);
      setIsSubmittingDecision(false);
      return;
    }

    try {
      const res = await ClimateShieldAPI.executeActionDecision(detailData.action_id, {
        decision: decisionType,
        changed_by: decisionAuthority || 'Municipal Incident Commander',
        reason: reasonToUse,
        notes: reasonToUse || `Decision ${decisionType} authorized via Command Desk.`,
      });

      if (res?.action) {
        setDetailData(res.action);
        setDecisionSuccessMsg(`Decision executed: ${res.message || 'Status successfully updated.'}`);
        setDecisionMode(null);
        setDecisionReason('');
        fetchAuditTrail(detailData.action_id);
        if (onActionUpdated) {
          onActionUpdated(res.action);
        }
        setTimeout(() => setDecisionSuccessMsg(null), 4000);
      }
    } catch (err) {
      console.error(`Decision error (${decisionType}):`, err);
      setDecisionError(err.message || `Failed to execute decision ${decisionType}.`);
    } finally {
      setIsSubmittingDecision(false);
    }
  };

  const overallVerifStatus = verificationReport?.overall_status || 'NOT_VERIFIED';
  const checklistItems = verificationReport?.checklist || [];
  const isVerificationFailed = overallVerifStatus === 'FAILED';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs select-none">
      <div className="bg-surface-container-lowest rounded-2xl border border-outline-variant shadow-2xl w-full max-w-4xl max-h-[94vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-outline-variant flex items-center justify-between bg-[#F8FAF8] shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary-container text-white flex items-center justify-center shadow-xs">
              <span className="material-symbols-outlined text-[22px]">fact_check</span>
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="font-headline-sm text-headline-sm text-primary font-bold">
                  Intervention Review & Decision Command
                </h3>
                <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-800 border font-bold">
                  {detailData.action_id}
                </span>
                <span
                  className={`px-2 py-0.5 rounded-full font-mono text-[10px] font-bold uppercase inline-flex items-center gap-1 ${
                    currentStatus === 'proposed'
                      ? 'bg-amber-100 text-amber-800'
                      : currentStatus === 'approved'
                      ? 'bg-blue-100 text-blue-800'
                      : currentStatus === 'in_progress'
                      ? 'bg-emerald-100 text-emerald-800'
                      : currentStatus === 'blocked'
                      ? 'bg-red-100 text-red-800'
                      : currentStatus === 'rejected'
                      ? 'bg-rose-100 text-rose-800'
                      : currentStatus === 'changes_requested'
                      ? 'bg-purple-100 text-purple-800'
                      : 'bg-slate-100 text-slate-800'
                  }`}
                >
                  {currentStatus.replace(/_/g, ' ')}
                </span>
                {isLoadingFresh && (
                  <span className="inline-flex items-center gap-1 font-mono text-[10px] text-outline">
                    <span className="w-2 h-2 rounded-full border border-primary border-t-transparent animate-spin"></span>
                    Syncing...
                  </span>
                )}
              </div>
              <p className="text-xs font-mono text-outline mt-0.5">
                AMC Operational Command Desk • Human-in-the-Loop Governance & Evidence Verification
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 text-outline hover:text-on-surface hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
            title="Close review modal"
          >
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        {/* Navigation Tabs */}
        <div className="px-6 pt-3 pb-0 bg-surface-bright border-b border-outline-variant flex items-center justify-between gap-4 shrink-0 overflow-x-auto">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab('details')}
              className={`px-4 py-2 border-b-2 font-mono text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                activeTab === 'details'
                  ? 'border-primary text-primary bg-white/70 rounded-t-lg'
                  : 'border-transparent text-outline hover:text-on-surface'
              }`}
            >
              <span className="material-symbols-outlined text-[16px]">list_alt</span>
              <span>Operational Details</span>
            </button>

            <button
              onClick={() => setActiveTab('verification')}
              className={`px-4 py-2 border-b-2 font-mono text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                activeTab === 'verification'
                  ? 'border-primary text-primary bg-white/70 rounded-t-lg'
                  : 'border-transparent text-outline hover:text-on-surface'
              }`}
            >
              <span className="material-symbols-outlined text-[16px]">verified_user</span>
              <span>Evidence Verification</span>
              <span
                className={`ml-1 px-1.5 py-0.2 rounded-full text-[9px] font-bold uppercase ${
                  overallVerifStatus === 'VERIFIED'
                    ? 'bg-emerald-100 text-emerald-800'
                    : overallVerifStatus === 'FAILED'
                    ? 'bg-red-100 text-red-800'
                    : overallVerifStatus === 'UNABLE_TO_VERIFY'
                    ? 'bg-amber-100 text-amber-800'
                    : 'bg-slate-200 text-slate-700'
                }`}
              >
                {overallVerifStatus.replace(/_/g, ' ')}
              </span>
            </button>

            <button
              onClick={() => setActiveTab('audit')}
              className={`px-4 py-2 border-b-2 font-mono text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 ${
                activeTab === 'audit'
                  ? 'border-primary text-primary bg-white/70 rounded-t-lg'
                  : 'border-transparent text-outline hover:text-on-surface'
              }`}
            >
              <span className="material-symbols-outlined text-[16px]">history</span>
              <span>Audit Trail</span>
              <span className="ml-1 px-1.5 py-0.2 rounded-full bg-slate-200 text-slate-700 text-[9px] font-mono">
                {auditEvents.length || history.length}
              </span>
            </button>
          </div>

          {/* Quick Verify CTA */}
          <button
            onClick={handleRunVerification}
            disabled={isVerifying}
            className="mb-2 px-3 py-1.5 rounded-lg bg-primary-container text-white hover:bg-[#1B5742] active:scale-[0.98] font-mono text-xs font-bold transition-all cursor-pointer shadow-xs inline-flex items-center gap-1.5 disabled:opacity-50 shrink-0"
            title="Execute evidence verification against active data"
          >
            {isVerifying ? (
              <>
                <span className="w-3 h-3 rounded-full border-2 border-white border-t-transparent animate-spin"></span>
                <span>Verifying...</span>
              </>
            ) : (
              <>
                <span className="material-symbols-outlined text-[15px]">task_alt</span>
                <span>Run Evidence Verification</span>
              </>
            )}
          </button>
        </div>

        {/* Global Notifications */}
        {decisionSuccessMsg && (
          <div className="mx-6 mt-3 p-3 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center gap-2 text-xs text-emerald-900 font-mono animate-in fade-in">
            <span className="material-symbols-outlined text-[18px] text-emerald-700">check_circle</span>
            <span>{decisionSuccessMsg}</span>
          </div>
        )}

        {decisionError && (
          <div className="mx-6 mt-3 p-3 bg-red-50 border border-red-200 rounded-xl flex items-center justify-between text-xs text-red-900 font-mono animate-in fade-in">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[18px] text-red-700">error</span>
              <span>{decisionError}</span>
            </div>
            <button onClick={() => setDecisionError(null)} className="text-red-700 hover:underline">
              Dismiss
            </button>
          </div>
        )}

        {verifySuccessToast && (
          <div className="mx-6 mt-3 p-3 bg-emerald-50 border border-emerald-300 rounded-xl flex items-center gap-2 text-xs font-mono text-emerald-900 animate-in fade-in">
            <span className="material-symbols-outlined text-[18px] text-emerald-600">verified</span>
            <span>Evidence verification completed and recorded to SQLite baseline. Overall Status: {overallVerifStatus}</span>
          </div>
        )}

        {/* Modal Scrollable Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-on-surface">
          
          {/* ========================================================================= */}
          {/* TAB 1: OPERATIONAL DETAILS                                                */}
          {/* ========================================================================= */}
          {activeTab === 'details' && (
            <div className="space-y-6">
              
              {/* Top Banner / Key Metrics */}
              <div className="p-4 rounded-xl border border-outline-variant bg-[#F8FAF8] grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
                <div>
                  <div className="text-[10px] text-outline uppercase font-semibold">Ward & Jurisdiction</div>
                  <div className="font-bold text-on-surface text-sm mt-0.5">
                    {detailData.ward_name} ({detailData.ward_id})
                  </div>
                </div>

                <div>
                  <div className="text-[10px] text-outline uppercase font-semibold">Intervention Type</div>
                  <div className="font-bold text-primary text-sm mt-0.5">
                    {formatActionTypeName(detailData.action_type)}
                  </div>
                </div>

                <div>
                  <div className="text-[10px] text-outline uppercase font-semibold">Priority Tier</div>
                  <div className="mt-0.5">
                    <span
                      className={`px-2 py-0.5 rounded-full font-bold uppercase text-[10px] ${
                        priority === 'critical'
                          ? 'bg-red-100 text-red-800'
                          : priority === 'high'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-slate-100 text-slate-800'
                      }`}
                    >
                      {priority}
                    </span>
                  </div>
                </div>

                <div>
                  <div className="text-[10px] text-outline uppercase font-semibold">Verification State</div>
                  <div className="mt-0.5 flex items-center gap-1.5">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        overallVerifStatus === 'VERIFIED'
                          ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                          : overallVerifStatus === 'FAILED'
                          ? 'bg-red-100 text-red-800 border border-red-300'
                          : 'bg-amber-100 text-amber-800 border border-amber-300'
                      }`}
                    >
                      {overallVerifStatus.replace(/_/g, ' ')}
                    </span>
                  </div>
                </div>
              </div>

              {/* Rationale & Justification */}
              <div className="space-y-2">
                <h5 className="font-mono text-[11px] uppercase font-bold text-outline flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[15px]">description</span>
                  <span>Operational Rationale & Risk Trigger Justification</span>
                </h5>
                <div className="p-3.5 rounded-xl border border-outline-variant bg-white text-xs leading-relaxed">
                  {detailData.reason || 'No specific rationale entered for this intervention record.'}
                </div>
              </div>

              {/* Required Resources Schedule */}
              <div className="space-y-2">
                <h5 className="font-mono text-[11px] uppercase font-bold text-outline flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[15px]">inventory_2</span>
                  <span>Municipal Resource Allocation Schedule</span>
                </h5>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div className="p-3 rounded-xl border border-outline-variant bg-white">
                    <div className="font-mono text-[10px] text-outline uppercase">Allocated Budget</div>
                    <div className="font-bold text-on-surface text-sm mt-0.5 font-mono">
                      {resources.cost_inr !== undefined && resources.cost_inr !== null
                        ? `₹${Number(resources.cost_inr).toLocaleString('en-IN')}`
                        : '—'}
                    </div>
                  </div>

                  <div className="p-3 rounded-xl border border-outline-variant bg-white">
                    <div className="font-mono text-[10px] text-outline uppercase">Field Personnel / Crew</div>
                    <div className="font-bold text-on-surface text-sm mt-0.5 font-mono">
                      {resources.crew_required !== undefined && resources.crew_required !== null
                        ? `${resources.crew_required} Members`
                        : '—'}
                    </div>
                  </div>

                  <div className="p-3 rounded-xl border border-outline-variant bg-white">
                    <div className="font-mono text-[10px] text-outline uppercase">Daily Water Allocation</div>
                    <div className="font-bold text-on-surface text-sm mt-0.5 font-mono">
                      {resources.water_required_l !== undefined && resources.water_required_l !== null
                        ? `${Number(resources.water_required_l).toLocaleString('en-IN')} Liters`
                        : '—'}
                    </div>
                  </div>
                </div>
              </div>

              {/* Risk Context */}
              <div className="space-y-2">
                <h5 className="font-mono text-[11px] uppercase font-bold text-outline flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[15px]">thermostat</span>
                  <span>Climate Risk Engine Context</span>
                </h5>
                <div className="p-3.5 rounded-xl border border-outline-variant bg-white grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs font-mono">
                  <div>
                    <span className="text-outline text-[10px] uppercase">Recorded Risk Score</span>
                    <div className="font-bold text-on-surface mt-0.5 text-sm">
                      {detailData.risk_score ? `${detailData.risk_score.toFixed(1)} / 100` : 'Not Attached'}
                    </div>
                  </div>

                  <div>
                    <span className="text-outline text-[10px] uppercase">Related Hazard</span>
                    <div className="font-bold text-on-surface mt-0.5 capitalize">
                      {detailData.related_hazard || 'Multi-Hazard'}
                    </div>
                  </div>

                  <div>
                    <span className="text-outline text-[10px] uppercase">Record Source</span>
                    <div className="font-bold text-on-surface mt-0.5">
                      {detailData.source || 'AMC Operational Registry'}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ========================================================================= */}
          {/* TAB 2: EVIDENCE VERIFICATION CHECKLIST                                    */}
          {/* ========================================================================= */}
          {activeTab === 'verification' && (
            <div className="space-y-5 animate-in fade-in-50">
              
              {/* Overall Verification Status Banner */}
              <div
                className={`p-4 rounded-xl border-2 flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
                  overallVerifStatus === 'VERIFIED'
                    ? 'bg-emerald-50/70 border-emerald-300 text-emerald-950'
                    : overallVerifStatus === 'FAILED'
                    ? 'bg-red-50/70 border-red-300 text-red-950'
                    : overallVerifStatus === 'UNABLE_TO_VERIFY'
                    ? 'bg-amber-50/70 border-amber-300 text-amber-950'
                    : 'bg-slate-50 border-slate-300 text-slate-800'
                }`}
              >
                <div className="flex items-start gap-3">
                  <span className="material-symbols-outlined text-[28px] shrink-0 mt-0.5">
                    {overallVerifStatus === 'VERIFIED'
                      ? 'verified'
                      : overallVerifStatus === 'FAILED'
                      ? 'gpp_bad'
                      : overallVerifStatus === 'UNABLE_TO_VERIFY'
                      ? 'warning'
                      : 'hourglass_empty'}
                  </span>
                  <div>
                    <div className="font-bold text-sm uppercase tracking-wide font-mono flex items-center gap-2">
                      <span>Verification Verdict: {overallVerifStatus.replace(/_/g, ' ')}</span>
                    </div>
                    <p className="text-xs mt-1 leading-relaxed">
                      {verificationReport?.verdict_summary ||
                        'Run evidence verification to cross-check this intervention against AMC ward boundaries, quantitative risk thresholds, and telemetry freshness.'}
                    </p>
                    {isVerificationFailed && (
                      <p className="text-xs font-bold text-red-700 mt-1 font-mono">
                        POLICY NOTICE: This intervention cannot be approved or dispatched while mandatory checks are FAILED.
                      </p>
                    )}
                  </div>
                </div>

                <button
                  onClick={handleRunVerification}
                  disabled={isVerifying}
                  className="px-4 py-2 rounded-xl bg-primary-container text-white hover:bg-[#1B5742] font-mono text-xs font-bold transition-all cursor-pointer shadow-xs inline-flex items-center gap-1.5 shrink-0 disabled:opacity-50"
                >
                  <span className="material-symbols-outlined text-[16px]">sync</span>
                  <span>{isVerifying ? 'Auditing...' : 'Re-verify Now'}</span>
                </button>
              </div>

              {/* Checklist Grid */}
              <div className="space-y-3">
                <h5 className="font-mono text-[11px] uppercase font-bold text-outline flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[15px]">checklist</span>
                  <span>Evidence Audit Checklist ({checklistItems.length} Mandatory & Operational Verification Checks)</span>
                </h5>

                {checklistItems.length === 0 ? (
                  <div className="p-6 text-center text-outline font-mono text-xs border border-dashed rounded-xl">
                    No verification records logged yet. Click "Run Evidence Verification" to evaluate this action against live data.
                  </div>
                ) : (
                  checklistItems.map((chk, i) => {
                    const st = chk.status;
                    return (
                      <div
                        key={chk.check_id || i}
                        className={`p-3.5 rounded-xl border transition-all ${
                          st === 'VERIFIED'
                            ? 'bg-emerald-50/30 border-emerald-200'
                            : st === 'FAILED'
                            ? 'bg-red-50/40 border-red-200'
                            : st === 'UNABLE_TO_VERIFY'
                            ? 'bg-amber-50/30 border-amber-200'
                            : 'bg-slate-50/50 border-slate-200'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex items-start gap-2.5">
                            <span
                              className={`material-symbols-outlined text-[18px] shrink-0 mt-0.5 ${
                                st === 'VERIFIED'
                                  ? 'text-emerald-700'
                                  : st === 'FAILED'
                                  ? 'text-red-700'
                                  : st === 'UNABLE_TO_VERIFY'
                                  ? 'text-amber-700'
                                  : 'text-outline'
                              }`}
                            >
                              {st === 'VERIFIED'
                                ? 'check_circle'
                                : st === 'FAILED'
                                ? 'cancel'
                                : st === 'UNABLE_TO_VERIFY'
                                ? 'help'
                                : 'pending'}
                            </span>
                            <div>
                              <div className="font-bold text-xs text-on-surface flex items-center gap-2">
                                <span>{chk.title}</span>
                                {chk.mandatory && (
                                  <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-red-100 text-red-800 uppercase font-bold">
                                    Mandatory
                                  </span>
                                )}
                              </div>
                              <p className="text-xs text-on-surface-variant mt-0.5">{chk.message}</p>
                              {chk.reason && (
                                <p className="text-[11px] text-outline font-mono mt-1">Audit Finding: {chk.reason}</p>
                              )}
                            </div>
                          </div>

                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase shrink-0 ${
                              st === 'VERIFIED'
                                ? 'bg-emerald-100 text-emerald-800'
                                : st === 'FAILED'
                                ? 'bg-red-100 text-red-800'
                                : st === 'UNABLE_TO_VERIFY'
                                ? 'bg-amber-100 text-amber-800'
                                : 'bg-slate-200 text-slate-700'
                            }`}
                          >
                            {st.replace(/_/g, ' ')}
                          </span>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          )}

          {/* ========================================================================= */}
          {/* TAB 3: AUDIT TRAIL & DECISION HISTORY                                     */}
          {/* ========================================================================= */}
          {activeTab === 'audit' && (
            <div className="space-y-5 animate-in fade-in-50">
              <div className="flex items-center justify-between">
                <h5 className="font-mono text-[11px] uppercase font-bold text-outline flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[15px]">history_edu</span>
                  <span>Immutable SQLite Municipal Audit Log</span>
                </h5>
                <span className="font-mono text-[10px] text-outline">
                  Total Events: {auditEvents.length}
                </span>
              </div>

              {isLoadingAudit ? (
                <div className="p-8 text-center text-outline font-mono text-xs">
                  <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                  Loading relational audit events from SQLite...
                </div>
              ) : auditEvents.length === 0 ? (
                <div className="p-6 rounded-xl border border-slate-200 bg-white text-center font-mono text-xs text-outline">
                  No relational audit events found for this action.
                </div>
              ) : (
                <div className="rounded-xl border border-outline-variant overflow-hidden bg-white">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="border-b border-outline-variant bg-[#F8FAF8] text-[10px] uppercase font-mono text-outline">
                        <th className="py-2.5 px-3">Event Type</th>
                        <th className="py-2.5 px-3">Authorized Actor</th>
                        <th className="py-2.5 px-3">Status Transition</th>
                        <th className="py-2.5 px-3">Reason / Justification</th>
                        <th className="py-2.5 px-3 text-right">Timestamp</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-outline-variant font-mono text-[11px]">
                      {auditEvents.map((ev) => (
                        <tr key={ev.event_id} className="hover:bg-slate-50 transition-colors">
                          <td className="py-2.5 px-3 font-bold text-primary">
                            <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-800 border text-[10px]">
                              {ev.event_type}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-on-surface font-semibold">
                            {ev.actor || 'System'}
                          </td>
                          <td className="py-2.5 px-3">
                            {ev.old_status && ev.new_status ? (
                              <span className="inline-flex items-center gap-1 text-[10px]">
                                <span className="uppercase text-outline">{ev.old_status}</span>
                                <span className="material-symbols-outlined text-[12px]">arrow_forward</span>
                                <span className="uppercase text-primary font-bold">{ev.new_status}</span>
                              </span>
                            ) : ev.new_status ? (
                              <span className="uppercase text-primary font-bold text-[10px]">{ev.new_status}</span>
                            ) : (
                              '—'
                            )}
                          </td>
                          <td className="py-2.5 px-3 text-on-surface-variant font-sans text-xs max-w-xs truncate" title={ev.reason}>
                            {ev.reason || '—'}
                          </td>
                          <td className="py-2.5 px-3 text-right text-outline text-[10px]">
                            {formatDateTime(ev.timestamp)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

        </div>

        {/* ========================================================================= */}
        {/* DECISION WORKFLOW BAR & MODAL FOOTER                                      */}
        {/* ========================================================================= */}
        <div className="px-6 py-4 border-t border-outline-variant bg-[#F8FAF8] space-y-3 shrink-0">
          
          {/* Inline Reason Form for Decision with Mandatory Justification */}
          {decisionMode && (
            <div className="p-4 rounded-xl border-2 border-primary/40 bg-white space-y-3 animate-in fade-in slide-in-from-bottom-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary text-[18px]">gavel</span>
                  <span className="font-bold text-xs uppercase font-mono text-primary">
                    {decisionMode === 'reject'
                      ? 'Confirm Rejection (Mandatory Reason Required)'
                      : decisionMode === 'block'
                      ? 'Confirm Hold / Block Operation (Mandatory Reason Required)'
                      : decisionMode === 'changes_requested'
                      ? 'Request Operational Changes (Mandatory Reason Required)'
                      : 'Confirm Operational Unblock'}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setDecisionMode(null)}
                  className="text-outline hover:text-on-surface text-xs font-mono cursor-pointer"
                >
                  Cancel
                </button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div>
                  <label className="block text-[10px] font-mono uppercase text-outline mb-1 font-bold">
                    Authorizing Municipal Officer / Role *
                  </label>
                  <select
                    value={decisionAuthority}
                    onChange={(e) => setDecisionAuthority(e.target.value)}
                    className="w-full h-8 px-2.5 bg-white border border-outline-variant rounded-lg font-mono text-xs focus:outline-none focus:border-primary"
                  >
                    <option value="Municipal Incident Commander">Municipal Incident Commander</option>
                    <option value="Municipal Commissioner (AMC)">Municipal Commissioner (AMC)</option>
                    <option value="Disaster Management Authority">Disaster Management Authority</option>
                    <option value="Chief Medical Officer">Chief Medical Officer</option>
                    <option value="Zonal Operations Officer">Zonal Operations Officer</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[10px] font-mono uppercase text-outline mb-1 font-bold">
                    Quick Preset Rationale
                  </label>
                  <select
                    onChange={(e) => {
                      if (e.target.value) setDecisionReason(e.target.value);
                    }}
                    className="w-full h-8 px-2.5 bg-white border border-outline-variant rounded-lg font-mono text-xs focus:outline-none focus:border-primary"
                  >
                    <option value="">Select quick preset reason...</option>
                    {decisionMode === 'reject' && (
                      <>
                        <option value="Duplicate active operation already present in this ward.">Duplicate active operation.</option>
                        <option value="Field ground inspection indicates hazard below emergency threshold.">Ground survey indicates low hazard.</option>
                        <option value="Exceeds current municipal emergency resource ceiling.">Exceeds resource ceiling.</option>
                      </>
                    )}
                    {decisionMode === 'block' && (
                      <>
                        <option value="Temporary route blockage prevents field crew deployment.">Road blockage / inaccessible route.</option>
                        <option value="Pending empirical telemetry calibration before authorization.">Awaiting sensor calibration.</option>
                        <option value="Water fleet redistribution required before dispatch.">Fleet redistribution pending.</option>
                      </>
                    )}
                    {decisionMode === 'changes_requested' && (
                      <>
                        <option value="Increase allocated water volume to match informal settlement density.">Increase water quota.</option>
                        <option value="Adjust dispatch schedule to avoid peak afternoon ambient temperatures.">Adjust deployment window.</option>
                      </>
                    )}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-[10px] font-mono uppercase text-outline mb-1 font-bold">
                  Justification Reason & Operational Notes *
                </label>
                <textarea
                  rows={2}
                  placeholder="Enter detailed municipal reason (required)..."
                  value={decisionReason}
                  onChange={(e) => setDecisionReason(e.target.value)}
                  className="w-full p-2 text-xs bg-slate-50 border border-outline-variant rounded-lg focus:outline-none focus:border-primary font-mono"
                />
              </div>

              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setDecisionMode(null)}
                  className="px-3 py-1.5 rounded-lg border border-outline-variant text-xs font-mono font-bold hover:bg-slate-50 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={isSubmittingDecision || !decisionReason.trim()}
                  onClick={() => handleExecuteDecision(decisionMode)}
                  className="px-4 py-1.5 rounded-lg bg-primary-container text-white font-mono text-xs font-bold hover:bg-[#1B5742] transition-all cursor-pointer shadow-xs disabled:opacity-50"
                >
                  {isSubmittingDecision ? 'Submitting Decision...' : 'Confirm Decision & Persist'}
                </button>
              </div>
            </div>
          )}

          {/* Context-Sensitive Decision Action Strip */}
          {!decisionMode && (
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[10px] font-mono uppercase font-bold text-outline">
                  Operational Actions:
                </span>

                {/* PROPOSED: Approve, Reject, Hold, Request Changes */}
                {currentStatus === 'proposed' && (
                  <>
                    <button
                      type="button"
                      disabled={isSubmittingDecision || isVerificationFailed}
                      onClick={() => handleExecuteDecision('approve')}
                      className={`px-3 py-1.5 rounded-lg font-mono text-xs font-bold transition-all shadow-xs flex items-center gap-1 ${
                        isVerificationFailed
                          ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
                          : 'bg-blue-600 text-white hover:bg-blue-700 cursor-pointer'
                      }`}
                      title={
                        isVerificationFailed
                          ? 'Approval blocked: evidence verification has failed mandatory checks'
                          : 'Approve intervention for municipal deployment'
                      }
                    >
                      <span className="material-symbols-outlined text-[15px]">check_circle</span>
                      <span>Approve</span>
                    </button>

                    <button
                      type="button"
                      disabled={isSubmittingDecision}
                      onClick={() => setDecisionMode('reject')}
                      className="px-3 py-1.5 rounded-lg bg-rose-50 text-rose-800 border border-rose-300 font-mono text-xs font-bold hover:bg-rose-100 transition-all cursor-pointer shadow-xs flex items-center gap-1"
                      title="Reject intervention with mandatory reason"
                    >
                      <span className="material-symbols-outlined text-[15px]">cancel</span>
                      <span>Reject</span>
                    </button>

                    <button
                      type="button"
                      disabled={isSubmittingDecision}
                      onClick={() => setDecisionMode('block')}
                      className="px-3 py-1.5 rounded-lg bg-amber-50 text-amber-800 border border-amber-300 font-mono text-xs font-bold hover:bg-amber-100 transition-all cursor-pointer shadow-xs flex items-center gap-1"
                      title="Hold / block intervention with mandatory reason"
                    >
                      <span className="material-symbols-outlined text-[15px]">pause_circle</span>
                      <span>Hold / Block</span>
                    </button>

                    <button
                      type="button"
                      disabled={isSubmittingDecision}
                      onClick={() => setDecisionMode('changes_requested')}
                      className="px-3 py-1.5 rounded-lg bg-purple-50 text-purple-800 border border-purple-300 font-mono text-xs font-bold hover:bg-purple-100 transition-all cursor-pointer shadow-xs flex items-center gap-1"
                      title="Request changes with mandatory notes"
                    >
                      <span className="material-symbols-outlined text-[15px]">edit_note</span>
                      <span>Request Changes</span>
                    </button>
                  </>
                )}

                {/* APPROVED: Deploy, Hold, Cancel */}
                {currentStatus === 'approved' && (
                  <>
                    <button
                      type="button"
                      disabled={isSubmittingDecision || isVerificationFailed}
                      onClick={() => handleExecuteDecision('deploy')}
                      className="px-3.5 py-1.5 rounded-lg bg-primary-container text-white font-mono text-xs font-bold hover:bg-[#1B5742] transition-all cursor-pointer shadow-xs flex items-center gap-1"
                      title="Deploy and mobilize field crew"
                    >
                      <span className="material-symbols-outlined text-[15px]">send</span>
                      <span>Deploy / Mobilize</span>
                    </button>

                    <button
                      type="button"
                      disabled={isSubmittingDecision}
                      onClick={() => setDecisionMode('block')}
                      className="px-3 py-1.5 rounded-lg bg-amber-50 text-amber-800 border border-amber-300 font-mono text-xs font-bold hover:bg-amber-100 transition-all cursor-pointer shadow-xs flex items-center gap-1"
                    >
                      <span className="material-symbols-outlined text-[15px]">pause_circle</span>
                      <span>Hold / Block</span>
                    </button>
                  </>
                )}

                {/* IN_PROGRESS: Complete, Hold */}
                {currentStatus === 'in_progress' && (
                  <>
                    <button
                      type="button"
                      disabled={isSubmittingDecision}
                      onClick={() => handleExecuteDecision('complete')}
                      className="px-3.5 py-1.5 rounded-lg bg-emerald-600 text-white font-mono text-xs font-bold hover:bg-emerald-700 transition-all cursor-pointer shadow-xs flex items-center gap-1"
                      title="Mark field operation resolved and completed"
                    >
                      <span className="material-symbols-outlined text-[15px]">task_alt</span>
                      <span>Complete Operation</span>
                    </button>

                    <button
                      type="button"
                      disabled={isSubmittingDecision}
                      onClick={() => setDecisionMode('block')}
                      className="px-3 py-1.5 rounded-lg bg-amber-50 text-amber-800 border border-amber-300 font-mono text-xs font-bold hover:bg-amber-100 transition-all cursor-pointer shadow-xs flex items-center gap-1"
                    >
                      <span className="material-symbols-outlined text-[15px]">pause_circle</span>
                      <span>Hold / Block</span>
                    </button>
                  </>
                )}

                {/* BLOCKED: Unblock, Reject */}
                {currentStatus === 'blocked' && (
                  <>
                    <button
                      type="button"
                      disabled={isSubmittingDecision}
                      onClick={() => handleExecuteDecision('unblock', 'Unblocked by authorizing municipal authority.')}
                      className="px-3.5 py-1.5 rounded-lg bg-blue-600 text-white font-mono text-xs font-bold hover:bg-blue-700 transition-all cursor-pointer shadow-xs flex items-center gap-1"
                      title="Unblock operation and restore to active queue"
                    >
                      <span className="material-symbols-outlined text-[15px]">play_circle</span>
                      <span>Unblock Operation</span>
                    </button>

                    <button
                      type="button"
                      disabled={isSubmittingDecision}
                      onClick={() => setDecisionMode('reject')}
                      className="px-3 py-1.5 rounded-lg bg-rose-50 text-rose-800 border border-rose-300 font-mono text-xs font-bold hover:bg-rose-100 transition-all cursor-pointer shadow-xs flex items-center gap-1"
                    >
                      <span className="material-symbols-outlined text-[15px]">cancel</span>
                      <span>Reject</span>
                    </button>
                  </>
                )}

                {/* CHANGES REQUESTED: Resubmit */}
                {currentStatus === 'changes_requested' && (
                  <button
                    type="button"
                    disabled={isSubmittingDecision}
                    onClick={() => handleExecuteDecision('unblock', 'Resubmitted after operational revisions.')}
                    className="px-3.5 py-1.5 rounded-lg bg-primary-container text-white font-mono text-xs font-bold hover:bg-[#1B5742] transition-all cursor-pointer shadow-xs flex items-center gap-1"
                  >
                    <span className="material-symbols-outlined text-[15px]">replay</span>
                    <span>Resubmit for Approval</span>
                  </button>
                )}

                {/* COMPLETED / REJECTED: Terminal state display */}
                {currentStatus === 'completed' && (
                  <span className="font-mono text-xs text-emerald-700 font-bold flex items-center gap-1">
                    <span className="material-symbols-outlined text-[16px]">check_circle</span>
                    <span>Operation Resolved</span>
                  </span>
                )}
                {currentStatus === 'rejected' && (
                  <span className="font-mono text-xs text-rose-700 font-bold flex items-center gap-1">
                    <span className="material-symbols-outlined text-[16px]">block</span>
                    <span>Operation Rejected</span>
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-1.5 rounded-lg bg-white border border-outline-variant text-on-surface hover:bg-slate-50 font-mono text-xs font-bold transition-all cursor-pointer shadow-xs shrink-0"
                >
                  Close Review
                </button>
              </div>
            </div>
          )}

        </div>

      </div>
    </div>
  );
}
