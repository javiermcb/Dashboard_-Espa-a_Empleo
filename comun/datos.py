"""
datos.py — Acceso a los datos del modelo RRHH 360 (Parquet) para la app.

Origen de los datos (por orden):
  1. variable de entorno o secreto de Streamlit RRHH_DATOS: carpeta local o URL base que contenga
     <tabla>.parquet y marts/<tabla>.parquet (p. ej. https://raw.githubusercontent.com/<usuario>/<repo>/datos-modelo/modelo/).
     Si el repositorio es privado, RRHH_DATOS_TOKEN = token de GitHub con permiso de lectura de contenidos.
  2. ../datos/modelo (modelo generado en local por el pipeline)
Con una URL, cada fichero se descarga una vez a una carpeta temporal y se vuelve a descargar cada 6 horas.
Todas las consultas son SQL de DuckDB sobre vistas con el nombre de cada tabla.
"""
import os, re, tempfile, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parent
CACHE = Path(tempfile.gettempdir()) / "rrhh360_datos"
TTL = 6 * 3600
_ERRORES = {}  # {tabla: motivo} de la última carga (compartido por todas las sesiones, como la conexión)

TABLAS = [  # (nombre, ruta relativa)
    "dim_territorio", "dim_tiempo", "fact_sepe_paro_municipio", "fact_sepe_contratos_municipio", "fact_ss_afiliacion",
    "fact_cpd_actividad", "fact_convenios", "fact_convenios_detalle", "fact_accidentes", "fact_accidentes_detalle",
    "fact_ett_mensual", "fact_ett_territorio", "fact_ett_actividad", "fact_ett_resumen", "fact_regulacion_empleo",
    "fact_incapacidad_temporal", "fact_ine", "fact_sepe_demandantes_municipio", "fact_it_detalle",
] + [f"marts/{m}" for m in (
    "mart_salarios_ees", "mart_salarios_eaes", "mart_coste_laboral", "mart_coste_actividad", "mart_tiempo_trabajo",
    "mart_tiempo_trabajo_actividad", "mart_it_despido", "mart_vacantes", "mart_vacantes_actividad", "mart_poblacion_actividad",
    "mart_ocupados_sector", "mart_tasas_epa", "mart_flujos", "mart_precios", "mart_brecha_genero", "mart_empresas",
    "mart_epa_ett", "mart_temporalidad_motivo", "mart_horas_extra", "mart_ocupados_ccaa", "mart_teletrabajo",
    "mart_salarios_ees_detalle", "mart_neet")]
# tablas que la app usa si están, pero cuya falta no impide publicar la carga (control_publicacion.py solo exige TABLAS):
# FUNDAE depende de un visor web que falla a menudo y sus series se van completando en cargas sucesivas
OPCIONALES = ["fact_fundae", "fact_eurostat", "marts/mart_oportunidad_ccaa", "fact_sepe_demandantes_nivel"]
# las cachés (conexión y consultas) llevan en la clave esta firma y la versión de la carga publicada (clave()): al añadir
# una tabla o publicarse una carga nueva, la app la lee en vez de seguir con la conexión antigua hasta que caduque la caché
_ACTIVAS = None  # nombres de las tablas que carga este dashboard (None: todas); lo fija usar()


def usar(tablas):
    """Limita la carga a estas tablas (nombres sin ruta, p. ej. «mart_neet»): cada dashboard descarga y abre solo las suyas."""
    global _ACTIVAS
    _ACTIVAS = None if tablas is None else frozenset(tablas)


def _rutas():
    """Tablas (con ruta relativa) que lee este dashboard."""
    return [r for r in TABLAS + OPCIONALES if _ACTIVAS is None or r.split("/")[-1] in _ACTIVAS]


def _ajuste(nombre):
    """Variable de entorno o secreto de Streamlit."""
    valor = os.environ.get(nombre)
    if not valor:
        try:
            valor = st.secrets.get(nombre)
        except Exception:
            valor = None
    return valor


def origen():
    return _ajuste("RRHH_DATOS") or str(RAIZ.parent / "datos" / "modelo")


