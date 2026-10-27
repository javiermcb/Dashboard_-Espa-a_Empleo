"""Dashboard 2 · pendiente de definir. Arranque en local:  streamlit run dashboards/dashboard_2/app.py"""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # raíz del repo: para importar comun/

import streamlit as st  # noqa: E402

from comun import base, recarga  # noqa: E402

importlib.reload(recarga)  # la lista de módulos a recargar también se actualiza al publicar código nuevo
recarga.comprobar()

AQUI = Path(__file__).resolve().parent

base.arrancar(
    titulo="Dashboard 2",
    tablas=["dim_territorio", "mart_tasas_epa"],
    icono="📊",
    menu={
        "Dashboard 2": [
            st.Page(str(AQUI / "paginas" / "inicio.py"), title="Inicio", icon=":material/home:", default=True),
        ],
        "Datos": [
            base.comun("estado", "Estado de los datos", ":material/fact_check:"),
            base.comun("datos_descarga", "Datos y descargas", ":material/download:"),
        ],
    },
)
