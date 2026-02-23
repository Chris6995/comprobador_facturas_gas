"""
Script para migrar datos desde Excel a Supabase
Exe: python migrate_excel_to_supabase.py
"""

import os
import sys
import pandas as pd
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

try:
    import db
except ImportError:
    print("Error: No se pudo importar el módulo db.py")
    sys.exit(1)


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
            
            db.supabase.table("peajes_local").upsert(data).execute()
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
            
            db.supabase.table("peajes_regas").upsert(data).execute()
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
            
            db.supabase.table("peajes_cargo").upsert(data).execute()
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
            
            db.supabase.table("peajes_transporte").insert(data).execute()
            print(f"✅ Insertado peaje transporte: {tf_transporte}")
        
        return True
    except Exception as e:
        print(f"❌ Error migrando peajes_transporte: {str(e)}")
        return False


def migrate_conceptos_rules(excel_path: str) -> bool:
    """Migra reglas de conceptos"""
    try:
        df = pd.read_excel(excel_path, sheet_name="REF_rules_conceptos")
        
        rules_mapping = {
            "2000": ("Término Variable Local", "peajes_local", "tv"),
            "2002": ("Término Fijo Local", "peajes_local", "tf"),
            "2006": ("Transporte", "peajes_transporte", "tf_transporte"),
            "2009": ("Regasificación", "peajes_regas", "tf_regas"),
            "2011": ("Cargo Ministerio", "peajes_cargo", "tf_cargo"),
        }
        
        for cod, (desc, tabla, col) in rules_mapping.items():
            data = {
                "cod_concepto": cod,
                "descripcion": desc,
                "tabla_referencia": tabla,
                "columna_referencia": col,
                "requiere_validacion": True,
            }
            
            db.supabase.table("conceptos_rules").upsert(data).execute()
            print(f"✅ Insertada regla: {cod} - {desc}")
        
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
