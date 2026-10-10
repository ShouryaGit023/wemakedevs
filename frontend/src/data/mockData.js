// ClimateShield AMC - Authentic Municipal Data & Telemetry Fixtures
// Matching Stitch MCP Screens & Phase 0 Ahmedabad Specifications

export const MUNICIPAL_OFFICERS = [
  {
    name: "K. Patel, IAS",
    designation: "Dy. Municipal Commissioner",
    avatar: "https://lh3.googleusercontent.com/aida-public/AB6AXuBNSZtOPVBZhNs87yk1sFMPf1bykJIFe_O78Bk9tMGIdvMk2W1SJrLS1d9Z81cwuH7u7cBdlA_XCH30DuBKwJqPQsPeX5eyoLSFETg9fdIFriHLCtWQFyQ7X3w_-XKflc2aGm0Q-zJu3Ac3QeFvvxfPmDSLOU4UDxwulHzWfHyBlrzrhGoOQcyWC8csa5eOYfMnbSuVNxLNxPbB6T7fBcFHYn76sEPv-77OYcgwT_3Ehm0oTtlstwI",
    role: "Health & Resilience Oversight"
  },
  {
    name: "M. Thennarasan, IAS",
    designation: "Municipal Commissioner",
    avatar: "https://lh3.googleusercontent.com/aida-public/AB6AXuDV0Ij_HlBlW_YIxnW8wm_RZI_ejPIhAaBqqCiAVP-Gsh8QW-PHOA9h6PidWbKvvK4P_JBzN6exrx8dCywKJkZ_eHEd1NgUggPZvH1FwITN5D89keUeAQwjyc0UBxIgP-6UbTykn6a7unrUy-WqPxZTQIKy2YEsMd1nn4C0q-J5ECeRmJXyG-yjq-p7hnMNY5Yxn8tfoR5VLtsYAev7eWZi_KESe4_TRazQn634nZ8QPV7vdEv_5Tw",
    role: "Central Operations Command"
  }
];

export const AHMEDABAD_ZONES = [
  "All 7 Zones",
  "East Zone",
  "South Zone",
  "North Zone",
  "Central Zone",
  "West Zone",
  "New West Zone",
  "South West Zone"
];

export const TOP_RISK_WARDS = [
  {
    rank: 1,
    ward_id: "AMC-E-04",
    name: "Gomtipur",
    zone: "East Zone",
    composite_score: 91,
    status: "Critical",
    primary_factor: "Severe Heat Island + Slum Density",
    detail: "LST: 47.4°C max • Slum density index 0.89",
    population: 172400,
    wbgt: 32.4,
    dry_bulb: 44.8,
    water_deficit: "-19%",
    cool_roof_deficit: "46%",
    cooling_centers: 2
  },
  {
    rank: 2,
    ward_id: "AMC-S-14",
    name: "Danilimda",
    zone: "South Zone",
    composite_score: 88,
    status: "Critical",
    primary_factor: "Industrial Heat + Drainage Overflow",
    detail: "Water Deficit: 24% • Canal surcharge risk",
    population: 184200,
    wbgt: 31.8,
    dry_bulb: 44.2,
    water_deficit: "-24%",
    cool_roof_deficit: "38%",
    cooling_centers: 3
  },
  {
    rank: 3,
    ward_id: "AMC-E-08",
    name: "Odhav",
    zone: "East Zone",
    composite_score: 85,
    status: "High",
    primary_factor: "Metal Roofing Heat + Water Stress",
    detail: "Kharicut Canal overflow risk • Industrial shed heat",
    population: 164000,
    wbgt: 31.2,
    dry_bulb: 43.9,
    water_deficit: "-16%",
    cool_roof_deficit: "52%",
    cooling_centers: 4
  },
  {
    rank: 4,
    ward_id: "AMC-N-06",
    name: "Bapunagar",
    zone: "North Zone",
    composite_score: 84,
    status: "High",
    primary_factor: "Extreme LST + Informal Settlement",
    detail: "Cool roof deficit: 42% • High infant vulnerability",
    population: 158900,
    wbgt: 31.0,
    dry_bulb: 43.6,
    water_deficit: "-14%",
    cool_roof_deficit: "42%",
    cooling_centers: 3
  },
  {
    rank: 5,
    ward_id: "AMC-S-09",
    name: "Vatva",
    zone: "South Zone",
    composite_score: 81,
    status: "High",
    primary_factor: "GIDC Chemical Cluster Heat Trap",
    detail: "Ambient night retention + Effluent water stress",
    population: 149200,
    wbgt: 30.8,
    dry_bulb: 43.4,
    water_deficit: "-21%",
    cool_roof_deficit: "35%",
    cooling_centers: 2
  }
];

