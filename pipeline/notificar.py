#!/usr/bin/env python3
"""
pipeline/notificar.py — Decide si hay que avisar y redacta el mensaje (lo publica el workflow como issue de GitHub).

Compara las alertas de esta carga (datos/qa/alertas.csv) con las de la carga anterior (resultados/pipeline/alertas.csv,
todavía sin sobrescribir cuando se ejecuta este script) para avisar solo de lo NUEVO:
  - fallos de carga (tipo 'carga'): tablas no actualizadas, sin datos o con un control de calidad no superado
  - datos nuevos (nivel 'novedad')
  - avisos de indicadores que no estaban en la carga anterior (misma regla y territorio)
Salida (solo si hay algo que avisar):
  datos/qa/notificacion_fallos.md    -> issue con etiqueta 'pipeline-fallo'
  datos/qa/notificacion_alertas.md   -> issue con etiqueta 'alertas'
"""
import csv, os, sys
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ACTUAL = RAIZ / "datos" / "qa" / "alertas.csv"
PREVIA = RAIZ / "resultados" / "pipeline" / "alertas.csv"
SALIDA = RAIZ / "datos" / "qa"


def leer(p):
    if not p.exists():
        return []
    with open(p, encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def main():
    actual, previa = leer(ACTUAL), leer(PREVIA)
    if not actual:
        print("Sin alertas en esta carga"); return 0
    clave = lambda a: (a["tipo"], a["indicador"], a["territorio"])
    avisos_previos = {clave(a) for a in previa if a["nivel"] == "aviso"}
    tipo_fallo = lambda a: (a["indicador"], a["mensaje"].split(":")[0])  # "No actualizada…", "Sin datos…", "Control de calidad"
    fallos_previos = {tipo_fallo(a) for a in previa if a["tipo"] == "carga"}

    fallos = [a for a in actual if a["tipo"] == "carga"]
    fallos_nuevos = [a for a in fallos if tipo_fallo(a) not in fallos_previos]
    novedades = [a for a in actual if a["nivel"] == "novedad"]
    avisos_nuevos = [a for a in actual if a["nivel"] == "aviso" and a["tipo"] != "carga" and clave(a) not in avisos_previos]

    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    ejecucion = ""
    if os.environ.get("GITHUB_RUN_ID"):
        ejecucion = (f"\n\nEjecución: {os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/"
                     f"{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/{os.environ['GITHUB_RUN_ID']}")
    for f in ("notificacion_fallos.md", "notificacion_alertas.md"):
        (SALIDA / f).unlink(missing_ok=True)

    if fallos_nuevos:
        lineas = [f"### Incidencias de carga · {ahora}", ""]
        lineas += [f"- **{a['indicador']}** · {a['mensaje']}" for a in fallos_nuevos]
        if len(fallos) > len(fallos_nuevos):
            lineas += ["", f"_Además siguen abiertas {len(fallos) - len(fallos_nuevos)} incidencias ya avisadas._"]
        lineas += ["", "Las tablas marcadas como «No actualizada» se publican con su última versión buena."]
        (SALIDA / "notificacion_fallos.md").write_text("\n".join(lineas) + ejecucion, encoding="utf-8")

    if novedades or avisos_nuevos:
        lineas = [f"### Alertas RRHH 360 · {ahora}", ""]
        if avisos_nuevos:
            lineas += ["**Avisos nuevos**", ""] + [f"- **{a['indicador']}** · {a['mensaje']}" for a in avisos_nuevos] + [""]
        if novedades:
            lineas += ["**Datos nuevos**", ""] + [f"- `{a['indicador']}` · {a['mensaje']}" for a in novedades] + [""]
        lineas += ["Detalle completo: `resultados/pipeline/alertas.md` (rama `calidad`) · tabla `modelo/alertas.csv` en el repositorio público."]
        (SALIDA / "notificacion_alertas.md").write_text("\n".join(lineas) + ejecucion, encoding="utf-8")

    print(f"fallos nuevos: {len(fallos_nuevos)} · avisos nuevos: {len(avisos_nuevos)} · datos nuevos: {len(novedades)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
