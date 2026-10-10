import React, { useState } from 'react';
import { 
  Sparkles, 
  CheckCircle2, 
  AlertTriangle, 
  ShieldAlert, 
  HelpCircle, 
  Scale, 
  ArrowRight,
  TrendingDown
} from 'lucide-react';
import { api } from '../api';

export default function ImpactVerificationModal({ action, wards = [], onClose }) {
  const [controlWard, setControlWard] = useState('W9');
  const [primaryMetric, setPrimaryMetric] = useState('hospital_heat_admissions');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleRunVerification = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = {
        action_id: action.action_id,
        primary_metric: primaryMetric,
        control_ward_id: controlWard === 'NONE' ? undefined : controlWard
      };
      const res = await api.verifyImpact(payload);
      setResult(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content" style={{ maxWidth: '640px', padding: '24px', maxHeight: '90vh', overflowY: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sparkles size={20} color="#06b6d4" />
            <h3 style={{ fontSize: '1.15rem', color: '#f8fafc' }}>
              Intervention Impact Verification
            </h3>
          </div>
          <button 
            onClick={onClose}
            style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '1.2rem' }}
          >
            ✕
          </button>
        </div>

        {/* Target Action Summary */}
        <div style={{ background: 'rgba(15, 23, 42, 0.7)', padding: '12px 14px', borderRadius: '8px', border: '1px solid var(--border-subtle)', marginBottom: '16px', fontSize: '0.82rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
            <span style={{ color: '#94a3b8' }}>Action ID:</span>
            <span style={{ fontFamily: 'var(--font-mono)', color: '#38bdf8' }}>{action.action_id}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
            <span style={{ color: '#94a3b8' }}>Intervention Dispatched:</span>
            <strong style={{ color: '#f8fafc', textTransform: 'capitalize' }}>{action.intervention_type}</strong>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: '#94a3b8' }}>Treated Ward:</span>
            <strong style={{ color: '#34d399' }}>{action.ward_name || action.ward_id} ({action.ward_id})</strong>
          </div>
        </div>

        {error && (
          <div style={{ padding: '10px 14px', background: 'rgba(244, 63, 94, 0.15)', border: '1px solid rgba(244, 63, 94, 0.3)', borderRadius: '8px', color: '#fb7185', fontSize: '0.82rem', marginBottom: '16px' }}>
            {error}
          </div>
        )}

        {/* Evaluation Configuration */}
        {!result && (
          <div>
            <div style={{ marginBottom: '14px' }}>
              <label style={{ display: 'block', fontSize: '0.8rem', color: '#cbd5e1', marginBottom: '6px' }}>
                Primary Evaluation Indicator *
              </label>
              <select 
                value={primaryMetric}
                onChange={e => setPrimaryMetric(e.target.value)}
                className="form-select"
              >
                <option value="hospital_heat_admissions">Hospital Heatstroke Inpatient Admissions (AMC)</option>
                <option value="emergency_108_calls">108 Emergency Ambulance Heat Dispatches</option>
                <option value="water_scarcity_complaints">Civic CCRS 155303 Water Complaints</option>
                <option value="waterlogging_depth_cm">Waterlogging Depth at Chronic Surcharge Points (cm)</option>
              </select>
            </div>

            <div style={{ marginBottom: '18px' }}>
              <label style={{ display: 'block', fontSize: '0.8rem', color: '#cbd5e1', marginBottom: '6px' }}>
                Comparison Control Ward (For Difference-in-Differences Causal Estimation)
              </label>
              <select 
                value={controlWard}
                onChange={e => setControlWard(e.target.value)}
                className="form-select"
              >
                <option value="NONE">— Simple Before &amp; After (Correlational Only) —</option>
                {wards.filter(w => w.id !== action.ward_id).map(w => (
                  <option key={w.id || w.name} value={w.id || w.name}>
                    {w.name} ({w.id}) — Control Ward
                  </option>
                ))}
              </select>
              <span style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '4px', display: 'block' }}>
                Select an un-intervened comparison ward to calculate the net treatment effect and control for background weather changes.
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button 
                type="button" 
                onClick={onClose}
                className="btn btn-secondary"
                disabled={loading}
              >
                Cancel
              </button>
              <button 
                onClick={handleRunVerification}
                className="btn btn-primary"
                disabled={loading}
              >
                {loading ? 'Evaluating Observations...' : 'Run Impact Verification'}
              </button>
            </div>
          </div>
        )}

        {/* Verification Result Display */}
        {result && (
          <div>
            <div style={{ 
              background: result.status === 'VERIFIED_COMPLETED' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)', 
              border: `1px solid ${result.status === 'VERIFIED_COMPLETED' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`,
              padding: '12px 14px', 
              borderRadius: '8px', 
              marginBottom: '16px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <span style={{ fontSize: '0.82rem', fontWeight: 600, color: result.status === 'VERIFIED_COMPLETED' ? '#34d399' : '#fbbf24' }}>
                  Status: {result.status}
                </span>
                <span className="badge badge-unverified">
                  Methodology: {result.evaluation_methodology || 'N/A'}
                </span>
              </div>
              <p style={{ fontSize: '0.78rem', color: '#cbd5e1', lineHeight: 1.4 }}>
                {result.explanation}
              </p>
            </div>

            {/* Causal Attribution Guardrail Disclaimer */}
            <div style={{ 
              background: 'rgba(244, 63, 94, 0.08)', 
              border: '1px solid rgba(244, 63, 94, 0.25)', 
              padding: '10px 12px', 
              borderRadius: '8px', 
              fontSize: '0.74rem', 
              color: '#fb7185',
              marginBottom: '16px' 
            }}>
              <strong>Epistemic Guardrail:</strong> {result.causal_disclaimer || result.disclaimer}
            </div>

            {/* Comparison Metrics if Verified */}
            {result.baseline_measurement && result.followup_measurement && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '16px' }}>
                <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '12px', borderRadius: '8px' }}>
                  <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Baseline Measurement</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f8fafc', marginTop: '2px' }}>
                    {result.baseline_measurement.value}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: '#64748b' }}>
                    Date: {result.baseline_measurement.date}
                  </div>
                </div>

                <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '12px', borderRadius: '8px' }}>
                  <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>Follow-up Measurement</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#10b981', marginTop: '2px' }}>
                    {result.followup_measurement.value}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: '#64748b' }}>
                    Date: {result.followup_measurement.date}
                  </div>
                </div>
              </div>
            )}

            {/* DiD Specific Estimate */}
            {result.difference_in_differences && result.difference_in_differences.eligible && (
              <div style={{ background: 'rgba(6, 182, 212, 0.08)', border: '1px solid rgba(6, 182, 212, 0.25)', padding: '12px 14px', borderRadius: '8px', marginBottom: '16px' }}>
                <div style={{ fontSize: '0.78rem', fontWeight: 600, color: '#06b6d4', marginBottom: '6px' }}>
                  Net Difference-in-Differences Treatment Effect (vs {result.difference_in_differences.control_ward_id})
                </div>
                <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#f8fafc', fontFamily: 'var(--font-mono)' }}>
                  {result.difference_in_differences.did_estimate} <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>net units prevented</span>
                </div>
                <div style={{ fontSize: '0.72rem', color: '#cbd5e1', marginTop: '4px' }}>
                  95% Confidence Interval: [{result.difference_in_differences.confidence_interval_95?.lower}, {result.difference_in_differences.confidence_interval_95?.upper}]
                </div>
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
              <button 
                onClick={() => setResult(null)}
                className="btn btn-secondary"
              >
                Re-evaluate
              </button>
              <button 
                onClick={onClose}
                className="btn btn-primary"
              >
                Done
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
