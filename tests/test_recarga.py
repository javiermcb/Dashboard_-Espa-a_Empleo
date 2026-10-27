"""Recarga de los módulos de comun/ al publicar código nuevo (Streamlit Cloud los mantiene en memoria)."""
import importlib
import sys
from pathlib import Path

from comun import recarga

RAIZ = Path(__file__).resolve().parent.parent


def test_todo_modulo_de_comun_esta_en_la_lista_de_recarga():
    """Si se añade un módulo a comun/ y no se lista en ORDEN, Streamlit Cloud seguiría usando su versión antigua."""
    modulos = {f"comun.{p.stem}" for p in (RAIZ / "comun").glob("*.py") if p.stem not in ("__init__", "recarga")}
    assert modulos <= set(recarga.ORDEN), f"faltan en recarga.ORDEN: {sorted(modulos - set(recarga.ORDEN))}"


def test_base_se_recarga_la_ultima():
    assert recarga.ORDEN[-1] == "comun.base"


def test_no_recarga_si_el_codigo_no_cambia():
    sys._rrhh_huella = None
    recarga.comprobar()
    assert recarga.comprobar() is False


def test_la_huella_sobrevive_a_recargar_el_propio_modulo():
    recarga.comprobar()
    huella = sys._rrhh_huella
    importlib.reload(recarga)
    assert recarga.comprobar() is False and sys._rrhh_huella == huella


def test_cada_dashboard_recarga_el_recargador():
    apps = sorted((RAIZ / "dashboards").glob("dashboard_*/app.py"))
    assert apps and all("importlib.reload(recarga)" in a.read_text(encoding="utf-8") for a in apps)
