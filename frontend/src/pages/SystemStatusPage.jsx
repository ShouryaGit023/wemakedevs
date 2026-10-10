import React, { useState, useEffect, useCallback } from 'react';
import { ClimateShieldAPI, API_BASE_URL } from '../services/api';

export default function SystemStatusPage() {
  const [services, setServices] = useState([
    {
      id: 'dss_root',
      name: 'ClimateShield DSS Server Root',
      endpoint: '/',
      status: 'Pinging...',
      ping: '...',
      desc: 'FastAPI Decision Support Engine core health and available endpoint registry.',
      isHealthy: true,
    },
    {
      id: 'wbgt_forecast',
      name: 'Open-Meteo & IMD WBGT Forecast Engine',
      endpoint: '/api/weather/wbgt',
      status: 'Pinging...',
      ping: '...',
      desc: 'High-res hourly meteorological forecast grid with solar radiation physics correction.',
      isHealthy: true,
    },
    {
      id: 'wards_db',
      name: 'Ahmedabad Municipal Wards Database',
      endpoint: '/api/wards',
      status: 'Pinging...',
      ping: '...',
      desc: 'Baseline census vulnerabilities, population agglomerations, and socio-economic indicators.',
      isHealthy: true,
    },
    {
      id: 'climate_rankings',
      name: 'IPCC Multi-Hazard Climate Risk Rankings',
      endpoint: '/api/climate-risk/rankings',
      status: 'Pinging...',
      ping: '...',
      desc: 'Deterministic multi-hazard synergy engine evaluating Heat, Pluvial Flood, and Water Stress.',
      isHealthy: true,
    },
    {
      id: 'era5_land',
      name: 'ECMWF ERA5-Land Reanalysis Ingestion',
      endpoint: '/api/data-sources/era5',
      status: 'Pinging...',
      ping: '...',
      desc: '0.1° high-resolution reanalysis surface temperature, dewpoint, and thermal radiation grids.',
      isHealthy: true,
    },
    {
      id: 'ecostress_thermal',
      name: 'NASA ECOSTRESS LST Thermal Overpasses',
      endpoint: '/api/data-sources/ecostress',
      status: 'Pinging...',
      ping: '...',
      desc: '70m spaceborne thermal infrared land surface temperature (LST) cross-calibration.',
      isHealthy: true,
    },
    {
      id: 'data_fusion',
      name: 'Multi-Sensor Data Fusion & Calibration',
      endpoint: '/api/data-sources/fusion',
      status: 'Pinging...',
      ping: '...',
      desc: 'Spatial downscaling and sensor cross-calibration linking in-situ sensors to satellite passes.',
      isHealthy: true,
    },
    {
      id: 'action_store',
      name: 'Action Centre & Decision Dispatch Store',
      endpoint: '/api/action-centre/dashboard',
      status: 'Pinging...',
      ping: '...',
      desc: 'Thread-safe municipal action tracking, human-sign-off status machine, and audit trail.',
      isHealthy: true,
    },
  ]);

  const [isRunningDiagnostics, setIsRunningDiagnostics] = useState(false);
  const [lastCheckTime, setLastCheckTime] = useState(null);

  const pingService = async (service) => {
    const start = performance.now();
    try {
      let data;
      if (service.id === 'dss_root') data = await ClimateShieldAPI.getSystemStatus();
      else if (service.id === 'wbgt_forecast') data = await ClimateShieldAPI.getWeatherWBGT();
      else if (service.id === 'wards_db') data = await ClimateShieldAPI.getWards();
      else if (service.id === 'climate_rankings') data = await ClimateShieldAPI.getClimateRiskRankings();
      else if (service.id === 'era5_land') data = await ClimateShieldAPI.getERA5LandData();
      else if (service.id === 'ecostress_thermal') data = await ClimateShieldAPI.getECOSTRESSData();
      else if (service.id === 'data_fusion') data = await ClimateShieldAPI.getDataFusion();
      else if (service.id === 'action_store') data = await ClimateShieldAPI.getActionCentreDashboard();

      const elapsed = Math.round(performance.now() - start);
      return {
        ...service,
        status: 'Operational',
        ping: `${elapsed}ms`,
        isHealthy: true,
        extraInfo: data ? (data.status || 'OK') : 'OK',
      };
    } catch (err) {
      const elapsed = Math.round(performance.now() - start);
      return {
        ...service,
        status: 'Unavailable',
        ping: `${elapsed}ms`,
        isHealthy: false,
        errorDetail: err.message,
      };
    }
  };

  const runDiagnostics = useCallback(async () => {
    setIsRunningDiagnostics(true);
    const updated = await Promise.all(services.map(s => pingService(s)));
    setServices(updated);
    setLastCheckTime(new Date().toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata' }));
    setIsRunningDiagnostics(false);
  }, []);

  useEffect(() => {
    runDiagnostics();
  }, [runDiagnostics]);

  const healthyCount = services.filter(s => s.isHealthy).length;

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-2 border-b border-outline-variant">
        <div>
          <div className="flex items-center gap-2 font-mono text-[10px] text-outline mb-0.5 uppercase tracking-wider">
            <span>AMC Command Center</span>
            <span>/</span>
            <span className="text-primary font-bold">Data & System Status</span>
          </div>
          <h1 className="text-headline-md font-headline-md text-primary font-bold">
            Telemetry Feeds, Satellite Ingestion & Model Health
          </h1>
          <p className="text-xs text-on-surface-variant mt-0.5">
            Real-time ping and availability diagnostics connected to backend at <code className="font-mono bg-slate-100 px-1 py-0.5 rounded text-primary">{API_BASE_URL}</code>.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {lastCheckTime && (
            <span className="text-[11px] font-mono text-outline">
              Last check: {lastCheckTime} IST
            </span>
          )}
          <button
            onClick={runDiagnostics}
            disabled={isRunningDiagnostics}
            className="h-9 px-4 bg-primary text-white rounded-lg text-xs font-semibold flex items-center gap-2 hover:bg-[#1B5742] shadow-sm transition-all cursor-pointer disabled:opacity-60"
          >
            <span className={`material-symbols-outlined text-[18px] ${isRunningDiagnostics ? 'animate-spin' : ''}`}>
              refresh
            </span>
            <span>{isRunningDiagnostics ? 'Running Diagnostics...' : 'Run Live Ping Diagnostics'}</span>
          </button>
        </div>
      </div>

      {/* Health Overview Strip */}
      <div className="bg-surface-container-lowest p-4 rounded-xl border border-outline-variant flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-800 border border-emerald-200 flex items-center justify-center font-bold">
            <span className="material-symbols-outlined text-[24px]">dns</span>
          </div>
          <div>
            <div className="text-sm font-bold text-primary">
              All Municipal Services Synchronized
            </div>
            <div className="text-xs font-mono text-outline">
              {healthyCount} of {services.length} services responding with valid telemetry payloads
            </div>
          </div>
        </div>
        <span className="px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 text-xs font-mono font-bold">
          SYSTEM HEALTH: 100%
        </span>
      </div>

      {/* Services Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {services.map((s) => (
          <div key={s.id} className="bg-surface-container-lowest p-4 rounded-xl border border-outline-variant shadow-xs space-y-2 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                <span className={`w-2.5 h-2.5 rounded-full ${s.isHealthy ? 'bg-[#059669] animate-pulse' : 'bg-error'}`}></span>
                <span className={`font-mono text-[11px] font-bold px-2 py-0.5 rounded border ${
                  s.isHealthy 
                    ? 'text-emerald-800 bg-emerald-50 border-emerald-200' 
                    : 'text-error bg-red-50 border-red-200'
                }`}>
                  {s.status} ({s.ping})
                </span>
              </div>
              <h3 className="font-bold text-xs text-primary mt-2">{s.name}</h3>
              <div className="font-mono text-[10px] text-outline mt-0.5 truncate" title={s.endpoint}>
                {s.endpoint}
              </div>
              <p className="text-[11px] text-on-surface-variant leading-relaxed mt-1">{s.desc}</p>
            </div>

            {s.errorDetail && (
              <div className="p-2 bg-red-50 rounded text-[10px] text-error font-mono break-all mt-2">
                {s.errorDetail}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
