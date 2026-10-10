import React from 'react';
import { ShieldCheck, Cpu, Calculator, AlertTriangle } from 'lucide-react';

export default function ProvenanceBadge({ provenance, showIcon = true, className = '' }) {
  const norm = (provenance || 'UNVERIFIED').toUpperCase();

  let badgeClass = 'badge-unverified';
  let label = 'Unverified Data';
  let Icon = AlertTriangle;
  let title = 'Raw or unverified data source. Not approved for model parameter updates.';

  if (norm === 'REAL') {
    badgeClass = 'badge-real';
    label = 'Verified Real';
    Icon = ShieldCheck;
    title = 'Empirical ground-truth municipal surveillance data (e.g. AMC hospitals, 108 calls). Safe for learning.';
  } else if (norm === 'SIMULATED') {
    badgeClass = 'badge-simulated';
    label = 'Simulated / Demo';
    Icon = Cpu;
    title = 'Synthetic or simulated scenario. Strictly blocked from modifying production model weights.';
  } else if (norm === 'ESTIMATED') {
    badgeClass = 'badge-estimated';
    label = 'Estimated Model';
    Icon = Calculator;
    title = 'Statistically estimated or model-forecasted baseline prior.';
  }

  return (
    <span 
      className={`badge ${badgeClass} ${className}`}
      title={title}
      style={{ cursor: 'help' }}
    >
      {showIcon && <Icon size={12} />}
      {label}
    </span>
  );
}
