"""Lector de Eurostat (JSON-stat) con respuestas sintéticas, sin red."""
import json

import eurostat


def jsonstat(dims, valores, estados=None):
    """dims: [(id, [códigos])] -> JSON-stat con valores en el orden de producto cartesiano."""
    return {"id": [d for d, _ in dims], "size": [len(c) for _, c in dims],
            "dimension": {d: {"category": {"index": {c: i for i, c in enumerate(cs)}}} for d, cs in dims},
            "value": {str(i): v for i, v in enumerate(valores) if v is not None}, "status": estados or {}}


def test_leer_omite_vacios_y_conserva_la_marca():
    j = jsonstat([("sex", ["T", "M"]), ("time", ["2024", "2025"])], [1.0, None, 3.0, 4.0], {"3": "d"})
    celdas = eurostat.leer(j)
    assert [(c["sex"], c["time"], c["valor"], c["estado"]) for c in celdas] == [("T", "2024", 1.0, ""), ("M", "2024", 3.0, ""), ("M", "2025", 4.0, "d")]


def test_url_lleva_los_filtros_repetidos():
    u = eurostat.url("demo_pjan", {"geo": "ES", "age": ["Y16", "Y17"]})
    assert u.count("age=") == 2 and "geo=ES" in u and "sinceTimePeriod=" in u


def test_poblacion_suma_las_14_edades_y_descarta_anyos_incompletos():
    edades = eurostat.EDADES_16_29
    j = jsonstat([("sex", ["T"]), ("age", edades), ("time", ["2024", "2025"])],
                 [100] * len(edades) + [None] + [100] * (len(edades) - 1))
    # el índice recorre sex, age, time: año 2025 de la primera edad sin dato -> ese año no es completo
    valores = {}
    for i, e in enumerate(edades):
        valores[f"{i * 2}"] = 100
        if i:
            valores[f"{i * 2 + 1}"] = 100
    j["value"] = valores
    filas = eurostat._serie("poblacion_16_29", lambda u: json.dumps(j).encode())
    assert [(f[1], f[2], f[4]) for f in filas] == [(2024, "Total", 1400)]


def test_serie_con_categoria_y_multiplicador():
    j = jsonstat([("isced11", ["ED0-2", "ED3_4", "ED5-8"]), ("time", ["2025"])], [1000.0, 2000.0, 3000.0])
    filas = eurostat._serie("poblacion_nivel", lambda u: json.dumps(j).encode())
    assert [(f[3], f[4]) for f in filas] == [("Educación superior", 3_000_000.0), ("Primaria y primera etapa de secundaria", 1_000_000.0),
                                             ("Segunda etapa de secundaria y postsecundaria", 2_000_000.0)]


def test_cargar_anota_la_serie_que_falla_y_sigue():
    ok = jsonstat([("sex", ["T"]), ("time", ["2025"])], [41.2])

    def descargar(u):
        if "lfsa_ergan" in u:
            return json.dumps(ok).encode()
        raise OSError("sin red")
    cab, filas, fallos = eurostat.cargar(descargar)
    assert cab == eurostat.CABECERA and {f[0] for f in filas} == {"tasa_empleo_15_29"}
    assert set(fallos) == set(eurostat.SERIES) - {"tasa_empleo_15_29"}


def test_cargar_sin_ninguna_serie_falla():
    try:
        eurostat.cargar(lambda u: (_ for _ in ()).throw(OSError("sin red")))
    except ValueError as e:
        assert "ninguna serie" in str(e)
    else:
        raise AssertionError("debería fallar")
