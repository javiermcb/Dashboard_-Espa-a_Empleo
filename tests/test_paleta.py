"""Los colores del código son los de la marca (azul marino y dorado sobre blanco), sus derivados y neutros: nada de la paleta anterior."""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PERMITIDOS = {
    # marca
    "#00145a", "#d9ab42", "#e1bc68", "#e8cd8e", "#ffffff", "#fff",
    # derivados del marino y del dorado (ver comun/graficos.py)
    "#6b79b0", "#9a7312", "#aab3d8", "#fbf6e9", "#eadfbd", "#e6e9f4", "#dfe3f1", "#2f3f85", "#4a5585", "#7a84ad", "#f5f6fb", "#eef0f8",
    "#eef1f8", "#c9d0e8",
    # neutros (rejilla, ejes, rotulado)
    "#c3c2b7", "#e1e0d9",
}


def _colores(ruta):
    return {c.lower() for c in re.findall(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b", ruta.read_text(encoding="utf-8"))}


def test_solo_colores_de_marca():
    fuera = {}
    for ruta in [*(RAIZ / "comun").glob("*.py"), *(RAIZ / "dashboards").glob("*/**/*.py"), RAIZ / ".streamlit" / "config.toml"]:
        sobran = _colores(ruta) - PERMITIDOS
        if sobran:
            fuera[str(ruta.relative_to(RAIZ))] = sorted(sobran)
    assert not fuera, f"colores fuera de la paleta de marca: {fuera}"


def test_la_paleta_de_series_empieza_por_marino_y_dorado():
    from comun import graficos as g
    assert g.PALETA[:2] == ["#00145a", "#d9ab42"]
    assert len(set(g.PALETA)) == len(g.PALETA)
