"""Lectura de la configuración y de los periodos del INE (sin red)."""
import csv

import ine


def test_tablas_ine_csv_valido():
    with open(ine.CONFIG, encoding="utf-8") as f:
        tablas = list(csv.DictReader(f, delimiter=";"))
    assert tablas, "tablas_ine.csv vacío"
    assert ine.validar(tablas) is None


def test_validar_detecta_repetidas_y_columnas_de_mas():
    assert "repetidas" in ine.validar([{"tabla_id": "1"}, {"tabla_id": "1"}])
    assert "sobran columnas" in ine.validar([{"tabla_id": "2", None: ["x"]}])


def test_fecha_en_milisegundos_y_texto():
    assert ine.fecha_iso(1735686000000) == "2025-01-01"  # medianoche en Madrid (UTC+1)
    assert ine.fecha_iso("2025-04-01T00:00:00.000+02:00") == "2025-04-01"
    assert ine.fecha_iso(None) == ""


def test_periodo_de_tablas_ods_solo_con_nombre():
    assert ine.periodo({"NombrePeriodo": "2025"}) == ("2025-01-01", "2025", "A")
    assert ine.periodo({"Fecha": "2024-07-01T00:00:00", "Anyo": 2024, "T3_Periodo": "T3"}) == ("2024-07-01", 2024, "T3")
    assert ine.periodo({}) == ("", "", "")
