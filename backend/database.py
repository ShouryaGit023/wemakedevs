"""
ClimateShield - Persistent Baseline Database Engine (SQLite)
Provides persistent storage for Ward profiles, Interventions catalog,
Municipal outcome tracking (mortality, hospital admissions, 108 calls),
and Optimization audit history.
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "climateshield_baseline.db")


def get_db_connection() -> sqlite3.Connection:
    """Returns a connection to the SQLite baseline database with row dict factory."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initializes tables in the baseline database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Wards Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS wards (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        slum_density REAL NOT NULL,
        outdoor_labor_ratio REAL NOT NULL,
        elderly_ratio REAL NOT NULL,
        baseline_heat_risk REAL NOT NULL,
        population INTEGER DEFAULT 100000,
        area_sq_km REAL DEFAULT 5.0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Interventions Catalog
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS interventions (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        cost_inr REAL NOT NULL,
        crew_req INTEGER NOT NULL,
        water_req_l REAL NOT NULL,
        base_risk_reduction REAL NOT NULL,
        max_per_ward INTEGER NOT NULL,
        vulnerable_impact_json TEXT NOT NULL
    );
    """)

    # 3. Ground-truth Municipal Outcome Records (Data-Sharing Agreements)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS outcome_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_date TEXT NOT NULL,
        ward_id TEXT NOT NULL,
        hospital_heat_admissions INTEGER DEFAULT 0,
        mortality_count INTEGER DEFAULT 0,
        emergency_108_calls INTEGER DEFAULT 0,
        water_scarcity_complaints INTEGER DEFAULT 0,
        reported_by TEXT DEFAULT 'AMC_HEALTH_SURVEILLANCE',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (ward_id) REFERENCES wards (id)
    );
    """)

    # 4. Optimization Audit Runs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS optimization_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        budget_inr REAL NOT NULL,
        crew_members INTEGER NOT NULL,
        water_cap_l REAL NOT NULL,
        equity_slider REAL NOT NULL,
        total_cost_inr REAL NOT NULL,
        total_risk_reduction REAL NOT NULL,
        allocation_summary_json TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()


