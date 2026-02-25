"""
Migra referencias de contratacion por CUPS desde un Excel a Supabase.

Uso:
  python scripts/migrate_cups_contracts.py --excel data/Info_CDM_Bot.xlsx
"""

from __future__ import annotations

import argparse
from datetime import date, datetime
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def _clean_text(value: Any) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if not text or text == "-":
        return None
    return text


def _clean_tarifa(value: Any) -> str | None:
    text = _clean_text(value)
    if text is None:
        return None
    return text.replace("\xa0", "").strip()


def _clean_cups(value: Any) -> str | None:
    text = _clean_text(value)
    if text is None:
        return None
    return re.sub(r"\s+", "", text).upper()


def _clean_qd(value: Any) -> float | None:
    if pd.isna(value):
        return None
    try:
        qd = float(value)
    except (TypeError, ValueError):
        return None
    if qd <= 0:
        return None
    return qd


def normalize_cups_excel(excel_path: Path) -> pd.DataFrame:
    df = pd.read_excel(excel_path, sheet_name="CUPS")

    result = pd.DataFrame(
        {
            "cups": df["CUPS"].map(_clean_cups),
            "agente": df["AGENTE"].map(_clean_text),
            "provincia": df["PROVINCIA"].map(_clean_text),
            "distribuidora": df["DISTRIBUIDORA"].map(_clean_text),
            "tarifa": df["TARIFA"].map(_clean_tarifa),
            "cogeneracion": df["Cogeneracion"].map(_clean_text),
            "qd_contratada_kwh": df["QD CONTRATADA (kWh)"].map(_clean_qd),
            "interrumpibilidad": df["INTERRUMPIBILIDAD"].map(_clean_text),
            "interrumpibilidad_detalle": df["INTERRUMPIBILIDAD.1"].map(_clean_text),
            "pctd": df["PCTD"].map(_clean_text),
            "inicio_actividad": pd.to_datetime(
                df["Inicio de actividad"], errors="coerce"
            ).dt.date,
        }
    )

    result = result[result["cups"].notna()].copy()
    result = result.drop_duplicates(subset=["cups"], keep="last")
    return result.reset_index(drop=True)


def migrate_cups_contracts(df: pd.DataFrame) -> int:
    from comprobador.infra import supabase_client as db

    rows: List[Dict[str, Any]] = df.where(pd.notna(df), None).to_dict(orient="records")

    inserted = 0
    for row in rows:
        for key, value in list(row.items()):
            if isinstance(value, (date, datetime, pd.Timestamp)):
                row[key] = value.isoformat()
            elif isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                row[key] = None
            elif pd.isna(value):
                row[key] = None
        try:
            cups = row.get("cups")
            update_response = (
                db.supabase.table("cups_contratos")
                .update(row)
                .eq("cups", cups)
                .execute()
            )
            if not update_response.data:
                db.supabase.table("cups_contratos").insert(row).execute()
            inserted += 1
        except Exception as exc:
            cups = row.get("cups")
            raise RuntimeError(f"Error insertando CUPS {cups}: {exc}") from exc
    return inserted


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--excel",
        type=str,
        default="data/Info_CDM_Bot.xlsx",
        help="Ruta al Excel fuente (hoja CUPS).",
    )
    parser.add_argument(
        "--export-csv",
        type=str,
        default="data/cups_contratos_normalizado.csv",
        help="CSV de salida para revisar el DataFrame normalizado.",
    )
    parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Solo genera el DataFrame/CSV y no inserta en Supabase.",
    )
    args = parser.parse_args()

    excel_path = (ROOT_DIR / args.excel).resolve()
    if not excel_path.exists():
        print(f"Excel no encontrado: {excel_path}")
        return 1

    df_norm = normalize_cups_excel(excel_path)
    print(f"Filas normalizadas con CUPS: {len(df_norm)}")
    print(df_norm.head(10).to_string(index=False))

    csv_path = (ROOT_DIR / args.export_csv).resolve()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df_norm.to_csv(csv_path, index=False)
    print(f"\nCSV generado: {csv_path}")

    if args.skip_db:
        print("Modo --skip-db: no se inserta en Supabase.")
        return 0

    from comprobador.infra import supabase_client as db

    if not db.test_connection():
        print("No hay conexion operativa con Supabase.")
        return 2

    inserted = migrate_cups_contracts(df_norm)
    print(f"Registros insertados/actualizados en cups_contratos: {inserted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
