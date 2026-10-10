/**
 * ClimateShield API Client - Learning Loop & Municipal Decision Engine
 */

const API_BASE = '/api';

async function handleResponse(res) {
  if (!res.ok) {
    let detail = `Request failed with status ${res.status}`;
    try {
      const err = await res.json();
      detail = err.detail || detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  // System Health
  checkHealth: async () => {
    try {
      const res = await fetch('/');
      return await handleResponse(res);
    } catch (e) {
      return { status: 'OFFLINE', error: e.message };
    }
  },

  // 1. Predictions
  getPredictions: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.ward_id) query.append('ward_id', params.ward_id);
    if (params.hazard_type) query.append('hazard_type', params.hazard_type);
    if (params.provenance) query.append('provenance', params.provenance);
    query.append('limit', params.limit || '100');
    const res = await fetch(`${API_BASE}/learning/predictions?${query.toString()}`);
    return await handleResponse(res);
  },

  createPrediction: async (data) => {
    const res = await fetch(`${API_BASE}/learning/predictions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return await handleResponse(res);
  },

  // 2. Executed Actions
  getActions: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.ward_id) query.append('ward_id', params.ward_id);
    if (params.execution_status) query.append('execution_status', params.execution_status);
    query.append('limit', params.limit || '100');
    const res = await fetch(`${API_BASE}/learning/actions?${query.toString()}`);
    return await handleResponse(res);
  },

  createAction: async (data) => {
    const res = await fetch(`${API_BASE}/learning/actions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return await handleResponse(res);
  },

  patchAction: async (actionId, data) => {
    const res = await fetch(`${API_BASE}/learning/actions/${actionId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return await handleResponse(res);
  },

  // 3. Verified Outcomes
  getOutcomes: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.ward_id) query.append('ward_id', params.ward_id);
    if (params.provenance) query.append('provenance', params.provenance);
    if (params.action_id) query.append('action_id', params.action_id);
    query.append('limit', params.limit || '100');
    const res = await fetch(`${API_BASE}/learning/outcomes?${query.toString()}`);
    return await handleResponse(res);
  },

  recordOutcome: async (data) => {
    const res = await fetch(`${API_BASE}/learning/outcomes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return await handleResponse(res);
  },

  // 4. Lineage & Impact Verification
  getLineage: async (predictionId) => {
    const res = await fetch(`${API_BASE}/learning/lineage/${predictionId}`);
    return await handleResponse(res);
  },

  verifyImpact: async (data) => {
    const res = await fetch(`${API_BASE}/impact/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return await handleResponse(res);
  },

  getVerifications: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.action_id) query.append('action_id', params.action_id);
    if (params.ward_id) query.append('ward_id', params.ward_id);
    query.append('limit', params.limit || '100');
    const res = await fetch(`${API_BASE}/impact/verifications?${query.toString()}`);
    return await handleResponse(res);
  },

  // 5. Model Evaluation & Performance
  runEvaluation: async (data = { eval_window_days: 30, min_samples: 3, exclude_simulated: true }) => {
    const res = await fetch(`${API_BASE}/learning/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return await handleResponse(res);
  },

  getEvaluations: async (limit = 20) => {
    const res = await fetch(`${API_BASE}/learning/evaluations?limit=${limit}`);
    return await handleResponse(res);
  },

  // 6. Proposed Updates & Approval
  getProposals: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.status) query.append('status', params.status);
    if (params.target_ward) query.append('target_ward', params.target_ward);
    const res = await fetch(`${API_BASE}/learning/proposals?${query.toString()}`);
    return await handleResponse(res);
  },

  approveProposal: async (proposalId, data) => {
    const res = await fetch(`${API_BASE}/learning/proposals/${proposalId}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return await handleResponse(res);
  },

  rejectProposal: async (proposalId, data) => {
    const res = await fetch(`${API_BASE}/learning/proposals/${proposalId}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return await handleResponse(res);
  },

  // 7. Model Versions & Parameters
  getActiveParameters: async () => {
    const res = await fetch(`${API_BASE}/learning/active-parameters`);
    return await handleResponse(res);
  },

  getVersions: async () => {
    const res = await fetch(`${API_BASE}/learning/versions`);
    return await handleResponse(res);
  },

  rollbackVersion: async (versionId, data) => {
    const res = await fetch(`${API_BASE}/learning/versions/${versionId}/rollback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return await handleResponse(res);
  },

  // Wards List
  getWards: async () => {
    const res = await fetch(`${API_BASE}/wards`);
    return await handleResponse(res);
  }
};
