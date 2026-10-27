"""
Prueba de humo: abre cada página de cada dashboard con la muestra del modelo (resultados/dev_modelo) y falla si alguna
lanza una excepción. Se ejecuta en GitHub Actions (apps_pruebas.yml). En local:  python -m pytest tests -q
"""
import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

RAIZ = Path(__file__).resolve().parent.parent
os.environ.setdefault("RRHH_DATOS", str(RAIZ / "resultados" / "dev_modelo"))
DASHBOARDS = sorted(p.name for p in (RAIZ / "dashboards").glob("dashboard_*") if (p / "app.py").exists())
COMUNES = ["estado.py", "datos_descarga.py"]


def _abrir(dashboard):
    at = AppTest.from_file(str(RAIZ / "dashboards" / dashboard / "app.py"), default_timeout=180)
    return at.run()


def _sin_errores(at, donde):
    assert not at.exception, f"{donde}: {at.exception[0].value}"
    assert not at.error, f"{donde}: {[e.value for e in at.error]}"


@pytest.mark.parametrize("dashboard", DASHBOARDS)
def test_entrada(dashboard):
    _sin_errores(_abrir(dashboard), dashboard)


@pytest.mark.parametrize("dashboard", DASHBOARDS)
def test_paginas_propias(dashboard):
    for pagina in sorted((RAIZ / "dashboards" / dashboard / "paginas").glob("*.py")):
        at = _abrir(dashboard)
        _sin_errores(at.switch_page(f"paginas/{pagina.name}").run(), f"{dashboard}/{pagina.name}")


@pytest.mark.parametrize("pagina", COMUNES)
def test_paginas_comunes(pagina):
    at = _abrir(DASHBOARDS[0])
    _sin_errores(at.switch_page(f"../../comun/paginas/{pagina}").run(), f"comun/{pagina}")


@pytest.mark.parametrize("dashboard", DASHBOARDS)
def test_sin_boton_pantalla_completa(dashboard):
    """Cada dashboard inyecta la regla que oculta el botón «Fullscreen» (útil al incrustarlos en otra web)."""
    at = _abrir(dashboard)
    reglas = [m.value for m in at.markdown if 'aria-label="Fullscreen"' in m.value and "display: none" in m.value]
    assert reglas, f"{dashboard}: falta la regla CSS que oculta «Fullscreen»"


@pytest.mark.parametrize("dashboard", DASHBOARDS)
def test_solo_carga_sus_tablas(dashboard):
    """Cada dashboard abre solo las tablas que declara (y alertas): así arranca rápido y gasta poca memoria."""
    from comun import datos
    at = _abrir(dashboard)
    _sin_errores(at, dashboard)
    declaradas = {t.strip('"') for t in (RAIZ / "dashboards" / dashboard / "app.py").read_text(encoding="utf-8").split("tablas=[", 1)[1].split("]", 1)[0].replace('"', "").split(",") if t.strip()}
    _, disponibles, _ = datos.conexion()
    assert set(disponibles) - {"alertas"} <= {t.strip() for t in declaradas}, f"{dashboard}: carga tablas que no declara"


@pytest.mark.parametrize("dashboard", DASHBOARDS)
def test_barra_lateral_minima(dashboard):
    """La barra lateral solo lleva la fecha de los datos; la atribución de las fuentes y los enlaces a las páginas van en el pie."""
    from comun import base
    at = _abrir(dashboard)
    _sin_errores(at, dashboard)
    lateral = " ".join(m.value for m in at.sidebar.markdown)
    assert "bl-fecha" in lateral and "Datos" in lateral
    assert not at.sidebar.radio and not at.sidebar.caption, f"{dashboard}: la barra lateral lleva más que la fecha"
    cuerpo = " ".join(m.value for m in at.markdown)
    assert "Elaboración propia con datos extraídos" in cuerpo or base.AVISO_FUENTES[:40] in cuerpo, f"{dashboard}: falta el aviso de fuentes"
