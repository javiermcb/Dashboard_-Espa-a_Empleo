#!/usr/bin/env python3
"""
pipeline/mites_detalle.py — Lectores de detalle del Ministerio de Trabajo (los usa pipeline/fuentes.py).

Cada función recibe los bytes del fichero Excel (más su URL) y devuelve (cabecera, filas). Así se pueden probar
en local con un fichero descargado:  python pipeline/mites_detalle.py ett resultados/fuentes_raw/mites_ett_2026_07.xlsx

ETT (Empresas de trabajo temporal, ETT_MM_AAAA.xlsx)
  ett_mensual(datos)      ETT-E1, ETT-E3, ETT-E4: serie mensual y anual en formato largo (indicador, categoría, valor)
                          · CPD por modalidad (obra o servicio, circunstancias, fijos discontinuos, sustitución…)
                          · cesiones de trabajadores y número de ETT
                          · trabajadores contratados por ETT por sexo, nacionalidad y edad
                          · contratos de trabajo de las ETT por tipo (fijo discontinuo, circunstancias…)
  ett_territorio(datos)   ETT-1: cesiones y CPD por modalidad, por CCAA y provincia (mes y acumulado del año)
  ett_actividad(datos)    ETT-2: CPD por modalidad, por sector y división CNAE a 2 dígitos (mes y acumulado)
  ett_resumen(datos)      ETT-R1..R4: acumulado del año por sección, CCAA, perfil del trabajador y afiliados a ETT,
                          con la variación oficial frente al mismo periodo del año anterior
Convenios (CCT_MM_AAAA.xls)
  cct_detalle(datos)      CCT-2.3 ámbito, CCT-2.5(a) sector/sección, CCT-2.6 CCAA y provincia, CCT-2.7 cláusula de
                          garantía salarial, CCT-2.8 tramos de jornada: convenios, empresas, trabajadores,
                          variación salarial pactada y jornada media (si la hoja la trae)
Accidentes (ATR_MM_AAAA.xlsx)
  atr_detalle(datos)      ATR-A2.1 sector/sección/división, ATR-A3 sexo y edad, ATR-I2.1 índice por sección,
                          ATR-A1.1 provincia (por gravedad): accidentes en jornada con baja, acumulado del año
"""
import io, re, sys, unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
         "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}


# ------------------------------------------------------------------------------------------------ utilidades
def libro(datos):
    """{nombre de hoja sin espacios: filas} de un .xls o .xlsx."""
    if datos[:4] == b"\xd0\xcf\x11\xe0":
        import xlrd
        wb = xlrd.open_workbook(file_contents=datos)
        return {h.name.strip(): [h.row_values(i) for i in range(h.nrows)] for h in wb.sheets()}
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(datos), read_only=True, data_only=True)
    return {n.strip(): [list(r) for r in wb[n].iter_rows(values_only=True, max_col=40)] for n in wb.sheetnames}


def celda(f, i):
    v = f[i] if i < len(f) else None
    return "" if v is None else re.sub(r"\s+", " ", str(v)).strip()


