"""mart_sectores_empleo: afiliados medios por sección CNAE y año completo, con la variación frente al año anterior."""
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parents[2]


def _filas(modelo):
    con = duckdb.connect()
    con.execute("CREATE TABLE fact_ss_afiliacion (fecha DATE, territorio_id VARCHAR, consulta VARCHAR, regimen VARCHAR, seccion_cnae VARCHAR, afiliados DOUBLE)")
    for f, t, c, r, s, v in modelo:
        con.execute("INSERT INTO fact_ss_afiliacion VALUES (?, ?, ?, ?, ?, ?)", [f, t, c, r, s, v])
    con.execute((RAIZ / "pipeline" / "marts_sectores.sql").read_text(encoding="utf-8"))
    return con.execute("SELECT anyo, seccion_cnae, afiliados, variacion, variacion_pct FROM mart_sectores_empleo ORDER BY 1, 2").fetchall()


def _anyo(a, seccion, v, territorio="N00", consulta="afil_medios_prov_cnae09_regimen", regimen="Total Regimenes(RG+RETA)", meses=12):
    return [(f"{a}-{m:02d}-01", territorio, consulta, regimen, seccion, v) for m in range(1, meses + 1)]


def test_media_anual_y_variacion():
    filas = _filas(_anyo(2024, "A", 100.0) + _anyo(2025, "A", 110.0))
    assert filas[0] == (2024, "A", 100.0, None, None)
    assert filas[1][:4] == (2025, "A", 110.0, 10.0) and abs(filas[1][4] - 10.0) < 1e-9


def test_un_año_incompleto_no_se_publica_ni_sirve_de_base():
    filas = _filas(_anyo(2024, "A", 100.0, meses=6) + _anyo(2025, "A", 110.0))
    assert filas == [(2025, "A", 110.0, None, None)]  # 2024 con 6 meses no cuenta: sin base, sin variación


def test_solo_total_españa_total_regimenes_y_cnae_2009():
    ruido = (_anyo(2025, "A", 5.0, territorio="C01") + _anyo(2025, "A", 7.0, regimen="REGIMEN GENERAL")
             + _anyo(2025, "A", 9.0, consulta="afil_medios_ccaa_cnae25_regimen"))
    assert _filas(_anyo(2025, "A", 110.0) + ruido) == [(2025, "A", 110.0, None, None)]
