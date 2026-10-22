#!/usr/bin/env python3
"""
pipeline/visual_datos.py — Extrae del modelo los números del informe de muestra (prototipo visual).

Entrada:  datos/rrhh.duckdb   (o, con --parquet <carpeta>, los Parquet publicados: modelo/*.parquet y modelo/marts/)
Salida:   datos/visual/datos_visual.json   (KPIs y series ya agregadas, sin datos personales)
Cada bloque es independiente: si uno falla (p. ej. una fuente que hoy no se ha cargado), queda {"error": ...} y el resto
se genera igual. Al final se calculan la ficha por provincia y las conclusiones, solo con cifras de los bloques.
"""
import argparse, csv, json, sys
from datetime import date, datetime, timezone
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "datos" / "visual" / "datos_visual.json"
SECTOR_TOTAL = "Industria, construcción y servicios%"

BLOQUES = {
    # ---------------------------------------------------------------- portada / contexto
    "coste_laboral": f"""SELECT fecha, round(euros) AS euros FROM mart_coste_laboral
        WHERE territorio_id = 'N00' AND componente = 'Coste laboral total' AND base = 'Por trabajador y mes'
          AND sector LIKE '{SECTOR_TOTAL}' ORDER BY fecha DESC LIMIT 20""",
    "paro_ccaa": """SELECT t.nombre AS ccaa, e.territorio_id, e.anyo, round(e.tasa, 1) AS tasa
        FROM mart_tasas_epa e JOIN dim_territorio t USING (territorio_id)
        WHERE e.indicador = 'Tasa de paro' AND e.sexo = 'Ambos sexos' AND e.edad = 'Total' AND t.nivel = 'CCAA'
          AND e.anyo = (SELECT max(anyo) FROM mart_tasas_epa) ORDER BY tasa DESC""",
    "paro_ccaa_sexo": """SELECT t.nombre AS ccaa, e.territorio_id, e.sexo, round(e.tasa, 1) AS tasa
        FROM mart_tasas_epa e JOIN dim_territorio t USING (territorio_id)
        WHERE e.indicador = 'Tasa de paro' AND e.sexo IN ('Hombres', 'Mujeres') AND e.edad = 'Total'
          AND (t.nivel = 'CCAA' OR e.territorio_id = 'N00') AND e.anyo = (SELECT max(anyo) FROM mart_tasas_epa)""",
    "paro_nacional": """SELECT anyo, round(tasa, 1) AS tasa FROM mart_tasas_epa
        WHERE indicador = 'Tasa de paro' AND sexo = 'Ambos sexos' AND edad = 'Total' AND territorio_id = 'N00'
        ORDER BY anyo DESC LIMIT 8""",
    "ipc_ultimo": """SELECT fecha, round(valor, 1) AS valor FROM mart_precios WHERE indice = 'IPC'
        AND indicador = 'Variación anual' AND territorio_id = 'N00' ORDER BY fecha DESC LIMIT 1""",
    "vacantes": """SELECT fecha, vacantes FROM mart_vacantes WHERE territorio_id = 'N00' ORDER BY fecha DESC LIMIT 12""",
    "vacantes_actividad": """SELECT actividad, actividad_codigo, vacantes FROM mart_vacantes_actividad
        WHERE fecha = (SELECT max(fecha) FROM mart_vacantes_actividad) AND length(actividad_codigo) = 1 ORDER BY vacantes DESC""",
    "empresas": """SELECT estrato_asalariados, anyo, empresas FROM mart_empresas
        WHERE territorio_id = 'N00' AND estrato_asalariados <> 'Total' AND anyo = (SELECT max(anyo) FROM mart_empresas)""",

    # ---------------------------------------------------------------- CPD y ETT
    "ett_mensual": """SELECT fecha, indicador, categoria, valor FROM fact_ett_mensual WHERE periodo = 'Mes'
        AND fecha >= (SELECT max(fecha) - INTERVAL 30 MONTH FROM fact_ett_mensual) ORDER BY fecha""",
    "ett_anual": """SELECT year(fecha) AS anyo, indicador, categoria, valor FROM fact_ett_mensual WHERE periodo = 'Año'
        AND indicador IN ('CPD por modalidad', 'Cesiones', 'ETT', 'Trabajadores contratados por ETT') ORDER BY anyo""",
    "ett_territorio": """SELECT year(periodo_hasta) AS anyo, month(periodo_hasta) AS mes, nivel, territorio_id, provincia_id,
            territorio_nombre, cesiones, cpd_total, cpd_circunstancias, cpd_fijos_discontinuos, cpd_sustitucion_formacion
        FROM fact_ett_territorio WHERE tipo_periodo = 'Acumulado'""",
    "ett_actividad": """SELECT year(periodo_hasta) AS anyo, month(periodo_hasta) AS mes, nivel, codigo, nombre,
            cpd_total, cpd_circunstancias, cpd_fijos_discontinuos, cpd_sustitucion_formacion
        FROM fact_ett_actividad WHERE tipo_periodo = 'Acumulado'""",
    "ett_resumen": """SELECT cuadro, codigo, territorio_id, nombre, valor, variacion_abs, variacion_pct, periodo_hasta
        FROM fact_ett_resumen""",
    "cpd_secciones": """SELECT seccion_cnae, seccion_nombre, sum(cpd) AS cpd, count(*) AS meses, max(fecha) AS hasta FROM fact_cpd_actividad
        WHERE seccion_cnae <> 'TOTAL' AND year(fecha) = (SELECT year(max(fecha)) FROM fact_cpd_actividad)
        GROUP BY ALL ORDER BY cpd DESC""",
    # afiliados medios del Régimen General por sección CNAE-2025 (suma de CCAA) en los mismos meses que los CPD del año
    "afiliados_rg_seccion": """SELECT left(seccion_cnae, 1) AS seccion, avg(afil) AS afiliados_rg, count(*) AS meses FROM (
            SELECT fecha, seccion_cnae, sum(afiliados) AS afil FROM fact_ss_afiliacion
            WHERE consulta = 'afil_medios_ccaa_cnae25_regimen' AND regimen = 'REGIMEN GENERAL' AND territorio_id LIKE 'C%'
              AND fecha BETWEEN date_trunc('year', (SELECT max(fecha) FROM fact_cpd_actividad)) AND (SELECT max(fecha) FROM fact_cpd_actividad)
              AND seccion_cnae NOT ILIKE 'TODAS%'
            GROUP BY ALL) GROUP BY 1 ORDER BY 1""",
    "epa_ett": """SELECT e.territorio_id, t.nombre, e.anyo, e.sexo,
            max(e.miles_asalariados) FILTER (WHERE contratado_ett = 'Sí') AS miles_ett,
            max(e.miles_asalariados) FILTER (WHERE contratado_ett = 'Total') AS miles_total
        FROM mart_epa_ett e LEFT JOIN dim_territorio t USING (territorio_id)
        WHERE e.anyo = (SELECT max(anyo) FROM mart_epa_ett) GROUP BY ALL""",

    # ---------------------------------------------------------------- absentismo, horas y coste
    "horas_ccaa": f"""SELECT t.nombre AS ccaa, h.territorio_id, h.fecha,
            max(h.horas_trabajador_mes) FILTER (WHERE concepto = 'Horas pactadas') AS pactadas,
            max(h.horas_trabajador_mes) FILTER (WHERE concepto = 'Horas efectivas') AS efectivas,
            max(h.horas_trabajador_mes) FILTER (WHERE concepto = 'Horas no trabajadas') AS no_trabajadas,
            max(h.horas_trabajador_mes) FILTER (WHERE concepto = 'Horas extras por trabajador') AS extras
        FROM mart_tiempo_trabajo h JOIN dim_territorio t USING (territorio_id)
        WHERE h.jornada = 'Ambas jornadas' AND h.sector LIKE '{SECTOR_TOTAL}' AND (t.nivel = 'CCAA' OR h.territorio_id = 'N00')
          AND h.fecha >= (SELECT max(fecha) - INTERVAL 4 YEAR FROM mart_tiempo_trabajo) GROUP BY ALL ORDER BY h.fecha""",
    "horas_actividad": """SELECT actividad, actividad_codigo, fecha,
            max(horas_trabajador_mes) FILTER (WHERE concepto = 'Horas pactadas') AS pactadas,
            max(horas_trabajador_mes) FILTER (WHERE concepto = 'Horas efectivas') AS efectivas,
            max(horas_trabajador_mes) FILTER (WHERE concepto = 'Horas no trabajadas') AS no_trabajadas,
            max(horas_trabajador_mes) FILTER (WHERE concepto = 'Horas no trabajadas por I.T') AS it,
            max(horas_trabajador_mes) FILTER (WHERE concepto = 'Horas no trabajadas por vacaciones y fiestas') AS vacaciones,
            max(horas_trabajador_mes) FILTER (WHERE concepto = 'Horas extras por trabajador') AS extras
        FROM mart_tiempo_trabajo_actividad WHERE jornada = 'Ambas jornadas'
          AND fecha >= (SELECT max(fecha) - INTERVAL 4 YEAR FROM mart_tiempo_trabajo_actividad) GROUP BY ALL ORDER BY fecha""",
    "it_provincias": """SELECT anyo, mes_hasta, periodo, nivel, territorio_id, provincia_id, nombre, duracion_media_dias,
            incidencia_media_mensual_mil, procesos_iniciados, prevalencia_mil, procesos_en_vigor_final, trabajadores_protegidos_media
        FROM fact_incapacidad_temporal""",
    "convenios_historico": """SELECT anyo_efectos AS anyo, mes_registro AS mes, desglose, nivel, codigo, nombre, territorio_id,
            ambito_funcional, trabajadores, variacion_salarial_pct AS variacion, jornada_media_horas AS jornada
        FROM fact_convenios_detalle WHERE ambito_funcional = 'Total' AND desglose IN ('Actividad', 'Territorio')
          AND nivel IN ('Total', 'Sector', 'Sección', 'Nacional', 'CCAA')""",
    "it_despido": """SELECT actividad, concepto, euros, fecha FROM mart_it_despido
        WHERE fecha = (SELECT max(fecha) FROM mart_it_despido) AND territorio_id = 'N00'""",
    "coste_actividad": """SELECT actividad, actividad_codigo, componente, round(euros_trabajador_mes) AS euros, fecha FROM mart_coste_actividad
        WHERE fecha = (SELECT max(fecha) FROM mart_coste_actividad)
          AND componente IN ('Coste laboral total', 'Coste salarial total', 'Coste por cotizaciones obligatorias', 'Coste por despido')""",
    "coste_ccaa": f"""SELECT t.nombre AS ccaa, c.territorio_id, c.base, round(c.euros, 2) AS euros, c.fecha
        FROM mart_coste_laboral c JOIN dim_territorio t USING (territorio_id)
        WHERE c.fecha = (SELECT max(fecha) FROM mart_coste_laboral) AND c.componente = 'Coste laboral total'
          AND c.sector LIKE '{SECTOR_TOTAL}' AND (t.nivel = 'CCAA' OR c.territorio_id = 'N00')""",
    "horas_extra": """SELECT fecha, sexo, actividad, actividad_codigo, horas_extra, miles_asalariados FROM mart_horas_extra
        WHERE fecha = (SELECT max(fecha) FROM mart_horas_extra)""",
    "teletrabajo": """SELECT m.territorio_id, t.nombre, m.anyo, m.sexo, m.frecuencia, m.pct_ocupados FROM mart_teletrabajo m
        LEFT JOIN dim_territorio t USING (territorio_id) WHERE m.anyo = (SELECT max(anyo) FROM mart_teletrabajo)""",

    # ---------------------------------------------------------------- accidentes
    "accidentes": """SELECT territorio_id, territorio_nombre AS nombre, periodo_hasta, accidentes_jornada, accidentes_mortales,
            afiliados_media_mensual, round(indice_incidencia, 1) AS indice, indice_incidencia_mortales AS indice_mortales
        FROM fact_accidentes""",
    "accidentes_detalle": """SELECT periodo_hasta, cuadro, codigo, nombre, sexo, territorio_id, medida, valor FROM fact_accidentes_detalle
        WHERE cuadro IN ('Sexo y edad', 'Índice por actividad', 'Índice por CCAA y sector', 'Variación interanual', 'Ocupación')
           OR (cuadro = 'Actividad' AND NOT regexp_matches(codigo, '^[0-9]+$'))""",
    "erte": """SELECT fecha, cuadro, codigo, nombre, territorio_id, tipo, sexo, trabajadores FROM fact_regulacion_empleo
        WHERE (cuadro = 'Actividad' AND NOT regexp_matches(codigo, '^[0-9]+$')) OR cuadro IN ('Causa', 'Tamaño de empresa')
           OR (cuadro = 'Territorio' AND territorio_id NOT LIKE 'P%' AND sexo = 'Total')""",

    # ---------------------------------------------------------------- convenios
    "convenios_ipc": """SELECT c.anyo_efectos AS anyo, c.variacion_salarial_pactada_pct AS pactada, c.tipo_dato,
            c.jornada_media_horas_anyo AS jornada,
            (SELECT round(valor, 2) FROM mart_precios p WHERE p.indice = 'IPC' AND p.indicador = 'Variación anual'
               AND p.territorio_id = 'N00' AND year(p.fecha) = c.anyo_efectos ORDER BY p.fecha DESC LIMIT 1) AS ipc
        FROM fact_convenios c WHERE c.tipo_dato IN ('Año completo', 'Año (provisional)') ORDER BY anyo""",
    "convenios_ultimo": """SELECT anyo_efectos AS anyo, mes_registro AS mes, variacion_salarial_pactada_pct AS pactada,
            trabajadores, jornada_media_horas_anyo AS jornada FROM fact_convenios WHERE tipo_dato = 'Registrados hasta el mes'
        ORDER BY anyo_efectos DESC, mes_registro DESC LIMIT 1""",
    "convenios_detalle": """SELECT anyo_efectos AS anyo, mes_registro AS mes, desglose, nivel, codigo, nombre, territorio_id,
            provincia_id, ambito_funcional, convenios, trabajadores, variacion_salarial_pct AS variacion, jornada_media_horas AS jornada
        FROM fact_convenios_detalle WHERE anyo_efectos = (SELECT max(anyo_efectos) FROM fact_convenios_detalle)
          AND (desglose <> 'Ámbito' OR ambito_funcional = 'Total')""",

    # ---------------------------------------------------------------- mercado de trabajo
    "paro_registrado": """SELECT fecha, sum(total_paro_registrado) AS paro,
            sum(paro_mujer_edad_25 + paro_mujer_edad_25_45 + paro_mujer_edad_45) AS mujeres,
            sum(paro_hombre_edad_25 + paro_mujer_edad_25) AS menores_25, sum(paro_hombre_edad_45 + paro_mujer_edad_45) AS mayores_45
        FROM fact_sepe_paro_municipio GROUP BY fecha ORDER BY fecha DESC LIMIT 37""",
    "contratos_mensual": """SELECT fecha, sum(total_contratos) AS total,
            sum(contratos_iniciales_indefinidos_hombres + contratos_iniciales_indefinidos_mujeres) AS indefinidos,
            sum(contratos_convertidos_en_indefinidos_hombres + contratos_convertidos_en_indefinidos_mujeres) AS convertidos,
            sum(contratos_iniciales_indefinidos_mujeres + contratos_iniciales_temporales_mujeres + contratos_convertidos_en_indefinidos_mujeres) AS mujeres
        FROM fact_sepe_contratos_municipio GROUP BY fecha ORDER BY fecha DESC LIMIT 37""",
    "afiliacion_contrato": """SELECT fecha, modalidad_contrato, sexo, sum(afiliados) AS afiliados FROM fact_ss_afiliacion
        WHERE consulta = 'afil_medios_rg_prov_contrato_sexo' AND territorio_id LIKE 'P%'
          AND fecha >= (SELECT max(fecha) - INTERVAL 25 MONTH FROM fact_ss_afiliacion WHERE consulta = 'afil_medios_rg_prov_contrato_sexo')
        GROUP BY ALL ORDER BY fecha""",
    "afiliacion_seccion": """SELECT fecha, left(seccion_cnae, 1) AS seccion, any_value(seccion_cnae) AS nombre, sum(afiliados) AS afiliados
        FROM fact_ss_afiliacion WHERE consulta = 'afil_medios_ccaa_cnae25_regimen' AND regimen ILIKE 'Total%'
          AND territorio_id LIKE 'C%' AND seccion_cnae NOT ILIKE 'TODAS%' GROUP BY ALL ORDER BY fecha""",
    "flujos": """SELECT fecha, situacion_anterior, situacion_actual, miles_personas FROM mart_flujos
        WHERE territorio_id = 'N00' AND fecha >= (SELECT max(fecha) - INTERVAL 3 YEAR FROM mart_flujos)
          AND situacion_actual IN ('Ocupados', 'Parados', 'Inactivos') AND situacion_anterior IN ('Ocupados', 'Parados', 'Inactivos')""",
    "temporalidad_motivo": """SELECT territorio_id, sexo, motivo, miles_asalariados, anyo FROM mart_temporalidad_motivo
        WHERE territorio_id = 'N00' AND anyo = (SELECT max(anyo) FROM mart_temporalidad_motivo)""",

    # ---------------------------------------------------------------- salarios e igualdad
    "salarios_ees": """SELECT ocupacion, sexo, round(euros) AS euros FROM mart_salarios_ees
        WHERE anyo = 2022 AND estadistico = 'Mediana' AND territorio_id = 'N00' AND sexo IN ('Hombres', 'Mujeres')
          AND ocupacion IS NOT NULL ORDER BY ocupacion, sexo""",
    "salarios_ees_detalle": """SELECT s.territorio_id, t.nombre, s.sexo, s.sector, s.desglose, s.categoria, round(s.euros_anuales) AS euros
        FROM mart_salarios_ees_detalle s LEFT JOIN dim_territorio t USING (territorio_id)""",
    "brecha": """SELECT categoria, anyo, round(brecha_pct, 1) AS brecha FROM mart_brecha_genero
        WHERE desglose = 'Edad' AND anyo = (SELECT max(anyo) FROM mart_brecha_genero) ORDER BY categoria""",

    # ---------------------------------------------------------------- ficha de provincia (se combinan en Python)
    "prov_paro": """SELECT provincia_id AS p, fecha, sum(total_paro_registrado) AS paro,
            sum(paro_mujer_edad_25 + paro_mujer_edad_25_45 + paro_mujer_edad_45) AS paro_mujeres
        FROM fact_sepe_paro_municipio WHERE fecha IN ((SELECT max(fecha) FROM fact_sepe_paro_municipio),
                                                     (SELECT max(fecha) - INTERVAL 12 MONTH FROM fact_sepe_paro_municipio))
        GROUP BY ALL""",
    "prov_contratos": """SELECT provincia_id AS p, sum(total_contratos) AS contratos,
            sum(contratos_iniciales_indefinidos_hombres + contratos_iniciales_indefinidos_mujeres) AS indefinidos,
            sum(contratos_convertidos_en_indefinidos_hombres + contratos_convertidos_en_indefinidos_mujeres) AS convertidos,
            min(fecha) AS desde, max(fecha) AS hasta
        FROM fact_sepe_contratos_municipio WHERE fecha > (SELECT max(fecha) - INTERVAL 12 MONTH FROM fact_sepe_contratos_municipio)
        GROUP BY ALL""",
    "prov_afiliacion": """SELECT territorio_id AS p, fecha, modalidad_contrato, sexo, afiliados FROM fact_ss_afiliacion
        WHERE consulta = 'afil_medios_rg_prov_contrato_sexo' AND territorio_id LIKE 'P%'
          AND fecha IN ((SELECT max(fecha) FROM fact_ss_afiliacion WHERE consulta = 'afil_medios_rg_prov_contrato_sexo'),
                        (SELECT max(fecha) - INTERVAL 12 MONTH FROM fact_ss_afiliacion WHERE consulta = 'afil_medios_rg_prov_contrato_sexo'))""",
    "prov_epa": """SELECT territorio_id AS p, fecha, situacion, miles_personas FROM mart_poblacion_actividad
        WHERE sexo = 'Ambos sexos' AND fecha IN ((SELECT max(fecha) FROM mart_poblacion_actividad),
                                                 (SELECT max(fecha) - INTERVAL 1 YEAR FROM mart_poblacion_actividad))""",
    "prov_empresas": """SELECT territorio_id AS p, anyo, estrato_asalariados, empresas FROM mart_empresas
        WHERE anyo = (SELECT max(anyo) FROM mart_empresas)""",
    "territorios": """SELECT territorio_id, nivel, nombre, ccaa_id, ccaa_nombre FROM dim_territorio WHERE nivel IN ('Nacional', 'CCAA', 'Provincia')""",
}


