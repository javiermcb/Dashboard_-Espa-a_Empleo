-- mart_sectores_empleo: afiliados medios a la Seguridad Social por sección CNAE (todas las edades, total España, RG + autónomos),
-- por año completo, con la variación frente al año anterior. Solo años con los 12 meses. Se crea desde modelo.py si existe fact_ss_afiliacion.
-- Lleva `fecha` (1 de enero del año) porque modelo.py resume todos los marts por fecha_min / fecha_max.
-- Usa la consulta CNAE 2009 (hasta 2025); la de 2026 usa CNAE 2025 y no es comparable sección a sección.
CREATE OR REPLACE VIEW mart_sectores_empleo AS
WITH m AS (
    SELECT year(fecha) AS anyo, seccion_cnae, avg(afiliados) AS afiliados, count(DISTINCT fecha) AS meses
    FROM fact_ss_afiliacion
    WHERE territorio_id = 'N00' AND consulta = 'afil_medios_prov_cnae09_regimen' AND regimen LIKE 'Total Reg%'
      AND seccion_cnae IS NOT NULL
    GROUP BY 1, 2)
SELECT make_date(a.anyo::INTEGER, 1, 1) AS fecha, a.anyo, a.seccion_cnae, a.afiliados, a.afiliados - b.afiliados AS variacion, (a.afiliados / b.afiliados - 1) * 100 AS variacion_pct
FROM m a LEFT JOIN m b ON b.seccion_cnae = a.seccion_cnae AND b.anyo = a.anyo - 1 AND b.meses = 12
WHERE a.meses = 12;