export const EXECUTIVE_KPIS = {
  highRiskWards: {
    value: 14,
    total: 48,
    label: "High-Risk Wards",
    subtitle: "Critical vulnerability",
    delta: "+2 vs yday",
    isDanger: true,
    icon: "warning"
  },
  heatStress: {
    value: "Severe",
    detail: "(44.2°C)",
    label: "Heat Stress Index",
    subtitle: "Wet-bulb: 31.8°C",
    tag: "9 Red Alert",
    isDanger: true,
    icon: "local_fire_department"
  },
  waterlogging: {
    value: 6,
    unit: "Hotspots",
    label: "Waterlogging Stress",
    subtitle: "East & South Zones",
    tag: "Elevated",
    isInfo: true,
    icon: "flood"
  },
  dualHazard: {
    value: 4,
    unit: "Compound Wards",
    label: "Dual-Hazard Compound",
    subtitle: "Gomtipur, Danilimda, Odhav, Vatva",
    tag: "High Priority",
    isWarning: true,
    icon: "sync_problem"
  },
  activeInterventions: {
    value: 29,
    unit: "Active Field Ops",
    label: "Active Interventions",
    subtitle: "Cool roofs, misting, bowsers",
    tag: "Normal Ops",
    isSuccess: true,
    icon: "engineering"
  }
};

export const ACTION_CENTRE_KPIS = {
  activeDeployments: {
    value: 29,
    statusText: "Ongoing",
    label: "Active Deployments",
    detail: "Across 14 high-risk wards",
    progress: 82
  },
  criticalBlockers: {
    value: 3,
    statusText: "Pending Resolution",
    label: "Critical Blockers",
    detail: "Danilimda & Gomtipur halts",
    progress: 60,
    isWarning: true
  },
  onTimeExecution: {
    value: "91.4%",
    statusText: "+2.1% w/w",
    label: "On-Time Execution",
    detail: "SLA Target ≥ 90.0%",
    progress: 91.4,
    isSuccess: true
  },
  teamsMobilized: {
    value: 18,
    statusText: "Wings Active",
    label: "Teams Mobilized",
    detail: "Health, Eng, Fire & Forestry",
    progress: 75
  },
  dailyTargetProgress: {
    value: "68%",
    statusText: "29/42 Ops Done",
    label: "Daily Target Progress",
    detail: "Shift window: 07:00 - 19:00 IST",
    progress: 68
  }
};

