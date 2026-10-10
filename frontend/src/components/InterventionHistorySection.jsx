import React, { useState } from 'react';
import { 
  ClipboardCheck, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  AlertTriangle, 
  Send, 
  Sparkles, 
  Edit3, 
  ChevronRight,
  Filter,
  Users,
  Droplet,
  IndianRupee
} from 'lucide-react';
import { api } from '../api';

export default function InterventionHistorySection({ actions = [], onActionUpdated, onOpenVerifyModal }) {
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [editingAction, setEditingAction] = useState(null);
  const [patchForm, setPatchForm] = useState({
    execution_status: 'COMPLETED',
    actual_cost_inr: '',
    actual_crew_used: '',
    actual_water_used_l: '',
    failure_reason: '',
    notes: ''
  });
  const [loadingPatch, setLoadingPatch] = useState(false);
  const [patchError, setPatchError] = useState(null);

  const filteredActions = actions.filter(a => {
    if (statusFilter === 'ALL') return true;
    return a.execution_status === statusFilter;
  });

  const counts = {
    total: actions.length,
    completed: actions.filter(a => a.execution_status === 'COMPLETED').length,
    inProgress: actions.filter(a => a.execution_status === 'IN_PROGRESS').length,
    scheduled: actions.filter(a => a.execution_status === 'SCHEDULED').length,
    failed: actions.filter(a => a.execution_status === 'FAILED' || a.execution_status === 'CANCELLED').length,
  };

  const handleOpenEdit = (action) => {
    setEditingAction(action);
    setPatchForm({
      execution_status: action.execution_status || 'COMPLETED',
      actual_cost_inr: action.actual_cost_inr ?? '',
      actual_crew_used: action.actual_crew_used ?? '',
      actual_water_used_l: action.actual_water_used_l ?? '',
      failure_reason: action.failure_reason ?? '',
      notes: action.notes ?? ''
    });
    setPatchError(null);
  };

  const handleSavePatch = async (e) => {
    e.preventDefault();
    if (!editingAction) return;
    setLoadingPatch(true);
    setPatchError(null);

    try {
      const payload = {
        execution_status: patchForm.execution_status,
        actual_cost_inr: patchForm.actual_cost_inr !== '' ? Number(patchForm.actual_cost_inr) : undefined,
        actual_crew_used: patchForm.actual_crew_used !== '' ? Number(patchForm.actual_crew_used) : undefined,
        actual_water_used_l: patchForm.actual_water_used_l !== '' ? Number(patchForm.actual_water_used_l) : undefined,
        failure_reason: patchForm.failure_reason ? patchForm.failure_reason.trim() : undefined,
        notes: patchForm.notes ? patchForm.notes.trim() : undefined
      };

      if ((payload.execution_status === 'FAILED' || payload.execution_status === 'CANCELLED') && !payload.failure_reason) {
        throw new Error('Failure reason is strictly required when marking action as FAILED or CANCELLED.');
      }

      await api.patchAction(editingAction.action_id, payload);
      setEditingAction(null);
      if (onActionUpdated) onActionUpdated();
    } catch (err) {
      setPatchError(err.message);
    } finally {
      setLoadingPatch(false);
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'COMPLETED':
        return <span className="badge badge-completed"><CheckCircle2 size={12} /> Completed</span>;
      case 'FAILED':
      case 'CANCELLED':
        return <span className="badge badge-failed"><XCircle size={12} /> {status}</span>;
      case 'IN_PROGRESS':
        return <span className="badge badge-progress"><Clock size={12} /> In Progress</span>;
      case 'SCHEDULED':
      default:
        return <span className="badge badge-scheduled"><Clock size={12} /> Scheduled</span>;
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
      {/* Title & Summary Cards */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', padding: '8px', borderRadius: '8px' }}>
            <ClipboardCheck size={20} />
          </div>
          <div>
            <h3 style={{ fontSize: '1.15rem', color: '#f8fafc', fontWeight: 600 }}>Executed Municipal Field Actions</h3>
            <p style={{ fontSize: '0.82rem', color: '#94a3b8' }}>
              Relational tracking of human authorizations, dispatched field interventions, actual resource consumption, and completion states
            </p>
          </div>
        </div>

        {/* Filter */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(15, 23, 42, 0.8)', padding: '4px 10px', borderRadius: '8px', border: '1px solid var(--border-subtle)' }}>
          <Filter size={14} color="#94a3b8" />
          <select 
            value={statusFilter} 
            onChange={e => setStatusFilter(e.target.value)}
            className="form-select"
            style={{ padding: '4px 8px', fontSize: '0.8rem', background: 'transparent', border: 'none', color: '#f8fafc' }}
          >
            <option value="ALL" style={{ background: '#0f172a' }}>All Statuses ({counts.total})</option>
            <option value="COMPLETED" style={{ background: '#0f172a' }}>Completed ({counts.completed})</option>
            <option value="IN_PROGRESS" style={{ background: '#0f172a' }}>In Progress ({counts.inProgress})</option>
            <option value="SCHEDULED" style={{ background: '#0f172a' }}>Scheduled ({counts.scheduled})</option>
            <option value="FAILED" style={{ background: '#0f172a' }}>Failed/Cancelled ({counts.failed})</option>
          </select>
        </div>
      </div>

      {/* KPI Stats Bar */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '12px', marginBottom: '20px' }}>
        <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '12px 14px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', textTransform: 'uppercase' }}>Total Dispatched</div>
          <div style={{ fontSize: '1.35rem', fontWeight: 700, color: '#f8fafc', marginTop: '2px' }}>{counts.total}</div>
        </div>
        <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '12px 14px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '0.75rem', color: '#34d399', textTransform: 'uppercase' }}>Completed</div>
          <div style={{ fontSize: '1.35rem', fontWeight: 700, color: '#34d399', marginTop: '2px' }}>{counts.completed}</div>
        </div>
        <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '12px 14px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '0.75rem', color: '#38bdf8', textTransform: 'uppercase' }}>In Progress</div>
          <div style={{ fontSize: '1.35rem', fontWeight: 700, color: '#38bdf8', marginTop: '2px' }}>{counts.inProgress}</div>
        </div>
        <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '12px 14px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '0.75rem', color: '#fbbf24', textTransform: 'uppercase' }}>Scheduled</div>
          <div style={{ fontSize: '1.35rem', fontWeight: 700, color: '#fbbf24', marginTop: '2px' }}>{counts.scheduled}</div>
        </div>
        <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '12px 14px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: '0.75rem', color: '#fb7185', textTransform: 'uppercase' }}>Failed / Cancelled</div>
          <div style={{ fontSize: '1.35rem', fontWeight: 700, color: '#fb7185', marginTop: '2px' }}>{counts.failed}</div>
        </div>
      </div>

      {/* Table */}
      {filteredActions.length === 0 ? (
        <div className="empty-state" style={{ minHeight: '180px' }}>
          <ClipboardCheck className="empty-state-icon" />
          <h4 style={{ fontSize: '0.95rem', color: '#f8fafc', marginBottom: '4px' }}>No Field Actions Recorded</h4>
          <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
            {statusFilter === 'ALL' 
              ? 'No municipal field interventions have been dispatched or logged in the system yet.'
              : `No actions match the '${statusFilter}' status filter.`}
          </p>
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Action ID</th>
                <th>Ward</th>
                <th>Intervention Dispatched</th>
                <th>Authorized By</th>
                <th>Execution Status</th>
                <th>Actual Resources Used</th>
                <th>Failure / Operational Notes</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredActions.map(action => (
                <tr key={action.action_id}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: '#38bdf8' }}>
                    {action.action_id}
                  </td>
                  <td>
                    <span style={{ fontWeight: 600 }}>{action.ward_name || action.ward_id}</span>
                  </td>
                  <td>
                    <span style={{ fontWeight: 500, color: '#cbd5e1', textTransform: 'capitalize' }}>
                      {action.intervention_type.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td>
                    <div style={{ fontSize: '0.8rem' }}>
                      <span style={{ color: '#f8fafc', fontWeight: 500 }}>{action.approved_by}</span>
                      <div style={{ fontSize: '0.7rem', color: '#64748b' }}>
                        {action.approved_at ? action.approved_at.slice(0, 10) : 'Pre-approved'}
                      </div>
                    </div>
                  </td>
                  <td>
                    {getStatusBadge(action.execution_status)}
                  </td>
                  <td>
                    <div style={{ fontSize: '0.76rem', color: '#cbd5e1' }}>
                      {action.actual_cost_inr ? (
                        <div>₹{action.actual_cost_inr.toLocaleString()}</div>
                      ) : null}
                      {action.actual_crew_used ? (
                        <div style={{ color: '#94a3b8' }}>{action.actual_crew_used} crew</div>
                      ) : null}
                      {action.actual_water_used_l ? (
                        <div style={{ color: '#94a3b8' }}>{action.actual_water_used_l} L water</div>
                      ) : null}
                      {!action.actual_cost_inr && !action.actual_crew_used && !action.actual_water_used_l && (
                        <span style={{ color: '#64748b' }}>— Unreported —</span>
                      )}
                    </div>
                  </td>
                  <td style={{ maxWidth: '200px' }}>
                    {action.failure_reason ? (
                      <div style={{ color: '#fb7185', fontSize: '0.76rem', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <AlertTriangle size={12} />
                        <span>{action.failure_reason}</span>
                      </div>
                    ) : action.notes ? (
                      <span style={{ color: '#94a3b8', fontSize: '0.76rem' }}>{action.notes}</span>
                    ) : (
                      <span style={{ color: '#475569', fontSize: '0.76rem' }}>None</span>
                    )}
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <button 
                        onClick={() => handleOpenEdit(action)}
                        className="btn btn-secondary"
                        style={{ padding: '5px 9px', fontSize: '0.75rem' }}
                        title="Update field execution status or report completion/failure"
                      >
                        <Edit3 size={12} /> Status
                      </button>
                      {action.execution_status === 'COMPLETED' && (
                        <button 
                          onClick={() => onOpenVerifyModal && onOpenVerifyModal(action)}
                          className="btn btn-primary"
                          style={{ padding: '5px 9px', fontSize: '0.75rem' }}
                          title="Evaluate empirical efficacy using Before-After or DiD"
                        >
                          <Sparkles size={12} /> Verify
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Status Patch Modal */}
      {editingAction && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '1.1rem', color: '#f8fafc' }}>
                Update Field Execution Status
              </h3>
              <button 
                onClick={() => setEditingAction(null)}
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '1.2rem' }}
              >
                ✕
              </button>
            </div>

            <div style={{ fontSize: '0.82rem', color: '#94a3b8', marginBottom: '16px' }}>
              Action: <strong style={{ color: '#38bdf8' }}>{editingAction.action_id}</strong> | Ward: <strong style={{ color: '#f8fafc' }}>{editingAction.ward_name || editingAction.ward_id}</strong> ({editingAction.intervention_type})
            </div>

            {patchError && (
              <div style={{ padding: '10px 14px', background: 'rgba(244, 63, 94, 0.15)', border: '1px solid rgba(244, 63, 94, 0.3)', borderRadius: '8px', color: '#fb7185', fontSize: '0.82rem', marginBottom: '16px' }}>
                {patchError}
              </div>
            )}

            <form onSubmit={handleSavePatch}>
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '0.8rem', color: '#cbd5e1', marginBottom: '6px' }}>
                  Execution State *
                </label>
                <select 
                  value={patchForm.execution_status}
                  onChange={e => setPatchForm({ ...patchForm, execution_status: e.target.value })}
                  className="form-select"
                >
                  <option value="SCHEDULED">SCHEDULED (Field crew queued)</option>
                  <option value="IN_PROGRESS">IN_PROGRESS (Currently deployed)</option>
                  <option value="COMPLETED">COMPLETED (Intervention executed)</option>
                  <option value="FAILED">FAILED (Disruption / equipment breakdown)</option>
                  <option value="CANCELLED">CANCELLED (Superseded or recalled)</option>
                </select>
              </div>

              {(patchForm.execution_status === 'FAILED' || patchForm.execution_status === 'CANCELLED') && (
                <div style={{ marginBottom: '14px' }}>
                  <label style={{ display: 'block', fontSize: '0.8rem', color: '#fb7185', marginBottom: '6px' }}>
                    Documented Failure Reason * (Required by Safety Protocol)
                  </label>
                  <input 
                    type="text"
                    required
                    placeholder="e.g. Pump generator seized; Tanker driver route flooded"
                    value={patchForm.failure_reason}
                    onChange={e => setPatchForm({ ...patchForm, failure_reason: e.target.value })}
                    className="form-input"
                    style={{ borderColor: 'rgba(244, 63, 94, 0.4)' }}
                  />
                </div>
              )}

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '10px', marginBottom: '14px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '4px' }}>
                    Actual Cost (₹)
                  </label>
                  <input 
                    type="number"
                    min="0"
                    placeholder="0"
                    value={patchForm.actual_cost_inr}
                    onChange={e => setPatchForm({ ...patchForm, actual_cost_inr: e.target.value })}
                    className="form-input"
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '4px' }}>
                    Actual Crew
                  </label>
                  <input 
                    type="number"
                    min="0"
                    placeholder="0"
                    value={patchForm.actual_crew_used}
                    onChange={e => setPatchForm({ ...patchForm, actual_crew_used: e.target.value })}
                    className="form-input"
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: '#94a3b8', marginBottom: '4px' }}>
                    Water Used (L)
                  </label>
                  <input 
                    type="number"
                    min="0"
                    placeholder="0"
                    value={patchForm.actual_water_used_l}
                    onChange={e => setPatchForm({ ...patchForm, actual_water_used_l: e.target.value })}
                    className="form-input"
                  />
                </div>
              </div>

              <div style={{ marginBottom: '18px' }}>
                <label style={{ display: 'block', fontSize: '0.8rem', color: '#cbd5e1', marginBottom: '6px' }}>
                  Operational Notes (Strictly Non-PII)
                </label>
                <textarea 
                  rows="2"
                  placeholder="Deployment notes, field logistics, site conditions (no personal info)..."
                  value={patchForm.notes}
                  onChange={e => setPatchForm({ ...patchForm, notes: e.target.value })}
                  className="form-input"
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button 
                  type="button" 
                  onClick={() => setEditingAction(null)}
                  className="btn btn-secondary"
                  disabled={loadingPatch}
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  className="btn btn-primary"
                  disabled={loadingPatch}
                >
                  {loadingPatch ? 'Updating...' : 'Commit Status Update'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
