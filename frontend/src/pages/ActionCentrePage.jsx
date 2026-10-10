import React, { useState, useEffect, useCallback, useMemo } from 'react';
import KPICard from '../components/KPICard';
import InterventionDetailModal from '../components/InterventionDetailModal';
import { ClimateShieldAPI } from '../services/api';

export default function ActionCentrePage({ onOpenDeployModal }) {
  // Filters & Search
  const [filterStatus, setFilterStatus] = useState('All');
  const [filterPriority, setFilterPriority] = useState('All');
  const [filterVerification, setFilterVerification] = useState('All');
  const [searchFilter, setSearchFilter] = useState('');

  // Data & Loading
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionsList, setActionsList] = useState([]);
  const [dashboardData, setDashboardData] = useState(null);
  const [isUpdating, setIsUpdating] = useState(false);
  const [notification, setNotification] = useState(null);

  // Review & Detail Modal
  const [selectedAction, setSelectedAction] = useState(null);
  const [detailModalTab, setDetailModalTab] = useState('details');
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);

  // Decision Modal State
  const [decisionTarget, setDecisionTarget] = useState(null);
  const [decisionType, setDecisionType] = useState(null); // 'reject' | 'block' | 'changes_requested' | 'approve'
  const [decisionReason, setDecisionReason] = useState('');
  const [decisionAuthority, setDecisionAuthority] = useState('Municipal Incident Commander');
  const [isDecisionModalOpen, setIsDecisionModalOpen] = useState(false);
  const [isSubmittingDecision, setIsSubmittingDecision] = useState(false);
  const [decisionModalError, setDecisionModalError] = useState(null);

  // Quick Dispatch Modal State
  const [quickDispatchPreset, setQuickDispatchPreset] = useState(null);
  const [isQuickDispatchModalOpen, setIsQuickDispatchModalOpen] = useState(false);
  const [quickDispatchAuthority, setQuickDispatchAuthority] = useState('Municipal Incident Commander');
  const [isSubmittingDispatch, setIsSubmittingDispatch] = useState(false);
  const [quickDispatchError, setQuickDispatchError] = useState(null);

  // Global Audit Trail Modal State
  const [isAuditModalOpen, setIsAuditModalOpen] = useState(false);
  const [globalAuditEvents, setGlobalAuditEvents] = useState([]);
  const [isLoadingAudit, setIsLoadingAudit] = useState(false);

  const showToast = (message, isError = false) => {
    setNotification({ message, isError });
    setTimeout(() => setNotification(null), 4500);
  };

  const handleReviewAction = (action, initialTab = 'details') => {
    setSelectedAction(action);
    setDetailModalTab(initialTab);
    setIsDetailModalOpen(true);
  };

  const fetchActionCentreData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await ClimateShieldAPI.getActionCentreDashboard();
      setDashboardData(res);
      let actions = res?.prioritized_actions || [];

      // If store is completely empty, populate initial transparent rule-based recommendations
      if (actions.length === 0 && (!res?.action_summary?.total_actions || res.action_summary.total_actions === 0)) {
        try {
          await ClimateShieldAPI.generateRuleRecommendations({
            persist_to_store: true,
            enforce_resource_constraints: false,
          });
          const refreshed = await ClimateShieldAPI.getActionCentreDashboard();
          setDashboardData(refreshed);
          actions = refreshed?.prioritized_actions || [];
        } catch (genErr) {
          console.warn('Auto-generation of initial recommendations skipped:', genErr);
        }
      }

      setActionsList(actions);
    } catch (err) {
      console.error('Failed to load Action Centre data:', err);
      setError(err.message || 'Failed to load Action Centre data from backend.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchActionCentreData();
  }, [fetchActionCentreData]);

  // Open Decision Modal
  const openDecisionModal = (action, type) => {
    setDecisionTarget(action);
    setDecisionType(type);
    setDecisionReason('');
    setDecisionModalError(null);
    setIsDecisionModalOpen(true);
  };

  // Submit Decision
  const handleConfirmDecision = async () => {
    if (!decisionTarget || !decisionType) return;

    const trimmedReason = decisionReason.trim();
    if (['reject', 'block', 'changes_requested'].includes(decisionType) && !trimmedReason) {
      setDecisionModalError(`A mandatory operational justification reason is required to ${decisionType} this intervention.`);
      return;
    }

    setIsSubmittingDecision(true);
    setDecisionModalError(null);

    try {
      const res = await ClimateShieldAPI.executeActionDecision(decisionTarget.action_id, {
        decision: decisionType,
        changed_by: decisionAuthority || 'Municipal Incident Commander',
        reason: trimmedReason,
        notes: trimmedReason || `Operational transition to ${decisionType} authorized via Command Desk.`,
      });

      if (res?.action) {
        setActionsList((prev) =>
          prev.map((a) => (a.action_id === decisionTarget.action_id ? res.action : a))
        );
        showToast(res.message || `Action ${decisionTarget.action_id} successfully updated.`);
        setIsDecisionModalOpen(false);
        setDecisionTarget(null);
        setDecisionType(null);
        // Sync fresh backend dashboard counts
        ClimateShieldAPI.getActionCentreDashboard().then(setDashboardData).catch(() => {});
      }
    } catch (err) {
      console.error('Decision execution failed:', err);
      setDecisionModalError(err.message || `Failed to execute ${decisionType}.`);
    } finally {
      setIsSubmittingDecision(false);
    }
  };

  // Direct status transition (e.g. for Approve, Deploy, Complete when no reason dialog needed)
  const handleDirectTransition = async (action, type) => {
    // Verification check for approval
    const verifStatus = action.latest_verification?.overall_status;
    if (type === 'approve' && verifStatus === 'FAILED') {
      showToast(`Cannot approve ${action.action_id}: Evidence verification has FAILED mandatory checks. Resolve discrepancies before approval.`, true);
      return;
    }

    setIsUpdating(true);
    try {
      const res = await ClimateShieldAPI.executeActionDecision(action.action_id, {
        decision: type,
        changed_by: 'Municipal Incident Commander',
        notes: `Operational decision ${type} authorized via Command Desk.`,
      });

      if (res?.action) {
        setActionsList((prev) =>
          prev.map((a) => (a.action_id === action.action_id ? res.action : a))
        );
        showToast(`Action ${action.action_id} successfully updated: ${type}.`);
        ClimateShieldAPI.getActionCentreDashboard().then(setDashboardData).catch(() => {});
      }
    } catch (err) {
      console.error(`Direct transition error (${type}):`, err);
      showToast(`Failed to execute ${type} for ${action.action_id}: ${err.message}`, true);
    } finally {
      setIsUpdating(false);
    }
  };

  // Quick Dispatch Click -> Opens Confirmation Modal
  const triggerQuickDispatchModal = (presetKey) => {
    let preset;
    if (presetKey === 'tankers') {
      preset = {
        key: 'tankers',
        title: 'Emergency Water Tanker Fleet (6 Tankers)',
        ward_id: 'W1',
        ward_name: 'Danilimda',
        action_type: 'water_tanker_dispatch',
        priority: 'critical',
        reason: 'Emergency water tanker dispatch to informal settlements in Danilimda facing critical water scarcity.',
        required_resources: { cost_inr: 72000, crew_required: 12, water_required_l: 30000 },
        related_hazard: 'heat_and_water',
        risk_score: 85.0,
      };
    } else if (presetKey === 'ors') {
      preset = {
        key: 'ors',
        title: 'Activate Urban Health Centre ORS Booths',
        ward_id: 'W4',
        ward_name: 'Gomtipur',
        action_type: 'cooling_centre',
        priority: 'high',
        reason: 'Activate Urban Health Centres with emergency ORS replenishment and hydration corners in Gomtipur.',
        required_resources: { cost_inr: 50000, crew_required: 6, water_required_l: 2000 },
        related_hazard: 'heat',
        risk_score: 78.0,
      };
    } else {
      preset = {
        key: 'misting',
        title: 'High-Pressure Outdoor Misting Deployment',
        ward_id: 'W2',
        ward_name: 'Kalupur',
        action_type: 'drinking_water_point',
        priority: 'high',
        reason: 'Deploy high-pressure misting systems at AMTS transit interchange in Kalupur to lower ambient WBGT.',
        required_resources: { cost_inr: 30000, crew_required: 4, water_required_l: 4000 },
        related_hazard: 'heat',
        risk_score: 74.0,
      };
    }

    // Check for duplicate active dispatches in same ward
    const duplicate = actionsList.find(
      (a) =>
        a.ward_id === preset.ward_id &&
        a.action_type === preset.action_type &&
        ['proposed', 'approved', 'in_progress', 'blocked'].includes(a.status)
    );

    preset.existingDuplicate = duplicate || null;
    setQuickDispatchPreset(preset);
    setQuickDispatchError(null);
    setIsQuickDispatchModalOpen(true);
  };

  // Confirm Quick Dispatch (Real Backend Persistence)
  const handleConfirmQuickDispatch = async (force = false) => {
    if (!quickDispatchPreset) return;
    setIsSubmittingDispatch(true);
    setQuickDispatchError(null);

    try {
      const payload = {
        ward_id: quickDispatchPreset.ward_id,
        ward_name: quickDispatchPreset.ward_name,
        action_type: quickDispatchPreset.action_type,
        priority: quickDispatchPreset.priority,
        reason: quickDispatchPreset.reason,
        required_resources: quickDispatchPreset.required_resources,
        related_hazard: quickDispatchPreset.related_hazard,
        risk_score: quickDispatchPreset.risk_score,
        authorized_by: quickDispatchAuthority || 'Municipal Incident Commander',
        initial_status: 'in_progress',
        force: force,
      };

      const res = await ClimateShieldAPI.quickDispatch(payload);
      if (res?.action) {
        setActionsList((prev) => [res.action, ...prev]);
        showToast(`Dispatched to field: ${res.action.action_id} in ${res.action.ward_name} (${res.action.action_type})`);
        setIsQuickDispatchModalOpen(false);
        setQuickDispatchPreset(null);
        fetchActionCentreData();
      }
    } catch (err) {
      console.error('Quick dispatch execution failed:', err);
      setQuickDispatchError(err.message || 'Quick dispatch failed.');
    } finally {
      setIsSubmittingDispatch(false);
    }
  };

  // Open Global Audit Trail Modal
  const handleOpenGlobalAudit = async () => {
    setIsAuditModalOpen(true);
    setIsLoadingAudit(true);
    try {
      const res = await ClimateShieldAPI.getGlobalActionAuditTrail(100);
      if (res?.audit_trail) {
        setGlobalAuditEvents(res.audit_trail);
      }
    } catch (err) {
      console.warn('Failed to load global audit trail:', err);
    } finally {
      setIsLoadingAudit(false);
    }
  };

  // Export CSV
  const handleExportCSV = () => {
    if (actionsList.length === 0) {
      alert('No active operations to export.');
      return;
    }
    const headers = ['Action ID', 'Ward Name', 'Ward ID', 'Type', 'Priority', 'Status', 'Risk Score', 'Verification Status', 'Reason'];
    const rows = actionsList.map((a) => [
      a.action_id,
      `"${a.ward_name || ''}"`,
      a.ward_id || '',
      a.action_type || '',
      a.priority || '',
      a.status || '',
      a.risk_score || '',
      a.latest_verification?.overall_status || 'NOT_VERIFIED',
      `"${(a.reason || '').replace(/"/g, '""')}"`,
    ]);
    const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `ClimateShield_Field_Operations_${Date.now()}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Filter Operations List
  const filteredOps = useMemo(() => {
    return actionsList.filter((op) => {
      const statusNorm = (op.status || '').toLowerCase();
      const priorityNorm = (op.priority || '').toLowerCase();
      const verifNorm = (op.latest_verification?.overall_status || 'NOT_VERIFIED').toUpperCase();

      const matchesStatus =
        filterStatus === 'All' ||
        statusNorm === filterStatus.toLowerCase();

      const matchesPriority =
        filterPriority === 'All' ||
        priorityNorm === filterPriority.toLowerCase();

      const matchesVerification =
        filterVerification === 'All' ||
        verifNorm === filterVerification.toUpperCase();

      const q = searchFilter.toLowerCase();
      const matchesSearch =
        !searchFilter ||
        (op.ward_name && op.ward_name.toLowerCase().includes(q)) ||
        (op.ward_id && op.ward_id.toLowerCase().includes(q)) ||
        (op.action_id && op.action_id.toLowerCase().includes(q)) ||
        (op.action_type && op.action_type.toLowerCase().includes(q)) ||
        (op.reason && op.reason.toLowerCase().includes(q));

      return matchesStatus && matchesPriority && matchesVerification && matchesSearch;
    });
  }, [actionsList, filterStatus, filterPriority, filterVerification, searchFilter]);

  // Real backend metrics calculation
  const backendMetrics = dashboardData?.metrics || {};
  const activeDeploymentsCount = backendMetrics.active_deployments ?? actionsList.filter((a) => ['in_progress', 'approved'].includes(a.status)).length;
  const criticalCount = backendMetrics.critical_interventions ?? actionsList.filter((a) => (a.priority || '').toLowerCase() === 'critical').length;
  const proposedCount = backendMetrics.pending_sign_off ?? actionsList.filter((a) => a.status === 'proposed').length;
  const completedCount = backendMetrics.completed_operations ?? actionsList.filter((a) => a.status === 'completed').length;
  const totalActionsCount = backendMetrics.total_registered_actions ?? actionsList.length;

  // Real Priority Approval Candidates from Backend Data
  const priorityApprovalCandidates = useMemo(() => {
    const list = dashboardData?.prioritized_actions || actionsList;
    return list.filter((a) => ['proposed', 'blocked'].includes(a.status)).slice(0, 3);
  }, [dashboardData, actionsList]);

  return (
    <div className="space-y-6">
      
      {/* Toast Notification */}
      {notification && (
        <div
          className={`fixed bottom-5 right-5 z-50 px-4 py-3 rounded-xl shadow-xl border text-xs font-mono flex items-center gap-2.5 animate-in slide-in-from-bottom-2 ${
            notification.isError
              ? 'bg-red-50 text-red-900 border-red-300'
              : 'bg-emerald-50 text-emerald-950 border-emerald-300'
          }`}
        >
          <span className="material-symbols-outlined text-[18px]">
            {notification.isError ? 'error' : 'check_circle'}
          </span>
          <span>{notification.message}</span>
        </div>
      )}

      {/* Header & Controls Strip */}
      <section className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-outline-variant">
        <div>
          <nav className="flex items-center gap-2 font-mono text-[10px] text-outline mb-1 uppercase tracking-wider">
            <span>AMC Command Center</span>
            <span className="material-symbols-outlined text-[12px]">chevron_right</span>
            <span>ClimateShield</span>
            <span className="material-symbols-outlined text-[12px]">chevron_right</span>
            <span className="text-primary font-bold">Action Centre</span>
          </nav>
          <div className="flex items-center gap-3">
            <h1 className="text-headline-md font-headline-md text-primary tracking-tight font-bold">
              Action Centre & Field Operations Command
            </h1>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[#ECFDF5] border border-[#A7F3D0] text-[#065F46] font-mono text-[10px] font-semibold">
              <span className="w-1.5 h-1.5 rounded-full bg-[#059669] animate-pulse"></span>
              LIVE OPS SYNC
            </span>
          </div>
        </div>

        {/* Header Action Buttons */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <button
            onClick={handleOpenGlobalAudit}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-surface-container-lowest border border-outline-variant text-on-surface text-label-md font-label-md hover:bg-surface-container-low shadow-xs active:scale-[0.98] transition-all cursor-pointer"
            title="Inspect relational municipal decision and dispatch audit log"
          >
            <span className="material-symbols-outlined text-[18px] text-outline">history_edu</span>
            <span>Audit History Log</span>
          </button>

          <button
            onClick={handleExportCSV}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-surface-container-lowest border border-outline-variant text-on-surface text-label-md font-label-md hover:bg-surface-container-low shadow-xs active:scale-[0.98] transition-all cursor-pointer"
            title="Download CSV log of all operational records"
          >
            <span className="material-symbols-outlined text-[18px] text-outline">download</span>
            <span>Export Ops Log</span>
          </button>

          <button
            onClick={onOpenDeployModal}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary-container text-white text-label-md font-label-md hover:bg-[#1B5742] active:scale-[0.98] shadow-sm transition-all cursor-pointer font-semibold"
          >
            <span className="material-symbols-outlined text-[18px]">add</span>
            <span>Deploy Custom Action</span>
          </button>
        </div>
      </section>

      {/* Error Alert */}
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-xl flex items-center justify-between text-xs text-error font-mono">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px]">error</span>
            <span>{error}</span>
          </div>
          <button
            onClick={fetchActionCentreData}
            className="px-3 py-1 bg-white border border-red-300 rounded font-bold hover:bg-red-50 cursor-pointer"
          >
            Retry Connection
          </button>
        </div>
      )}

      {/* Real Backend Dashboard Metrics */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
        <KPICard
          title="Active Deployments"
          icon="near_me"
          value={loading ? '...' : activeDeploymentsCount}
          unit="In Field"
          subtitle="Approved & in-progress operations"
          progress={totalActionsCount > 0 ? Math.round((activeDeploymentsCount / totalActionsCount) * 100) : 0}
          isSuccess={true}
        />

        <KPICard
          title="Critical Interventions"
          icon="warning"
          value={loading ? '...' : criticalCount}
          unit="Critical"
          subtitle="Priority tier: Critical risk response"
          progress={totalActionsCount > 0 ? Math.round((criticalCount / totalActionsCount) * 100) : 0}
          isDanger={criticalCount > 0}
        />

        <KPICard
          title="Pending Sign-Off"
          icon="pending_actions"
          value={loading ? '...' : proposedCount}
          unit="Proposed"
          subtitle="Awaiting Commissioner sign-off"
          progress={totalActionsCount > 0 ? Math.round((proposedCount / totalActionsCount) * 100) : 0}
          isWarning={proposedCount > 0}
        />

        <KPICard
          title="Completed Operations"
          icon="task_alt"
          value={loading ? '...' : completedCount}
          unit="Resolved"
          subtitle="Executed and closed dispatch cycles"
          progress={totalActionsCount > 0 ? Math.round((completedCount / totalActionsCount) * 100) : 0}
          isInfo={true}
        />

        <KPICard
          title="Total Registered Actions"
          icon="flag"
          value={loading ? '...' : totalActionsCount}
          unit="Total"
          subtitle="Decision Support Action Queue"
          progress={100}
        />
      </section>

      {/* Main 2-Column Grid: Operations Table (8 Cols) + Right Desk (4 Cols) */}
      <section className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        
        {/* Left 8 Cols: Field Operations Dispatch Table */}
        <div className="xl:col-span-8 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-xs overflow-hidden">
          
          {/* Table Filters & Search Bar */}
          <div className="p-3.5 border-b border-outline-variant bg-[#F8FAF8] space-y-3">
            
            {/* Top Row: Search Input & Filter Counters */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="relative flex-1 max-w-sm">
                <span className="material-symbols-outlined absolute left-2.5 top-2 text-outline text-[16px]">search</span>
                <input
                  type="text"
                  placeholder="Search by Ward, ID, Action Type, Reason..."
                  value={searchFilter}
                  onChange={(e) => setSearchFilter(e.target.value)}
                  className="w-full h-8 pl-8 pr-3 text-xs bg-white border border-outline-variant rounded-lg focus:outline-none focus:border-primary font-sans"
                />
              </div>

              {/* Priority & Verification Dropdowns */}
              <div className="flex items-center gap-2 flex-wrap">
                <select
                  value={filterPriority}
                  onChange={(e) => setFilterPriority(e.target.value)}
                  className="h-8 px-2.5 bg-white border border-outline-variant rounded-lg font-mono text-xs focus:outline-none focus:border-primary"
                  title="Filter by priority tier"
                >
                  <option value="All">Priority: All</option>
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>

                <select
                  value={filterVerification}
                  onChange={(e) => setFilterVerification(e.target.value)}
                  className="h-8 px-2.5 bg-white border border-outline-variant rounded-lg font-mono text-xs focus:outline-none focus:border-primary"
                  title="Filter by evidence verification state"
                >
                  <option value="All">Verification: All</option>
                  <option value="VERIFIED">Verified</option>
                  <option value="FAILED">Failed</option>
                  <option value="UNABLE_TO_VERIFY">Unable to Verify</option>
                  <option value="NOT_VERIFIED">Not Verified</option>
                </select>

                {(filterStatus !== 'All' || filterPriority !== 'All' || filterVerification !== 'All' || searchFilter) && (
                  <button
                    onClick={() => {
                      setFilterStatus('All');
                      setFilterPriority('All');
                      setFilterVerification('All');
                      setSearchFilter('');
                    }}
                    className="h-8 px-2.5 text-xs font-mono text-red-700 hover:bg-red-50 border border-red-200 rounded-lg cursor-pointer"
                    title="Reset all filters"
                  >
                    Clear Filters
                  </button>
                )}
              </div>
            </div>

            {/* Bottom Row: Status Filter Tabs */}
            <div className="flex items-center gap-1 bg-surface-bright p-1 rounded-lg border border-slate-200 overflow-x-auto">
              {[
                { key: 'All', label: 'All' },
                { key: 'proposed', label: 'Proposed' },
                { key: 'approved', label: 'Approved' },
                { key: 'in_progress', label: 'In Progress' },
                { key: 'blocked', label: 'Blocked / Hold' },
                { key: 'changes_requested', label: 'Changes Requested' },
                { key: 'completed', label: 'Completed' },
                { key: 'rejected', label: 'Rejected' },
              ].map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setFilterStatus(tab.key)}
                  className={`px-3 py-1 rounded-md text-xs font-mono transition-colors cursor-pointer shrink-0 ${
                    filterStatus === tab.key
                      ? 'bg-primary-container text-white font-semibold shadow-xs'
                      : 'text-on-surface-variant hover:bg-slate-100'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

          </div>

          {/* Operations Table Content */}
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-outline-variant bg-[#F8FAF8] text-[10px] uppercase font-mono text-outline">
                  <th className="py-2.5 px-3">Operation & Ward</th>
                  <th className="py-2.5 px-3">Type & Scope</th>
                  <th className="py-2.5 px-3">Priority & Risk</th>
                  <th className="py-2.5 px-2 text-center">Verification</th>
                  <th className="py-2.5 px-2 text-center">Status</th>
                  <th className="py-2.5 px-3 text-center">Decision & Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant">
                
                {loading && actionsList.length === 0 && (
                  <tr>
                    <td colSpan="6" className="py-12 text-center text-outline font-mono text-xs">
                      <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                      Connecting to Municipal Command Store...
                    </td>
                  </tr>
                )}

                {!loading && filteredOps.length === 0 && (
                  <tr>
                    <td colSpan="6" className="py-10 text-center text-outline font-mono text-xs">
                      <div className="material-symbols-outlined text-[32px] text-outline mb-1">search_off</div>
                      <div>No active operations found matching the selected filter criteria.</div>
                    </td>
                  </tr>
                )}

                {filteredOps.map((op) => {
                  const status = (op.status || 'proposed').toLowerCase();
                  const priority = (op.priority || 'medium').toLowerCase();
                  const verifStatus = op.latest_verification?.overall_status || 'NOT_VERIFIED';

                  return (
                    <tr
                      key={op.action_id}
                      onClick={() => handleReviewAction(op)}
                      className="hover:bg-[#F8FAF8] transition-colors cursor-pointer group"
                      title="Click row to open comprehensive review modal"
                    >
                      {/* Operation & Ward */}
                      <td className="py-3 px-3">
                        <div className="font-bold text-on-surface text-xs group-hover:text-primary transition-colors">
                          {op.ward_name} Ward
                        </div>
                        <div className="font-mono text-[10px] text-outline flex items-center gap-1.5 mt-0.5">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleReviewAction(op);
                            }}
                            className="font-semibold text-primary hover:underline cursor-pointer"
                          >
                            {op.action_id}
                          </button>
                          <span>•</span>
                          <span>{op.ward_id || 'AMC'}</span>
                        </div>
                      </td>

                      {/* Type & Scope */}
                      <td className="py-3 px-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-slate-100 text-slate-800 border uppercase">
                          {(op.action_type || 'intervene').replace(/_/g, ' ')}
                        </span>
                        <div
                          className="font-mono text-[10px] text-outline mt-1 max-w-[200px] truncate"
                          title={op.reason}
                        >
                          {op.reason || 'Advisory recommendation'}
                        </div>
                      </td>

                      {/* Priority & Risk */}
                      <td className="py-3 px-3">
                        <span
                          className={`px-2 py-0.5 rounded-full font-mono text-[10px] font-bold uppercase ${
                            priority === 'critical'
                              ? 'bg-red-100 text-red-800'
                              : priority === 'high'
                              ? 'bg-amber-100 text-amber-800'
                              : 'bg-slate-100 text-slate-800'
                          }`}
                        >
                          {priority}
                        </span>
                        <div className="text-[10px] font-mono text-outline mt-0.5">
                          Risk: {op.risk_score ? Math.round(op.risk_score) : 50}/100
                        </div>
                      </td>

                      {/* Verification Status */}
                      <td className="py-3 px-2 text-center">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleReviewAction(op, 'verification');
                          }}
                          className={`px-2 py-0.5 rounded text-[9px] font-mono font-bold uppercase transition-transform hover:scale-105 cursor-pointer ${
                            verifStatus === 'VERIFIED'
                              ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                              : verifStatus === 'FAILED'
                              ? 'bg-red-100 text-red-800 border border-red-300'
                              : verifStatus === 'UNABLE_TO_VERIFY'
                              ? 'bg-amber-100 text-amber-800 border border-amber-300'
                              : 'bg-slate-100 text-slate-700 border border-slate-300'
                          }`}
                          title="Click to view evidence verification checklist"
                        >
                          {verifStatus.replace(/_/g, ' ')}
                        </button>
                      </td>

                      {/* Status */}
                      <td className="py-3 px-2 text-center">
                        <span
                          className={`px-2 py-0.5 rounded-full font-mono text-[10px] font-bold inline-flex items-center gap-1 uppercase ${
                            status === 'proposed'
                              ? 'bg-amber-50 text-amber-800 border border-amber-200'
                              : status === 'approved'
                              ? 'bg-blue-50 text-blue-800 border border-blue-200'
                              : status === 'in_progress'
                              ? 'bg-emerald-50 text-emerald-800 border border-emerald-300'
                              : status === 'blocked'
                              ? 'bg-red-50 text-red-800 border border-red-300'
                              : status === 'changes_requested'
                              ? 'bg-purple-50 text-purple-800 border border-purple-300'
                              : status === 'rejected'
                              ? 'bg-rose-50 text-rose-800 border border-rose-300'
                              : 'bg-slate-100 text-slate-800'
                          }`}
                        >
                          {status === 'in_progress' && (
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-ping"></span>
                          )}
                          {status.replace(/_/g, ' ')}
                        </span>
                      </td>

                      {/* Context-Sensitive Actions */}
                      <td className="py-3 px-3 text-center" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-center gap-1.5 flex-wrap">
                          
                          {/* Review Action */}
                          <button
                            type="button"
                            onClick={() => handleReviewAction(op)}
                            className="px-2 py-1 rounded bg-surface-container-low text-primary border border-outline-variant font-mono text-[10px] font-semibold hover:bg-surface-container transition-all cursor-pointer inline-flex items-center gap-0.5"
                            title="Inspect details & verification"
                          >
                            <span className="material-symbols-outlined text-[12px]">visibility</span>
                            <span>Review</span>
                          </button>

                          {/* Verify Shortcut */}
                          <button
                            type="button"
                            onClick={() => handleReviewAction(op, 'verification')}
                            className="px-2 py-1 rounded bg-slate-100 text-slate-800 border border-slate-300 font-mono text-[10px] font-semibold hover:bg-slate-200 transition-all cursor-pointer inline-flex items-center gap-0.5"
                            title="Open evidence audit checklist"
                          >
                            <span className="material-symbols-outlined text-[12px]">fact_check</span>
                            <span>Verify</span>
                          </button>

                          {/* PROPOSED: Approve, Reject, Hold */}
                          {status === 'proposed' && (
                            <>
                              <button
                                type="button"
                                onClick={() => handleDirectTransition(op, 'approve')}
                                disabled={isUpdating || verifStatus === 'FAILED'}
                                className={`px-2.5 py-1 rounded font-mono text-[10px] font-bold transition-colors ${
                                  verifStatus === 'FAILED'
                                    ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
                                    : 'bg-blue-600 text-white hover:bg-blue-700 cursor-pointer'
                                }`}
                                title={
                                  verifStatus === 'FAILED'
                                    ? 'Cannot approve: mandatory checks failed'
                                    : 'Approve intervention'
                                }
                              >
                                Approve
                              </button>

                              <button
                                type="button"
                                onClick={() => openDecisionModal(op, 'reject')}
                                className="px-2 py-1 rounded bg-rose-50 text-rose-800 border border-rose-300 font-mono text-[10px] font-bold hover:bg-rose-100 transition-colors cursor-pointer"
                                title="Reject intervention with mandatory reason"
                              >
                                Reject
                              </button>

                              <button
                                type="button"
                                onClick={() => openDecisionModal(op, 'block')}
                                className="px-2 py-1 rounded bg-amber-50 text-amber-800 border border-amber-300 font-mono text-[10px] font-bold hover:bg-amber-100 transition-colors cursor-pointer"
                                title="Hold/block operation"
                              >
                                Hold
                              </button>
                            </>
                          )}

                          {/* APPROVED: Deploy, Hold */}
                          {status === 'approved' && (
                            <>
                              <button
                                type="button"
                                onClick={() => handleDirectTransition(op, 'deploy')}
                                disabled={isUpdating}
                                className="px-2.5 py-1 rounded bg-primary text-white font-mono text-[10px] font-bold hover:bg-[#1B5742] transition-colors cursor-pointer"
                                title="Mobilize and deploy field crew"
                              >
                                Deploy
                              </button>

                              <button
                                type="button"
                                onClick={() => openDecisionModal(op, 'block')}
                                className="px-2 py-1 rounded bg-amber-50 text-amber-800 border border-amber-300 font-mono text-[10px] font-bold hover:bg-amber-100 transition-colors cursor-pointer"
                                title="Hold before dispatch"
                              >
                                Hold
                              </button>
                            </>
                          )}

                          {/* IN_PROGRESS: Complete, Hold */}
                          {status === 'in_progress' && (
                            <>
                              <button
                                type="button"
                                onClick={() => handleDirectTransition(op, 'complete')}
                                disabled={isUpdating}
                                className="px-2.5 py-1 rounded bg-[#059669] text-white font-mono text-[10px] font-bold hover:bg-[#047857] transition-colors cursor-pointer"
                                title="Mark operation resolved"
                              >
                                Complete
                              </button>

                              <button
                                type="button"
                                onClick={() => openDecisionModal(op, 'block')}
                                className="px-2 py-1 rounded bg-amber-50 text-amber-800 border border-amber-300 font-mono text-[10px] font-bold hover:bg-amber-100 transition-colors cursor-pointer"
                              >
                                Hold
                              </button>
                            </>
                          )}

                          {/* BLOCKED: Unblock, Reject */}
                          {status === 'blocked' && (
                            <>
                              <button
                                type="button"
                                onClick={() => handleDirectTransition(op, 'unblock')}
                                disabled={isUpdating}
                                className="px-2.5 py-1 rounded bg-blue-600 text-white font-mono text-[10px] font-bold hover:bg-blue-700 transition-colors cursor-pointer"
                                title="Unblock operation"
                              >
                                Unblock
                              </button>

                              <button
                                type="button"
                                onClick={() => openDecisionModal(op, 'reject')}
                                className="px-2 py-1 rounded bg-rose-50 text-rose-800 border border-rose-300 font-mono text-[10px] font-bold hover:bg-rose-100 transition-colors cursor-pointer"
                              >
                                Reject
                              </button>
                            </>
                          )}

                          {/* CHANGES_REQUESTED: Resubmit */}
                          {status === 'changes_requested' && (
                            <button
                              type="button"
                              onClick={() => handleDirectTransition(op, 'unblock')}
                              disabled={isUpdating}
                              className="px-2.5 py-1 rounded bg-primary text-white font-mono text-[10px] font-bold hover:bg-[#1B5742] transition-colors cursor-pointer"
                              title="Resubmit revised action"
                            >
                              Resubmit
                            </button>
                          )}

                          {/* COMPLETED / REJECTED: Resolved */}
                          {status === 'completed' && (
                            <span className="font-mono text-[10px] text-emerald-700 font-bold">Resolved</span>
                          )}
                          {status === 'rejected' && (
                            <span className="font-mono text-[10px] text-rose-700 font-bold">Rejected</span>
                          )}

                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

        </div>

        {/* Right 4 Cols: Priority Approval Panel & Quick Dispatch Triggers */}
        <div className="xl:col-span-4 space-y-4">
          
          {/* Priority Approval Panel (Real Backend Data) */}
          <div className="bg-surface-container-lowest border-2 border-red-200 rounded-xl p-4 shadow-xs bg-gradient-to-br from-white to-red-50/30">
            <div className="flex items-start justify-between pb-2 border-b border-red-100">
              <div className="flex items-center gap-2 text-error">
                <span className="material-symbols-outlined text-[20px]">warning</span>
                <h3 className="font-title-sm text-title-sm font-bold">Priority Approval Desk</h3>
              </div>
              <span className="px-2 py-0.5 rounded bg-error text-white text-[10px] font-mono font-bold">
                COMMAND DESK
              </span>
            </div>

            <div className="mt-3 space-y-3 text-xs">
              {priorityApprovalCandidates.length === 0 ? (
                <div className="p-4 text-center text-outline font-mono text-[11px] bg-white rounded-lg border border-slate-100">
                  <span className="material-symbols-outlined text-[24px] text-emerald-600 block mb-1">verified</span>
                  No urgent pending approvals. All high-risk actions cleared.
                </div>
              ) : (
                priorityApprovalCandidates.map((b) => (
                  <div key={b.action_id} className="p-3 rounded-lg border border-red-200 bg-white space-y-2 shadow-2xs">
                    <div className="flex items-center justify-between font-bold text-on-surface">
                      <span className="text-xs">{b.ward_name} ({b.action_id})</span>
                      <span
                        className={`font-mono uppercase text-[9px] px-1.5 py-0.2 rounded font-bold ${
                          b.status === 'blocked'
                            ? 'bg-red-100 text-red-800'
                            : 'bg-amber-100 text-amber-800'
                        }`}
                      >
                        {b.status === 'blocked' ? 'BLOCKED' : b.priority}
                      </span>
                    </div>

                    <p className="text-on-surface-variant text-[11px] leading-snug line-clamp-2">
                      {b.reason}
                    </p>

                    <div className="flex items-center justify-between pt-1 border-t border-slate-100 flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => handleReviewAction(b)}
                        className="text-outline hover:text-primary text-[10px] font-mono font-semibold inline-flex items-center gap-0.5 cursor-pointer hover:underline"
                        title="Review full intervention details"
                      >
                        <span className="material-symbols-outlined text-[13px]">visibility</span>
                        <span>Review</span>
                      </button>

                      <div className="flex items-center gap-1.5">
                        {b.status === 'blocked' ? (
                          <button
                            type="button"
                            onClick={() => handleDirectTransition(b, 'unblock')}
                            disabled={isUpdating}
                            className="px-2.5 py-1 rounded bg-blue-600 text-white font-mono text-[10px] font-bold hover:bg-blue-700 transition-colors cursor-pointer"
                          >
                            Unblock
                          </button>
                        ) : (
                          <>
                            <button
                              type="button"
                              onClick={() => handleDirectTransition(b, 'approve')}
                              disabled={isUpdating}
                              className="px-2.5 py-1 rounded bg-blue-600 text-white font-mono text-[10px] font-bold hover:bg-blue-700 transition-colors cursor-pointer"
                            >
                              Authorize →
                            </button>
                            <button
                              type="button"
                              onClick={() => openDecisionModal(b, 'reject')}
                              className="px-2 py-1 rounded border border-rose-300 text-rose-800 font-mono text-[10px] font-bold hover:bg-rose-50 cursor-pointer"
                            >
                              Reject
                            </button>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Quick Dispatch Triggers (With Confirmation & Duplicate Prevention) */}
          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="font-title-sm text-title-sm font-bold text-primary flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[18px]">bolt</span>
                <span>Quick Dispatch Triggers</span>
              </h4>
              <span className="text-[10px] font-mono text-outline font-semibold">PERSISTENT OPS</span>
            </div>

            <p className="text-[11px] text-outline font-mono leading-relaxed">
              Dispatches authenticated emergency operations directly into the field store with duplicate prevention:
            </p>

            <div className="space-y-2 text-xs">
              <button
                type="button"
                onClick={() => triggerQuickDispatchModal('tankers')}
                className="w-full p-2.5 rounded-lg bg-surface-bright hover:bg-surface-container-low border border-slate-200 flex items-center justify-between transition-colors text-left cursor-pointer group"
              >
                <div>
                  <div className="font-semibold text-primary group-hover:underline">Deploy 6 Water Tankers</div>
                  <div className="text-[10px] font-mono text-outline">Danilimda informal settlements (₹72k)</div>
                </div>
                <span className="material-symbols-outlined text-[18px] text-primary">send</span>
              </button>

              <button
                type="button"
                onClick={() => triggerQuickDispatchModal('ors')}
                className="w-full p-2.5 rounded-lg bg-surface-bright hover:bg-surface-container-low border border-slate-200 flex items-center justify-between transition-colors text-left cursor-pointer group"
              >
                <div>
                  <div className="font-semibold text-primary group-hover:underline">Activate UHC ORS Booths</div>
                  <div className="text-[10px] font-mono text-outline">Gomtipur health centres (₹50k)</div>
                </div>
                <span className="material-symbols-outlined text-[18px] text-primary">local_hospital</span>
              </button>

              <button
                type="button"
                onClick={() => triggerQuickDispatchModal('misting')}
                className="w-full p-2.5 rounded-lg bg-surface-bright hover:bg-surface-container-low border border-slate-200 flex items-center justify-between transition-colors text-left cursor-pointer group"
              >
                <div>
                  <div className="font-semibold text-primary group-hover:underline">Deploy High-Pressure Misting</div>
                  <div className="text-[10px] font-mono text-outline">Kalupur AMTS transit interchange (₹30k)</div>
                </div>
                <span className="material-symbols-outlined text-[18px] text-primary">air</span>
              </button>
            </div>
          </div>

        </div>

      </section>

      {/* ========================================================================= */}
      {/* DECISION MODAL (Reject, Hold/Block, Request Changes)                      */}
      {/* ========================================================================= */}
      {isDecisionModalOpen && decisionTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
          <div className="bg-white rounded-2xl border border-outline-variant shadow-2xl w-full max-w-lg p-6 space-y-4 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b pb-3">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-[22px]">gavel</span>
                <h3 className="font-bold text-sm text-primary uppercase font-mono">
                  Confirm {decisionType === 'reject' ? 'Rejection' : decisionType === 'block' ? 'Hold / Blocker' : 'Changes Request'}
                </h3>
              </div>
              <button
                onClick={() => setIsDecisionModalOpen(false)}
                className="text-outline hover:text-on-surface"
              >
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>

            <div className="text-xs space-y-1">
              <div className="font-bold text-on-surface">Target Operation: {decisionTarget.action_id}</div>
              <div className="text-outline font-mono">{decisionTarget.ward_name} ({decisionTarget.ward_id}) • {decisionTarget.action_type}</div>
            </div>

            {decisionModalError && (
              <div className="p-2.5 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800 font-mono">
                {decisionModalError}
              </div>
            )}

            <div className="space-y-3 text-xs">
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
                  Operational Justification Reason *
                </label>
                <textarea
                  rows={3}
                  placeholder={`Mandatory reason for ${decisionType} (e.g. duplicate deployment, resource shortage, ground verification finding)...`}
                  value={decisionReason}
                  onChange={(e) => setDecisionReason(e.target.value)}
                  className="w-full p-2.5 text-xs bg-slate-50 border border-outline-variant rounded-lg font-mono focus:outline-none focus:border-primary"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t">
              <button
                onClick={() => setIsDecisionModalOpen(false)}
                className="px-4 py-2 rounded-lg border border-outline-variant text-xs font-mono font-bold hover:bg-slate-50 cursor-pointer"
              >
                Cancel
              </button>
              <button
                disabled={isSubmittingDecision}
                onClick={handleConfirmDecision}
                className="px-4 py-2 rounded-lg bg-primary text-white text-xs font-mono font-bold hover:bg-[#1B5742] cursor-pointer disabled:opacity-50"
              >
                {isSubmittingDecision ? 'Submitting...' : 'Confirm Decision & Persist'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* QUICK DISPATCH CONFIRMATION MODAL                                         */}
      {/* ========================================================================= */}
      {isQuickDispatchModalOpen && quickDispatchPreset && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
          <div className="bg-white rounded-2xl border border-outline-variant shadow-2xl w-full max-w-lg p-6 space-y-4 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b pb-3">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-[22px]">send</span>
                <h3 className="font-bold text-sm text-primary uppercase font-mono">
                  Confirm Emergency Operational Dispatch
                </h3>
              </div>
              <button
                onClick={() => setIsQuickDispatchModalOpen(false)}
                className="text-outline hover:text-on-surface"
              >
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>

            <div className="p-3 bg-[#F8FAF8] rounded-xl border space-y-2 text-xs font-mono">
              <div className="font-bold text-sm text-on-surface">{quickDispatchPreset.title}</div>
              <div className="grid grid-cols-2 gap-2 text-[11px] text-outline">
                <div>Target Ward: <strong className="text-on-surface">{quickDispatchPreset.ward_name} ({quickDispatchPreset.ward_id})</strong></div>
                <div>Priority: <strong className="text-red-700 uppercase">{quickDispatchPreset.priority}</strong></div>
                <div>Budget: <strong className="text-on-surface">₹{quickDispatchPreset.required_resources.cost_inr.toLocaleString()}</strong></div>
                <div>Crew: <strong className="text-on-surface">{quickDispatchPreset.required_resources.crew_required} Members</strong></div>
              </div>
              <p className="text-[11px] text-on-surface-variant font-sans pt-1 border-t">{quickDispatchPreset.reason}</p>
            </div>

            {quickDispatchPreset.existingDuplicate && (
              <div className="p-3 bg-amber-50 border border-amber-300 rounded-xl text-xs font-mono text-amber-900 space-y-1">
                <div className="font-bold flex items-center gap-1.5 text-amber-800">
                  <span className="material-symbols-outlined text-[16px]">warning</span>
                  <span>Duplicate Dispatch Detected</span>
                </div>
                <p className="text-[11px]">
                  An active operation of this type ({quickDispatchPreset.existingDuplicate.action_id}) is already{' '}
                  <strong className="uppercase">{quickDispatchPreset.existingDuplicate.status}</strong> in this ward.
                </p>
              </div>
            )}

            {quickDispatchError && (
              <div className="p-2.5 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800 font-mono">
                {quickDispatchError}
              </div>
            )}

            <div className="text-xs space-y-2">
              <label className="block text-[10px] font-mono uppercase text-outline font-bold">
                Authorizing Incident Official *
              </label>
              <select
                value={quickDispatchAuthority}
                onChange={(e) => setQuickDispatchAuthority(e.target.value)}
                className="w-full h-8 px-2.5 bg-white border border-outline-variant rounded-lg font-mono text-xs focus:outline-none focus:border-primary"
              >
                <option value="Municipal Incident Commander">Municipal Incident Commander</option>
                <option value="Municipal Commissioner (AMC)">Municipal Commissioner (AMC)</option>
                <option value="Disaster Management Authority">Disaster Management Authority</option>
                <option value="Chief Medical Officer">Chief Medical Officer</option>
              </select>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t">
              <button
                onClick={() => setIsQuickDispatchModalOpen(false)}
                className="px-4 py-2 rounded-lg border border-outline-variant text-xs font-mono font-bold hover:bg-slate-50 cursor-pointer"
              >
                Cancel
              </button>

              {quickDispatchPreset.existingDuplicate ? (
                <button
                  disabled={isSubmittingDispatch}
                  onClick={() => handleConfirmQuickDispatch(true)}
                  className="px-4 py-2 rounded-lg bg-amber-600 text-white text-xs font-mono font-bold hover:bg-amber-700 cursor-pointer"
                  title="Override duplicate prevention and mobilize secondary team"
                >
                  {isSubmittingDispatch ? 'Dispatching...' : 'Override & Dispatch Force'}
                </button>
              ) : (
                <button
                  disabled={isSubmittingDispatch}
                  onClick={() => handleConfirmQuickDispatch(false)}
                  className="px-4 py-2 rounded-lg bg-primary text-white text-xs font-mono font-bold hover:bg-[#1B5742] cursor-pointer"
                >
                  {isSubmittingDispatch ? 'Dispatching...' : 'Confirm Field Dispatch'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* GLOBAL AUDIT TRAIL MODAL                                                  */}
      {/* ========================================================================= */}
      {isAuditModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs">
          <div className="bg-white rounded-2xl border border-outline-variant shadow-2xl w-full max-w-4xl max-h-[85vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95">
            <div className="px-6 py-4 border-b flex items-center justify-between bg-[#F8FAF8]">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-primary text-[24px]">history_edu</span>
                <h3 className="font-bold text-sm text-primary uppercase font-mono">
                  Municipal Action Centre Audit Trail (SQLite Baseline)
                </h3>
              </div>
              <button
                onClick={() => setIsAuditModalOpen(false)}
                className="text-outline hover:text-on-surface"
              >
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>

            <div className="p-6 overflow-y-auto flex-1">
              {isLoadingAudit ? (
                <div className="p-12 text-center text-outline font-mono text-xs">
                  <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                  Querying immutable audit logs from SQLite...
                </div>
              ) : globalAuditEvents.length === 0 ? (
                <div className="p-8 text-center text-outline font-mono text-xs border rounded-xl">
                  No audit events recorded yet.
                </div>
              ) : (
                <div className="rounded-xl border border-outline-variant overflow-hidden">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="border-b bg-[#F8FAF8] text-[10px] uppercase font-mono text-outline">
                        <th className="py-2.5 px-3">Event Type</th>
                        <th className="py-2.5 px-3">Action ID</th>
                        <th className="py-2.5 px-3">Actor / Official</th>
                        <th className="py-2.5 px-3">Status Change</th>
                        <th className="py-2.5 px-3">Reason / Details</th>
                        <th className="py-2.5 px-3 text-right">Timestamp</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y font-mono text-[11px]">
                      {globalAuditEvents.map((ev) => (
                        <tr key={ev.event_id} className="hover:bg-slate-50">
                          <td className="py-2.5 px-3 font-bold text-primary">
                            <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-800 border text-[9px]">
                              {ev.event_type}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 font-bold">{ev.action_id}</td>
                          <td className="py-2.5 px-3 text-on-surface">{ev.actor}</td>
                          <td className="py-2.5 px-3 text-[10px]">
                            {ev.old_status && ev.new_status
                              ? `${ev.old_status} → ${ev.new_status}`
                              : ev.new_status || '—'}
                          </td>
                          <td className="py-2.5 px-3 font-sans text-xs max-w-xs truncate" title={ev.reason}>
                            {ev.reason || '—'}
                          </td>
                          <td className="py-2.5 px-3 text-right text-outline text-[10px]">
                            {new Date(ev.timestamp).toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="px-6 py-3 border-t bg-[#F8FAF8] flex justify-end">
              <button
                onClick={() => setIsAuditModalOpen(false)}
                className="px-4 py-1.5 rounded-lg border border-outline-variant font-mono text-xs font-bold hover:bg-slate-50 cursor-pointer"
              >
                Close Audit Log
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Intervention Review Detail Modal */}
      <InterventionDetailModal
        isOpen={isDetailModalOpen}
        action={selectedAction}
        initialTab={detailModalTab}
        onActionUpdated={(updated) => {
          setActionsList((prev) =>
            prev.map((a) => (a.action_id === updated.action_id ? updated : a))
          );
          ClimateShieldAPI.getActionCentreDashboard().then(setDashboardData).catch(() => {});
        }}
        onClose={() => {
          setIsDetailModalOpen(false);
          setSelectedAction(null);
        }}
      />

    </div>
  );
}
