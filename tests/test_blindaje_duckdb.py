"""La conexión de la app solo lee la carpeta de los datos y no se puede reabrir."""
import duckdb
import pandas as pd
import pytest

from comun import datos


def _conexion_blindada(tmp_path):
    p = tmp_path / "t.parquet"
    pd.DataFrame({"a": [1, 2, 3]}).to_parquet(p)
    con = duckdb.connect()
    con.execute(f"CREATE VIEW t AS SELECT * FROM read_parquet('{p.as_posix()}')")
    datos._blindar(con, {str(tmp_path)})
    return con


def test_sigue_leyendo_las_vistas(tmp_path):
    assert _conexion_blindada(tmp_path).execute("SELECT sum(a) FROM t").fetchone()[0] == 6


def test_no_lee_otros_ficheros(tmp_path):
    con = _conexion_blindada(tmp_path)
    with pytest.raises(duckdb.Error):
        con.execute("SELECT * FROM read_csv('/etc/passwd')").fetchall()


def test_no_se_puede_reabrir_el_acceso(tmp_path):
    con = _conexion_blindada(tmp_path)
    with pytest.raises(duckdb.Error):
        con.execute("SET enable_external_access = true")
