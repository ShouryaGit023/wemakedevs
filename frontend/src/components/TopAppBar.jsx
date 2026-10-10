import React, { useState } from 'react';
import { MUNICIPAL_OFFICERS, AHMEDABAD_ZONES } from '../data/mockData';

export default function TopAppBar({ onOpenMobileMenu, selectedZone, onSelectZone, onRefreshData }) {
  const [officerIndex, setOfficerIndex] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showZoneDropdown, setShowZoneDropdown] = useState(false);
  const [showOfficerDropdown, setShowOfficerDropdown] = useState(false);

  const officer = MUNICIPAL_OFFICERS[officerIndex];

  const handleRefresh = () => {
    setIsRefreshing(true);
    if (onRefreshData) onRefreshData();
    setTimeout(() => setIsRefreshing(false), 800);
  };

  return (
    <header className="bg-surface-container-lowest border-b border-outline-variant h-14 shrink-0 flex items-center justify-between px-4 lg:px-margin-desktop z-40 shadow-xs select-none sticky top-0">
      {/* Left Section: Mobile Menu + Jurisdiction Selector + Sensor Stream Badge */}
      <div className="flex items-center gap-2 lg:gap-space-lg">
        {/* Mobile Hamburger Toggle */}
        <button
          onClick={onOpenMobileMenu}
          className="lg:hidden p-1.5 text-on-surface-variant hover:bg-surface-container-low rounded-lg transition-colors"
          aria-label="Open menu"
        >
          <span className="material-symbols-outlined text-[22px]">menu</span>
        </button>

        {/* Jurisdiction Selector */}
        <div className="flex items-center gap-1.5 sm:gap-2">
          <span className="hidden sm:inline font-mono text-[10px] uppercase font-bold text-outline">Jurisdiction:</span>
          
          <div className="relative inline-block">
            <button
              onClick={() => setShowZoneDropdown(!showZoneDropdown)}
              className="flex items-center gap-1.5 sm:gap-2 bg-[#F0F5F1] border border-outline-variant px-2.5 sm:px-3 py-1.5 rounded-lg text-primary font-title-sm text-title-sm hover:bg-[#E1EDE3] transition-colors cursor-pointer text-left"
            >
              <span className="material-symbols-outlined text-primary text-[18px]">location_city</span>
              <span className="font-semibold text-xs sm:text-sm">
                Ahmedabad {selectedZone && selectedZone !== 'All 7 Zones' ? `• ${selectedZone}` : '• All 48 Wards'}
              </span>
              <span className="material-symbols-outlined text-[16px] text-outline">arrow_drop_down</span>
            </button>

            {/* Zone Dropdown */}
            {showZoneDropdown && (
              <div 
                className="absolute left-0 mt-1 w-56 bg-surface-container-lowest border border-outline-variant rounded-lg shadow-lg z-50 py-1"
                onMouseLeave={() => setShowZoneDropdown(false)}
              >
                <div className="px-3 py-1.5 text-[10px] font-mono uppercase text-outline border-b border-slate-100">
                  Select Municipal Zone
                </div>
                {AHMEDABAD_ZONES.map((zone) => (
                  <button
                    key={zone}
                    onClick={() => {
                      if (onSelectZone) onSelectZone(zone);
                      setShowZoneDropdown(false);
                    }}
                    className={`w-full text-left px-3 py-1.5 text-xs hover:bg-surface-container-low transition-colors flex items-center justify-between ${selectedZone === zone ? 'font-bold text-primary bg-emerald-50' : 'text-on-surface'}`}
                  >
                    <span>{zone}</span>
                    {selectedZone === zone && (
                      <span className="material-symbols-outlined text-[16px] text-primary">check</span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Live Sensor Stream Freshness Badge */}
        <div className="hidden xl:flex items-center gap-2 px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200">
          <span className="h-2 w-2 rounded-full bg-emerald-600 animate-pulse"></span>
          <span className="font-mono text-[10px] text-emerald-800 font-semibold tracking-normal">
            IMD & AMC Sensor Stream: Live (Synced 8m ago)
          </span>
        </div>
      </div>

      {/* Right Section: Weather Quick Pill + Action Icons + Officer Profile */}
      <div className="flex items-center gap-2 sm:gap-space-md">
        {/* Weather / Alert Quick Pill */}
        <div className="hidden md:flex items-center gap-2 bg-[#FEF2F2] border border-[#FECACA] px-3 py-1 rounded-lg">
          <span className="material-symbols-outlined text-[#DC2626] text-[18px]">thermostat</span>
          <span className="font-mono text-[11px] text-[#991B1B] font-bold">43.8°C Extreme Heat Alert</span>
          <span className="text-outline-variant">|</span>
          <span className="material-symbols-outlined text-[#0284C7] text-[18px]">waves</span>
          <span className="font-mono text-[11px] text-[#075985]">Sabarmati: Normal</span>
        </div>

        {/* Action Icon Buttons */}
        <div className="flex items-center gap-1 border-r border-outline-variant pr-2 sm:pr-space-md">
          <button 
            className="relative p-1.5 sm:p-2 text-on-surface-variant hover:bg-surface-container-low rounded-lg transition-colors cursor-pointer" 
            title="Operational Alerts"
            onClick={() => alert("Alerts Feed: 3 active advisories broadcasted to East & South zone UHC units.")}
          >
            <span className="material-symbols-outlined text-[20px]">notifications</span>
            <span className="absolute top-1 right-1 flex h-4 w-4 items-center justify-center rounded-full bg-error text-white font-mono text-[9px] font-bold">3</span>
          </button>
          
          <button 
            onClick={handleRefresh}
            className={`p-1.5 sm:p-2 text-on-surface-variant hover:bg-surface-container-low rounded-lg transition-colors cursor-pointer ${isRefreshing ? 'animate-spin text-primary' : ''}`} 
            title="Refresh Telemetry Feeds"
          >
            <span className="material-symbols-outlined text-[20px]">refresh</span>
          </button>

          <button 
            onClick={() => alert("AMC Command Desk Help: Connected to Open-Meteo High-Res Grid + Landsat-9 TIRS Thermal Overpasses.")}
            className="p-1.5 sm:p-2 text-on-surface-variant hover:bg-surface-container-low rounded-lg transition-colors cursor-pointer hidden sm:block" 
            title="Help & Protocols"
          >
            <span className="material-symbols-outlined text-[20px]">help</span>
          </button>
        </div>

        {/* Officer Profile Menu */}
        <div className="relative">
          <button 
            onClick={() => setShowOfficerDropdown(!showOfficerDropdown)}
            className="flex items-center gap-2 pl-1 cursor-pointer hover:opacity-90 transition-opacity"
          >
            <img 
              className="w-8 h-8 rounded-full border border-outline-variant object-cover shadow-2xs" 
              alt={officer.name} 
              src={officer.avatar}
            />
            <div className="hidden lg:flex flex-col text-left">
              <span className="font-title-sm text-title-sm text-on-surface leading-tight font-semibold">{officer.name}</span>
              <span className="font-mono text-[10px] text-on-surface-variant">{officer.designation}</span>
            </div>
            <span className="material-symbols-outlined text-outline text-[16px]">expand_more</span>
          </button>

          {/* Officer Selector Dropdown */}
          {showOfficerDropdown && (
            <div 
              className="absolute right-0 mt-1 w-64 bg-surface-container-lowest border border-outline-variant rounded-lg shadow-lg z-50 py-1"
              onMouseLeave={() => setShowOfficerDropdown(false)}
            >
              <div className="px-3 py-1.5 text-[10px] font-mono uppercase text-outline border-b border-slate-100">
                Active Command Officer
              </div>
              {MUNICIPAL_OFFICERS.map((off, idx) => (
                <button
                  key={off.name}
                  onClick={() => {
                    setOfficerIndex(idx);
                    setShowOfficerDropdown(false);
                  }}
                  className={`w-full text-left px-3 py-2 text-xs hover:bg-surface-container-low transition-colors flex items-center gap-2.5 ${officerIndex === idx ? 'bg-emerald-50 text-primary' : 'text-on-surface'}`}
                >
                  <img src={off.avatar} className="w-7 h-7 rounded-full object-cover border" alt={off.name} />
                  <div>
                    <div className="font-semibold text-xs">{off.name}</div>
                    <div className="text-[10px] text-outline font-mono">{off.designation}</div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
