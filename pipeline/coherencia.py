"""
pipeline/coherencia.py — Coherencia interna de las cifras del modelo, antes de publicar.

Comprueba relaciones que tienen que cumplirse entre columnas o tablas del propio modelo (no compara con datos externos):
  - EPA: las tasas están entre 0 y 100 y la tasa de empleo = actividad × (1 − paro/100) (tolerancia 0,3 puntos).
  - NEET: porcentajes entre 0 y 100.
  - FUNDAE: en las series por edad, tamaño de empresa, estudios y por comunidad, las partes suman el total (tolerancia 1 %).
  - SEPE por nivel formativo: españoles + extranjeros = total de parados; indefinidos + temporales = total de contratos.
  - Eurostat: los porcentajes están entre 0 y 100 y la población total = hombres + mujeres.
  - Oportunidad por comunidad: los demandantes menores de 25 no superan el total de demandantes.
Las tablas que no están se saltan (muchas son opcionales). Devuelve la lista de problemas (vacía = coherente).
Lo usa control_publicacion.py sobre datos/publicar/modelo y tests/ sobre la muestra resultados/dev_modelo.
"""
from pathlib import Path

import duckdb

TOL_EPA = 0.3       # puntos de tasa
TOL_FUNDAE = 0.01   # fracción del total (FUNDAE avisa de pequeñas diferencias por valores nulos o fuera de rango)


def _t(carpeta, rel):
    p = Path(carpeta) / f"{rel}.parquet"
    return f"'{p.as_posix()}'" if p.exists() else None


def _consulta(sql):
    return duckdb.sql(sql).fetchall()


def revisar_modelo(carpeta):
    problemas = []

    t = _t(carpeta, "marts/mart_tasas_epa")
    if t:
        n = _consulta(f"SELECT count(*) FROM {t} WHERE tasa < 0 OR tasa > 100")[0][0]
        if n:
            problemas.append(f"`mart_tasas_epa`: {n} tasas fuera de 0-100")
        r = _consulta(f"""WITH p AS (SELECT anyo, territorio_id, sexo, edad,
              max(CASE WHEN indicador = 'Tasa de actividad' THEN tasa END) a, max(CASE WHEN indicador = 'Tasa de empleo' THEN tasa END) e,
              max(CASE WHEN indicador = 'Tasa de paro' THEN tasa END) u FROM {t} GROUP BY 1, 2, 3, 4)
            SELECT count(*), max(abs(e - a * (1 - u / 100))) FROM p WHERE a IS NOT NULL AND e IS NOT NULL AND u IS NOT NULL
              AND abs(e - a * (1 - u / 100)) > {TOL_EPA}""")[0]
        if r[0]:
            problemas.append(f"`mart_tasas_epa`: en {r[0]} casos la tasa de empleo no cuadra con actividad y paro (hasta {r[1]:.2f} puntos)")

    t = _t(carpeta, "marts/mart_neet")
    if t:
        n = _consulta(f"SELECT count(*) FROM {t} WHERE porcentaje < 0 OR porcentaje > 100")[0][0]
        if n:
            problemas.append(f"`mart_neet`: {n} porcentajes fuera de 0-100")

    t = _t(carpeta, "fact_fundae")
    if t:
        for serie in ("01", "03", "04", "38"):
            r = _consulta(f"""SELECT count(*), max(abs(s - t) / t) FROM (SELECT anyo, medida,
                  sum(CASE WHEN categoria <> 'Total' THEN valor END) s, max(CASE WHEN categoria = 'Total' THEN valor END) t
                FROM {t} WHERE serie = '{serie}' AND coalesce(subdimension, '') = '' GROUP BY 1, 2)
                WHERE t > 0 AND s IS NOT NULL AND abs(s - t) / t > {TOL_FUNDAE}""")[0]
            if r[0]:
                problemas.append(f"`fact_fundae` serie {serie}: en {r[0]} casos las partes no suman el total (hasta {r[1]:.1%})")
        r = _consulta(f"""SELECT count(*), max(abs(s - t) / t) FROM (SELECT anyo, medida,
              sum(CASE WHEN coalesce(ccaa_id, '') <> '' THEN valor END) s, max(CASE WHEN categoria = 'Total' THEN valor END) t
            FROM {t} WHERE serie = '30' GROUP BY 1, 2) WHERE t > 0 AND s IS NOT NULL AND abs(s - t) / t > {TOL_FUNDAE}""")[0]
        if r[0]:
            problemas.append(f"`fact_fundae` serie 30: en {r[0]} casos las comunidades no suman el total (hasta {r[1]:.1%})")

    t = _t(carpeta, "fact_sepe_demandantes_nivel")
    if t:
        n = _consulta(f"SELECT count(*) FROM {t} WHERE espanoles + extranjeros <> total")[0][0]
        if n:
            problemas.append(f"`fact_sepe_demandantes_nivel`: en {n} filas españoles + extranjeros no suman el total")
    t = _t(carpeta, "fact_sepe_contratos_nivel")
    if t:
        n = _consulta(f"SELECT count(*) FROM {t} WHERE indefinidos + temporales <> total")[0][0]
        if n:
            problemas.append(f"`fact_sepe_contratos_nivel`: en {n} filas indefinidos + temporales no suman el total")

    t = _t(carpeta, "fact_eurostat")
    if t:
        r = _consulta(f"SELECT serie, count(*) FROM {t} WHERE unidad = '%' AND (valor < 0 OR valor > 100) GROUP BY 1")
        for serie, n in r:
            problemas.append(f"`fact_eurostat` {serie}: {n} porcentajes fuera de 0-100")
        r = _consulta(f"""SELECT count(*) FROM (SELECT anyo, max(CASE WHEN sexo = 'Total' THEN valor END) t,
              max(CASE WHEN sexo = 'Hombres' THEN valor END) h, max(CASE WHEN sexo = 'Mujeres' THEN valor END) m
            FROM {t} WHERE serie = 'poblacion_16_29' GROUP BY 1) WHERE t > 0 AND h IS NOT NULL AND m IS NOT NULL AND abs(t - h - m) / t > 0.005""")[0][0]
        if r:
            problemas.append(f"`fact_eurostat` poblacion_16_29: en {r} años hombres + mujeres no suman el total")

    t = _t(carpeta, "marts/mart_oportunidad_ccaa")
    if t:
        n = _consulta(f"SELECT count(*) FROM {t} WHERE demandantes_menores_25 > demandantes")[0][0]
        if n:
            problemas.append(f"`mart_oportunidad_ccaa`: {n} filas con más demandantes menores de 25 que demandantes en total")
    return problemas
