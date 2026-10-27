"""
base.py — Arranque común de los dashboards: página, menú, barra lateral mínima con la fecha de los datos y pie de página
(periodos de cada fuente, avisos de atribución y enlaces a «Estado de los datos» y «Datos y descargas»).

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
.bl-fecha { color: #4a5585; font-size: 0.64rem; line-height: 1.35; text-align: center; word-break: keep-all; }
.bl-fecha b { color: #00145A; font-weight: 600; display: block; margin-bottom: 0.15rem; }
</style>"""

AVISO_FUENTES = ("Elaboración propia con datos extraídos del sitio web del INE (www.ine.es), del SEPE, de la Seguridad Social, "
                 "del Ministerio de Trabajo y Economía Social y de FUNDAE. Los indicadores calculados (cocientes, acumulados, "
                 "aproximaciones) son elaboración propia, no cifras oficiales. Estos organismos no participan en esta "
                 "herramienta ni la respaldan. Periodo y fecha de cada fuente: «Estado de los datos».")
AVISO_PERSONAS = ("Datos agregados de territorios y sectores: describen colectivos, no personas. No deben aplicarse a un "
                  "candidato o trabajador concreto para seleccionarlo, perfilarlo o tomar decisiones sobre él.")


def comun(nombre, titulo, icono):
    """Página de comun/paginas/ (estado de los datos, descargas) para incluirla en el menú de cualquier dashboard."""
    return st.Page(str(PAGINAS_COMUNES / f"{nombre}.py"), title=titulo, icon=icono, url_path=nombre)


def _fecha_corta(carga):
    """'2026-10-26 17:49 UTC' -> ('26/10/26', '17:49 UTC') (año con 2 cifras: cabe en la barra); si el formato no es ese, (texto, '')."""
    try:
        dia, hora = carga.split(" ", 1)
        a, m, d = dia.split("-")
        return f"{d}/{m}/{a[-2:]}", hora
    except ValueError:
        return carga, ""


def _pie_legal(menu, carga, faltan):
    """Pie de todas las páginas: enlaces a las páginas del menú, fecha de la carga, avisos de atribución de las fuentes y
    tablas que faltan. Antes estaban en la barra lateral."""
    paginas = [p for lista in menu.values() for p in lista]
    if len(paginas) > 1:
        cols = st.columns(len(paginas) + 2)
        for c, p in zip(cols, paginas):
            c.page_link(p)
    notas = []
    if carga:
        notas.append(f"Datos de la carga del {carga}.")
    if faltan:
        notas.append(f"Tablas no disponibles en esta carga: {', '.join(faltan)}.")
    notas += [AVISO_FUENTES, AVISO_PERSONAS]
    st.markdown("<div class='rr-pie'>" + "<br>".join(escape(n) for n in notas) + "</div>", unsafe_allow_html=True)


def arrancar(titulo, icono, menu, pantalla_completa=False, tablas=None):
    """
    titulo  nombre del dashboard (pestaña del navegador)
    menu    {sección: [st.Page, ...]}; la primera página con default=True es la de entrada. La navegación no se pinta en la barra
            lateral: las páginas se enlazan desde el pie
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

    # pie de todas las páginas: hasta qué periodo llega cada fuente (evita mezclar datos de fechas distintas sin saberlo)
    relato.estilo()
    relato.pie_periodos(datos.periodos())
    _pie_legal(menu, carga, faltan)
