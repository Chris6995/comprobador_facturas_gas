# Comprobador de Facturas de Gas - Sercomgas

Aplicación web para validar facturas XML contra tablas de referencia de peajes y conceptos.

## 🚀 Características

- ✅ Validación de facturas XML (SCTD B7031)
- ✅ Consulta de tarificación BOE en **Supabase** (base de datos)
- ✅ Historial de validaciones
- ✅ Fallback automático a Excel si no hay BD
- ✅ Interfaz web con Streamlit

## 📋 Requisitos

- Python 3.8+
- Entorno virtual (.venv)
- Conexión a internet para Supabase

## ⚙️ Instalación Rápida

### 1. Clonar y activar entorno

```bash
git clone <repo>
cd comprador_facturas_sercomgas
source .venv/bin/activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar Supabase

Lee [SUPABASE_SETUP.md](./SUPABASE_SETUP.md) para:
- Crear las tablas en Supabase
- Cargar datos desde Excel
- Verificar la conexión

### 4. Ejecutar aplicación

```bash
streamlit run app.py
```

Se abrirá en `http://localhost:8501`

---

## 📁 Estructura de Archivos

```
├── app.py                          # Interfaz Streamlit
├── backend.py                      # Lógica de validación
├── db.py                          # Módulo de conexión a Supabase
├── .env                           # Variables de entorno (NO en Git)
├── database_schema.sql            # SQL para crear tablas
├── migrate_excel_to_supabase.py   # Script para migrar datos
├── requirements.txt               # Dependencias Python
├── SUPABASE_SETUP.md              # Guía de configuración
└── data/
    └── Consumos-NEDGIA_SEPIOL_tablas.xlsx  # Datos legacy (Excel)
```

---

## 🗄️ Base de Datos

### Tablas de Referencia
- `peajes_local` - Peajes locales (TF/TV)
- `peajes_regas` - Peajes de regasificación
- `peajes_cargo` - Cargos ministeriales
- `peajes_transporte` - Peajes de transporte
- `peajes_multiplicadores` - Multiplicadores
- `conceptos_rules` - Reglas de validación

### Tablas de Auditoría
- `validaciones` - Registro de validaciones
- `conceptos_validados` - Detalle de conceptos

---

## 🔄 Migración desde Excel

Para cargar datos del Excel a Supabase automáticamente:

```bash
python migrate_excel_to_supabase.py
```

---

## 🛠️ Desarrollo

### Ejecutar en modo desarrollo

```bash
streamlit run app.py --logger.level=debug
```

### Probar conexión a Supabase

```python
import db
print(db.test_connection())
```

### Ver logs de la BD

```python
import db
tables = db.get_reference_tables()
print(tables['local'])
```

---

## 📦 Versiones

- **Python**: 3.10+
- **Streamlit**: 1.50.0
- **Pandas**: 2.2.3
- **Supabase**: Última

Ver `requirements.txt` para lista completa.

---

## 🔐 Seguridad

- ⚠️ Las credenciales de Supabase están en `.env` (NO incluir en Git)
- 🔒 Usa variables de entorno para SUPABASE_URL y SUPABASE_KEY
- 🔐 En producción, habilita Row Level Security (RLS) en Supabase

---

## 📝 Compilar a .exe (Windows)

```bash
pyinstaller --onefile --add-data="data:data" launcher_streamlit.py -n ValidadorFacturas
```

---

## 🆘 Solución de Problemas

| Problema | Solución |
|----------|----------|
| "SUPABASE_URL no encontrada" | Verifica `.env` y recarga terminal |
| "No se pudo conectar a Supabase" | Comprueba URL y KEY, intenta con Excel |
| "Tabla no encontrada" | Ejecuta `database_schema.sql` en Supabase |

Ver [SUPABASE_SETUP.md](./SUPABASE_SETUP.md) para más detalles.

---

## 📞 Contacto

- **Autor**: Sercomgas
- **Repositorio**: GitHub
- **Issues**: [GitHub Issues](https://github.com/Chris6995/comprobador_facturas_gas/issues)