"""
Script para migrar datos desde Excel a Supabase
Exe: python scripts/migrate_excel_to_supabase.py
"""

import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
import sys
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Cargar variables de entorno
load_dotenv(ROOT_DIR / ".env")

try:
    import backend as db
except ImportError:
    print("Error: No se pudo importar el modulo de Supabase")
    raise


def _client():
    return db.get_supabase_client()


def migrate_peajes_local(excel_path: str) -> bool:
    """Migra peajes locales del Excel a Supabase"""
    try:
        df = pd.read_excel(excel_path, sheet_name="REF_peajes_local")
        
        for _, row in df.iterrows():
            peaje = str(row.get("peaje") or "").strip()
            if not peaje:
                continue
            
            data = {
                "peaje": peaje,
                "tf": float(row.get("tf") or 0),
                "tv": float(row.get("tv") or 0),
            }
            
            _client().table("peajes_local").upsert(
                data,
                on_conflict="peaje",
            ).execute()
            print(f"✅ Insertado peaje local: {peaje}")
        
        return True
    except Exception as e:
        print(f"❌ Error migrando peajes_local: {str(e)}")
        return False


def migrate_peajes_regas(excel_path: str) -> bool:
    """Migra peajes de regasificación"""
    try:
        df = pd.read_excel(excel_path, sheet_name="REF_peajes_regas")
        
        for _, row in df.iterrows():
            peaje = str(row.get("peaje") or "").strip()
            if not peaje:
                continue
            
            # Buscar columna tf_regas
            tf_regas = None
            for col in ["tf_regas", "tf", "regas"]:
                if col in df.columns:
                    tf_regas = float(row.get(col) or 0)
                    break
            
            if tf_regas is None:
                continue
            
            data = {
                "peaje": peaje,
                "tf_regas": tf_regas,
            }
            
            _client().table("peajes_regas").upsert(
                data,
                on_conflict="peaje",
            ).execute()
            print(f"✅ Insertado peaje regas: {peaje}")
        
        return True
    except Exception as e:
        print(f"❌ Error migrando peajes_regas: {str(e)}")
        return False


def migrate_peajes_cargo(excel_path: str) -> bool:
    """Migra cargos ministeriales"""
    try:
        df = pd.read_excel(excel_path, sheet_name="REF_cargo_ministerio")
        
        for _, row in df.iterrows():
            peaje = str(row.get("peaje") or "").strip()
            if not peaje:
                continue
            
            # Buscar columna tf_cargo
            tf_cargo = None
            for col in ["tf_cargo", "tf", "cargo"]:
                if col in df.columns:
                    tf_cargo = float(row.get(col) or 0)
                    break
            
            if tf_cargo is None:
                continue
            
            data = {
                "peaje": peaje,
                "tf_cargo": tf_cargo,
            }
            
            _client().table("peajes_cargo").upsert(
                data,
                on_conflict="peaje",
            ).execute()
            print(f"✅ Insertado cargo ministerio: {peaje}")
        
        return True
    except Exception as e:
        print(f"❌ Error migrando peajes_cargo: {str(e)}")
        return False


def migrate_peajes_transporte(excel_path: str) -> bool:
    """Migra peajes de transporte"""
    try:
        df = pd.read_excel(excel_path, sheet_name="REF_peajes_transporte")
        
        for _, row in df.iterrows():
            # Buscar columna de precio de transporte
            tf_transporte = None
            for col in df.columns:
                if "transporte" in col.lower():
                    tf_transporte = float(row.get(col) or 0)
                    break
            
            if tf_transporte is None or tf_transporte == 0:
                continue
            
            data = {
                "tf_transporte": tf_transporte,
            }
            
            _client().table("peajes_transporte").insert(data).execute()
            print(f"✅ Insertado peaje transporte: {tf_transporte}")
        
        return True
    except Exception as e:
        print(f"❌ Error migrando peajes_transporte: {str(e)}")
        return False