export const FIELD_OPERATIONS = [
  {
    id: "OP-2024-041",
    ward: "Gomtipur (AMC-E-04)",
    title: "Slum Cluster #4 Cool Roof Coating Deployment",
    type: "Cool Roof",
    team: "AMC Engineering Wing B",
    personnel: 8,
    status: "In Progress",
    progress: 72,
    target: "1,200 m²",
    eta: "16:30 IST",
    priority: "High"
  },
  {
    id: "OP-2024-039",
    ward: "Danilimda (AMC-S-14)",
    title: "Emergency Water Tanker & Hydration Point Setup",
    type: "Hydration",
    team: "Disaster Cell Taskforce 2",
    personnel: 6,
    status: "Blocked",
    progress: 35,
    target: "30,000 Liters",
    eta: "Pending Valve Clearance",
    priority: "Critical"
  },
  {
    id: "OP-2024-042",
    ward: "Odhav (AMC-E-08)",
    title: "AMTS Bus Terminal High-Pressure Micro-Misting",
    type: "Misting Pod",
    team: "AMC Urban Forest Division",
    personnel: 4,
    status: "In Progress",
    progress: 90,
    target: "2 Misting Pods",
    eta: "14:15 IST",
    priority: "Medium"
  },
  {
    id: "OP-2024-038",
    ward: "Bapunagar (AMC-N-06)",
    title: "ORS Distribution & Mobile Health Clinic Mobilization",
    type: "Medical Support",
    team: "Urban Health Centre (UHC) Squad 7",
    personnel: 5,
    status: "Completed",
    progress: 100,
    target: "800 Kits",
    eta: "Finished (11:45 IST)",
    priority: "High"
  },
  {
    id: "OP-2024-044",
    ward: "Vatva (AMC-S-09)",
    title: "Industrial Shaded Corridor & Temporary Awning Erection",
    type: "Shading Canopy",
    team: "Engineering Wing C",
    personnel: 7,
    status: "Scheduled",
    progress: 15,
    target: "450 meters",
    eta: "17:00 IST",
    priority: "Medium"
  }
];

export const IMPACT_KPIS = {
  totalVerified: {
    value: 42,
    label: "Total Verified",
    subLabel: "Interventions Audited",
    footerLeft: "Scope Coverage",
    footerRight: "18 of 48 Wards"
  },
  surfaceTempDrop: {
    value: "-6.8°C",
    label: "Mean Surface Temp",
    subLabel: "Avg Rooftop Drop",
    footerLeft: "12,400 m² Cool Roofs",
    footerRight: "Target: -5.0°C"
  },
  runoffMitigation: {
    value: "34.2%",
    label: "Runoff Mitigation",
    subLabel: "Waterlogging Absorbed",
    footerLeft: "Monsoon Telemetry",
    footerRight: "+11.4% vs Model"
  },
  evidenceConfidence: {
    value: "94.1%",
    label: "Evidence Confidence",
    subLabel: "Grade A Empirical",
    footerLeft: "Ground IoT + Landsat-9",
    footerRight: "TIRS Cross-Validated"
  },
  outcomeAudit: {
    value: "28",
    secondaryValue: "/ 11 / 3",
    label: "Outcome Audit",
    subLabel: "Classification Status",
    footerPill1: "28 Exceeded",
    footerPill2: "11 Met",
    footerPill3: "3 Under"
  }
};

export const DIURNAL_TEMPERATURE_PROFILE = [
  { hour: "02h", baseline: 31.0, coated: 28.0, baselinePct: 38, coatedPct: 32 },
  { hour: "06h", baseline: 29.0, coated: 27.0, baselinePct: 34, coatedPct: 30 },
  { hour: "10h", baseline: 44.0, coated: 37.0, baselinePct: 65, coatedPct: 52 },
  { hour: "13h", baseline: 54.2, coated: 43.1, delta: "-11.1°", baselinePct: 98, coatedPct: 72, isPeak: true },
  { hour: "15h", baseline: 51.0, coated: 41.0, baselinePct: 88, coatedPct: 68 },
  { hour: "18h", baseline: 42.0, coated: 35.0, baselinePct: 60, coatedPct: 48 },
  { hour: "22h", baseline: 36.0, coated: 31.0, baselinePct: 48, coatedPct: 38 }
];

