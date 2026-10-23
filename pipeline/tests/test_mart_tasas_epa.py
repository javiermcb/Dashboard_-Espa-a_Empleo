"""mart_tasas_epa: incluye actividad, empleo y paro, por CCAA y grupos de edad jóvenes (los usa el Dashboard 2)."""
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parents[2]
MUESTRA = RAIZ / "resultados" / "dev_modelo"


def test_tasas_jovenes_completas():
    con = duckdb.connect()
    con.execute(f"CREATE VIEW fact_ine AS SELECT * FROM read_parquet('{MUESTRA / 'fact_ine.parquet'}')")
    con.execute(f"CREATE TABLE dim_territorio AS SELECT * FROM read_parquet('{MUESTRA / 'dim_territorio.parquet'}')")
    con.execute((RAIZ / "pipeline" / "marts.sql").read_text(encoding="utf-8"))
    filas = con.execute("""SELECT indicador, count(DISTINCT territorio_id) FROM mart_tasas_epa
                           WHERE edad = 'Menores de 25 años' AND sexo = 'Ambos sexos' GROUP BY 1""").fetchall()
    assert dict(filas) == {"Tasa de actividad": 20, "Tasa de empleo": 20, "Tasa de paro": 20}
