"""Todos los módulos de comun/ se pueden importar. Las pruebas de páginas no lo detectan si ninguna página usa el módulo
(así pasó con un import con el nombre antiguo, que solo habría fallado al llamar a una función sin uso)."""
import importlib
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
MODULOS = sorted(p.stem for p in (RAIZ / "comun").glob("*.py") if p.stem != "__init__")


@pytest.mark.parametrize("modulo", MODULOS)
def test_modulo_comun_importable(modulo):
    importlib.import_module(f"comun.{modulo}")


def test_imports_internos_con_ruta_de_paquete():
    """Un `import datos` suelto (nombre de antes de mover los módulos a comun/) fallaría en Streamlit Cloud."""
    sueltos = []
    for p in (RAIZ / "comun").rglob("*.py"):
        for n, linea in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            l = linea.strip()
            if l.startswith(("import ", "from ")) and any(
                    l.split()[1] == m or l.split()[1].startswith(m + ".") for m in MODULOS):
                sueltos.append(f"{p.relative_to(RAIZ)}:{n}: {l}")
    assert not sueltos, sueltos
