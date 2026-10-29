"""
pipeline/referencias.py — Comparación de las cifras del modelo con cifras oficiales publicadas.

pipeline/referencias_oficiales.csv (separador «;») lista cada cifra oficial: informe (Dashboard 1/2/3), descripción, una consulta SQL
sobre el modelo que devuelve UN número, el valor oficial, la tolerancia (en las unidades de la cifra), la fuente, su enlace y cuándo se
comprobó. En las consultas, cada fichero parquet del modelo es una tabla con el nombre del fichero (mart_neet, fact_fundae…).

Se ejecuta en el control de publicación (control_publicacion.py) como AVISO que no bloquea: los organismos revisan sus cifras y una
diferencia puede ser legítima, pero conviene verla. Estados: ok · difiere · sin_dato (la consulta no devuelve nada: falta la tabla o el
periodo) · error (la consulta falla). Las pruebas (tests/test_referencias.py) comprueban el fichero y que la muestra no discrepa.
"""
import csv
from pathlib import Path

import duckdb

CSV = Path(__file__).resolve().parent / "referencias_oficiales.csv"
CAMPOS = ["id", "informe", "descripcion", "sql", "valor", "tolerancia", "fuente", "url", "comprobado", "en_muestra"]


def cargar(ruta=CSV):
    with open(ruta, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def _vistas(carpeta):
    con = duckdb.connect()
    for p in sorted(Path(carpeta).rglob("*.parquet")):
        con.execute(f'CREATE OR REPLACE VIEW "{p.stem}" AS SELECT * FROM \'{p.as_posix()}\'')
    return con


def comparar(carpeta, ruta=CSV):
    """[{**referencia, estado, obtenido, diferencia}] para cada referencia."""
    con, out = _vistas(carpeta), []
    for r in cargar(ruta):
        res = dict(r, obtenido=None, diferencia=None)
        try:
            fila = con.execute(r["sql"]).fetchone()
            obtenido = None if fila is None or fila[0] is None else float(fila[0])
        except duckdb.CatalogException:  # la tabla no está en el modelo (las hay opcionales): no hay dato
            obtenido = None
        except Exception as e:  # una consulta rota no debe tumbar la carga
            res.update(estado="error", obtenido=f"{type(e).__name__}: {str(e)[:100]}")
            out.append(res)
            continue
        if obtenido is None:
            res["estado"] = "sin_dato"
        else:
            dif = obtenido - float(r["valor"])
            res.update(obtenido=obtenido, diferencia=dif, estado="ok" if abs(dif) <= float(r["tolerancia"]) else "difiere")
        out.append(res)
    return out


def revisar(carpeta, ruta=CSV):
    """Avisos (lista de textos) para las referencias que no cuadran, faltan o fallan. Vacía = todas cuadran."""
    avisos = []
    for r in comparar(carpeta, ruta):
        base = f"{r['id']} · {r['informe']} · {r['descripcion']}"
        if r["estado"] == "difiere":
            avisos.append(f"{base}: oficial {float(r['valor']):,.2f}, modelo {r['obtenido']:,.2f} "
                          f"(diferencia {r['diferencia']:+,.2f}; tolerancia {float(r['tolerancia']):,.2f}) · {r['fuente']}")
        elif r["estado"] == "sin_dato":
            avisos.append(f"{base}: el modelo no tiene este dato (falta la tabla o el periodo)")
        elif r["estado"] == "error":
            avisos.append(f"{base}: la consulta falla ({r['obtenido']})")
    return avisos
