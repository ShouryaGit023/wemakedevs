// ClimateShield Centralized Frontend API Client
// Connected to FastAPI Decision Support System Server

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

class ApiError extends Error {
  constructor(message, status, details = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const config = {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...options.headers,
    },
  };

  try {
    const res = await fetch(url, config);
    if (!res.ok) {
      let errorDetail = `HTTP ${res.status}: ${res.statusText}`;
      try {
        const errorJson = await res.json();
        if (errorJson.detail) {
          errorDetail = typeof errorJson.detail === 'string' 
            ? errorJson.detail 
            : JSON.stringify(errorJson.detail);
        }
      } catch {
        // Fallback to status text
      }
      throw new ApiError(errorDetail, res.status);
    }
    return await res.json();
  } catch (err) {
    if (err instanceof ApiError) {
      throw err;
    }
    // Network or connection failure
    throw new ApiError(
      `Network connection to ClimateShield backend failed (${url}). Please ensure the FastAPI server is running on port 8000. Error: ${err.message}`,
      0
    );
  }
}

export const ClimateShieldAPI = {
  // System root status
  async getSystemStatus() {
    return request('/');
  },

  // 1. Weather & WBGT Forecasting
  async getWeatherWBGT(lat = 23.0225, lon = 72.5714) {
    return request(`/api/weather/wbgt?lat=${lat}&lon=${lon}`);
  },

  // 2. Ahmedabad Wards Baseline Vulnerabilities
  async getWards() {
    return request('/api/wards');
  },

  // 3. Official Ahmedabad Wards GeoJSON Spatial Boundaries
  async getWardsGeoJSON() {
    return request('/api/wards/geojson');
  },

  // 4. Combined Multi-Hazard Climate Risk (All 48 Wards)
  async getCombinedClimateRisk(params = {}) {
    const query = new URLSearchParams();
    if (params.scenario_id) query.append('scenario_id', params.scenario_id);
    if (params.weight_heat !== undefined) query.append('weight_heat', params.weight_heat);
    if (params.weight_water !== undefined) query.append('weight_water', params.weight_water);
    if (params.scoring_mode) query.append('scoring_mode', params.scoring_mode);
    if (params.heat_wbgt !== undefined) query.append('heat_wbgt', params.heat_wbgt);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return request(`/api/climate/combined-risk${qs}`);
  },

  // 5. Deterministic Climate Risk Rankings (Executive Priority List)
  async getClimateRiskRankings(params = {}) {
    const query = new URLSearchParams();
    if (params.limit !== undefined) query.append('limit', params.limit);
    if (params.compound_only !== undefined) query.append('compound_only', params.compound_only);
    if (params.scenario_id) query.append('scenario_id', params.scenario_id);
    if (params.weight_heat !== undefined) query.append('weight_heat', params.weight_heat);
    if (params.weight_water !== undefined) query.append('weight_water', params.weight_water);
    if (params.scoring_mode) query.append('scoring_mode', params.scoring_mode);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return request(`/api/climate-risk/rankings${qs}`);
  },

  // 6. Detailed Multi-Hazard Climate Risk for Single Ward
  async getSingleWardClimateRisk(wardId, params = {}) {
    const query = new URLSearchParams();
    if (params.scenario_id) query.append('scenario_id', params.scenario_id);
    if (params.scoring_mode) query.append('scoring_mode', params.scoring_mode);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return request(`/api/climate-risk/wards/${encodeURIComponent(wardId)}${qs}`);
  },

  // 7. Urban Water Risk Engine
  async getWaterRiskWards(params = {}) {
    const query = new URLSearchParams();
    if (params.scenario_id) query.append('scenario_id', params.scenario_id);
    if (params.supply_lpcd !== undefined) query.append('supply_lpcd', params.supply_lpcd);
    if (params.reservoir_storage_pct !== undefined) query.append('reservoir_storage_pct', params.reservoir_storage_pct);
    if (params.rainfall_24h_mm !== undefined) query.append('rainfall_24h_mm', params.rainfall_24h_mm);
    if (params.peak_hourly_rainfall_mm !== undefined) query.append('peak_hourly_rainfall_mm', params.peak_hourly_rainfall_mm);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return request(`/api/water/wards${qs}`);
  },

  async getCitywideWaterRisk(params = {}) {
    const query = new URLSearchParams();
    if (params.scenario_id) query.append('scenario_id', params.scenario_id);
    if (params.supply_lpcd !== undefined) query.append('supply_lpcd', params.supply_lpcd);
    if (params.reservoir_storage_pct !== undefined) query.append('reservoir_storage_pct', params.reservoir_storage_pct);
    if (params.rainfall_24h_mm !== undefined) query.append('rainfall_24h_mm', params.rainfall_24h_mm);
    if (params.peak_hourly_rainfall_mm !== undefined) query.append('peak_hourly_rainfall_mm', params.peak_hourly_rainfall_mm);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return request(`/api/water/risk${qs}`);
  },

  async getWaterScenarios() {
    return request('/api/water/scenarios');
  },

  async getSingleWardWaterRisk(wardId, params = {}) {
    const query = new URLSearchParams();
    if (params.scenario_id) query.append('scenario_id', params.scenario_id);
    if (params.supply_lpcd !== undefined) query.append('supply_lpcd', params.supply_lpcd);
    if (params.reservoir_storage_pct !== undefined) query.append('reservoir_storage_pct', params.reservoir_storage_pct);
    if (params.rainfall_24h_mm !== undefined) query.append('rainfall_24h_mm', params.rainfall_24h_mm);
    if (params.peak_hourly_rainfall_mm !== undefined) query.append('peak_hourly_rainfall_mm', params.peak_hourly_rainfall_mm);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return request(`/api/water/wards/${encodeURIComponent(wardId)}${qs}`);
  },

  async calculateCustomWaterRisk(payload) {
    return request('/api/water/calculate', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // 7B. CGWB Groundwater In-situ Monitoring
  async getGroundwaterSummary() {
    return request('/api/water/groundwater/summary');
  },

  async getGroundwaterStations(district = 'Ahmedabad') {
    const qs = district ? `?district=${encodeURIComponent(district)}` : '';
    return request(`/api/water/groundwater/stations${qs}`);
  },

  async getGroundwaterObservations(params = {}) {
    const query = new URLSearchParams();
    if (params.station_id) query.append('station_id', params.station_id);
    if (params.district) query.append('district', params.district);
    if (params.limit !== undefined) query.append('limit', params.limit);
    if (params.offset !== undefined) query.append('offset', params.offset);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return request(`/api/water/groundwater/observations${qs}`);
  },

  async getGroundwaterTrends(params = {}) {
    const query = new URLSearchParams();
    if (params.district) query.append('district', params.district);
    if (params.station_name) query.append('station_name', params.station_name);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return request(`/api/water/groundwater/trends${qs}`);
  },

  // 7C. CWC Reservoir Storage Bulletins
  async getReservoirs(maxAgeDays = 30) {
    return request(`/api/water/reservoirs?max_age_days=${maxAgeDays}`);
  },

  async getReservoirObservations(params = {}) {
    const query = new URLSearchParams();
    if (params.reservoir_name) query.append('reservoir_name', params.reservoir_name);
    if (params.limit !== undefined) query.append('limit', params.limit);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return request(`/api/water/reservoirs/observations${qs}`);
  },

  async getReservoirsSummary() {
    return request('/api/water/reservoirs/summary');
  },

  // 8. Action Centre Unified Dashboard
  async getActionCentreDashboard(scenarioId = null, forceRefresh = false) {
    const query = new URLSearchParams();
    if (scenarioId) query.append('scenario_id', scenarioId);
    if (forceRefresh) query.append('force_refresh', 'true');
    const qs = query.toString() ? `?${query.toString()}` : '';
    return request(`/api/action-centre/dashboard${qs}`);
  },

  // 9. Prioritized Actions Queue
  async getPrioritizedActions(params = {}) {
    const query = new URLSearchParams();
    if (params.ward_id) query.append('ward_id', params.ward_id);
    if (params.action_type) query.append('action_type', params.action_type);
    if (params.status) query.append('status', params.status);
    if (params.limit) query.append('limit', params.limit);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return request(`/api/action-centre/actions/prioritized${qs}`);
  },

  // 9b. Retrieve Single Action Details
  async getActionById(actionId) {
    return request(`/api/action-centre/actions/${encodeURIComponent(actionId)}`);
  },

  // 9c. Verify Action Evidence
  async verifyActionEvidence(actionId, payload = {}) {
    return request(`/api/action-centre/actions/${encodeURIComponent(actionId)}/verify`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // 9d. Get Action Verification Report
  async getActionVerification(actionId) {
    return request(`/api/action-centre/actions/${encodeURIComponent(actionId)}/verification`);
  },

  // 10. Update Action Status (proposed -> approved -> in_progress -> completed / cancelled / blocked / rejected / changes_requested)
  async updateActionStatus(actionId, { new_status, changed_by = 'Municipal Incident Commander', notes = null, reason = null }) {
    return request(`/api/action-centre/actions/${encodeURIComponent(actionId)}/status`, {
      method: 'PUT',
      body: JSON.stringify({
        new_status,
        changed_by,
        notes: notes || reason,
        reason,
      }),
    });
  },

  // 10b. Execute Decision Workflow (approve, reject, hold/block, unblock, request_changes, deploy, complete)
  async executeActionDecision(actionId, { decision, changed_by = 'Municipal Incident Commander', notes = null, reason = null, target_status = null }) {
    return request(`/api/action-centre/actions/${encodeURIComponent(actionId)}/decision`, {
      method: 'POST',
      body: JSON.stringify({
        decision,
        changed_by,
        notes: notes || reason,
        reason,
        target_status,
      }),
    });
  },

  // 10c. Authenticated Operational Quick Dispatch with Duplicate Prevention
  async quickDispatch(payload) {
    return request('/api/action-centre/dispatch/quick', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // 10d. Action-Specific Audit Trail
  async getActionAuditTrail(actionId, limit = 50) {
    return request(`/api/action-centre/actions/${encodeURIComponent(actionId)}/audit-trail?limit=${limit}`);
  },

  // 10e. Global Action Centre Audit Trail
  async getGlobalActionAuditTrail(limit = 100) {
    return request(`/api/action-centre/audit-trail?limit=${limit}`);
  },

  // 11. Create Manual Operational Action
  async createManualAction(payload) {
    return request('/api/action-centre/create', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // 12. Generate Rule-Based Recommendations into Action Store
  async generateRuleRecommendations(payload = {}) {
    return request('/api/action-centre/recommendations', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // 13. Resource Optimization (Knapsack Solver)
  async runOptimization(payload) {
    return request('/api/optimize', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // 14. Combined Climate Optimization
  async runClimateOptimization(payload) {
    return request('/api/optimize/climate', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // 15. Multi-Hazard Interventions Catalog
  async getInterventionsCatalog() {
    return request('/api/interventions/catalog');
  },

  // 16. What-If Simulation
  async simulateWhatIf(payload) {
    return request('/api/interventions/simulate', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // 17. Impact Verification Summary
  async getImpactSummary(params = {}) {
    const query = new URLSearchParams();
    if (params.ward_id) query.append('ward_id', params.ward_id);
    if (params.intervention_type) query.append('intervention_type', params.intervention_type);
    if (params.hazard_category) query.append('hazard_category', params.hazard_category);
    if (params.include_synthetic !== undefined) query.append('include_synthetic', params.include_synthetic);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return request(`/api/impact/summary${qs}`);
  },

  // 18. Ward Impact Assessments
  async getWardImpactAssessments(wardId, params = {}) {
    const query = new URLSearchParams();
    if (params.include_synthetic !== undefined) query.append('include_synthetic', params.include_synthetic);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return request(`/api/impact/wards/${encodeURIComponent(wardId)}${qs}`);
  },

  // 19. Submit Empirical Impact Assessment
  async submitImpactAssessment(payload) {
    return request('/api/impact/assessments', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // 20. Satellite & Reanalysis Data Sources (ERA5-Land, ECOSTRESS, Fusion)
  async getERA5LandData() {
    return request('/api/data-sources/era5');
  },

  async getECOSTRESSData(productType = 'LST') {
    return request(`/api/data-sources/ecostress?product_type=${productType}`);
  },

  async getDataFusion() {
    return request('/api/data-sources/fusion');
  },

  // 21. Water Scarcity / Drought Advisory
  async issueWaterAdvisory(payload) {
    return request('/api/water/advisory', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  // 22. Authentic Multi-Component System Health Diagnostics
  async getSystemHealth() {
    return request('/api/system/health');
  },
};

export { ApiError, API_BASE_URL };
