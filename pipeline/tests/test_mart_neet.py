"""mart_neet: la tabla 62285 trae la CCAA solo en el nombre de la serie; todas deben resolverse a dim_territorio."""
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parents[2]
MUESTRA = RAIZ / "resultados" / "dev_modelo"


def test_neet_resuelve_todas_las_comunidades():
    con = duckdb.connect()
    con.execute(f"CREATE VIEW fact_ine AS SELECT * FROM read_parquet('{MUESTRA / 'fact_ine.parquet'}')")
    con.execute(f"CREATE TABLE dim_territorio AS SELECT * FROM read_parquet('{MUESTRA / 'dim_territorio.parquet'}')")
    con.execute((RAIZ / "pipeline" / "marts.sql").read_text(encoding="utf-8"))
    sin_territorio = con.execute("SELECT count(*) FROM mart_neet WHERE territorio_id IS NULL").fetchone()[0]
    ccaa = con.execute("SELECT count(DISTINCT territorio_id) FROM mart_neet WHERE desglose = 'Comunidad autónoma'").fetchone()[0]
    assert sin_territorio == 0
    assert ccaa == 20  # 19 comunidades y ciudades autónomas + total nacional
