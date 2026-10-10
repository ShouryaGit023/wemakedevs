import React, { useState, useEffect, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import TopAppBar from './components/TopAppBar';
import OverviewPage from './pages/OverviewPage';
import ActionCentrePage from './pages/ActionCentrePage';
import ImpactVerificationPage from './pages/ImpactVerificationPage';
import WardExplorerPage from './pages/WardExplorerPage';
import InterventionPlannerPage from './pages/InterventionPlannerPage';
import SystemStatusPage from './pages/SystemStatusPage';
import LearningLoopDashboard from './components/LearningLoopDashboard';
import IssueAdvisoryModal from './components/IssueAdvisoryModal';
import WardInspectionModal from './components/WardInspectionModal';
import { TOP_RISK_WARDS } from './data/mockData';
import { ClimateShieldAPI } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isAdvisoryModalOpen, setIsAdvisoryModalOpen] = useState(false);
  const [inspectedWard, setInspectedWard] = useState(TOP_RISK_WARDS[0]);
  const [isInspectionModalOpen, setIsInspectionModalOpen] = useState(false);
  const [selectedZone, setSelectedZone] = useState('All 7 Zones');
  const [liveWeather, setLiveWeather] = useState(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const fetchGlobalTelemetry = useCallback(async () => {
    try {
      const res = await ClimateShieldAPI.getWeatherWBGT();
      if (res && res.current_heat_status) {
        setLiveWeather(res.current_heat_status);
      }
    } catch (err) {
      console.warn('Could not load global weather telemetry:', err);
    }
  }, []);

  useEffect(() => {
    fetchGlobalTelemetry();
  }, [fetchGlobalTelemetry, refreshTrigger]);

  const handleInspectWard = (ward) => {
    setInspectedWard(ward);
    setIsInspectionModalOpen(true);
  };

  const handleRefreshAll = () => {
    setRefreshTrigger(prev => prev + 1);
  };

  return (
    <div className="h-full flex overflow-hidden text-on-surface bg-[#F4F6F4] font-sans antialiased">
      {/* Sidebar Navigation */}
      <Sidebar 
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        onOpenAdvisory={() => setIsAdvisoryModalOpen(true)}
        isMobileOpen={isMobileMenuOpen}
        onCloseMobile={() => setIsMobileMenuOpen(false)}
      />

      {/* Main Viewport Wrapper (TopBar + Dashboard Canvas) */}
      <div className="flex-1 flex flex-col h-full min-w-0 overflow-hidden">
        {/* Top App Bar */}
        <TopAppBar 
          onOpenMobileMenu={() => setIsMobileMenuOpen(true)}
          selectedZone={selectedZone}
          onSelectZone={setSelectedZone}
          onRefreshData={handleRefreshAll}
          liveWeather={liveWeather}
          activeAlertsCount={3}
        />

        {/* Scrollable Main Content Canvas */}
        <main className="flex-1 overflow-y-auto px-4 lg:px-margin-desktop py-space-md">
          {activeTab === 'overview' && (
            <OverviewPage 
              key={`overview-${refreshTrigger}`}
              selectedZone={selectedZone}
              onOpenAdvisory={() => setIsAdvisoryModalOpen(true)}
              onInspectWard={handleInspectWard}
            />
          )}

          {activeTab === 'action-centre' && (
            <ActionCentrePage 
              key={`action-centre-${refreshTrigger}`}
              onOpenDeployModal={() => setIsAdvisoryModalOpen(true)}
            />
          )}

          {activeTab === 'verification' && (
            <ImpactVerificationPage 
              key={`verification-${refreshTrigger}`}
            />
          )}

          {activeTab === 'learning-loop' && (
            <div className="learning-loop-container p-4">
              <LearningLoopDashboard 
                key={`learning-loop-${refreshTrigger}`}
              />
            </div>
          )}

          {activeTab === 'ward-explorer' && (
            <WardExplorerPage 
              key={`ward-explorer-${refreshTrigger}`}
              selectedZone={selectedZone}
              onInspectWard={handleInspectWard} 
            />
          )}

          {activeTab === 'planner' && (
            <InterventionPlannerPage 
              key={`planner-${refreshTrigger}`}
            />
          )}

          {activeTab === 'system-status' && (
            <SystemStatusPage 
              key={`status-${refreshTrigger}`}
            />
          )}
        </main>
      </div>

      {/* Interactive Modals */}
      <IssueAdvisoryModal 
        isOpen={isAdvisoryModalOpen}
        onClose={() => setIsAdvisoryModalOpen(false)}
      />

      <WardInspectionModal 
        ward={inspectedWard}
        isOpen={isInspectionModalOpen}
        onClose={() => setIsInspectionModalOpen(false)}
      />
    </div>
  );
}
