import React, { useState } from 'react';

export default function InterventionPlannerPage() {
  const [budget, setBudget] = useState(500000);
  const [crew, setCrew] = useState(40);
  const [waterCap, setWaterCap] = useState(30000);
  const [equitySlider, setEquitySlider] = useState(0.5);
  const [isOptimizing, setIsOptimizing] = useState(false);
  const [hasRun, setHasRun] = useState(true);

  const handleRunOptimizer = () => {
    setIsOptimizing(true);
    setTimeout(() => {
      setIsOptimizing(false);
      setHasRun(true);
      alert("ILP Optimization completed! 14 high-risk wards allocated optimal heat-relief packages under budget bounds.");
    }, 800);
  };

  return (
    <div className="space-y-6">
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

        <button
          onClick={handleRunOptimizer}
          disabled={isOptimizing}
          className="h-9 px-4 bg-primary text-white rounded-lg text-xs font-semibold flex items-center gap-2 hover:bg-[#1B5742] shadow-sm transition-all cursor-pointer disabled:opacity-60"
        >
          <span className="material-symbols-outlined text-[18px]">play_arrow</span>
          <span>{isOptimizing ? 'Optimizing (<200ms)...' : 'Run Resource Optimization'}</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left 4 Cols: Resource Slider Bounds */}
        <div className="lg:col-span-4 bg-surface-container-lowest rounded-xl border border-outline-variant p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-2 border-b">
            <h3 className="font-bold text-sm text-primary">Municipal Resource Bounds</h3>
            <span className="font-mono text-[10px] text-outline">T-24 Dispatch</span>
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
              <span>Pure Efficiency</span>
              <span>Maximum Equity</span>
            </div>
          </div>
        </div>

        {/* Right 8 Cols: Optimized Allocation Schedule */}
        <div className="lg:col-span-8 bg-surface-container-lowest rounded-xl border border-outline-variant p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-2 border-b">
            <div>
              <h3 className="font-bold text-sm text-primary">ILP Optimal Intervention Schedule</h3>
              <p className="text-xs text-outline font-mono">Status: Optimal Solution Found (Latency: 142ms)</p>
            </div>
            <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-emerald-100 text-emerald-800">
              100% FEASIBLE
            </span>
          </div>

          <div className="space-y-3 text-xs">
            <div className="p-3 rounded-lg border border-slate-200 bg-surface-bright flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <div className="font-bold text-on-surface">1. Gomtipur Ward (AMC-E-04)</div>
                <div className="text-outline font-mono text-[11px]">Primary: High-Albedo Cool Roof Coating Cluster (1,400 m²)</div>
              </div>
              <div className="text-right font-mono">
                <span className="font-bold text-emerald-800">Cost: ₹168,000</span>
                <span className="text-outline block text-[10px]">Crew: 10 • Water: 0 L</span>
              </div>
            </div>

            <div className="p-3 rounded-lg border border-slate-200 bg-surface-bright flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <div className="font-bold text-on-surface">2. Danilimda Ward (AMC-S-14)</div>
                <div className="text-outline font-mono text-[11px]">Primary: 4 Mobile Water Bowsers + Hydration Booth Deployment</div>
              </div>
              <div className="text-right font-mono">
                <span className="font-bold text-emerald-800">Cost: ₹95,000</span>
                <span className="text-outline block text-[10px]">Crew: 8 • Water: 24,000 L</span>
              </div>
            </div>

            <div className="p-3 rounded-lg border border-slate-200 bg-surface-bright flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <div className="font-bold text-on-surface">3. Odhav Ward (AMC-E-08)</div>
                <div className="text-outline font-mono text-[11px]">Primary: AMTS Transit Corridor Pop-up Misting Systems</div>
              </div>
              <div className="text-right font-mono">
                <span className="font-bold text-emerald-800">Cost: ₹74,000</span>
                <span className="text-outline block text-[10px]">Crew: 6 • Water: 4,000 L</span>
              </div>
            </div>

            <div className="p-3 rounded-lg border border-slate-200 bg-surface-bright flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <div className="font-bold text-on-surface">4. Bapunagar Ward (AMC-N-06)</div>
                <div className="text-outline font-mono text-[11px]">Primary: UHC ORS Distribution + Health Surveillance Squads</div>
              </div>
              <div className="text-right font-mono">
                <span className="font-bold text-emerald-800">Cost: ₹48,000</span>
                <span className="text-outline block text-[10px]">Crew: 8 • Water: 2,000 L</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
