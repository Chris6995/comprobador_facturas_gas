from pathlib import Path
import sys

import streamlit as st

from backend import validate_from_streamlit_upload


def _resource_path(relative_path: str) -> str:
    base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return str(base_dir / relative_path)


EXCEL_PATH = _resource_path("data/Consumos-NEDGIA_SEPIOL_tablas.xlsx")

st.title("Validador XML")

xml_file = st.file_uploader("Sube el XML", type=["xml"])

if st.button("Validar") and xml_file:
    out = validate_from_streamlit_upload(xml_file, excel_path=EXCEL_PATH)

    st.write(out.summary)
    st.dataframe(out.df_result, use_container_width=True)
