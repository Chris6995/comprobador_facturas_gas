-- Politicas RLS para uso con clave anon en la app.
-- Ejecuta esto en Supabase SQL Editor si tienes RLS activado.

-- =========================
-- TABLAS DE REFERENCIA
-- =========================
ALTER TABLE public.peajes_local ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.peajes_regas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.peajes_cargo ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.peajes_transporte ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.peajes_multiplicadores ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conceptos_rules ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS peajes_local_select_anon ON public.peajes_local;
CREATE POLICY peajes_local_select_anon
ON public.peajes_local
FOR SELECT
TO anon, authenticated
USING (true);

DROP POLICY IF EXISTS peajes_regas_select_anon ON public.peajes_regas;
CREATE POLICY peajes_regas_select_anon
ON public.peajes_regas
FOR SELECT
TO anon, authenticated
USING (true);

DROP POLICY IF EXISTS peajes_cargo_select_anon ON public.peajes_cargo;
CREATE POLICY peajes_cargo_select_anon
ON public.peajes_cargo
FOR SELECT
TO anon, authenticated
USING (true);

DROP POLICY IF EXISTS peajes_transporte_select_anon ON public.peajes_transporte;
CREATE POLICY peajes_transporte_select_anon
ON public.peajes_transporte
FOR SELECT
TO anon, authenticated
USING (true);

DROP POLICY IF EXISTS peajes_multiplicadores_select_anon ON public.peajes_multiplicadores;
CREATE POLICY peajes_multiplicadores_select_anon
ON public.peajes_multiplicadores
FOR SELECT
TO anon, authenticated
USING (true);

DROP POLICY IF EXISTS conceptos_rules_select_anon ON public.conceptos_rules;
CREATE POLICY conceptos_rules_select_anon
ON public.conceptos_rules
FOR SELECT
TO anon, authenticated
USING (true);

-- =========================
-- TABLAS DE AUDITORIA
-- =========================
ALTER TABLE public.validaciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conceptos_validados ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS validaciones_insert_anon ON public.validaciones;
CREATE POLICY validaciones_insert_anon
ON public.validaciones
FOR INSERT
TO anon, authenticated
WITH CHECK (true);

DROP POLICY IF EXISTS validaciones_select_anon ON public.validaciones;
CREATE POLICY validaciones_select_anon
ON public.validaciones
FOR SELECT
TO anon, authenticated
USING (true);

DROP POLICY IF EXISTS conceptos_validados_insert_anon ON public.conceptos_validados;
CREATE POLICY conceptos_validados_insert_anon
ON public.conceptos_validados
FOR INSERT
TO anon, authenticated
WITH CHECK (true);

DROP POLICY IF EXISTS conceptos_validados_select_anon ON public.conceptos_validados;
CREATE POLICY conceptos_validados_select_anon
ON public.conceptos_validados
FOR SELECT
TO anon, authenticated
USING (true);
