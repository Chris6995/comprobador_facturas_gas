# Integración con Supabase

## 📋 Descripción

La aplicación usa Supabase como fuente única de datos de referencia. Esto permite:

- ✅ Actualizar datos sin modificar archivos
- ✅ Historial de validaciones
- ✅ Mejor escalabilidad

---

## 🚀 Configuración Rápida

### 1. Crear las tablas en Supabase

1. Accede a tu proyecto Supabase: https://app.supabase.com
2. Ve a "SQL Editor"
3. Crea una nueva query y copia el contenido de `sql/database_schema.sql`
4. Ejecuta el script

**Las siguientes tablas se crearán:**

#### Tablas de Referencia:
- `peajes_local` - Peajes locales (TF, TV)
- `peajes_regas` - Peajes de regasificación
- `peajes_cargo` - Cargos ministeriales
- `peajes_transporte` - Peajes de transporte
- `peajes_multiplicadores` - Multiplicadores
- `conceptos_rules` - Reglas de validación

#### Tablas de Auditoría:
- `validaciones` - Registro de validaciones realizadas
- `conceptos_validados` - Detalle de conceptos por validación

---

### 2. Cargar datos de referencia

Carga tus datos de referencia en las tablas de Supabase (manual o scripts propios), por ejemplo:

```bash
# En el editor SQL de Supabase, ejecuta:
INSERT INTO peajes_local (peaje, tf, tv) VALUES
  ('NEDGIA', 0.01, 0.005),
  ('SEPIOL', 0.012, 0.006);

INSERT INTO conceptos_rules (cod_concepto, descripcion, tabla_referencia) VALUES
  ('2000', 'Término Variable Local', 'peajes_local'),
  ('2002', 'Término Fijo Local', 'peajes_local'),
  ('2006', 'Transporte', 'peajes_transporte'),
  ('2009', 'Regasificación', 'peajes_regas'),
  ('2011', 'Cargo Ministerio', 'peajes_cargo');
```

---

### 3. Verificar la conexión

La app verifica automáticamente la conexión al inicio. Si funciona:

```
✅ Conectado a Supabase
```

Si falla:

```
❌ No se pudo conectar a Supabase.
```

---

## 📦 Archivos Nuevos

### `src/comprobador/infra/supabase_client.py`
Módulo de conexión y operaciones con Supabase:
- `get_reference_tables()` - Carga todas las tablas
- `get_peaje_by_type()` - Obtiene un peaje específico
- `insert_validation_result()` - Inserta resultados
- `test_connection()` - Prueba la conexión

### `sql/database_schema.sql`
Script SQL para crear todas las tablas. Ejecutar en Supabase SQL Editor.

### `.env` (actualizado)
```
SUPABASE_URL=https://wiqtbpvjydzpqluvnduh.supabase.co
SUPABASE_KEY=...
```

---

## 🔄 Cambios en el Backend

### `src/comprobador/core/validation.py`
- `load_reference_tables()` lee desde Supabase
- `validate_invoice()` valida contra tablas en BD

### `src/comprobador/ui/streamlit_app.py`
- Verifica conexión a Supabase al iniciar
- Detiene la app si no hay conexión

---

## 🐛 Solución de Problemas

### "Error: SUPABASE_URL y SUPABASE_KEY no están definidas"
- Verifica que `.env` contenga las credenciales
- Recarga la terminal: `source .venv/bin/activate`

### "Error al conectar a Supabase"
- Verifica URL y KEY en `.env`
- Comprueba conectividad a internet

### "Tabla no encontrada"
- Verifica que hayas ejecutado el SQL de `sql/database_schema.sql`
- Lista las tablas en Supabase: SQL Editor → `SELECT * FROM information_schema.tables WHERE table_schema = 'public';`

---

## 📝 Próximos Pasos

1. ✅ Ejecutar `sql/database_schema.sql` en Supabase
2. ✅ Cargar datos de referencia (peajes, conceptos, etc.)
3. ✅ Probar la validación con XML de ejemplo

---

## 🔐 Seguridad

⚠️ **Importante**: 
- Las credenciales están en `.env` (NO incluido en Git)
- Nunca compartas la `SUPABASE_KEY` en público
- Usa RLS (Row Level Security) en Supabase para producción

---

## 📞 Soporte

Para más información sobre Supabase:
- Docs: https://supabase.com/docs
- Dashboard: https://app.supabase.com
