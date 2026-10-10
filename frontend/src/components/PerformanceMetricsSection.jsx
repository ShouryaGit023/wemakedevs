import React, { useState } from 'react';
import { 
  BarChart3, 
  Flame, 
  Droplet, 
  Waves, 
  RefreshCw, 
  CheckCircle2, 
  AlertTriangle,
  Sparkles,
  Info
} from 'lucide-react';
import { api } from '../api';

export default function PerformanceMetricsSection({ latestEvaluation, onEvaluationTriggered }) {
  const [runningEval, setRunningEval] = useState(false);
  const [evalMsg, setEvalMsg] = useState(null);

  const handleRunEvaluation = async () => {
    setRunningEval(true);
    setEvalMsg(null);
    try {
      const res = await api.runEvaluation({
        eval_window_days: 30,
        min_samples: 3,
        exclude_simulated: true
      });
      setEvalMsg({ type: 'success', text: `Evaluation complete! Status: ${res.status}. Real pairs evaluated: ${res.sample_counts?.verified_real_pairs || 0}` });
      if (onEvaluationTriggered) onEvaluationTriggered();
    } catch (err) {
      setEvalMsg({ type: 'error', text: err.message });
    } finally {
      setRunningEval(false);
    }
  };

  const heatMetrics = latestEvaluation?.heat_metrics || latestEvaluation?.accuracy_by_hazard?.heat;
  const floodMetrics = latestEvaluation?.waterlogging_metrics || latestEvaluation?.accuracy_by_hazard?.waterlogging;
  const shortageMetrics = latestEvaluation?.water_shortage_metrics || latestEvaluation?.accuracy_by_hazard?.water_shortage;

  const renderMetricCard = (title, icon, metrics, colorTheme) => {
    const hasData = metrics && metrics.sample_count > 0 && metrics.status !== 'INSUFFICIENT_DATA';

    return (
      <div style={{ 
        background: 'rgba(15, 23, 42, 0.7)', 
        borderRadius: '12px', 
        border: '1px solid var(--border-subtle)',
        padding: '18px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between'
      }}>
        <div>
          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ 
                background: colorTheme.bg, 
                color: colorTheme.color, 
                padding: '6px', 
                borderRadius: '6px' 
              }}>
                {icon}
              </div>
              <h4 style={{ fontSize: '0.95rem', color: '#f8fafc', fontWeight: 600 }}>{title}</h4>
            </div>
            <span className={`badge ${hasData ? 'badge-completed' : 'badge-unverified'}`}>
              {hasData ? `${metrics.sample_count} Samples` : 'Insufficient Data'}
            </span>
          </div>

          {/* Metrics Values */}
          {hasData ? (
            <div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '14px' }}>
                <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: '10px', borderRadius: '8px' }}>
                  <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>MAE (Mean Absolute Error)</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f8fafc', fontFamily: 'var(--font-mono)' }}>
                    {metrics.mae} <span style={{ fontSize: '0.75rem', color: '#64748b' }}>pts</span>
                  </div>
                </div>
                <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: '10px', borderRadius: '8px' }}>
                  <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>RMSE (Root Mean Square)</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f8fafc', fontFamily: 'var(--font-mono)' }}>
                    {metrics.rmse} <span style={{ fontSize: '0.75rem', color: '#64748b' }}>pts</span>
                  </div>
                </div>
              </div>

              {/* Classification Metrics */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '6px', marginBottom: '14px' }}>
                <div style={{ textAlign: 'center', background: 'rgba(255, 255, 255, 0.03)', padding: '6px', borderRadius: '6px' }}>
                  <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>Precision</div>
                  <div style={{ fontSize: '0.95rem', fontWeight: 600, color: '#38bdf8' }}>
                    {Math.round((metrics.precision || 0) * 100)}%
                  </div>
                </div>
                <div style={{ textAlign: 'center', background: 'rgba(255, 255, 255, 0.03)', padding: '6px', borderRadius: '6px' }}>
                  <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>Recall</div>
                  <div style={{ fontSize: '0.95rem', fontWeight: 600, color: '#34d399' }}>
                    {Math.round((metrics.recall || 0) * 100)}%
                  </div>
                </div>
                <div style={{ textAlign: 'center', background: 'rgba(255, 255, 255, 0.03)', padding: '6px', borderRadius: '6px' }}>
                  <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>F1 Score</div>
                  <div style={{ fontSize: '0.95rem', fontWeight: 600, color: '#fbbf24' }}>
                    {metrics.f1_score ?? '0.00'}
                  </div>
                </div>
              </div>

              {/* Confusion Matrix Breakdown */}
              {metrics.confusion_matrix && (
                <div style={{ fontSize: '0.72rem', color: '#94a3b8', background: 'rgba(0, 0, 0, 0.2)', padding: '8px 10px', borderRadius: '6px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '3px' }}>
                    <span>True Positives (Correct alerts):</span>
                    <strong style={{ color: '#34d399' }}>{metrics.confusion_matrix.true_positives}</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '3px' }}>
                    <span>False Positives (Unneeded alerts):</span>
                    <strong style={{ color: '#fb7185' }}>{metrics.confusion_matrix.false_positives}</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>False Negatives (Missed spikes):</span>
                    <strong style={{ color: '#f43f5e' }}>{metrics.confusion_matrix.false_negatives}</strong>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div style={{ padding: '20px 10px', textAlign: 'center', color: '#94a3b8' }}>
              <AlertTriangle size={24} color="#f59e0b" style={{ margin: '0 auto 8px auto', opacity: 0.8 }} />
              <div style={{ fontSize: '0.82rem', color: '#f8fafc', fontWeight: 500, marginBottom: '4px' }}>
                Evidence Below Threshold
              </div>
              <p style={{ fontSize: '0.74rem', color: '#64748b' }}>
                Requires minimum 3 verified real observations to compute statistical accuracy. Simulated demonstration data is excluded.
              </p>
            </div>
          )}
        </div>

        {/* Footer Note */}
        <div style={{ marginTop: '12px', paddingTop: '10px', borderTop: '1px solid rgba(255, 255, 255, 0.05)', fontSize: '0.7rem', color: '#64748b' }}>
          Alert boundary: Risk score ≥ 50 pts
        </div>
      </div>
    );
  };

  return (
    <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
      {/* Header and Trigger Button */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ background: 'rgba(245, 158, 11, 0.15)', color: '#f59e0b', padding: '8px', borderRadius: '8px' }}>
            <BarChart3 size={20} />
          </div>
          <div>
            <h3 style={{ fontSize: '1.15rem', color: '#f8fafc', fontWeight: 600 }}>Multi-Hazard Prediction Accuracy Metrics</h3>
            <p style={{ fontSize: '0.82rem', color: '#94a3b8' }}>
              Separately evaluates Heatwave, Pluvial Flood, and Water Scarcity models against verified municipal outcomes
            </p>
          </div>
        </div>

        <button 
          onClick={handleRunEvaluation}
          disabled={runningEval}
          className="btn btn-primary"
          style={{ fontSize: '0.82rem' }}
        >
          <RefreshCw size={14} className={runningEval ? 'spin' : ''} />
          {runningEval ? 'Evaluating Real Pairs...' : 'Run Statistical Evaluation'}
        </button>
      </div>

      {/* Evaluation Feedback Message */}
      {evalMsg && (
        <div style={{ 
          padding: '10px 14px', 
          background: evalMsg.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(244, 63, 94, 0.15)', 
          border: `1px solid ${evalMsg.type === 'success' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)'}`,
          borderRadius: '8px', 
          color: evalMsg.type === 'success' ? '#34d399' : '#fb7185', 
          fontSize: '0.82rem', 
          marginBottom: '18px' 
        }}>
          {evalMsg.text}
        </div>
      )}

      {/* Epistemic Guardrail Notice */}
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        gap: '8px', 
        background: 'rgba(15, 23, 42, 0.6)', 
        padding: '10px 14px', 
        borderRadius: '8px', 
        border: '1px solid var(--border-subtle)',
        marginBottom: '20px',
        fontSize: '0.78rem',
        color: '#cbd5e1'
      }}>
        <Info size={16} color="#38bdf8" />
        <span>
          <strong>Scientific Integrity Guardrail:</strong> Accuracy metrics are computed strictly against empirical real observations. Simulated data and incomplete actions are safely filtered out to prevent artificial metric inflation.
        </span>
      </div>

      {/* Hazard-Specific Accuracy Metric Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
        {renderMetricCard(
          'Heatwave Risk Accuracy',
          <Flame size={18} />,
          heatMetrics,
          { bg: 'rgba(244, 63, 94, 0.15)', color: '#fb7185' }
        )}

        {renderMetricCard(
          'Waterlogging / Flood Accuracy',
          <Waves size={18} />,
          floodMetrics,
          { bg: 'rgba(6, 182, 212, 0.15)', color: '#06b6d4' }
        )}

        {renderMetricCard(
          'Water Shortage Accuracy',
          <Droplet size={18} />,
          shortageMetrics,
          { bg: 'rgba(59, 130, 246, 0.15)', color: '#3b82f6' }
        )}
      </div>
    </div>
  );
}
