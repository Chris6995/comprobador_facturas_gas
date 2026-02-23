-- ============================================
-- TABLAS DE REFERENCIA
-- ============================================

CREATE TABLE IF NOT EXISTS public.peajes_local (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  peaje VARCHAR(100) NOT NULL UNIQUE,
  tf NUMERIC(10, 6) NOT NULL,
  tv NUMERIC(10, 6) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON COLUMN public.peajes_local.tf IS 'Término Fijo';
COMMENT ON COLUMN public.peajes_local.tv IS 'Término Variable';

CREATE TABLE IF NOT EXISTS public.peajes_regas (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  peaje VARCHAR(100) NOT NULL UNIQUE,
  tf_regas NUMERIC(10, 6) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.peajes_cargo (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  peaje VARCHAR(100) NOT NULL UNIQUE,
  tf_cargo NUMERIC(10, 6) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.peajes_transporte (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  peaje VARCHAR(100),
  tf_transporte NUMERIC(10, 6) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.peajes_multiplicadores (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  peaje VARCHAR(100) NOT NULL UNIQUE,
  multiplicador NUMERIC(10, 6) NOT NULL DEFAULT 1.0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.conceptos_rules (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  cod_concepto VARCHAR(50) NOT NULL UNIQUE,
  descripcion VARCHAR(255),
  tabla_referencia VARCHAR(100),
  columna_referencia VARCHAR(100),
  requiere_validacion BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- TABLAS DE AUDITORIA Y RESULTADOS
-- ============================================

CREATE TABLE IF NOT EXISTS public.validaciones (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  cups VARCHAR(50) NOT NULL,
  tipopeaje VARCHAR(100),
  importetotal_xml NUMERIC(12, 2),
  n_conceptos INT,
  n_errors INT,
  status VARCHAR(20) CHECK (status IN ('OK', 'KO')),
  archivo_nombre VARCHAR(255),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.conceptos_validados (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  validacion_id BIGINT NOT NULL REFERENCES public.validaciones(id) ON DELETE CASCADE,
  cod_concepto VARCHAR(50),
  descripcion VARCHAR(255),
  unidad NUMERIC(12, 6),
  precunidad_xml NUMERIC(12, 6),
  precunidad_boe NUMERIC(12, 6),
  precio_ok BOOLEAN,
  importe_xml NUMERIC(12, 2),
  importe_calc NUMERIC(12, 2),
  importe_ok BOOLEAN,
  estado VARCHAR(20) CHECK (estado IN ('OK', 'ERROR', 'SIN_REGLA')),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDICES
-- ============================================

CREATE INDEX IF NOT EXISTS idx_validaciones_cups ON public.validaciones(cups);
CREATE INDEX IF NOT EXISTS idx_validaciones_created ON public.validaciones(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_conceptos_validados_validacion ON public.conceptos_validados(validacion_id);
CREATE INDEX IF NOT EXISTS idx_conceptos_rules_cod ON public.conceptos_rules(cod_concepto);

-- ============================================
-- updated_at auto (OPCIONAL, recomendado)
-- ============================================

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
BEGIN
  -- lista de tablas con updated_at
  IF EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_schema='public' AND table_name='peajes_local' AND column_name='updated_at') THEN
    CREATE TRIGGER trg_peajes_local_updated
    BEFORE UPDATE ON public.peajes_local
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
  END IF;
EXCEPTION WHEN duplicate_object THEN
  -- trigger ya existe
  NULL;
END$$;

-- Repite triggers si quieres para las demás tablas (peajes_regas, peajes_cargo, etc.)
