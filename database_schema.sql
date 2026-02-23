-- Script SQL para crear las tablas en Supabase
-- Estructura normalizada para el comprobador de facturas

-- ============================================
-- TABLAS DE REFERENCIA
-- ============================================

-- Tabla: peajes_local
-- Información de peajes locales (término fijo y variable)
CREATE TABLE IF NOT EXISTS peajes_local (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  peaje VARCHAR(100) NOT NULL UNIQUE,
  tf DECIMAL(10, 6) NOT NULL COMMENT 'Término Fijo',
  tv DECIMAL(10, 6) NOT NULL COMMENT 'Término Variable',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: peajes_regas
-- Información de peajes de regasificación
CREATE TABLE IF NOT EXISTS peajes_regas (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  peaje VARCHAR(100) NOT NULL UNIQUE,
  tf_regas DECIMAL(10, 6) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: peajes_cargo
-- Cargos ministeriales
CREATE TABLE IF NOT EXISTS peajes_cargo (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  peaje VARCHAR(100) NOT NULL UNIQUE,
  tf_cargo DECIMAL(10, 6) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: peajes_transporte
-- Información de peajes de transporte
CREATE TABLE IF NOT EXISTS peajes_transporte (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  peaje VARCHAR(100),
  tf_transporte DECIMAL(10, 6) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: peajes_multiplicadores
-- Multiplicadores para ajustes
CREATE TABLE IF NOT EXISTS peajes_multiplicadores (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  peaje VARCHAR(100) NOT NULL UNIQUE,
  multiplicador DECIMAL(10, 6) NOT NULL DEFAULT 1.0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: conceptos_rules
-- Reglas de validación para conceptos
CREATE TABLE IF NOT EXISTS conceptos_rules (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  cod_concepto VARCHAR(50) NOT NULL UNIQUE,
  descripcion VARCHAR(255),
  tabla_referencia VARCHAR(100),
  columna_referencia VARCHAR(100),
  requiere_validacion BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- TABLAS DE AUDITORIA Y RESULTADOS
-- ============================================

-- Tabla: validaciones
-- Registro de validaciones realizadas
CREATE TABLE IF NOT EXISTS validaciones (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  cups VARCHAR(50) NOT NULL,
  tipopeaje VARCHAR(100),
  importetotal_xml DECIMAL(12, 2),
  n_conceptos INT,
  n_errors INT,
  status VARCHAR(20) CHECK (status IN ('OK', 'KO')),
  archivo_nombre VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla: conceptos_validados
-- Detalle de conceptos de una validación
CREATE TABLE IF NOT EXISTS conceptos_validados (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  validacion_id BIGINT NOT NULL REFERENCES validaciones(id) ON DELETE CASCADE,
  cod_concepto VARCHAR(50),
  descripcion VARCHAR(255),
  unidad DECIMAL(12, 6),
  precunidad_xml DECIMAL(12, 6),
  precunidad_boe DECIMAL(12, 6),
  precio_ok BOOLEAN,
  importe_xml DECIMAL(12, 2),
  importe_calc DECIMAL(12, 2),
  importe_ok BOOLEAN,
  estado VARCHAR(20) CHECK (estado IN ('OK', 'ERROR', 'SIN_REGLA')),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- INDICES PARA OPTIMIZACIÓN
-- ============================================

CREATE INDEX IF NOT EXISTS idx_validaciones_cups ON validaciones(cups);
CREATE INDEX IF NOT EXISTS idx_validaciones_created ON validaciones(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conceptos_validados_validacion ON conceptos_validados(validacion_id);
CREATE INDEX IF NOT EXISTS idx_conceptos_rules_cod ON conceptos_rules(cod_concepto);

-- ============================================
-- DATOS DE EJEMPLO (OPCIONAL)
-- ============================================

-- Si necesitas cargar datos de prueba, descomenta lo siguiente:
/*
INSERT INTO peajes_local (peaje, tf, tv) VALUES
  ('NEDGIA', 0.01, 0.005),
  ('SEPIOL', 0.012, 0.006);

INSERT INTO conceptos_rules (cod_concepto, descripcion, tabla_referencia) VALUES
  ('2000', 'Término Variable Local', 'peajes_local'),
  ('2002', 'Término Fijo Local', 'peajes_local'),
  ('2006', 'Transporte', 'peajes_transporte'),
  ('2009', 'Regasificación', 'peajes_regas'),
  ('2011', 'Cargo Ministerio', 'peajes_cargo');
*/
