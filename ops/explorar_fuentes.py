#!/usr/bin/env python3
"""
ops/explorar_fuentes.py — Exploración de solo lectura, desde GitHub Actions (el entorno de desarrollo no llega a estas webs):
  1. FUNDAE: títulos de las series del visor (rptSeriesNN) que el pipeline todavía no carga, para ver si hay formación de oferta
     (subvencionada).
  2. SEPE vía datos.gob.es: ficha «Demandantes de empleo por nivel formativo»: enlaces de descarga, columnas y primeras filas
     (nivel territorial y si trae edad).
No escribe datos en el repositorio: todo va al log y al resumen del job.

Uso: python ops/explorar_fuentes.py [--fundae-max-min 12]
"""
import argparse, html as html_mod, http.cookiejar, io, json, os, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "pipeline"))
from catalogo_fuentes import contexto  # noqa: E402
import fundae  # noqa: E402

RESUMEN = os.environ.get("GITHUB_STEP_SUMMARY")


def salida(linea=""):
    print(linea, flush=True)
    if RESUMEN:
        with open(RESUMEN, "a", encoding="utf-8") as f:
            f.write(linea + "\n")


def titulo_serie(nn, ctx):
    """Título (primera celda con texto) del Excel de rptSeriesNN, o motivo por el que no se ha podido leer."""
    import openpyxl
    visor = f"{fundae.BASE}publicaciones/visor?reportPath=rptSeries{nn}"
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()), urllib.request.HTTPSHandler(context=ctx))
    op.addheaders = list(fundae.UA.items())
    with op.open(fundae._url(visor), timeout=90) as r:
        pagina = r.read().decode("utf-8", "replace")
    src = re.findall(r'<iframe[^>]+src="([^"]+)"', pagina, re.I)
    if not src:
        return "(el visor no tiene este informe)"
    rv_url = urllib.parse.urljoin(visor, html_mod.unescape(src[0]))
    with op.open(fundae._url(rv_url), timeout=120) as r:
        rv, final = r.read().decode("utf-8", "replace"), r.geturl()
    time.sleep(2)
    exp = re.findall(r'"ExportUrlBase"\s*:\s*"([^"]+)"', rv)
    if not exp:
        return "(sin URL de exportación)"
    base = urllib.parse.urljoin(final, exp[0].replace("\\u0026", "&"))
    nombre = (re.findall(r"FileName=(\w+)", base) or ["?"])[0]
    with op.open(base + "EXCELOPENXML", timeout=180) as r:
        datos = r.read()
    if datos[:2] != b"PK":
        return f"(la exportación no es un Excel; FileName={nombre})"
    ws = openpyxl.load_workbook(io.BytesIO(datos), read_only=True, data_only=True).worksheets[0]
    titulo = next((str(v) for f in ws.iter_rows(max_row=6, values_only=True) for v in f if v), "")
    return f"[{ws.title}] {titulo[:230]}"


def explorar_fundae(max_min):
    salida("## FUNDAE: series del visor que el pipeline no carga")
    ctx = contexto("www.fundae.es")
    conocidas = set(fundae.SERIES)
    t0 = time.time()
    for n in range(1, 61):
        nn = f"{n:02d}"
        if nn in conocidas:
            continue
        if time.time() - t0 > max_min * 60:
            salida(f"- (se corta a los {max_min} min; última serie probada: {nn})")
            break
        try:
            salida(f"- rptSeries{nn}: {titulo_serie(nn, ctx)}")
        except Exception as e:
            salida(f"- rptSeries{nn}: ERROR {type(e).__name__}: {str(e)[:120]}")
        time.sleep(1)


def explorar_sepe():
    salida("## SEPE: «Demandantes de empleo por nivel formativo» (ficha de datos.gob.es)")
    ident = "ea0041513-demandantes-de-empleo-por-nivel-formativo1"
    url = f"https://datos.gob.es/apidata/catalog/dataset/{ident}.json"
    try:
        ctx = contexto("datos.gob.es")
        with urllib.request.urlopen(urllib.request.Request(url, headers=fundae.UA), timeout=60, context=ctx) as r:
            ficha = json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        salida(f"- ficha no accesible ({type(e).__name__}: {str(e)[:150]})")
        return
    items = (ficha.get("result") or {}).get("items") or []
    if not items:
        salida("- la ficha no trae datos")
        return
    it = items[0]
    titulo = it.get("title")
    if isinstance(titulo, list):
        titulo = next((t.get("_value") for t in titulo if t.get("_lang") == "es"), titulo[0].get("_value"))
    salida(f"- título: {titulo}")
    salida(f"- modificado: {it.get('modified')} · frecuencia: {it.get('accrualPeriodicity')} · cobertura: {it.get('spatial')}")
    dist = it.get("distribution") or []
    enlaces = []
    for d in dist:
        acceso = d.get("accessURL")
        formato = (d.get("format") or {}).get("value") if isinstance(d.get("format"), dict) else d.get("format")
        salida(f"- distribución: {formato} · {acceso}")
        if acceso:
            enlaces.append((formato, acceso))
    for formato, acceso in enlaces[:2]:
        try:
            host = urllib.parse.urlparse(acceso).hostname
            with urllib.request.urlopen(urllib.request.Request(acceso, headers=fundae.UA), timeout=120, context=contexto(host)) as r:
                datos = r.read()
            salida(f"- descargado {acceso} ({len(datos)} bytes)")
            if datos[:2] == b"PK":  # xlsx
                import openpyxl
                ws = openpyxl.load_workbook(io.BytesIO(datos), read_only=True, data_only=True).worksheets[0]
                for f in ws.iter_rows(max_row=8, values_only=True):
                    salida("    " + " | ".join("" if v is None else str(v)[:40] for v in f[:14]))
            elif datos[:4] == b"\xd0\xcf\x11\xe0":  # xls antiguo
                import xlrd
                hoja = xlrd.open_workbook(file_contents=datos).sheet_by_index(0)
                for i in range(min(8, hoja.nrows)):
                    salida("    " + " | ".join(str(c)[:40] for c in hoja.row_values(i)[:14]))
            else:
                for linea in datos.decode("latin-1", "replace").splitlines()[:6]:
                    salida("    " + linea[:300])
        except Exception as e:
            salida(f"- {acceso}: ERROR {type(e).__name__}: {str(e)[:150]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fundae-max-min", type=int, default=12)
    a = ap.parse_args()
    for f in (lambda: explorar_sepe(), lambda: explorar_fundae(a.fundae_max_min)):
        try:
            f()
        except Exception as e:
            salida(f"ERROR general: {type(e).__name__}: {e}")
        salida()
    return 0


if __name__ == "__main__":
    sys.exit(main())
