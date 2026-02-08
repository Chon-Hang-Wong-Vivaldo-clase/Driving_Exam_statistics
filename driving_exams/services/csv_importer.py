"""CSV import logic for DGT driving exam statistics."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from .database import Database


def _to_int(value: str) -> int:
    try:
        return int(str(value).replace(".", "").replace(",", "").strip())
    except Exception:
        return 0


def _read_rows(path: Path) -> list[list[str]]:
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            with path.open(encoding=enc, newline="") as f:
                sample = f.read(4096)
                f.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample, ",;\t|")
                except Exception:
                    dialect = csv.excel
                    dialect.delimiter = ";"
                return list(csv.reader(f, dialect))
        except Exception:
            continue
    raise ValueError("Could not read the file with supported encodings")


def _normalize_header(value: str) -> str:
    return value.strip().lower()


def parse_rows(path: Path) -> tuple[list[tuple], set[tuple[int, int]]]:
    rows = _read_rows(path)
    if not rows:
        return [], set()

    header = [_normalize_header(h) for h in rows[0]]
    data_rows = rows[1:] if "provincia" in header[0] or "desc_provincia" in header[0] else rows

    index = {name: idx for idx, name in enumerate(header)}

    def get(row: list[str], *keys: str) -> str:
        for k in keys:
            if k in index and index[k] < len(row):
                return row[index[k]].strip()
        return ""

    parsed: list[tuple] = []
    periods: set[tuple[int, int]] = set()

    for r in data_rows:
        if not r or len(r) < 5:
            continue

        province = get(r, "desc_provincia", "provincia")
        exam_center = get(r, "centro_examen", "centro")
        school_code = get(r, "codigo_autoescuela", "cod_autoescuela")
        school_name = get(r, "nombre_autoescuela", "autoescuela")
        section_code = get(r, "codigo_seccion", "seccion")
        month = _to_int(get(r, "mes"))
        year = _to_int(get(r, "anyo", "anio", "year"))
        exam_type = get(r, "tipo_examen")
        permit = get(r, "nombre_permiso", "permiso")
        passed = _to_int(get(r, "num_aptos", "aptos"))
        passed_1 = _to_int(get(r, "num_aptos_1conv"))
        passed_2 = _to_int(get(r, "num_aptos_2conv"))
        passed_3 = _to_int(get(r, "num_aptos_3o4conv"))
        passed_5 = _to_int(get(r, "num_aptos_5_o_mas_conv"))
        failed = _to_int(get(r, "num_no_aptos", "no_aptos"))

        if not province or not exam_center or not year or not month:
            continue

        parsed.append(
            (
                province,
                exam_center,
                school_code,
                school_name,
                section_code,
                month,
                year,
                exam_type,
                permit,
                passed,
                passed_1,
                passed_2,
                passed_3,
                passed_5,
                failed,
            )
        )
        periods.add((year, month))

    return parsed, periods


def import_csv(path: Path, db: Database) -> int:
    rows, periods = parse_rows(path)
    if not rows:
        raise ValueError("No data rows found in the file")

    to_insert = []
    imported_periods = set()
    skipped_periods = set()

    for row in rows:
        year = row[6]
        month = row[5]
        if db.is_period_imported(year, month):
            skipped_periods.add((year, month))
            continue
        to_insert.append(row)
        imported_periods.add((year, month))

    if not to_insert:
        raise ValueError("All periods in this file were already imported")

    inserted = db.insert_rows(to_insert)
    db.mark_periods_imported(imported_periods)
    return inserted
