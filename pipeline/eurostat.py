"""
pipeline/eurostat.py — Eurostat: indicadores de la población joven de España (API de difusión 1.0, JSON-stat).

Eurostat toma los datos de la Encuesta de Población Activa del INE y de las estadísticas demográficas del INE. Se usa porque
publica por API lo que el dashboard necesita y el INE no entrega en un formato descargable sin intermediarios.

Tabla (formato largo): serie; anyo; sexo; categoria; valor; unidad; estado; zona  (zona: España o UE-27)
  poblacion_16_29     personas de 16 a 29 años a 1 de enero (suma de las edades simples 16…29, demo_pjan)
  tasa_empleo_15_29   tasa de empleo de 15 a 29 años, % (lfsa_ergan). Eurostat no publica el grupo 16-29
  neet_nivel          % de NEET (15-29) dentro de cada nivel de formación (edat_lfse_21)
  poblacion_nivel     personas de 15 a 29 años por nivel de formación (lfsa_pganedm, miles × 1000)
  neet_urbanizacion   % de NEET (15-29) según el grado de urbanización: ciudades, pueblos y periferias, zonas rurales (edat_lfse_29)
  empleo_ue           tasa de empleo 15-29, España y UE-27 (lfsa_ergan)
  paro_ue             tasa de paro, España y UE-27, por grupo de edad: 15-24, 15-29 y 15-74 (une_rt_a)
  temporalidad_ue     asalariados con contrato temporal, % del total de asalariados, España y UE-27: 15-29 y 15-64 (lfsa_etpgan)
  parcialidad_ue      ocupados a tiempo parcial, % del total de ocupados, España y UE-27: 15-29 y 15-64 (lfsa_eppga)
estado: marca de calidad de Eurostat (b = ruptura de serie, d = definición distinta, u = poco fiable…); vacío si no hay.
"""
import itertools, json, urllib.parse

BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"
DESDE = 2015
EDADES_16_29 = [f"Y{i}" for i in range(16, 30)]
SEXOS = {"T": "Total", "M": "Hombres", "F": "Mujeres"}
NIVELES = {"ED0-2": "Primaria y primera etapa de secundaria", "ED3_4": "Segunda etapa de secundaria y postsecundaria",
           "ED5-8": "Educación superior"}
URBANIZACION = {"DEG1": "Ciudades", "DEG2": "Pueblos y periferias", "DEG3": "Zonas rurales"}
ZONAS = {"ES": "España", "EU27_2020": "UE-27"}
EDADES_UE = {"Y15-24": "15-24", "Y15-29": "15-29", "Y15-74": "15-74"}
EDADES_CONTRATO = {"Y15-29": "15-29", "Y15-64": "15-64"}

# serie -> (dataset, filtros, dimensión que da la categoría, {código: etiqueta}, unidad, multiplicador)
SERIES = {
    "poblacion_16_29": ("demo_pjan", {"geo": "ES", "sex": list(SEXOS), "age": EDADES_16_29, "unit": "NR"}, None, None, "personas", 1),
    "tasa_empleo_15_29": ("lfsa_ergan", {"geo": "ES", "sex": list(SEXOS), "age": "Y15-29", "citizen": "TOTAL", "unit": "PC"},
                          None, None, "%", 1),
    "neet_nivel": ("edat_lfse_21", {"geo": "ES", "sex": "T", "age": "Y15-29", "isced11": list(NIVELES), "unit": "PC"},
                   "isced11", NIVELES, "%", 1),
    "poblacion_nivel": ("lfsa_pganedm", {"geo": "ES", "sex": "T", "age": "Y15-29", "citizen": "TOTAL", "mgstatus": "TOTAL",
                                         "isced11": list(NIVELES), "unit": "THS_PER"}, "isced11", NIVELES, "personas", 1000),
    "neet_urbanizacion": ("edat_lfse_29", {"geo": "ES", "sex": "T", "age": "Y15-29", "deg_urb": list(URBANIZACION), "unit": "PC"},
                          "deg_urb", URBANIZACION, "%", 1),
    "empleo_ue": ("lfsa_ergan", {"geo": list(ZONAS), "sex": "T", "age": "Y15-29", "citizen": "TOTAL", "unit": "PC"}, "age", {"Y15-29": "15-29"}, "%", 1),
    "paro_ue": ("une_rt_a", {"geo": list(ZONAS), "sex": "T", "age": list(EDADES_UE), "unit": "PC_ACT"}, "age", EDADES_UE, "%", 1),
    "temporalidad_ue": ("lfsa_etpgan", {"geo": list(ZONAS), "sex": "T", "age": list(EDADES_CONTRATO), "citizen": "TOTAL", "unit": "PC"},
                        "age", EDADES_CONTRATO, "%", 1),
    "parcialidad_ue": ("lfsa_eppga", {"geo": list(ZONAS), "sex": "T", "age": list(EDADES_CONTRATO), "unit": "PC"},
                       "age", EDADES_CONTRATO, "%", 1),
}
CABECERA = ["serie", "anyo", "sexo", "categoria", "valor", "unidad", "estado", "zona"]


