import React, { useState } from 'react';

export default function AhmedabadVectorMap({ onSelectWard, onInspectWard }) {
  const [activeLayer, setActiveLayer] = useState('combined');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedZone, setSelectedZone] = useState('All 7 Zones');
  const [hoveredWard, setHoveredWard] = useState({
    id: 'AMC-S-14',
    name: 'Danilimda Ward',
    score: 88,
    status: 'CRITICAL',
    population: '184,200',
    heatVulnerability: '92 / 100',
    waterDeficit: '-24% Required',
    coolingCenters: '3 Operational',
    primaryHazard: 'Compound Industrial Heat & Canal Inundation'
  });
  const [zoomLevel, setZoomLevel] = useState(1);
  const [mapType, setMapType] = useState('carto');

  const wardsData = [
    // West & North-West
    { id: 'AMC-NW-01', name: 'Thaltej', score: 28, status: 'Low', zone: 'New West Zone', points: "110,90 190,80 230,130 170,170 90,140", textPos: [135, 130], fill: "#DCFCE7", stroke: "#86EFAC" },
    { id: 'AMC-W-02', name: 'Navrangpura', score: 34, status: 'Low', zone: 'West Zone', points: "190,80 280,95 290,170 230,180 230,130", textPos: [215, 145], fill: "#DCFCE7", stroke: "#16A34A" },
    { id: 'AMC-W-03', name: 'Paldi', score: 46, status: 'Moderate', zone: 'West Zone', points: "230,180 300,180 320,250 240,260 210,210", textPos: [245, 225], fill: "#FEF3C7", stroke: "#FBBF24" },
    { id: 'AMC-SW-04', name: 'Vasna', score: 52, status: 'Moderate', zone: 'South West Zone', points: "240,260 320,250 335,340 260,350 220,300", textPos: [260, 305], fill: "#FEF3C7", stroke: "#F59E0B" },
    { id: 'AMC-SW-05', name: 'Sarkhej', score: 42, status: 'Moderate', zone: 'South West Zone', points: "110,240 220,240 240,340 160,370 90,290", textPos: [140, 300], fill: "#DCFCE7", stroke: "#86EFAC" },
    // North & Central
    { id: 'AMC-N-01', name: 'Chandkheda', score: 48, status: 'Moderate', zone: 'North Zone', points: "280,30 360,20 400,80 320,95", textPos: [320, 60], fill: "#FEF3C7", stroke: "#FBBF24" },
    { id: 'AMC-C-02', name: 'Shahibaug', score: 67, status: 'High', zone: 'Central Zone', points: "340,110 430,100 450,170 350,180", textPos: [365, 145], fill: "#FFEDD5", stroke: "#F97316" },
    { id: 'AMC-C-03', name: 'Jamalpur', score: 78, status: 'High', zone: 'Central Zone', points: "325,200 400,190 420,270 340,270", textPos: [345, 235], fill: "#FFEDD5", stroke: "#EA580C" },
    // East Critical Cluster
    { id: 'AMC-N-06', name: 'Bapunagar', score: 84, status: 'High', zone: 'North Zone', points: "450,100 540,85 570,165 470,170", textPos: [480, 130], fill: "#FEE2E2", stroke: "#DC2626" },
    { id: 'AMC-E-04', name: 'GOMTIPUR', score: 91, status: 'Critical', zone: 'East Zone', points: "440,180 540,170 560,250 450,260", textPos: [465, 215], fill: "#FEE2E2", stroke: "#B91C1C", isCritical: true, center: [495, 230] },
    { id: 'AMC-E-08', name: 'Odhav', score: 85, status: 'High', zone: 'East Zone', points: "555,140 660,130 680,230 575,235", textPos: [590, 185], fill: "#FEE2E2", stroke: "#DC2626", center: [620, 200] },
    // South / South-East
    { id: 'AMC-S-14', name: 'DANILIMDA', score: 88, status: 'Critical', zone: 'South Zone', points: "350,285 450,280 470,380 370,390", textPos: [380, 335], fill: "#FEE2E2", stroke: "#B91C1C", isCritical: true, center: [410, 355] },
    { id: 'AMC-S-09', name: 'Vatva', score: 81, status: 'High', zone: 'South Zone', points: "470,340 590,320 620,420 490,430", textPos: [515, 380], fill: "#FEE2E2", stroke: "#DC2626", center: [545, 380] },
    { id: 'AMC-S-03', name: 'Maninagar', score: 58, status: 'Moderate', zone: 'South Zone', points: "435,270 510,265 520,335 445,340", textPos: [450, 305], fill: "#FEF3C7", stroke: "#F59E0B" },
    { id: 'AMC-S-07', name: 'Isanpur', score: 63, status: 'High', zone: 'South Zone', points: "410,390 490,385 500,460 410,470", textPos: [430, 430], fill: "#FFEDD5", stroke: "#F97316" }
  ];

  const handlePolygonClick = (ward) => {
    const updated = {
      id: ward.id,
      name: `${ward.name} Ward`,
      score: ward.score,
      status: ward.status.toUpperCase(),
      population: ward.score > 80 ? '172,000' : '145,000',
      heatVulnerability: `${ward.score} / 100`,
      waterDeficit: ward.score > 80 ? '-22% Required' : '-8% Required',
      coolingCenters: ward.score > 80 ? '3 Operational' : '5 Operational',
      primaryHazard: ward.score > 85 ? 'Critical Heat Island & Informal Settlement' : 'Elevated Ambient Heat & Drainage Stress'
    };
    setHoveredWard(updated);
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
            className={`px-2.5 py-1 rounded text-[12px] font-semibold transition-all flex items-center gap-1.5 shrink-0 ${
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
            className={`px-2.5 py-1 rounded text-[12px] transition-all flex items-center gap-1.5 shrink-0 ${
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
            className={`px-2.5 py-1 rounded text-[12px] transition-all flex items-center gap-1.5 shrink-0 ${
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
            className={`px-2.5 py-1 rounded text-[12px] transition-all flex items-center gap-1.5 shrink-0 ${
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
              placeholder="Search ward e.g. Gomtipur..."
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
        {/* SVG Map Schematic of Ahmedabad Wards & River */}
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

          {/* Sabarmati River Channel cutting North-South through Ahmedabad */}
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
          {wardsData.map((ward) => {
            const isMatch = !searchQuery || ward.name.toLowerCase().includes(searchQuery.toLowerCase());
            const opacity = isMatch ? "1" : "0.3";
            const isSelected = hoveredWard?.id === ward.id;

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
                  fill={ward.score >= 80 ? "#991B1B" : ward.score >= 60 ? "#C2410C" : ward.score >= 40 ? "#92400E" : "#14532D"} 
                  fontFamily="Inter" 
                  fontSize={ward.score >= 80 ? "11" : "10"} 
                  fontWeight={ward.score >= 80 ? "700" : "600"}
                >
                  {ward.name} ({ward.score})
                </text>

                {/* Pulsing indicator for Critical Wards */}
                {ward.isCritical && ward.center && (
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

        {/* Floating Inspection Card Over Danilimda/Selected Ward */}
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
                hoveredWard.score >= 80 ? 'bg-error-container text-on-error-container' : 'bg-amber-100 text-amber-800'
              }`}>
                {hoveredWard.status} {hoveredWard.score}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-2 text-[11px]">
              <div>
                <span className="text-outline block font-mono text-[9px] uppercase">Population</span>
                <span className="font-bold text-on-surface font-mono">{hoveredWard.population}</span>
              </div>
              <div>
                <span className="text-outline block font-mono text-[9px] uppercase">Heat Vulnerability</span>
                <span className="font-bold text-error font-mono">{hoveredWard.heatVulnerability}</span>
              </div>
              <div>
                <span className="text-outline block font-mono text-[9px] uppercase">Potable Water Deficit</span>
                <span className="font-bold text-error font-mono">{hoveredWard.waterDeficit}</span>
              </div>
              <div>
                <span className="text-outline block font-mono text-[9px] uppercase">Cooling Centers</span>
                <span className="font-bold text-primary font-mono">{hoveredWard.coolingCenters}</span>
              </div>
            </div>

            <div className="mt-2.5 pt-2 border-t border-outline-variant flex items-center justify-between">
              <span className="text-[10px] text-on-surface-variant truncate max-w-[170px]" title={hoveredWard.primaryHazard}>
                {hoveredWard.primaryHazard}
              </span>
              <button 
                onClick={() => onInspectWard && onInspectWard(hoveredWard)}
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
              <span className="font-mono text-[10px] text-on-surface font-semibold">Critical (80 - 100%)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-orange-400 border border-orange-500"></span>
              <span className="font-mono text-[10px] text-on-surface">High (60 - 79%)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-amber-200 border border-amber-400"></span>
              <span className="font-mono text-[10px] text-on-surface">Moderate (40 - 59%)</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded bg-emerald-200 border border-emerald-400"></span>
              <span className="font-mono text-[10px] text-on-surface">Low (&lt; 40%)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Map Strip: GIS Telemetry Metadata */}
      <div className="px-space-md py-2 bg-[#F8FAF8] flex flex-col sm:flex-row sm:items-center justify-between text-outline font-mono text-[10px] gap-1">
        <span>Projection: EPSG 4326 (WGS84) | AMC GIS Cartography v4.2</span>
        <span>Spatial Extent: 23.0225° N, 72.5714° E (Ahmedabad Urban Agglomeration)</span>
      </div>
    </div>
  );
}
