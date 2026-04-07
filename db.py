"""
db.py — SQLite persistence layer for Sentinel.

Tables:
  reports   — one row per CLI run (metadata + precomputed summary stats)
  asteroids — one row per asteroid, linked to a report, includes Claude assessment
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "sentinel.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create tables if they do not already exist."""
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS reports (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                start_date      TEXT    NOT NULL,
                end_date        TEXT    NOT NULL,
                max_distance_km REAL    NOT NULL,
                model           TEXT    NOT NULL,
                created_at      TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS asteroids (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id        INTEGER NOT NULL REFERENCES reports(id),
                nasa_id          TEXT    NOT NULL,
                name             TEXT    NOT NULL,
                hazardous        INTEGER NOT NULL,
                diameter_min_m   REAL    NOT NULL,
                diameter_max_m   REAL    NOT NULL,
                approach_date    TEXT    NOT NULL,
                velocity_kph     REAL    NOT NULL,
                miss_distance_km REAL    NOT NULL,
                orbiting_body    TEXT    NOT NULL,
                risk_score       INTEGER NOT NULL,
                narrative        TEXT    NOT NULL
            );
        """)


def save_report(
    start_date: str,
    end_date: str,
    max_distance_km: float,
    model: str,
    asteroids: list[dict],
    assessments: list[dict],
) -> int:
    """
    Persist a full report run. Returns the new report_id.

    asteroids   — list of dicts as produced by fetch_neos()
    assessments — parallel list of {"score": int, "narrative": str}
    """
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO reports (start_date, end_date, max_distance_km, model, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (str(start_date), str(end_date), max_distance_km, model, created_at),
        )
        report_id = cursor.lastrowid

        conn.executemany(
            """
            INSERT INTO asteroids
                (report_id, nasa_id, name, hazardous,
                 diameter_min_m, diameter_max_m, approach_date,
                 velocity_kph, miss_distance_km, orbiting_body,
                 risk_score, narrative)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    report_id,
                    a["nasa_id"],
                    a["name"],
                    int(a["hazardous"]),
                    a["diameter_min_m"],
                    a["diameter_max_m"],
                    a["approach_date"],
                    a["velocity_kph"],
                    a["miss_distance_km"],
                    a["orbiting_body"],
                    asmt["score"],
                    asmt["narrative"],
                )
                for a, asmt in zip(asteroids, assessments)
            ],
        )

    return report_id


def get_reports() -> list[sqlite3.Row]:
    """
    All reports, newest first, with precomputed summary stats via JOIN.
    Each row includes: all reports columns + object_count, hazardous_count,
    max_risk_score, avg_risk_score.
    """
    with _connect() as conn:
        return conn.execute(
            """
            SELECT
                r.*,
                COUNT(a.id)                 AS object_count,
                SUM(a.hazardous)            AS hazardous_count,
                MAX(a.risk_score)           AS max_risk_score,
                ROUND(AVG(a.risk_score), 1) AS avg_risk_score
            FROM reports r
            LEFT JOIN asteroids a ON a.report_id = r.id
            GROUP BY r.id
            ORDER BY r.id DESC
            """
        ).fetchall()


def get_total_asteroid_count() -> int:
    """Total number of asteroid records across all reports."""
    with _connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM asteroids").fetchone()[0]


def get_approach_timeline() -> list[sqlite3.Row]:
    """
    Aggregate close-approach counts by date across all reports,
    deduplicating asteroids that appear in multiple reports.
    Returns rows of (approach_date, count, hazardous_count, max_risk).
    """
    with _connect() as conn:
        return conn.execute(
            """
            SELECT
                approach_date,
                COUNT(*)          AS count,
                SUM(hazardous)    AS hazardous_count,
                MAX(risk_score)   AS max_risk
            FROM (
                SELECT nasa_id, approach_date,
                       MAX(hazardous)   AS hazardous,
                       MAX(risk_score)  AS risk_score
                FROM asteroids
                GROUP BY nasa_id, approach_date
            )
            GROUP BY approach_date
            ORDER BY approach_date ASC
            """
        ).fetchall()


def get_next_approach() -> sqlite3.Row | None:
    """
    Return the single asteroid with the nearest upcoming approach_date (>= today).
    If multiple reports contain the same asteroid, the closest-distance record wins.
    Returns None when no future approaches are on record.
    """
    with _connect() as conn:
        return conn.execute(
            """
            SELECT name, approach_date, miss_distance_km, risk_score, hazardous
            FROM asteroids
            WHERE approach_date >= date('now')
            ORDER BY approach_date ASC, miss_distance_km ASC
            LIMIT 1
            """
        ).fetchone()


def get_report(report_id: int) -> tuple:
    """
    Returns (report_row, asteroid_rows) for the given report_id.
    Asteroid rows are sorted by miss_distance_km ascending (closest first).
    Returns (None, []) if the report does not exist.
    """
    with _connect() as conn:
        report = conn.execute(
            "SELECT * FROM reports WHERE id = ?", (report_id,)
        ).fetchone()

        if report is None:
            return None, []

        asteroids = conn.execute(
            """
            SELECT * FROM asteroids
            WHERE report_id = ?
            ORDER BY miss_distance_km ASC
            """,
            (report_id,),
        ).fetchall()

    return report, asteroids
