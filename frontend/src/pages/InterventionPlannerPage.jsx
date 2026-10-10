import React, { useState, useEffect, useCallback } from 'react';
import { ClimateShieldAPI } from '../services/api';

export default function InterventionPlannerPage() {
  const [budget, setBudget] = useState(500000);
  const [crew, setCrew] = useState(40);
  const [waterCap, setWaterCap] = useState(30000);
  const [equitySlider, setEquitySlider] = useState(0.5);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [error, setError] = useState(null);
  const [solverResult, setSolverResult] = useState(null);
  const [dispatchStatus, setDispatchStatus] = useState(null);

  const runOptimizer = useCallback(async () => {
    setIsOptimizing(true);
    setError(null);
    try {
      const res = await ClimateShieldAPI.runOptimization({
        total_budget_inr: budget,
        total_crew_members: crew,
        total_water_cap_l: waterCap,
        equity_slider: equitySlider,
      });
      setSolverResult(res);
    } catch (err) {
      console.error('ILP Optimizer solver failed:', err);
      setError(err.message || 'Optimization solver failed.');
    } finally {
      setIsOptimizing(false);
    }
  }, [budget, crew, waterCap, equitySlider]);

  useEffect(() => {
    runOptimizer();
  }, [runOptimizer]);

  const handleDispatchPlanToActionCentre = async () => {
    if (!solverResult?.ward_allocations) return;
    setDispatchStatus('Dispatching interventions to Action Centre...');
    try {
      const entries = Object.entries(solverResult.ward_allocations);
      let createdCount = 0;
      for (const [wardKey, wardData] of entries) {
        for (const it of wardData.interventions || []) {
          await ClimateShieldAPI.createManualAction({
            ward_id: wardKey,
            ward_name: wardData.ward_name,
            action_type: it.action_id || 'cooling_centre',
            priority: wardData.vulnerability >= 0.85 ? 'critical' : 'high',
            reason: it.reason_for_recommendation || `ILP optimal allocation: ${it.action_name}`,
            required_resources: {
              cost_inr: it.estimated_cost_inr || it.cost_inr || 25000,
              crew_required: it.crew_required || 2,
              water_required_l: it.water_required_l || 0,
            },
            related_hazard: it.risk_type || 'heat',
            risk_score: Math.round(wardData.vulnerability * 100),
          });
          createdCount++;
        }
      }
      setDispatchStatus(`Successfully dispatched ${createdCount} interventions to the Action Centre Queue!`);
      setTimeout(() => setDispatchStatus(null), 4000);
    } catch (err) {
      setDispatchStatus(`Dispatch failed: ${err.message}`);
    }
  };

  const wardAllocations = solverResult?.ward_allocations ? Object.entries(solverResult.ward_allocations) : [];
  const summary = solverResult?.summary;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-2 border-b border-outline-variant">
        <div>
          <div className="flex items-center gap-2 font-mono text-[10px] text-outline mb-0.5 uppercase tracking-wider">
            <span>AMC Command Center</span>
            <span>/</span>
            <span className="text-primary font-bold">Intervention Planner</span>
          </div>
          <h1 className="text-headline-md font-headline-md text-primary font-bold">
            Municipal Resource Allocation & What-If Optimizer
          </h1>
          <p className="text-xs text-on-surface-variant mt-0.5">
            Integer Linear Programming (ILP) solver matching resource constraints against multi-hazard ward vulnerability.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {wardAllocations.length > 0 && (
            <button
              onClick={handleDispatchPlanToActionCentre}
              className="h-9 px-3.5 bg-surface-container-lowest border border-outline-variant hover:bg-[#F8FAF8] rounded-lg text-xs font-semibold text-primary flex items-center gap-2 shadow-xs transition-all cursor-pointer"
              title="Add all allocated actions to the live Action Centre queue"
            >
              <span className="material-symbols-outlined text-[16px]">send</span>
              <span>Dispatch Plan to Ops Queue</span>
            </button>
          )}

          <button
            onClick={runOptimizer}
            disabled={isOptimizing}
            className="h-9 px-4 bg-primary text-white rounded-lg text-xs font-semibold flex items-center gap-2 hover:bg-[#1B5742] shadow-sm transition-all cursor-pointer disabled:opacity-60"
          >
            <span className="material-symbols-outlined text-[18px]">
              {isOptimizing ? 'sync' : 'play_arrow'}
            </span>
            <span>{isOptimizing ? 'Optimizing (<200ms)...' : 'Run Resource Optimization'}</span>
          </button>
        </div>
      </div>

      {/* Dispatch feedback toast */}
      {dispatchStatus && (
        <div className="p-3 bg-emerald-50 border border-emerald-300 rounded-xl text-xs font-mono text-emerald-900 flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px]">check_circle</span>
          <span>{dispatchStatus}</span>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-xl flex items-center justify-between text-xs text-error">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[18px]">error</span>
            <span className="font-mono">{error}</span>
          </div>
          <button
            onClick={runOptimizer}
            className="px-3 py-1 bg-white border border-red-300 rounded font-mono font-bold hover:bg-red-50 cursor-pointer"
          >
            Retry Solver
          </button>
        </div>
      )}

      {/* Resource Utilization Bar */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-surface-container-lowest p-4 rounded-xl border border-outline-variant">
          <div>
            <span className="text-[10px] font-mono uppercase text-outline block">Budget Utilization</span>
            <span className="text-base font-bold font-mono text-primary">
              ₹{(summary.budget?.allocated_inr || 0).toLocaleString()}
            </span>
            <span className="text-[10px] font-mono text-outline block">
              {summary.budget?.utilization_pct}% of ₹{(summary.budget?.cap_inr || budget).toLocaleString()}
            </span>
          </div>

          <div>
            <span className="text-[10px] font-mono uppercase text-outline block">Crew Deployment</span>
            <span className="text-base font-bold font-mono text-primary">
              {summary.crew?.allocated_members || 0} Personnel
            </span>
            <span className="text-[10px] font-mono text-outline block">
              {summary.crew?.utilization_pct}% of {summary.crew?.cap_members || crew} cap
            </span>
          </div>

          <div>
            <span className="text-[10px] font-mono uppercase text-outline block">Water Allocation</span>
            <span className="text-base font-bold font-mono text-[#0284C7]">
              {(summary.water?.allocated_liters || 0).toLocaleString()} L
            </span>
            <span className="text-[10px] font-mono text-outline block">
              {summary.water?.utilization_pct}% of {(summary.water?.cap_liters || waterCap).toLocaleString()} L
            </span>
          </div>

          <div>
            <span className="text-[10px] font-mono uppercase text-outline block">Net Risk Reduction</span>
            <span className="text-base font-bold font-mono text-emerald-700">
              {summary.total_risk_reduction_achieved || 0} pts
            </span>
            <span className="text-[10px] font-mono text-emerald-800 block">
              Optimal Multi-Hazard Benefit
            </span>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left 4 Cols: Resource Slider Bounds */}
        <div className="lg:col-span-4 bg-surface-container-lowest rounded-xl border border-outline-variant p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-2 border-b">
            <h3 className="font-bold text-sm text-primary">Municipal Resource Bounds</h3>
            <span className="font-mono text-[10px] text-outline">T-24 Dispatch Bounds</span>
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1 font-mono">
              <span className="text-outline">Budget Allocation (INR)</span>
              <span className="font-bold text-primary">₹{budget.toLocaleString()}</span>
            </div>
            <input 
              type="range" 
              min={100000} 
              max={2000000} 
              step={50000}
              value={budget} 
              onChange={(e) => setBudget(Number(e.target.value))}
              className="w-full accent-primary cursor-pointer"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1 font-mono">
              <span className="text-outline">Available Deployment Crew</span>
              <span className="font-bold text-primary">{crew} Personnel</span>
            </div>
            <input 
              type="range" 
              min={10} 
              max={150} 
              step={5}
              value={crew} 
              onChange={(e) => setCrew(Number(e.target.value))}
              className="w-full accent-primary cursor-pointer"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1 font-mono">
              <span className="text-outline">Daily Water Cap Limit</span>
              <span className="font-bold text-primary">{waterCap.toLocaleString()} L</span>
            </div>
            <input 
              type="range" 
              min={5000} 
              max={100000} 
              step={5000}
              value={waterCap} 
              onChange={(e) => setWaterCap(Number(e.target.value))}
              className="w-full accent-primary cursor-pointer"
            />
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1 font-mono">
              <span className="text-outline">Equity Priority Slider</span>
              <span className="font-bold text-primary">{Math.round(equitySlider * 100)}% Equity</span>
            </div>
            <input 
              type="range" 
              min={0} 
              max={1} 
              step={0.05}
              value={equitySlider} 
              onChange={(e) => setEquitySlider(Number(e.target.value))}
              className="w-full accent-primary cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-outline font-mono mt-1">
              <span>Pure Efficiency (0%)</span>
              <span>Maximum Equity (100%)</span>
            </div>
          </div>
        </div>

        {/* Right 8 Cols: Optimized Allocation Schedule */}
        <div className="lg:col-span-8 bg-surface-container-lowest rounded-xl border border-outline-variant p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-2 border-b">
            <div>
              <h3 className="font-bold text-sm text-primary">ILP Optimal Intervention Schedule</h3>
              <p className="text-xs text-outline font-mono">
                Solver: {solverResult?.solver || 'Google OR-Tools SCIP/CBC'} • Status: {solverResult?.status || 'OPTIMAL'}
              </p>
            </div>
            <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-emerald-100 text-emerald-800">
              {solverResult?.is_optimal ? '100% FEASIBLE' : 'COMPUTING'}
            </span>
          </div>

          {isOptimizing && (
            <div className="p-8 text-center space-y-2">
              <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto"></div>
              <span className="text-xs font-mono text-outline">Solving Multi-Hazard Knapsack Program...</span>
            </div>
          )}

          {!isOptimizing && wardAllocations.length === 0 && (
            <div className="p-8 text-center text-xs font-mono text-outline">
              No allocations found under the specified constraints. Try increasing the budget or crew bounds.
            </div>
          )}

          {!isOptimizing && wardAllocations.length > 0 && (
            <div className="space-y-3 text-xs">
              {wardAllocations.map(([wKey, wData], idx) => (
                <div key={wKey} className="p-3.5 rounded-lg border border-slate-200 bg-surface-bright space-y-2">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 pb-1.5 border-b border-slate-200/60">
                    <div>
                      <div className="font-bold text-on-surface text-sm">
                        {idx + 1}. {wData.ward_name} ({wKey})
                      </div>
                      <span className="font-mono text-[10px] text-outline">
                        Vulnerability: {wData.vulnerability ? Math.round(wData.vulnerability * 100) : 80}/100 • Risk Reduction: +{wData.ward_risk_reduction || 0} pts
                      </span>
                    </div>
                    <div className="text-left sm:text-right font-mono">
                      <span className="font-bold text-emerald-800 text-xs">
                        ₹{(wData.ward_cost || 0).toLocaleString()}
                      </span>
                      <span className="text-outline block text-[10px]">
                        Crew: {wData.ward_crew || 0} • Water: {(wData.ward_water_l || 0).toLocaleString()} L
                      </span>
                    </div>
                  </div>

                  {/* Interventions for this ward */}
                  <div className="space-y-1.5 pl-2">
                    {wData.interventions?.map((it, itIdx) => (
                      <div key={itIdx} className="flex items-start justify-between gap-2 text-[11px]">
                        <div className="flex items-start gap-1.5">
                          <span className="material-symbols-outlined text-[14px] text-primary mt-0.5">check</span>
                          <div>
                            <span className="font-semibold text-primary">{it.action_name}</span>
                            <span className="text-outline font-mono ml-1.5">({it.units || 1} units)</span>
                            <p className="text-[10px] text-on-surface-variant font-sans mt-0.5">
                              {it.reason_for_recommendation}
                            </p>
                          </div>
                        </div>
                        <span className="font-mono text-outline shrink-0">
                          ₹{(it.cost_inr || it.estimated_cost_inr || 0).toLocaleString()}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
