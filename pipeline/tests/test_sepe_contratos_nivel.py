"""Lector de «Contratos registrados por nivel formativo» del SEPE (texto de un fichero real, sin red)."""
import pytest

import fuentes

CSV = '''"Nivel Formativo Agrupación OBS-1";"Indicadores";"EST: Contratos Hombres";"EST: Contratos Mujeres";"EST: Contratos Españoles";"EST: Contratos Extranjeros";"EST: Contratos Indefinidos";"EST: Contratos Temporales";"EST: Contratos Jornada Completa";"EST: Contratos Jornada Parcial";"EST: Contratos Jornada Fijo Discontinuo"
"Estudios primarios/No acreditado";;"297.731";"200.289";"261.766";"236.254";"244.945";"253.075";"267.183";"130.684";"100.153"
"Educación secundaria obligatoria";;"162.971";"127.741";"240.172";"50.540";"121.278";"169.434";"164.610";"84.973";"41.129"
"Bachillerato y equivalentes";;"77.169";"81.088";"123.824";"34.433";"64.855";"93.402";"84.130";"54.603";"19.524"
"FP Grado medio";;"42.202";"49.171";"83.649";"7.724";"29.844";"61.529";"55.617";"27.501";"8.255"
"FP Grado superior";;"38.756";"46.773";"81.719";"3.810";"27.976";"57.553";"53.572";"25.140";"6.817"
"Universitario";;"48.814";"77.953";"111.808";"14.959";"48.374";"78.393";"82.242";"35.988";"8.537"
"Indeterminado";;"801";"6.837";"722";"6.916";"6.271";"1.367";"2.811";"4.491";"336"
'''


def test_lee_los_siete_niveles():
    filas = fuentes.parsear_contratos_nivel(CSV, "2026-04-01")
    assert len(filas) == 7
    assert filas[0] == ["2026-04-01", "Estudios primarios/No acreditado", 297731, 200289, 244945, 253075, 498020]
    assert all(f[4] + f[5] == f[6] for f in filas)  # indefinidos + temporales = hombres + mujeres


def test_rechaza_otro_fichero():
    with pytest.raises(ValueError):
        fuentes.parsear_contratos_nivel("<html>no encontrado</html>", "2026-04-01")
    # el de demandantes por nivel formativo no es este fichero
    with pytest.raises(ValueError):
        fuentes.parsear_contratos_nivel('"Nivel Formativo Agrupación OBS-1";"Dem. Parados Hombres"\n"x";"1"', "2026-04-01")
