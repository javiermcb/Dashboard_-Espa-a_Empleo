#!/usr/bin/env python3
"""
pipeline/modelo.py — Construye el modelo en estrella a partir de la capa normalizada (DuckDB).

Entradas:  datos/normalizado/ine_valores.csv, ine_series_dims.csv, datos/qa/ine_carga.csv
           pipeline/config/dimensiones.csv (variable del INE -> dimensión común), territorio.csv, tablas_ine.csv
Salidas:   datos/modelo/fact_ine.parquet        una fila por dato, con las dimensiones comunes ya resueltas
           datos/modelo/dim_tabla.parquet       qué es cada tabla, a qué punto de RRHH sirve y qué periodos tiene
           datos/modelo/dim_territorio.parquet  nacional / CCAA / provincia con códigos INE
           datos/modelo/dim_tiempo.parquet      calendario diario
           (y los mismos en .csv) · datos/rrhh.duckdb para consultas SQL
QA:        datos/qa/variables_sin_mapear.csv, territorio_sin_resolver.csv, resumen_modelo.csv

Uso:  python pipeline/modelo.py      (requiere: pip install duckdb)
"""
import csv, re, sys
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
CFG = RAIZ / "pipeline" / "config"
DATOS = RAIZ / "datos"
NORM, MODELO, QA = DATOS / "normalizado", DATOS / "modelo", DATOS / "qa"
CATALOGO_INE = RAIZ / "resultados" / "exploracion" / "tablas_operaciones.csv"


def leer(p):
    with open(p, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))


