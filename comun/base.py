"""
base.py — Arranque común de los dashboards: página, menú, barra lateral con la fuente de los datos y pie de periodos.

Cada dashboards/<nombre>/app.py solo declara su título y su menú y llama a arrancar(). Los datos y los gráficos
son los de comun/; lo único propio de cada dashboard son sus páginas (dashboards/<nombre>/paginas/).
"""
from pathlib import Path

import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
PAGINAS_COMUNES = RAIZ / "comun" / "paginas"

AVISO_FUENTES = ("Elaboración propia con datos extraídos del sitio web del INE (www.ine.es), del SEPE, de la Seguridad Social "
                 "y del Ministerio de Trabajo y Economía Social. Los indicadores calculados (cocientes, acumulados, "
                 "aproximaciones) son elaboración propia, no cifras oficiales. Estos organismos no participan en esta "
                 "herramienta ni la respaldan. Periodo y fecha de cada fuente: «Estado de los datos».")
AVISO_PERSONAS = ("Datos agregados de territorios y sectores: describen colectivos, no personas. No deben aplicarse a un "
                  "candidato o trabajador concreto para seleccionarlo, perfilarlo o tomar decisiones sobre él.")


def comun(nombre, titulo, icono):
    """Página de comun/paginas/ (estado de los datos, descargas) para incluirla en el menú de cualquier dashboard."""
    return st.Page(str(PAGINAS_COMUNES / f"{nombre}.py"), title=titulo, icon=icono, url_path=nombre)


def arrancar(titulo, icono, menu, mapas=False):
    """
    titulo  nombre del dashboard (pestaña del navegador y barra lateral)
    menu    {sección: [st.Page, ...]}; la primera página con default=True es la de entrada
    mapas   True: selector «Geográfico / Mosaico» de los mapas de comunidades en la barra lateral
    """
    st.set_page_config(page_title=titulo, page_icon=icono, layout="wide")

    from comun import recarga
    recarga.comprobar()  # tras publicar código nuevo, recarga los módulos comunes (Streamlit Cloud guarda la versión antigua)

    from comun import datos, relato

    menu = dict(menu)
    nav = st.navigation(menu, expanded=True)

    with st.sidebar:
        st.caption(titulo)
        _, disponibles, faltan = datos.conexion()
        carga = datos.fecha_carga()
        if carga:
            st.caption(f"Datos de la carga del {carga}")
        if faltan:
            st.caption(f"Tablas no disponibles en esta carga: {', '.join(faltan)}")
        st.caption(AVISO_FUENTES)
        st.caption(AVISO_PERSONAS)
        if mapas:
            st.radio("Mapas de comunidades", ["Geográfico", "Mosaico"], horizontal=True, key="vista_mapa",
                     help="Mosaico: una casilla por comunidad, mismo tamaño para todas (se comparan mejor las pequeñas).")

    errores = datos.errores_descarga()
    if errores and not disponibles:
        # sin ninguna tabla: casi siempre es el token o la URL; se dice en claro en vez de mostrar páginas vacías
        st.error("No se han podido cargar los datos: " + sorted(set(errores.values()))[0])
        st.stop()
    if errores:
        st.sidebar.warning(f"{len(errores)} tablas no se han podido actualizar (se muestra la última copia descargada, "
                           "si la hay). Detalle en «Estado de los datos».")

    nav.run()

    # pie de todas las páginas: hasta qué periodo llega cada fuente (evita mezclar datos de fechas distintas sin saberlo)
    relato.estilo()
    relato.pie_periodos(datos.periodos())
