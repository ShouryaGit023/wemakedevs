import React, { useState } from 'react';

export default function AhmedabadVectorMap({ liveWards = [], onSelectWard, onInspectWard }) {
  const [activeLayer, setActiveLayer] = useState('combined');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedZone, setSelectedZone] = useState('All 7 Zones');
  const [zoomLevel, setZoomLevel] = useState(1);
  const [mapType, setMapType] = useState('carto');

  // Base spatial polygons representing key Ahmedabad municipal wards
  const baseWards = [
    // West & North-West
    { id: 'AMC-NW-01', lookupId: 'W8', name: 'Thaltej', defaultScore: 28, defaultStatus: 'Low', zone: 'New West Zone', points: "110,90 190,80 230,130 170,170 90,140", textPos: [135, 130] },
    { id: 'AMC-W-02', lookupId: 'W9', name: 'Navrangpura', defaultScore: 34, defaultStatus: 'Low', zone: 'West Zone', points: "190,80 280,95 290,170 230,180 230,130", textPos: [215, 145] },
    { id: 'AMC-W-03', lookupId: 'W17', name: 'Paldi', defaultScore: 46, defaultStatus: 'Moderate', zone: 'West Zone', points: "230,180 300,180 320,250 240,260 210,210", textPos: [245, 225] },
    { id: 'AMC-SW-04', lookupId: 'W18', name: 'Vasna', defaultScore: 52, defaultStatus: 'Moderate', zone: 'South West Zone', points: "240,260 320,250 335,340 260,350 220,300", textPos: [260, 305] },
    { id: 'AMC-SW-05', lookupId: 'W19', name: 'Sarkhej', defaultScore: 42, defaultStatus: 'Moderate', zone: 'South West Zone', points: "110,240 220,240 240,340 160,370 90,290", textPos: [140, 300] },
    // North & Central
    { id: 'AMC-N-01', lookupId: 'W20', name: 'Chandkheda', defaultScore: 48, defaultStatus: 'Moderate', zone: 'North Zone', points: "280,30 360,20 400,80 320,95", textPos: [320, 60] },
    { id: 'AMC-C-02', lookupId: 'W3', name: 'Shahibaug', defaultScore: 67, defaultStatus: 'High', zone: 'Central Zone', points: "340,110 430,100 450,170 350,180", textPos: [365, 145] },
    { id: 'AMC-C-03', lookupId: 'W5', name: 'Jamalpur', defaultScore: 78, defaultStatus: 'High', zone: 'Central Zone', points: "325,200 400,190 420,270 340,270", textPos: [345, 235] },
    // East Critical Cluster
    { id: 'AMC-N-06', lookupId: 'W4', name: 'Bapunagar', defaultScore: 84, defaultStatus: 'High', zone: 'North Zone', points: "450,100 540,85 570,165 470,170", textPos: [480, 130] },
    { id: 'AMC-E-04', lookupId: 'W1', name: 'Gomtipur', defaultScore: 91, defaultStatus: 'Critical', zone: 'East Zone', points: "440,180 540,170 560,250 450,260", textPos: [465, 215], isCritical: true, center: [495, 230] },
    { id: 'AMC-E-08', lookupId: 'W10', name: 'Odhav', defaultScore: 85, defaultStatus: 'High', zone: 'East Zone', points: "555,140 660,130 680,230 575,235", textPos: [590, 185], center: [620, 200] },
    // South / South-East
    { id: 'AMC-S-14', lookupId: 'W2', name: 'Danilimda', defaultScore: 88, defaultStatus: 'Critical', zone: 'South Zone', points: "350,285 450,280 470,380 370,390", textPos: [380, 335], isCritical: true, center: [410, 355] },
    { id: 'AMC-S-09', lookupId: 'W7', name: 'Vatva', defaultScore: 81, defaultStatus: 'High', zone: 'South Zone', points: "470,340 590,320 620,420 490,430", textPos: [515, 380], center: [545, 380] },
    { id: 'AMC-S-03', lookupId: 'W9', name: 'Maninagar', defaultScore: 58, defaultStatus: 'Moderate', zone: 'South Zone', points: "435,270 510,265 520,335 445,340", textPos: [450, 305] },
    { id: 'AMC-S-07', lookupId: 'W4', name: 'Isanpur', defaultScore: 63, defaultStatus: 'High', zone: 'South Zone', points: "410,390 490,385 500,460 410,470", textPos: [430, 430] }
  ];

  // Merge live API data with spatial polygons
  const mergedWards = baseWards.map((bw) => {
    const live = liveWards.find((lw) => 
      (lw.id && (lw.id.toLowerCase() === bw.lookupId?.toLowerCase() || lw.id.toLowerCase() === bw.id.toLowerCase())) ||
      (lw.name && lw.name.toLowerCase().includes(bw.name.toLowerCase()))
    );

    let score = bw.defaultScore;
    let status = bw.defaultStatus;

    if (live) {
      if (activeLayer === 'heat' && live.heat_risk) {
        score = Math.round(live.heat_risk.score ?? score);
        status = live.heat_risk.category || status;
      } else if (activeLayer === 'water' && live.water_risk) {
        score = Math.round(live.water_risk.score ?? score);
        status = live.water_risk.category || status;
      } else if (live.combined_risk_score !== undefined) {
        score = Math.round(live.combined_risk_score);
        status = live.combined_risk_category || status;
      }
    }

    // Dynamic color coding based on active layer score
    let fill = "#DCFCE7";
    let stroke = "#86EFAC";
    if (score >= 75) {
      fill = "#FEE2E2";
      stroke = "#DC2626";
    } else if (score >= 55) {
      fill = "#FFEDD5";
      stroke = "#F97316";
    } else if (score >= 40) {
      fill = "#FEF3C7";
      stroke = "#F59E0B";
    }

    return {
      ...bw,
      score,
      status,
      fill,
      stroke,
      liveData: live
    };
  });

  const [hoveredWard, setHoveredWard] = useState(mergedWards[11] || mergedWards[0]);

  const handlePolygonClick = (ward) => {
    setHoveredWard(ward);
    if (onSelectWard) onSelectWard(ward);
  };

  return (
    <div className="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-xs flex flex-col overflow-hidden">
      {/* Map Header & Filter Toolbar */}
      <div className="p-space-md border-b border-outline-variant flex flex-wrap items-center justify-between gap-3 bg-[#F8FAF8]">
        {/* Layer Selector Buttons */}
        <div className="flex items-center bg-[#E5EEFF] p-1 rounded-lg border border-outline-variant overflow-x-auto">
          <button 
            onClick={() => setActiveLayer('combined')}
            className={`px-2.5 py-1 rounded text-[12px] font-semibold transition-all flex items-center gap-1.5 shrink-0 cursor-pointer ${
              activeLayer === 'combined' 
                ? 'bg-surface-container-lowest text-primary shadow-xs' 
                : 'text-on-surface-variant hover:text-primary'
            }`}
          >
            <span className="material-symbols-outlined text-[15px] text-primary fill">layers</span>
            <span>Combined Multi-Hazard</span>
          </button>

          <button 
            onClick={() => setActiveLayer('heat')}
            className={`px-2.5 py-1 rounded text-[12px] transition-all flex items-center gap-1.5 shrink-0 cursor-pointer ${
              activeLayer === 'heat' 
                ? 'bg-surface-container-lowest text-[#DC2626] font-semibold shadow-xs' 
                : 'text-on-surface-variant hover:text-primary'
            }`}
          >
            <span className="material-symbols-outlined text-[15px]">device_thermostat</span>
            <span>Heat Stress (LST)</span>
          </button>

          <button 
            onClick={() => setActiveLayer('water')}
            className={`px-2.5 py-1 rounded text-[12px] transition-all flex items-center gap-1.5 shrink-0 cursor-pointer ${
              activeLayer === 'water' 
                ? 'bg-surface-container-lowest text-[#0284C7] font-semibold shadow-xs' 
                : 'text-on-surface-variant hover:text-primary'
            }`}
          >
            <span className="material-symbols-outlined text-[15px]">water_drop</span>
            <span>Water & Drainage</span>
          </button>

          <button 
            onClick={() => setActiveLayer('svi')}
            className={`px-2.5 py-1 rounded text-[12px] transition-all flex items-center gap-1.5 shrink-0 cursor-pointer ${
              activeLayer === 'svi' 
                ? 'bg-surface-container-lowest text-emerald-800 font-semibold shadow-xs' 
                : 'text-on-surface-variant hover:text-primary'
            }`}
          >
            <span className="material-symbols-outlined text-[15px]">groups</span>
            <span>Social (SVI)</span>
          </button>
        </div>

        {/* Search & Zone Dropdown */}
        <div className="flex items-center gap-2">
          <div className="relative">
            <span className="material-symbols-outlined absolute left-2.5 top-2 text-outline text-[16px]">search</span>
            <input 
              type="text"
              placeholder="Search ward e.g. Danilimda..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-8 pl-8 pr-3 py-1 bg-surface-container-lowest border border-outline-variant rounded-lg text-body-sm text-on-surface placeholder-outline focus:outline-none focus:border-primary w-40 sm:w-48 text-[12px]"
            />
          </div>

          <select 
            value={selectedZone}
            onChange={(e) => setSelectedZone(e.target.value)}
            className="h-8 px-2 bg-surface-container-lowest border border-outline-variant rounded-lg text-body-sm text-on-surface text-[12px] focus:outline-none focus:border-primary cursor-pointer"
          >
            <option>All 7 Zones</option>
            <option>East Zone</option>
            <option>South Zone</option>
            <option>North Zone</option>
            <option>Central Zone</option>
            <option>West Zone</option>
            <option>New West Zone</option>
          </select>
        </div>
      </div>

      {/* Interactive Schematic Map Canvas Area */}
      <div className={`relative bg-[#EFF4EA] h-[520px] w-full overflow-hidden flex items-center justify-center border-b border-outline-variant select-none ${mapType === 'satellite' ? 'filter saturate-75 brightness-95' : ''}`}>
        <svg 
          viewBox="0 0 760 520" 
          fill="none" 
          xmlns="http://www.w3.org/2000/svg" 
          className="w-full h-full max-h-[500px] transition-transform duration-300"
          style={{ transform: `scale(${zoomLevel})` }}
        >
          <defs>
            <pattern id="grid-pattern" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#DCE5DC" strokeWidth="0.5" />
            </pattern>
            <filter id="card-shadow" x="-10%" y="-10%" width="125%" height="125%">
              <feDropShadow dx="0" dy="4" stdDeviation="4" floodColor="#144534" floodOpacity="0.12" />
            </filter>
          </defs>

          {/* Tactical Background Grid */}
          <rect width="760" height="520" fill="url(#grid-pattern)" />

          {/* Sabarmati River Channel */}
          <path 
            d="M 330 0 C 340 80, 310 140, 325 210 C 340 280, 370 330, 360 410 C 350 470, 370 520, 370 520" 
            stroke="#38BDF8" 
            strokeWidth="24" 
            opacity="0.35" 
            strokeLinecap="round" 
            strokeLinejoin="round" 
          />
          <path 
            d="M 330 0 C 340 80, 310 140, 325 210 C 340 280, 370 330, 360 410 C 350 470, 370 520, 370 520" 
            fill="none" 
            stroke="#0284C7" 
            strokeWidth="8" 
            strokeDasharray="8 4" 
            opacity="0.75" 
            strokeLinecap="round" 
          />
          <text 
            x="350" 
            y="70" 
            fill="#0369A1" 
            fontFamily="JetBrains Mono" 
            fontSize="10" 
            fontWeight="600" 
            letterSpacing="2" 
            transform="rotate(78 350 70)"
          >
            SABARMATI RIVER
          </text>

          {/* Ward Polygons */}
          {mergedWards.map((ward) => {
            const isMatch = !searchQuery || ward.name.toLowerCase().includes(searchQuery.toLowerCase());
            const opacity = isMatch ? "1" : "0.3";
            const isSelected = hoveredWard?.name === ward.name;

            return (
              <g key={ward.id} opacity={opacity} className="cursor-pointer" onClick={() => handlePolygonClick(ward)}>
                <polygon 
                  points={ward.points} 
                  fill={ward.fill} 
                  stroke={isSelected ? "#002E20" : ward.stroke} 
                  strokeWidth={isSelected ? "3" : "1.8"} 
                  className="transition hover:opacity-80"
                />
                <text 
                  x={ward.textPos[0]} 
                  y={ward.textPos[1]} 
                  fill={ward.score >= 70 ? "#991B1B" : ward.score >= 50 ? "#C2410C" : "#14532D"} 
                  fontFamily="Inter" 
                  fontSize={ward.score >= 70 ? "11" : "10"} 
                  fontWeight={ward.score >= 70 ? "700" : "600"}
                >
                  {ward.name} ({ward.score})
                </text>

                {/* Pulsing indicator for Critical Wards */}
                {(ward.isCritical || ward.score >= 75) && ward.center && (
                  <>
                    <circle cx={ward.center[0]} cy={ward.center[1]} r="5" fill="#B91C1C" />
                    <circle 
                      cx={ward.center[0]} 
                      cy={ward.center[1]} 
                      r="12" 
                      fill="none" 
                      stroke="#DC2626" 
                      strokeWidth="1.5" 
                      opacity="0.6"
                      className="animate-ping origin-center"
                    />
                  </>
                )}
              </g>
            );
          })}
        </svg>

        {/* Floating Inspection Card Over Selected Ward */}
        {hoveredWard && (
          <div className="absolute bottom-4 sm:bottom-6 left-4 sm:left-6 w-72 sm:w-80 bg-surface-container-lowest border border-outline rounded-xl p-3 sm:p-3.5 shadow-lg z-30">
            <div className="flex items-center justify-between pb-2 border-b border-outline-variant">
              <div className="flex items-center gap-1.5 min-w-0">
                <span className="w-2.5 h-2.5 rounded-full bg-error animate-ping shrink-0"></span>
                <span className="font-title-sm text-title-sm text-on-surface font-bold truncate">
                  {hoveredWard.name} ({hoveredWard.id})
                </span>
              </div>
              <span className={`px-1.5 py-0.5 rounded font-mono text-[10px] font-bold shrink-0 ${
                hoveredWard.score >= 70 ? 'bg-error-container text-on-error-container' : 'bg-amber-100 text-amber-800'
              }`}>
                {hoveredWard.status} {hoveredWard.score}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-2 text-[11px]">
              <div>
                <span className="text-outline block font-mono text-[9px] uppercase">Jurisdiction</span>
                <span className="font-bold text-on-surface font-mono truncate block">{hoveredWard.zone}</span>
              </div>
              <div>
                <span className="text-outline block font-mono text-[9px] uppercase">Layer Risk Score</span>
                <span className="font-bold text-error font-mono">{hoveredWard.score} / 100</span>
              </div>
              <div>
                <span className="text-outline block font-mono text-[9px] uppercase">Active Layer</span>
                <span className="font-bold text-[#0284C7] font-mono capitalize">{activeLayer}</span>
              </div>
              <div>
                <span className="text-outline block font-mono text-[9px] uppercase">Assessment</span>
                <span className="font-bold text-primary font-mono">{hoveredWard.liveData ? 'Live API Synced' : 'Baseline Priors'}</span>
              </div>
            </div>

            <div className="mt-2.5 pt-2 border-t border-outline-variant flex items-center justify-between">
              <span className="text-[10px] text-on-surface-variant truncate max-w-[170px]">
                {hoveredWard.liveData?.ranking_rationale || hoveredWard.liveData?.action_recommendation || 'Municipal Climate Risk Telemetry'}
              </span>
              <button 
                onClick={() => onInspectWard && onInspectWard(hoveredWard.liveData || hoveredWard)}
                className="text-primary hover:underline font-mono text-[11px] font-bold flex items-center gap-0.5 cursor-pointer"
              >
                <span>Open Dossier</span>
                <span className="material-symbols-outlined text-[12px]">open_in_new</span>
              </button>
            </div>
          </div>
        )}

        {/* Map HUD Controls Overlay (Top-Right) */}
        <div className="absolute top-4 right-4 flex flex-col gap-2 z-20">
          <div className="bg-surface-container-lowest border border-outline-variant rounded-lg shadow-xs flex flex-col p-1">
            <button 
              onClick={() => setZoomLevel((z) => Math.min(1.6, z + 0.15))}
              className="w-7 h-7 flex items-center justify-center hover:bg-surface-container-low text-on-surface rounded text-sm font-bold cursor-pointer"
              title="Zoom In"
            >
              <span className="material-symbols-outlined text-[16px]">add</span>
            </button>
            <div className="h-px bg-outline-variant my-0.5" />
            <button 
              onClick={() => setZoomLevel((z) => Math.max(0.8, z - 0.15))}
              className="w-7 h-7 flex items-center justify-center hover:bg-surface-container-low text-on-surface rounded text-sm font-bold cursor-pointer"
              title="Zoom Out"
            >
              <span className="material-symbols-outlined text-[16px]">remove</span>
            </button>
          </div>

          <button 
            onClick={() => setZoomLevel(1)}
            className="w-7 h-7 bg-surface-container-lowest border border-outline-variant rounded-lg shadow-xs flex items-center justify-center hover:bg-surface-container-low text-on-surface cursor-pointer" 
            title="Reset Map View"
          >
            <span className="material-symbols-outlined text-[16px]">restart_alt</span>
          </button>

          <button 
            onClick={() => setMapType(mapType === 'carto' ? 'satellite' : 'carto')}
            className="w-7 h-7 bg-surface-container-lowest border border-outline-variant rounded-lg shadow-xs flex items-center justify-center hover:bg-surface-container-low text-primary cursor-pointer" 
            title="Toggle Municipal Carto / Satellite"
          >
            <span className="material-symbols-outlined text-[16px]">public</span>
          </button>
        </div>

        {/* Map Legend Overlay (Top-Left) */}
        <div className="absolute top-4 left-4 bg-surface-container-lowest/95 backdrop-blur-xs border border-outline-variant rounded-lg p-2.5 shadow-xs text-[11px] z-20 hidden sm:block">
          <span className="font-mono text-[9px] font-bold uppercase tracking-wider text-outline block mb-1.5">Composite Risk Index</span>
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-red-600 border border-red-700"></span>
              <span className="font-mono text-[10px] text-on-surface font-semibold">Critical (75 - 100%)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-orange-400 border border-orange-500"></span>
              <span className="font-mono text-[10px] text-on-surface">High (55 - 74%)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-amber-200 border border-amber-400"></span>
              <span className="font-mono text-[10px] text-on-surface">Moderate (40 - 54%)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-emerald-200 border border-emerald-400"></span>
              <span className="font-mono text-[10px] text-on-surface">Low (&lt; 40%)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Map Strip */}
      <div className="px-space-md py-2 bg-[#F8FAF8] flex flex-col sm:flex-row sm:items-center justify-between text-outline font-mono text-[10px] gap-1">
        <span>Projection: EPSG 4326 (WGS84) | AMC GIS Cartography v4.2</span>
        <span>Spatial Extent: 23.0225° N, 72.5714° E (Ahmedabad Urban Agglomeration)</span>
      </div>
    </div>
  );
}
