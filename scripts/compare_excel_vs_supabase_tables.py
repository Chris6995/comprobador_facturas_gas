"""
Compara tablas de referencia entre Excel y Supabase.

Uso:
  .venv/bin/python scripts/compare_excel_vs_supabase_tables.py --excel data/Consumos-NEDGIA_SEPIOL_tablas.xlsx
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Dict, List

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import backend


TABLES = ["local", "regas", "cargo", "transporte", "mult", "rules"]


def _norm_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c).strip() for c in out.columns]
    for c in out.columns:
        if pd.api.types.is_object_dtype(out[c]):
            out[c] = out[c].astype("string").str.strip()
    return out


def _common_cols(a: pd.DataFrame, b: pd.DataFrame) -> List[str]:
    ignore = {"id", "created_at", "updated_at"}
    cols = [c for c in a.columns if c in b.columns and c not in ignore]
    return cols


def _to_numeric_if_possible(series: pd.Series) -> pd.Series:
    try:
        converted = pd.to_numeric(series)
    except Exception:
        return series
    return converted


def compare_table(name: str, excel_df: pd.DataFrame, db_df: pd.DataFrame) -> Dict:
    excel_df = _norm_df(excel_df)
    db_df = _norm_df(db_df)

    cols = _common_cols(excel_df, db_df)
    if not cols:
        return {
            "table": name,
            "excel_rows": len(excel_df),
            "db_rows": len(db_df),
            "status": "NO_COMMON_COLUMNS",
            "only_excel_columns": [c for c in excel_df.columns if c not in db_df.columns],
            "only_db_columns": [c for c in db_df.columns if c not in excel_df.columns],
        }

    a = excel_df[cols].copy()
    b = db_df[cols].copy()
    for c in cols:
        if pd.api.types.is_numeric_dtype(a[c]) or pd.api.types.is_numeric_dtype(b[c]):
            a[c] = _to_numeric_if_possible(a[c])
            b[c] = _to_numeric_if_possible(b[c])

    # Representación ordenable/estable
    a_s = a.astype("string").fillna("").sort_values(cols).reset_index(drop=True)
    b_s = b.astype("string").fillna("").sort_values(cols).reset_index(drop=True)

    a_set = set(map(tuple, a_s.values.tolist()))
    b_set = set(map(tuple, b_s.values.tolist()))

    only_excel = list(a_set - b_set)
    only_db = list(b_set - a_set)

    status = "OK" if not only_excel and not only_db else "DIFF"
    return {
        "table": name,
        "excel_rows": len(excel_df),
        "db_rows": len(db_df),
        "compared_columns": cols,
        "status": status,
        "only_excel_count": len(only_excel),
        "only_db_count": len(only_db),
        "only_excel_samples": [dict(zip(cols, row)) for row in only_excel[:5]],
        "only_db_samples": [dict(zip(cols, row)) for row in only_db[:5]],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--excel", required=True, help="Ruta Excel tablas BOE")
    parser.add_argument(
        "--out-json",
        default="docs/diff_excel_vs_supabase_tables.json",
        help="Salida JSON con el detalle de diferencias",
    )
    args = parser.parse_args()

    excel_tables = backend.load_reference_tables_from_excel(args.excel)
    db_tables = backend.get_reference_tables()

    results = []
    for t in TABLES:
        results.append(compare_table(t, excel_tables.get(t, pd.DataFrame()), db_tables.get(t, pd.DataFrame())))

    ok = all(r["status"] == "OK" for r in results)
    summary = {
        "all_tables_equal": ok,
        "results": results,
    }

    out_path = (ROOT_DIR / args.out_json).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("all_tables_equal:", ok)
    for r in results:
        print(
            f"- {r['table']}: {r['status']} "
            f"(excel={r['excel_rows']}, db={r['db_rows']}, "
            f"only_excel={r.get('only_excel_count', 0)}, only_db={r.get('only_db_count', 0)})"
        )
    print("report:", out_path)
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
