// ClimateShield API Client with Graceful Fallback
import {
  TOP_RISK_WARDS,
  EXECUTIVE_KPIS,
  ACTION_CENTRE_KPIS,
  FIELD_OPERATIONS,
  IMPACT_KPIS,
  IMPACT_AUDIT_CASES
} from '../data/mockData';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function safeFetch(endpoint, options = {}) {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2500);
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      ...options,
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    // Return null on failure to allow caller to use fallback
    return null;
  }
}

export const ClimateShieldAPI = {
  // Ward Data
  async getWards() {
    const data = await safeFetch('/api/wards');
    if (data && data.wards) return data.wards;
    return TOP_RISK_WARDS;
  },

  // Weather & WBGT
  async getWeatherWBGT() {
    const data = await safeFetch('/api/weather/wbgt');
    return data || null;
  },

  // Combined Climate Risk
  async getCombinedClimateRisk() {
    const data = await safeFetch('/api/climate/combined-risk');
    return data || null;
  },

  // Impact Assessments
  async getImpactAssessments() {
    const data = await safeFetch('/api/impact/assessments');
    if (data && data.assessments) return data.assessments;
    return IMPACT_AUDIT_CASES;
  },

  // Impact Summary
  async getImpactSummary() {
    const data = await safeFetch('/api/impact/summary');
    return data || IMPACT_KPIS;
  },

  // Run What-If Simulation
  async runSimulation(payload) {
    const data = await safeFetch('/api/interventions/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return data;
  }
};
