import React, { useState, useMemo } from 'react';
import { 
  TrendingUp, 
  Calendar, 
  MapPin, 
  Flame, 
  Droplet, 
  Layers, 
  Info, 
  AlertCircle,
  Database,
  ArrowRight
} from 'lucide-react';
import ProvenanceBadge from './ProvenanceBadge';

export default function RiskTimeSeriesSection({ predictions = [], outcomes = [], wards = [] }) {
  const [selectedWard, setSelectedWard] = useState('ALL');
  const [selectedHazard, setSelectedHazard] = useState('ALL');

  // Filter predictions
  const filteredPredictions = useMemo(() => {
    return predictions.filter(p => {
      const matchWard = selectedWard === 'ALL' || p.ward_id === selectedWard;
      const matchHazard = selectedHazard === 'ALL' || p.hazard_type === selectedHazard;
      return matchWard && matchHazard;
    }).sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
  }, [predictions, selectedWard, selectedHazard]);

  // Filter outcomes
  const filteredOutcomes = useMemo(() => {
    return outcomes.filter(o => {
      const matchWard = selectedWard === 'ALL' || o.ward_id === selectedWard;
      const matchHazard = selectedHazard === 'ALL' || o.hazard_type === selectedHazard || o.hazard_type === 'compound';
      return matchWard && matchHazard;
    }).sort((a, b) => new Date(a.measurement_date) - new Date(b.measurement_date));
  }, [outcomes, selectedWard, selectedHazard]);

  // Normalize outcomes into equivalent risk scale (0-100) exactly as backend learning engine does
  const outcomeRiskPoints = useMemo(() => {
    return filteredOutcomes.map(o => {
      let riskVal = 0;
      const hazard = o.hazard_type || 'heat';
      if (hazard === 'heat') {
        const admissions = Number(o.hospital_heat_admissions || 0);
        const calls = Number(o.emergency_108_calls || 0);
        riskVal = Math.min(100, (admissions * 8.0) + (calls * 4.0));
      } else if (hazard === 'waterlogging') {
        const depth = Number(o.waterlogging_depth_cm || 0);
        riskVal = Math.min(100, depth * 2.0);
      } else if (hazard === 'water_shortage') {
        const complaints = Number(o.water_scarcity_complaints || 0);
        riskVal = Math.min(100, complaints * 4.0);
      } else {
        const admissions = Number(o.hospital_heat_admissions || 0);
        const depth = Number(o.waterlogging_depth_cm || 0);
        riskVal = Math.min(100, (admissions * 6.0) + (depth * 1.5));
      }

      return {
        ...o,
        computedRiskScore: Math.round(riskVal * 10) / 10,
        dateStr: (o.measurement_date || '').slice(0, 10)
      };
    });
  }, [filteredOutcomes]);

  // Check if we have verified real outcomes
  const hasRealOutcomes = outcomeRiskPoints.some(o => o.provenance === 'REAL');
  const hasAnyOutcomes = outcomeRiskPoints.length > 0;
  const hasPredictions = filteredPredictions.length > 0;

  // Build merged timeline points for rendering the SVG chart
  const timelineDates = useMemo(() => {
    const dates = new Set();
    filteredPredictions.forEach(p => {
      if (p.timestamp) dates.add(p.timestamp.slice(0, 10));
    });
    outcomeRiskPoints.forEach(o => {
      if (o.dateStr) dates.add(o.dateStr);
    });
    return Array.from(dates).sort();
  }, [filteredPredictions, outcomeRiskPoints]);

  return (
    <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
      {/* Header and Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ background: 'rgba(6, 182, 212, 0.15)', color: '#06b6d4', padding: '8px', borderRadius: '8px' }}>
              <TrendingUp size={20} />
            </div>
            <div>
              <h3 style={{ fontSize: '1.15rem', color: '#f8fafc', fontWeight: 600 }}>Predicted vs. Observed Risk Timeline</h3>
              <p style={{ fontSize: '0.82rem', color: '#94a3b8' }}>
                Relational calibration connecting model forecasts with empirical ground-truth hospital morbidity and civic outcomes
              </p>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(15, 23, 42, 0.8)', padding: '4px 10px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            <MapPin size={14} color="#94a3b8" />
            <select 
              value={selectedWard} 
              onChange={e => setSelectedWard(e.target.value)}
              className="form-select"
              style={{ padding: '4px 8px', fontSize: '0.8rem', background: 'transparent', border: 'none', color: '#f8fafc' }}
            >
              <option value="ALL" style={{ background: '#0f172a' }}>All Ahmedabad Wards</option>
              {wards.map(w => (
                <option key={w.id || w.name} value={w.id || w.name} style={{ background: '#0f172a' }}>
                  {w.name} ({w.id})
                </option>
              ))}
            </select>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(15, 23, 42, 0.8)', padding: '4px 10px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
            <Layers size={14} color="#94a3b8" />
            <select 
              value={selectedHazard} 
              onChange={e => setSelectedHazard(e.target.value)}
              className="form-select"
              style={{ padding: '4px 8px', fontSize: '0.8rem', background: 'transparent', border: 'none', color: '#f8fafc' }}
            >
              <option value="ALL" style={{ background: '#0f172a' }}>All Hazards</option>
              <option value="heat" style={{ background: '#0f172a' }}>Heatwaves</option>
              <option value="waterlogging" style={{ background: '#0f172a' }}>Waterlogging / Pluvial Flood</option>
              <option value="water_shortage" style={{ background: '#0f172a' }}>Potable Water Deficit</option>
              <option value="compound" style={{ background: '#0f172a' }}>Compound Multi-Hazard</option>
            </select>
          </div>
        </div>
      </div>

      {/* Epistemic Status Banner */}
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px',
        padding: '10px 16px', 
        background: 'rgba(15, 23, 42, 0.6)', 
        borderRadius: '8px', 
        border: '1px solid var(--border-subtle)',
        marginBottom: '20px',
        fontSize: '0.8rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Info size={16} color="#38bdf8" />
          <span style={{ color: '#cbd5e1' }}>
            Data Filter: <strong>{filteredPredictions.length}</strong> Predictions recorded | <strong>{filteredOutcomes.length}</strong> Observed outcomes ({outcomeRiskPoints.filter(o => o.provenance === 'REAL').length} Verified Real)
          </span>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '2px', background: '#f59e0b', display: 'inline-block' }}></span>
            <span style={{ color: '#94a3b8', fontSize: '0.75rem' }}>Predicted Risk (Forecast)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '2px', background: '#10b981', display: 'inline-block' }}></span>
            <span style={{ color: '#94a3b8', fontSize: '0.75rem' }}>Observed Ground Truth (Real)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '2px', background: '#8b5cf6', display: 'inline-block' }}></span>
            <span style={{ color: '#94a3b8', fontSize: '0.75rem' }}>Observed (Simulated Drill)</span>
          </div>
        </div>
      </div>

      {/* Main Chart Area or Informative Empty State */}
      {!hasPredictions && !hasAnyOutcomes ? (
        <div className="empty-state" style={{ minHeight: '260px' }}>
          <Database className="empty-state-icon" />
          <h4 style={{ fontSize: '1rem', color: '#f8fafc', marginBottom: '6px' }}>No Data Available for Selection</h4>
          <p style={{ maxWidth: '420px', fontSize: '0.82rem', color: '#94a3b8', marginBottom: '16px' }}>
            No prediction records or observed municipal outcomes match the current ward or hazard filter.
          </p>
          <span className="badge badge-unverified">Awaiting municipal telemetry ingestion</span>
        </div>
      ) : !hasAnyOutcomes ? (
        /* Empty State: Predictions exist but NO verified outcomes recorded yet */
        <div style={{
          background: 'rgba(30, 41, 59, 0.4)',
          borderRadius: '10px',
          border: '1px dashed rgba(245, 158, 11, 0.4)',
          padding: '32px 20px',
          textAlign: 'center',
          marginBottom: '20px'
        }}>
          <AlertCircle size={36} color="#f59e0b" style={{ margin: '0 auto 12px auto' }} />
          <h4 style={{ color: '#f8fafc', fontSize: '1.05rem', marginBottom: '6px' }}>
            Awaiting Ground-Truth Outcome Verification
          </h4>
          <p style={{ maxWidth: '560px', margin: '0 auto 14px auto', fontSize: '0.84rem', color: '#cbd5e1' }}>
            There are <strong>{filteredPredictions.length}</strong> active risk forecasts for this selection, but <strong>no verified municipal outcomes have been recorded yet</strong>.
          </p>
          <div style={{ 
            display: 'inline-flex', 
            background: 'rgba(15, 23, 42, 0.8)', 
            padding: '8px 16px', 
            borderRadius: '8px', 
            border: '1px solid var(--border-subtle)',
            fontSize: '0.78rem',
            color: '#94a3b8',
            textAlign: 'left',
            gap: '12px'
          }}>
            <div><strong>Required Surveillance Data:</strong></div>
            <div>• Heat: AMC Hospital Inpatient Admissions &amp; 108 Dispatches</div>
            <div>• Water: Civic CCRS 155303 Complaints &amp; Flood Surcharge Depth</div>
          </div>
          <p style={{ marginTop: '12px', fontSize: '0.75rem', color: '#64748b', fontStyle: 'italic' }}>
            Per ClimateShield safety protocol: Model calibration curves are never fabricated or simulated as real observations without actual measurement data.
          </p>
        </div>
      ) : (
        /* Render SVG Time-Series Chart */
        <div style={{ marginBottom: '24px' }}>
          <div style={{ 
            width: '100%', 
            height: '240px', 
            background: 'rgba(15, 23, 42, 0.7)', 
            borderRadius: '10px', 
            border: '1px solid var(--border-subtle)', 
            padding: '16px 20px',
            position: 'relative',
            overflow: 'hidden'
          }}>
            {/* SVG Plot */}
            <svg viewBox="0 0 800 200" preserveAspectRatio="none" style={{ width: '100%', height: '100%', overflow: 'visible' }}>
              {/* Grid Lines */}
              <line x1="50" y1="20" x2="780" y2="20" stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" />
              <line x1="50" y1="60" x2="780" y2="60" stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" />
              <line x1="50" y1="100" x2="780" y2="100" stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" />
              <line x1="50" y1="140" x2="780" y2="140" stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" />
              <line x1="50" y1="180" x2="780" y2="180" stroke="rgba(255,255,255,0.15)" />

              {/* Y-Axis Labels */}
              <text x="40" y="24" fill="#64748b" fontSize="10" textAnchor="end">100</text>
              <text x="40" y="64" fill="#64748b" fontSize="10" textAnchor="end">75</text>
              <text x="40" y="104" fill="#64748b" fontSize="10" textAnchor="end">50</text>
              <text x="40" y="144" fill="#64748b" fontSize="10" textAnchor="end">25</text>
              <text x="40" y="184" fill="#64748b" fontSize="10" textAnchor="end">0</text>

              {/* Threshold 50 line (Severe / Alert threshold) */}
              <line x1="50" y1="100" x2="780" y2="100" stroke="rgba(245, 158, 11, 0.25)" strokeDasharray="4 4" strokeWidth="1.5" />
              <text x="775" y="96" fill="#f59e0b" fontSize="9" textAnchor="end">Alert Threshold (50)</text>

              {/* Prediction Points & Path */}
              {timelineDates.length > 0 && (
                <>
                  {/* Lines for predictions */}
                  <polyline
                    fill="none"
                    stroke="#f59e0b"
                    strokeWidth="2"
                    strokeDasharray="4 2"
                    points={timelineDates.map((date, idx) => {
                      const matchPred = filteredPredictions.find(p => (p.timestamp || '').slice(0, 10) === date);
                      const val = matchPred ? matchPred.predicted_risk_score : 0;
                      const x = 60 + (idx / Math.max(1, timelineDates.length - 1)) * 710;
                      const y = 180 - (val / 100) * 160;
                      return `${x},${y}`;
                    }).join(' ')}
                  />

                  {/* Lines for observed outcomes */}
                  <polyline
                    fill="none"
                    stroke={hasRealOutcomes ? "#10b981" : "#8b5cf6"}
                    strokeWidth="2.5"
                    points={timelineDates.map((date, idx) => {
                      const matchOut = outcomeRiskPoints.find(o => o.dateStr === date);
                      const val = matchOut ? matchOut.computedRiskScore : 0;
                      const x = 60 + (idx / Math.max(1, timelineDates.length - 1)) * 710;
                      const y = 180 - (val / 100) * 160;
                      return `${x},${y}`;
                    }).join(' ')}
                  />

                  {/* Prediction Circles */}
                  {timelineDates.map((date, idx) => {
                    const matchPred = filteredPredictions.find(p => (p.timestamp || '').slice(0, 10) === date);
                    if (!matchPred) return null;
                    const x = 60 + (idx / Math.max(1, timelineDates.length - 1)) * 710;
                    const y = 180 - (matchPred.predicted_risk_score / 100) * 160;
                    return (
                      <g key={`p-${idx}`}>
                        <circle cx={x} cy={y} r="5" fill="#f59e0b" stroke="#0f172a" strokeWidth="2" />
                      </g>
                    );
                  })}

                  {/* Outcome Circles */}
                  {timelineDates.map((date, idx) => {
                    const matchOut = outcomeRiskPoints.find(o => o.dateStr === date);
                    if (!matchOut) return null;
                    const x = 60 + (idx / Math.max(1, timelineDates.length - 1)) * 710;
                    const y = 180 - (matchOut.computedRiskScore / 100) * 160;
                    const color = matchOut.provenance === 'REAL' ? '#10b981' : '#8b5cf6';
                    return (
                      <g key={`o-${idx}`}>
                        <circle cx={x} cy={y} r="6" fill={color} stroke="#0f172a" strokeWidth="2" />
                      </g>
                    );
                  })}

                  {/* X-axis date labels */}
                  {timelineDates.map((date, idx) => {
                    if (timelineDates.length > 8 && idx % 2 !== 0 && idx !== timelineDates.length - 1) return null;
                    const x = 60 + (idx / Math.max(1, timelineDates.length - 1)) * 710;
                    return (
                      <text key={`lbl-${idx}`} x={x} y="195" fill="#64748b" fontSize="9" textAnchor="middle">
                        {date.slice(5)}
                      </text>
                    );
                  })}
                </>
              )}
            </svg>
          </div>
        </div>
      )}

      {/* Contemporaneous Observation Comparison Table */}
      {timelineDates.length > 0 && (
        <div style={{ overflowX: 'auto' }}>
          <h4 style={{ fontSize: '0.88rem', color: '#cbd5e1', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>Observation Comparison Log</span>
            <span style={{ fontSize: '0.75rem', color: '#64748b' }}>({timelineDates.length} chronological timestamps)</span>
          </h4>
          <table className="data-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Ward</th>
                <th>Hazard</th>
                <th>Predicted Risk</th>
                <th>Observed Outcome Proxy</th>
                <th>Model Residual (Error)</th>
                <th>Data Source &amp; Provenance</th>
              </tr>
            </thead>
            <tbody>
              {timelineDates.map(date => {
                const pred = filteredPredictions.find(p => (p.timestamp || '').slice(0, 10) === date);
                const out = outcomeRiskPoints.find(o => o.dateStr === date);

                const predScore = pred ? pred.predicted_risk_score : null;
                const outScore = out ? out.computedRiskScore : null;
                const residual = (predScore !== null && outScore !== null) 
                  ? Math.round((outScore - predScore) * 10) / 10 
                  : null;

                return (
                  <tr key={date}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem', color: '#94a3b8' }}>{date}</td>
                    <td>
                      <span style={{ fontWeight: 500 }}>{pred?.ward_name || out?.ward_name || pred?.ward_id || out?.ward_id || 'All Wards'}</span>
                    </td>
                    <td>
                      <span style={{ textTransform: 'capitalize', color: '#cbd5e1' }}>
                        {pred?.hazard_type || out?.hazard_type || 'General'}
                      </span>
                    </td>
                    <td>
                      {predScore !== null ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{ 
                            fontWeight: 600, 
                            color: predScore >= 70 ? '#f43f5e' : (predScore >= 50 ? '#f59e0b' : '#38bdf8') 
                          }}>
                            {predScore}
                          </span>
                          <span style={{ fontSize: '0.7rem', color: '#64748b' }}>({pred?.risk_category})</span>
                        </div>
                      ) : (
                        <span style={{ color: '#475569' }}>— No Forecast —</span>
                      )}
                    </td>
                    <td>
                      {outScore !== null ? (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <span style={{ fontWeight: 600, color: '#10b981' }}>{outScore}</span>
                          <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
                            ({out.hospital_heat_admissions} adm / {out.emergency_108_calls} calls / {out.water_scarcity_complaints} comp)
                          </span>
                        </div>
                      ) : (
                        <span style={{ color: '#475569' }}>— Pending Outcome —</span>
                      )}
                    </td>
                    <td>
                      {residual !== null ? (
                        <span style={{ 
                          fontWeight: 600, 
                          color: Math.abs(residual) <= 8 ? '#10b981' : (residual > 0 ? '#f43f5e' : '#38bdf8'),
                          fontFamily: 'var(--font-mono)',
                          fontSize: '0.8rem'
                        }}>
                          {residual > 0 ? `+${residual}` : residual} pts
                        </span>
                      ) : (
                        <span style={{ color: '#475569' }}>—</span>
                      )}
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ fontSize: '0.78rem', color: '#cbd5e1' }}>
                          {out?.data_source || pred?.data_source || 'Telemetry'}
                        </span>
                        <ProvenanceBadge provenance={out?.provenance || pred?.provenance || 'ESTIMATED'} />
                      </div>
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
