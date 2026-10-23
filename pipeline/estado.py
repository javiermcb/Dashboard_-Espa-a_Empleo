"""
pipeline/estado.py — Registro de la última carga buena de cada tabla (datos/estado_cargas.json).

Lo usan ine.py y fuentes.py: cuando una tabla se carga bien se anota la fecha; cuando falla, se reutiliza
la última versión buena (que GitHub Actions conserva en caché entre ejecuciones) y se informa de esa fecha.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

RUTA = Path(__file__).resolve().parent.parent / "datos" / "estado_cargas.json"


def leer():
    try:
        return json.loads(RUTA.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def marcar_ok(claves):
    estado = leer()
    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    for c in claves:
        estado[c] = ahora
    RUTA.parent.mkdir(parents=True, exist_ok=True)
    RUTA.write_text(json.dumps(estado, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")


def ultima_ok(clave):
    return leer().get(clave, "fecha desconocida")
