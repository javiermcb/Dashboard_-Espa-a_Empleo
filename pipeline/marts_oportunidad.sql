-- mart_oportunidad_ccaa: demandantes de empleo (y los menores de 25) y contratos del SEPE, por comunidad y mes.
-- Se crea desde modelo.py solo si existen las dos tablas del SEPE (DuckDB valida las tablas al crear una vista).
-- Los valores ocultos por secreto estadístico del SEPE ('<5') van vacíos en origen: las sumas pueden quedarse algo cortas.
CREATE OR REPLACE VIEW mart_oportunidad_ccaa AS
WITH d AS (
    SELECT fecha, ccaa_id AS territorio_id, sum(total_dtes_empleo) AS demandantes,
           sum(coalesce(dtes_empleo_hombre_edad_25, 0) + coalesce(dtes_empleo_mujer_edad_25, 0)) AS demandantes_menores_25
    FROM fact_sepe_demandantes_municipio WHERE ccaa_id IS NOT NULL GROUP BY 1, 2),
c AS (
    SELECT fecha, ccaa_id AS territorio_id, sum(total_contratos) AS contratos
    FROM fact_sepe_contratos_municipio WHERE ccaa_id IS NOT NULL GROUP BY 1, 2)
SELECT d.fecha, d.territorio_id, d.demandantes, d.demandantes_menores_25, c.contratos
FROM d LEFT JOIN c USING (fecha, territorio_id);
