# Comprobador de Facturas de Gas - Sercomgas

Aplicación web para validar facturas XML contra tablas de referencia de peajes y conceptos.

## 🚀 Características

- ✅ Validación de facturas XML (SCTD B7031)
- ✅ Consulta de tarificación BOE en **Supabase** (base de datos)
- ✅ Historial de validaciones
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

Lee [SUPABASE_SETUP.md](./docs/SUPABASE_SETUP.md) para:
- Crear las tablas en Supabase
- Verificar la conexión

### 4. Ejecutar aplicación

```bash
streamlit run app.py
```

Se abrirá en `http://localhost:8501`

---

## 📁 Estructura de Archivos

```
├── app.py                                # Entrypoint Streamlit (wrapper)
├── backend.py                            # Wrapper de compatibilidad
├── db.py                                 # Wrapper de compatibilidad
├── src/comprobador/
│   ├── core/validation.py                # Lógica de validación
│   ├── infra/supabase_client.py          # Integración con Supabase
│   └── ui/streamlit_app.py               # Interfaz Streamlit
├── scripts/
│   └── launcher_streamlit.py             # Entry point para EXE
├── sql/database_schema.sql               # SQL para crear tablas
├── docs/SUPABASE_SETUP.md                # Guía de configuración
└── requirements.txt                      # Dependencias Python
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
pyinstaller --onefile --add-data="data:data" scripts/launcher_streamlit.py -n ValidadorFacturas
```

---

## 🆘 Solución de Problemas

| Problema | Solución |
|----------|----------|
| "SUPABASE_URL no encontrada" | Verifica `.env` y recarga terminal |
| "No se pudo conectar a Supabase" | Comprueba URL y KEY |
| "Tabla no encontrada" | Ejecuta `sql/database_schema.sql` en Supabase |

Ver [SUPABASE_SETUP.md](./docs/SUPABASE_SETUP.md) para más detalles.

---

## 📞 Contacto

- **Autor**: Sercomgas
- **Repositorio**: GitHub
- **Issues**: [GitHub Issues](https://github.com/Chris6995/comprobador_facturas_gas/issues)
