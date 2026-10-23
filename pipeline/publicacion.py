#!/usr/bin/env python3
"""
pipeline/publicacion.py — Prepara la carpeta que se publica en el repositorio público.

Entrada:  datos/modelo/*.parquet|csv (modelo.py), pipeline/config/diccionario.csv, datos/qa/ine_carga.csv
Salida:   datos/publicar/
            README.md          qué hay, cómo conectarse desde Power BI y fecha de actualización
            modelo/            los Parquet y CSV del modelo + diccionario.csv + tablas_ine.csv
            modelo/metadatos.json  fecha de generación y, por tabla, filas y último periodo
Uso:      python pipeline/publicacion.py [--repo usuario/repositorio]
"""
import argparse, csv, json, shutil, sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
MODELO, PUB = RAIZ / "datos" / "modelo", RAIZ / "datos" / "publicar"
CFG = RAIZ / "pipeline" / "config"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="USUARIO/REPOSITORIO")
    a = ap.parse_args()

    if PUB.exists():
        shutil.rmtree(PUB)
    (PUB / "modelo").mkdir(parents=True)
    for f in MODELO.iterdir():
        (shutil.copytree if f.is_dir() else shutil.copy2)(f, PUB / "modelo" / f.name)
    shutil.copy2(CFG / "diccionario.csv", PUB / "modelo" / "diccionario.csv")
    shutil.copy2(CFG / "tablas_ine.csv", PUB / "modelo" / "tablas_ine.csv")
    alertas = RAIZ / "datos" / "qa" / "alertas.csv"
    if alertas.exists():  # alertas de esta carga (pipeline/alertas.py), para mostrarlas en Power BI
        shutil.copy2(alertas, PUB / "modelo" / "alertas.csv")

    con = duckdb.connect()
    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    tablas = {}
    for p in sorted(MODELO.glob("*.parquet")) + sorted(MODELO.glob("marts/*.parquet")):
        n = con.execute(f"SELECT count(*) FROM '{p}'").fetchone()[0]
        tablas[str(p.relative_to(MODELO).with_suffix(""))] = {"filas": n, "bytes_parquet": p.stat().st_size}
    por_tabla = con.execute(f"""
        SELECT d.tabla_id, d.punto_nombre, d.tema, count(f.valor) AS datos, max(f.fecha) AS ultimo_periodo
        FROM '{MODELO / "dim_tabla.parquet"}' d LEFT JOIN '{MODELO / "fact_ine.parquet"}' f USING (tabla_id)
        GROUP BY ALL ORDER BY d.punto_nombre, d.tabla_id""").fetchall()
    # tablas que en esta carga no se han actualizado (se publica su última versión buena) o no tienen datos
    incidencias = []
    for fichero, col in (("ine_carga.csv", "tabla_id"), ("fuentes_carga.csv", "tabla")):
        q = RAIZ / "datos" / "qa" / fichero
        if q.exists():
            with open(q, encoding="utf-8") as fh:
                for r in csv.DictReader(fh, delimiter=";"):
                    if r["estado"] in ("ANTERIOR", "ERROR"):
                        incidencias.append({"tabla": r[col], "estado": r["estado"],
                                            "detalle": (r.get("error") or r.get("detalle") or "")[:300]})
    meta = {"generado": ahora, "ficheros": tablas, "incidencias_carga": incidencias,
            "tablas_ine": [{"tabla_id": t, "punto": p, "tema": te, "datos": n, "ultimo_periodo": str(u) if u else None}
                           for t, p, te, n, u in por_tabla]}
    (PUB / "modelo" / "metadatos.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")

    miles = lambda n: f"{n:,}".replace(",", ".")  # 380537 -> 380.537
    filas = "\n".join(f"| {p} | {t} | {te} | {miles(n)} | {u or ''} |" for t, p, te, n, u in por_tabla)
    ficheros = "\n".join(f"| `modelo/{k}.parquet` | {miles(v['filas'])} | {v['bytes_parquet'] / 1e6:.1f} MB |"
                         for k, v in tablas.items())
    base = f"https://raw.githubusercontent.com/{a.repo}/main/modelo/"
    aviso = ""
    if incidencias:
        aviso = "\n> **Tablas no actualizadas en esta carga** (se mantiene su última versión buena, o no hay datos):\n" + "\n".join(
            f"> - `{i['tabla']}` · {i['estado']} · {i['detalle']}" for i in incidencias) + "\n"
    (PUB / "README.md").write_text(f"""# Datos RRHH 360

Modelo de datos generado automáticamente a partir de **estadísticas oficiales públicas** (INE; próximamente SEPE,
Seguridad Social y Ministerio de Trabajo). **Última actualización: {ahora}.**
{aviso}
## Ficheros

| Fichero | Filas | Tamaño |
|---|---|---|
{ficheros}

Cada tabla está también en CSV (`;` como separador). `modelo/diccionario.csv` describe todas las columnas y
`modelo/metadatos.json` indica la fecha de generación y el último periodo de cada tabla.

## Conexión desde Power BI

Origen web sin credenciales (Anónimo). Ejemplo en Power Query:

```
Parquet.Document(Binary.Buffer(Web.Contents("https://raw.githubusercontent.com",
    [RelativePath = "{a.repo}/main/modelo/fact_ine.parquet"])))
```

URL directa de cada fichero: `{base}<fichero>`

Relaciones: `fact_ine[tabla_id]` → `dim_tabla`, `fact_ine[territorio_id]` → `dim_territorio`, `fact_ine[fecha]` → `dim_tiempo`.
`fact_ine` mezcla magnitudes distintas: filtra siempre por `tabla_id` y `medida` antes de agregar `valor`.

## Tablas del INE incluidas

| Punto RRHH | Tabla | Tema | Datos | Último periodo |
|---|---|---|---|---|
{filas}

Fuente de los datos: Instituto Nacional de Estadística (INE), API JSON `servicios.ine.es/wstempus`.
""", encoding="utf-8")
    print(f"Publicación preparada en {PUB} ({len(tablas)} tablas)")


if __name__ == "__main__":
    sys.exit(main())
