import React, { useState } from 'react';
import { 
  GitCommit, 
  RotateCcw, 
  CheckCircle, 
  Calendar, 
  UserCheck, 
  Code,
  ShieldCheck,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { api } from '../api';

export default function ModelVersionsSection({ versions = [], activeVersion, onVersionRollback }) {
  const [expandedVersion, setExpandedVersion] = useState(null);
  const [rollbackTarget, setRollbackTarget] = useState(null);
  const [rollbackOfficial, setRollbackOfficial] = useState('AMC Disaster Cell Lead');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const handleRollback = async (e) => {
    e.preventDefault();
    if (!rollbackTarget) return;
    setLoading(true);
    setError(null);
    try {
      if (!rollbackOfficial.trim()) {
        throw new Error('Authorizing official name is required to execute a model version rollback.');
      }
      await api.rollbackVersion(rollbackTarget.version_id, {
        approved_by: rollbackOfficial.trim()
      });
      setSuccess(`Model rolled back successfully to version ${rollbackTarget.version_id}.`);
      setRollbackTarget(null);
      if (onVersionRollback) onVersionRollback();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#10b981', padding: '8px', borderRadius: '8px' }}>
            <GitCommit size={20} />
          </div>
          <div>
            <h3 style={{ fontSize: '1.15rem', color: '#f8fafc', fontWeight: 600 }}>Immutable Model Version History</h3>
            <p style={{ fontSize: '0.82rem', color: '#94a3b8' }}>
              Append-only audit ledger of production model weights, human sign-offs, and instant rollback capability
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.78rem', color: '#94a3b8' }}>Currently Active:</span>
          <span className="badge badge-completed" style={{ fontSize: '0.8rem', padding: '4px 12px' }}>
            <ShieldCheck size={13} /> {activeVersion?.version_id || 'v1.0.0'}
          </span>
        </div>
      </div>

      {success && (
        <div style={{ padding: '10px 14px', background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: '8px', color: '#34d399', fontSize: '0.82rem', marginBottom: '16px' }}>
          {success}
        </div>
      )}

      {/* Version History List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {versions.map(v => {
          const isActive = v.is_active || v.version_id === activeVersion?.version_id;
          const isExpanded = expandedVersion === v.version_id;
          const offsets = v.parameters?.ward_vulnerability_offsets || {};
          const offsetCount = Object.keys(offsets).length;

          return (
            <div 
              key={v.version_id}
              style={{ 
                background: isActive ? 'rgba(16, 185, 129, 0.05)' : 'rgba(15, 23, 42, 0.6)', 
                border: `1px solid ${isActive ? 'rgba(16, 185, 129, 0.35)' : 'var(--border-subtle)'}`, 
                borderRadius: '10px', 
                padding: '16px',
                transition: 'border-color 0.2s ease'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ 
                    fontFamily: 'var(--font-mono)', 
                    fontWeight: 700, 
                    fontSize: '1rem', 
                    color: isActive ? '#34d399' : '#f8fafc' 
                  }}>
                    {v.version_id}
                  </span>
                  {isActive ? (
                    <span className="badge badge-completed">Active In Production</span>
                  ) : (
                    <span className="badge badge-unverified">Archived</span>
                  )}
                  <span style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
                    Authorized by: <strong style={{ color: '#cbd5e1' }}>{v.approved_by || 'System Genesis'}</strong>
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '0.74rem', color: '#64748b' }}>
                    {(v.approved_at || '').slice(0, 16).replace('T', ' ')} UTC
                  </span>
                  {!isActive && (
                    <button 
                      onClick={() => setRollbackTarget(v)}
                      className="btn btn-secondary"
                      style={{ padding: '4px 10px', fontSize: '0.75rem' }}
                      title="Reactivate this vetted model configuration"
                    >
                      <RotateCcw size={12} /> Rollback
                    </button>
                  )}
                  <button 
                    onClick={() => setExpandedVersion(isExpanded ? null : v.version_id)}
                    className="btn btn-outline"
                    style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                  >
                    {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>
                </div>
              </div>

              <p style={{ fontSize: '0.82rem', color: '#cbd5e1', marginTop: '8px', lineHeight: 1.4 }}>
                {v.change_summary || 'Initial production baseline weights and empirical hazard priors.'}
              </p>

              {/* Collapsible Parameter Details */}
              {isExpanded && (
                <div style={{ marginTop: '14px', paddingTop: '12px', borderTop: '1px solid rgba(255, 255, 255, 0.06)' }}>
                  <div style={{ fontSize: '0.78rem', fontWeight: 600, color: '#94a3b8', marginBottom: '8px' }}>
                    Active Vulnerability Offsets ({offsetCount} Wards Calibrated):
                  </div>
                  {offsetCount === 0 ? (
                    <div style={{ fontSize: '0.75rem', color: '#64748b', fontStyle: 'italic' }}>
                      Standard baseline priors (0.00 offset across all Ahmedabad wards).
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {Object.entries(offsets).map(([ward, val]) => (
                        <span 
                          key={ward} 
                          style={{ 
                            background: 'rgba(0, 0, 0, 0.3)', 
                            padding: '3px 8px', 
                            borderRadius: '6px', 
                            fontSize: '0.74rem', 
                            fontFamily: 'var(--font-mono)',
                            color: Number(val) > 0 ? '#fb7185' : '#34d399' 
                          }}
                        >
                          {ward}: {Number(val) > 0 ? `+${val}` : val}
                        </span>
                      ))}
                    </div>
                  )}

                  <div style={{ marginTop: '10px', background: 'rgba(0,0,0,0.3)', padding: '10px', borderRadius: '6px' }}>
                    <pre style={{ fontSize: '0.72rem', color: '#94a3b8', overflowX: 'auto', margin: 0, fontFamily: 'var(--font-mono)' }}>
                      {JSON.stringify(v.parameters, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Rollback Confirmation Modal */}
      {rollbackTarget && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '1.1rem', color: '#f8fafc' }}>
                Confirm Model Rollback to {rollbackTarget.version_id}
              </h3>
              <button 
                onClick={() => setRollbackTarget(null)}
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '1.2rem' }}
              >
                ✕
              </button>
            </div>

            <div style={{ padding: '10px 14px', background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: '8px', color: '#fbbf24', fontSize: '0.8rem', marginBottom: '16px' }}>
              ⚠️ <strong>Rollback Advisory:</strong> This will instantly switch live production risk scoring back to parameters from <strong>{rollbackTarget.version_id}</strong>.
            </div>

            {error && (
              <div style={{ padding: '10px 14px', background: 'rgba(244, 63, 94, 0.15)', border: '1px solid rgba(244, 63, 94, 0.3)', borderRadius: '8px', color: '#fb7185', fontSize: '0.82rem', marginBottom: '16px' }}>
                {error}
              </div>
            )}

            <form onSubmit={handleRollback}>
              <div style={{ marginBottom: '18px' }}>
                <label style={{ display: 'block', fontSize: '0.8rem', color: '#cbd5e1', marginBottom: '6px' }}>
                  Authorizing Official Name / Role *
                </label>
                <input 
                  type="text"
                  required
                  value={rollbackOfficial}
                  onChange={e => setRollbackOfficial(e.target.value)}
                  className="form-input"
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button 
                  type="button" 
                  onClick={() => setRollbackTarget(null)}
                  className="btn btn-secondary"
                  disabled={loading}
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  className="btn btn-primary"
                  disabled={loading}
                >
                  {loading ? 'Rolling back...' : 'Confirm Rollback'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
