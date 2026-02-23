from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, Union
import os

import pandas as pd
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Importar módulo de base de datos
from comprobador.infra import supabase_client as db


# -------------------------
# Modelos de salida
# -------------------------
@dataclass
class ValidationOutput:
    meta: Dict[str, Any]
    df_result: pd.DataFrame
    summary: Dict[str, Any]


# -------------------------
# 1) Leer XML (ruta o bytes)
# -------------------------
def parse_invoice_xml(
    xml_input: Union[str, bytes],
    namespace_uri: str = "http://localhost/sctd/B7031",
) -> Tuple[Dict[str, Any], pd.DataFrame]:
    """
    Parsea un XML de factura y devuelve:
      - meta: campos clave
      - df_conceptos: DataFrame con conceptos

    xml_input puede ser:
      - str: ruta a fichero
      - bytes: contenido del xml (ideal para Streamlit uploader)
    """
    ns = {"s": namespace_uri}

    if isinstance(xml_input, bytes):
        tree = ET.ElementTree(ET.fromstring(xml_input))
    else:
        tree = ET.parse(xml_input)

    root = tree.getroot()
    factura = root.find("s:factura", ns)
    if factura is None:
        raise ValueError("No se encontró el nodo <factura> con el namespace esperado.")

    def _get_text(tag: str) -> Optional[str]:
        el = factura.find(f"s:{tag}", ns)
        return el.text.strip() if el is not None and el.text else None

    meta = {
        "tipopeaje": _get_text("tipopeaje"),
        "importetotal": _get_text("importetotal"),
        "cups": _get_text("cups"),
    }

    # conceptos
    conceptos_xml = factura.findall("s:listaconceptos/s:concepto", ns)

    conceptos = []
    for c in conceptos_xml:
        def get_c(field: str) -> Optional[str]:
            el = c.find(f"s:{field}", ns)
            return el.text.strip() if el is not None and el.text else None

        conceptos.append(
            {
                "codconcepto": get_c("codconcepto"),
                "desconcepto": get_c("desconcepto"),
                "unidad": float(get_c("unidad") or 0.0),
                "precunidad": float(get_c("precunidad") or 0.0),
                "importe": float(get_c("importe") or 0.0),
            }
        )

    df_conceptos = pd.DataFrame(conceptos)
    return meta, df_conceptos


# -------------------------
# 2) Cargar tablas de referencia (ahora desde Supabase)
# -------------------------
def load_reference_tables(excel_path: str = None) -> Dict[str, pd.DataFrame]:
    """
    Carga las tablas de referencia desde Supabase.
    El parámetro excel_path se mantiene por compatibilidad pero no se usa.
    
    Si Supabase no está disponible, intenta cargar desde Excel como fallback.
    """
    try:
        # Intentar cargar desde Supabase
        return db.get_reference_tables()
    except Exception as e:
        # Fallback a Excel si Supabase falla
        if excel_path and os.path.exists(excel_path):
            print(f"Advertencia: No se pudo conectar a Supabase ({str(e)}). "
                  f"Usando Excel como fallback: {excel_path}")
            return load_reference_tables_from_excel(excel_path)
        else:
            raise Exception(f"No se pudo cargar tablas de referencia desde Supabase ni Excel: {str(e)}")


def load_reference_tables_from_excel(excel_path: str) -> Dict[str, pd.DataFrame]:
    """
    Carga las tablas de referencia desde Excel (método legacy).
    Se usa como fallback si Supabase no está disponible.
    """
    tables = {
        "local": pd.read_excel(excel_path, sheet_name="REF_peajes_local"),
        "regas": pd.read_excel(excel_path, sheet_name="REF_peajes_regas"),
        "cargo": pd.read_excel(excel_path, sheet_name="REF_cargo_ministerio"),
        "transporte": pd.read_excel(excel_path, sheet_name="REF_peajes_transporte"),
        "mult": pd.read_excel(excel_path, sheet_name="REF_multiplicadores"),
        "rules": pd.read_excel(excel_path, sheet_name="REF_rules_conceptos"),
    }
    return tables


# -------------------------
# 3) Precio esperado BOE (if/elif)
# -------------------------
def expected_price_boe(
    codconcepto: str,
    tipopeaje: str,
    tables: Dict[str, pd.DataFrame],
) -> Optional[float]:
    """
    Devuelve el precio BOE esperado según el código de concepto.
    Versión simple if/elif, usando las tablas REF ya cargadas.
    """
    df_local = tables["local"]
    df_regas = tables["regas"]
    df_cargo = tables["cargo"]
    df_transporte = tables["transporte"]

    # Local: TF/TV
    if codconcepto == "2002":  # término fijo local
        if df_local.empty or "peaje" not in df_local.columns or "tf" not in df_local.columns:
            return None
        fila = df_local[df_local["peaje"] == tipopeaje]
        if fila.empty:
            return None
        return float(fila["tf"].values[0])

    elif codconcepto == "2000":  # término variable local
        if df_local.empty or "peaje" not in df_local.columns or "tv" not in df_local.columns:
            return None
        fila = df_local[df_local["peaje"] == tipopeaje]
        if fila.empty:
            return None
        return float(fila["tv"].values[0])

    # Regasificación
    elif codconcepto == "2009":
        if df_regas.empty or "peaje" not in df_regas.columns:
            return None
        fila = df_regas[df_regas["peaje"] == tipopeaje]
        if fila.empty:
            return None
        # Ajusta aquí si tu columna se llama distinto
        col = "tf_regas" if "tf_regas" in fila.columns else "tf"
        return float(fila[col].values[0])

    # Cargo ministerio
    elif codconcepto == "2011":
        if df_cargo.empty or "peaje" not in df_cargo.columns:
            return None
        fila = df_cargo[df_cargo["peaje"] == tipopeaje]
        if fila.empty:
            return None
        col = "tf_cargo" if "tf_cargo" in fila.columns else "tf"
        return float(fila[col].values[0])

    # Transporte (normalmente no depende de peaje)
    elif codconcepto == "2006":
        # Tu columna real (según tu último código)
        col = "tf_transporte €/(kWh/día) y año"
        if col in df_transporte.columns:
            return float(df_transporte[col].values[0])
        # fallback si la renombráis a algo más simple
        for fallback in ["tf", "tf_tp", "tf_transporte"]:
            if fallback in df_transporte.columns:
                return float(df_transporte[fallback].values[0])
        return None

    # Otros conceptos no implementados aún
    return None


