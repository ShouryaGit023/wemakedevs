import React from 'react';
import { TOP_RISK_WARDS } from '../data/mockData';

export default function TopWardsTable({ onInspectWard }) {
  return (
    <div className="bg-surface-container-lowest rounded-xl border border-outline-variant shadow-xs overflow-hidden">
      {/* Table Header Strip */}
      <div className="px-space-md py-space-sm border-b border-outline-variant flex items-center justify-between bg-[#F8FAF8]">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-error text-[18px]">priority_high</span>
          <h3 className="font-title-sm text-title-sm text-primary font-bold">Top 5 Highest-Risk Priority Wards</h3>
        </div>
        <span className="font-mono text-[10px] text-outline uppercase font-semibold">Auto-Ranked</span>
      </div>

      {/* Table Body */}
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
            {TOP_RISK_WARDS.map((ward) => (
              <tr key={ward.ward_id} className="hover:bg-[#F8FAF8] transition-colors">
                <td className="py-2 px-3">
                  <div className="font-bold text-on-surface text-xs">{ward.rank}. {ward.name}</div>
                  <div className="font-mono text-[10px] text-outline">{ward.zone}</div>
                </td>
                <td className="py-2 px-2 text-right">
                  <div className="flex items-baseline justify-end gap-0.5">
                    <span className={`font-mono text-[13px] font-bold ${ward.composite_score >= 88 ? 'text-error' : 'text-amber-700'}`}>
                      {ward.composite_score}
                    </span>
                    <span className="text-outline font-mono text-[10px]">/100</span>
                  </div>
                  <span className={`block font-mono text-[9px] font-bold uppercase ${ward.composite_score >= 88 ? 'text-red-600' : 'text-amber-700'}`}>
                    {ward.status}
                  </span>
                </td>
                <td className="py-2 px-3">
                  <div className="text-[11px] text-on-surface leading-tight font-medium">
                    {ward.primary_factor}
                  </div>
                  <div className={`font-mono text-[10px] mt-0.5 ${ward.composite_score >= 88 ? 'text-error' : 'text-outline'}`}>
                    {ward.detail}
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
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
