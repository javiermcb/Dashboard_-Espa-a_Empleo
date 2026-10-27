"""Piezas de comun/impacto.py que no dependen de Streamlit: formato de variaciones, minigráficos y separación de etiquetas."""
from comun import impacto as im


def test_delta_pp_con_signo_flecha_y_coma():
    assert im.delta_pp(11.5, 12.0) == "▼ -0,5 p.p."
    assert im.delta_pp(12.4, 12.0) == "▲ +0,4 p.p."
    assert "p,p" not in im.delta_pp(11.5, 12.0)  # la coma decimal no toca la abreviatura


def test_delta_pp_sin_cambio_y_sin_dato():
    assert im.delta_pp(5.0, 5.01) == "■ 0,0 p.p."
    assert im.delta_pp(5.0, None) is None
    assert im.delta_pp(float("nan"), 5.0) is None


def test_delta_rel():
    assert im.delta_rel(103, 100) == "▲ +3,0 %"
    assert im.delta_rel(90, 100) == "▼ -10,0 %"
    assert im.delta_rel(5, 0) is None


def test_minigrafico():
    assert im._spark([1.0], "#2a78d6") == ""  # una sola cifra no hace línea
    svg = im._spark([3, 1, 2, 5], "#2a78d6")
    assert svg.startswith("<svg") and "pathLength='1'" in svg and "stop-color='#2a78d6'" in svg


def test_etiquetas_finales_no_se_pisan_y_mantienen_el_orden():
    out = im._separar([10.0, 10.1, 10.05, 20.0], 1.0)
    orden = sorted(range(4), key=lambda i: [10.0, 10.1, 10.05, 20.0][i])
    pos = [out[i] for i in orden]
    assert all(b - a >= 0.999 for a, b in zip(pos, pos[1:]))
    assert out[3] == 20.0  # la que ya estaba lejos no se mueve


def test_rosco_reparte_en_porcentajes_y_ordena():
    import pandas as pd
    df = pd.DataFrame({"c": ["A", "B", "C", "D"], "v": [50.0, 30.0, 20.0, 0.0]})  # solo para probar la función
    ch = im._rosco(df, "c", "v", orden=["C", "B", "A", "D"], centro="2025", sub="x")
    d = ch.to_dict()
    capas = d["layer"]
    assert capas[0]["mark"]["type"] == "arc" and len(capas) == 3
    datos = d["datasets"][d["layer"][0]["data"]["name"]]
    assert [r["c"] for r in sorted(datos, key=lambda r: r["_ord"])] == ["C", "B", "A"]  # la categoría con 0 no entra
    assert abs(sum(r["_pct"] for r in datos) - 1) < 1e-9
