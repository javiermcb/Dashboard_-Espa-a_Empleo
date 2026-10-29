"""Coherencia interna de las cifras: la muestra del modelo pasa, y cada tipo de incoherencia se detecta."""
import shutil
from pathlib import Path

import duckdb
import pytest

import coherencia

MUESTRA = Path(__file__).resolve().parents[2] / "resultados" / "dev_modelo"


def _copia(tmp_path):
    shutil.copytree(MUESTRA, tmp_path / "m")
    return tmp_path / "m"


def _cambiar(carpeta, rel, set_sql, donde="true"):
    """Reescribe un parquet de la copia con `UPDATE`-equivalente: set_sql es una lista de «columna = expresión»."""
    p = carpeta / f"{rel}.parquet"
    cols = [r[0] for r in duckdb.sql(f"DESCRIBE SELECT * FROM '{p.as_posix()}'").fetchall()]
    sets = dict(x.split(" = ", 1) for x in set_sql)
    sel = ", ".join(f"CASE WHEN {donde} THEN {sets[c]} ELSE {c} END AS {c}" if c in sets else c for c in cols)
    tmp = carpeta / "tmp.parquet"
    duckdb.sql(f"COPY (SELECT {sel} FROM '{p.as_posix()}') TO '{tmp.as_posix()}' (FORMAT PARQUET)")
    tmp.replace(p)


def test_la_muestra_es_coherente():
    assert coherencia.revisar_modelo(MUESTRA) == []


def test_una_carpeta_sin_tablas_no_da_problemas(tmp_path):
    assert coherencia.revisar_modelo(tmp_path) == []


@pytest.mark.parametrize("rel, cambio, donde, texto", [
    ("marts/mart_tasas_epa", ["tasa = 140"], "indicador = 'Tasa de paro'", "fuera de 0-100"),
    ("marts/mart_tasas_epa", ["tasa = tasa + 5"], "indicador = 'Tasa de empleo'", "no cuadra con actividad y paro"),
    ("marts/mart_neet", ["porcentaje = -1"], "true", "mart_neet"),
    ("fact_sepe_demandantes_nivel", ["total = total + 1"], "true", "españoles + extranjeros"),
    ("marts/mart_oportunidad_ccaa", ["demandantes_menores_25 = demandantes * 2"], "true", "mart_oportunidad_ccaa"),
    ("fact_sepe_demandantes_nivel", ["nivel = 'Total'"], "nivel = 'Universitario'", "filas «Total»"),
    ("fact_fundae", ["valor = valor * 3"], "serie = '01' AND categoria = 'Total' AND medida = 'Participantes'", "serie 01"),
])
def test_se_detecta_cada_incoherencia(tmp_path, rel, cambio, donde, texto):
    carpeta = _copia(tmp_path)
    if not (carpeta / f"{rel}.parquet").exists():
        pytest.skip(f"la muestra no tiene {rel}")
    _cambiar(carpeta, rel, cambio, donde)
    problemas = coherencia.revisar_modelo(carpeta)
    assert any(texto in p for p in problemas), problemas