def migrate_peajes_multiplicadores(excel_path: str) -> bool:
    """Migra multiplicadores (diario/mensual/trimestral/intradiario)."""
    try:
        df = pd.read_excel(excel_path, sheet_name="REF_multiplicadores")

        for _, row in df.iterrows():
            fecha = pd.to_datetime(row.get("fecha"), errors="coerce")
            if pd.isna(fecha):
                continue

            data_new = {
                "fecha": fecha.date().isoformat(),
                "trimestral": float(row.get("trimestral") or 0),
                "mensual": float(row.get("mensual") or 0),
                "diario": float(row.get("diario") or 0),
                "intradiario": float(row.get("intradiario") or 0),
            }

            try:
                _client().table("peajes_multiplicadores").upsert(
                    data_new,
                    on_conflict="fecha",
                ).execute()
            except Exception:
                # Compatibilidad con esquema legacy (peaje/multiplicador)
                data_legacy = {
                    "peaje": data_new["fecha"],
                    "multiplicador": data_new["diario"],
                }
                _client().table("peajes_multiplicadores").upsert(
                    data_legacy,
                    on_conflict="peaje",
                ).execute()

            print(f"✅ Insertado multiplicador fecha: {data_new['fecha']}")

        return True
    except Exception as e:
        print(f"❌ Error migrando peajes_multiplicadores: {str(e)}")
        return False


def migrate_conceptos_rules(excel_path: str) -> bool:
    """Migra reglas de conceptos"""
    try:
        df = pd.read_excel(excel_path, sheet_name="REF_rules_conceptos")

        table_map = {
            "REF_peajes_local": "peajes_local",
            "REF_peajes_transporte": "peajes_transporte",
            "REF_peajes_regas": "peajes_regas",
            "REF_cargo_ministerio": "peajes_cargo",
            "REF_multiplicadores": "peajes_multiplicadores",
        }

        for _, row in df.iterrows():
            cod = str(row.get("codconcepto") or "").strip()
            if not cod:
                continue

            cod = cod.replace(".0", "")
            desc = str(row.get("descripcion") or "").strip() or None
            ref_sheet = str(row.get("ref_sheet") or "").strip()
            tabla = table_map.get(ref_sheet, ref_sheet)
            col = str(row.get("value_col") or "").strip() or None

            data = {
                "cod_concepto": cod,
                "descripcion": desc,
                "tabla_referencia": tabla,
                "columna_referencia": col,
                "requiere_validacion": True,
            }

            _client().table("conceptos_rules").upsert(
                data,
                on_conflict="cod_concepto",
            ).execute()
            print(f"✅ Insertada regla: {cod} - {desc or 'sin descripcion'}")
        
        return True
    except Exception as e:
        print(f"❌ Error migrando conceptos_rules: {str(e)}")
        return False


def main():
    """Ejecuta la migración completa"""
    excel_path = os.getenv("EXCEL_PATH")
    
    if not excel_path or not os.path.exists(excel_path):
        print(f"❌ Excel no encontrado: {excel_path}")
        print("   Verifica EXCEL_PATH en .env")
        return False
    
    print(f"📂 Leyendo Excel: {excel_path}")
    print()
    
    # Verificar conexión a Supabase
    if not db.test_connection():
        print("❌ No se pudo conectar a Supabase")
        print("   Verifica SUPABASE_URL y SUPABASE_KEY en .env")
        return False
    
    print("✅ Conectado a Supabase")
    print()
    
    print("🔄 Iniciando migración...")
    print()
    
    results = []
    results.append(("Peajes Locales", migrate_peajes_local(excel_path)))
    results.append(("Peajes Regas", migrate_peajes_regas(excel_path)))
    results.append(("Peajes Cargo", migrate_peajes_cargo(excel_path)))
    results.append(("Peajes Transporte", migrate_peajes_transporte(excel_path)))
    results.append(("Peajes Multiplicadores", migrate_peajes_multiplicadores(excel_path)))
    results.append(("Reglas de Conceptos", migrate_conceptos_rules(excel_path)))
    
    print()
    print("=" * 50)
    print("📊 RESUMEN DE MIGRACIÓN")
    print("=" * 50)
    
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {name}")
    
    all_success = all(success for _, success in results)
    
    if all_success:
        print()
        print("🎉 ¡Migración completada exitosamente!")
        return True
    else:
        print()
        print("⚠️ Migración completada con errores. Revisa los logs anterior.")
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Migración cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {str(e)}")
        sys.exit(1)
