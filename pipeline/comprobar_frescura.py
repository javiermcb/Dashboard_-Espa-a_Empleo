#!/usr/bin/env python3
"""
pipeline/comprobar_frescura.py — Comprueba que la carga publicada en la rama datos-modelo no es demasiado vieja.

La carga corre de lunes a viernes, así que de un viernes a un lunes pasan ~72 h; por defecto se avisa a partir de 96 h.
Lo ejecuta el workflow mantener_apps_activas.yml (job «frescura»), aparte de las visitas a las apps: si el pipeline deja de
publicar sin fallar (workflow desactivado, cron parado por inactividad), ningún otro aviso salta.
Uso:    python pipeline/comprobar_frescura.py metadatos.json [--max-horas 96]
Salida: código 1 y un texto en stdout si la carga es más vieja que el máximo o no se puede leer la fecha.
"""
import argparse, json, sys
from datetime import datetime, timezone

FORMATO = "%Y-%m-%d %H:%M UTC"  # el que escribe publicacion.py


def edad_horas(generado, ahora=None):
    f = datetime.strptime(generado, FORMATO).replace(tzinfo=timezone.utc)
    return ((ahora or datetime.now(timezone.utc)) - f).total_seconds() / 3600


def revisar(meta, max_horas=96, ahora=None):
    """Devuelve el problema (texto) o None si la carga está al día."""
    generado = (meta or {}).get("generado")
    if not generado:
        return "metadatos.json no trae la fecha de generación"
    try:
        h = edad_horas(generado, ahora)
    except ValueError:
        return f"fecha de generación ilegible: «{generado}»"
    if h > max_horas:
        return f"la carga publicada es del {generado}, hace {h / 24:.1f} días (máximo {max_horas / 24:.0f})"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("metadatos")
    ap.add_argument("--max-horas", type=float, default=96)
    a = ap.parse_args()
    try:
        meta = json.load(open(a.metadatos, encoding="utf-8"))
    except (OSError, ValueError) as e:
        print(f"no se puede leer {a.metadatos}: {e}")
        return 1
    problema = revisar(meta, a.max_horas)
    print(problema or "Datos al día")
    return 1 if problema else 0


if __name__ == "__main__":
    sys.exit(main())
