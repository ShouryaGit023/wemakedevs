import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import TopAppBar from './components/TopAppBar';
import OverviewPage from './pages/OverviewPage';
import ActionCentrePage from './pages/ActionCentrePage';
import ImpactVerificationPage from './pages/ImpactVerificationPage';
import WardExplorerPage from './pages/WardExplorerPage';
import InterventionPlannerPage from './pages/InterventionPlannerPage';
import SystemStatusPage from './pages/SystemStatusPage';
import IssueAdvisoryModal from './components/IssueAdvisoryModal';
import WardInspectionModal from './components/WardInspectionModal';
import { TOP_RISK_WARDS } from './data/mockData';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isAdvisoryModalOpen, setIsAdvisoryModalOpen] = useState(false);
  const [inspectedWard, setInspectedWard] = useState(TOP_RISK_WARDS[0]);
  const [isInspectionModalOpen, setIsInspectionModalOpen] = useState(false);
  const [selectedZone, setSelectedZone] = useState('All 7 Zones');

  const handleInspectWard = (ward) => {
    setInspectedWard(ward);
    setIsInspectionModalOpen(true);
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
          onRefreshData={() => console.log('Refreshing telemetry...')}
        />

        {/* Scrollable Main Content Canvas */}
        <main className="flex-1 overflow-y-auto px-4 lg:px-margin-desktop py-space-md">
          {activeTab === 'overview' && (
            <OverviewPage 
              onOpenAdvisory={() => setIsAdvisoryModalOpen(true)}
              onInspectWard={handleInspectWard}
            />
          )}

          {activeTab === 'action-centre' && (
            <ActionCentrePage 
              onOpenDeployModal={() => setIsAdvisoryModalOpen(true)}
            />
          )}

          {activeTab === 'verification' && (
            <ImpactVerificationPage />
          )}

          {activeTab === 'ward-explorer' && (
            <WardExplorerPage onInspectWard={handleInspectWard} />
          )}

          {activeTab === 'planner' && (
            <InterventionPlannerPage />
          )}

          {activeTab === 'system-status' && (
            <SystemStatusPage />
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
