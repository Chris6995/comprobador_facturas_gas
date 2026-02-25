"""
Extraccion de informacion de factura XML usando pandas.

Uso:
  .venv/bin/python scripts/extract_xml_pandas.py --xml "/ruta/factura.xml"
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Dict

import pandas as pd


NS = {"s": "http://localhost/sctd/B7031"}


def _to_float(value: Any) -> float | None:
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def extract_invoice_data(xml_path: str | Path) -> Dict[str, Any]:
    xml_path = str(xml_path)

    df_factura = pd.read_xml(
        xml_path,
        xpath=".//s:factura",
        namespaces=NS,
        parser="etree",
        encoding="ISO-8859-1",
    )
    df_emisora = pd.read_xml(
        xml_path,
        xpath=".//s:datosempresaemisora",
        namespaces=NS,
        parser="etree",
        encoding="ISO-8859-1",
    )
    df_conceptos = pd.read_xml(
        xml_path,
        xpath=".//s:listaconceptos/s:concepto",
        namespaces=NS,
        parser="etree",
        encoding="ISO-8859-1",
    )
    df_medidores = pd.read_xml(
        xml_path,
        xpath=".//s:listamedidores/s:medidor",
        namespaces=NS,
        parser="etree",
        encoding="ISO-8859-1",
    )

    meta = {
        "cups": df_factura.at[0, "cups"] if not df_factura.empty and "cups" in df_factura else None,
        "tipopeaje": (
            df_factura.at[0, "tipopeaje"]
            if not df_factura.empty and "tipopeaje" in df_factura
            else None
        ),
        "importetotal": (
            _to_float(df_factura.at[0, "importetotal"])
            if not df_factura.empty and "importetotal" in df_factura
            else None
        ),
        "numfactura": (
            df_factura.at[0, "numfactura"]
            if not df_factura.empty and "numfactura" in df_factura
            else None
        ),
        "fecfactura": (
            df_factura.at[0, "fecfactura"]
            if not df_factura.empty and "fecfactura" in df_factura
            else None
        ),
        "distribuidora_razonsocial": (
            df_emisora.at[0, "razonsocial"]
            if not df_emisora.empty and "razonsocial" in df_emisora
            else None
        ),
    }

    concepto_cols = [
        "codconcepto",
        "desconcepto",
        "unidad",
        "precunidad",
        "importe",
        "diascapacidadcontratada",
        "coeficientecortoplazo",
        "impuestoconcepto",
        "codtipoimpuesto",
        "porcentajeimpcto",
    ]
    cols_present = [c for c in concepto_cols if c in df_conceptos.columns]
    df_conceptos = df_conceptos[cols_present].copy()

    for col in [
        "unidad",
        "precunidad",
        "importe",
        "diascapacidadcontratada",
        "coeficientecortoplazo",
        "porcentajeimpcto",
    ]:
        if col in df_conceptos.columns:
            df_conceptos[col] = pd.to_numeric(df_conceptos[col], errors="coerce")

    if "codconcepto" in df_conceptos.columns:
        df_conceptos["codconcepto"] = (
            df_conceptos["codconcepto"]
            .astype("string")
            .str.replace(r"\.0$", "", regex=True)
            .str.zfill(4)
        )

    if "qdcontratado" in df_medidores.columns:
        qd_series = pd.to_numeric(df_medidores["qdcontratado"], errors="coerce").dropna()
        meta["qdcontratado_xml"] = float(qd_series.max()) if not qd_series.empty else None
    else:
        meta["qdcontratado_xml"] = None

    medidor_cols = [c for c in ["um", "aparato", "qdcontratado", "excesocaudal"] if c in df_medidores]
    df_medidores = df_medidores[medidor_cols].copy()
    for col in ["qdcontratado", "excesocaudal"]:
        if col in df_medidores.columns:
            df_medidores[col] = pd.to_numeric(df_medidores[col], errors="coerce")

    return {
        "meta": meta,
        "conceptos": df_conceptos,
        "medidores": df_medidores,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xml", required=True, help="Ruta al XML de factura")
    args = parser.parse_args()

    out = extract_invoice_data(args.xml)
    print("META")
    print(out["meta"])
    print("\nCONCEPTOS (head)")
    print(out["conceptos"].head(20).to_string(index=False))
    print("\nMEDIDORES (head)")
    print(out["medidores"].head(20).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
