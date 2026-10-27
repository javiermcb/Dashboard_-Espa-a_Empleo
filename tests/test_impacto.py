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
    assert svg.startswith("<div class='im-sparkw'><svg") and "pathLength='1'" in svg and "stop-color='#2a78d6'" in svg
    assert "class='im-dot'" in svg and "<circle" not in svg  # el punto final va fuera del SVG para no deformarse


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


def test_tarjeta_doble_apila_las_dos_partes_en_un_solo_hueco():
    html = "".join(im._mitad(p) for p in [dict(titulo="Hombres, 2025", valor="11,4 %", delta="▼ -0,5 p.p.", bueno=True, serie=[3, 2, 1]),
                                           dict(titulo="Mujeres, 2025", valor="11,5 %", serie=[3, 2, 1])])
    assert html.count("class='im-mitad'") == 2 and "Hombres, 2025" in html and "Mujeres, 2025" in html


def test_tabla_semaforo_gris_en_la_media_y_verde_rojo_segun_el_sentido():
    import pandas as pd
    from comun import graficos as g
    df = pd.DataFrame({"T": ["España", "A", "B"], "Empleo": [30.0, 40.0, 20.0], "Paro": [20.0, 10.0, 30.0]})
    st = g.tabla_semaforo(df, "T", "España", bajo_es_bueno=("Paro",))
    css = st._compute().ctx
    assert g.GRIS_MEDIA in css[(0, 1)][0][1] and g.GRIS_MEDIA in css[(0, 0)][0][1]  # media en gris
    assert css[(1, 1)][0][1] != css[(2, 1)][0][1]  # empleo: más alto y más bajo, colores distintos
    verde_a, rojo_a = g._mezcla(g.BLANCO, g.VERDE, 0.9), g._mezcla(g.BLANCO, g.ROJO, 0.9)
    assert css[(1, 1)][0][1] == verde_a and css[(2, 1)][0][1] == rojo_a  # empleo alto = verde
    assert css[(1, 2)][0][1] == verde_a and css[(2, 2)][0][1] == rojo_a  # paro bajo = verde
    assert df.iloc[1, 1] == 40.0 and st.data.equals(df)  # los datos no se tocan
