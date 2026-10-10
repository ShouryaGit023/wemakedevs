import React from 'react';

export default function SystemStatusPage() {
  const systems = [
    { name: "Ahmedabad Municipal Telemetry Mesh", status: "Operational", ping: "24ms", desc: "48 of 48 municipal IoT pods transmitting real-time microclimate feeds" },
    { name: "Open-Meteo WBGT High-Res Forecast Grid", status: "Operational", ping: "94ms", desc: "10-day hourly forecast ingested with physical solar radiation correction" },
    { name: "USGS Landsat-9 TIRS Thermal Ingestion", status: "Operational", ping: "180ms", desc: "100m Land Surface Temperature (LST) cross-validation calibrated" },
    { name: "IMD Doppler Weather Radar (Ahmedabad Station)", status: "Operational", ping: "42ms", desc: "Precipitation surge and cloud cover telemetry synced" },
    { name: "EPA SWMM Hydrodynamic Run Engine", status: "Operational", ping: "310ms", desc: "Urban drainage surcharge and Kharicut canal simulation active" },
    { name: "108 EMRI Emergency Surveillance Feed", status: "Operational", ping: "65ms", desc: "Daily heatstroke and clinical dehydration admissions live-streamed" }
  ];

  return (
    <div className="space-y-6">
      <div className="pb-2 border-b border-outline-variant">
        <div className="flex items-center gap-2 font-mono text-[10px] text-outline mb-0.5 uppercase tracking-wider">
          <span>AMC Command Center</span>
          <span>/</span>
          <span className="text-primary font-bold">Data & System Status</span>
        </div>
        <h1 className="text-headline-md font-headline-md text-primary font-bold">
          Telemetry Feeds, Satellite Ingestion & Model Health
        </h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {systems.map((s, idx) => (
          <div key={idx} className="bg-surface-container-lowest p-4 rounded-xl border border-outline-variant shadow-xs space-y-2">
            <div className="flex items-center justify-between">
              <span className="w-2.5 h-2.5 rounded-full bg-[#059669] animate-pulse"></span>
              <span className="font-mono text-[11px] text-emerald-800 font-bold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                {s.status} ({s.ping})
              </span>
            </div>
            <h3 className="font-bold text-sm text-primary">{s.name}</h3>
            <p className="text-xs text-on-surface-variant leading-relaxed">{s.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
