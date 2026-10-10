import React, { useState, useEffect, useCallback } from 'react';
import { 
  Shield, 
  TrendingUp, 
  ClipboardCheck, 
  CheckCircle2, 
  BarChart3, 
  History, 
  GitPullRequest, 
  GitCommit, 
  RefreshCw, 
  AlertCircle,
  Database,
  Cpu,
  Layers,
  Sparkles
} from 'lucide-react';
import { api } from '../api';
import ProvenanceBadge from './ProvenanceBadge';
import RiskTimeSeriesSection from './RiskTimeSeriesSection';
import InterventionHistorySection from './InterventionHistorySection';
import VerifiedOutcomesSection from './VerifiedOutcomesSection';
import PerformanceMetricsSection from './PerformanceMetricsSection';
import PerformanceTrendsSection from './PerformanceTrendsSection';
import ProposedUpdatesSection from './ProposedUpdatesSection';
import ModelVersionsSection from './ModelVersionsSection';
import ImpactVerificationModal from './ImpactVerificationModal';
import DemoDataHelper from './DemoDataHelper';

export default function LearningLoopDashboard() {
  const [activeTab, setActiveTab] = useState('timeseries'); // 'timeseries', 'actions', 'outcomes', 'metrics', 'trends', 'proposals', 'versions'
  
  // Data State
  const [predictions, setPredictions] = useState([]);
  const [actions, setActions] = useState([]);
  const [outcomes, setOutcomes] = useState([]);
  const [evaluations, setEvaluations] = useState([]);
  const [proposals, setProposals] = useState([]);
  const [versions, setVersions] = useState([]);
  const [activeParams, setActiveParams] = useState(null);
  const [wards, setWards] = useState([]);

  // UI State
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [backendStatus, setBackendStatus] = useState('CONNECTING');
  const [verifyingAction, setVerifyingAction] = useState(null);

  // Fetch all Learning Loop data
  const loadAllData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. Health check
      const health = await api.checkHealth();
      setBackendStatus(health.status === 'OPERATIONAL' ? 'ONLINE' : 'OFFLINE');

      // 2. Fetch parallel datasets
      const [
        predsRes,
        actionsRes,
        outcomesRes,
        evalsRes,
        propsRes,
        versRes,
        activeRes,
        wardsRes
      ] = await Promise.all([
        api.getPredictions({ limit: 150 }).catch(() => ({ predictions: [] })),
        api.getActions({ limit: 100 }).catch(() => ({ actions: [] })),
        api.getOutcomes({ limit: 100 }).catch(() => ({ outcomes: [] })),
        api.getEvaluations(20).catch(() => ({ evaluations: [] })),
        api.getProposals().catch(() => ({ proposals: [] })),
        api.getVersions().catch(() => ({ versions: [] })),
        api.getActiveParameters().catch(() => null),
        api.getWards().catch(() => ({ wards: [] }))
      ]);

      setPredictions(predsRes.predictions || []);
      setActions(actionsRes.actions || []);
      setOutcomes(outcomesRes.outcomes || []);
      setEvaluations(evalsRes.evaluations || []);
      setProposals(propsRes.proposals || []);
      setVersions(versRes.versions || []);
      setActiveParams(activeRes);
      setWards(wardsRes.wards || []);
    } catch (err) {
      setError(err.message);
      setBackendStatus('OFFLINE');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAllData();
  }, [loadAllData]);

  const latestEvaluation = evaluations[0] || null;
  const pendingProposalsCount = proposals.filter(p => p.status === 'PENDING_APPROVAL').length;
  const realOutcomesCount = outcomes.filter(o => o.provenance === 'REAL').length;

  return (
    <div style={{ maxWidth: '1280px', margin: '0 auto', padding: '24px 16px' }}>
      {/* Live Command Center Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '24px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '4px' }}>
            <div style={{ 
              background: 'linear-gradient(135deg, rgba(6, 182, 212, 0.2), rgba(59, 130, 246, 0.2))', 
              border: '1px solid rgba(56, 189, 248, 0.4)',
              padding: '10px', 
              borderRadius: '12px', 
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 15px rgba(6, 182, 212, 0.2)'
            }}>
              <Shield size={26} color="#38bdf8" />
            </div>
            <div>
              <h1 style={{ fontSize: '1.6rem', color: '#f8fafc', fontWeight: 700, letterSpacing: '-0.02em' }}>
                ClimateShield Learning Loop
              </h1>
              <div style={{ fontSize: '0.84rem', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span>Ahmedabad Municipal Corporation Closed-Loop Calibration &amp; Model Governance</span>
              </div>
            </div>
          </div>
        </div>

        {/* Status Indicators & Refresh */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '8px', 
            background: 'rgba(15, 23, 42, 0.8)', 
            padding: '6px 12px', 
            borderRadius: '9999px',
            border: '1px solid var(--border-subtle)',
            fontSize: '0.78rem'
          }}>
            <span 
              className="pulse-dot" 
              style={{ background: backendStatus === 'ONLINE' ? '#10b981' : '#f43f5e' }}
            />
            <span style={{ color: backendStatus === 'ONLINE' ? '#34d399' : '#fb7185', fontWeight: 600 }}>
              {backendStatus === 'ONLINE' ? 'FastAPI Connected' : 'Backend Offline'}
            </span>
          </div>

          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '6px', 
            background: 'rgba(15, 23, 42, 0.8)', 
            padding: '6px 12px', 
            borderRadius: '9999px',
            border: '1px solid var(--border-subtle)',
            fontSize: '0.78rem'
          }}>
            <span style={{ color: '#94a3b8' }}>Active Model:</span>
            <span style={{ color: '#38bdf8', fontWeight: 600, fontFamily: 'var(--font-mono)' }}>
              {activeParams?.version_id || 'v1.0.0'}
            </span>
          </div>

          <button 
            onClick={loadAllData} 
            disabled={loading}
            className="btn btn-secondary"
            style={{ padding: '6px 12px', fontSize: '0.8rem' }}
            title="Reload live database records"
          >
            <RefreshCw size={13} className={loading ? 'spin' : ''} />
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Demo Controls Bar */}
      <DemoDataHelper onDataChanged={loadAllData} />

      {/* Global Summary KPI Bar */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', 
        gap: '14px', 
        marginBottom: '24px' 
      }}>
        <div className="glass-panel" style={{ padding: '16px' }}>
          <div style={{ fontSize: '0.74rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Risk Predictions
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#f8fafc', marginTop: '2px', fontFamily: 'var(--font-mono)' }}>
            {predictions.length}
          </div>
          <div style={{ fontSize: '0.72rem', color: '#64748b', marginTop: '4px' }}>
            Historical forecasts stored
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '16px' }}>
          <div style={{ fontSize: '0.74rem', color: '#38bdf8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Dispatched Actions
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#38bdf8', marginTop: '2px', fontFamily: 'var(--font-mono)' }}>
            {actions.length}
          </div>
          <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '4px' }}>
            {actions.filter(a => a.execution_status === 'COMPLETED').length} verified completed
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '16px' }}>
          <div style={{ fontSize: '0.74rem', color: '#34d399', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Observed Outcomes
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#34d399', marginTop: '2px', fontFamily: 'var(--font-mono)' }}>
            {outcomes.length}
          </div>
          <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '4px' }}>
            {realOutcomesCount} verified real (Non-PII)
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '16px' }}>
          <div style={{ fontSize: '0.74rem', color: '#fbbf24', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Calibration Status
          </div>
          <div style={{ fontSize: '1.6rem', fontWeight: 700, color: pendingProposalsCount > 0 ? '#f59e0b' : '#34d399', marginTop: '2px', fontFamily: 'var(--font-mono)' }}>
            {pendingProposalsCount > 0 ? `${pendingProposalsCount} Staged` : 'Stable'}
          </div>
          <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginTop: '4px' }}>
            {pendingProposalsCount > 0 ? 'Pending municipal sign-off' : 'Parameters in consensus'}
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="tabs-container" style={{ marginBottom: '24px' }}>
        <button 
          onClick={() => setActiveTab('timeseries')}
          className={`tab-btn ${activeTab === 'timeseries' ? 'active' : ''}`}
        >
          <TrendingUp size={15} />
          Predicted vs. Observed Risk
        </button>

        <button 
          onClick={() => setActiveTab('actions')}
          className={`tab-btn ${activeTab === 'actions' ? 'active' : ''}`}
        >
          <ClipboardCheck size={15} />
          Intervention History ({actions.length})
        </button>

        <button 
          onClick={() => setActiveTab('outcomes')}
          className={`tab-btn ${activeTab === 'outcomes' ? 'active' : ''}`}
        >
          <CheckCircle2 size={15} />
          Verified Outcomes ({outcomes.length})
        </button>

        <button 
          onClick={() => setActiveTab('metrics')}
          className={`tab-btn ${activeTab === 'metrics' ? 'active' : ''}`}
        >
          <BarChart3 size={15} />
          Multi-Hazard Accuracy
        </button>

        <button 
          onClick={() => setActiveTab('trends')}
          className={`tab-btn ${activeTab === 'trends' ? 'active' : ''}`}
        >
          <History size={15} />
          Trends &amp; Data Gaps
        </button>

        <button 
          onClick={() => setActiveTab('proposals')}
          className={`tab-btn ${activeTab === 'proposals' ? 'active' : ''}`}
        >
          <GitPullRequest size={15} />
          Proposed Updates
          {pendingProposalsCount > 0 && (
            <span style={{ 
              background: '#f59e0b', 
              color: '#0f172a', 
              fontSize: '0.65rem', 
              fontWeight: 700, 
              padding: '1px 6px', 
              borderRadius: '9999px',
              marginLeft: '4px' 
            }}>
              {pendingProposalsCount}
            </span>
          )}
        </button>

        <button 
          onClick={() => setActiveTab('versions')}
          className={`tab-btn ${activeTab === 'versions' ? 'active' : ''}`}
        >
          <GitCommit size={15} />
          Model Versions ({versions.length})
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div style={{ 
          padding: '14px 18px', 
          background: 'rgba(244, 63, 94, 0.15)', 
          border: '1px solid rgba(244, 63, 94, 0.4)', 
          borderRadius: '10px', 
          color: '#fb7185', 
          fontSize: '0.85rem', 
          marginBottom: '24px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px'
        }}>
          <AlertCircle size={20} />
          <div>
            <strong>Backend Connection Notice:</strong> {error}
          </div>
        </div>
      )}

      {/* Active Tab View */}
      {activeTab === 'timeseries' && (
        <RiskTimeSeriesSection 
          predictions={predictions}
          outcomes={outcomes}
          wards={wards}
        />
      )}

      {activeTab === 'actions' && (
        <InterventionHistorySection 
          actions={actions}
          onActionUpdated={loadAllData}
          onOpenVerifyModal={(act) => setVerifyingAction(act)}
        />
      )}

      {activeTab === 'outcomes' && (
        <VerifiedOutcomesSection 
          outcomes={outcomes}
          wards={wards}
          onOutcomeRecorded={loadAllData}
        />
      )}

      {activeTab === 'metrics' && (
        <PerformanceMetricsSection 
          latestEvaluation={latestEvaluation}
          onEvaluationTriggered={loadAllData}
        />
      )}

      {activeTab === 'trends' && (
        <PerformanceTrendsSection 
          evaluations={evaluations}
          predictions={predictions}
          outcomes={outcomes}
          wards={wards}
        />
      )}

      {activeTab === 'proposals' && (
        <ProposedUpdatesSection 
          proposals={proposals}
          onProposalUpdated={loadAllData}
        />
      )}

      {activeTab === 'versions' && (
        <ModelVersionsSection 
          versions={versions}
          activeVersion={activeParams}
          onVersionRollback={loadAllData}
        />
      )}

      {/* Impact Verification Modal */}
      {verifyingAction && (
        <ImpactVerificationModal 
          action={verifyingAction}
          wards={wards}
          onClose={() => setVerifyingAction(null)}
        />
      )}
    </div>
  );
}
