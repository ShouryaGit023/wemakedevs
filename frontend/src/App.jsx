import React, { useState } from 'react';
import { 
  Shield, 
  Flame, 
  Droplet, 
  Sliders, 
  RotateCw, 
  MapPin, 
  Building, 
  ExternalLink,
  BookOpen
} from 'lucide-react';
import LearningLoopDashboard from './components/LearningLoopDashboard';

export default function App() {
  const [navSection, setNavSection] = useState('learning-loop'); // 'learning-loop', 'overview'

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Top Navbar */}
      <header style={{ 
        background: 'rgba(10, 14, 23, 0.85)', 
        backdropFilter: 'blur(16px)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
        position: 'sticky',
        top: 0,
        zIndex: 50
      }}>
        <div style={{ 
          maxWidth: '1280px', 
          margin: '0 auto', 
          padding: '12px 16px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px'
        }}>
          {/* Logo Brand */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ 
              background: 'linear-gradient(135deg, #0284c7, #0f172a)', 
              border: '1px solid rgba(56, 189, 248, 0.5)',
              padding: '6px 8px', 
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              boxShadow: '0 0 12px rgba(56, 189, 248, 0.3)'
            }}>
              <Shield size={20} color="#38bdf8" />
            </div>
            <div>
              <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#f8fafc', letterSpacing: '-0.02em', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span>ClimateShield</span>
                <span style={{ fontSize: '0.65rem', background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', padding: '2px 6px', borderRadius: '4px', border: '1px solid rgba(56, 189, 248, 0.3)' }}>
                  Ahmedabad 2026
                </span>
              </div>
              <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
                Multi-Hazard Heat &amp; Water Decision Support System
              </div>
            </div>
          </div>

          {/* Navigation Items */}
          <nav style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
            <button
              onClick={() => setNavSection('learning-loop')}
              style={{
                background: navSection === 'learning-loop' ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
                color: navSection === 'learning-loop' ? '#38bdf8' : '#94a3b8',
                border: navSection === 'learning-loop' ? '1px solid rgba(56, 189, 248, 0.35)' : '1px solid transparent',
                borderRadius: '8px',
                padding: '6px 12px',
                fontSize: '0.82rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                transition: 'all 0.2s ease'
              }}
            >
              <RotateCw size={14} /> Learning Loop &amp; Governance
            </button>

            <button
              onClick={() => setNavSection('overview')}
              style={{
                background: navSection === 'overview' ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
                color: navSection === 'overview' ? '#38bdf8' : '#94a3b8',
                border: navSection === 'overview' ? '1px solid rgba(56, 189, 248, 0.35)' : '1px solid transparent',
                borderRadius: '8px',
                padding: '6px 12px',
                fontSize: '0.82rem',
                fontWeight: 500,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                transition: 'all 0.2s ease'
              }}
            >
              <Building size={14} /> System Architecture &amp; APIs
            </button>
          </nav>
        </div>
      </header>

      {/* Main Container */}
      <main style={{ flex: 1 }}>
        {navSection === 'learning-loop' && (
          <LearningLoopDashboard />
        )}

        {navSection === 'overview' && (
          <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '36px 16px' }}>
            <div className="glass-panel" style={{ padding: '32px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
                <div style={{ background: 'rgba(6, 182, 212, 0.15)', color: '#06b6d4', padding: '10px', borderRadius: '10px' }}>
                  <Shield size={26} />
                </div>
                <div>
                  <h2 style={{ fontSize: '1.4rem', color: '#f8fafc' }}>
                    ClimateShield Ahmedabad Decision Engine
                  </h2>
                  <p style={{ fontSize: '0.86rem', color: '#94a3b8' }}>
                    Closed-loop municipal framework combining physics-based thermal forecasts, multi-constraint integer programming, and empirical learning
                  </p>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px', margin: '24px 0' }}>
                <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#f43f5e', marginBottom: '8px' }}>
                    <Flame size={18} />
                    <strong style={{ fontSize: '0.95rem' }}>Heat Engine (WBGT)</strong>
                  </div>
                  <p style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>
                    Open-Meteo hourly meteorological data converted to Stull (2011) Natural Wet-Bulb &amp; Outdoor WBGT across 48 Ahmedabad wards.
                  </p>
                  <code style={{ display: 'block', marginTop: '8px', fontSize: '0.74rem', color: '#38bdf8' }}>GET /api/weather/wbgt</code>
                </div>

                <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#06b6d4', marginBottom: '8px' }}>
                    <Droplet size={18} />
                    <strong style={{ fontSize: '0.95rem' }}>Water &amp; Flood Engine</strong>
                  </div>
                  <p style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>
                    Chronic surcharge point monitoring for pluvial waterlogging and potable water delivery vs the 140 LPCD urban benchmark.
                  </p>
                  <code style={{ display: 'block', marginTop: '8px', fontSize: '0.74rem', color: '#38bdf8' }}>GET /api/water/wards</code>
                </div>

                <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#a78bfa', marginBottom: '8px' }}>
                    <Sliders size={18} />
                    <strong style={{ fontSize: '0.95rem' }}>Resource Optimizer</strong>
                  </div>
                  <p style={{ fontSize: '0.8rem', color: '#cbd5e1' }}>
                    Multi-constraint integer knapsack solver with Equity Slider weighting informal settlements (Danilimda, Behrampura).
                  </p>
                  <code style={{ display: 'block', marginTop: '8px', fontSize: '0.74rem', color: '#38bdf8' }}>POST /api/optimize</code>
                </div>
              </div>

              <div style={{ textAlign: 'center', marginTop: '24px' }}>
                <button 
                  onClick={() => setNavSection('learning-loop')}
                  className="btn btn-primary"
                  style={{ padding: '10px 24px', fontSize: '0.9rem' }}
                >
                  Open Learning Loop Dashboard <RotateCw size={14} />
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer style={{ 
        background: 'rgba(10, 14, 23, 0.95)', 
        borderTop: '1px solid rgba(255, 255, 255, 0.06)',
        padding: '16px 20px',
        textAlign: 'center',
        fontSize: '0.75rem',
        color: '#64748b'
      }}>
        ClimateShield Municipal Decision Support • Target City: Ahmedabad, Gujarat, India (23.0225° N, 72.5714° E) • Closed-Loop Learning &amp; Controlled Parameter Calibration
      </footer>
    </div>
  );
}
