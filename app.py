from pathlib import Path
import sys

import streamlit as st
from dotenv import load_dotenv

from backend import validate_from_streamlit_upload, db

# Cargar variables de entorno
load_dotenv()

st.title("Validador XML de Facturas")

# Prueba de conexión a Supabase
with st.spinner("Validando conexión..."):
    if not db.test_connection():
        st.error("⚠️ No se pudo conectar a Supabase. Usando fallback a Excel.")
        use_db = False
    else:
        st.success("✅ Conectado a Supabase")
        use_db = True

xml_file = st.file_uploader("Sube el XML", type=["xml"])

if st.button("Validar") and xml_file:
    try:
        out = validate_from_streamlit_upload(xml_file, use_database=use_db)
        
        st.write("### Resumen")
        st.write(out.summary)
        
        st.write("### Detalle de Conceptos")
        st.dataframe(out.df_result, use_container_width=True)
    except Exception as e:
        st.error(f"Error en validación: {str(e)}")

