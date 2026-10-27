"""Lector de FUNDAE (pipeline/fundae.py) con Excel sintéticos con la misma disposición que los del visor."""
import io
import sys
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import fundae  # noqa: E402


def _excel(filas, hoja):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = hoja
    for f in filas:
        ws.append(f)
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


def test_anyos_en_filas():  # rptSeries01: año y medida en filas, categorías en columnas
    x = _excel([[], [None, "Número de participantes formados y horas de formación por edad. Total"], [],
                [None, None, None, "De 16 a 25", "De 26 a 35", "Total"], [None, "Año"],
                [None, "2025", "Participantes ", 10, 20, 30], [None, None, "Horas de formación", 100, 200, 300],
                [None, "2024", "Participantes ", 9, 18, 27], [None, None, "Horas de formación", 90, 180, 270],
                [None, "NOTAS:"]], "rptSeries01")
    r = fundae.leer("01", x)
    assert len(r) == 12
    assert ["01", 2025, "Edad", "De 26 a 35", "Participantes", 20.0] == [r[1][0], r[1][2], r[1][3], r[1][4], r[1][8], r[1][9]]
    assert {(f[2], f[8]) for f in r if f[4] == "Total"} == {(2025, "Participantes"), (2025, "Horas de formación"),
                                                           (2024, "Participantes"), (2024, "Horas de formación")}


def test_anyos_en_columnas_y_ccaa():  # rptSeries30: categorías (comunidades) en filas, años en columnas
    x = _excel([[], [None, "Número de participantes formados y horas de formación por Comunidad Autónoma del participante."],
                [None, None, None, "2025", "2024"], [None, "CC.AA. del participante"],
                [None, "Castilla-La Mancha", "Participantes ", 5, 4], [None, None, "Horas de formación", 50, 40],
                [None, "Total", "Participantes ", 7, 6], [None, None, "Horas de formación", 70, 60]], "rptSeries30")
    r = fundae.leer("30", x)
    clm = [f for f in r if f[4] == "Castilla-La Mancha"]
    assert len(clm) == 4 and all(f[7] == "C08" for f in clm)
    assert [f[9] for f in clm if f[2] == 2024 and f[8] == "Participantes"] == [4.0]


def test_ccaa_por_columnas_con_anyo_fijo():  # rptSeries50: «Año: 2025», comunidad en filas, sector en columnas
    x = _excel([[], [None, "Empresas formadoras y crédito dispuesto según Comunidad Autónoma y sector de actividad."],
                [None, "Año: 2025"], [None, "Comunidad Autónoma de la empresa", None, "Agricultura", "Industria", "Total"], [],
                [None, "Aragón", "Empresas Formadoras", 1, 2, 3], [None, None, "Crédito dispuesto", 10.5, 20, 30.5]], "rptSeries50")
    r = fundae.leer("50", x)
    assert len(r) == 6 and all(f[2] == 2025 and f[4] == "Aragón" and f[7] == "C02" for f in r)
    assert [f[9] for f in r if f[6] == "Agricultura" and f[8] == "Crédito dispuesto"] == [10.5]


def test_filas_sin_medida():  # rptSeries41: año solo en una fila, organización en filas, tamaño en columnas
    x = _excel([[], [None, "Empresas formadoras según organización de la formación y tamaño de la empresa."],
                [None, None, None, "De 1 a 9", "Más de 249", "Total"], [None, "2025"],
                [None, "Formación Agrupada", None, 5, 1, 6], [None, "Total", None, 7, 2, 9]], "rptSeries41")
    r = fundae.leer("41", x)
    assert len(r) == 6 and all(f[2] == 2025 and f[8] == "Empresas formadoras" for f in r)
    assert [f[9] for f in r if f[4] == "Formación Agrupada" and f[6] == "Más de 249"] == [1.0]


def test_contenidos_formativos():  # rptSeries13: contenido en filas, medida en la segunda columna, años en columnas con huecos
    x = _excel([[], [None, "Número de participantes formados y horas de formación por contenidos formativos. Formación bonificada"], [],
                [None, None, None, "2025", "2024", None, None, "2020"], [None, "Contenidos formativos"],
                [None, "Acabado de cueros", "Participantes ", 290, 8, None, None, 639],
                [None, None, "Horas de formación", 1669, 40, None, None, 5537],
                [None, "Idiomas", "Participantes ", 100, 90, None, None, 80],
                [None, None, "Horas de formación", 1000, 900, None, None, 800], [None, "NOTAS:"]], "rptSeries13")
    r = fundae.leer("13", x)
    assert len(r) == 12
    assert {(f[2], f[4], f[8]): f[9] for f in r if f[4] == "Idiomas" and f[8] == "Participantes"} == {
        (2025, "Idiomas", "Participantes"): 100.0, (2024, "Idiomas", "Participantes"): 90.0, (2020, "Idiomas", "Participantes"): 80.0}
    assert {f[3] for f in r} == {"Contenidos formativos"}


def test_orden_de_carga_primero_lo_que_falta_y_lo_mas_viejo(tmp_path):
    import os
    series = list(fundae.SERIES)
    for i, serie in enumerate(series[:-1]):  # todas con copia salvo la última, de más vieja a más nueva en el orden de SERIES
        p = tmp_path / f"rptSeries{serie}.csv"
        p.write_text("x")
        os.utime(p, (1000 + i, 1000 + i))
    orden = fundae.orden_de_carga(tmp_path)
    assert orden[0] == series[-1]  # la que no tiene copia va la primera
    assert orden[1:] == series[:-1]  # y después, de la copia más antigua a la más reciente
    assert sorted(orden) == sorted(series)
