-- pipeline/marts.sql — Tablas listas para explotar (una por tema), construidas sobre fact_ine.
-- Las ejecuta pipeline/modelo.py después de crear fact_ine; cada vista se exporta a datos/modelo/marts/<nombre>.parquet|csv.
-- Los filtros usan los valores reales vistos en resultados/pipeline/catalogo_series.csv.
-- Todas comparten territorio_id (-> dim_territorio) y fecha (-> dim_tiempo).

-- Quita de 'medida' las etiquetas genéricas y deja el concepto (p. ej. 'Coste laboral total', 'Horas no trabajadas')
CREATE OR REPLACE MACRO concepto(m) AS array_to_string(list_filter(string_split(m, ' · '), x -> x NOT IN (
    'Costes laborales', 'Euros', 'Número de Horas', 'Tiempo de trabajo', 'Dato base', 'Salario medio',
    'Salario bruto mensual del empleo principal')), ' · ');

-- 1. BENCHMARK SALARIAL ---------------------------------------------------------------------------------------
-- EES (2018 y 2022): ganancia por sexo y gran grupo de ocupación, media y percentiles
CREATE OR REPLACE VIEW mart_salarios_ees AS
SELECT anyo, fecha, territorio_id, sexo, ocupacion, ocupacion_codigo,
       coalesce(nullif(estadistico, ''), CASE WHEN medida LIKE '%Media%' THEN 'Media' END) AS estadistico,
       valor AS euros, tabla_id
FROM fact_ine WHERE tabla_id IN ('36846', '70688') AND valor IS NOT NULL;

-- EAES (anual): ganancia por sexo y CCAA, media y percentiles
CREATE OR REPLACE VIEW mart_salarios_eaes AS
SELECT anyo, fecha, territorio_id, sexo,
       coalesce(nullif(estadistico, ''), CASE WHEN medida LIKE '%Media%' THEN 'Media' END) AS estadistico,
       valor AS euros, tabla_id
FROM fact_ine WHERE tabla_id = '28191' AND valor IS NOT NULL;

-- EPA: salario medio mensual por decil (sexo, CCAA, ocupación)
CREATE OR REPLACE VIEW mart_deciles_epa AS
SELECT anyo, fecha, territorio_id,
       CASE tabla_id WHEN '66238' THEN 'Sexo' WHEN '66241' THEN 'Comunidad autónoma' WHEN '66244' THEN 'Ocupación' END AS desglose,
       coalesce(sexo, 'Total') AS sexo, coalesce(ocupacion, 'Total') AS ocupacion, jornada,
       estadistico AS decil, TRY_CAST(estadistico AS INTEGER) AS decil_num,
       valor AS salario_medio_mensual, tabla_id
FROM fact_ine WHERE tabla_id IN ('66238', '66241', '66244') AND valor IS NOT NULL;

-- EPA: límite inferior y media de cada decil (nacional)
CREATE OR REPLACE VIEW mart_limites_deciles AS
SELECT anyo, fecha, territorio_id, TRY_CAST(estadistico AS INTEGER) AS decil,
       max(valor) FILTER (WHERE concepto(medida) = 'Límite inferior') AS limite_inferior,
       max(valor) FILTER (WHERE concepto(medida) = 'Media') AS media
FROM fact_ine WHERE tabla_id = '66252' GROUP BY ALL;

-- 2. COSTE LABORAL Y ABSENTISMO ----------------------------------------------------------------------------------
-- ETCL: coste laboral por trabajador y mes y por hora efectiva, por componente
CREATE OR REPLACE VIEW mart_coste_laboral AS
SELECT fecha, anyo, periodo, territorio_id, actividad AS sector, concepto(medida) AS componente,
       CASE tabla_id WHEN '6061' THEN 'Por trabajador y mes' ELSE 'Por hora efectiva' END AS base,
       valor AS euros, tabla_id
FROM fact_ine WHERE tabla_id IN ('6061', '6062') AND valor IS NOT NULL;

-- ETCL: horas por trabajador y mes (pactadas, pagadas, efectivas, extras, no trabajadas)
CREATE OR REPLACE VIEW mart_tiempo_trabajo AS
SELECT fecha, anyo, periodo, territorio_id, actividad AS sector, jornada, concepto(medida) AS concepto,
       valor AS horas_trabajador_mes, tabla_id
FROM fact_ine WHERE tabla_id = '6063' AND valor IS NOT NULL;

-- ETCL: percepciones por día de incapacidad temporal y coste de indemnización por despido, por actividad
CREATE OR REPLACE VIEW mart_it_despido AS
SELECT fecha, anyo, periodo, territorio_id, actividad, concepto(medida) AS concepto, valor AS euros, tabla_id
FROM fact_ine WHERE tabla_id = '6056' AND valor IS NOT NULL;

-- ETCL: vacantes
CREATE OR REPLACE VIEW mart_vacantes AS
SELECT fecha, anyo, periodo, territorio_id, valor AS vacantes, tabla_id
FROM fact_ine WHERE tabla_id = '6064' AND valor IS NOT NULL;

