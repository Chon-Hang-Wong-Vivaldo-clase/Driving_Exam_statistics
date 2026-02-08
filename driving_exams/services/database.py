"""Database helpers."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Sequence


TABLE_COLUMNS = [
    ("province", "Province"),
    ("exam_center", "Exam Center"),
    ("driving_school_name", "Driving School"),
    ("exam_type", "Exam Type"),
    ("permit_name", "Permit"),
    ("year", "Year"),
    ("month", "Month"),
    ("passed", "Passed"),
    ("failed", "Failed"),
    ("presented", "Presented"),
]


class Database:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS driving_exams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    province TEXT NOT NULL,
                    exam_center TEXT NOT NULL,
                    driving_school_code TEXT,
                    driving_school_name TEXT,
                    section_code TEXT,
                    month INTEGER NOT NULL,
                    year INTEGER NOT NULL,
                    exam_type TEXT NOT NULL,
                    permit_name TEXT,
                    passed INTEGER NOT NULL,
                    passed_1conv INTEGER NOT NULL,
                    passed_2conv INTEGER NOT NULL,
                    passed_3or4conv INTEGER NOT NULL,
                    passed_5plus INTEGER NOT NULL,
                    failed INTEGER NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS imported_periods (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    year INTEGER NOT NULL,
                    month INTEGER NOT NULL,
                    UNIQUE(year, month)
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_exams_period ON driving_exams (year, month)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_exams_filters ON driving_exams (province, exam_center, driving_school_name, exam_type, permit_name)"
            )
            conn.commit()

    def is_period_imported(self, year: int, month: int) -> bool:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM imported_periods WHERE year = ? AND month = ?",
                (year, month),
            )
            return cursor.fetchone() is not None

    def mark_periods_imported(self, periods: Iterable[tuple[int, int]]) -> None:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.executemany(
                "INSERT OR IGNORE INTO imported_periods (year, month) VALUES (?, ?)",
                list(periods),
            )
            conn.commit()

    def insert_rows(self, rows: Iterable[Sequence]) -> int:
        sql = """
            INSERT INTO driving_exams (
                province, exam_center, driving_school_code, driving_school_name,
                section_code, month, year, exam_type, permit_name,
                passed, passed_1conv, passed_2conv, passed_3or4conv,
                passed_5plus, failed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.executemany(sql, list(rows))
            conn.commit()
            return cursor.rowcount

    def distinct_values(self, column: str) -> list[str]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT DISTINCT {column} FROM driving_exams WHERE {column} IS NOT NULL AND {column} != '' ORDER BY {column}"
            )
            return [row[0] for row in cursor.fetchall()]

    def available_years(self) -> list[int]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT year FROM driving_exams ORDER BY year")
            return [row[0] for row in cursor.fetchall()]

    def fetch_table(self, filters: dict) -> tuple[list[str], list[tuple]]:
        where, params = _build_filters(filters)
        sql = """
            SELECT
                province,
                exam_center,
                driving_school_name,
                exam_type,
                permit_name,
                year,
                month,
                passed,
                failed,
                (passed + failed) AS presented
            FROM driving_exams
        """
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY year, month, province"

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        headers = [label for _, label in TABLE_COLUMNS]
        return headers, [tuple(r) for r in rows]

    def fetch_chart_data(self, filters: dict) -> list[tuple]:
        where, params = _build_filters(filters)
        sql = """
            SELECT exam_type, SUM(passed) AS passed, SUM(failed) AS failed
            FROM driving_exams
        """
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " GROUP BY exam_type ORDER BY exam_type"

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return [tuple(r) for r in cursor.fetchall()]


def _build_filters(filters: dict) -> tuple[list[str], list]:
    where = []
    params: list = []

    if filters.get("province"):
        where.append("province LIKE ?")
        params.append(f"%{filters['province']}%")
    if filters.get("exam_center"):
        where.append("exam_center LIKE ?")
        params.append(f"%{filters['exam_center']}%")
    if filters.get("driving_school"):
        where.append("driving_school_name LIKE ?")
        params.append(f"%{filters['driving_school']}%")
    if filters.get("exam_type"):
        where.append("exam_type LIKE ?")
        params.append(f"%{filters['exam_type']}%")
    if filters.get("permit"):
        where.append("permit_name LIKE ?")
        params.append(f"%{filters['permit']}%")

    from_ym = filters.get("from_ym")
    to_ym = filters.get("to_ym")
    if from_ym is not None and to_ym is not None:
        where.append("(year * 100 + month) BETWEEN ? AND ?")
        params.extend([from_ym, to_ym])

    return where, params
