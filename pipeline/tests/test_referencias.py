"""Cifras oficiales de referencia: el fichero es válido, la muestra cuadra y cada tipo de discrepancia se detecta."""
import csv
import shutil
from pathlib import Path

import duckdb

import referencias

MUESTRA = Path(__file__).resolve().parents[2] / "resultados" / "dev_modelo"


def test_el_fichero_de_referencias_es_valido():
    refs = referencias.cargar()
    assert len(refs) >= 20
    assert [r["id"] for r in refs] == sorted(set(r["id"] for r in refs), key=[r["id"] for r in refs].index)  # ids únicos
    assert {r["informe"] for r in refs} == {"Dashboard 1", "Dashboard 2", "Dashboard 3"}  # hay referencias de los tres informes
    for r in refs:
        assert set(referencias.CAMPOS) <= set(r), r["id"]
        assert r["url"].startswith("https://") and r["fuente"] and r["comprobado"], r["id"]
        assert float(r["valor"]) > 0 and float(r["tolerancia"]) >= 0, r["id"]
        assert r["sql"].lstrip().upper().startswith("SELECT"), r["id"]
        assert r["en_muestra"] in ("sí", "no"), r["id"]


def test_la_muestra_cuadra_con_las_cifras_oficiales():
    """Solo las referencias marcadas en_muestra=sí: de las demás la muestra no trae la tabla completa."""
    en_muestra = {r["id"] for r in referencias.cargar() if r["en_muestra"] == "sí"}
    assert len(en_muestra) >= 14
    resultado = {r["id"]: r for r in referencias.comparar(MUESTRA) if r["id"] in en_muestra}
    assert {i: r["estado"] for i, r in resultado.items() if r["estado"] != "ok"} == {}


def _copia(tmp_path):
    shutil.copytree(MUESTRA, tmp_path / "m")
    return tmp_path / "m"


def test_se_detecta_una_cifra_que_no_cuadra(tmp_path):
    carpeta = _copia(tmp_path)
    p = (carpeta / "marts" / "mart_neet.parquet").as_posix()
    tmp = (carpeta / "tmp.parquet").as_posix()
    duckdb.sql(f"COPY (SELECT * REPLACE (CASE WHEN anyo = 2025 THEN 19.0 ELSE porcentaje END AS porcentaje) FROM '{p}') TO '{tmp}' (FORMAT PARQUET)")
    Path(tmp).replace(p)
    avisos = referencias.revisar(carpeta)
    assert any(a.startswith("D1-01") and "oficial 11.50" in a and "modelo 19.00" in a for a in avisos), avisos


def test_un_dato_que_falta_se_avisa(tmp_path):
    avisos = referencias.revisar(tmp_path)  # carpeta sin tablas: no hay ningún dato
    assert len(avisos) == len(referencias.cargar()) and all("no tiene este dato" in a for a in avisos)


def test_una_consulta_rota_se_avisa_y_no_tumba_la_carga(tmp_path):
    ruta = tmp_path / "r.csv"
    with open(ruta, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(referencias.CAMPOS)
        w.writerow(["X-01", "Dashboard 1", "consulta rota", "SELECT max(columna_que_no_existe) FROM mart_neet", 1, 0, "f", "https://x", "2026-10-29", "no"])
    avisos = referencias.revisar(MUESTRA, ruta)
    assert len(avisos) == 1 and "la consulta falla" in avisos[0]