-- 3. MERCADO DE TALENTO --------------------------------------------------------------------------------------------
-- EPA por provincia: activos, ocupados, parados, inactivos (miles de personas)
CREATE OR REPLACE VIEW mart_poblacion_actividad AS
SELECT fecha, anyo, periodo, territorio_id, sexo, situacion, valor AS miles_personas, tabla_id
FROM fact_ine WHERE tabla_id = '65345' AND valor IS NOT NULL;

-- EPA por provincia: ocupados por sector (miles)
CREATE OR REPLACE VIEW mart_ocupados_sector AS
SELECT fecha, anyo, periodo, territorio_id, actividad AS sector, valor AS miles_ocupados, tabla_id
FROM fact_ine WHERE tabla_id = '65354' AND valor IS NOT NULL;

-- EPA por CCAA: tasas de empleo y paro por sexo y edad (anual)
CREATE OR REPLACE VIEW mart_tasas_epa AS
SELECT anyo, fecha, territorio_id, sexo, edad,
       CASE tabla_id WHEN '66031' THEN 'Tasa de empleo' ELSE 'Tasa de paro' END AS indicador,
       valor AS tasa, tabla_id
FROM fact_ine WHERE tabla_id IN ('66031', '66055') AND valor IS NOT NULL;

-- EFPA: flujos entre trimestres (miles de personas)
CREATE OR REPLACE VIEW mart_flujos AS
SELECT fecha, anyo, periodo, territorio_id,
       trim(replace(list_filter(string_split(situacion, ' · '), x -> x LIKE '%(trimestre actual)')[1], '(trimestre actual)', '')) AS situacion_actual,
       trim(replace(list_filter(string_split(situacion, ' · '), x -> x LIKE '%(trimestre anterior)')[1], '(trimestre anterior)', '')) AS situacion_anterior,
       valor AS miles_personas, tabla_id
FROM fact_ine WHERE tabla_id = '66266' AND valor IS NOT NULL;

-- 4. REVISIÓN SALARIAL --------------------------------------------------------------------------------------------
-- IPC (mensual) e IPT (anual) en una tabla: indicador + valor
CREATE OR REPLACE VIEW mart_precios AS
SELECT fecha, anyo, periodo, territorio_id,
       CASE WHEN tabla_id IN ('76134', '76140') THEN 'IPC' ELSE 'IPT' END AS indice,
       medida AS indicador, coalesce(ocupacion, 'Total') AS ocupacion, valor, unidad, tabla_id
FROM fact_ine WHERE tabla_id IN ('76134', '76140', '37630', '37624') AND valor IS NOT NULL;

-- 5. IGUALDAD -----------------------------------------------------------------------------------------------------
-- Brecha salarial de género no ajustada (% por hora), por edad o por jornada
CREATE OR REPLACE VIEW mart_brecha_genero AS
SELECT anyo, fecha, territorio_id,
       CASE tabla_id WHEN '10888' THEN 'Edad' ELSE 'Jornada' END AS desglose,
       coalesce(edad, jornada) AS categoria, valor AS brecha_pct, tabla_id
FROM fact_ine WHERE tabla_id IN ('10888', '10891') AND valor IS NOT NULL;

-- 6. CONTEXTO DE MERCADO ------------------------------------------------------------------------------------------
-- DIRCE: empresas por provincia y estrato de asalariados
CREATE OR REPLACE VIEW mart_empresas AS
SELECT anyo, fecha, territorio_id, tamano_empresa AS estrato_asalariados, valor AS empresas, tabla_id
FROM fact_ine WHERE tabla_id = '39374' AND valor IS NOT NULL;

-- 7. AMPLIACIÓN (iteración 3) -----------------------------------------------------------------------------------
-- Valor de una variable guardada en 'detalle' ("Variable: valor | Variable: valor")
CREATE OR REPLACE MACRO det(d, v) AS nullif(trim(regexp_extract(d, v || '[^:|]*: ([^|]+)', 1)), '');

-- ETCL por sección CNAE: horas pactadas, efectivas, no trabajadas (total, por IT, por vacaciones y fiestas), extras
CREATE OR REPLACE VIEW mart_tiempo_trabajo_actividad AS
SELECT fecha, anyo, periodo, territorio_id, actividad, actividad_codigo, jornada, concepto(medida) AS concepto,
       valor AS horas_trabajador_mes, tabla_id
FROM fact_ine WHERE tabla_id = '6043' AND valor IS NOT NULL;

-- ETCL por sección CNAE: coste laboral por trabajador y mes, por componente (salarial, cotizaciones, despido…)
CREATE OR REPLACE VIEW mart_coste_actividad AS
SELECT fecha, anyo, periodo, territorio_id, actividad, actividad_codigo, concepto(medida) AS componente,
       valor AS euros_trabajador_mes, tabla_id
FROM fact_ine WHERE tabla_id = '6032' AND valor IS NOT NULL AND coalesce(tamano_empresa, 'Total') = 'Total';

