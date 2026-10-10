import React from 'react';
import { 
  History, 
  AlertTriangle, 
  FileText, 
  Calendar, 
  ShieldAlert,
  ArrowRight,
  DatabaseZap,
  TrendingDown
} from 'lucide-react';

export default function PerformanceTrendsSection({ evaluations = [], predictions = [], outcomes = [], wards = [] }) {
  // Compute known data gaps
  const wardsWithFewObservations = wards.filter(w => {
    const realForWard = outcomes.filter(o => o.ward_id === w.id && o.provenance === 'REAL');
    return realForWard.length < 3;
  });

  return (
    <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
        <div style={{ background: 'rgba(139, 92, 246, 0.15)', color: '#8b5cf6', padding: '8px', borderRadius: '8px' }}>
          <History size={20} />
        </div>
        <div>
          <h3 style={{ fontSize: '1.15rem', color: '#f8fafc', fontWeight: 600 }}>Performance Trends &amp; Data Gaps</h3>
          <p style={{ fontSize: '0.82rem', color: '#94a3b8' }}>
            Audit trail of historical model evaluation runs and transparent disclosure of observational coverage deficits
          </p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px', marginBottom: '20px' }}>
        {/* Left Column: Data Gap Disclosures */}
        <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '18px', borderRadius: '12px', border: '1px solid var(--border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', color: '#f59e0b' }}>
            <AlertTriangle size={18} />
            <h4 style={{ fontSize: '0.92rem', color: '#f8fafc', fontWeight: 600 }}>Identified Municipal Data Gaps</h4>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.8rem' }}>
            <div style={{ background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.2)', padding: '10px 12px', borderRadius: '8px' }}>
              <div style={{ color: '#fbbf24', fontWeight: 600, marginBottom: '2px' }}>
                Sparse Ward Surveillance ({wardsWithFewObservations.length} of {wards.length} Wards)
              </div>
              <p style={{ color: '#cbd5e1', fontSize: '0.76rem' }}>
                Wards with fewer than 3 verified real observations cannot reliably calibrate vulnerability priors. The learning engine strictly enforces an N ≥ 3 threshold before proposing updates.
              </p>
              {wardsWithFewObservations.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '6px' }}>
                  {wardsWithFewObservations.slice(0, 8).map(w => (
                    <span key={w.id} style={{ background: 'rgba(15, 23, 42, 0.8)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.7rem', color: '#94a3b8' }}>
                      {w.name} ({w.id})
                    </span>
                  ))}
                  {wardsWithFewObservations.length > 8 && (
                    <span style={{ fontSize: '0.7rem', color: '#64748b', alignSelf: 'center' }}>
                      +{wardsWithFewObservations.length - 8} more
                    </span>
                  )}
                </div>
              )}
            </div>

            <div style={{ background: 'rgba(56, 189, 248, 0.08)', border: '1px solid rgba(56, 189, 248, 0.2)', padding: '10px 12px', borderRadius: '8px' }}>
              <div style={{ color: '#38bdf8', fontWeight: 600, marginBottom: '2px' }}>
                Counterfactual Control Limitations
              </div>
              <p style={{ color: '#cbd5e1', fontSize: '0.76rem' }}>
                Difference-in-Differences causal estimates require an un-intervened comparison ward measured contemporaneously. In citywide heat alerts where all wards receive shade/hydration, causal estimation falls back to correlational before-and-after tracking.
              </p>
            </div>

            <div style={{ background: 'rgba(139, 92, 246, 0.08)', border: '1px solid rgba(139, 92, 246, 0.2)', padding: '10px 12px', borderRadius: '8px' }}>
              <div style={{ color: '#a78bfa', fontWeight: 600, marginBottom: '2px' }}>
                Synthetic Data Isolation
              </div>
              <p style={{ color: '#cbd5e1', fontSize: '0.76rem' }}>
                Simulated demonstration data ({outcomes.filter(o => o.provenance === 'SIMULATED').length} records) is isolated in audit tables and prevented from contributing to real-world model parameter updates.
              </p>
            </div>
          </div>
        </div>

        {/* Right Column: Historical Evaluation Runs */}
        <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '18px', borderRadius: '12px', border: '1px solid var(--border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', color: '#38bdf8' }}>
            <DatabaseZap size={18} />
            <h4 style={{ fontSize: '0.92rem', color: '#f8fafc', fontWeight: 600 }}>Historical Model Evaluation Runs</h4>
          </div>

          {evaluations.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '30px 10px', color: '#94a3b8' }}>
              <FileText size={28} style={{ margin: '0 auto 8px auto', opacity: 0.5 }} />
              <div style={{ fontSize: '0.84rem', color: '#cbd5e1' }}>No Evaluation History Yet</div>
              <p style={{ fontSize: '0.75rem', color: '#64748b' }}>
                Click "Run Statistical Evaluation" in the accuracy section above to generate the first evaluation audit report.
              </p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '280px', overflowY: 'auto' }}>
              {evaluations.map(ev => (
                <div 
                  key={ev.evaluation_id} 
                  style={{ 
                    background: 'rgba(30, 41, 59, 0.4)', 
                    padding: '10px 12px', 
                    borderRadius: '8px', 
                    border: '1px solid rgba(255, 255, 255, 0.05)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}
                >
                  <div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.76rem', color: '#38bdf8' }}>
                      {ev.evaluation_id}
                    </div>
                    <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '2px' }}>
                      {(ev.timestamp || '').slice(0, 16).replace('T', ' ')} UTC • Window: {ev.eval_window_days}d
                    </div>
                    <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '2px' }}>
                      Real Pairs: <strong>{ev.sample_count_real}</strong> | Excluded: {ev.sample_count_excluded}
                    </div>
                  </div>

                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Overall MAE</div>
                    <div style={{ 
                      fontSize: '1.05rem', 
                      fontWeight: 700, 
                      color: ev.overall_mae !== null ? (ev.overall_mae <= 12 ? '#34d399' : '#f59e0b') : '#64748b',
                      fontFamily: 'var(--font-mono)' 
                    }}>
                      {ev.overall_mae !== null ? `${ev.overall_mae} pts` : 'N/A'}
                    </div>
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
