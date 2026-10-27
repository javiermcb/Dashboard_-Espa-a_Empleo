"""
recarga.py — Al publicar código nuevo, Streamlit Cloud vuelve a ejecutar las páginas pero mantiene en memoria la versión
antigua de los módulos auxiliares (comun.graficos...), y una página nueva que usa una función nueva falla con
AttributeError hasta reiniciar la app (o, peor, se queda con el comportamiento antiguo sin avisar: ocurrió con la barra
lateral, que pinta comun.base). Este módulo los recarga una vez cuando cambia el código, en orden de dependencias.

Cada app.py hace `importlib.reload(recarga)` antes de usarlo: así la lista ORDEN y la lógica de aquí también se actualizan
(si no, la propia versión antigua de este módulo decidiría qué recargar). Por eso la huella no vive en una variable del
módulo, que se reinicia al recargarlo, sino en `sys`.
"""
import hashlib, importlib, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
# en orden de dependencias; al añadir un módulo a comun/ que importen las páginas, añadirlo aquí (comun.base el último)
ORDEN = ["comun.datos", "comun.graficos", "comun.relato", "comun.impacto", "comun.base"]


def _calcular():
    h = hashlib.sha256()
    for f in sorted(RAIZ.glob("*.py")):
        h.update(f.name.encode()); h.update(f.read_bytes())
    return h.hexdigest()


def comprobar():
    """Recarga los módulos propios si el código ha cambiado desde la última ejecución. True si ha recargado."""
    actual = _calcular()
    anterior = getattr(sys, "_rrhh_huella", None)  # huella del código cargado; vive mientras el servidor no se reinicie
    if actual == anterior:
        return False
    primera = anterior is None
    sys._rrhh_huella = actual
    recargados = [n for n in ORDEN if n in sys.modules]
    for n in recargados:
        importlib.reload(sys.modules[n])
    return bool(recargados) and not primera
