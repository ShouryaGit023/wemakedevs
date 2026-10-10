import React, { useState, useEffect, useCallback } from 'react';
import KPICard from '../components/KPICard';
import { ClimateShieldAPI } from '../services/api';

export default function ActionCentrePage({ onOpenDeployModal }) {
  const [filterStatus, setFilterStatus] = useState('All');
  const [searchFilter, setSearchFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionsList, setActionsList] = useState([]);
  const [dashboardData, setDashboardData] = useState(null);
  const [isUpdating, setIsUpdating] = useState(false);
  const [notification, setNotification] = useState(null);

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

  const showToast = (message, isError = false) => {
    setNotification({ message, isError });
    setTimeout(() => setNotification(null), 4000);
  };

  const handleStatusTransition = async (actionId, newStatus) => {
    setIsUpdating(true);
    try {
      await ClimateShieldAPI.updateActionStatus(actionId, {
        new_status: newStatus,
        changed_by: 'Municipal Incident Commander',
        notes: `Operational transition to ${newStatus} authorized via Command Desk.`,
      });
      // Optimistically update local actions
      setActionsList((prev) =>
        prev.map((a) =>
          a.action_id === actionId
            ? {
                ...a,
                status: newStatus,
                status_history: [
                  ...(a.status_history || []),
                  {
                    status: newStatus,
                    timestamp: new Date().toISOString(),
                    changed_by: 'Municipal Incident Commander',
                  },
                ],
              }
            : a
        )
      );
      showToast(`Action ${actionId} successfully transitioned to "${newStatus}".`);
      // Background re-fetch to sync counts
      ClimateShieldAPI.getActionCentreDashboard().then(setDashboardData).catch(() => {});
    } catch (err) {
      console.error(`Status transition error for ${actionId}:`, err);
      showToast(`Failed to update status for ${actionId}: ${err.message}`, true);
    } finally {
      setIsUpdating(false);
    }
  };

  const handleQuickDispatch = async (type) => {
    setIsUpdating(true);
    try {
      let payload;
      if (type === 'tankers') {
        payload = {
          ward_id: 'W1',
          ward_name: 'Danilimda',
          action_type: 'water_tanker_dispatch',
          priority: 'critical',
          reason: 'Emergency water tanker dispatch to informal settlements in Danilimda.',
          required_resources: { cost_inr: 72000, crew_required: 12, water_required_l: 30000 },
          related_hazard: 'heat_and_water',
          risk_score: 85.0,
        };
      } else if (type === 'ors') {
        payload = {
          ward_id: 'W4',
          ward_name: 'Gomtipur',
          action_type: 'cooling_centre',
          priority: 'high',
          reason: 'Activate Urban Health Centres with ORS replenishment & hydration corners.',
          required_resources: { cost_inr: 50000, crew_required: 6, water_required_l: 2000 },
          related_hazard: 'heat',
          risk_score: 78.0,
        };
      } else {
        payload = {
          ward_id: 'W2',
          ward_name: 'Kalupur',
          action_type: 'drinking_water_point',
          priority: 'high',
          reason: 'Deploy high-pressure misting systems at AMTS transit interchange.',
          required_resources: { cost_inr: 30000, crew_required: 4, water_required_l: 4000 },
          related_hazard: 'heat',
          risk_score: 74.0,
        };
      }

      const res = await ClimateShieldAPI.createManualAction(payload);
      if (res && res.action) {
        setActionsList((prev) => [res.action, ...prev]);
        showToast(`Dispatched: ${payload.reason} (${res.action.action_id})`);
        fetchActionCentreData();
      }
    } catch (err) {
      console.error('Quick dispatch failed:', err);
      showToast(`Quick dispatch failed: ${err.message}`, true);
    } finally {
      setIsUpdating(false);
    }
  };

  const handleExportCSV = () => {
    if (actionsList.length === 0) {
      alert('No active operations to export.');
      return;
    }
    const headers = ['Action ID', 'Ward Name', 'Ward ID', 'Type', 'Priority', 'Status', 'Risk Score', 'Reason'];
    const rows = actionsList.map((a) => [
      a.action_id,
      `"${a.ward_name || ''}"`,
      a.ward_id || '',
      a.action_type || '',
      a.priority || '',
      a.status || '',
      a.risk_score || '',
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

  // Status mapping for filter
  const filteredOps = actionsList.filter((op) => {
    const statusNorm = (op.status || '').toLowerCase();
    const filterNorm = filterStatus.toLowerCase();
    const matchesStatus =
      filterStatus === 'All' ||
      statusNorm === filterNorm ||
      (filterStatus === 'In Progress' && statusNorm === 'in_progress');

    const matchesSearch =
      !searchFilter ||
      (op.ward_name && op.ward_name.toLowerCase().includes(searchFilter.toLowerCase())) ||
      (op.reason && op.reason.toLowerCase().includes(searchFilter.toLowerCase())) ||
      (op.action_type && op.action_type.toLowerCase().includes(searchFilter.toLowerCase())) ||
      (op.action_id && op.action_id.toLowerCase().includes(searchFilter.toLowerCase()));

    return matchesStatus && matchesSearch;
  });

  // Calculate live KPIs
  const summaryByStatus = dashboardData?.action_summary?.by_status || {};
  const activeDeploymentsCount = (summaryByStatus.in_progress || 0) + (summaryByStatus.approved || 0);
  const criticalCount = actionsList.filter((a) => (a.priority || '').toLowerCase() === 'critical').length;
  const proposedCount = summaryByStatus.proposed || actionsList.filter((a) => a.status === 'proposed').length;
  const completedCount = summaryByStatus.completed || actionsList.filter((a) => a.status === 'completed').length;
  const totalActionsCount = dashboardData?.action_summary?.total_actions || actionsList.length;

  // Find critical blocker or high-risk items requiring immediate decision
  const pendingBlockers = actionsList.filter(
    (a) => (a.priority || '').toLowerCase() === 'critical' || a.status === 'proposed'
  ).slice(0, 2);

  return (
    <div className="space-y-6">
      {/* Toast Notification */}
      {notification && (
        <div
          className={`fixed bottom-5 right-5 z-50 px-4 py-3 rounded-xl shadow-lg border text-xs font-mono flex items-center gap-2 animate-in slide-in-from-bottom-2 ${
            notification.isError
              ? 'bg-red-50 text-red-800 border-red-300'
              : 'bg-emerald-50 text-emerald-900 border-emerald-300'
          }`}
        >
          <span className="material-symbols-outlined text-[18px]">
            {notification.isError ? 'error' : 'check_circle'}
          </span>
          <span>{notification.message}</span>
        </div>
      )}

      {/* Header & Breadcrumbs & Actions */}
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
              Action Centre & Field Operations Tracker
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
            onClick={() => setFilterStatus(filterStatus === 'All' ? 'proposed' : 'All')}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-surface-container-lowest border border-outline-variant text-on-surface text-label-md font-label-md hover:bg-surface-container-low shadow-xs active:scale-[0.98] transition-all cursor-pointer"
          >
            <span className="material-symbols-outlined text-[18px] text-outline">filter_list</span>
            <span>{filterStatus === 'All' ? 'Filter: All' : `Filter: ${filterStatus}`}</span>
          </button>

          <button
            onClick={handleExportCSV}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-surface-container-lowest border border-outline-variant text-on-surface text-label-md font-label-md hover:bg-surface-container-low shadow-xs active:scale-[0.98] transition-all cursor-pointer"
            title="Download CSV file of all operational dispatches"
          >
            <span className="material-symbols-outlined text-[18px] text-outline">download</span>
            <span>Export Ops Log (CSV)</span>
          </button>

          <button
            onClick={onOpenDeployModal}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary-container text-white text-label-md font-label-md hover:bg-[#1B5742] active:scale-[0.98] shadow-sm transition-all cursor-pointer font-semibold"
          >
            <span className="material-symbols-outlined text-[18px]">add</span>
            <span>Deploy New Operation</span>
          </button>
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
            onClick={fetchActionCentreData}
            className="px-3 py-1 bg-white border border-red-300 rounded font-mono font-bold hover:bg-red-50 cursor-pointer"
          >
            Retry Connection
          </button>
        </div>
      )}

      {/* Operational KPI Summary Strip */}
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

      {/* Main 2-Column Section: Operations Table (8 Cols) + Escalation Desk (4 Cols) */}
      <section className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* Left 8 Cols: Field Operations Dispatch Table */}
        <div className="xl:col-span-8 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-xs overflow-hidden">
          {/* Table Controls */}
          <div className="p-3.5 border-b border-outline-variant flex flex-wrap items-center justify-between gap-3 bg-[#F8FAF8]">
            <div className="flex items-center gap-1 bg-surface-bright p-1 rounded-lg border border-slate-200 overflow-x-auto">
              {['All', 'proposed', 'approved', 'in_progress', 'completed'].map((tab) => {
                const label =
                  tab === 'All'
                    ? 'All'
                    : tab === 'proposed'
                    ? 'Proposed'
                    : tab === 'approved'
                    ? 'Approved'
                    : tab === 'in_progress'
                    ? 'In Progress'
                    : 'Completed';
                return (
                  <button
                    key={tab}
                    onClick={() => setFilterStatus(tab)}
                    className={`px-3 py-1 rounded-md text-xs transition-colors cursor-pointer shrink-0 ${
                      filterStatus === tab
                        ? 'bg-primary-container text-white font-semibold shadow-xs'
                        : 'text-on-surface-variant hover:bg-slate-100'
                    }`}
                  >
                    {label}
                  </button>
                );
              })}
            </div>

            <div className="relative">
              <span className="material-symbols-outlined absolute left-2.5 top-2 text-outline text-[16px]">search</span>
              <input
                type="text"
                placeholder="Filter operations..."
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                className="h-8 pl-8 pr-3 text-xs bg-white border border-outline-variant rounded-lg w-48 focus:outline-none focus:border-primary"
              />
            </div>
          </div>

          {/* Table Content */}
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-outline-variant bg-[#F8FAF8] text-[10px] uppercase font-mono text-outline">
                  <th className="py-2.5 px-3">Operation & Ward</th>
                  <th className="py-2.5 px-3">Type & Scope</th>
                  <th className="py-2.5 px-3">Priority & Risk</th>
                  <th className="py-2.5 px-2 text-center">Progress</th>
                  <th className="py-2.5 px-2 text-center">Status</th>
                  <th className="py-2.5 px-2 text-center">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant">
                {loading && actionsList.length === 0 && (
                  <tr>
                    <td colSpan="6" className="py-8 text-center text-outline font-mono text-xs">
                      <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                      Connecting to Municipal Action Store...
                    </td>
                  </tr>
                )}

                {!loading && filteredOps.length === 0 && (
                  <tr>
                    <td colSpan="6" className="py-8 text-center text-outline font-mono text-xs">
                      No active operational actions found matching criteria.
                    </td>
                  </tr>
                )}

                {filteredOps.map((op) => {
                  const status = (op.status || 'proposed').toLowerCase();
                  const priority = (op.priority || 'medium').toLowerCase();
                  const progressPct =
                    status === 'completed' ? 100 : status === 'in_progress' ? 70 : status === 'approved' ? 35 : 15;

                  return (
                    <tr key={op.action_id} className="hover:bg-[#F8FAF8] transition-colors">
                      <td className="py-3 px-3">
                        <div className="font-bold text-on-surface text-xs">{op.ward_name} Ward</div>
                        <div className="font-mono text-[10px] text-outline flex items-center gap-1.5 mt-0.5">
                          <span className="font-semibold text-primary">{op.action_id}</span>
                          <span>•</span>
                          <span>{op.ward_id || 'AMC'}</span>
                        </div>
                      </td>

                      <td className="py-3 px-3">
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-slate-100 text-slate-800 border uppercase">
                          {(op.action_type || 'intervene').replace(/_/g, ' ')}
                        </span>
                        <div
                          className="font-mono text-[10px] text-outline mt-1 max-w-[200px] truncate"
                          title={op.reason}
                        >
                          {op.reason || 'Advisory action'}
                        </div>
                      </td>

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

                      <td className="py-3 px-2 text-center">
                        <div className="flex flex-col items-center gap-1">
                          <span className="font-mono text-[11px] font-bold text-on-surface">{progressPct}%</span>
                          <div className="w-16 bg-slate-200 h-1.5 rounded-full overflow-hidden">
                            <div
                              className={`h-full ${
                                status === 'completed'
                                  ? 'bg-[#059669]'
                                  : status === 'in_progress'
                                  ? 'bg-primary'
                                  : 'bg-amber-500'
                              }`}
                              style={{ width: `${progressPct}%` }}
                            />
                          </div>
                        </div>
                      </td>

                      <td className="py-3 px-2 text-center">
                        <span
                          className={`px-2 py-0.5 rounded-full font-mono text-[10px] font-bold inline-flex items-center gap-1 uppercase ${
                            status === 'proposed'
                              ? 'bg-amber-50 text-amber-800 border border-amber-200'
                              : status === 'approved'
                              ? 'bg-blue-50 text-blue-800 border border-blue-200'
                              : status === 'in_progress'
                              ? 'bg-emerald-50 text-emerald-800 border border-emerald-300'
                              : 'bg-slate-100 text-slate-800'
                          }`}
                        >
                          {status === 'in_progress' && (
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-ping"></span>
                          )}
                          {status.replace('_', ' ')}
                        </span>
                      </td>

                      <td className="py-3 px-2 text-center">
                        {status === 'proposed' && (
                          <button
                            onClick={() => handleStatusTransition(op.action_id, 'approved')}
                            disabled={isUpdating}
                            className="px-2.5 py-1 rounded bg-blue-600 text-white font-mono text-[10px] font-bold hover:bg-blue-700 transition-colors cursor-pointer"
                            title="Approve proposed municipal intervention"
                          >
                            Approve
                          </button>
                        )}

                        {status === 'approved' && (
                          <button
                            onClick={() => handleStatusTransition(op.action_id, 'in_progress')}
                            disabled={isUpdating}
                            className="px-2.5 py-1 rounded bg-primary text-white font-mono text-[10px] font-bold hover:bg-[#1B5742] transition-colors cursor-pointer"
                            title="Deploy and mobilize field crew"
                          >
                            Deploy
                          </button>
                        )}

                        {status === 'in_progress' && (
                          <button
                            onClick={() => handleStatusTransition(op.action_id, 'completed')}
                            disabled={isUpdating}
                            className="px-2.5 py-1 rounded bg-[#059669] text-white font-mono text-[10px] font-bold hover:bg-[#047857] transition-colors cursor-pointer"
                            title="Mark field operation resolved and completed"
                          >
                            Complete
                          </button>
                        )}

                        {status === 'completed' && (
                          <span className="font-mono text-[10px] text-emerald-700 font-semibold">Done</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right 4 Cols: Operational Escalation & Emergency Desk */}
        <div className="xl:col-span-4 space-y-4">
          {/* Active Blocker Alert Card */}
          <div className="bg-surface-container-lowest border-2 border-red-200 rounded-xl p-4 shadow-xs bg-gradient-to-br from-white to-red-50/30">
            <div className="flex items-start justify-between pb-2 border-b border-red-100">
              <div className="flex items-center gap-2 text-error">
                <span className="material-symbols-outlined text-[20px]">error</span>
                <h3 className="font-title-sm text-title-sm font-bold">Priority Approval Required</h3>
              </div>
              <span className="px-2 py-0.5 rounded bg-error text-white text-[10px] font-mono font-bold">
                INCIDENT DESK
              </span>
            </div>

            <div className="mt-3 space-y-3 text-xs">
              {pendingBlockers.length === 0 ? (
                <div className="p-3 text-center text-outline font-mono text-[11px]">
                  No urgent pending blockers. All active actions cleared.
                </div>
              ) : (
                pendingBlockers.map((b) => (
                  <div key={b.action_id} className="p-2.5 rounded-lg border border-red-200 bg-white">
                    <div className="flex items-center justify-between font-bold text-on-surface">
                      <span>{b.ward_name} ({b.action_id})</span>
                      <span className="text-error font-mono uppercase text-[10px]">{b.priority}</span>
                    </div>
                    <p className="text-on-surface-variant text-[11px] mt-1 line-clamp-2">
                      {b.reason}
                    </p>
                    <div className="mt-2 flex items-center justify-between">
                      <span className="text-[10px] font-mono text-outline">
                        Status: {b.status}
                      </span>
                      {b.status === 'proposed' ? (
                        <button
                          onClick={() => handleStatusTransition(b.action_id, 'approved')}
                          className="text-primary hover:underline text-[11px] font-mono font-bold cursor-pointer"
                        >
                          Authorize Sign-Off →
                        </button>
                      ) : (
                        <button
                          onClick={() => handleStatusTransition(b.action_id, 'completed')}
                          className="text-primary hover:underline text-[11px] font-mono font-bold cursor-pointer"
                        >
                          Resolve →
                        </button>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Quick Dispatch Action Widget */}
          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 shadow-xs space-y-3">
            <h4 className="font-title-sm text-title-sm font-bold text-primary flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[18px]">bolt</span>
              <span>Quick Dispatch Triggers</span>
            </h4>
            <p className="text-[11px] text-outline font-mono">
              Triggers verified operations directly into the backend store:
            </p>

            <div className="space-y-2 text-xs">
              <button
                onClick={() => handleQuickDispatch('tankers')}
                disabled={isUpdating}
                className="w-full p-2.5 rounded-lg bg-surface-bright hover:bg-surface-container-low border border-slate-200 flex items-center justify-between transition-colors text-left cursor-pointer"
              >
                <div>
                  <div className="font-semibold text-primary">Deploy 6 Water Tankers</div>
                  <div className="text-[10px] font-mono text-outline">To Danilimda informal settlements</div>
                </div>
                <span className="material-symbols-outlined text-[18px] text-primary">send</span>
              </button>

              <button
                onClick={() => handleQuickDispatch('ors')}
                disabled={isUpdating}
                className="w-full p-2.5 rounded-lg bg-surface-bright hover:bg-surface-container-low border border-slate-200 flex items-center justify-between transition-colors text-left cursor-pointer"
              >
                <div>
                  <div className="font-semibold text-primary">Activate UHC ORS Booths</div>
                  <div className="text-[10px] font-mono text-outline">Gomtipur health centres</div>
                </div>
                <span className="material-symbols-outlined text-[18px] text-primary">local_hospital</span>
              </button>

              <button
                onClick={() => handleQuickDispatch('misting')}
                disabled={isUpdating}
                className="w-full p-2.5 rounded-lg bg-surface-bright hover:bg-surface-container-low border border-slate-200 flex items-center justify-between transition-colors text-left cursor-pointer"
              >
                <div>
                  <div className="font-semibold text-primary">Deploy High-Pressure Misting</div>
                  <div className="text-[10px] font-mono text-outline">At Kalupur AMTS transit hub</div>
                </div>
                <span className="material-symbols-outlined text-[18px] text-primary">air</span>
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
