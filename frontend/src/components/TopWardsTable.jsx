import React from 'react';

export default function TopWardsTable({ wards = [], loading = false, error = null, onRetry, onInspectWard }) {
  return (
    <div className="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-xs overflow-hidden">
      {/* Table Header Strip */}
      <div className="px-space-md py-space-sm border-b border-outline-variant flex items-center justify-between bg-[#F8FAF8]">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-error text-[18px]">priority_high</span>
          <h3 className="font-title-sm text-title-sm text-primary font-bold">Top Highest-Risk Priority Wards</h3>
        </div>
        <div className="flex items-center gap-2">
          {loading && (
            <span className="font-mono text-[10px] text-primary flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-primary animate-ping"></span>
              Live Sync
            </span>
          )}
          <span className="font-mono text-[10px] text-outline uppercase font-semibold">Auto-Ranked</span>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-4 bg-red-50 text-error text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[16px]">error</span>
            <span>Failed to load live ward rankings: {error}</span>
          </div>
          {onRetry && (
            <button 
              onClick={onRetry}
              className="px-2 py-1 bg-white border border-red-200 text-error rounded font-mono font-semibold hover:bg-red-50"
            >
              Retry
            </button>
          )}
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && wards.length === 0 && (
        <div className="p-6 text-center space-y-2">
          <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto"></div>
          <span className="text-xs text-outline font-mono">Computing Multi-Hazard IPCC Risk Engine...</span>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && wards.length === 0 && (
        <div className="p-6 text-center text-xs text-outline font-mono">
          No ward risk assessments recorded.
        </div>
      )}

      {/* Table Body */}
      {wards.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-outline-variant bg-[#F8FAF8] text-[10px] uppercase font-mono text-outline">
                <th className="py-2 px-3">Ward & Zone</th>
                <th className="py-2 px-2 text-right">Composite</th>
                <th className="py-2 px-3">Primary Risk Factor</th>
                <th className="py-2 px-2 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant font-body-sm text-body-sm">
              {wards.slice(0, 5).map((ward, idx) => {
                const rank = ward.rank || idx + 1;
                const score = Math.round(ward.combined_risk_score ?? ward.composite_score ?? 0);
                const status = ward.combined_risk_category || ward.status || (score >= 80 ? 'CRITICAL' : score >= 50 ? 'HIGH' : 'MODERATE');
                const primaryFactor = ward.ranking_rationale || ward.action_recommendation || ward.primary_factor || 'Thermal Stress & Pluvial Runoff';
                const detail = ward.heat_risk?.explanation 
                  ? `WBGT: ${ward.heat_risk.effective_wbgt_c ?? ward.heat_risk.score}°C • Water: ${ward.water_risk?.score ?? 0}`
                  : (ward.detail || `Score: ${score}/100`);
                const zone = ward.zone || ward.official_name || 'Ahmedabad Municipal Ward';

                return (
                  <tr key={ward.id || ward.ward_id || idx} className="hover:bg-[#F8FAF8] transition-colors">
                    <td className="py-2 px-3">
                      <div className="font-bold text-on-surface text-xs">{rank}. {ward.name}</div>
                      <div className="font-mono text-[10px] text-outline truncate max-w-[140px]" title={zone}>{zone}</div>
                    </td>
                    <td className="py-2 px-2 text-right">
                      <div className="flex items-baseline justify-end gap-0.5">
                        <span className={`font-mono text-[13px] font-bold ${score >= 70 ? 'text-error' : score >= 45 ? 'text-amber-700' : 'text-[#059669]'}`}>
                          {score}
                        </span>
                        <span className="text-outline font-mono text-[10px]">/100</span>
                      </div>
                      <span className={`block font-mono text-[9px] font-bold uppercase ${score >= 70 ? 'text-red-600' : score >= 45 ? 'text-amber-700' : 'text-[#059669]'}`}>
                        {status}
                      </span>
                    </td>
                    <td className="py-2 px-3">
                      <div className="text-[11px] text-on-surface leading-tight font-medium line-clamp-1" title={primaryFactor}>
                        {primaryFactor}
                      </div>
                      <div className={`font-mono text-[10px] mt-0.5 truncate max-w-[200px] ${score >= 70 ? 'text-error' : 'text-outline'}`} title={detail}>
                        {detail}
                      </div>
                    </td>
                    <td className="py-2 px-2 text-center">
                      <button 
                        onClick={() => onInspectWard && onInspectWard(ward)}
                        className="px-2.5 py-1 rounded bg-[#F0F5F1] hover:bg-[#E1EDE3] text-primary font-mono text-[11px] font-bold border border-outline-variant transition-colors cursor-pointer"
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