def url(dataset, filtros):
    q = {"lang": "EN", "format": "JSON", "sinceTimePeriod": str(DESDE), **filtros}
    return f"{BASE}/{dataset}?" + urllib.parse.urlencode(q, doseq=True)


def leer(j):
    """JSON-stat -> lista de {dimensión: código, 'valor': número, 'estado': marca}. Se omiten las celdas vacías."""
    ids, tamanos = j["id"], j["size"]
    cats = []
    for d in ids:
        indice = j["dimension"][d]["category"]["index"]
        cats.append(sorted(indice, key=indice.get) if isinstance(indice, dict) else list(indice))
    valores, estados = j.get("value") or {}, j.get("status") or {}
    if isinstance(valores, list):
        valores = {str(i): v for i, v in enumerate(valores)}
    if isinstance(estados, list):
        estados = {str(i): v for i, v in enumerate(estados)}
    filas = []
    for i, combo in enumerate(itertools.product(*[range(n) for n in tamanos])):
        v = valores.get(str(i))
        if v is None:
            continue
        fila = {d: cats[k][c] for k, (d, c) in enumerate(zip(ids, combo))}
        fila.update(valor=float(v), estado=estados.get(str(i), "") or "")
        filas.append(fila)
    return filas


def _serie(nombre, descargar):
    dataset, filtros, dim_cat, etiquetas, unidad, mult = SERIES[nombre]
    celdas = leer(json.loads(descargar(url(dataset, filtros))))
    if not celdas:
        raise ValueError(f"{dataset}: sin datos")
    if nombre == "poblacion_16_29":  # suma de las 14 edades simples; un año con alguna edad sin dato se descarta
        suma, cuenta, marcas = {}, {}, {}
        for c in celdas:
            k = (c["time"], c["sex"])
            suma[k] = suma.get(k, 0) + c["valor"]
            cuenta[k] = cuenta.get(k, 0) + 1
            marcas.setdefault(k, set()).add(c["estado"])
        return [[nombre, int(a), SEXOS[s], "Total", round(suma[(a, s)]), unidad, "".join(sorted(marcas[(a, s)] - {""})), "España"]
                for (a, s) in sorted(suma) if cuenta[(a, s)] == len(EDADES_16_29)]
    filas = []
    for c in celdas:
        sexo = SEXOS.get(c.get("sex"), "Total")
        categoria = etiquetas[c[dim_cat]] if dim_cat else "Total"
        filas.append([nombre, int(c["time"]), sexo, categoria, round(c["valor"] * mult, 3), unidad, c["estado"], ZONAS.get(c.get("geo"), "España")])
    return sorted(filas, key=lambda f: (f[1], f[7], f[2], f[3]))


def cargar(descargar):
    """(cabecera, filas, series sin datos). `descargar(url) -> bytes`. Una serie que falla se anota pero no tumba las demás."""
    filas, fallos = [], {}
    for nombre in SERIES:
        try:
            filas += _serie(nombre, descargar)
        except Exception as e:
            fallos[nombre] = f"{type(e).__name__}: {e}"[:150]
    if not filas:
        raise ValueError(f"Eurostat: ninguna serie descargada ({fallos})")
    return CABECERA, filas, fallos
