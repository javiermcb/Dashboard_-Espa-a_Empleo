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
