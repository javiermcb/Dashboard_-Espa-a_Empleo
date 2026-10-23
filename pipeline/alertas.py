#!/usr/bin/env python3
"""
pipeline/alertas.py — Parte proactiva: novedades y alertas sobre indicadores, tras cada carga.

Entrada:  datos/rrhh.duckdb (modelo.py) y resultados/pipeline/periodos.csv (últimos periodos de la carga anterior)
Salida:   datos/qa/alertas.csv     una fila por alerta (tipo, indicador, territorio, periodo, valor, referencia, mensaje, nivel)
          datos/qa/alertas.md      el mismo contenido en texto, para leerlo de un vistazo
          datos/qa/periodos.csv    últimos periodos de esta carga (sustituye al anterior en resultados/pipeline/)
Niveles:  'novedad' (hay periodo nuevo), 'aviso' (supera el umbral), 'info' (dato de seguimiento).
Cada regla es independiente: si una no se puede calcular, se anota y se sigue.
"""
import csv, re, sys
from datetime import date, datetime, timezone
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
QA = RAIZ / "datos" / "qa"
PREVIOS = RAIZ / "resultados" / "pipeline" / "periodos.csv"
SECTOR_TOTAL = "Industria, construcción y servicios%"   # total de la ETCL
UMBRAL_PARO_PCT = 10.0      # subida interanual del paro EPA por provincia que se marca como aviso
MIN_PARADOS_MILES = 15.0    # por debajo, la muestra provincial de la EPA es demasiado pequeña para avisar de variaciones
UMBRAL_HNT_PP = 0.5         # subida interanual (puntos) del % de horas no trabajadas sobre pactadas


def es(v, d=1, signo=False):
    """Número con formato español: 1.234,5 (con signo + si se pide)."""
    t = f"{v:{'+' if signo else ''},.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return t


def nom(s):
    """'Balears, Illes' -> 'Illes Balears'; 'Madrid, Comunidad de' -> 'Madrid'; 'Palmas (Las)' -> 'Las Palmas'."""
    s = str(s or "").strip()
    s = re.sub(r",? \(?(Comunidad Foral|Comunidad|Principado|Región) de\)?$", "", s)
    m = re.match(r"^(.+?)(?:, | \()(Illes|La|Las|Los|A|Les|El|O)\)?$", s, flags=re.I)
    return f"{m.group(2).capitalize()} {m.group(1)}" if m else s.replace("Castilla - La Mancha", "Castilla-La Mancha")


def miles(n):
    return f"{n:,.0f}".replace(",", ".")  # 2732469 -> 2.732.469