def filas(con, sql):
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    return [{c: (v.isoformat() if isinstance(v, (date, datetime)) else (round(v, 4) if isinstance(v, float) else v))
             for c, v in zip(cols, r)} for r in cur.fetchall()]


def conectar(parquet):
    if not parquet:
        return duckdb.connect(str(RAIZ / "datos" / "rrhh.duckdb"), read_only=True)
    con = duckdb.connect()
    base = Path(parquet)
    for p in sorted(base.glob("*.parquet")) + sorted(base.glob("marts/*.parquet")):
        con.execute(f"CREATE VIEW {p.stem} AS SELECT * FROM '{p}'")
    return con


# ------------------------------------------------------------------------------------------------ ficha por provincia
def ficha_provincias(out):
    ok = lambda k: isinstance(out.get(k), list) and len(out[k]) > 0
    terr = {t["territorio_id"]: t for t in out["territorios"]} if ok("territorios") else {}
    fichas = {}

    def f(p):
        if p not in fichas and p in terr:
            fichas[p] = {"nombre": terr[p]["nombre"], "ccaa_id": terr[p]["ccaa_id"], "ccaa": terr[p]["ccaa_nombre"]}
        return fichas.get(p)

    nac = {}
    if ok("prov_paro"):
        fechas = sorted({r["fecha"] for r in out["prov_paro"]})
        for r in out["prov_paro"]:
            x = f(r["p"])
            if x is None:
                continue
            clave = "paro" if r["fecha"] == fechas[-1] else "paro_anterior"
            x[clave] = r["paro"]
            if clave == "paro":
                x["paro_mujeres_pct"] = 100 * r["paro_mujeres"] / r["paro"] if r["paro"] else None
                x["paro_fecha"] = r["fecha"]
            nac[clave] = nac.get(clave, 0) + (r["paro"] or 0)
            if clave == "paro":
                nac["paro_mujeres"] = nac.get("paro_mujeres", 0) + (r["paro_mujeres"] or 0)
        nac["paro_fecha"] = fechas[-1]
    if ok("prov_contratos"):
        for r in out["prov_contratos"]:
            x = f(r["p"])
            if x is None or not r["contratos"]:
                continue
            x.update(contratos_12m=r["contratos"], indefinidos_pct=100 * r["indefinidos"] / r["contratos"],
                     convertidos_12m=r["convertidos"], contratos_hasta=r["hasta"])
            for k in ("contratos", "indefinidos", "convertidos"):
                nac[f"c_{k}"] = nac.get(f"c_{k}", 0) + (r[k] or 0)
            nac["contratos_hasta"] = r["hasta"]
    if ok("prov_afiliacion"):
        fechas = sorted({r["fecha"] for r in out["prov_afiliacion"]})
        agg = {}
        for r in out["prov_afiliacion"]:
            mod = (r["modalidad_contrato"] or "").upper()
            per = "act" if r["fecha"] == fechas[-1] else "ant"
            if mod.startswith("TODAS"):  # fila de total de la consulta: es la que da los totales (no se suman modalidades)
                if r["sexo"] == "Total Sexo":
                    agg[(r["p"], per)] = r["afiliados"] or 0
                elif r["sexo"] in ("Mujer", "Mujeres") and per == "act":
                    agg[(r["p"], "mujeres")] = r["afiliados"] or 0
                continue
            if r["sexo"] != "Total Sexo":
                continue
            if per == "act" and mod.startswith("TEMPORAL"):
                agg[(r["p"], "temporal")] = agg.get((r["p"], "temporal"), 0) + (r["afiliados"] or 0)
            if per == "act" and "DISCONTINU" in mod:
                agg[(r["p"], "fd")] = agg.get((r["p"], "fd"), 0) + (r["afiliados"] or 0)
        for p in {k[0] for k in agg}:
            x = f(p)
            if x is None or not agg.get((p, "act")):
                continue
            act = agg[(p, "act")]
            x.update(afiliados_rg=act, afiliados_rg_anterior=agg.get((p, "ant")),
                     temporal_pct=100 * agg.get((p, "temporal"), 0) / act, fd_pct=100 * agg.get((p, "fd"), 0) / act,
                     mujeres_afil_pct=100 * agg.get((p, "mujeres"), 0) / act, afiliacion_fecha=fechas[-1])
            for k, v in (("a_act", act), ("a_ant", agg.get((p, "ant"), 0)), ("a_temp", agg.get((p, "temporal"), 0)),
                         ("a_fd", agg.get((p, "fd"), 0)), ("a_muj", agg.get((p, "mujeres"), 0))):
                nac[k] = nac.get(k, 0) + v
        nac["afiliacion_fecha"] = fechas[-1] if fechas else None
    if ok("prov_epa"):
        fechas = sorted({r["fecha"] for r in out["prov_epa"]})
        tmp = {}
        for r in out["prov_epa"]:
            tmp[(r["p"], r["fecha"], r["situacion"])] = r["miles_personas"]
        for p in {k[0] for k in tmp}:
            def tasa(fe):
                act, par = tmp.get((p, fe, "Activos")), tmp.get((p, fe, "Parados"))
                return 100 * par / act if act and par is not None else None
            if p == "N00":
                nac.update(tasa_paro=tasa(fechas[-1]), tasa_paro_anterior=tasa(fechas[0]), epa_fecha=fechas[-1])
                continue
            x = f(p)
            if x is not None:
                x.update(tasa_paro=tasa(fechas[-1]), tasa_paro_anterior=tasa(fechas[0]), epa_fecha=fechas[-1])
    if ok("ett_territorio"):
        anyo_max = max(r["anyo"] for r in out["ett_territorio"])
        for r in out["ett_territorio"]:
            p = r["provincia_id"] if r["nivel"] != "Nacional" else "N00"
            if not p:
                continue
            destino = nac if p == "N00" else f(p)
            if destino is None:
                continue
            if r["anyo"] == anyo_max:
                destino.update(cpd=r["cpd_total"], cpd_fd_pct=100 * r["cpd_fijos_discontinuos"] / r["cpd_total"] if r["cpd_total"] else None,
                               cpd_por_cesion=r["cpd_total"] / r["cesiones"] if r["cesiones"] else None, cpd_mes=r["mes"], cpd_anyo=r["anyo"])
    if ok("ett_resumen"):  # variación interanual oficial del ministerio (por CCAA; no se publica por provincia)
        var_ccaa = {r["territorio_id"]: r["variacion_pct"] for r in out["ett_resumen"] if r["cuadro"] == "CPD por CCAA"}
        nac["cpd_var"] = var_ccaa.get("N00")
        for x in fichas.values():
            x["cpd_var_ccaa"] = var_ccaa.get(x["ccaa_id"])
    if ok("it_provincias"):  # incapacidad temporal del último ejercicio publicado
        ult = max((r["anyo"], r["mes_hasta"]) for r in out["it_provincias"])
        for r in out["it_provincias"]:
            if (r["anyo"], r["mes_hasta"]) != ult:
                continue
            destino = nac if r["nivel"] == "Nacional" else (f(r["provincia_id"]) if r["nivel"] == "Provincia" else None)
            if destino is not None:
                destino.update(it_incidencia=r["incidencia_media_mensual_mil"], it_duracion=r["duracion_media_dias"],
                               it_prevalencia=r["prevalencia_mil"], it_periodo=f"{r['periodo']} {r['anyo']}")
    if ok("accidentes"):
        for r in out["accidentes"]:
            p = r["territorio_id"]
            if not p:
                continue
            if p == "N00":
                nac.update(acc_indice=r["indice"], acc_hasta=r["periodo_hasta"])
            elif p.startswith("P") and f(p) is not None:
                fichas[p].update(acc_indice=r["indice"], acc_hasta=r["periodo_hasta"], acc_mortales=r["accidentes_mortales"])
            elif p.startswith("C"):  # CCAA uniprovinciales (Madrid, Murcia…): el dato de la CCAA es el de su provincia
                provs = [q for q in terr if terr[q]["nivel"] == "Provincia" and terr[q]["ccaa_id"] == p]
                if len(provs) == 1 and f(provs[0]) is not None and "acc_indice" not in fichas[provs[0]]:
                    fichas[provs[0]].update(acc_indice=r["indice"], acc_hasta=r["periodo_hasta"], acc_mortales=r["accidentes_mortales"])
    if ok("convenios_detalle"):
        for r in out["convenios_detalle"]:
            if r["desglose"] != "Territorio" or r["ambito_funcional"] != "Total" or r["anyo"] != max(
                    x["anyo"] for x in out["convenios_detalle"]):
                continue
            if r["nivel"] == "Nacional":
                nac.update(conv_var=r["variacion"], conv_jornada=r["jornada"], conv_trab=r["trabajadores"])
            p = r["provincia_id"]
            if p and f(p) is not None:
                fichas[p].update(conv_var=r["variacion"], conv_jornada=r["jornada"], conv_trab=r["trabajadores"])
    if ok("prov_empresas"):
        grandes = ("De 50 a 99", "De 100 a 199", "De 200 a 249", "De 250 a 999", "De 1000 a 4999", "De 5000 o más asalariados")
        for r in out["prov_empresas"]:
            destino = nac if r["p"] == "N00" else f(r["p"])
            if destino is None:
                continue
            if r["estrato_asalariados"] == "Total":
                destino["empresas"] = r["empresas"]
            elif r["estrato_asalariados"] in grandes:
                destino["empresas_50"] = destino.get("empresas_50", 0) + (r["empresas"] or 0)
            elif r["estrato_asalariados"] != "Sin asalariados":
                destino["empresas_con_asal"] = destino.get("empresas_con_asal", 0) + (r["empresas"] or 0)
    # contexto de la CCAA (coste, horas no trabajadas, paro EPA anual)
    ccaa = {}
    if ok("coste_ccaa"):
        for r in out["coste_ccaa"]:
            ccaa.setdefault(r["territorio_id"], {})["coste_" + ("mes" if "mes" in r["base"] else "hora")] = r["euros"]
    if ok("horas_ccaa"):
        ult = max(r["fecha"] for r in out["horas_ccaa"])
        for r in out["horas_ccaa"]:
            if r["fecha"] == ult and r["pactadas"]:
                ccaa.setdefault(r["territorio_id"], {})["no_trab_pct"] = 100 * r["no_trabajadas"] / r["pactadas"]
    for p, x in fichas.items():
        x["contexto_ccaa"] = ccaa.get(x["ccaa_id"], {})
    # totales nacionales con las mismas definiciones
    if nac.get("paro"):
        nac["paro_mujeres_pct"] = 100 * nac.pop("paro_mujeres", 0) / nac["paro"]
    if nac.get("c_contratos"):
        nac.update(contratos_12m=nac["c_contratos"], indefinidos_pct=100 * nac["c_indefinidos"] / nac["c_contratos"],
                   convertidos_12m=nac["c_convertidos"])
    if nac.get("a_act"):
        nac.update(afiliados_rg=nac["a_act"], afiliados_rg_anterior=nac["a_ant"], temporal_pct=100 * nac["a_temp"] / nac["a_act"],
                   fd_pct=100 * nac["a_fd"] / nac["a_act"], mujeres_afil_pct=100 * nac["a_muj"] / nac["a_act"])
    nac = {k: v for k, v in nac.items() if not k.startswith(("c_", "a_"))}
    nac["nombre"] = "España"
    nac["contexto_ccaa"] = ccaa.get("N00", {})
    return {"N00": nac, **dict(sorted(fichas.items(), key=lambda kv: kv[1]["nombre"]))}


