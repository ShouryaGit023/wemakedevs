import React, { useState } from 'react';

export default function IssueAdvisoryModal({ isOpen, onClose }) {
  const [selectedTier, setSelectedTier] = useState('Orange');
  const [selectedZones, setSelectedZones] = useState(['East Zone', 'South Zone']);
  const [channels, setChannels] = useState({
    sms: true,
    pa: true,
    hospitals: true,
    waterTankers: true
  });
  const [isBroadcasting, setIsBroadcasting] = useState(false);
  const [broadcastSuccess, setBroadcastSuccess] = useState(false);

  if (!isOpen) return null;

  const handleBroadcast = () => {
    setIsBroadcasting(true);
    setTimeout(() => {
      setIsBroadcasting(false);
      setBroadcastSuccess(true);
      setTimeout(() => {
        setBroadcastSuccess(false);
        onClose();
      }, 1500);
    }, 1000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs select-none">
      <div className="bg-surface-container-lowest rounded-2xl border border-outline-variant shadow-xl w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="px-5 py-4 border-b border-outline-variant flex items-center justify-between bg-[#F8FAF8]">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-error flex items-center justify-center text-white">
              <span className="material-symbols-outlined text-[18px]">campaign</span>
            </div>
            <div>
              <h3 className="font-title-sm text-title-sm text-primary font-bold">Issue Municipal Climate Advisory</h3>
              <p className="text-[11px] font-mono text-outline">Ahmedabad Heat Action Plan (HAP) Dispatch</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 text-outline hover:text-primary rounded cursor-pointer">
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4">
          {broadcastSuccess ? (
            <div className="p-6 text-center space-y-2">
              <div className="w-12 h-12 bg-emerald-100 text-emerald-800 rounded-full flex items-center justify-center mx-auto">
                <span className="material-symbols-outlined text-[28px]">check_circle</span>
              </div>
              <h4 className="font-bold text-base text-primary">Advisory Broadcast Dispatched!</h4>
              <p className="text-xs text-on-surface-variant">
                Alert Tier {selectedTier} transmitted to 108 Emergency, Paldi Disaster Cell, and Urban Health Centres.
              </p>
            </div>
          ) : (
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
          )}
        </div>

        {/* Footer */}
        {!broadcastSuccess && (
          <div className="px-5 py-3 border-t border-outline-variant bg-[#F8FAF8] flex items-center justify-end gap-2">
            <button
              onClick={onClose}
              className="px-3.5 py-1.5 rounded-lg border border-outline-variant text-on-surface hover:bg-slate-100 text-xs font-semibold cursor-pointer"
            >
              Cancel
            </button>
            <button
              onClick={handleBroadcast}
              disabled={isBroadcasting}
              className="px-4 py-1.5 rounded-lg bg-error hover:bg-[#991B1B] text-white text-xs font-semibold flex items-center gap-1.5 shadow-sm active:scale-98 cursor-pointer disabled:opacity-60"
            >
              <span className="material-symbols-outlined text-[16px]">broadcast_on_home</span>
              <span>{isBroadcasting ? 'Broadcasting...' : `Authorize Tier ${selectedTier} Broadcast`}</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