export const IMPACT_AUDIT_CASES = [
  {
    id: "AUDIT-2024-001",
    wardId: "AMC-E-04",
    wardName: "Gomtipur Ward",
    title: "High-Albedo Cool Roof Coating Cluster (Slum Settlement #4)",
    hazard: "Extreme Heat Stress (LST)",
    confidenceTier: "Tier 1 Ground Measured (Confidence 98.4%)",
    measurementWindow: "Baseline: May 12–18, 2024 (pre-treatment) | Follow-up: June 2–8, 2024 (21-day post-coat)",
    isCurrentlyInspecting: true,
    metrics: [
      {
        title: "Rooftop Surface Temp",
        deltaPercent: "-20.5%",
        baseline: "54.2°C",
        followUp: "43.1°C",
        netDrop: "Δ -11.1°C Net Drop",
        sensor: "Thermistor Array",
        rail1: "79.5%",
        rail2: "20.5%"
      },
      {
        title: "Indoor Living Space",
        deltaPercent: "-12.9%",
        baseline: "41.8°C",
        followUp: "36.4°C",
        netDrop: "Δ -5.4°C Cooling",
        sensor: "In-situ Sensor (Grade A)",
        rail1: "87.1%",
        rail2: "12.9%"
      },
      {
        title: "Heat Discomfort Hrs/Day",
        deltaPercent: "-55.4%",
        baseline: "9.2 hrs",
        followUp: "4.1 hrs",
        netDrop: "-5.1 hrs/day Relief",
        sensor: "Threshold >38°C",
        rail1: "44.6%",
        rail2: "55.4%"
      }
    ],
    source: "AMC IoT Node #GT-09 + Landsat-9 TIRS Thermal Overpass",
    significance: "Statistically Significant (p < 0.001)"
  },
  {
    id: "AUDIT-2024-002",
    wardId: "AMC-S-14",
    wardName: "Danilimda Industrial Belt",
    title: "Decentralized Recharge Wells & Stormwater Infiltration Basins",
    hazard: "Urban Waterlogging & Groundwater",
    confidenceTier: "Tier 1 Hybrid SCADA",
    measurementWindow: "Baseline: Monsoon 2023 | Follow-up: July 2024 Post-Storm Event Telemetry",
    statusBadge: "Target Exceeded (+24%)",
    metrics: [
      {
        title: "Inundation Duration",
        deltaPercent: "-78%",
        baseline: "14.5 hrs",
        followUp: "3.2 hrs",
        netDrop: "Δ -11.3 hrs reduction",
        sensor: "Empirical Probes",
        rail1: "22%",
        rail2: "78%"
      },
      {
        title: "Recharge Volume / Event",
        deltaPercent: "+338%",
        baseline: "420 kL",
        followUp: "1,840 kL",
        netDrop: "+1,420 kL captured",
        sensor: "Flowmeters SCADA",
        rail1: "85%",
        rail2: "15%"
      },
      {
        title: "Water Salinity (TDS)",
        deltaPercent: "-17%",
        baseline: "1,420 ppm",
        followUp: "1,180 ppm",
        netDrop: "Aquifer Dilution",
        sensor: "Hydro-Lab Test",
        rail1: "83%",
        rail2: "17%"
      }
    ],
    source: "AMC SCADA Ultrasonic Sensors + Central Groundwater Board Wells (Tier 1 Hybrid)"
  },
  {
    id: "AUDIT-2024-003",
    wardId: "AMC-E-08",
    wardName: "Odhav Ward",
    title: "Urban Canopy & Micro-Misting Network (Bus Station Corridor)",
    hazard: "Ambient Heat & Commuter Exhaustion",
    confidenceTier: "Tier 2 Multi-Source",
    measurementWindow: "Baseline: April 2024 | Follow-up: May 2024 Peak Heatwave",
    statusBadge: "Positive Impact Verified",
    metrics: [
      {
        title: "Wet-Bulb Globe Temp (WBGT)",
        deltaPercent: "-3.8°C",
        baseline: "33.6°C (Extreme Danger)",
        followUp: "29.8°C (Moderate)",
        netDrop: "Crossed below extreme danger limit",
        sensor: "AMC Weather Pods",
        rail1: "78%",
        rail2: "22%"
      },
      {
        title: "Reported Heat Exhaustion Cases",
        deltaPercent: "-84.2%",
        baseline: "19 cases/wk",
        followUp: "3 cases/wk",
        netDrop: "UHC Ward Clinic Registry",
        sensor: "N=350 Surveyed",
        rail1: "15.8%",
        rail2: "84.2%"
      }
    ],
    source: "AMC Microclimate Pods #OD-03 & #OD-04 correlated with Urban Health Centre emergency logs"
  }
];