def main():
    con = duckdb.connect(str(RAIZ / "datos" / "rrhh.duckdb"), read_only=True)
    tablas = {r[0] for r in con.execute("SELECT table_name FROM information_schema.tables").fetchall()}
    alertas = []

    def add(tipo, indicador, territorio, periodo, valor, referencia, mensaje, nivel="info"):
        alertas.append([tipo, indicador, territorio, str(periodo or ""), None if valor is None else round(valor, 2),
                        None if referencia is None else round(referencia, 2), mensaje, nivel])

    def regla(nombre, f):
        try:
            f()
        except Exception as e:
            add("error", nombre, "", "", None, None, f"No calculable: {type(e).__name__}: {e}"[:300], "info")

    # 1) Novedades: último periodo por tabla frente a la carga anterior
    actuales = {}
    for t, f in con.execute("SELECT tabla_id, max(fecha) FROM fact_ine GROUP BY 1").fetchall():
        actuales[f"ine:{t}"] = str(f)
    fuentes = {"fact_sepe_paro_municipio": "fecha", "fact_sepe_contratos_municipio": "fecha", "fact_ss_afiliacion": "fecha",
               "fact_cpd_actividad": "fecha", "fact_accidentes": "periodo_hasta",
               "fact_convenios": "make_date(anyo_efectos, coalesce(mes_registro, 12), 1)"}
    for t, col in fuentes.items():
        if t in tablas:
            actuales[t] = str(con.execute(f"SELECT max({col}) FROM {t}").fetchone()[0])
    previos = {}
    if PREVIOS.exists():
        with open(PREVIOS, encoding="utf-8") as fh:
            previos = {r["tabla"]: r["ultimo_periodo"] for r in csv.DictReader(fh, delimiter=";")}
    for t, p in sorted(actuales.items()):
        if previos and p != previos.get(t):
            add("novedad", t, "", p, None, None, f"Nuevo periodo {p} (antes: {previos.get(t) or 'sin datos'})", "novedad")
    QA.mkdir(parents=True, exist_ok=True)
    with open(QA / "periodos.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";"); w.writerow(["tabla", "ultimo_periodo"]); w.writerows(sorted(actuales.items()))

    # 1b) Estado de la carga: tablas que no se han podido actualizar o que no superan un control de calidad
    for fichero, col_tabla in (("ine_carga.csv", "tabla_id"), ("fuentes_carga.csv", "tabla")):
        p = QA / fichero
        if not p.exists():
            continue
        with open(p, encoding="utf-8") as fh:
            for r in csv.DictReader(fh, delimiter=";"):
                det = r.get("error") or r.get("detalle") or ""
                nombre = ("ine:" if fichero.startswith("ine") else "") + r[col_tabla]
                if r["estado"] == "ANTERIOR":
                    add("carga", nombre, "", "", None, None, f"No actualizada en esta carga: {det}", "aviso")
                    # si la última carga buena tiene más de 3 días, aviso aparte (se notifica una vez al pasar el umbral)
                    m = re.search(r"última carga buena \((\d{4}-\d{2}-\d{2})", det)
                    if m and (date.today() - date.fromisoformat(m.group(1))).days > 3:
                        add("carga", nombre, "", "", None, None,
                            f"Desactualizada más de 3 días: última carga buena el {m.group(1)}", "aviso")
                elif r["estado"] == "ERROR":
                    add("carga", nombre, "", "", None, None, f"Sin datos (falló y no hay carga buena previa): {det}", "aviso")
                elif r["estado"] == "AVISO":
                    add("carga", nombre, "", "", None, None, f"Control de calidad: {det}", "aviso")

    # 2) Subida salarial pactada en convenios frente al IPC
    def convenios_ipc():
        anyo, mes, pactada = con.execute("""SELECT anyo_efectos, mes_registro, variacion_salarial_pactada_pct FROM fact_convenios
            WHERE tipo_dato = 'Registrados hasta el mes' ORDER BY anyo_efectos DESC, mes_registro DESC LIMIT 1""").fetchone()
        fecha, ipc = con.execute("""SELECT fecha, valor FROM mart_precios WHERE indice = 'IPC' AND indicador = 'Variación anual'
            AND territorio_id = 'N00' ORDER BY fecha DESC LIMIT 1""").fetchone()
        dif = pactada - ipc
        add("indicador", "Convenios vs IPC", "N00", f"convenios {anyo} hasta mes {mes} · IPC {fecha}", pactada, ipc,
            f"Subida pactada {es(pactada, 2)} % frente a IPC interanual {es(ipc, 2)} % ({es(dif, 2, True)} puntos)",
            "aviso" if dif < 0 else "info")
    if "fact_convenios" in tablas:
        regla("Convenios vs IPC", convenios_ipc)

    # 3) Coste laboral por trabajador: variación interanual frente al IPC
    def coste_ipc():
        r = con.execute(f"""WITH c AS (SELECT fecha, euros FROM mart_coste_laboral WHERE territorio_id = 'N00'
                AND componente = 'Coste laboral total' AND base = 'Por trabajador y mes' AND sector LIKE '{SECTOR_TOTAL}')
            SELECT a.fecha, a.euros, b.euros FROM c a JOIN c b ON b.fecha = a.fecha - INTERVAL 1 YEAR
            ORDER BY a.fecha DESC LIMIT 1""").fetchone()
        var = 100 * (r[1] / r[2] - 1)
        ipc = con.execute("""SELECT valor FROM mart_precios WHERE indice = 'IPC' AND indicador = 'Variación anual'
            AND territorio_id = 'N00' AND fecha <= ? ORDER BY fecha DESC LIMIT 1""", [r[0]]).fetchone()[0]
        add("indicador", "Coste laboral por trabajador (interanual) vs IPC", "N00", r[0], var, ipc,
            f"Coste laboral total por trabajador {es(r[1], 0)} €/mes, {es(var, 1, True)} % interanual (IPC {es(ipc)} %)")
    regla("Coste laboral vs IPC", coste_ipc)

    # 4) Paro EPA por provincia: mayores subidas interanuales
    def paro_provincias():
        filas = con.execute("""WITH p AS (SELECT fecha, territorio_id, miles_personas FROM mart_poblacion_actividad
                WHERE situacion = 'Parados' AND sexo = 'Ambos sexos' AND territorio_id LIKE 'P%'),
            u AS (SELECT max(fecha) AS f FROM p)
            SELECT a.territorio_id, t.nombre, a.fecha, a.miles_personas, b.miles_personas,
                   100 * (a.miles_personas / b.miles_personas - 1) AS var
            FROM p a JOIN p b ON b.territorio_id = a.territorio_id AND b.fecha = a.fecha - INTERVAL 1 YEAR
            JOIN dim_territorio t ON t.territorio_id = a.territorio_id
            WHERE a.fecha = (SELECT f FROM u) AND b.miles_personas >= ? ORDER BY var DESC LIMIT 5""", [MIN_PARADOS_MILES]).fetchall()
        for tid, nombre, f, act, ant, var in filas:
            add("indicador", "Paro EPA: subida interanual", f"{tid} {nom(nombre)}", f, var, ant,
                f"{nom(nombre)}: {es(act)} mil parados, {es(var, 1, True)} % interanual (EPA: en una provincia la muestra es "
                "pequeña; confirmar con el paro registrado)", "aviso" if var >= UMBRAL_PARO_PCT else "info")
    regla("Paro por provincia", paro_provincias)

    # 5) Horas no trabajadas sobre pactadas (ETCL) por CCAA: subidas interanuales
    def horas_no_trabajadas():
        filas = con.execute(f"""WITH h AS (SELECT fecha, territorio_id,
                    100 * max(horas_trabajador_mes) FILTER (WHERE concepto = 'Horas no trabajadas')
                        / max(horas_trabajador_mes) FILTER (WHERE concepto = 'Horas pactadas') AS pct
                FROM mart_tiempo_trabajo WHERE jornada = 'Ambas jornadas' AND sector LIKE '{SECTOR_TOTAL}' GROUP BY 1, 2),
            u AS (SELECT max(fecha) AS f FROM h)
            SELECT a.territorio_id, t.nombre, a.fecha, a.pct, a.pct - b.pct AS dif
            FROM h a JOIN h b ON b.territorio_id = a.territorio_id AND b.fecha = a.fecha - INTERVAL 1 YEAR
            JOIN dim_territorio t ON t.territorio_id = a.territorio_id
            WHERE a.fecha = (SELECT f FROM u) ORDER BY dif DESC LIMIT 5""").fetchall()
        for tid, nombre, f, pct, dif in filas:
            add("indicador", "Horas no trabajadas / pactadas", f"{tid} {nom(nombre)}", f, pct, dif,
                f"{nom(nombre)}: {es(pct)} % de las horas pactadas no se trabajan ({es(dif, 2, True)} puntos interanual)",
                "aviso" if dif >= UMBRAL_HNT_PP else "info")
    regla("Horas no trabajadas", horas_no_trabajadas)

    # 6) Siniestralidad: provincias con mayor índice de incidencia (acumulado del año)
    def accidentes():
        for tid, nombre, hasta, ind in con.execute("""SELECT territorio_id, territorio_nombre, periodo_hasta, indice_incidencia
                FROM fact_accidentes WHERE territorio_id LIKE 'P%' ORDER BY indice_incidencia DESC LIMIT 5""").fetchall():
            add("indicador", "Índice de incidencia de accidentes", f"{tid} {nombre}", hasta, ind, None,
                f"{nom(nombre)}: índice de incidencia {es(ind)} (acumulado enero-{str(hasta)[:7]})")
    if "fact_accidentes" in tablas:
        regla("Accidentes", accidentes)

    # 7) Contratos de puesta a disposición: acumulado del año frente al mismo periodo del año anterior
    def cpd():
        anyo, mes = con.execute("""SELECT year(max(fecha)), month(max(fecha)) FROM fact_cpd_actividad""").fetchone()
        act, ant = con.execute("""SELECT sum(cpd) FILTER (WHERE year(fecha) = ?), sum(cpd) FILTER (WHERE year(fecha) = ? - 1)
            FROM fact_cpd_actividad WHERE seccion_cnae = 'TOTAL' AND month(fecha) <= ?""", [anyo, anyo, mes]).fetchone()
        var = 100 * (act / ant - 1)
        add("indicador", "CPD acumulados del año", "N00", f"{anyo} enero-mes {mes}", act, ant,
            f"{miles(act)} contratos de puesta a disposición, {es(var, 1, True)} % frente al mismo periodo de {anyo - 1}")
    if "fact_cpd_actividad" in tablas:
        regla("CPD", cpd)

    # 8) Vacantes: último trimestre frente al mismo del año anterior
    def vacantes():
        f, act, ant = con.execute("""SELECT a.fecha, a.vacantes, b.vacantes FROM mart_vacantes a JOIN mart_vacantes b
            ON b.territorio_id = a.territorio_id AND b.fecha = a.fecha - INTERVAL 1 YEAR
            WHERE a.territorio_id = 'N00' ORDER BY a.fecha DESC LIMIT 1""").fetchone()
        add("indicador", "Vacantes", "N00", f, act, ant, f"{miles(act)} vacantes, {es(100 * (act / ant - 1), 1, True)} % interanual")
    regla("Vacantes", vacantes)

    cab = ["tipo", "indicador", "territorio", "periodo", "valor", "referencia", "mensaje", "nivel"]
    with open(QA / "alertas.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";"); w.writerow(cab); w.writerows(alertas)
    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    orden = {"aviso": 0, "novedad": 1, "info": 2}
    lineas = [f"# Alertas RRHH 360 · {ahora}", ""]
    for nivel, titulo in (("aviso", "Avisos"), ("novedad", "Datos nuevos"), ("info", "Seguimiento")):
        grupo = [a for a in alertas if a[7] == nivel]
        if grupo:
            lineas += [f"## {titulo}", ""] + [f"- **{a[1]}** · {a[6]}" for a in sorted(grupo, key=lambda a: a[1])] + [""]
    if not previos:
        lineas += ["_Primera ejecución: no hay carga anterior con la que comparar los periodos._"]
    (QA / "alertas.md").write_text("\n".join(lineas), encoding="utf-8")
    print(f"{len(alertas)} alertas ({sum(a[7] == 'aviso' for a in alertas)} avisos)")


if __name__ == "__main__":
    sys.exit(main())