def seed_baseline_data() -> None:
    """Seeds baseline wards, interventions catalog, and sample historical outcomes."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if wards already seeded
    cursor.execute("SELECT COUNT(*) as count FROM wards;")
    if cursor.fetchone()["count"] == 0:
        # Seed Ahmedabad 10 Priority Pilot Wards
        ahmedabad_wards = [
            ("W1", "Danilimda", 0.85, 0.75, 0.20, 0.92, 125000, 6.2),
            ("W2", "Behrampura", 0.80, 0.70, 0.18, 0.88, 110000, 5.4),
            ("W3", "Asarwa", 0.65, 0.60, 0.25, 0.78, 95000, 4.8),
            ("W4", "Bapunagar", 0.75, 0.65, 0.22, 0.84, 130000, 5.9),
            ("W5", "Khadia (Old City)", 0.40, 0.45, 0.35, 0.72, 85000, 3.2),
            ("W6", "Amraiwadi", 0.70, 0.68, 0.19, 0.81, 105000, 5.1),
            ("W7", "Vatva", 0.78, 0.72, 0.17, 0.86, 140000, 7.8),
            ("W8", "Sabarmati", 0.35, 0.35, 0.28, 0.55, 90000, 6.5),
            ("W9", "Maninagar", 0.30, 0.30, 0.30, 0.50, 115000, 5.0),
            ("W10", "Naroda", 0.60, 0.58, 0.21, 0.70, 100000, 6.8)
        ]
        cursor.executemany("""
        INSERT INTO wards (id, name, slum_density, outdoor_labor_ratio, elderly_ratio, baseline_heat_risk, population, area_sq_km)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, ahmedabad_wards)

    # Check if interventions catalog already seeded
    cursor.execute("SELECT COUNT(*) as count FROM interventions;")
    if cursor.fetchone()["count"] == 0:
        interventions = [
            ("cooling_center", "Cooling Center Shelter", 50000, 4, 500, 85.0, 2, json.dumps({"slum_dwellers": 40, "outdoor_laborers": 20, "elderly_infants": 40})),
            ("hydration_kiosk", "Emergency Hydration Kiosk", 15000, 2, 1200, 45.0, 4, json.dumps({"slum_dwellers": 30, "outdoor_laborers": 60, "elderly_infants": 10})),
            ("shade_canopy", "Pop-up Bus Stop Shade Canopy", 25000, 3, 0, 35.0, 3, json.dumps({"slum_dwellers": 20, "outdoor_laborers": 70, "elderly_infants": 10})),
            ("cool_roof_coating", "Slum Cool Roof Painting", 35000, 5, 100, 65.0, 3, json.dumps({"slum_dwellers": 80, "outdoor_laborers": 0, "elderly_infants": 20})),
            ("water_tanker_dispatch", "Mobile Water Tanker Dispatch", 10000, 2, 5000, 50.0, 2, json.dumps({"slum_dwellers": 50, "outdoor_laborers": 30, "elderly_infants": 20}))
        ]
        cursor.executemany("""
        INSERT INTO interventions (id, name, cost_inr, crew_req, water_req_l, base_risk_reduction, max_per_ward, vulnerable_impact_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, interventions)

    # Check if sample historical outcome records seeded
    cursor.execute("SELECT COUNT(*) as count FROM outcome_records;")
    if cursor.fetchone()["count"] == 0:
        sample_outcomes = [
            ("2026-05-15", "W1", 14, 2, 8, 22, "AMC_HEALTH_SURVEILLANCE"),
            ("2026-05-15", "W2", 12, 1, 6, 18, "AMC_HEALTH_SURVEILLANCE"),
            ("2026-05-15", "W4", 10, 1, 5, 15, "AMC_HEALTH_SURVEILLANCE"),
            ("2026-05-15", "W7", 11, 2, 7, 20, "AMC_HEALTH_SURVEILLANCE"),
            ("2026-05-15", "W9", 2, 0, 1, 3, "AMC_HEALTH_SURVEILLANCE")
        ]
        cursor.executemany("""
        INSERT INTO outcome_records (record_date, ward_id, hospital_heat_admissions, mortality_count, emergency_108_calls, water_scarcity_complaints, reported_by)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """, sample_outcomes)

    conn.commit()
    conn.close()


def get_all_wards() -> List[Dict[str, Any]]:
    """Returns all ward records as dictionaries."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM wards ORDER BY baseline_heat_risk DESC;")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_all_interventions() -> List[Dict[str, Any]]:
    """Returns the interventions catalog."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM interventions;")
    rows = []
    for r in cursor.fetchall():
        item = dict(r)
        item["vulnerable_impact"] = json.loads(item["vulnerable_impact_json"])
        del item["vulnerable_impact_json"]
        rows.append(item)
    conn.close()
    return rows


def insert_outcome_record(
    record_date: str,
    ward_id: str,
    hospital_admissions: int,
    mortality_count: int,
    emergency_108_calls: int,
    water_complaints: int,
    reported_by: str = "AMC_HEALTH_SURVEILLANCE"
) -> int:
    """Inserts a new ground-truth municipal outcome record."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO outcome_records (record_date, ward_id, hospital_heat_admissions, mortality_count, emergency_108_calls, water_scarcity_complaints, reported_by)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, (record_date, ward_id, hospital_admissions, mortality_count, emergency_108_calls, water_complaints, reported_by))
    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return record_id


def get_outcome_records(limit: int = 50) -> List[Dict[str, Any]]:
    """Returns recent municipal outcome records."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT o.*, w.name as ward_name 
    FROM outcome_records o
    JOIN wards w ON o.ward_id = w.id
    ORDER BY o.record_date DESC, o.id DESC
    LIMIT ?;
    """, (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


# Auto-initialize and seed when module loaded
init_db()
seed_baseline_data()
