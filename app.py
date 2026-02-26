from __future__ import annotations

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

import backend


def _status_icon(ok: bool | None) -> str:
    if ok is True:
        return "✅"
    if ok is None:
        return "➖"
    return "❌"


def _build_compact_output(out) -> pd.DataFrame:
    df = out.df_result.copy()
    summary = out.summary

    rows = []
    for _, r in df.iterrows():
        cod = str(r.get("codconcepto") or "")
        desc = str(r.get("desconcepto") or "")

        if cod == "0000":
            valor_xml = summary.get("importetotal_xml")
            valor_calc = summary.get("importetotal_calc_conceptos")
            ok = summary.get("importetotal_ok")
        elif cod == "0007":
            valor_xml = summary.get("base_imponible_xml")
            valor_calc = summary.get("base_imponible_calc_alquileres")
            ok = summary.get("base_imponible_ok")
        elif cod == "0008":
            valor_xml = summary.get("iva_xml")
            valor_calc = summary.get("iva_calc")
            ok = summary.get("iva_ok")
        elif pd.notna(r.get("importe_calc_boe")):
            valor_xml = r.get("importe_xml")
            valor_calc = r.get("importe_calc_boe")
            ok = r.get("importe_ok")
        elif pd.notna(r.get("importe_calc_xml")):
            valor_xml = r.get("importe_xml")
            valor_calc = r.get("importe_calc_xml")
            ok = r.get("importe_ok")
        else:
            valor_xml = r.get("importe_xml")
            valor_calc = None
            ok = None

        rows.append(
            {
                "concepto": f"{cod} - {desc}",
                "valor_xml": valor_xml,
                "valor_calculado": valor_calc,
                "estado": _status_icon(ok),
            }
        )

    df_out = pd.DataFrame(rows)
    if "valor_xml" in df_out.columns:
        df_out["valor_xml"] = pd.to_numeric(df_out["valor_xml"], errors="coerce").round(2)
    if "valor_calculado" in df_out.columns:
        df_out["valor_calculado"] = pd.to_numeric(df_out["valor_calculado"], errors="coerce").round(2)
    return df_out


def run() -> None:
    load_dotenv()

    st.title("Validador XML de Facturas")

    db_available = False
    with st.spinner("Validando conexion..."):
        if not backend.test_connection():
            st.error("No se pudo conectar a Supabase. Usando fallback a Excel.")
            db_available = False
        else:
            st.success("Conectado a Supabase")
            db_available = True

    if db_available:
        source = st.radio(
            "Fuente de validacion",
            options=["Supabase", "Excel"],
            index=1,
            horizontal=True,
            help="Excel usa tablas locales configuradas en EXCEL_PATH y Info_CDM_Bot.xlsx.",
        )
        use_db = source == "Supabase"
    else:
        use_db = False
        st.info("Modo Excel activo (Supabase no disponible).")

    xml_file = st.file_uploader("Sube el XML", type=["xml"])

    if st.button("Validar") and xml_file:
        try:
            out = backend.validate_from_streamlit_upload(xml_file, use_database=use_db)
            st.subheader(f"Resultado: {out.summary.get('status', 'KO')}")
            st.caption(f"Errores detectados: {out.summary.get('n_errors', 0)}")
            st.write("### Comparativa XML vs Calculado")
            st.dataframe(_build_compact_output(out), use_container_width=True)
        except Exception as exc:
            st.error(f"Error en validacion: {exc}")


if __name__ == "__main__":
    run()
