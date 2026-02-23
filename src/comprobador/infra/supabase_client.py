"""
Módulo de conexión y operaciones con Supabase
"""

import os
from typing import Dict, List, Any, Optional
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv


# Cargar variables de entorno
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL y SUPABASE_KEY no están definidas en .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# -------------------------
# Funciones de consulta
# -------------------------


def get_reference_tables() -> Dict[str, pd.DataFrame]:
    """
    Carga todas las tablas de referencia desde Supabase.
    Retorna un diccionario similar al de load_reference_tables() del Excel.
    """
    tables = {}

    try:
        # Peajes locales
        tables["local"] = _fetch_table_as_df("peajes_local")

        # Peajes regasificación
        tables["regas"] = _fetch_table_as_df("peajes_regas")

        # Cargo ministerio
        tables["cargo"] = _fetch_table_as_df("peajes_cargo")

        # Peajes transporte
        tables["transporte"] = _fetch_table_as_df("peajes_transporte")

        # Multiplicadores
        tables["mult"] = _fetch_table_as_df("peajes_multiplicadores")

        # Reglas de validación
        tables["rules"] = _fetch_table_as_df("conceptos_rules")

        return tables

    except Exception as e:
        raise Exception(f"Error al cargar tablas de referencias: {str(e)}")


def _fetch_table_as_df(table_name: str) -> pd.DataFrame:
    """
    Helper: fetch una tabla completa como DataFrame
    """
    try:
        response = supabase.table(table_name).select("*").execute()
        data = response.data
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)
    except Exception as e:
        raise Exception(f"Error al obtener tabla {table_name}: {str(e)}")


def get_concepto_rule(cod_concepto: str) -> Optional[Dict[str, Any]]:
    """
    Obtiene la regla (fila) de un concepto específico
    """
    try:
        response = (
            supabase.table("conceptos_rules")
            .select("*")
            .eq("cod_concepto", cod_concepto)
            .execute()
        )
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        raise Exception(f"Error al obtener regla del concepto {cod_concepto}: {str(e)}")


def get_peaje_by_type(table_name: str, peaje: str) -> Optional[Dict[str, Any]]:
    """
    Obtiene la fila de peaje por tipo (ej: "local", "regas", etc.)
    """
    try:
        response = (
            supabase.table(table_name)
            .select("*")
            .eq("peaje", peaje)
            .execute()
        )
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        raise Exception(f"Error al obtener peaje {peaje} de {table_name}: {str(e)}")


def insert_validation_result(
    validation_data: Dict[str, Any],
    result_rows: List[Dict[str, Any]],
) -> bool:
    """
    Inserta un resultado de validación en la tabla validaciones y conceptos_validados
    
    validation_data debe contener:
        - cups
        - tipopeaje
        - importetotal_xml
        - n_conceptos
        - n_errors
        - status
        
    result_rows es la lista de dicts con los conceptos validados
    """
    try:
        # Insertar validación principal
        val_response = supabase.table("validaciones").insert(validation_data).execute()
        
        if not val_response.data:
            return False
        
        validacion_id = val_response.data[0].get("id")
        
        # Insertar conceptos validados
        for row in result_rows:
            row["validacion_id"] = validacion_id
            supabase.table("conceptos_validados").insert(row).execute()
        
        return True

    except Exception as e:
        raise Exception(f"Error al insertar resultado de validación: {str(e)}")


def get_validation_history(cups: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Obtiene el historial de validaciones para un CUPS específico
    """
    try:
        response = (
            supabase.table("validaciones")
            .select("*")
            .eq("cups", cups)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data
    except Exception as e:
        raise Exception(f"Error al obtener historial de {cups}: {str(e)}")


def test_connection() -> bool:
    """
    Prueba la conexión a Supabase
    """
    try:
        # Intentar una consulta simple
        response = supabase.table("peajes_local").select("*").limit(1).execute()
        return True
    except Exception as e:
        print(f"Error de conexión a Supabase: {str(e)}")
        return False
