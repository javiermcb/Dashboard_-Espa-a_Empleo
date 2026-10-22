"""
recarga.py — Al publicar código nuevo, Streamlit Cloud vuelve a ejecutar las páginas pero mantiene en memoria la versión
antigua de los módulos auxiliares (comun.graficos, comun.acceso...), y una página nueva que usa una función nueva falla con
AttributeError hasta reiniciar la app. Este módulo los recarga una vez cuando cambia el código, en orden de dependencias.
"""
import hashlib, importlib, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ORDEN = ["comun.datos", "comun.graficos", "comun.calculos_informe", "comun.acceso", "comun.relato"]
_huella = None  # huella del código cargado; vive mientras el servidor no se reinicie


def _calcular():
    h = hashlib.sha256()
    for f in sorted(RAIZ.glob("*.py")):
        h.update(f.name.encode()); h.update(f.read_bytes())
    return h.hexdigest()


def comprobar():
    """Recarga los módulos propios si el código ha cambiado desde la última ejecución. True si ha recargado."""
    global _huella
    actual = _calcular()
    if actual == _huella:
        return False
    primera = _huella is None
    _huella = actual
    recargados = [n for n in ORDEN if n in sys.modules]
    for n in recargados:
        importlib.reload(sys.modules[n])
    return bool(recargados) and not primera
