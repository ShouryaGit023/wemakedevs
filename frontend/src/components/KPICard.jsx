import React from 'react';

export default function KPICard({ 
  title, 
  icon, 
  value, 
  unit, 
  subtitle, 
  delta, 
  progress, 
  isDanger, 
  isWarning, 
  isSuccess, 
  isInfo,
  tag
}) {
  return (
    <div className={`
      bg-surface-container-lowest p-space-md rounded-xl border shadow-xs 
      flex flex-col justify-between transition-all hover:shadow-sm
      ${isDanger ? 'border-red-200 bg-gradient-to-br from-white to-red-50/20' : 'border-outline-variant'}
    `}>
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] uppercase font-bold tracking-wider text-on-surface-variant">
          {title}
        </span>
        {icon && (
          <span className={`material-symbols-outlined text-[18px] ${
            isDanger ? 'text-error' :
            isWarning ? 'text-amber-600' :
            isSuccess ? 'text-primary' :
            isInfo ? 'text-[#0284C7]' :
            'text-outline'
          }`}>
            {icon}
          </span>
        )}
      </div>

      {/* Main Metric Value */}
      <div className="mt-2.5">
        <div className="flex items-baseline gap-2">
          <span className={`
            leading-none font-bold tracking-tight tabular-nums
            ${typeof value === 'number' || (typeof value === 'string' && value.length <= 4) ? 'text-display-lg font-display-lg' : 'text-headline-md font-headline-md'}
            ${isDanger ? 'text-error' :
              isWarning ? 'text-amber-700' :
              isSuccess ? 'text-primary' :
              isInfo ? 'text-[#075985]' :
              'text-primary'}
          `}>
            {value}
          </span>
          {unit && (
            <span className="font-body-md text-body-md text-outline font-medium">
              {unit}
            </span>
          )}
        </div>

        {/* Subtitle & Delta / Tag Pill */}
        <div className="mt-2 flex items-center justify-between text-[11px]">
          {subtitle && (
            <span className="text-on-surface-variant font-medium truncate" title={subtitle}>
              {subtitle}
            </span>
          )}

          {delta && (
            <span className={`font-mono text-[10px] px-1.5 py-0.5 rounded font-semibold shrink-0 ml-1.5 ${
              isDanger ? 'bg-error-container text-on-error-container' :
              isWarning ? 'bg-amber-100 text-amber-800' :
              'bg-emerald-100 text-emerald-800'
            }`}>
              {delta}
            </span>
          )}

          {tag && (
            <span className={`font-mono text-[10px] px-1.5 py-0.5 rounded font-semibold shrink-0 ml-1.5 ${
              isDanger ? 'bg-red-100 text-red-800' :
              isWarning ? 'bg-amber-100 text-amber-800' :
              isInfo ? 'bg-blue-100 text-blue-800' :
              'bg-[#ECFDF5] text-[#065F46] border border-[#A7F3D0]'
            }`}>
              {tag}
            </span>
          )}
        </div>

        {/* Optional Progress Rail */}
        {typeof progress === 'number' && (
          <div className="w-full bg-surface-container h-1.5 rounded-full mt-2.5 overflow-hidden">
            <div 
              className={`h-full rounded-full transition-all duration-500 ${
                isDanger ? 'bg-error' :
                isWarning ? 'bg-amber-600' :
                isSuccess ? 'bg-[#059669]' :
                'bg-primary-container'
              }`}
              style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
            />
          </div>
        )}
      </div>
    </div>
  );
}
