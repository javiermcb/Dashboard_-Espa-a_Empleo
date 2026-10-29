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


def test_un_mes_que_falla_no_borra_los_ya_guardados(tmp_path, monkeypatch):
    import urllib.error
    monkeypatch.setattr(fuentes, "NORM", tmp_path)
    previo = fuentes.parsear_contratos_nivel(CSV, "2026-04-01")
    cab = ["fecha", "nivel", "hombres", "mujeres", "indefinidos", "temporales", "total"]
    fuentes.escribir("sepe_contratos_nivel", cab, previo)  # carga anterior: abril

    def descargar(url, *a, **k):  # ahora solo responde mayo; abril da 404
        if "202605" in url:
            return CSV.encode("utf-8")
        raise urllib.error.HTTPError(url, 404, "no encontrado", {}, None)
    monkeypatch.setattr(fuentes, "descargar", descargar)
    res = fuentes.sepe_contratos_nivel(desde=2026)
    with open(tmp_path / "sepe_contratos_nivel.csv", encoding="utf-8") as fh:
        meses = sorted({l.split(",")[0] for l in fh.read().splitlines()[1:]})
    assert meses == ["2026-04-01", "2026-05-01"]  # abril se conserva y mayo se añade
    assert res[0][3:5] == ["2026-04", "2026-05"]
    assert "sin fichero" in res[0][5] and "(HTTP 404)" in res[0][5]  # se anota qué meses recientes fallan y por qué


def test_la_fila_total_no_es_un_nivel_en_contratos():
    h = sum(f[2] for f in fuentes.parsear_contratos_nivel(CSV, "2026-04-01"))
    m = sum(f[3] for f in fuentes.parsear_contratos_nivel(CSV, "2026-04-01"))
    con_total = CSV + f'"Total";;"{h}";"{m}";"1";"1";"1";"1";"1";"1";"1"\n'
    filas = fuentes.parsear_contratos_nivel(con_total, "2026-04-01")
    assert len(filas) == 7 and not any(f[1].lower().startswith("total") for f in filas)
    with pytest.raises(ValueError, match="suman"):
        fuentes.parsear_contratos_nivel(CSV + '"Total";;"1";"2";"1";"1";"1";"1";"1";"1";"1"\n', "2026-04-01")


def test_las_filas_total_de_cargas_viejas_no_se_conservan(tmp_path, monkeypatch):
    import urllib.error
    monkeypatch.setattr(fuentes, "NORM", tmp_path)
    cab = ["fecha", "nivel", "hombres", "mujeres", "indefinidos", "temporales", "total"]
    viejo = fuentes.parsear_contratos_nivel(CSV, "2026-03-01") + [["2026-03-01", "Total", 1, 1, 1, 1, 2]]
    fuentes.escribir("sepe_contratos_nivel", cab, viejo)  # una carga anterior que guardó la fila «Total»

    def descargar(url, *a, **k):
        if "202605" in url:
            return CSV.encode("utf-8")
        raise urllib.error.HTTPError(url, 404, "no encontrado", {}, None)
    monkeypatch.setattr(fuentes, "descargar", descargar)
    fuentes.sepe_contratos_nivel(desde=2026)
    with open(tmp_path / "sepe_contratos_nivel.csv", encoding="utf-8") as fh:
        niveles = {l.split(",")[1] for l in fh.read().splitlines()[1:]}
    assert not any(n.lower().startswith("total") for n in niveles)
