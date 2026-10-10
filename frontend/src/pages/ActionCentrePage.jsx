import React, { useState } from 'react';
import KPICard from '../components/KPICard';
import { ACTION_CENTRE_KPIS, FIELD_OPERATIONS } from '../data/mockData';

export default function ActionCentrePage({ onOpenDeployModal }) {
  const [filterStatus, setFilterStatus] = useState('All');
  const [searchFilter, setSearchFilter] = useState('');
  const [operationsList, setOperationsList] = useState(FIELD_OPERATIONS);

  const filteredOps = operationsList.filter((op) => {
    const matchesStatus = filterStatus === 'All' || op.status === filterStatus;
    const matchesSearch = !searchFilter || 
      op.ward.toLowerCase().includes(searchFilter.toLowerCase()) ||
      op.title.toLowerCase().includes(searchFilter.toLowerCase()) ||
      op.id.toLowerCase().includes(searchFilter.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  const handleResolveBlocker = (opId) => {
    setOperationsList((prev) => 
      prev.map((op) => op.id === opId ? { ...op, status: 'In Progress', progress: 55 } : op)
    );
    alert(`Escalation resolved for ${opId}. Task force cleared for operations.`);
  };

  return (
    <div className="space-y-6">
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
            onClick={() => alert("Applying operational filters: East and South Zone emergency wards active.")}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-surface-container-lowest border border-outline-variant text-on-surface text-label-md font-label-md hover:bg-surface-container-low shadow-xs active:scale-[0.98] transition-all cursor-pointer"
          >
            <span className="material-symbols-outlined text-[18px] text-outline">filter_list</span>
            <span>Filter View</span>
          </button>

          <button 
            onClick={() => alert("Downloading Field Operations Dispatch Log (CSV)...")}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-surface-container-lowest border border-outline-variant text-on-surface text-label-md font-label-md hover:bg-surface-container-low shadow-xs active:scale-[0.98] transition-all cursor-pointer"
          >
            <span className="material-symbols-outlined text-[18px] text-outline">download</span>
            <span>Export Ops Log (CSV)</span>
          </button>

          <button 
            onClick={() => onOpenDeployModal ? onOpenDeployModal() : alert("Deploy New Operation Desk initialized.")}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary-container text-white text-label-md font-label-md hover:bg-[#1B5742] active:scale-[0.98] shadow-sm transition-all cursor-pointer font-semibold"
          >
            <span className="material-symbols-outlined text-[18px]">add</span>
            <span>Deploy New Operation</span>
          </button>
        </div>
      </section>

      {/* Operational KPI Summary Strip */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
        <KPICard 
          title={ACTION_CENTRE_KPIS.activeDeployments.label}
          icon="near_me"
          value={ACTION_CENTRE_KPIS.activeDeployments.value}
          unit={ACTION_CENTRE_KPIS.activeDeployments.statusText}
          subtitle={ACTION_CENTRE_KPIS.activeDeployments.detail}
          progress={ACTION_CENTRE_KPIS.activeDeployments.progress}
          isSuccess={true}
        />

        <KPICard 
          title={ACTION_CENTRE_KPIS.criticalBlockers.label}
          icon="warning"
          value={ACTION_CENTRE_KPIS.criticalBlockers.value}
          unit={ACTION_CENTRE_KPIS.criticalBlockers.statusText}
          subtitle={ACTION_CENTRE_KPIS.criticalBlockers.detail}
          progress={ACTION_CENTRE_KPIS.criticalBlockers.progress}
          isDanger={true}
        />

        <KPICard 
          title={ACTION_CENTRE_KPIS.onTimeExecution.label}
          icon="pace"
          value={ACTION_CENTRE_KPIS.onTimeExecution.value}
          unit={ACTION_CENTRE_KPIS.onTimeExecution.statusText}
          subtitle={ACTION_CENTRE_KPIS.onTimeExecution.detail}
          progress={ACTION_CENTRE_KPIS.onTimeExecution.progress}
          isSuccess={true}
        />

        <KPICard 
          title={ACTION_CENTRE_KPIS.teamsMobilized.label}
          icon="group_work"
          value={ACTION_CENTRE_KPIS.teamsMobilized.value}
          unit={ACTION_CENTRE_KPIS.teamsMobilized.statusText}
          subtitle={ACTION_CENTRE_KPIS.teamsMobilized.detail}
          progress={ACTION_CENTRE_KPIS.teamsMobilized.progress}
          isInfo={true}
        />

        <KPICard 
          title={ACTION_CENTRE_KPIS.dailyTargetProgress.label}
          icon="flag"
          value={ACTION_CENTRE_KPIS.dailyTargetProgress.value}
          unit={ACTION_CENTRE_KPIS.dailyTargetProgress.statusText}
          subtitle={ACTION_CENTRE_KPIS.dailyTargetProgress.detail}
          progress={ACTION_CENTRE_KPIS.dailyTargetProgress.progress}
        />
      </section>

      {/* Main 2-Column Section: Operations Table (8 Cols) + Escalation Desk (4 Cols) */}
      <section className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* Left 8 Cols: Field Operations Dispatch Table */}
        <div className="xl:col-span-8 bg-surface-container-lowest rounded-xl border border-outline-variant shadow-xs overflow-hidden">
          {/* Table Controls */}
          <div className="p-3.5 border-b border-outline-variant flex flex-wrap items-center justify-between gap-3 bg-[#F8FAF8]">
            <div className="flex items-center gap-1 bg-surface-bright p-1 rounded-lg border border-slate-200">
              {['All', 'In Progress', 'Blocked', 'Completed', 'Scheduled'].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setFilterStatus(tab)}
                  className={`px-3 py-1 rounded-md text-xs transition-colors cursor-pointer ${
                    filterStatus === tab 
                      ? 'bg-primary-container text-white font-semibold shadow-xs' 
                      : 'text-on-surface-variant hover:bg-slate-100'
                  }`}
                >
                  {tab}
                </button>
              ))}
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
                  <th className="py-2.5 px-3">Assigned Wing</th>
                  <th className="py-2.5 px-2 text-center">Progress</th>
                  <th className="py-2.5 px-2 text-center">Status</th>
                  <th className="py-2.5 px-2 text-center">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant">
                {filteredOps.map((op) => (
                  <tr key={op.id} className="hover:bg-[#F8FAF8] transition-colors">
                    <td className="py-3 px-3">
                      <div className="font-bold text-on-surface text-xs">{op.title}</div>
                      <div className="font-mono text-[10px] text-outline flex items-center gap-1.5 mt-0.5">
                        <span className="font-semibold text-primary">{op.id}</span>
                        <span>•</span>
                        <span>{op.ward}</span>
                      </div>
                    </td>

                    <td className="py-3 px-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-slate-100 text-slate-800 border">
                        {op.type}
                      </span>
                      <div className="font-mono text-[10px] text-outline mt-1">Target: {op.target}</div>
                    </td>

                    <td className="py-3 px-3">
                      <div className="font-medium text-on-surface">{op.team}</div>
                      <div className="text-[10px] font-mono text-outline">{op.personnel} Personnel • ETA: {op.eta}</div>
                    </td>

                    <td className="py-3 px-2 text-center">
                      <div className="flex flex-col items-center gap-1">
                        <span className="font-mono text-[11px] font-bold text-on-surface">{op.progress}%</span>
                        <div className="w-16 bg-slate-200 h-1.5 rounded-full overflow-hidden">
                          <div 
                            className={`h-full ${op.status === 'Blocked' ? 'bg-error' : op.status === 'Completed' ? 'bg-[#059669]' : 'bg-primary'}`}
                            style={{ width: `${op.progress}%` }}
                          />
                        </div>
                      </div>
                    </td>

                    <td className="py-3 px-2 text-center">
                      <span className={`px-2 py-0.5 rounded-full font-mono text-[10px] font-bold inline-flex items-center gap-1 ${
                        op.status === 'Blocked' ? 'bg-error-container text-on-error-container' :
                        op.status === 'Completed' ? 'bg-emerald-100 text-emerald-800' :
                        op.status === 'Scheduled' ? 'bg-slate-100 text-slate-800' :
                        'bg-blue-50 text-blue-800 border border-blue-200'
                      }`}>
                        {op.status === 'Blocked' && <span className="w-1.5 h-1.5 rounded-full bg-error animate-ping"></span>}
                        {op.status}
                      </span>
                    </td>

                    <td className="py-3 px-2 text-center">
                      {op.status === 'Blocked' ? (
                        <button
                          onClick={() => handleResolveBlocker(op.id)}
                          className="px-2.5 py-1 rounded bg-error text-white font-mono text-[10px] font-bold hover:bg-[#991B1B] transition-colors cursor-pointer"
                        >
                          Resolve
                        </button>
                      ) : (
                        <button
                          onClick={() => alert(`Reviewing operational telemetry for ${op.id}`)}
                          className="px-2.5 py-1 rounded bg-[#F0F5F1] text-primary font-mono text-[10px] font-bold border border-outline-variant hover:bg-[#E1EDE3] transition-colors cursor-pointer"
                        >
                          View
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
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
                <h3 className="font-title-sm text-title-sm font-bold">Active Operational Blockers</h3>
              </div>
              <span className="px-2 py-0.5 rounded bg-error text-white text-[10px] font-mono font-bold">
                HIGH PRIORITY
              </span>
            </div>

            <div className="mt-3 space-y-3 text-xs">
              <div className="p-2.5 rounded-lg border border-red-200 bg-white">
                <div className="flex items-center justify-between font-bold text-on-surface">
                  <span>Danilimda Pipeline Halt (OP-039)</span>
                  <span className="text-error font-mono">10:15 IST</span>
                </div>
                <p className="text-on-surface-variant text-[11px] mt-1">
                  Water bowser fill valve valve jammed at Paldi filling hub. 4 tankers queued.
                </p>
                <div className="mt-2 flex items-center justify-between">
                  <span className="text-[10px] font-mono text-outline">Engineering Wing A dispatched</span>
                  <button 
                    onClick={() => handleResolveBlocker('OP-2024-039')}
                    className="text-primary hover:underline text-[11px] font-mono font-bold cursor-pointer"
                  >
                    Bypass Line →
                  </button>
                </div>
              </div>

              <div className="p-2.5 rounded-lg border border-red-200 bg-white">
                <div className="flex items-center justify-between font-bold text-on-surface">
                  <span>Gomtipur Coating Resin Shortage</span>
                  <span className="text-error font-mono">09:40 IST</span>
                </div>
                <p className="text-on-surface-variant text-[11px] mt-1">
                  12 barrels of cool roof acrylic resin in transit from Odhav depot delayed.
                </p>
                <div className="mt-2 flex items-center justify-between">
                  <span className="text-[10px] font-mono text-outline">Supply Officer Re-routed</span>
                  <button 
                    onClick={() => alert("Emergency supply dispatch re-routed via S.G. Highway.")}
                    className="text-primary hover:underline text-[11px] font-mono font-bold cursor-pointer"
                  >
                    Escalate →
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Quick Dispatch Action Widget */}
          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 shadow-xs space-y-3">
            <h4 className="font-title-sm text-title-sm font-bold text-primary flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[18px]">bolt</span>
              <span>Quick Dispatch Triggers</span>
            </h4>
            
            <div className="space-y-2 text-xs">
              <button 
                onClick={() => alert("Triggered: 6 emergency water bowsers dispatched to Danilimda & Gomtipur.")}
                className="w-full p-2.5 rounded-lg bg-surface-bright hover:bg-surface-container-low border border-slate-200 flex items-center justify-between transition-colors text-left cursor-pointer"
              >
                <div>
                  <div className="font-semibold text-primary">Deploy 6 Water Tankers</div>
                  <div className="text-[10px] font-mono text-outline">To informal settlements (Slums)</div>
                </div>
                <span className="material-symbols-outlined text-[18px] text-primary">send</span>
              </button>

              <button 
                onClick={() => alert("Triggered: Urban Health Centres activated for emergency ORS distribution.")}
                className="w-full p-2.5 rounded-lg bg-surface-bright hover:bg-surface-container-low border border-slate-200 flex items-center justify-between transition-colors text-left cursor-pointer"
              >
                <div>
                  <div className="font-semibold text-primary">Activate UHC ORS Booths</div>
                  <div className="text-[10px] font-mono text-outline">Chhabils & Parabs replenishment</div>
                </div>
                <span className="material-symbols-outlined text-[18px] text-primary">local_hospital</span>
              </button>

              <button 
                onClick={() => alert("Triggered: Pop-up misting pods deployed at Kalupur & Geeta Mandir bus terminals.")}
                className="w-full p-2.5 rounded-lg bg-surface-bright hover:bg-surface-container-low border border-slate-200 flex items-center justify-between transition-colors text-left cursor-pointer"
              >
                <div>
                  <div className="font-semibold text-primary">Deploy High-Pressure Misting</div>
                  <div className="text-[10px] font-mono text-outline">At AMTS transit hubs</div>
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
