"""
base.py — Arranque común de los dashboards: página, menú, barra lateral mínima con la fecha de los datos y pie de página
(solo día y hora de la carga). Las páginas «Estado de los datos» y «Datos y descargas» siguen en el menú, sin enlaces visibles.

Cada dashboards/<nombre>/app.py solo declara su título y su menú y llama a arrancar(). Los datos y los gráficos
son los de comun/; lo único propio de cada dashboard son sus páginas (dashboards/<nombre>/paginas/).
"""
from html import escape
from pathlib import Path

import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
PAGINAS_COMUNES = RAIZ / "comun" / "paginas"

# Oculta el botón «Fullscreen» que Streamlit muestra al pasar el ratón por gráficos y tablas (molesta al incrustar los
# dashboards en otra web). Se apoya en atributos internos de Streamlit (data-testid / aria-label), fijados en la versión de
# requirements.txt: al actualizar Streamlit hay que comprobar que sigue funcionando.
CSS_SIN_PANTALLA_COMPLETA = """<style>
[data-testid="stElementToolbar"] button[aria-label="Fullscreen"] { display: none !important; }
</style>"""

# Barra lateral mínima (unos 2 cm): solo la fecha de los datos. Se apoya en atributos internos de Streamlit (data-testid, incluido el botón de abrir la barra), fijados
# en la versión de requirements.txt: al actualizar Streamlit hay que comprobar que sigue funcionando. En pantallas estrechas
# (móvil) no se fuerza el ancho: Streamlit la pliega sola y la fecha también va en el pie.
CSS_BARRA_MINIMA = """<style>
@media (min-width: 768px) {
  [data-testid="stSidebar"] { width: 76px !important; min-width: 76px !important; max-width: 76px !important; }
  [data-testid="stSidebarContent"] { padding: 0.9rem 0.35rem 0.5rem 0.35rem; }
}
[data-testid="stSidebarHeader"], [data-testid="stSidebarCollapseButton"], [data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarResizeHandle"], [data-testid="stSidebarNav"], [data-testid="stExpandSidebarButton"] { display: none !important; }
[data-testid="stMainBlockContainer"] { padding-top: 3rem !important; padding-bottom: 3.5rem !important; }  /* arriba, de 6 rem: el título queda a unos 3 cm del borde; abajo, 56 px (incrustado eran 16) para que el pie no quede pegado al borde */
.bl-fecha { color: #4a5585; font-size: 0.64rem; line-height: 1.35; text-align: center; word-break: keep-all; }
.bl-fecha b { color: #00145A; font-weight: 600; display: block; margin-bottom: 0.15rem; }
</style>"""

def comun(nombre, titulo, icono):
    """Página de comun/paginas/ (estado de los datos, descargas) para incluirla en el menú de cualquier dashboard."""
    return st.Page(str(PAGINAS_COMUNES / f"{nombre}.py"), title=titulo, icon=icono, url_path=nombre)


def _fecha_corta(carga, anyo_largo=False):
    """'2026-10-26 17:49 UTC' -> ('26/10/26', '17:49 UTC'), o con año de 4 cifras ('26/10/2026', ...) si anyo_largo; si el formato no
    es ese, (texto, '')."""
    try:
        dia, hora = carga.split(" ", 1)
        a, m, d = dia.split("-")
        return f"{d}/{m}/{a if anyo_largo else a[-2:]}", hora
    except ValueError:
        return carga, ""


def _pie_fecha(carga):
    """Pie de todas las páginas: solo día y hora de la carga de los datos."""
    if not carga:
        return
    dia, hora = _fecha_corta(carga, anyo_largo=True)
    st.markdown(f"<div class='rr-pie'>Datos actualizados el {escape(dia)} a las {escape(hora)}.</div>", unsafe_allow_html=True)


def arrancar(titulo, icono, menu, pantalla_completa=False, tablas=None):
    """
    titulo  nombre del dashboard (pestaña del navegador)
    menu    {sección: [st.Page, ...]}; la primera página con default=True es la de entrada. La navegación no se pinta (ni barra
            lateral ni enlaces): las páginas siguen disponibles por su dirección (/estado, /datos_descarga)
    tablas  nombres de las tablas del modelo que usa el dashboard (sin ruta): solo se descargan y abren esas (None: todas)
    pantalla_completa   True: deja el botón «Fullscreen» de gráficos y tablas (por defecto se oculta)
    """
    st.set_page_config(page_title=titulo, page_icon=icono, layout="wide")
    if not pantalla_completa:
        st.markdown(CSS_SIN_PANTALLA_COMPLETA, unsafe_allow_html=True)

    from comun import recarga
    recarga.comprobar()  # tras publicar código nuevo, recarga los módulos comunes (Streamlit Cloud guarda la versión antigua)

    from comun import datos, relato
    datos.usar(tablas)

    menu = dict(menu)
    nav = st.navigation(menu, position="hidden")
    st.markdown(CSS_BARRA_MINIMA, unsafe_allow_html=True)

    _, disponibles, faltan = datos.conexion()
    carga = datos.fecha_carga()
    with st.sidebar:
        if carga:
            dia, hora = _fecha_corta(carga)
            st.markdown(f"<div class='bl-fecha'><b>Datos</b>{escape(dia)}<br>{escape(hora)}</div>", unsafe_allow_html=True)

    errores = datos.errores_descarga()
    if errores and not disponibles:
        # sin ninguna tabla: casi siempre es el token o la URL; se dice en claro en vez de mostrar páginas vacías
        st.error("No se han podido cargar los datos: " + sorted(set(errores.values()))[0])
        st.stop()
    if errores:
        st.warning(f"{len(errores)} tablas no se han podido actualizar (se muestra la última copia descargada, "
                   "si la hay). Detalle en «Estado de los datos».")

    nav.run()

    relato.estilo()
    _pie_fecha(carga)