def _abrir(url, timeout):
    """Descarga una URL. Con RRHH_DATOS_TOKEN (repositorio privado), una URL raw.githubusercontent.com/<dueño>/<repo>/<rama>/<ruta>
    se pide a la API de contenidos de GitHub con el token (lectura de contenidos)."""
    cab = {"User-Agent": "rrhh360-app"}
    token = _ajuste("RRHH_DATOS_TOKEN")
    if token and url.startswith("https://raw.githubusercontent.com/"):
        dueno, repo, rama, ruta = url.removeprefix("https://raw.githubusercontent.com/").split("/", 3)
        url = f"https://api.github.com/repos/{dueno}/{repo}/contents/{ruta}?ref={rama}"
        cab |= {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.raw+json"}
    return urllib.request.urlopen(urllib.request.Request(url, headers=cab), timeout=timeout)


def _motivo(e):
    """Texto corto para el aviso de la app según el error de descarga."""
    import urllib.error
    if isinstance(e, urllib.error.HTTPError):
        if e.code in (401, 403):
            return f"acceso denegado (HTTP {e.code}): el token RRHH_DATOS_TOKEN no es válido o ha caducado"
        if e.code == 404:
            return "no encontrado (HTTP 404): revisa la URL RRHH_DATOS o que el token tenga acceso al repositorio"
        return f"HTTP {e.code}"
    return f"{type(e).__name__}: {e}"[:160]


def _ruta_local(base, rel, version=""):
    """(ruta local del fichero <rel>.parquet o None, error o None), descargándolo si el origen es una URL.
    Cada carga publicada (version) se descarga en su propia carpeta: una carga nueva no reutiliza ficheros de la anterior."""
    if not base.startswith("http"):
        p = Path(base) / f"{rel}.parquet"
        return (p, None) if p.exists() else (None, f"no existe {p}")
    destino = CACHE / (re.sub(r"[^0-9A-Za-z]", "", version or "") or "sin_version") / f"{rel}.parquet"
    if destino.exists() and time.time() - destino.stat().st_mtime < TTL:
        return destino, None
    destino.parent.mkdir(parents=True, exist_ok=True)
    try:
        url = base.rstrip("/") + f"/{rel}.parquet"
        with _abrir(url, 120) as r:
            tmp = destino.with_suffix(".tmp")
            tmp.write_bytes(r.read())
            tmp.replace(destino)
        return destino, None
    except Exception as e:
        # si falla, la última copia descargada (si la hay)
        return (destino if destino.exists() else None), _motivo(e)


def _extra(base, nombre):
    """alertas.csv, metadatos.json… junto a los Parquet."""
    if not base.startswith("http"):
        p = Path(base) / nombre
        return p.read_bytes() if p.exists() else None
    try:
        with _abrir(base.rstrip("/") + "/" + nombre, 60) as r:
            return r.read()
    except Exception:
        return None


@st.cache_data(ttl=600, show_spinner=False)
def version():
    """Fecha de generación de la carga publicada (metadatos.json), comprobada cada 10 minutos: cuando el pipeline
    publica una carga nueva, cambia la clave de todas las cachés y la app la lee sin esperar a que caduquen (6 horas)."""
    import json
    try:
        m = _extra(origen(), "metadatos.json")
        return str(json.loads(m).get("generado", "")) if m else ""
    except Exception:
        return ""


def clave():
    """Clave de las cachés: tablas que lee este dashboard + carga publicada."""
    return "|".join(_rutas()) + "|" + version()


def conexion():
    return _conexion(clave())


def _limpiar_cache(ver):
    """Borra las descargas de cargas anteriores con más de un día (cada carga publicada ocupa su propia carpeta)."""
    import shutil
    actual = re.sub(r"[^0-9A-Za-z]", "", ver or "") or "sin_version"
    if not CACHE.exists():
        return
    for d in CACHE.iterdir():
        if d.is_dir() and d.name != actual and time.time() - d.stat().st_mtime > 86400:
            shutil.rmtree(d, ignore_errors=True)


@st.cache_resource(ttl=TTL, show_spinner="Cargando los datos…")
def _conexion(firma):  # sin «_» delante: Streamlit no usa en la clave los argumentos que empiezan por «_»
    base = origen()
    *rels, ver = firma.split("|")  # la clave lleva las tablas que lee este dashboard y, al final, la carga publicada
    _limpiar_cache(ver)
    con = duckdb.connect()
    disponibles, faltan = [], []
    # descargas en paralelo
    with ThreadPoolExecutor(max_workers=8) as ex:
        rutas = dict(zip(rels, ex.map(lambda rel: _ruta_local(base, rel, ver), rels)))
    errores = {rel.split("/")[-1]: err for rel, (_, err) in rutas.items() if err and rel not in OPCIONALES}
    for rel in rels:
        p = rutas[rel][0]
        nombre = rel.split("/")[-1]
        if p is None:
            if rel not in OPCIONALES:
                faltan.append(nombre)
            continue
        con.execute(f"CREATE VIEW {nombre} AS SELECT * FROM read_parquet('{p.as_posix()}')")
        disponibles.append(nombre)
    alertas = _extra(base, "alertas.csv")
    if alertas:
        p = CACHE / "alertas.csv"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(alertas)
        con.execute(f"CREATE VIEW alertas AS SELECT * FROM read_csv('{p.as_posix()}', delim=';', header=true, all_varchar=true)")
        disponibles.append("alertas")
    _ERRORES.clear(); _ERRORES.update(errores)
    return con, disponibles, faltan


def errores_descarga():
    """{tabla: motivo} de las descargas que han fallado en la última carga de datos (con o sin copia anterior)."""
    conexion()
    return dict(_ERRORES)


def hay(*tablas):
    _, disp, _ = conexion()
    return all(t in disp for t in tablas)


def q(sql, params=None):
    """Consulta SQL -> DataFrame. Si una tabla no está disponible devuelve un DataFrame vacío."""
    return _q(sql, params, clave())


@st.cache_data(ttl=TTL, show_spinner=False)
def _q(sql, params, firma):
    con, _, _ = conexion()
    try:
        return con.execute(sql, params or []).df()
    except duckdb.CatalogException:
        return pd.DataFrame()


def territorios():
    return q("SELECT territorio_id, nivel, nombre, ccaa_id, ccaa_nombre FROM dim_territorio WHERE nivel IN ('Nacional','CCAA','Provincia')")


def metadatos():
    """metadatos.json del modelo: fecha de generación y filas por tabla."""
    return _metadatos(clave())


@st.cache_data(ttl=TTL, show_spinner=False)
def _metadatos(firma):
    import json
    m = _extra(origen(), "metadatos.json")
    try:
        return json.loads(m) if m else {}
    except Exception:
        return {}


def fecha_carga():
    return metadatos().get("generado")


def csv_extra(nombre):
    """CSV de calidad publicado junto al modelo (fuentes_carga.csv, resumen_fuentes.csv…), separador ';'."""
    return _csv_extra(nombre, clave())


@st.cache_data(ttl=TTL, show_spinner=False)
def _csv_extra(nombre, firma):
    import io
    b = _extra(origen(), nombre)
    if not b:
        return pd.DataFrame()
    try:
        return pd.read_csv(io.BytesIO(b), sep=";", dtype=str).fillna("")
    except Exception:
        return pd.DataFrame()


# último periodo publicado por cada fuente: (nombre, consulta que devuelve la fecha o el texto, tipo de periodo)
_PERIODOS = [
    ("EPA (INE)", "SELECT max(fecha) FROM mart_poblacion_actividad", "T"),
    ("Coste laboral (INE)", "SELECT max(fecha) FROM mart_coste_laboral", "T"),
    ("IPC (INE)", "SELECT max(fecha) FROM mart_precios WHERE indice = 'IPC'", "M"),
    ("Sociedades (INE)", "SELECT max(fecha) FROM fact_ine WHERE tabla_id = '13913'", "M"),
    ("PIB regional (INE)", "SELECT max(fecha) FROM fact_ine WHERE tabla_id = '80109'", "A"),
    ("NEET (INE)", "SELECT max(fecha) FROM mart_neet", "A"),
    ("Salarios EES (INE)", "SELECT max(fecha) FROM mart_salarios_ees_detalle", "A"),
    ("Paro y contratos (SEPE)", "SELECT max(fecha) FROM fact_sepe_paro_municipio", "M"),
    ("Afiliación (Seg. Social)", "SELECT max(fecha) FROM fact_ss_afiliacion", "M"),
    ("Bajas IT (Seg. Social)", "SELECT make_date(max(anyo), 1, 1) + INTERVAL (arg_max(mes_hasta, anyo * 100 + mes_hasta) - 1) MONTH "
                               "FROM fact_incapacidad_temporal", "M"),
    ("ETT (Ministerio)", "SELECT max(fecha) FROM fact_ett_mensual", "M"),
    ("Convenios (Ministerio)", "SELECT make_date(max(anyo_efectos), 1, 1) + INTERVAL (arg_max(mes_registro, anyo_efectos * 100 + "
                               "coalesce(mes_registro, 0)) - 1) MONTH FROM fact_convenios WHERE mes_registro IS NOT NULL", "M"),
    ("Accidentes (Ministerio)", "SELECT max(periodo_hasta) FROM fact_accidentes", "M"),
    ("Formación (FUNDAE)", "SELECT make_date(max(anyo), 1, 1) FROM fact_fundae", "A"),
]


def periodos():
    """[(fuente, 'ago 2026' | '2T 2026' | '2025')]: hasta dónde llega cada fuente en esta carga (las que falten se omiten)."""
    return _periodos(clave())


@st.cache_data(ttl=TTL, show_spinner=False)
def _periodos(firma):
    meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    out = []
    for nombre, sql, tipo in _PERIODOS:
        d = q(sql)
        if d.empty or pd.isna(d.iloc[0, 0]):
            continue
        f = pd.Timestamp(d.iloc[0, 0])
        out.append((nombre, f"{(f.month - 1) // 3 + 1}T {f.year}" if tipo == "T" else str(f.year) if tipo == "A"
                    else f"{meses[f.month - 1]} {f.year}"))
    return out