def num(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s or s in ("-", ".", "..") or s.startswith("<"):
        return None
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def norm_nombre(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = s.replace("c. foral", "comunidad foral").replace("s. c. ", "santa cruz de ").replace("s.c.", "santa cruz de ")
    palabras = [p for p in re.split(r"[^a-z]+", s) if p and p not in ("de", "la", "el", "las", "los", "y", "del")]
    return " ".join(sorted(palabras))


def territorios():
    import csv
    with open(RAIZ / "pipeline" / "config" / "territorio.csv", encoding="utf-8") as f:
        filas = list(csv.DictReader(f, delimiter=";"))
    por_nombre, prov_de_ccaa = {}, {}
    for t in filas:
        for n in t["nombre"].split("/") + [t["nombre"]]:
            por_nombre.setdefault((t["nivel"], norm_nombre(n)), t["territorio_id"])
    for t in filas:
        if t["nivel"] == "Provincia":
            prov_de_ccaa.setdefault(t["ccaa_id"], []).append(t["territorio_id"])
    alias = {("CCAA", "ceuta melilla"): "C1819", ("Provincia", "tenerife"): "P38"}
    for nombre, cid in (("comunidad valenciana", "C10"), ("madrid", "C13"), ("murcia", "C14"), ("navarra", "C15"),
                        ("asturias", "C03"), ("cantabria", "C06"), ("rioja", "C17"), ("illes balears", "C04"),
                        ("castilla mancha", "C08"), ("castilla leon", "C07")):
        alias[("CCAA", norm_nombre(nombre))] = cid
    por_nombre.update(alias)
    return por_nombre, {c: p[0] for c, p in prov_de_ccaa.items() if len(p) == 1}


def resolver(nombre, es_ccaa, terr, uniprov):
    """(territorio_id, provincia_id) de un nombre de CCAA (en mayúsculas en los ficheros) o de provincia."""
    n = norm_nombre(nombre)
    if es_ccaa:
        tid = terr.get(("CCAA", n)) or terr.get(("Provincia", n))
        if tid and tid.startswith("P"):  # uniprovincial escrita como provincia
            return tid, tid
        return tid, uniprov.get(tid)
    tid = terr.get(("Provincia", n)) or terr.get(("CCAA", n))
    return tid, tid if tid and tid.startswith("P") else None


# ------------------------------------------------------------------------------------------------ ETT
def _bloques_evolucion(filas, cols):
    """Recorre una hoja de evolución (filas de años 'AAAA', bloques 'AAAA:' + meses). Devuelve (periodo, fecha, fila)."""
    anyo_bloque = None
    for f in filas:
        c0 = celda(f, 0)
        m = re.match(r"^(\d{4})\s*(\(\*\))?\s*:$", c0)
        if m:
            anyo_bloque = int(m.group(1)); continue
        m = re.match(r"^(\d{4})\s*(\(\*\))?$", c0)
        if m and num(f[1] if len(f) > 1 else None) is not None:
            yield "Año", f"{m.group(1)}-01-01", f; continue
        mes = MESES.get(c0.lower())
        if anyo_bloque and mes and num(f[1] if len(f) > 1 else None) is not None:
            yield "Mes", f"{anyo_bloque}-{mes:02d}-01", f


def ett_mensual(datos, url=""):
    h = libro(datos)
    filas = []
    e1 = [("ETT", "Empresas de trabajo temporal", 1), ("Cesiones", "Cesiones de trabajadores", 2),
          ("CPD por modalidad", "Total", 3), ("CPD por modalidad", "Obra o servicio", 4),
          ("CPD por modalidad", "Circunstancias de la producción", 5), ("CPD por modalidad", "Fijos discontinuos", 6),
          ("CPD por modalidad", "Sustitución", 7), ("CPD por modalidad", "Formación y aprendizaje", 8),
          ("CPD por modalidad", "Otros contratos", 9)]
    e3 = [("Trabajadores contratados por ETT", "Total", 1), ("Trabajadores contratados por ETT", "Hombres", 2),
          ("Trabajadores contratados por ETT", "Mujeres", 3), ("Trabajadores contratados por ETT", "Española", 4),
          ("Trabajadores contratados por ETT", "Extranjera", 5), ("Trabajadores contratados por ETT", "Menos de 20 años", 6),
          ("Trabajadores contratados por ETT", "De 20 a 29 años", 7), ("Trabajadores contratados por ETT", "De 30 a 39 años", 8),
          ("Trabajadores contratados por ETT", "De 40 y más años", 9)]
    e4 = [("Contratos de trabajo de ETT", "Total", 1), ("Contratos de trabajo de ETT", "Indefinido fijo discontinuo", 2),
          ("Contratos de trabajo de ETT", "Indefinido no fijo discontinuo", 3), ("Contratos de trabajo de ETT", "Obra o servicio", 4),
          ("Contratos de trabajo de ETT", "Circunstancias de la producción", 5), ("Contratos de trabajo de ETT", "Sustitución", 6),
          ("Contratos de trabajo de ETT", "Otros contratos", 7)]
    # comprobación de la cabecera: si el ministerio cambia el orden de columnas, el lector falla en vez de mezclar datos
    esperado = {"ETT-E1": ["CONTRATOS DE PUE", "Obra o servicio", "Circunstancias", "Fijos discontinu", "Sustitución"],
                "ETT-E3": ["SEXO", "Hombres", "Mujeres", "Española", "Extranjera"],
                "ETT-E4": ["Fijos discontinu", "No fijos discont", "Obra", "Circunstancias", "Sustitución"]}
    for hoja, cols in (("ETT-E1", e1), ("ETT-E3", e3), ("ETT-E4", e4)):
        texto_cab = " ".join(celda(f, j) for f in h[hoja][:12] for j in range(12)).lower()
        faltan = [e for e in esperado[hoja] if e.lower()[:12] not in texto_cab]
        if faltan:
            raise ValueError(f"{hoja}: la cabecera ha cambiado (no aparece {faltan})")
        for periodo, fecha, f in _bloques_evolucion(h[hoja], cols):
            for ind, cat, j in cols:
                v = num(f[j] if j < len(f) else None)
                if v is not None:
                    filas.append([fecha, periodo, ind, cat, v, url])
    # control: en E1 la suma de modalidades = total
    tot = {(r[0], r[1]): r[4] for r in filas if r[2] == "CPD por modalidad" and r[3] == "Total"}
    suma = {}
    for r in filas:
        if r[2] == "CPD por modalidad" and r[3] != "Total":
            suma[(r[0], r[1])] = suma.get((r[0], r[1]), 0) + r[4]
    malos = [k for k, v in tot.items() if abs(v - suma.get(k, 0)) > 0.005 * v]
    if malos:
        raise ValueError(f"ETT-E1: la suma de modalidades no cuadra con el total en {malos[:3]}")
    return ["fecha", "periodo", "indicador", "categoria", "valor", "fichero"], filas


def _periodo_hoja(filas):
    """('Julio', 2026) a partir de 'Año 2026' y la fila de 'Julio | Acumulado Ene.-Jul.'."""
    anyo = mes = None
    for f in filas[:10]:
        for j in range(len(f)):
            c = celda(f, j)
            m = re.match(r"^Año (\d{4})", c)
            if m:
                anyo = int(m.group(1))
            if c.lower() in MESES and mes is None:
                mes = MESES[c.lower()]
    if not (anyo and mes):
        raise ValueError("no se encuentra el año o el mes del cuadro")
    return anyo, mes


def ett_territorio(datos, url=""):
    h = libro(datos)["ETT-1"]
    anyo, mes = _periodo_hoja(h)
    terr, uniprov = territorios()
    filas, sin_casar = [], []
    for f in h:
        nombre = celda(f, 0)
        if not nombre or num(f[1] if len(f) > 1 else None) is None:
            continue
        if nombre.upper().startswith("TOTAL"):
            tid, pid, nivel = "N00", None, "Nacional"
        else:
            es_ccaa = nombre.isupper()
            tid, pid = resolver(nombre, es_ccaa, terr, uniprov)
            nivel = "CCAA" if es_ccaa else "Provincia"
            if nombre in ("Ceuta", "Melilla"):
                nivel, pid = "CCAA", tid
                tid = terr.get(("CCAA", norm_nombre(nombre)))
            if tid is None:
                sin_casar.append(nombre)
        for tipo, desp, desde in (("Mes", 0, f"{anyo}-{mes:02d}-01"), ("Acumulado", 1, f"{anyo}-01-01")):
            filas.append([desde, f"{anyo}-{mes:02d}-01", tipo, nivel, tid, pid, nombre,
                          num(f[1 + desp]), num(f[3 + desp]), num(f[5 + desp]), num(f[7 + desp]), num(f[9 + desp]), url])
    if sin_casar:
        raise ValueError(f"ETT-1: territorios sin casar: {sin_casar}")
    return (["periodo_desde", "periodo_hasta", "tipo_periodo", "nivel", "territorio_id", "provincia_id", "territorio_nombre",
             "cesiones", "cpd_total", "cpd_circunstancias", "cpd_fijos_discontinuos", "cpd_sustitucion_formacion", "fichero"],
            filas)


def ett_actividad(datos, url=""):
    h = libro(datos)["ETT-2"]
    anyo, mes = _periodo_hoja(h)
    filas = []
    for f in h:
        cod, nombre = celda(f, 0), celda(f, 1)
        if not nombre or num(f[2] if len(f) > 2 else None) is None:
            continue
        if nombre.upper().startswith("TOTAL"):
            nivel, cod = "Total", "TOTAL"
        elif re.fullmatch(r"\d{2}", cod):
            nivel = "División"
        else:
            nivel, cod = "Sector", nombre
        for tipo, desp, desde in (("Mes", 0, f"{anyo}-{mes:02d}-01"), ("Acumulado", 1, f"{anyo}-01-01")):
            filas.append([desde, f"{anyo}-{mes:02d}-01", tipo, nivel, cod, re.sub(r"\s*\(\d\)\s*$", "", nombre),
                          num(f[2 + desp]), num(f[4 + desp]), num(f[6 + desp]), num(f[8 + desp]), url])
    return (["periodo_desde", "periodo_hasta", "tipo_periodo", "nivel", "codigo", "nombre", "cpd_total",
             "cpd_circunstancias", "cpd_fijos_discontinuos", "cpd_sustitucion_formacion", "fichero"], filas)


def ett_resumen(datos, url=""):
    """ETT-R1 (CPD por sección), ETT-R2 (CPD por CCAA), ETT-R3 (trabajadores con contrato por sexo, nacionalidad y edad)
    y ETT-R4 (afiliados a ETT): acumulado del año con la variación oficial sobre el mismo periodo del año anterior
    (calculada por el ministerio con datos revisados; no se recalcula con avances provisionales antiguos)."""
    h = libro(datos)
    terr, uniprov = territorios()
    filas = []
    for hoja, cuadro in (("ETT-R1", "CPD por sección"), ("ETT-R2", "CPD por CCAA"),
                         ("ETT-R3", "Trabajadores con contrato"), ("ETT-R4", "Afiliados a ETT")):
        hj = h[hoja]
        texto = " ".join(celda(f, j) for f in hj[:8] for j in range(len(f)))
        m = re.search(r"Enero-(\w+) (\d{4})", texto) or re.search(r"final del (?:\w+ )?(\w+) (\d{4})", texto)
        mes = MESES.get(m.group(1).lower()) if m else None
        anyo = int(m.group(2)) if m else None
        t = re.search(r"trimestre de (\d{4})", texto)  # ETT-R4: "Media datos a final del primer y segundo trimestre de 2026"
        if t and not mes:
            anyo = int(t.group(1))
            mes = 12 if "cuarto" in texto else 9 if "tercer" in texto else 6 if "segundo" in texto else 3
        for f in hj:
            c0, c1 = celda(f, 0), celda(f, 1)
            v = num(f[2] if len(f) > 2 else None)
            if v is None or not c0:
                continue
            nombre = c1 if (hoja == "ETT-R1" and c1) else c0
            codigo, tid = (c0 if hoja == "ETT-R1" and re.fullmatch(r"[A-V]", c0) else None), None
            if c0.upper().startswith(("CONTRATOS DE PUESTA", "TOTAL")):
                codigo, tid, nombre = "TOTAL", "N00", "Total"
            elif hoja == "ETT-R2":
                tid, _ = resolver(c0, True, terr, uniprov)
                if tid is None:
                    raise ValueError(f"ETT-R2: territorio sin casar: {c0}")
            filas.append([f"{anyo}-01-01" if anyo else None, f"{anyo}-{mes:02d}-01" if anyo and mes else None, cuadro,
                          codigo, tid, re.sub(r"\s+", " ", nombre).strip(), v, num(f[4] if len(f) > 4 else None),
                          num(f[6] if len(f) > 6 else None), url])
    if not filas:
        raise ValueError("ETT-R1..R4 sin datos")
    return (["periodo_desde", "periodo_hasta", "cuadro", "codigo", "territorio_id", "nombre", "valor", "variacion_abs",
             "variacion_pct", "fichero"], filas)


# ------------------------------------------------------------------------------------------------ Convenios
def _periodo_cct(filas):
    """(año de efectos, mes de registro) a partir de 'REGISTRADOS HASTA AGOSTO DE 2026' / 'EFECTOS ECONÓMICOS EN 2026'."""
    texto = " ".join(celda(f, j) for f in filas[:3] for j in range(len(f))).upper()
    m = re.search(r"HASTA\s+([A-ZÁÉÍÓÚ]+)\s+(?:DE\s+)?(\d{4})", texto)
    e = re.search(r"EFECTOS\s+ECON[ÓO]MICOS\s+EN\s+(\d{4})", texto)
    mes = MESES.get(m.group(1).lower()) if m else None
    anyo = int(e.group(1)) if e else (int(m.group(2)) if m else None)
    return anyo, mes


def cct_detalle(datos, url=""):
    h = libro(datos)
    terr, uniprov = territorios()
    filas = []
    ambitos = ["Total", "Empresa", "Grupo de empresas", "Sector"]

    def ambitos_de(hj, inicio, ancho):
        """Ámbitos de las columnas a partir de la cabecera (fila con 'TOTAL CONVENIOS'): los avances mensuales traen
        empresa / grupo / sector; los de diciembre, empresa / ámbito superior a la empresa."""
        cab = next(f for f in hj[:8] if any("TOTAL CONVENIOS" in celda(f, j).upper() for j in range(len(f))))
        res, j = [], inicio
        while j < len(cab):
            t = celda(cab, j).upper()
            if t.startswith("CONVENIOS DE"):
                res.append((j, "Empresa" if "EMPRESA" in t and "GRUPO" not in t and "SUPERIOR" not in t and "ÁMB" not in t
                            else "Grupo de empresas" if "GRUPO" in t else "Sector" if "SECTOR" in t else "Superior a la empresa"))
            j += 1
        return res

    # CCT-2.5(a) / CCT-2.5: sector y sección. [cod, nombre, conv, empr, trab, var, (conv, trab, var) por ámbito]
    hj = h.get("CCT-2.5(a)") or h["CCT-2.5"]
    anyo, mes = _periodo_cct(hj)
    amb_cols = ambitos_de(hj, 6, 3)
    for f in hj:
        cod, nombre = celda(f, 0), celda(f, 1)
        if not nombre or num(f[2] if len(f) > 2 else None) is None:
            continue
        nivel = "Total" if nombre.upper() == "TOTAL" else ("Sección" if re.fullmatch(r"[A-U]", cod) else "Sector")
        codigo = cod if nivel == "Sección" else nombre
        filas.append([anyo, mes, "Actividad", nivel, codigo, nombre, None, None, "Total",
                      num(f[2]), num(f[3]), num(f[4]), num(f[5]), None, url])
        for j, amb in amb_cols:
            filas.append([anyo, mes, "Actividad", nivel, codigo, nombre, None, None, amb,
                          num(f[j]), None, num(f[j + 1]), num(f[j + 2]), None, url])

    # CCT-2.6: CCAA y provincia. [nombre, conv, empr, trab, var, jornada, (conv, trab, var, jornada) por ámbito]
    hj = h["CCT-2.6"]
    amb_cols = ambitos_de(hj, 6, 4)
    sin_casar, ccaa_actual = [], None
    for f in hj:
        nombre = celda(f, 0)
        if not nombre or num(f[1] if len(f) > 1 else None) is None:
            continue
        compacto = nombre.replace(" ", "").upper()
        if compacto == "TOTAL":
            nivel, tid, pid = "Nacional", "N00", None
        elif compacto.startswith("INTERAUTON"):
            nivel, tid, pid = "Interautonómico", None, None
        elif nombre.lower().startswith("autonómicos"):
            nivel, tid, pid = "Autonómicos de la CCAA", ccaa_actual, None  # convenios autonómicos: CCAA anterior
        else:
            es_ccaa = nombre.isupper()
            tid, pid = resolver(nombre, es_ccaa, terr, uniprov)
            nivel = "CCAA" if es_ccaa else "Provincia"
            if tid is None:
                sin_casar.append(nombre)
        if nivel == "CCAA":
            ccaa_actual = tid
        filas.append([anyo, mes, "Territorio", nivel, tid or nombre, nombre, tid, pid, "Total",
                      num(f[1]), num(f[2]), num(f[3]), num(f[4]), num(f[5]), url])
        for j, amb in amb_cols:
            filas.append([anyo, mes, "Territorio", nivel, tid or nombre, nombre, tid, pid, amb,
                          num(f[j]), None, num(f[j + 1]), num(f[j + 2]), num(f[j + 3]), url])
    if sin_casar:
        raise ValueError(f"CCT-2.6: territorios sin casar: {sin_casar}")

    # CCT-2.3: ámbito funcional y territorial. Columnas: [nombre, conv, empr, trab, var]
    for f in h["CCT-2.3"]:
        nombre = celda(f, 0)
        if not nombre or num(f[1] if len(f) > 1 else None) is None or nombre.upper() == "TOTAL":
            continue
        filas.append([anyo, mes, "Ámbito", "Ámbito", nombre, nombre, None, None, "Total",
                      num(f[1]), num(f[2]), num(f[3]), num(f[4]), None, url])

    # CCT-2.8: tramos de jornada anual (bloques por ámbito con filas Convenios/Empresas/Trabajadores/Jornada/Variación)
    hj = h["CCT-2.8"]
    tramos = [celda(hj[5], j) for j in range(2, 7)] if len(hj) > 5 else []
    if not all(tramos):
        raise ValueError("CCT-2.8: no se encuentran los tramos de jornada en la fila 6")
    amb = None
    valores = {}
    for f in hj[7:]:
        c0 = celda(f, 0)
        if c0 and num(f[1] if len(f) > 1 else None) is None and not c0.startswith("("):
            amb = {"TOTAL": "Total"}.get(c0.upper(), "Empresa" if "EMPRESA" in c0.upper() and "GRUPO" not in c0.upper()
                                                  else ("Grupo de empresas" if "GRUPO" in c0.upper() else "Sector"))
            continue
        if amb and num(f[1] if len(f) > 1 else None) is not None:
            concepto = c0.lower()
            for k, tramo in enumerate(tramos):
                valores.setdefault((amb, tramo), {})[concepto[:6]] = num(f[2 + k])
    for (amb, tramo), v in valores.items():
        filas.append([anyo, mes, "Jornada", "Tramo de jornada", tramo, tramo, None, None, amb,
                      v.get("conven"), v.get("empres"), v.get("trabaj"), v.get("variac"), v.get("jornad"), url])

    # CCT-2.7: cláusula de garantía salarial, por sector (solo bloque del total de convenios)
    # la hoja tiene dos cuadros con la misma estructura: primero convenios y trabajadores, después variación y jornada
    hj = h["CCT-2.7"]
    cuadro, bloque, recuentos, medias = 0, False, {}, {}
    for f in hj:
        c0 = celda(f, 0)
        if c0.upper().startswith("TOTAL CONVENIO"):
            cuadro, bloque = cuadro + 1, True; continue
        if c0.upper().startswith("CONVENIOS DE"):
            bloque = False; continue
        if bloque and c0 and num(f[2] if len(f) > 2 else None) is not None:
            destino = recuentos if cuadro == 1 else medias
            destino[c0] = {"sin": (num(f[3]), num(f[8])), "con": (num(f[4]), num(f[9]))}
    if set(recuentos) != set(medias) or not recuentos:
        raise ValueError(f"CCT-2.7: los dos cuadros no tienen los mismos sectores ({sorted(recuentos)} / {sorted(medias)})")
    for sector in recuentos:
        for clave, etiqueta in (("con", "con cláusula"), ("sin", "sin cláusula")):
            (conv, trab), (var, jor) = recuentos[sector][clave], medias[sector][clave]
            filas.append([anyo, mes, "Cláusula de garantía", "Sector", f"{sector} · {etiqueta}", f"{sector} · {etiqueta}",
                          None, None, "Total", conv, None, trab, var or None, jor or None, url])
    return (["anyo_efectos", "mes_registro", "desglose", "nivel", "codigo", "nombre", "territorio_id", "provincia_id",
             "ambito_funcional", "convenios", "empresas", "trabajadores", "variacion_salarial_pct", "jornada_media_horas",
             "fichero"], filas)


# ------------------------------------------------------------------------------------------------ Accidentes
def _periodo_atr(filas):
    """('2026-01-01', '2026-07-01') a partir de 'Avance enero - julio 2026'."""
    texto = " ".join(celda(f, j) for f in filas[:8] for j in range(len(f))).lower()
    m = re.search(r"enero\s*-\s*([a-záéíóú]+)\s+(\d{4})", texto)
    if not m:
        raise ValueError("no se encuentra el periodo 'Avance enero - <mes> <año>'")
    anyo, mes = int(m.group(2)), MESES[m.group(1)]
    return f"{anyo}-01-01", f"{anyo}-{mes:02d}-01"


def atr_detalle(datos, url=""):
    """Formato largo (cuadro, código, nombre, sexo, territorio, medida, valor). Medidas: jornada_total, jornada_leves,
    jornada_graves, jornada_mortales, itinere_total…; afiliados, indice, indice_mortales (índice = accidentes en
    jornada al mes por cada 100.000 afiliados, media del periodo); anterior y variacion_pct (ATR-R1, oficial)."""
    h = libro(datos)
    terr, uniprov = territorios()
    filas = []
    gravedad = ["total", "leves", "graves", "mortales"]

    def add(desde, hasta, cuadro, codigo, nombre, sexo, tid, pid, medida, valor):
        if valor is not None:
            filas.append([desde, hasta, cuadro, codigo, re.sub(r"\s+", " ", str(nombre)).strip(), sexo, tid, pid, medida, valor, url])

    # A1.1 territorio, A2.1 actividad, A4 ocupación: [código?, nombre, jornada x4, _, itínere x4]
    for hoja, cuadro in (("ATR-A1.1", "Territorio"), ("ATR-A2.1", "Actividad"), ("ATR-A4", "Ocupación")):
        hj = h[hoja]
        desde, hasta = _periodo_atr(hj)
        nivel = None
        for f in hj[8:]:
            c0, c1 = celda(f, 0), celda(f, 1)
            if hoja == "ATR-A1.1":
                nombre, j0 = c0, 2
            else:
                nombre, j0 = c1, 2
            if c1.upper() in ("SECTOR", "SECCIÓN Y DIVISIÓN"):
                nivel = "Sector" if c1.upper() == "SECTOR" else None
                continue
            if not nombre or num(f[j0] if len(f) > j0 else None) is None:
                continue
            tid = pid = None
            codigo = c0 if hoja != "ATR-A1.1" else None
            if nombre.upper() == "TOTAL":
                codigo, tid, nivel_fila = "TOTAL", "N00", "Total"
            elif hoja == "ATR-A1.1":
                es_ccaa = nombre.isupper()
                tid, pid = resolver(nombre, es_ccaa, terr, uniprov)
                if nombre.strip() in ("Ceuta", "Melilla"):
                    pid, tid = tid, terr.get(("CCAA", norm_nombre(nombre)))
                if tid is None:
                    raise ValueError(f"{hoja}: territorio sin casar: {nombre}")
                nivel_fila = "CCAA" if es_ccaa else "Provincia"
            elif hoja == "ATR-A2.1":
                nivel_fila = "Sector" if not codigo else ("Sección" if re.fullmatch(r"[A-U]", codigo) else "División")
                codigo = codigo or nombre
            else:
                nivel_fila = "Gran grupo de ocupación"
            for k, g in enumerate(gravedad):
                add(desde, hasta, cuadro, codigo, nombre, None, tid, pid, f"jornada_{g}", num(f[j0 + k]))
                add(desde, hasta, cuadro, codigo, nombre, None, tid, pid, f"itinere_{g}", num(f[j0 + 5 + k]))
            add(desde, hasta, cuadro, codigo, nombre, None, tid, pid, "nivel:" + nivel_fila, 1.0)

    # A3 sexo y edad: [nombre, jornada x4, _, itínere x4]; bloques TOTAL / VARONES / MUJERES
    hj = h["ATR-A3"]
    desde, hasta = _periodo_atr(hj)
    sexo = "Total"
    for f in hj[8:]:
        c0 = celda(f, 0)
        if not c0 or num(f[1] if len(f) > 1 else None) is None:
            continue
        if c0.upper() in ("TOTAL", "VARONES", "MUJERES"):
            sexo = {"TOTAL": "Total", "VARONES": "Hombres", "MUJERES": "Mujeres"}[c0.upper()]
            edad = "Total"
        else:
            edad = c0
        for k, g in enumerate(gravedad):
            add(desde, hasta, "Sexo y edad", edad, edad, sexo, None, None, f"jornada_{g}", num(f[1 + k]))
            add(desde, hasta, "Sexo y edad", edad, edad, sexo, None, None, f"itinere_{g}", num(f[6 + k]))

    # I2.1 índices por sector y sección: [código, nombre, _, acc, mortales, _, afiliados, _, índice, índice mortales]
    hj = h["ATR-I2.1"]
    desde, hasta = _periodo_atr(hj)
    for f in hj[8:]:
        c0, c1 = celda(f, 0), celda(f, 1)
        if not c1 or num(f[3] if len(f) > 3 else None) is None:
            continue
        codigo = "TOTAL" if c1.upper() == "TOTAL" else (c0 or c1)
        for medida, j in (("jornada_total", 3), ("jornada_mortales", 4), ("afiliados", 6), ("indice", 8), ("indice_mortales", 9)):
            add(desde, hasta, "Índice por actividad", codigo, c1, None, "N00", None, medida, num(f[j]))

    # I3 índices por CCAA y sector: [CCAA, acc total, agrario, industria, construcción, servicios, _, índice x5]
    hj = h["ATR-I3"]
    desde, hasta = _periodo_atr(hj)
    sectores = ["Total", "Agrario", "Industria", "Construcción", "Servicios"]
    for f in hj[9:]:
        c0 = celda(f, 0)
        if not c0 or num(f[1] if len(f) > 1 else None) is None:
            continue
        tid = "N00" if c0.upper() == "TOTAL" else resolver(c0, True, terr, uniprov)[0]
        if tid is None:
            raise ValueError(f"ATR-I3: territorio sin casar: {c0}")
        for k, sec in enumerate(sectores):
            add(desde, hasta, "Índice por CCAA y sector", sec, sec, None, tid, None, "jornada_total", num(f[1 + k]))
            add(desde, hasta, "Índice por CCAA y sector", sec, sec, None, tid, None, "indice", num(f[7 + k]))

    # R1: comparación oficial con el mismo periodo del año anterior
    hj = h["ATR-R1"]
    desde, hasta = _periodo_atr(hj)
    grupo = None
    for f in hj[6:]:
        c1, c2 = celda(f, 1), celda(f, 2)
        if c1 and not c2 and num(f[3] if len(f) > 3 else None) is None:
            grupo = c1; continue
        nombre = c2 or c1 or celda(f, 0)
        if not nombre or num(f[4] if len(f) > 4 else None) is None:
            continue
        add(desde, hasta, "Variación interanual", grupo or "Total", nombre, None, "N00", None, "anterior", num(f[3]))
        add(desde, hasta, "Variación interanual", grupo or "Total", nombre, None, "N00", None, "actual", num(f[4]))
        add(desde, hasta, "Variación interanual", grupo or "Total", nombre, None, "N00", None, "variacion_pct", num(f[6]))
    return (["periodo_desde", "periodo_hasta", "cuadro", "codigo", "nombre", "sexo", "territorio_id", "provincia_id",
             "medida", "valor", "fichero"], filas)


# ------------------------------------------------------------------------------------------------ Regulación de empleo (ERE/ERTE)
def reg_detalle(datos, url=""):
    """Un mes de regulación de empleo (reg_MM_AAAA.xlsx; cada fichero es el dato del mes, no acumulado):
    trabajadores afectados por despido colectivo, suspensión de contrato (ERTE) o reducción de jornada, por sexo,
    sector/división (REG-1), CCAA y provincia (REG-4), causa (REG-3) y tamaño de empresa (REG-2)."""
    h = libro(datos)
    terr, uniprov = territorios()
    texto = " ".join(celda(f, 0) for f in h["REG-1"][:6])
    m = re.search(r"\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre) (\d{4})",
                  texto.lower())
    if not m:
        raise ValueError("REG-1: no se encuentra el mes")
    fecha = f"{m.group(2)}-{MESES[m.group(1)]:02d}-01"
    tipos = ["Total", "Despidos colectivos", "Suspensión de contrato", "Reducción de jornada"]
    filas = []

    def add(cuadro, codigo, nombre, tid, pid, tipo, sexo, v):
        if v is not None:
            filas.append([fecha, cuadro, codigo, re.sub(r"\s+", " ", nombre).strip(), tid, pid, tipo, sexo, v, url])

    # REG-1: [código, nombre, (total, hombres, mujeres) x 4 tipos]
    for f in h["REG-1"][8:]:
        cod, nombre = celda(f, 0), celda(f, 1)
        if not nombre or num(f[2] if len(f) > 2 else None) is None:
            continue
        codigo = "TOTAL" if nombre.upper() == "TOTAL" else (cod or nombre)
        for k, tipo in enumerate(tipos):
            for d, sexo in enumerate(("Total", "Hombres", "Mujeres")):
                add("Actividad", codigo, nombre, None, None, tipo, sexo, num(f[2 + 3 * k + d]))
    # REG-4: [territorio, (total, hombres, mujeres) x 4 tipos]
    for f in h["REG-4"][8:]:
        nombre = celda(f, 0)
        if not nombre or num(f[1] if len(f) > 1 else None) is None:
            continue
        if nombre.replace(" ", "").upper() == "TOTAL":
            tid, pid = "N00", None
        else:
            tid, pid = resolver(nombre, nombre.isupper(), terr, uniprov)
            if nombre.strip() in ("Ceuta", "Melilla"):
                pid, tid = tid, terr.get(("CCAA", norm_nombre(nombre)))
            if tid is None:
                raise ValueError(f"REG-4: territorio sin casar: {nombre}")
        for k, tipo in enumerate(tipos):
            for d, sexo in enumerate(("Total", "Hombres", "Mujeres")):
                add("Territorio", tid, nombre, tid, pid, tipo, sexo, num(f[1 + 3 * k + d]))
    # REG-3 causa y REG-2 tamaño (solo trabajadores): [nombre, total, despidos, suspensión, reducción]
    for hoja, cuadro in (("REG-3", "Causa"), ("REG-2", "Tamaño de empresa")):
        en_trab = hoja == "REG-3"
        for f in h[hoja][6:]:
            nombre = celda(f, 0)
            if hoja == "REG-2" and nombre.upper().startswith("TRABAJADORES"):
                en_trab = True; continue
            if not en_trab or not nombre or num(f[1] if len(f) > 1 else None) is None:
                continue
            for k, tipo in enumerate(tipos):
                add(cuadro, nombre, nombre, None, None, tipo, "Total", num(f[1 + k]))
    return (["fecha", "cuadro", "codigo", "nombre", "territorio_id", "provincia_id", "tipo", "sexo", "trabajadores", "fichero"],
            filas)


# ------------------------------------------------------------------------------------------------ Incapacidad temporal (Seguridad Social)
def it_provincias(datos, url=""):
    """Publicación de IT del sistema de la Seguridad Social (Publicacion_IT_SISTEMA_<año>_<mes>.xlsx o
    'IT cierre Sistema <año>'). Hoja 'Estadística' (tabla dinámica con todos los regímenes y ambas contingencias,
    comprobado: sus procesos en vigor coinciden con la suma de la hoja de datos mensuales): por CCAA y provincia,
    duración media de los procesos finalizados, incidencia media mensual y prevalencia por mil trabajadores
    protegidos, procesos iniciados, finalizados y en vigor, y trabajadores protegidos. Periodo: de enero al último
    mes de 'Datos mensuales' (o el año completo si el mes es 'Cierre')."""
    import openpyxl, warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        wb = openpyxl.load_workbook(io.BytesIO(datos), read_only=True, data_only=True)
    est = [list(r) for r in wb["Estadística"].iter_rows(values_only=True)]
    meses = {}
    for r in wb["Datos mensuales"].iter_rows(values_only=True, min_row=2, max_col=2):
        if r[0]:
            meses.setdefault(int(r[0]), set()).add(str(r[1]))
    anyo = max(meses)
    ms = meses[anyo]
    mes = 12 if "Cierre" in ms else max(MESES[m.lower()] for m in ms if m.lower() in MESES)
    cab = next((i, r) for i, r in enumerate(est) if r and "Provincia" in [celda(r, j) for j in range(len(r))])
    i0, fila_cab = cab
    j0 = [celda(fila_cab, j) for j in range(len(fila_cab))].index("Provincia")
    esperado = ["Duración media", "Incidencia media mensual", "procesos iniciados", "procesos finalizados", "Prevalencia",
                "procesos en vigor", "Trabajadores protegidos", "Media de trabajadores"]
    nombres = [celda(fila_cab, j0 + 1 + k) for k in range(8)]
    for e, n in zip(esperado, nombres):
        if e.lower() not in n.lower():
            raise ValueError(f"IT: la columna '{n}' no es '{e}' (ha cambiado la hoja Estadística)")
    terr, uniprov = territorios()
    alias = {"santa cruz de te": "santa cruz de tenerife"}
    filas, ccaa, ccaa_id = [], None, None
    for r in est[i0 + 1:]:
        c_ccaa, c_prov = celda(r, j0 - 1), celda(r, j0)
        if c_ccaa.startswith("Total general"):
            c_prov, nivel, tid, pid = "Total general", "Nacional", "N00", None
            vals = [num(r[j0 + 1 + k]) for k in range(8)]  # la etiqueta va en la columna de CCAA; los valores, igual
        else:
            if c_ccaa:
                ccaa = c_ccaa
                ccaa_id, _ = resolver(ccaa, True, terr, uniprov)
                if ccaa_id is None:
                    raise ValueError(f"IT: CCAA sin casar: {ccaa}")
            if not c_prov or num(r[j0 + 1] if len(r) > j0 + 1 else None) is None:
                continue
            vals = [num(r[j0 + 1 + k]) for k in range(8)]
            if c_prov == "Total":
                nivel, tid, pid = "CCAA", ccaa_id, uniprov.get(ccaa_id)
            else:
                nivel = "Provincia"
                n = alias.get(c_prov.lower(), c_prov)
                tid, pid = resolver(n, False, terr, uniprov)
                if tid is None or not str(tid).startswith("P"):
                    tid = pid = uniprov.get(ccaa_id) if tid is None or not str(tid).startswith("P") else tid
                if tid is None:
                    raise ValueError(f"IT: provincia sin casar: {c_prov}")
        filas.append([anyo, mes, "Año completo" if mes == 12 and "Cierre" in ms else f"Enero-{list(MESES)[mes - 1].capitalize()}",
                      nivel, tid, pid, c_prov if nivel != "CCAA" else ccaa] + vals + [url])
        if nivel == "Nacional":
            break
    if not any(f[3] == "Nacional" for f in filas):
        raise ValueError("IT: no aparece la fila 'Total general'")
    return (["anyo", "mes_hasta", "periodo", "nivel", "territorio_id", "provincia_id", "nombre", "duracion_media_dias",
             "incidencia_media_mensual_mil", "procesos_iniciados", "procesos_finalizados", "prevalencia_mil",
             "procesos_en_vigor_final", "trabajadores_protegidos_final", "trabajadores_protegidos_media", "fichero"], filas)


def it_detalle(datos, url=""):
    """Hoja 'Datos mensuales' de la publicación de IT del sistema: por mes, régimen, contingencia, sexo y provincia, los
    indicadores i19 (procesos finalizados con alta), i20 (días de duración de esos procesos), i21 (en vigor el último
    día), i22 (afiliados el último día), i25 (procesos iniciados) e i26 (afiliados medios). Se suman los organismos
    (INSS, ISM, mutuas), igual que la hoja 'Estadística'. Duración media = i20 / i19. Mes 0 = 'Cierre' (año completo).
    No hay desglose por edad, actividad ni ocupación en esta publicación."""
    import openpyxl, warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        wb = openpyxl.load_workbook(io.BytesIO(datos), read_only=True, data_only=True)
    filas_h = wb["Datos mensuales"].iter_rows(values_only=True)
    cab = [celda(list(r), j) for r in [next(filas_h)] for j in range(len(r))]
    col = {n: cab.index(n) for n in ("Ejercicio", "Mes", "Régimen", "Contingencia", "Sexo", "Provincia", "Indicador")}
    j_val = next(j for j, n in enumerate(cab) if "cantidad" in n.lower())
    terr, uniprov = territorios()
    alias = {"santa cruz de te": "santa cruz de tenerife"}
    cache, agg = {}, {}
    for r in filas_h:
        r = list(r)
        if not r or r[col["Ejercicio"]] in (None, ""):
            continue
        mes_txt = celda(r, col["Mes"]).lower()
        mes = 0 if mes_txt.startswith("cierre") else MESES.get(mes_txt)
        if mes is None:
            continue
        prov = celda(r, col["Provincia"])
        if prov not in cache:
            tid, _ = resolver(alias.get(prov.lower(), prov), False, terr, uniprov)
            if tid is not None and not str(tid).startswith("P"):
                tid = uniprov.get(tid)
            cache[prov] = tid
        pid = cache[prov]
        if pid is None:  # 'Sin determinar' u otros sin provincia: cuentan en el total nacional
            pid = "SD"
        clave = (int(r[col["Ejercicio"]]), mes, celda(r, col["Régimen"]), celda(r, col["Contingencia"]), celda(r, col["Sexo"]),
                 pid, int(num(r[col["Indicador"]]) or 0))
        agg[clave] = agg.get(clave, 0) + (num(r[j_val]) or 0)
    if not agg:
        raise ValueError("IT detalle: la hoja 'Datos mensuales' está vacía o ha cambiado")
    sin = [p for p, t in cache.items() if t is None and p and "determinar" not in p.lower()]
    if len(sin) > 3:
        raise ValueError(f"IT detalle: provincias sin casar: {sin[:5]}")
    filas = [list(k) + [v, url] for k, v in sorted(agg.items())]
    return (["anyo", "mes", "regimen", "contingencia", "sexo", "provincia_id", "indicador", "cantidad", "fichero"], filas)


# ------------------------------------------------------------------------------------------------ prueba local
if __name__ == "__main__":
    tipo, ruta = sys.argv[1], Path(sys.argv[2])
    datos = ruta.read_bytes()
    funciones = {"ett": [ett_mensual, ett_territorio, ett_actividad, ett_resumen], "cct": [cct_detalle], "atr": [atr_detalle], "reg": [reg_detalle], "it": [it_provincias, it_detalle]}[tipo]
    for fn in funciones:
        cab, filas = fn(datos, ruta.name)
        print(f"== {fn.__name__}: {len(filas)} filas · {cab}")
        for r in filas[:4] + filas[-3:]:
            print("  ", r[:-1])
