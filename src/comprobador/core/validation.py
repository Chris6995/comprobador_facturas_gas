from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, Union
import os
import re

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
                "fecdesde": get_c("fecdesde"),
                "fechasta": get_c("fechasta"),
                "diascapacidadcontratada": float(get_c("diascapacidadcontratada") or 0.0),
                "coeficientecortoplazo": float(get_c("coeficientecortoplazo") or 0.0),
                "multexcesocaudal": float(get_c("multexcesocaudal") or 0.0),
                "impuestoconcepto": get_c("impuestoconcepto"),
                "codtipoimpuesto": get_c("codtipoimpuesto"),
                "porcentajeimpcto": float(get_c("porcentajeimpcto") or 0.0),
            }
        )

    # QD contratado desde medidores (puede venir repetido por lectura)
    qd_values = []
    for med in factura.findall("s:listamedidores/s:medidor", ns):
        qd_el = med.find("s:qdcontratado", ns)
        if qd_el is not None and qd_el.text:
            try:
                qd_values.append(float(qd_el.text.strip()))
            except ValueError:
                pass
    meta["qdcontratado_xml"] = max(qd_values) if qd_values else None

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
    tables["cups_contracts"] = _load_cups_contracts_from_excel()
    return tables


def _clean_cups(value: Any) -> Optional[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    cups = re.sub(r"\s+", "", str(value)).upper().strip()
    return cups or None


def _clean_text(value: Any) -> Optional[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().replace("\xa0", "")
    if not text or text == "-":
        return None
    return text


def _load_cups_contracts_from_excel() -> pd.DataFrame:
    """
    Carga referencia de CUPS desde Info_CDM_Bot.xlsx para validar
    tarifa y capacidad contratada.
    """
    candidates = [
        os.getenv("CUPS_CONTRACTS_EXCEL_PATH"),
        "data/Info_CDM_Bot.xlsx",
    ]
    cups_excel_path = next((p for p in candidates if p and os.path.exists(p)), None)
    if not cups_excel_path:
        return pd.DataFrame()

    df = pd.read_excel(cups_excel_path, sheet_name="CUPS")
    result = pd.DataFrame(
        {
            "cups": df["CUPS"].map(_clean_cups),
            "tarifa": df["TARIFA"].map(_clean_text),
            "qd_contratada_kwh": pd.to_numeric(df["QD CONTRATADA (kWh)"], errors="coerce"),
            "interrumpibilidad": df["INTERRUMPIBILIDAD"].map(_clean_text),
        }
    )
    result = result[result["cups"].notna()].copy()
    result = result.drop_duplicates(subset=["cups"], keep="last")
    return result.reset_index(drop=True)


def _get_cups_contract_from_tables(
    cups: Optional[str], tables: Dict[str, pd.DataFrame]
) -> Optional[Dict[str, Any]]:
    if not cups:
        return None
    df = tables.get("cups_contracts", pd.DataFrame())
    if df.empty or "cups" not in df.columns:
        return None
    match = df[df["cups"] == cups]
    if match.empty:
        return None
    return match.iloc[0].to_dict()


def expected_capacity_unit(
    codconcepto: str,
    cups_contract: Optional[Dict[str, Any]],
    diascapacidadcontratada: float,
    coeficiente: float,
) -> Optional[float]:
    """
    Calcula unidad esperada para conceptos de capacidad fija:
    unidad = qd_contratada_kwh * dias * coef / 365
    """
    fixed_capacity_codes = {"2002", "2006", "2009", "2011"}
    if codconcepto not in fixed_capacity_codes or not cups_contract:
        return None

    qd = cups_contract.get("qd_contratada_kwh")
    if qd is None or pd.isna(qd):
        return None

    dias = diascapacidadcontratada or 0.0
    coef = coeficiente or 0.0
    if dias <= 0 or coef <= 0:
        return None

    return float(qd) * float(dias) * float(coef) / 365.0


def _month_start(dt: pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(year=dt.year, month=dt.month, day=1)


def _period_days_from_conceptos(df_conceptos: pd.DataFrame) -> Optional[int]:
    if df_conceptos.empty or "fecdesde" not in df_conceptos.columns or "fechasta" not in df_conceptos.columns:
        return None
    work = df_conceptos[df_conceptos["fecdesde"].notna() & df_conceptos["fechasta"].notna()]
    if work.empty:
        return None
    row = work.iloc[0]
    start = pd.to_datetime(row.get("fecdesde"), errors="coerce")
    end = pd.to_datetime(row.get("fechasta"), errors="coerce")
    if pd.isna(start) or pd.isna(end):
        return None
    days = int((end - start).days) + 1
    return days if days > 0 else None


def _consumo_global_mensual_xml(df_result: pd.DataFrame) -> Optional[float]:
    if df_result.empty or "codconcepto" not in df_result.columns:
        return None
    mask = df_result["codconcepto"].astype(str).isin({"2000", "2004"})
    if not mask.any():
        return None
    return float(df_result.loc[mask, "unidad"].max())


def expected_coef_cortoplazo_from_tables(
    codconcepto: str,
    fecdesde: Optional[str],
    tables: Dict[str, pd.DataFrame],
) -> Optional[float]:
    """
    Devuelve coeficiente esperado desde tabla de multiplicadores.
    Reglas actuales:
      - 2003 y 2007: multiplicador diario
      - 2002, 2006, 2009, 2011: 1.0 (termino fijo capacidad anualizado)
    """
    fixed_codes = {"2002", "2006", "2009", "2011"}
    short_daily_codes = {"2003", "2007"}

    if codconcepto in fixed_codes:
        return 1.0
    if codconcepto not in short_daily_codes:
        return None

    df_mult = tables.get("mult", pd.DataFrame())
    if df_mult.empty:
        return None

    # Compatibilidad de esquemas:
    # - Nuevo: fecha, trimestral, mensual, diario, intradiario
    # - Legacy: peaje (fecha en texto), multiplicador (equivale a diario)
    if "fecha" not in df_mult.columns and "peaje" in df_mult.columns:
        df_mult = df_mult.rename(columns={"peaje": "fecha"})
    if "diario" not in df_mult.columns and "multiplicador" in df_mult.columns:
        df_mult = df_mult.rename(columns={"multiplicador": "diario"})

    if "fecha" not in df_mult.columns or "diario" not in df_mult.columns:
        return None

    target_date = pd.to_datetime(fecdesde, errors="coerce")
    if pd.isna(target_date):
        return None
    target_month = _month_start(target_date)

    df_work = df_mult.copy()
    df_work["fecha"] = pd.to_datetime(df_work["fecha"], errors="coerce")
    df_work = df_work[df_work["fecha"].notna()]
    if df_work.empty:
        return None

    same_month = df_work[df_work["fecha"].map(_month_start) == target_month]
    if not same_month.empty:
        return float(same_month.iloc[0]["diario"])

    prev_rows = df_work[df_work["fecha"] <= target_month].sort_values("fecha")
    if not prev_rows.empty:
        return float(prev_rows.iloc[-1]["diario"])
    return None


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

    # 1) Intentar con reglas dinamicas (Excel REF_rules_conceptos / Supabase conceptos_rules)
    price_from_rules = _expected_price_from_rules(codconcepto, tipopeaje, tables)
    if price_from_rules is not None:
        return price_from_rules

    # 2) Fallback legacy hardcodeado
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


def _normalize_code(code: Any) -> str:
    if code is None:
        return ""
    text = str(code).strip()
    if not text:
        return ""
    # Convierte "2006.0" en "2006"
    if text.endswith(".0"):
        text = text[:-2]
    return text


def _rules_columns(df_rules: pd.DataFrame) -> Dict[str, str]:
    """
    Devuelve nombres de columnas reales para reglas, soportando
    formatos Excel y Supabase.
    """
    cols = set(df_rules.columns)
    out = {}
    if "codconcepto" in cols:
        out["cod"] = "codconcepto"
    elif "cod_concepto" in cols:
        out["cod"] = "cod_concepto"

    if "ref_sheet" in cols:
        out["sheet"] = "ref_sheet"
    elif "tabla_referencia" in cols:
        out["sheet"] = "tabla_referencia"

    if "lookup_key" in cols:
        out["lookup"] = "lookup_key"

    if "value_col" in cols:
        out["value"] = "value_col"
    elif "columna_referencia" in cols:
        out["value"] = "columna_referencia"
    return out


def _resolve_table_by_rule(sheet_name: str, tables: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    mapping = {
        "REF_peajes_local": "local",
        "peajes_local": "local",
        "REF_peajes_regas": "regas",
        "peajes_regas": "regas",
        "REF_cargo_ministerio": "cargo",
        "peajes_cargo": "cargo",
        "REF_peajes_transporte": "transporte",
        "peajes_transporte": "transporte",
        "REF_multiplicadores": "mult",
        "peajes_multiplicadores": "mult",
    }
    key = mapping.get(str(sheet_name).strip())
    if not key:
        return pd.DataFrame()
    return tables.get(key, pd.DataFrame())


def _resolve_value_column(df: pd.DataFrame, value_col: str) -> Optional[str]:
    if not value_col:
        return None
    if value_col in df.columns:
        return value_col

    norm_target = str(value_col).strip().lower().replace(" ", "_")
    for col in df.columns:
        norm_col = str(col).strip().lower().replace(" ", "_")
        if norm_col == norm_target or norm_target in norm_col:
            return col

    return None


def _expected_price_from_rules(
    codconcepto: str,
    tipopeaje: str,
    tables: Dict[str, pd.DataFrame],
) -> Optional[float]:
    df_rules = tables.get("rules", pd.DataFrame())
    if df_rules.empty:
        return None

    cols = _rules_columns(df_rules)
    if "cod" not in cols or "sheet" not in cols or "value" not in cols:
        return None

    cod_norm = _normalize_code(codconcepto)
    rules = df_rules[df_rules[cols["cod"]].map(_normalize_code) == cod_norm]
    if rules.empty:
        return None

    rule = rules.iloc[0]
    sheet_name = str(rule.get(cols["sheet"]) or "").strip()
    value_col = str(rule.get(cols["value"]) or "").strip()
    lookup_key = str(rule.get(cols["lookup"]) or "").strip() if "lookup" in cols else ""

    df_ref = _resolve_table_by_rule(sheet_name, tables)
    if df_ref.empty:
        return None

    col = _resolve_value_column(df_ref, value_col)
    if not col:
        return None

    # lookup por tipopeaje
    if lookup_key.lower() == "tipopeaje" and "peaje" in df_ref.columns:
        row = df_ref[df_ref["peaje"] == tipopeaje]
        if row.empty:
            return None
        return float(row.iloc[0][col])

    # lookup textual (ej. "Salida Nacional") sobre punto_salida
    if lookup_key:
        if "punto_salida" in df_ref.columns:
            mask = (
                df_ref["punto_salida"]
                .astype(str)
                .str.upper()
                .str.contains(lookup_key.upper(), na=False)
            )
            row = df_ref[mask]
            if not row.empty:
                return float(row.iloc[0][col])

    # fallback: primera fila con valor
    series = pd.to_numeric(df_ref[col], errors="coerce").dropna()
    if not series.empty:
        return float(series.iloc[0])
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
    tol_capacity: float = 0.05,
    tol_coef: float = 1e-6,
    tol_consumption: float = 0.01,
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
      - tol_capacity: tolerancia para unidad esperada por capacidad (kWh/d)
      - tol_coef: tolerancia para comparar coeficiente de cortoplazo
      - tol_consumption: tolerancia para validaciones de consumo (kWh)
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
    cups = meta.get("cups")
    cups_contract = None
    if use_database and cups:
        try:
            cups_contract = db.get_cups_contract(cups)
        except Exception:
            cups_contract = None
    elif not use_database:
        cups_contract = _get_cups_contract_from_tables(cups, tables)

    # Construir resultado fila a fila
    rows = []
    errors = 0

    for _, r in df_conceptos.iterrows():
        cod = str(r.get("codconcepto") or "")
        desconcepto = r.get("desconcepto")
        unidad = float(r.get("unidad") or 0.0)
        prec_xml = float(r.get("precunidad") or 0.0)
        imp_xml = float(r.get("importe") or 0.0)
        fecdesde = r.get("fecdesde")
        dias_cap = float(r.get("diascapacidadcontratada") or 0.0)
        coef_cp_xml = float(r.get("coeficientecortoplazo") or 0.0)
        impuestoconcepto = r.get("impuestoconcepto")
        codtipoimpuesto = r.get("codtipoimpuesto")
        porcentajeimpcto = float(r.get("porcentajeimpcto") or 0.0)

        prec_boe = expected_price_boe(cod, tipopeaje, tables)
        coef_cp_tabla = expected_coef_cortoplazo_from_tables(cod, fecdesde, tables)
        coef_cp_ok = (
            abs(coef_cp_xml - coef_cp_tabla) <= tol_coef
            if coef_cp_tabla is not None and coef_cp_xml > 0
            else None
        )

        expected_unidad_xml = expected_capacity_unit(
            cod, cups_contract, dias_cap, coef_cp_xml
        )
        coef_for_table_calc = (
            coef_cp_tabla if coef_cp_tabla is not None else coef_cp_xml
        )
        expected_unidad_tabla = expected_capacity_unit(
            cod, cups_contract, dias_cap, coef_for_table_calc
        )

        capacidad_ok = (
            abs(unidad - expected_unidad_tabla) <= tol_capacity
            if expected_unidad_tabla is not None
            else None
        )

        if prec_boe is None:
            importe_calc_xml = round(unidad * prec_xml, 2)
            formula_only_codes = {"0003", "0013"}
            formula_ok = (
                abs(imp_xml - importe_calc_xml) <= tol_amount
                if cod in formula_only_codes
                else None
            )
            estado_formula = (
                "OK" if formula_ok is True else "ERROR" if formula_ok is False else "SIN_REGLA"
            )
            if estado_formula == "ERROR":
                errors += 1
            rows.append(
                {
                    "codconcepto": cod,
                    "desconcepto": desconcepto,
                    "unidad": unidad,
                    "precunidad_xml": prec_xml,
                    "precunidad_boe": None,
                    "precio_ok": None,
                    "importe_xml": imp_xml,
                    "importe_calc": importe_calc_xml,
                    "importe_calc_xml": importe_calc_xml,
                    "importe_calc_boe": None,
                    "importe_ok": formula_ok,
                    "impuestoconcepto": impuestoconcepto,
                    "codtipoimpuesto": codtipoimpuesto,
                    "porcentajeimpcto": porcentajeimpcto,
                    "coeficientecortoplazo_xml": coef_cp_xml,
                    "coeficientecortoplazo_tabla": coef_cp_tabla,
                    "coeficientecortoplazo_ok": coef_cp_ok,
                    "unidad_esperada_cups": expected_unidad_tabla,
                    "unidad_esperada_xml_coef": expected_unidad_xml,
                    "unidad_esperada_tabla_coef": expected_unidad_tabla,
                    "capacidad_ok": capacidad_ok,
                    "estado": estado_formula,
                }
            )
            continue

        importe_calc_xml = round(unidad * prec_xml, 2)
        importe_calc_boe = round(unidad * prec_boe, 2)
        precio_ok = abs(prec_xml - prec_boe) <= tol_price
        # Regla principal: el importe facturado debe cuadrar con el calculado usando BOE.
        importe_ok = abs(imp_xml - importe_calc_boe) <= tol_amount
        checks_ok = [precio_ok, importe_ok]
        if capacidad_ok is not None:
            checks_ok.append(capacidad_ok)
        if coef_cp_ok is not None:
            checks_ok.append(coef_cp_ok)
        estado = "OK" if all(checks_ok) else "ERROR"
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
                "importe_calc": importe_calc_boe,
                "importe_calc_xml": importe_calc_xml,
                "importe_calc_boe": importe_calc_boe,
                "importe_ok": importe_ok,
                "impuestoconcepto": impuestoconcepto,
                "codtipoimpuesto": codtipoimpuesto,
                "porcentajeimpcto": porcentajeimpcto,
                "coeficientecortoplazo_xml": coef_cp_xml,
                "coeficientecortoplazo_tabla": coef_cp_tabla,
                "coeficientecortoplazo_ok": coef_cp_ok,
                "unidad_esperada_cups": expected_unidad_tabla,
                "unidad_esperada_xml_coef": expected_unidad_xml,
                "unidad_esperada_tabla_coef": expected_unidad_tabla,
                "capacidad_ok": capacidad_ok,
                "estado": estado,
            }
        )

    df_result = pd.DataFrame(rows)

    # Comprobacion de total factura usando suma de conceptos.
    # 0000 es total informado y 0007 suele ser base imponible (agregado),
    # por eso se excluyen para evitar doble conteo.
    total_excluded_codes = {"0000", "0007"}
    importetotal_xml = float(meta["importetotal"]) if meta.get("importetotal") else None
    importetotal_calc = round(
        float(
            df_result.loc[
                ~df_result["codconcepto"].astype(str).isin(total_excluded_codes),
                "importe_xml",
            ].sum()
        ),
        2,
    )
    total_ok = (
        abs(importetotal_xml - importetotal_calc) <= tol_amount
        if importetotal_xml is not None
        else None
    )
    if total_ok is False:
        errors += 1

    # Base imponible de IVA asociada a alquileres.
    # Se considera alquiler por codconcepto y/o descripcion.
    desc_upper = df_result["desconcepto"].fillna("").astype(str).str.upper()
    alquiler_mask = (
        df_result["codconcepto"].astype(str).isin({"0003", "0013"})
        | desc_upper.str.contains("ALQUILER", na=False)
    )
    base_imponible_calc = round(float(df_result.loc[alquiler_mask, "importe_xml"].sum()), 2)

    base_rows = df_result[df_result["codconcepto"].astype(str) == "0007"]
    base_imponible_xml = (
        round(float(base_rows["importe_xml"].sum()), 2) if not base_rows.empty else None
    )
    base_imponible_ok = (
        abs(base_imponible_xml - base_imponible_calc) <= tol_amount
        if base_imponible_xml is not None
        else None
    )
    if base_imponible_ok is False:
        errors += 1

    iva_rows = df_result[df_result["codconcepto"].astype(str) == "0008"]
    iva_xml = round(float(iva_rows["importe_xml"].sum()), 2) if not iva_rows.empty else None
    iva_rate = None
    if not base_rows.empty:
        rate_series = base_rows["porcentajeimpcto"]
        non_zero_rate = rate_series[rate_series > 0]
        if not non_zero_rate.empty:
            iva_rate = float(non_zero_rate.iloc[0])
    if iva_rate is None:
        iva_rate = 21.0

    iva_calc = round(base_imponible_calc * iva_rate / 100.0, 2)
    iva_ok = abs(iva_xml - iva_calc) <= tol_amount if iva_xml is not None else None
    if iva_ok is False:
        errors += 1

    # Validacion de QD del XML contra referencia contractual por CUPS.
    qd_xml = meta.get("qdcontratado_xml")
    qd_ref = cups_contract.get("qd_contratada_kwh") if cups_contract else None
    qd_match = (
        abs(float(qd_xml) - float(qd_ref)) <= tol_capacity
        if qd_xml is not None and qd_ref is not None
        else None
    )
    if qd_match is False:
        errors += 1

    # CONSUMO INDEFINIDO CALCULADO (kWh)
    # regla: min(consumo_global, capacidad) y si capacidad=0 -> consumo_global.
    consumo_global_xml = _consumo_global_mensual_xml(df_result)
    period_days = _period_days_from_conceptos(df_conceptos)
    qd_for_capacity = qd_ref if qd_ref is not None else qd_xml
    capacidad_mensual_kwh = (
        float(qd_for_capacity) * int(period_days)
        if qd_for_capacity is not None and period_days is not None
        else 0.0
    )
    if consumo_global_xml is not None:
        if capacidad_mensual_kwh > 0:
            consumo_indefinido_calc = min(float(consumo_global_xml), float(capacidad_mensual_kwh))
        else:
            consumo_indefinido_calc = float(consumo_global_xml)
    else:
        consumo_indefinido_calc = None

    consumo_indefinido_ok = (
        abs(float(consumo_global_xml) - float(consumo_indefinido_calc)) <= tol_consumption
        if consumo_global_xml is not None and consumo_indefinido_calc is not None
        else None
    )
    if consumo_indefinido_ok is False:
        errors += 1

    # Reflejar validaciones globales en filas agregadas.
    mask_total = df_result["codconcepto"].astype(str) == "0000"
    if mask_total.any() and total_ok is not None:
        df_result.loc[mask_total, "estado"] = "OK" if total_ok else "ERROR"

    mask_base = df_result["codconcepto"].astype(str) == "0007"
    if mask_base.any() and base_imponible_ok is not None:
        df_result.loc[mask_base, "estado"] = "OK" if base_imponible_ok else "ERROR"

    mask_iva = df_result["codconcepto"].astype(str) == "0008"
    if mask_iva.any() and iva_ok is not None:
        df_result.loc[mask_iva, "estado"] = "OK" if iva_ok else "ERROR"

    # Resumen
    summary = {
        "tipopeaje": tipopeaje,
        "cups": cups,
        "importetotal_xml": importetotal_xml,
        "importetotal_calc_conceptos": importetotal_calc,
        "importetotal_ok": total_ok,
        "importetotal_excluded_codes": sorted(total_excluded_codes),
        "base_imponible_xml": base_imponible_xml,
        "base_imponible_calc_alquileres": base_imponible_calc,
        "base_imponible_ok": base_imponible_ok,
        "iva_xml": iva_xml,
        "iva_rate_pct": iva_rate,
        "iva_calc": iva_calc,
        "iva_ok": iva_ok,
        "consumo_global_mensual_xml_kwh": consumo_global_xml,
        "capacidad_mensual_kwh": capacidad_mensual_kwh,
        "consumo_indefinido_calc_kwh": consumo_indefinido_calc,
        "consumo_indefinido_ok": consumo_indefinido_ok,
        "n_conceptos": int(len(df_result)),
        "n_coef_cortoplazo_checks": int(
            df_result["coeficientecortoplazo_ok"].notna().sum()
            if "coeficientecortoplazo_ok" in df_result.columns
            else 0
        ),
        "n_coef_cortoplazo_errors": int(
            (df_result["coeficientecortoplazo_ok"] == False).sum()  # noqa: E712
            if "coeficientecortoplazo_ok" in df_result.columns
            else 0
        ),
        "n_errors": int(errors),
        "status": "OK" if errors == 0 else "KO",
        "cups_ref_found": bool(cups_contract),
        "cups_tarifa_ref": cups_contract.get("tarifa") if cups_contract else None,
        "cups_qd_contratada_kwh_ref": (
            cups_contract.get("qd_contratada_kwh") if cups_contract else None
        ),
        "cups_qd_contratada_kwh_xml": qd_xml,
        "cups_qd_match_xml_vs_ref": qd_match,
        "cups_tarifa_match_xml_vs_ref": (
            str(meta.get("tipopeaje") or "").strip() == str(cups_contract.get("tarifa") or "").strip()
            if cups_contract
            and cups_contract.get("tarifa") is not None
            else None
        ),
        "cups_interrumpibilidad_ref": (
            cups_contract.get("interrumpibilidad") if cups_contract else None
        ),
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
