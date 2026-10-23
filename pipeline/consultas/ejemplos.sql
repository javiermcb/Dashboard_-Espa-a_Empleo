-- Consultas puntuales sobre el modelo RRHH 360 con DuckDB (https://duckdb.org, gratuito).
--
-- Opción A, fichero local (artefacto del workflow o ejecución propia):   duckdb datos/rrhh.duckdb
-- Opción B, directamente desde el repositorio público, sin descargar nada:
--   duckdb
--   INSTALL httpfs; LOAD httpfs;
--   CREATE VIEW mart_coste_laboral AS SELECT * FROM 'https://raw.githubusercontent.com/javiermcb/datos-rrhh-publicos/main/modelo/marts/mart_coste_laboral.parquet';
--   (igual para cada tabla que se quiera consultar)

-- 1. Coste laboral total por trabajador y mes, último trimestre, por CCAA (mayor a menor)
SELECT t.nombre AS ccaa, c.fecha, round(c.euros) AS euros_trabajador_mes
FROM mart_coste_laboral c JOIN dim_territorio t USING (territorio_id)
WHERE c.componente = 'Coste laboral total' AND c.base = 'Por trabajador y mes'
  AND c.sector LIKE 'Industria, construcción y servicios%' AND t.nivel = 'CCAA'
  AND c.fecha = (SELECT max(fecha) FROM mart_coste_laboral)
ORDER BY euros_trabajador_mes DESC;

-- 2. % de horas no trabajadas sobre pactadas por CCAA, evolución anual (proxy de absentismo)
SELECT t.nombre AS ccaa, year(h.fecha) AS anyo,
       round(100 * sum(h.horas_trabajador_mes) FILTER (WHERE concepto = 'Horas no trabajadas')
                 / sum(h.horas_trabajador_mes) FILTER (WHERE concepto = 'Horas pactadas'), 2) AS pct_no_trabajadas
FROM mart_tiempo_trabajo h JOIN dim_territorio t USING (territorio_id)
WHERE h.jornada = 'Ambas jornadas' AND h.sector LIKE 'Industria, construcción y servicios%' AND t.nivel = 'CCAA'
GROUP BY ALL ORDER BY ccaa, anyo;

-- 3. Salario EES 2022 por gran grupo de ocupación: mediana de hombres y mujeres y brecha
SELECT ocupacion,
       max(euros) FILTER (WHERE sexo = 'Hombres') AS mediana_hombres,
       max(euros) FILTER (WHERE sexo = 'Mujeres') AS mediana_mujeres,
       round(100 * (1 - max(euros) FILTER (WHERE sexo = 'Mujeres') / max(euros) FILTER (WHERE sexo = 'Hombres')), 1) AS brecha_pct
FROM mart_salarios_ees
WHERE anyo = 2022 AND estadistico = 'Mediana' AND territorio_id = 'N00' AND ocupacion IS NOT NULL
GROUP BY ocupacion ORDER BY mediana_hombres DESC;

-- 4. Provincias donde más ha subido el paro EPA en el último año
WITH p AS (SELECT fecha, territorio_id, miles_personas FROM mart_poblacion_actividad
           WHERE situacion = 'Parados' AND sexo = 'Ambos sexos' AND territorio_id LIKE 'P%')
SELECT t.nombre, a.fecha, a.miles_personas AS parados_miles,
       round(100 * (a.miles_personas / b.miles_personas - 1), 1) AS var_interanual_pct
FROM p a JOIN p b ON b.territorio_id = a.territorio_id AND b.fecha = a.fecha - INTERVAL 1 YEAR
JOIN dim_territorio t USING (territorio_id)
WHERE a.fecha = (SELECT max(fecha) FROM p)
ORDER BY var_interanual_pct DESC LIMIT 10;

-- 5. Contratos de puesta a disposición por sección CNAE: acumulado del año frente al año anterior
WITH u AS (SELECT year(max(fecha)) AS a, month(max(fecha)) AS m FROM fact_cpd_actividad)
SELECT seccion_cnae, seccion_nombre,
       sum(cpd) FILTER (WHERE year(fecha) = u.a) AS cpd_anyo,
       sum(cpd) FILTER (WHERE year(fecha) = u.a - 1) AS cpd_anyo_anterior,
       round(100 * (sum(cpd) FILTER (WHERE year(fecha) = u.a) / sum(cpd) FILTER (WHERE year(fecha) = u.a - 1) - 1), 1) AS var_pct
FROM fact_cpd_actividad, u WHERE month(fecha) <= u.m
GROUP BY ALL ORDER BY cpd_anyo DESC;

-- 6. Subida salarial pactada en convenios frente al IPC, por año
SELECT c.anyo_efectos, c.variacion_salarial_pactada_pct AS pactada,
       round(avg(p.valor) FILTER (WHERE month(p.fecha) = 12), 2) AS ipc_diciembre
FROM fact_convenios c
LEFT JOIN mart_precios p ON year(p.fecha) = c.anyo_efectos AND p.indice = 'IPC'
     AND p.indicador = 'Variación anual' AND p.territorio_id = 'N00'
WHERE c.tipo_dato IN ('Año completo', 'Año (provisional)')
GROUP BY ALL ORDER BY c.anyo_efectos;

-- 7. Municipios de una provincia: paro registrado y contratos del último mes (ej.: Madrid, P28)
SELECT t.nombre AS municipio, p.fecha, p.total_paro_registrado, c.total_contratos
FROM fact_sepe_paro_municipio p
JOIN fact_sepe_contratos_municipio c USING (fecha, territorio_id)
JOIN dim_territorio t USING (territorio_id)
WHERE p.provincia_id = 'P28' AND p.fecha = (SELECT max(fecha) FROM fact_sepe_paro_municipio)
ORDER BY p.total_paro_registrado DESC LIMIT 20;

-- 8. Afiliación media por provincia y sección CNAE (último mes, total de regímenes)
SELECT t.nombre AS provincia, a.seccion_cnae, round(a.afiliados) AS afiliados
FROM fact_ss_afiliacion a JOIN dim_territorio t USING (territorio_id)
WHERE a.consulta = 'afil_medios_prov_cnae09_regimen' AND a.regimen LIKE 'Total%'
  AND a.seccion_cnae <> 'TODAS LAS SECCIONES' AND t.nivel = 'Provincia'
  AND a.fecha = (SELECT max(fecha) FROM fact_ss_afiliacion WHERE consulta = 'afil_medios_prov_cnae09_regimen')
ORDER BY provincia, afiliados DESC;

-- 9. Qué tablas del INE hay y hasta qué periodo llegan
SELECT punto_nombre, tabla_id, tema, fecha_max FROM dim_tabla ORDER BY punto, tabla_id;
