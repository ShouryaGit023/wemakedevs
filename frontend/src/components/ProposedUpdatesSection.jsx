import React, { useState } from 'react';
import { 
  GitPullRequest, 
  CheckCheck, 
  XOctagon, 
  UserCheck, 
  FileText, 
  AlertCircle,
  HelpCircle,
  ShieldAlert,
  ArrowRight
} from 'lucide-react';
import { api } from '../api';

export default function ProposedUpdatesSection({ proposals = [], onProposalUpdated }) {
  const [selectedProposal, setSelectedProposal] = useState(null);
  const [modalMode, setModalMode] = useState(null); // 'APPROVE' or 'REJECT'
  const [authorityName, setAuthorityName] = useState('');
  const [reviewNotes, setReviewNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const pendingProposals = proposals.filter(p => p.status === 'PENDING_APPROVAL');
  const pastProposals = proposals.filter(p => p.status !== 'PENDING_APPROVAL');

  const handleOpenApprove = (prop) => {
    setSelectedProposal(prop);
    setModalMode('APPROVE');
    setAuthorityName('Municipal Commissioner (AMC)');
    setReviewNotes('Validated against 30-day verified hospital surveillance admissions.');
    setError(null);
  };

  const handleOpenReject = (prop) => {
    setSelectedProposal(prop);
    setModalMode('REJECT');
    setAuthorityName('Disaster Management Authority');
    setReviewNotes('Observed variance deemed temporary due to unseasonal rainfall. Retaining baseline prior.');
    setError(null);
  };

  const handleConfirmDecision = async (e) => {
    e.preventDefault();
    if (!selectedProposal || !modalMode) return;
    setLoading(true);
    setError(null);

    try {
      if (!authorityName.trim()) {
        throw new Error('Named municipal official/role is required for governance authorization.');
      }

      if (modalMode === 'APPROVE') {
        const res = await api.approveProposal(selectedProposal.proposal_id, {
          approved_by: authorityName.trim(),
          review_notes: reviewNotes.trim() || undefined
        });
        setSuccessMsg(`Proposal ${selectedProposal.proposal_id} APPROVED! Created new active model version ${res.new_active_model_version}.`);
      } else {
        if (!reviewNotes.trim()) {
          throw new Error('Documented justification reason is required to reject a parameter proposal.');
        }
        await api.rejectProposal(selectedProposal.proposal_id, {
          reviewed_by: authorityName.trim(),
          review_notes: reviewNotes.trim()
        });
        setSuccessMsg(`Proposal ${selectedProposal.proposal_id} REJECTED. Production parameters remain untouched.`);
      }

      setSelectedProposal(null);
      setModalMode(null);
      if (onProposalUpdated) onProposalUpdated();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '24px', marginBottom: '24px' }}>
      {/* Title & Governance Banner */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ background: 'rgba(245, 158, 11, 0.15)', color: '#f59e0b', padding: '8px', borderRadius: '8px' }}>
            <GitPullRequest size={20} />
          </div>
          <div>
            <h3 style={{ fontSize: '1.15rem', color: '#f8fafc', fontWeight: 600 }}>Proposed Model Parameter Updates</h3>
            <p style={{ fontSize: '0.82rem', color: '#94a3b8' }}>
              Human-in-the-Loop Governance: Model parameters NEVER auto-mutate in production. All proposed weight calibrations require named municipal authorization.
            </p>
          </div>
        </div>

        <span className={`badge ${pendingProposals.length > 0 ? 'badge-scheduled' : 'badge-completed'}`}>
          {pendingProposals.length > 0 ? `${pendingProposals.length} Pending Approval` : 'All Proposals Resolved'}
        </span>
      </div>

      {successMsg && (
        <div style={{ padding: '10px 14px', background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: '8px', color: '#34d399', fontSize: '0.82rem', marginBottom: '16px' }}>
          {successMsg}
        </div>
      )}

      {/* Pending Proposals Section */}
      <div style={{ marginBottom: '24px' }}>
        <h4 style={{ fontSize: '0.88rem', color: '#cbd5e1', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span>Staged Proposals Awaiting Municipal Approval</span>
          <span style={{ fontSize: '0.74rem', color: '#64748b' }}>({pendingProposals.length})</span>
        </h4>

        {pendingProposals.length === 0 ? (
          <div style={{ 
            background: 'rgba(15, 23, 42, 0.5)', 
            padding: '24px 16px', 
            borderRadius: '10px', 
            border: '1px dashed var(--border-subtle)',
            textAlign: 'center',
            color: '#94a3b8'
          }}>
            <UserCheck size={28} color="#34d399" style={{ margin: '0 auto 8px auto', opacity: 0.8 }} />
            <div style={{ fontSize: '0.88rem', color: '#f8fafc', fontWeight: 500, marginBottom: '2px' }}>
              No Pending Proposals
            </div>
            <p style={{ fontSize: '0.76rem', color: '#64748b' }}>
              Production risk parameters are calibrated and in consensus with verified real observations.
            </p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {pendingProposals.map(prop => (
              <div 
                key={prop.proposal_id}
                style={{ 
                  background: 'rgba(30, 41, 59, 0.5)', 
                  border: '1px solid rgba(245, 158, 11, 0.3)', 
                  borderRadius: '10px', 
                  padding: '16px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  flexWrap: 'wrap',
                  gap: '14px'
                }}
              >
                <div style={{ flex: 1, minWidth: '280px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: '#38bdf8' }}>
                      {prop.proposal_id}
                    </span>
                    <span className="badge badge-scheduled">Pending Approval</span>
                    <span style={{ fontSize: '0.74rem', color: '#94a3b8' }}>
                      Supporting Evidence: <strong>{prop.supporting_samples_count} real observations</strong>
                    </span>
                  </div>

                  <div style={{ fontSize: '0.9rem', color: '#f8fafc', fontWeight: 600, marginBottom: '4px' }}>
                    Target: {prop.target_parameter_type} for Ward '{prop.target_identifier}'
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '0.82rem', margin: '8px 0', fontFamily: 'var(--font-mono)' }}>
                    <span style={{ color: '#94a3b8' }}>Current: <strong>{prop.current_value}</strong></span>
                    <ArrowRight size={14} color="#64748b" />
                    <span style={{ color: '#38bdf8' }}>Proposed: <strong>{prop.proposed_value}</strong></span>
                    <span style={{ 
                      color: prop.delta > 0 ? '#fb7185' : '#34d399', 
                      background: 'rgba(0,0,0,0.3)', 
                      padding: '2px 6px', 
                      borderRadius: '4px' 
                    }}>
                      Delta: {prop.delta > 0 ? `+${prop.delta}` : prop.delta}
                    </span>
                  </div>

                  <p style={{ fontSize: '0.78rem', color: '#cbd5e1', marginTop: '6px', lineHeight: 1.4 }}>
                    {prop.justification}
                  </p>
                </div>

                <div style={{ display: 'flex', gap: '8px', alignSelf: 'center' }}>
                  <button 
                    onClick={() => handleOpenReject(prop)}
                    className="btn btn-danger"
                    style={{ padding: '6px 12px', fontSize: '0.78rem' }}
                  >
                    <XOctagon size={13} /> Reject
                  </button>
                  <button 
                    onClick={() => handleOpenApprove(prop)}
                    className="btn btn-success"
                    style={{ padding: '6px 12px', fontSize: '0.78rem' }}
                  >
                    <CheckCheck size={13} /> Authorize &amp; Deploy
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Historical Resolved Proposals */}
      {pastProposals.length > 0 && (
        <div>
          <h4 style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '10px' }}>
            Archived Proposal Resolutions ({pastProposals.length})
          </h4>
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Proposal ID</th>
                  <th>Target Parameter</th>
                  <th>Value Change</th>
                  <th>Status</th>
                  <th>Reviewed By</th>
                  <th>Review Notes</th>
                </tr>
              </thead>
              <tbody>
                {pastProposals.map(p => (
                  <tr key={p.proposal_id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.76rem', color: '#94a3b8' }}>
                      {p.proposal_id}
                    </td>
                    <td style={{ fontSize: '0.8rem' }}>
                      {p.target_parameter_type} ({p.target_identifier})
                    </td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem' }}>
                      {p.current_value} → {p.proposed_value} ({p.delta > 0 ? `+${p.delta}` : p.delta})
                    </td>
                    <td>
                      <span className={`badge ${p.status === 'APPROVED' ? 'badge-completed' : 'badge-failed'}`}>
                        {p.status}
                      </span>
                    </td>
                    <td style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>
                      {p.reviewed_by || '—'}
                    </td>
                    <td style={{ fontSize: '0.76rem', color: '#94a3b8', maxWidth: '240px' }}>
                      {p.review_notes || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Decision Modal */}
      {selectedProposal && modalMode && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '1.1rem', color: '#f8fafc' }}>
                {modalMode === 'APPROVE' ? 'Authorize Parameter Update' : 'Reject Parameter Update'}
              </h3>
              <button 
                onClick={() => { setSelectedProposal(null); setModalMode(null); }}
                style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', fontSize: '1.2rem' }}
              >
                ✕
              </button>
            </div>

            <div style={{ 
              background: modalMode === 'APPROVE' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(244, 63, 94, 0.1)', 
              border: `1px solid ${modalMode === 'APPROVE' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)'}`,
              padding: '10px 14px', 
              borderRadius: '8px', 
              fontSize: '0.8rem', 
              color: modalMode === 'APPROVE' ? '#34d399' : '#fb7185',
              marginBottom: '16px'
            }}>
              {modalMode === 'APPROVE' 
                ? 'Approving will commit a new immutable model version (e.g. v1.1.0) and activate the new vulnerability offset.' 
                : 'Rejecting will leave production model parameters unchanged and archive the proposal with documented rationale.'}
            </div>

            {error && (
              <div style={{ padding: '10px 14px', background: 'rgba(244, 63, 94, 0.15)', border: '1px solid rgba(244, 63, 94, 0.3)', borderRadius: '8px', color: '#fb7185', fontSize: '0.82rem', marginBottom: '16px' }}>
                {error}
              </div>
            )}

            <form onSubmit={handleConfirmDecision}>
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '0.8rem', color: '#cbd5e1', marginBottom: '6px' }}>
                  Authorizing Municipal Authority / Role *
                </label>
                <input 
                  type="text"
                  required
                  placeholder="e.g. AMC Health Officer, Disaster Mgmt Commissioner"
                  value={authorityName}
                  onChange={e => setAuthorityName(e.target.value)}
                  className="form-input"
                />
                <span style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '3px', display: 'block' }}>
                  Note: Logged for civic audit compliance.
                </span>
              </div>

              <div style={{ marginBottom: '18px' }}>
                <label style={{ display: 'block', fontSize: '0.8rem', color: '#cbd5e1', marginBottom: '6px' }}>
                  {modalMode === 'APPROVE' ? 'Review / Justification Notes (Optional)' : 'Documented Reason for Rejection *'}
                </label>
                <textarea 
                  rows="3"
                  required={modalMode === 'REJECT'}
                  placeholder={modalMode === 'APPROVE' ? 'Document rationale or supporting context...' : 'Reason for rejecting this calibration proposal...'}
                  value={reviewNotes}
                  onChange={e => setReviewNotes(e.target.value)}
                  className="form-input"
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
                <button 
                  type="button" 
                  onClick={() => { setSelectedProposal(null); setModalMode(null); }}
                  className="btn btn-secondary"
                  disabled={loading}
                >
                  Cancel
                </button>
                <button 
                  type="submit" 
                  className={`btn ${modalMode === 'APPROVE' ? 'btn-success' : 'btn-danger'}`}
                  disabled={loading}
                >
                  {loading ? 'Processing...' : (modalMode === 'APPROVE' ? 'Commit & Activate Version' : 'Confirm Rejection')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
