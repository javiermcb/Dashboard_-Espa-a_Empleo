#!/usr/bin/env python3
"""
pipeline/ine.py — Ingesta de tablas del INE (API JSON) a la capa normalizada.

Lee pipeline/config/tablas_ine.csv y, por cada tabla:
  1. BRUTO       datos/raw/ine/<id>.json        respuesta tal cual de DATOS_TABLA/<id>?tip=AM
  2. NORMALIZADO datos/normalizado/ine_valores.csv     una fila por dato (serie, periodo, valor)
                 datos/normalizado/ine_series_dims.csv una fila por serie y variable (Sexo, Provincias...)
  3. QA          datos/qa/ine_carga.csv                estado, series, datos y periodos de cada tabla
Si una tabla falla y existe su última descarga buena (datos/raw/ine/<id>.json, conservada en caché), se reutiliza
y se marca como ANTERIOR, con la fecha de esa carga (datos/estado_cargas.json).

Uso:  python pipeline/ine.py [--tablas 6061 66031] [--nult N]
Solo librería estándar. Una tabla que falla no para las demás.
"""
import argparse, re, csv, json, sys, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

import estado

RAIZ = Path(__file__).resolve().parent.parent
CONFIG = RAIZ / "pipeline" / "config" / "tablas_ine.csv"
DATOS = RAIZ / "datos"
API = "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/{}?tip=AM"
UA = {"User-Agent": "Mozilla/5.0 rrhh360-pipeline/1.0"}


def get_json(url, intentos=3):
    for i in range(intentos):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception:
            if i == intentos - 1:
                raise
            time.sleep(5 * (i + 1))


def fecha_iso(v):
    """El INE da Fecha como texto ISO ('2025-01-01T00:00:00.000+01:00') o como milisegundos."""
    if isinstance(v, (int, float)):
        # son medianoche hora de España (UTC+1/+2): se suman 12 h para no caer en el día anterior al pasar a UTC
        return datetime.fromtimestamp(v / 1000 + 12 * 3600, tz=timezone.utc).date().isoformat()
    return str(v)[:10] if v else ""


def validar(tablas):
    """Error de configuración de tablas_ine.csv, o None si está bien."""
    ids = [r["tabla_id"] for r in tablas]
    repetidas = sorted({i for i in ids if ids.count(i) > 1})
    if repetidas:  # una tabla dos veces duplica sus datos en el modelo
        return f"tablas repetidas {repetidas}"
    malas = [r["tabla_id"] for r in tablas if None in r]  # un ';' dentro de un texto desplaza las columnas
    if malas:
        return f"sobran columnas en {malas} (¿un ';' dentro del tema o la nota?)"
    return None


def periodo(d):
    """(fecha ISO, año, periodo) de un dato del INE."""
    f, anyo, per = fecha_iso(d.get("Fecha")), d.get("Anyo", ""), d.get("T3_Periodo", "")
    if not f and d.get("NombrePeriodo"):
        # tablas con formato de indicador (ODS, p. ej. 59513): solo traen NombrePeriodo ("2025")
        m = re.match(r"\s*(\d{4})", str(d["NombrePeriodo"]))
        if m:
            f, anyo, per = f"{m.group(1)}-01-01", anyo or m.group(1), per or "A"
    return f, anyo, per


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tablas", nargs="+")
    ap.add_argument("--nult", type=int)
    a = ap.parse_args()

    with open(CONFIG, encoding="utf-8") as f:
        tablas = [r for r in csv.DictReader(f, delimiter=";") if not a.tablas or r["tabla_id"] in a.tablas]
    error = validar(tablas)
    if error:
        sys.exit(f"tablas_ine.csv: {error}")
    for d in ("raw/ine", "normalizado", "qa"):
        (DATOS / d).mkdir(parents=True, exist_ok=True)

    fv = open(DATOS / "normalizado" / "ine_valores.csv", "w", newline="", encoding="utf-8")
    fd = open(DATOS / "normalizado" / "ine_series_dims.csv", "w", newline="", encoding="utf-8")
    wv, wd = csv.writer(fv), csv.writer(fd)
    wv.writerow(["tabla_id", "serie_cod", "serie_nombre", "unidad", "escala", "fecha", "anyo", "periodo", "tipo_dato", "valor", "secreto"])
    wd.writerow(["tabla_id", "serie_cod", "variable", "variable_valor_id", "codigo", "nombre"])
    qa, ok = [], []
    for t in tablas:
        tid, t0 = t["tabla_id"], time.time()
        url = API.format(tid) + (f"&nult={a.nult}" if a.nult else "")
        crudo = DATOS / "raw" / "ine" / f"{tid}.json"
        situacion, nota = "OK", ""
        try:
            series = get_json(url)
            if not isinstance(series, list):
                raise ValueError(f"respuesta inesperada: {str(series)[:200]}")
            crudo.write_text(json.dumps(series, ensure_ascii=False), encoding="utf-8")
            ok.append(f"ine:{tid}")
        except Exception as e:
            error = f"{type(e).__name__}: {e}"[:250]
            if crudo.exists():  # última descarga buena, conservada en caché entre ejecuciones
                series = json.loads(crudo.read_text(encoding="utf-8"))
                situacion, nota = "ANTERIOR", f"{error} · se usa la última carga buena ({estado.ultima_ok(f'ine:{tid}')})"
            else:
                qa.append([tid, t["punto"], t["tema"], "ERROR", "", "", "", "", f"{time.time() - t0:.0f}s", error])
                print(f"[{tid}] ERROR {e}")
                time.sleep(1)
                continue
        n, periodos = 0, set()
        for s in series:
            cod = s.get("COD", "")
            for m in s.get("MetaData", []) or []:
                wd.writerow([tid, cod, m.get("T3_Variable", ""), m.get("Id", ""), m.get("Codigo", ""), m.get("Nombre", "")])
            for d in s.get("Data", []) or []:
                f, anyo, per = periodo(d)
                periodos.add(f)
                wv.writerow([tid, cod, s.get("Nombre", "").strip(), s.get("T3_Unidad", ""), (s.get("T3_Escala") or "").strip(),
                             f, anyo, per, d.get("T3_TipoDato", ""), d.get("Valor", ""), d.get("Secreto", "")])
                n += 1
        qa.append([tid, t["punto"], t["tema"], situacion, len(series), n, min(periodos, default=""), max(periodos, default=""),
                   f"{time.time() - t0:.0f}s", nota])
        print(f"[{tid}] {situacion} {len(series)} series, {n} datos, {min(periodos, default='')} – {max(periodos, default='')}")
        time.sleep(1)
    estado.marcar_ok(ok)
    fv.close(); fd.close()
    with open(DATOS / "qa" / "ine_carga.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["tabla_id", "punto", "tema", "estado", "series", "datos", "fecha_min", "fecha_max", "tiempo", "error"])
        w.writerows(qa)
    errores = sum(1 for q in qa if q[3] == "ERROR")
    anteriores = sum(1 for q in qa if q[3] == "ANTERIOR")
    print(f"{len(qa) - errores - anteriores} tablas OK, {anteriores} con la última carga buena, {errores} con error")
    return 1 if errores == len(qa) else 0


if __name__ == "__main__":
    sys.exit(main())
