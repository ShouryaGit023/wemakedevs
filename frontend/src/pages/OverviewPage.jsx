import React from 'react';
import KPICard from '../components/KPICard';
import AhmedabadVectorMap from '../components/AhmedabadVectorMap';
import TopWardsTable from '../components/TopWardsTable';
import { EXECUTIVE_KPIS } from '../data/mockData';

export default function OverviewPage({ onOpenAdvisory, onInspectWard }) {
  const handleExportPDF = () => {
    alert("Exporting official AMC Ward Climate Situation Report (PDF) with current telemetry telemetry logs.");
  };

  return (
    <div className="space-y-space-md">
      {/* Header & Breadcrumbs & Executive Actions */}
      <section className="space-y-space-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 font-mono text-[10px] text-outline mb-0.5 uppercase tracking-wider">
              <span>AMC Command Center</span>
              <span className="text-outline-variant">/</span>
              <span>ClimateShield</span>
              <span className="text-outline-variant">/</span>
              <span className="text-primary font-bold">Overview</span>
            </div>
            <h1 className="font-headline-lg text-headline-lg-mobile md:text-headline-lg text-primary tracking-tight font-bold">
              Ahmedabad Climate Vulnerability & Incident Overview
            </h1>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button 
              onClick={handleExportPDF}
              className="h-9 px-3.5 bg-surface-container-lowest border border-outline-variant hover:bg-[#F8FAF8] rounded-lg font-title-sm text-title-sm text-primary flex items-center gap-2 shadow-xs transition-all cursor-pointer"
            >
              <span className="material-symbols-outlined text-[18px]">picture_as_pdf</span>
              <span className="hidden sm:inline">Export Ward Situation Report (PDF)</span>
              <span className="sm:hidden">Export PDF</span>
            </button>

            <button 
              onClick={onOpenAdvisory}
              className="h-9 px-3.5 bg-primary-container hover:bg-[#1B5742] text-white rounded-lg font-title-sm text-title-sm flex items-center gap-2 shadow-xs transition-all active:scale-[0.98] cursor-pointer"
            >
              <span className="material-symbols-outlined text-[18px]">campaign</span>
              <span>Issue Ward Advisory</span>
            </button>
          </div>
        </div>

        {/* 5 High-Density Executive KPI Cards (Responsive Grid) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-space-sm">
          <KPICard 
            title={EXECUTIVE_KPIS.highRiskWards.label}
            icon={EXECUTIVE_KPIS.highRiskWards.icon}
            value={EXECUTIVE_KPIS.highRiskWards.value}
            unit={`/ ${EXECUTIVE_KPIS.highRiskWards.total} Wards`}
            subtitle={EXECUTIVE_KPIS.highRiskWards.subtitle}
            delta={EXECUTIVE_KPIS.highRiskWards.delta}
            isDanger={EXECUTIVE_KPIS.highRiskWards.isDanger}
          />

          <KPICard 
            title={EXECUTIVE_KPIS.heatStress.label}
            icon={EXECUTIVE_KPIS.heatStress.icon}
            value={EXECUTIVE_KPIS.heatStress.value}
            unit={EXECUTIVE_KPIS.heatStress.detail}
            subtitle={EXECUTIVE_KPIS.heatStress.subtitle}
            tag={EXECUTIVE_KPIS.heatStress.tag}
            isDanger={EXECUTIVE_KPIS.heatStress.isDanger}
          />

          <KPICard 
            title={EXECUTIVE_KPIS.waterlogging.label}
            icon={EXECUTIVE_KPIS.waterlogging.icon}
            value={EXECUTIVE_KPIS.waterlogging.value}
            unit={EXECUTIVE_KPIS.waterlogging.unit}
            subtitle={EXECUTIVE_KPIS.waterlogging.subtitle}
            tag={EXECUTIVE_KPIS.waterlogging.tag}
            isInfo={EXECUTIVE_KPIS.waterlogging.isInfo}
          />

          <KPICard 
            title={EXECUTIVE_KPIS.dualHazard.label}
            icon={EXECUTIVE_KPIS.dualHazard.icon}
            value={EXECUTIVE_KPIS.dualHazard.value}
            unit={EXECUTIVE_KPIS.dualHazard.unit}
            subtitle={EXECUTIVE_KPIS.dualHazard.subtitle}
            tag={EXECUTIVE_KPIS.dualHazard.tag}
            isWarning={EXECUTIVE_KPIS.dualHazard.isWarning}
          />

          <KPICard 
            title={EXECUTIVE_KPIS.activeInterventions.label}
            icon={EXECUTIVE_KPIS.activeInterventions.icon}
            value={EXECUTIVE_KPIS.activeInterventions.value}
            unit={EXECUTIVE_KPIS.activeInterventions.unit}
            subtitle={EXECUTIVE_KPIS.activeInterventions.subtitle}
            tag={EXECUTIVE_KPIS.activeInterventions.tag}
            isSuccess={EXECUTIVE_KPIS.activeInterventions.isSuccess}
          />
        </div>
      </section>

      {/* Central Bento: Map (7 Cols) + Right Intel Panel (5 Cols) */}
      <section className="grid grid-cols-1 xl:grid-cols-12 gap-space-md items-start">
        {/* Left 7 Columns on Desktop: Interactive Tactical Map */}
        <div className="xl:col-span-7">
          <AhmedabadVectorMap 
            onInspectWard={onInspectWard}
            onSelectWard={(w) => console.log('Selected ward:', w)}
          />
        </div>

        {/* Right 5 Columns on Desktop: Ranked Highest-Risk Wards Table */}
        <div className="xl:col-span-5">
          <TopWardsTable onInspectWard={onInspectWard} />
        </div>
      </section>
    </div>
  );
}