# -------------------------
# 4) Validación
# -------------------------
def validate_invoice(
    xml_input: Union[str, bytes],
    excel_path: str = None,
    namespace_uri: str = "http://localhost/sctd/B7031",
    tol_price: float = 1e-6,
    tol_amount: float = 0.01,
    use_database: bool = True,
) -> ValidationOutput:
    """
    Valida una factura XML contra tablas de referencia.
    
    Parámetros:
      - xml_input: ruta o bytes del XML
      - excel_path: ruta al Excel (usado si use_database=False o como fallback)
      - namespace_uri: namespace del XML
      - tol_price: tolerancia para precios
      - tol_amount: tolerancia para importes
      - use_database: True para usar Supabase, False para Excel
    """
    meta, df_conceptos = parse_invoice_xml(xml_input, namespace_uri=namespace_uri)
    
    # Cargar tablas de referencia
    if use_database:
        try:
            tables = load_reference_tables(excel_path=excel_path)
        except Exception as e:
            raise ValueError(f"No se pudo cargar datos desde base de datos: {str(e)}")
    else:
        if not excel_path:
            excel_path = os.getenv("EXCEL_PATH")
        tables = load_reference_tables_from_excel(excel_path)

    if use_database:
        required = ["local", "regas", "cargo", "transporte", "rules"]
        if all(tables.get(name, pd.DataFrame()).empty for name in required):
            raise ValueError(
                "Supabase devolvio todas las tablas de referencia vacias. "
                "Revisa datos cargados, proyecto/URL y politicas RLS."
            )

    tipopeaje = meta.get("tipopeaje")
    if not tipopeaje:
        raise ValueError("No se pudo leer tipopeaje del XML.")

    # Construir resultado fila a fila
    rows = []
    errors = 0

    for _, r in df_conceptos.iterrows():
        cod = str(r.get("codconcepto") or "")
        desconcepto = r.get("desconcepto")
        unidad = float(r.get("unidad") or 0.0)
        prec_xml = float(r.get("precunidad") or 0.0)
        imp_xml = float(r.get("importe") or 0.0)

        prec_boe = expected_price_boe(cod, tipopeaje, tables)

        if prec_boe is None:
            rows.append(
                {
                    "codconcepto": cod,
                    "desconcepto": desconcepto,
                    "unidad": unidad,
                    "precunidad_xml": prec_xml,
                    "precunidad_boe": None,
                    "precio_ok": None,
                    "importe_xml": imp_xml,
                    "importe_calc": round(unidad * prec_xml, 2),
                    "importe_ok": None,
                    "estado": "SIN_REGLA",
                }
            )
            continue

        importe_calc = round(unidad * prec_xml, 2)
        precio_ok = abs(prec_xml - prec_boe) <= tol_price
        importe_ok = abs(imp_xml - importe_calc) <= tol_amount
        estado = "OK" if (precio_ok and importe_ok) else "ERROR"
        if estado == "ERROR":
            errors += 1

        rows.append(
            {
                "codconcepto": cod,
                "desconcepto": desconcepto,
                "unidad": unidad,
                "precunidad_xml": prec_xml,
                "precunidad_boe": prec_boe,
                "precio_ok": precio_ok,
                "importe_xml": imp_xml,
                "importe_calc": importe_calc,
                "importe_ok": importe_ok,
                "estado": estado,
            }
        )

    df_result = pd.DataFrame(rows)

    # Resumen
    summary = {
        "tipopeaje": tipopeaje,
        "cups": meta.get("cups"),
        "importetotal_xml": float(meta["importetotal"]) if meta.get("importetotal") else None,
        "n_conceptos": int(len(df_result)),
        "n_errors": int(errors),
        "status": "OK" if errors == 0 else "KO",
    }

    return ValidationOutput(meta=meta, df_result=df_result, summary=summary)


# -------------------------
# Helpers para Streamlit
# -------------------------
def validate_from_streamlit_upload(
    uploaded_xml_file,
    excel_path: str = None,
    use_database: bool = True,
) -> ValidationOutput:
    """
    Helper para Streamlit:
      uploaded_xml_file = st.file_uploader(...)
    
    Valida usando Supabase por defecto (use_database=True).
    """
    if uploaded_xml_file is None:
        raise ValueError("No se ha subido ningún XML.")

    # Si no se proporciona excel_path, obtenerlo del .env
    if not excel_path:
        excel_path = os.getenv("EXCEL_PATH")

    xml_bytes = uploaded_xml_file.getvalue()
    return validate_invoice(xml_bytes, excel_path=excel_path, use_database=use_database)
