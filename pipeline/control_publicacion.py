#!/usr/bin/env python3
"""
pipeline/control_publicacion.py — Control de calidad ANTES de publicar los datos de la app (rama datos-modelo).

Si algo falla, el workflow no publica: la app sigue con la última carga buena y se abre la issue de incidencias.
Comprueba, con datos/publicar/modelo/metadatos.json (publicacion.py) y el de la carga publicada ahora
(datos/qa/metadatos_previos.json, sacado de la rama datos-modelo):
  1. Están todas las tablas que lee la app (lista TABLAS de comun/datos.py) y ninguna está vacía.
  2. No desaparece ninguna tabla que estaba publicada.
  3. Ninguna tabla pierde más del 50 % de sus filas frente a la carga publicada (un fichero cortado o un cambio de formato).
Salida: datos/qa/control_publicacion.md · código 1 si no se debe publicar.
Uso:    python pipeline/control_publicacion.py [--caida-max 0.5]
"""
import argparse, ast, json, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
NUEVO = RAIZ / "datos" / "publicar" / "modelo" / "metadatos.json"
PREVIO = RAIZ / "datos" / "qa" / "metadatos_previos.json"
SALIDA = RAIZ / "datos" / "qa" / "control_publicacion.md"
APP = RAIZ / "comun" / "datos.py"


def tablas_app(ruta=APP):
    """Lista TABLAS de la app, leída del código sin importarlo (así no hace falta instalar Streamlit)."""
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign) and any(getattr(t, "id", None) == "TABLAS" for t in nodo.targets):
            return list(eval(compile(ast.Expression(nodo.value), str(ruta), "eval"), {"__builtins__": {}}))
    raise ValueError(f"no se encuentra TABLAS en {ruta}")


def filas(meta):
    return {k: v.get("filas") for k, v in (meta or {}).get("ficheros", {}).items()}


def revisar(nuevo, previo, requeridas, caida_max=0.5):
    """Devuelve la lista de problemas (vacía = se puede publicar)."""
    n, p = filas(nuevo), filas(previo)
    problemas = []
    for t in requeridas:
        if t not in n:
            problemas.append(f"`{t}`: falta (la app la necesita)")
        elif not n[t]:
            problemas.append(f"`{t}`: sin filas")
    for t, antes in sorted(p.items()):
        if t in requeridas and not n.get(t):
            continue  # ya avisada arriba (falta o sin filas)
        if t not in n:
            problemas.append(f"`{t}`: estaba publicada y ha desaparecido")
        elif antes and n[t] is not None and n[t] < antes * (1 - caida_max):
            problemas.append(f"`{t}`: pasa de {antes:,} a {n[t]:,} filas (cae más de un {caida_max:.0%})".replace(",", "."))
    return problemas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--caida-max", type=float, default=0.5)
    a = ap.parse_args()
    if not NUEVO.exists():
        problemas = [f"no existe {NUEVO.relative_to(RAIZ)} (¿falló publicacion.py?)"]
        previo = None
    else:
        previo = json.loads(PREVIO.read_text(encoding="utf-8")) if PREVIO.exists() else None
        problemas = revisar(json.loads(NUEVO.read_text(encoding="utf-8")), previo, tablas_app(), a.caida_max)
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    if problemas:
        texto = ["### No se han publicado los datos de hoy: no superan el control de calidad", "",
                 *[f"- {x}" for x in problemas], "",
                 "La app sigue mostrando la última carga buena."]
    else:
        texto = ["Control de publicación superado" + ("" if previo else " (sin carga previa con la que comparar)")]
    SALIDA.write_text("\n".join(texto) + "\n", encoding="utf-8")
    print("\n".join(texto))
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