# ------------------------------------------------------------------------------------------------ conclusiones
def cap(s):
    """'SANTA CRUZ DE TENERIFE' -> 'Santa Cruz de Tenerife'."""
    s = str(s).strip()
    if s != s.upper():
        return s
    return " ".join(w if w in ("de", "del", "la", "las", "los", "y") else w.capitalize() for w in s.lower().split())


def conclusiones(out, ficha):
    """Frases cortas calculadas con los datos de este fichero (sin estimaciones externas). Cada una dice su fuente."""
    c = []
    ok = lambda k: isinstance(out.get(k), list) and out[k]
    pct = lambda v, d=1: f"{v:.{d}f}".replace(".", ",") + " %"
    num = lambda v: f"{v:,.0f}".replace(",", ".")
    # poder adquisitivo acumulado desde 2021
    if ok("convenios_ipc"):
        filas_ok = [r for r in out["convenios_ipc"] if r["anyo"] >= 2021 and r["pactada"] is not None and r["ipc"] is not None]
        if filas_ok:
            a = b = 1.0
            for r in filas_ok:
                a *= 1 + r["pactada"] / 100; b *= 1 + r["ipc"] / 100
            c.append({"tema": "Convenios", "nivel": "aviso" if a < b else "info",
                      "texto": f"De {filas_ok[0]['anyo']} a {filas_ok[-1]['anyo']} las subidas pactadas en convenio suman "
                               f"{pct(100 * (a - 1))} y el IPC de diciembre {pct(100 * (b - 1))}: "
                               f"{'pérdida' if a < b else 'ganancia'} de poder adquisitivo de {pct(abs(100 * (a / b - 1)))}.",
                      "fuente": "Ministerio de Trabajo (CCT) e INE (IPC)"})
    if ok("convenios_ultimo") and ok("ipc_ultimo"):
        u, i = out["convenios_ultimo"][0], out["ipc_ultimo"][0]
        c.append({"tema": "Convenios", "nivel": "aviso" if u["pactada"] < i["valor"] else "info",
                  "texto": f"En {u['anyo']} los convenios registrados hasta el mes {u['mes']} suben {pct(u['pactada'], 2)}, "
                           f"frente a un IPC interanual del {pct(i['valor'])}.", "fuente": "Ministerio de Trabajo e INE"})
    # CPD: fijos discontinuos y rotación
    n = ficha.get("N00", {})
    if n.get("cpd") and n.get("cpd_var") is not None:
        meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
        c.append({"tema": "CPD", "nivel": "info",
                  "texto": f"Las ETT han firmado {num(n['cpd'])} contratos de puesta a disposición de enero a {meses[n['cpd_mes'] - 1]} "
                           f"de {n['cpd_anyo']} ({'+' if n['cpd_var'] >= 0 else ''}{pct(n['cpd_var'])} sobre el mismo periodo del año anterior). "
                           f"El {pct(n['cpd_fd_pct'])} son para trabajadores fijos discontinuos y cada cesión de un trabajador genera "
                           f"de media {str(round(n['cpd_por_cesion'], 2)).replace('.', ',')} CPD.",
                  "fuente": "Ministerio de Trabajo (ETT-1 y ETT-R2)"})
    if ok("ett_resumen"):
        ccaa = [r for r in out["ett_resumen"] if r["cuadro"] == "CPD por CCAA" and r["territorio_id"] != "N00" and r["valor"] > 10000]
        if ccaa:
            top = max(ccaa, key=lambda r: r["variacion_pct"]); bajo = min(ccaa, key=lambda r: r["variacion_pct"])
            c.append({"tema": "CPD", "nivel": "info",
                      "texto": f"Por comunidades, el uso de ETT crece más en {top['nombre']} ({'+' if top['variacion_pct'] >= 0 else ''}{pct(top['variacion_pct'])}) "
                               f"y menos en {bajo['nombre']} ({'+' if bajo['variacion_pct'] >= 0 else ''}{pct(bajo['variacion_pct'])}).",
                      "fuente": "Ministerio de Trabajo (ETT-R2)"})
    if ok("ett_anual"):
        fd = {r["anyo"]: r["valor"] for r in out["ett_anual"] if r["indicador"] == "CPD por modalidad" and r["categoria"] == "Fijos discontinuos"}
        tot = {r["anyo"]: r["valor"] for r in out["ett_anual"] if r["indicador"] == "CPD por modalidad" and r["categoria"] == "Total"}
        anyos = sorted(a for a in tot if a in fd and tot[a])
        if len(anyos) >= 2 and 2022 in tot:
            ult = anyos[-1]
            c.append({"tema": "CPD", "nivel": "info",
                      "texto": f"Tras la reforma laboral, los CPD para fijos discontinuos pasan de 0 en 2021 a {num(fd[ult])} en {ult} "
                               f"({pct(100 * fd[ult] / tot[ult])} del total). Un fijo discontinuo puede encadenar varios CPD en el año: "
                               f"contar CPD no es contar personas.", "fuente": "Ministerio de Trabajo (ETT-E1)"})
    # absentismo
    if ok("horas_actividad"):
        ult = max(r["fecha"] for r in out["horas_actividad"])
        f_ = [r for r in out["horas_actividad"] if r["fecha"] == ult and r["pactadas"] and r["it"] is not None and len(r["actividad_codigo"] or "") == 1]
        tot = next((r for r in out["horas_actividad"] if r["fecha"] == ult and (r["actividad_codigo"] or "") == "B_S"), None)
        if f_ and tot and tot["pactadas"]:
            top = max(f_, key=lambda r: r["it"] / r["pactadas"])
            c.append({"tema": "Absentismo", "nivel": "info",
                      "texto": f"Las bajas por incapacidad temporal se llevan el {pct(100 * tot['it'] / tot['pactadas'])} de las horas pactadas "
                               f"(media de todos los sectores). El sector con más peso de la IT es {top['actividad'].lower()} "
                               f"({pct(100 * top['it'] / top['pactadas'])}).", "fuente": "INE (ETCL, tabla 6043)"})
    if ok("horas_ccaa"):
        ult = max(r["fecha"] for r in out["horas_ccaa"])
        f_ = [r for r in out["horas_ccaa"] if r["fecha"] == ult and r["territorio_id"] != "N00" and r["pactadas"]]
        if f_:
            top = max(f_, key=lambda r: r["no_trabajadas"] / r["pactadas"])
            low = min(f_, key=lambda r: r["no_trabajadas"] / r["pactadas"])
            c.append({"tema": "Absentismo", "nivel": "info",
                      "texto": f"Por comunidades, las horas pactadas no trabajadas van del {pct(100 * low['no_trabajadas'] / low['pactadas'])} "
                               f"de {low['ccaa']} al {pct(100 * top['no_trabajadas'] / top['pactadas'])} de {top['ccaa']} "
                               f"(incluye vacaciones, festivos y bajas).", "fuente": "INE (ETCL, tabla 6063)"})
    # incapacidad temporal por provincia
    if ok("it_provincias"):
        ult = max((r["anyo"], r["mes_hasta"]) for r in out["it_provincias"])
        prov = [r for r in out["it_provincias"] if (r["anyo"], r["mes_hasta"]) == ult and r["nivel"] == "Provincia"
                and r["incidencia_media_mensual_mil"]]
        n_ = next((r for r in out["it_provincias"] if (r["anyo"], r["mes_hasta"]) == ult and r["nivel"] == "Nacional"), None)
        if prov and n_:
            top = max(prov, key=lambda r: r["incidencia_media_mensual_mil"])
            lar = max(prov, key=lambda r: r["duracion_media_dias"] or 0)
            c.append({"tema": "Absentismo", "nivel": "info",
                      "texto": f"Bajas por incapacidad temporal ({n_['periodo'].lower()} {n_['anyo']}): cada mes empiezan "
                               f"{str(round(n_['incidencia_media_mensual_mil'], 1)).replace('.', ',')} bajas por cada mil trabajadores protegidos en España "
                               f"y duran {n_['duracion_media_dias']:.0f} días de media. La incidencia más alta es la de {cap(top['nombre'])} "
                               f"({str(round(top['incidencia_media_mensual_mil'], 1)).replace('.', ',')}) y la duración más larga, la de {cap(lar['nombre'])} "
                               f"({lar['duracion_media_dias']:.0f} días).", "fuente": "Seguridad Social (estadística de IT)"})
    # accidentes
    if ok("accidentes"):
        prov = [r for r in out["accidentes"] if (r["territorio_id"] or "").startswith("P") and r["indice"]]
        n_ = next((r for r in out["accidentes"] if r["territorio_id"] == "N00"), None)
        if prov and n_:
            top = max(prov, key=lambda r: r["indice"])
            c.append({"tema": "Accidentes", "nivel": "info",
                      "texto": f"{top['nombre'].strip()} tiene el mayor índice de accidentes en jornada con baja: {top['indice']:.0f} al mes por cada "
                               f"100.000 afiliados, frente a {n_['indice']:.0f} de media en España.", "fuente": "Ministerio de Trabajo (ATR-I1.1)"})
    # temporalidad y contratación
    if n.get("indefinidos_pct"):
        c.append({"tema": "Contratación", "nivel": "info",
                  "texto": f"En los últimos 12 meses, el {pct(n['indefinidos_pct'])} de los contratos registrados son indefinidos iniciales "
                           f"y además {num(n['convertidos_12m'])} contratos temporales se han convertido en indefinidos.",
                  "fuente": "SEPE (contratos por municipio)"})
    if ok("salarios_ees_detalle"):
        g = {(r["sexo"], r["categoria"]): r["euros"] for r in out["salarios_ees_detalle"]
             if r["territorio_id"] == "N00" and r["sector"] == "Todas las secciones" and r["desglose"] == "Antigüedad"}
        if g.get(("Ambos sexos", "Menos de 1 año")) and g.get(("Ambos sexos", "30 y más años")):
            c.append({"tema": "Salarios", "nivel": "info",
                      "texto": f"La antigüedad pesa: el salario medio pasa de {num(g[('Ambos sexos', 'Menos de 1 año')])} € al año con menos de un año "
                               f"en la empresa a {num(g[('Ambos sexos', '30 y más años')])} € con 30 años o más (EES 2022).",
                      "fuente": "INE (EES 2022, tabla 36861)"})
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", help="carpeta con los Parquet publicados (modelo/) en vez de datos/rrhh.duckdb")
    ap.add_argument("--salida", default=str(SALIDA))
    a = ap.parse_args()
    con = conectar(a.parquet)
    out = {"generado": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
    for nombre, sql in BLOQUES.items():
        try:
            out[nombre] = filas(con, sql)
        except Exception as e:
            out[nombre] = {"error": f"{type(e).__name__}: {e}"[:300]}
    for ruta in (RAIZ / "datos" / "qa" / "alertas.csv", Path(a.parquet or "-") / "alertas.csv"):
        if ruta.exists():
            with open(ruta, encoding="utf-8") as fh:
                out["alertas"] = [r for r in csv.DictReader(fh, delimiter=";") if r["tipo"] != "error"]
            break
    try:
        out["ficha"] = ficha_provincias(out)
    except Exception as e:
        out["ficha"] = {"error": f"{type(e).__name__}: {e}"[:300]}
    try:
        out["conclusiones"] = conclusiones(out, out["ficha"] if isinstance(out["ficha"], dict) else {})
    except Exception as e:
        out["conclusiones"] = {"error": f"{type(e).__name__}: {e}"[:300]}
    for k in [k for k in out if k.startswith("prov_")] + ["territorios"]:
        out.pop(k, None)  # ya están en la ficha
    salida = Path(a.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps(out, ensure_ascii=False, default=str, separators=(",", ":")), encoding="utf-8")
    errores = {k: v["error"] for k, v in out.items() if isinstance(v, dict) and "error" in v}
    print(f"datos_visual.json: {salida.stat().st_size / 1e3:.0f} kB · {len(out) - len(errores)} bloques OK"
          + (f" · con error: {list(errores)}" if errores else ""))
    for k, v in errores.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    sys.exit(main())
