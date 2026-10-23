"""Lectura del detalle de incapacidad temporal (hoja 'Datos mensuales') con un fichero sintético (sin red)."""
import io

import openpyxl

import mites_detalle


def _fichero(filas):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Datos mensuales"
    ws.append(["Ejercicio", "Mes", "Organismo", "Régimen", "Contingencia", "Sexo", "Provincia", "Indicador", "Suma de Cantidad",
               "Origen"])
    for f in filas:
        ws.append(f)
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


def test_suma_organismos_y_resuelve_provincias():
    datos = _fichero([
        [2026, "Enero", "I.N.S.S.", "RÉGIMEN GENERAL", "CONTINGENCIAS COMUNES", "MUJERES", "ALBACETE", 19, 100, "SISTEMAS"],
        [2026, "Enero", "Agregado de M.C.S.S.", "RÉGIMEN GENERAL", "CONTINGENCIAS COMUNES", "MUJERES", "ALBACETE", 19, 50, "SISTEMAS"],
        [2026, "Enero", "I.N.S.S.", "RÉGIMEN GENERAL", "CONTINGENCIAS COMUNES", "MUJERES", "ALBACETE", 20, 4500, "SISTEMAS"],
        [2026, "Febrero", "I.N.S.S.", "RÉGIMEN GENERAL", "CONTINGENCIAS COMUNES", "HOMBRES", "MADRID", 19, 10, "SISTEMAS"],
        [2025, "Cierre", "I.N.S.S.", "RÉGIMEN GENERAL", "CONTINGENCIAS COMUNES", "HOMBRES", "SIN DETERMINAR", 19, 3, "SISTEMAS"],
    ])
    cab, filas = mites_detalle.it_detalle(datos, "x.xlsx")
    assert cab[:8] == ["anyo", "mes", "regimen", "contingencia", "sexo", "provincia_id", "indicador", "cantidad"]
    d = {tuple(f[:7]): f[7] for f in filas}
    assert d[(2026, 1, "RÉGIMEN GENERAL", "CONTINGENCIAS COMUNES", "MUJERES", "P02", 19)] == 150  # INSS + mutuas
    assert d[(2026, 1, "RÉGIMEN GENERAL", "CONTINGENCIAS COMUNES", "MUJERES", "P02", 20)] == 4500
    assert d[(2026, 2, "RÉGIMEN GENERAL", "CONTINGENCIAS COMUNES", "HOMBRES", "P28", 19)] == 10  # Madrid, uniprovincial
    assert d[(2025, 0, "RÉGIMEN GENERAL", "CONTINGENCIAS COMUNES", "HOMBRES", "SD", 19)] == 3  # cierre, sin provincia