def main():
    MODELO.mkdir(parents=True, exist_ok=True); QA.mkdir(parents=True, exist_ok=True)
    db_path = DATOS / "rrhh.duckdb"
    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))

    con.execute(f"""CREATE TABLE valores AS SELECT * FROM read_csv('{NORM / "ine_valores.csv"}', header=true, all_varchar=true)""")
    con.execute(f"""CREATE TABLE series_dims AS SELECT * FROM read_csv('{NORM / "ine_series_dims.csv"}', header=true, all_varchar=true)""")

    # 1) variable del INE -> dimensión común (primera regla que encaje, en el orden de dimensiones.csv)
    reglas = [(r["dimension"], re.compile(r["regex_variable"], re.I)) for r in leer(CFG / "dimensiones.csv")]
    variables = [v for (v,) in con.execute("SELECT DISTINCT variable FROM series_dims").fetchall()]
    mapa = [(v, next((d for d, rx in reglas if rx.search(v or "")), "otra")) for v in variables]
    con.execute("CREATE TABLE mapa_variables(variable VARCHAR, dimension VARCHAR)")
    con.executemany("INSERT INTO mapa_variables VALUES (?, ?)", mapa)

    con.execute(f"""CREATE TABLE dim_territorio AS SELECT * FROM read_csv('{CFG / "territorio.csv"}', header=true, delim=';', all_varchar=true)""")

    # 2) atributos de cada serie: una columna por dimensión común; lo que no encaja va a 'detalle'
    con.execute("""
    CREATE TABLE serie_attr AS
    WITH d AS (
        SELECT s.*, m.dimension FROM series_dims s JOIN mapa_variables m USING (variable)
    ), terr AS (
        SELECT tabla_id, serie_cod,
               first(variable) AS terr_variable, first(codigo) AS terr_codigo, first(nombre) AS terr_nombre
        FROM d WHERE dimension = 'territorio' GROUP BY ALL
    )
    SELECT d.tabla_id, d.serie_cod,
        string_agg(nombre, ' · ' ORDER BY variable, nombre) FILTER (WHERE dimension = 'medida')       AS medida,
        string_agg(nombre, ' · ' ORDER BY variable, nombre) FILTER (WHERE dimension = 'sexo')         AS sexo,
        string_agg(nombre, ' · ' ORDER BY variable, nombre) FILTER (WHERE dimension = 'situacion')    AS situacion,
        string_agg(nombre, ' · ' ORDER BY variable, nombre) FILTER (WHERE dimension = 'jornada')      AS jornada,
        string_agg(nombre, ' · ' ORDER BY variable, nombre) FILTER (WHERE dimension = 'tamano_empresa') AS tamano_empresa,
        string_agg(nombre, ' · ' ORDER BY variable, nombre) FILTER (WHERE dimension = 'estadistico')  AS estadistico,
        string_agg(nombre, ' · ' ORDER BY variable, nombre) FILTER (WHERE dimension = 'edad')         AS edad,
        string_agg(nombre, ' · ' ORDER BY variable, nombre) FILTER (WHERE dimension = 'actividad')    AS actividad,
        string_agg(codigo, ' · ' ORDER BY variable, codigo) FILTER (WHERE dimension = 'actividad' AND codigo <> '') AS actividad_codigo,
        string_agg(nombre, ' · ' ORDER BY variable, nombre) FILTER (WHERE dimension = 'ocupacion')    AS ocupacion,
        string_agg(codigo, ' · ' ORDER BY variable, codigo) FILTER (WHERE dimension = 'ocupacion' AND codigo <> '') AS ocupacion_codigo,
        string_agg(nombre, ' · ' ORDER BY variable, nombre) FILTER (WHERE dimension = 'nacionalidad') AS nacionalidad,
        string_agg(nombre, ' · ' ORDER BY variable, nombre) FILTER (WHERE dimension = 'formacion')    AS formacion,
        string_agg(variable || ': ' || nombre, ' | ' ORDER BY variable) FILTER (WHERE dimension = 'otra') AS detalle,
        any_value(t.terr_variable) AS terr_variable, any_value(t.terr_codigo) AS terr_codigo, any_value(t.terr_nombre) AS terr_nombre
    FROM d LEFT JOIN terr t USING (tabla_id, serie_cod)
    GROUP BY d.tabla_id, d.serie_cod
    """)

    # 3) territorio común: por código; si no hay código, por nombre; sin variable de territorio = dato nacional implícito
    con.execute("""
    CREATE TABLE serie_terr AS
    SELECT a.tabla_id, a.serie_cod, a.terr_variable, a.terr_codigo, a.terr_nombre,
        COALESCE(
            CASE WHEN a.terr_variable IS NULL THEN 'N00'
                 WHEN a.terr_codigo = '00' OR a.terr_variable ILIKE 'Total Nacional' OR a.terr_variable ILIKE 'Totales Territoriales' THEN 'N00'
                 WHEN a.terr_variable ILIKE '%provincia%' AND a.terr_codigo <> '' THEN 'P' || lpad(a.terr_codigo, 2, '0')
                 WHEN (a.terr_variable ILIKE '%comunidad%' OR a.terr_variable ILIKE '%CCAA%') AND a.terr_codigo <> ''
                      THEN 'C' || lpad(a.terr_codigo, 2, '0') END,
            (SELECT min(t.territorio_id) FROM dim_territorio t
              WHERE lower(t.nombre) = lower(trim(a.terr_nombre))
                AND t.nivel = CASE WHEN a.terr_variable ILIKE '%provincia%' THEN 'Provincia' ELSE 'CCAA' END)
        ) AS territorio_id,
        a.terr_variable IS NULL AS territorio_implicito
    FROM serie_attr a
    """)

    # 4) tabla de hechos
    con.execute("""
    CREATE TABLE fact_ine AS
    SELECT v.tabla_id, v.serie_cod, v.serie_nombre,
        TRY_CAST(v.fecha AS DATE) AS fecha, TRY_CAST(v.anyo AS INTEGER) AS anyo, v.periodo,
        CASE WHEN coalesce(v.periodo, '') = '' THEN 'Puntual'
             WHEN v.periodo = 'A' THEN 'Anual'
             WHEN v.periodo LIKE 'M%' THEN 'Mensual'
             WHEN v.periodo LIKE 'T%' OR v.periodo LIKE 'Q%' THEN 'Trimestral'
             WHEN v.periodo LIKE 'S%' THEN 'Semestral'
             ELSE 'Otra (' || v.periodo || ')' END AS periodicidad,
        t.territorio_id, t.territorio_implicito,
        a.medida, a.estadistico, a.situacion, a.sexo, a.edad, a.jornada, a.tamano_empresa, a.actividad, a.actividad_codigo, a.ocupacion, a.ocupacion_codigo,
        a.nacionalidad, a.formacion, a.detalle,
        v.unidad, v.escala, v.tipo_dato,
        TRY_CAST(v.valor AS DOUBLE) AS valor,
        lower(coalesce(v.secreto, '')) IN ('true', '1') AS secreto
    FROM valores v
    LEFT JOIN serie_attr a USING (tabla_id, serie_cod)
    LEFT JOIN serie_terr t USING (tabla_id, serie_cod)
    """)

    # 5) dimensiones de tabla y tiempo
    con.execute(f"""CREATE TABLE cfg_tablas AS SELECT * FROM read_csv('{CFG / "tablas_ine.csv"}', header=true, delim=';', all_varchar=true)""")
    con.execute(f"""CREATE TABLE carga AS SELECT * FROM read_csv('{QA / "ine_carga.csv"}', header=true, delim=';', all_varchar=true)""")
    if CATALOGO_INE.exists():
        con.execute(f"""CREATE TABLE cat AS SELECT tabla_id, first(op_cod) AS operacion_cod, first(op_nombre) AS operacion,
                        first(tabla_nombre) AS tabla_nombre
                        FROM read_csv('{CATALOGO_INE}', header=true, delim=';', all_varchar=true) GROUP BY tabla_id""")
    else:
        con.execute("CREATE TABLE cat(tabla_id VARCHAR, operacion_cod VARCHAR, operacion VARCHAR, tabla_nombre VARCHAR)")
    con.execute("""
    CREATE TABLE dim_tabla AS
    SELECT c.tabla_id, c.punto,
        CASE c.punto WHEN '1' THEN 'Benchmark salarial' WHEN '2' THEN 'Coste laboral y absentismo'
                     WHEN '3' THEN 'Mercado de talento' WHEN '4' THEN 'Revisión salarial'
                     WHEN '5' THEN 'Igualdad y diversidad' WHEN '6' THEN 'Contexto de mercado' END AS punto_nombre,
        c.tema, c.nota, k.operacion_cod, k.operacion, k.tabla_nombre, 'INE' AS organismo,
        'https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/' || c.tabla_id AS url_api,
        g.estado AS estado_carga, TRY_CAST(g.fecha_min AS DATE) AS fecha_min, TRY_CAST(g.fecha_max AS DATE) AS fecha_max
    FROM cfg_tablas c LEFT JOIN cat k USING (tabla_id) LEFT JOIN carga g USING (tabla_id)
    """)
    con.execute("""
    CREATE TABLE dim_tiempo AS
    SELECT CAST(d AS DATE) AS fecha, year(d) AS anyo, quarter(d) AS trimestre, month(d) AS mes,
           strftime(d, '%Y-%m') AS anyo_mes, year(d) || '-T' || quarter(d) AS anyo_trimestre
    FROM range((SELECT make_date(min(anyo), 1, 1) FROM fact_ine WHERE anyo IS NOT NULL),
               (SELECT make_date(max(anyo) + 1, 1, 1) FROM fact_ine WHERE anyo IS NOT NULL), INTERVAL 1 DAY) t(d)
    """)

    # 5a) fuentes de la fase 2 (pipeline/fuentes.py): ya vienen limpias; se cargan si existen
    fuentes = {"sepe_paro_municipio": "fact_sepe_paro_municipio", "sepe_contratos_municipio": "fact_sepe_contratos_municipio",
               "sepe_demandantes_municipio": "fact_sepe_demandantes_municipio",
               "ss_afiliacion": "fact_ss_afiliacion", "mites_cpd_actividad": "fact_cpd_actividad",
               "mites_convenios": "fact_convenios", "mites_accidentes": "fact_accidentes",
               "mites_ett_mensual": "fact_ett_mensual", "mites_ett_territorio": "fact_ett_territorio",
               "mites_ett_actividad": "fact_ett_actividad", "mites_ett_resumen": "fact_ett_resumen", "mites_convenios_detalle": "fact_convenios_detalle",
               "mites_accidentes_detalle": "fact_accidentes_detalle", "mites_regulacion_empleo": "fact_regulacion_empleo",
               "ss_incapacidad_temporal": "fact_incapacidad_temporal", "ss_it_detalle": "fact_it_detalle",
               "fundae_formacion": "fact_fundae", "eurostat_indicadores": "fact_eurostat"}
    con.execute("ALTER TABLE dim_territorio ADD COLUMN provincia_id VARCHAR")
    con.execute("UPDATE dim_territorio SET provincia_id = territorio_id WHERE nivel = 'Provincia'")
    cargadas = []
    for origen, destino in fuentes.items():
        p = NORM / f"{origen}.csv"
        if p.exists() and p.stat().st_size > 0:
            con.execute(f"CREATE TABLE {destino} AS SELECT * FROM read_csv('{p}', header=true, sample_size=-1)")
            cargadas.append(destino)
    if "fact_sepe_paro_municipio" in cargadas or "fact_sepe_contratos_municipio" in cargadas:
        # municipios a dim_territorio, con su provincia y CCAA (para jerarquías y cruces)
        origen_muni = " UNION ".join(f"SELECT DISTINCT territorio_id, municipio, provincia_id, ccaa_id FROM {t}"
                                     for t in ("fact_sepe_paro_municipio", "fact_sepe_contratos_municipio") if t in cargadas)
        con.execute(f"""INSERT INTO dim_territorio
            SELECT m.territorio_id, 'Municipio', substr(m.territorio_id, 2), any_value(m.municipio), m.ccaa_id,
                   any_value(c.nombre), m.provincia_id
            FROM ({origen_muni}) m LEFT JOIN dim_territorio c ON c.territorio_id = m.ccaa_id
            WHERE m.territorio_id NOT IN (SELECT territorio_id FROM dim_territorio)
            GROUP BY m.territorio_id, m.ccaa_id, m.provincia_id""")
    for t in cargadas:
        n = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        con.execute(f"COPY {t} TO '{MODELO / (t + '.parquet')}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        if n <= 300_000:  # los CSV grandes superarían el límite de 100 MB de GitHub: solo Parquet
            con.execute(f"COPY {t} TO '{MODELO / (t + '.csv')}' (HEADER, DELIMITER ';')")
    if cargadas:
        def periodo(t):
            cols = [c for (c,) in con.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{t}'").fetchall()]
            c = next((x for x in ("fecha", "periodo_hasta", "anyo_efectos", "anyo") if x in cols), None)
            if c is None:
                return f"NULL AS desde, NULL AS hasta, 0 AS sin_territorio"
            terr = ("count(*) FILTER (WHERE territorio_id IS NULL)" if "territorio_id" in cols and t != "fact_convenios_detalle"
                    else "0")
            return f"min({c})::VARCHAR AS desde, max({c})::VARCHAR AS hasta, {terr} AS sin_territorio"
        con.execute(f"""COPY ({" UNION ALL ".join(
            f"SELECT '{t}' AS tabla, count(*) AS filas, {periodo(t)} FROM {t}" for t in cargadas)})
            TO '{QA / "resumen_fuentes.csv"}' (HEADER, DELIMITER ';')""")

    # 5b) tablas listas para explotar (pipeline/marts.sql)
    con.execute((RAIZ / "pipeline" / "marts.sql").read_text(encoding="utf-8"))
    marts = [r[0] for r in con.execute(
        "SELECT view_name FROM duckdb_views() WHERE NOT internal AND view_name LIKE 'mart_%' ORDER BY 1").fetchall()]
    (MODELO / "marts").mkdir(exist_ok=True)
    for m in marts:
        con.execute(f"COPY (SELECT * FROM {m}) TO '{MODELO / 'marts' / (m + '.parquet')}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        con.execute(f"COPY (SELECT * FROM {m}) TO '{MODELO / 'marts' / (m + '.csv')}' (HEADER, DELIMITER ';')")
    con.execute(f"""COPY ({" UNION ALL ".join(
        f"SELECT '{m}' AS mart, count(*) AS filas, min(fecha) AS fecha_min, max(fecha) AS fecha_max FROM {m}" for m in marts)})
        TO '{QA / "resumen_marts.csv"}' (HEADER, DELIMITER ';')""")

    # 6) exportar
    for tabla in ("fact_ine", "dim_tabla", "dim_territorio", "dim_tiempo"):
        con.execute(f"COPY {tabla} TO '{MODELO / (tabla + '.parquet')}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        con.execute(f"COPY {tabla} TO '{MODELO / (tabla + '.csv')}' (HEADER, DELIMITER ';')")

    # 7) QA
    con.execute(f"""COPY (
        SELECT m.variable, count(DISTINCT s.tabla_id) AS n_tablas, string_agg(DISTINCT s.tabla_id, ',') AS tablas,
               string_agg(DISTINCT s.nombre, ' | ')[:300] AS valores_ejemplo
        FROM mapa_variables m JOIN series_dims s USING (variable) WHERE m.dimension = 'otra' GROUP BY m.variable ORDER BY n_tablas DESC
    ) TO '{QA / "variables_sin_mapear.csv"}' (HEADER, DELIMITER ';')""")
    con.execute(f"""COPY (
        SELECT tabla_id, terr_variable, terr_codigo, terr_nombre, count(*) AS n_series
        FROM serie_terr WHERE territorio_id IS NULL GROUP BY ALL ORDER BY n_series DESC
    ) TO '{QA / "territorio_sin_resolver.csv"}' (HEADER, DELIMITER ';')""")
    con.execute(f"""COPY (
        SELECT f.tabla_id, any_value(d.tema) AS tema, count(*) AS datos, count(DISTINCT serie_cod) AS series,
               min(fecha) AS fecha_min, max(fecha) AS fecha_max, string_agg(DISTINCT periodicidad, ',') AS periodicidad,
               string_agg(DISTINCT left(territorio_id, 1), ',') AS niveles_territorio,
               round(100.0 * count(*) FILTER (WHERE valor IS NULL) / count(*), 1) AS pct_valor_nulo,
               bool_or(territorio_id IS NULL) AS hay_territorio_sin_resolver
        FROM fact_ine f LEFT JOIN dim_tabla d USING (tabla_id) GROUP BY f.tabla_id ORDER BY f.tabla_id
    ) TO '{QA / "resumen_modelo.csv"}' (HEADER, DELIMITER ';')""")
    # combinaciones de atributos de cada tabla (sin territorio ni fecha): base para diseñar las tablas por punto de RRHH
    con.execute(f"""COPY (
        SELECT tabla_id, medida, estadistico, situacion, sexo, edad, jornada, tamano_empresa, actividad, ocupacion,
               nacionalidad, formacion, detalle, unidad, escala,
               string_agg(DISTINCT left(territorio_id, 1), ',') AS niveles_territorio,
               count(DISTINCT serie_cod) AS n_series, min(fecha) AS fecha_min, max(fecha) AS fecha_max
        FROM fact_ine GROUP BY ALL ORDER BY ALL
    ) TO '{QA / "catalogo_series.csv"}' (HEADER, DELIMITER ';')""")
    con.execute("CREATE VIEW v_mapa_variables AS SELECT * FROM mapa_variables")
    n = con.execute("SELECT count(*) FROM fact_ine").fetchone()[0]
    print(f"fact_ine: {n} filas · tablas en el modelo: {con.execute('SELECT count(DISTINCT tabla_id) FROM fact_ine').fetchone()[0]}")
    for tabla in ("fact_ine", "dim_tabla", "dim_territorio", "dim_tiempo"):
        print(f"  {tabla}.parquet {(MODELO / (tabla + '.parquet')).stat().st_size / 1e6:.1f} MB")
    con.close()


if __name__ == "__main__":
    sys.exit(main())
