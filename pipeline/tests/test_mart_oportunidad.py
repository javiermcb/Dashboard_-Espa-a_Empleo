"""mart_oportunidad_ccaa: demandantes (y menores de 25) y contratos del SEPE agregados por comunidad y mes."""
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parents[2]


def _modelo():
    con = duckdb.connect()
    con.execute("""CREATE TABLE fact_sepe_demandantes_municipio AS SELECT * FROM (VALUES
        (DATE '2026-09-01', 'C01', 100.0, 10.0, 5.0), (DATE '2026-09-01', 'C01', 50.0, NULL, 2.0),
        (DATE '2026-09-01', 'C02', 40.0, 4.0, 1.0), (DATE '2026-09-01', NULL, 99.0, 9.0, 9.0))
        t(fecha, ccaa_id, total_dtes_empleo, dtes_empleo_hombre_edad_25, dtes_empleo_mujer_edad_25)""")
    con.execute("""CREATE TABLE fact_sepe_contratos_municipio AS SELECT * FROM (VALUES
        (DATE '2026-09-01', 'C01', 70.0), (DATE '2026-09-01', 'C01', 30.0)) t(fecha, ccaa_id, total_contratos)""")
    con.execute((RAIZ / "pipeline" / "marts_oportunidad.sql").read_text(encoding="utf-8"))
    return con


def test_suma_por_comunidad_y_trata_los_secretos_como_cero():
    d = {r[0]: r[1:] for r in _modelo().execute(
        "SELECT territorio_id, demandantes, demandantes_menores_25, contratos FROM mart_oportunidad_ccaa ORDER BY 1").fetchall()}
    assert d["C01"] == (150.0, 17.0, 100.0)  # el hueco (secreto) de hombres <25 en una fila cuenta como 0
    assert d["C02"] == (40.0, 5.0, None)  # sin contratos en esa comunidad: queda vacío, no 0


def test_ignora_los_municipios_sin_comunidad():
    assert _modelo().execute("SELECT count(*) FROM mart_oportunidad_ccaa WHERE territorio_id IS NULL").fetchone()[0] == 0