-- ETCL: vacantes por sección CNAE
CREATE OR REPLACE VIEW mart_vacantes_actividad AS
SELECT fecha, anyo, periodo, territorio_id, actividad, actividad_codigo, valor AS vacantes, tabla_id
FROM fact_ine WHERE tabla_id = '6048' AND valor IS NOT NULL;

-- EPA: asalariados contratados a través de una ETT (miles de personas), por sexo y CCAA
CREATE OR REPLACE VIEW mart_epa_ett AS
SELECT anyo, fecha, territorio_id, sexo, det(detalle, 'Contratado a través de una empresa de trabajo temporal') AS contratado_ett,
       valor AS miles_asalariados, tabla_id
FROM fact_ine WHERE tabla_id = '65805' AND valor IS NOT NULL;

-- EPA: asalariados temporales por motivo (miles), por sexo y CCAA
CREATE OR REPLACE VIEW mart_temporalidad_motivo AS
SELECT anyo, fecha, territorio_id, sexo, det(detalle, 'Motivo de tener un contrato') AS motivo,
       valor AS miles_asalariados, tabla_id
FROM fact_ine WHERE tabla_id = '65809' AND valor IS NOT NULL;

-- EPA: asalariados según hagan horas extra (miles), por sexo y sección CNAE
CREATE OR REPLACE VIEW mart_horas_extra AS
SELECT fecha, anyo, periodo, territorio_id, sexo, coalesce(actividad, 'Total') AS actividad, actividad_codigo,
       det(detalle, 'Realizan o no, horas extraordinarias') AS horas_extra, valor AS miles_asalariados, tabla_id
FROM fact_ine WHERE tabla_id = '65212' AND valor IS NOT NULL;

-- EPA: ocupados por CCAA, sexo, edad y sector (miles)
CREATE OR REPLACE VIEW mart_ocupados_ccaa AS
SELECT fecha, anyo, periodo, territorio_id, sexo, coalesce(edad, 'Total') AS edad, coalesce(actividad, 'Total') AS sector,
       valor AS miles_ocupados, tabla_id
FROM fact_ine WHERE tabla_id = '65304' AND valor IS NOT NULL;

-- EPA: ocupados según los días que trabajan desde casa (% de ocupados), por sexo y CCAA
CREATE OR REPLACE VIEW mart_teletrabajo AS
SELECT anyo, fecha, territorio_id, sexo, det(detalle, 'Días trabajados en el domicilio') AS frecuencia,
       valor AS pct_ocupados, tabla_id
FROM fact_ine WHERE tabla_id = '65776' AND valor IS NOT NULL;

-- EES 2022: salario medio bruto anual por CCAA, sexo y sector, según tipo de contrato o antigüedad
CREATE OR REPLACE VIEW mart_salarios_ees_detalle AS
SELECT anyo, fecha, territorio_id, sexo, coalesce(actividad, 'Total') AS sector,
       CASE tabla_id WHEN '36858' THEN 'Tipo de contrato' ELSE 'Antigüedad' END AS desglose,
       coalesce(det(detalle, 'Tipo de contrato'), det(detalle, 'Antigüedad en el empleo')) AS categoria,
       valor AS euros_anuales, tabla_id
FROM fact_ine WHERE tabla_id IN ('36858', '36861') AND valor IS NOT NULL;

-- 8. JÓVENES NEET (ni estudian ni trabajan), anual, % ---------------------------------------------------------
-- 62285 por CCAA, 59513 por sexo y 59514 por nacionalidad (15-29 años), 49508 por sexo (15-24, indicador ODS 8.6.1.1).
-- La tabla 62285 trae la CCAA solo en el nombre de la serie: se resuelve por nombre contra dim_territorio.
CREATE OR REPLACE MACRO sin_acentos(x) AS regexp_replace(lower(strip_accents(x)), '[^a-z]', '', 'g');
CREATE OR REPLACE VIEW mart_neet AS
SELECT f.anyo, f.fecha,
       CASE WHEN f.tabla_id = '62285' THEN t.territorio_id ELSE 'N00' END AS territorio_id,
       CASE f.tabla_id WHEN '62285' THEN 'Comunidad autónoma' WHEN '59514' THEN 'Nacionalidad' ELSE 'Sexo' END AS desglose,
       CASE WHEN f.tabla_id = '62285' THEN 'Total' ELSE f.serie_nombre END AS categoria,
       CASE f.tabla_id WHEN '49508' THEN '15-24' ELSE '15-29' END AS grupo_edad,
       f.valor AS porcentaje, f.tabla_id
FROM fact_ine f
LEFT JOIN dim_territorio t ON f.tabla_id = '62285' AND t.nivel IN ('Nacional', 'CCAA') AND sin_acentos(t.nombre) = sin_acentos(f.serie_nombre)
WHERE f.tabla_id IN ('62285', '59513', '59514', '49508') AND f.valor IS NOT NULL;
