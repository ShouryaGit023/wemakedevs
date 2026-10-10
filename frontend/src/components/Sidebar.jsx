import React from 'react';

export default function Sidebar({ activeTab, onSelectTab, onOpenAdvisory, isMobileOpen, onCloseMobile }) {
  const navTabs = [
    { id: 'overview', label: 'Overview', icon: 'dashboard' },
    { id: 'ward-explorer', label: 'Ward Explorer', icon: 'map' },
    { id: 'planner', label: 'Intervention Planner', icon: 'crisis_alert' },
    { id: 'action-centre', label: 'Action Centre', icon: 'local_police' },
    { id: 'verification', label: 'Impact Verification', icon: 'verified' },
    { id: 'learning-loop', label: 'Learning & Governance', icon: 'sync' },
    { id: 'system-status', label: 'Data & System Status', icon: 'database' }
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isMobileOpen && (
        <div 
          className="fixed inset-0 bg-black/40 z-40 lg:hidden backdrop-blur-xs transition-opacity"
          onClick={onCloseMobile}
        />
      )}

      <aside className={`
        fixed lg:static inset-y-0 left-0 z-50
        w-64 h-full bg-surface-container-lowest border-r border-outline-variant
        flex flex-col justify-between shrink-0 select-none
        transition-transform duration-200 ease-in-out
        ${isMobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        {/* Top Brand & Header Section */}
        <div>
          <div className="px-space-md py-space-md border-b border-outline-variant flex items-center justify-between">
            <div className="flex items-center gap-space-sm">
              <div className="w-10 h-10 rounded-lg bg-primary-container flex items-center justify-center text-white shadow-sm">
                <span className="material-symbols-outlined text-[24px]">shield</span>
              </div>
              <div className="flex flex-col">
                <div className="flex items-center gap-1.5">
                  <span className="font-headline-sm text-headline-sm text-primary tracking-tight font-bold">ClimateShield</span>
                  <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-semibold bg-secondary-container text-on-secondary-container uppercase">AMC</span>
                </div>
                <span className="text-[11px] font-mono text-on-surface-variant">AMC Climate Risk</span>
              </div>
            </div>

            {/* Mobile close button */}
            <button 
              onClick={onCloseMobile}
              className="lg:hidden p-1 text-outline hover:text-primary rounded"
            >
              <span className="material-symbols-outlined text-[20px]">close</span>
            </button>
          </div>

          {/* Desk Context Tag */}
          <div className="px-space-md pt-space-sm pb-space-xs">
            <span className="text-[10px] font-mono uppercase tracking-wider text-outline block">Command Operations Desk</span>
          </div>

          {/* Navigation Tabs */}
          <nav className="px-space-sm space-y-1 mt-1">
            {navTabs.map((tab) => {
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => {
                    onSelectTab(tab.id);
                    if (onCloseMobile) onCloseMobile();
                  }}
                  className={`
                    w-full flex items-center gap-space-sm px-space-md py-space-sm rounded-lg text-left
                    transition-all duration-150 active:scale-[0.98]
                    ${isActive 
                      ? 'bg-surface-container text-primary font-title-sm border-l-4 border-primary shadow-xs font-semibold' 
                      : 'text-on-surface-variant font-body-md hover:bg-surface-container-low hover:text-primary'}
                  `}
                >
                  <span 
                    className={`material-symbols-outlined text-[20px] ${isActive ? 'text-primary fill' : 'text-outline'}`}
                  >
                    {tab.icon}
                  </span>
                  <span className="text-body-md leading-none">{tab.label}</span>
                </button>
              );
            })}
          </nav>

          {/* CTA Issue Advisory */}
          <div className="px-space-md mt-space-md">
            <button
              onClick={onOpenAdvisory}
              className="w-full h-10 bg-error hover:bg-[#991B1B] text-white rounded-lg font-title-sm text-title-sm flex items-center justify-center gap-2 shadow-sm transition-all active:scale-[0.98] cursor-pointer"
            >
              <span className="material-symbols-outlined text-[18px]">warning</span>
              <span className="font-semibold tracking-wide">Issue Advisory</span>
            </button>
          </div>
        </div>

        {/* Bottom Sidebar Section */}
        <div className="p-space-md border-t border-outline-variant bg-[#F8FAF8] space-y-2">
          {/* Telemetry Health Box */}
          <div className="p-2 rounded bg-surface-container-lowest border border-outline-variant flex items-center gap-2 shadow-2xs">
            <span className="relative flex h-2.5 w-2.5 shrink-0">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-600"></span>
            </span>
            <div className="flex-1 min-w-0">
              <div className="text-[10px] font-mono text-primary font-bold leading-tight">Telemetry Sensors Online</div>
              <div className="text-[10px] font-mono text-outline truncate">48/48 Wards reporting (100%)</div>
            </div>
            <span className="material-symbols-outlined text-outline text-[16px]">sensors</span>
          </div>

          {/* Bottom Nav Links */}
          <button 
            onClick={() => { onSelectTab('system-status'); if (onCloseMobile) onCloseMobile(); }}
            className="w-full flex items-center justify-between text-on-surface-variant hover:text-primary text-[11px] font-mono py-1 px-1 transition-colors text-left"
          >
            <span className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[15px]">sensors</span>
              System Telemetry
            </span>
            <span className="material-symbols-outlined text-[14px]">chevron_right</span>
          </button>

          <a 
            href="#support" 
            onClick={(e) => { e.preventDefault(); alert("ClimateShield AMC v4.2 Command Desk. Hotline: AMC Disaster Management Cell Paldi (108 / 1926)."); }}
            className="flex items-center justify-between text-on-surface-variant hover:text-primary text-[11px] font-mono py-1 px-1 transition-colors"
          >
            <span className="flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[15px]">help_center</span>
              Support & Manuals
            </span>
            <span className="material-symbols-outlined text-[14px]">chevron_right</span>
          </a>

          <div className="text-[9px] font-mono text-outline text-center pt-1 border-t border-slate-200/60">
            ClimateShield v4.2 • AMC Cell
          </div>
        </div>
      </aside>
    </>
  );
}
