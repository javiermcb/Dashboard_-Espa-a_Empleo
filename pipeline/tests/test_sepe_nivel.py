"""Lector de «Demandantes de empleo por nivel formativo» del SEPE (texto de ejemplo de un fichero real, sin red)."""
import pytest

import fuentes

CSV = '''"Nivel Formativo Agrupación OBS-1";"Indicadores";"Dem. Parados Hombres";"Dem. Parados Mujeres";"Dem. Parados Españoles";"Dem. Parados Extranjeros";"Dem. Parados <= 3 meses";"Dem. Parados de 4 a 12 meses";"Dem. Parados > 12 meses"
"Estudios primarios/No acreditado";;"392.725";"541.950";"679.257";"255.418";"14.443";"27.752";"892.480"
"Educación secundaria obligatoria";;"245.624";"351.635";"562.045";"35.214";"7.824";"15.204";"574.231"
"Bachillerato y equivalentes";;"82.381";"129.853";"186.907";"25.327";"3.600";"6.695";"201.939"
"FP Grado medio";;"63.124";"125.981";"182.362";"6.743";"2.858";"5.582";"180.665"
"FP Grado superior";;"67.162";"112.397";"175.658";"3.901";"2.999";"5.648";"170.912"
"Universitario";;"81.239";"161.693";"228.817";"14.115";"4.668";"8.258";"230.006"
"Indeterminado";;"363";"917";"447";"833";"40";"64";"1.176"
'''


def test_lee_los_siete_niveles_con_punto_de_millares():
    filas = fuentes.parsear_nivel_formativo(CSV, "2026-04-01")
    assert len(filas) == 7
    assert filas[0] == ["2026-04-01", "Estudios primarios/No acreditado", 392725, 541950, 679257, 255418, 934675]
    assert all(f[4] + f[5] == f[6] for f in filas[:6])  # españoles + extranjeros = hombres + mujeres


def test_rechaza_un_fichero_que_no_es_el_esperado():
    with pytest.raises(ValueError):
        fuentes.parsear_nivel_formativo("<html>no encontrado</html>", "2026-04-01")
    with pytest.raises(ValueError):
        fuentes.parsear_nivel_formativo(CSV.splitlines()[0] + "\n" + CSV.splitlines()[1], "2026-04-01")
