#!/usr/bin/env python3
"""
catalogo_fuentes.py — Descubre códigos de tabla y URLs de descarga de las fuentes de RRHH.

Salida (carpeta fuentes/):
  accesibilidad.csv        dominio; url; http; error  (qué webs responden desde donde se ejecuta)
  ine_inebase_tablas.csv   tablas INEbase de operaciones que no están en la API Tempus (TIC, discapacidad, EADA...)
  ine_prueba_api.csv       prueba de DATOS_TABLA sobre una muestra de esas tablas
  datosgob_publicadores.csv publicadores de datos.gob.es que interesan (SEPE, Seguridad Social, Trabajo, AEAT)
  datosgob_datasets.csv    datasets y distribuciones (URL de descarga y formato) de esos publicadores
  ficheros_<fuente>.csv    enlaces a ficheros (xlsx, csv, px, pdf...) encontrados en las webs de MITES, SEPE, SS y AEAT

Solo librería estándar. Cada bloque es independiente: si uno falla, los demás siguen.
"""
import csv, json, os, re, ssl, sys, time, urllib.parse, urllib.request
from collections import deque
from pathlib import Path

OUT = Path("fuentes")
UA = {"User-Agent": "Mozilla/5.0 catalogo-fuentes/1.0"}
PAUSA = 0.5

# --- INEbase: categorías de las que se parte para encontrar operaciones y tablas
INEBASE_SEMILLAS = {
    # operaciones de RRHH que no están en la API Tempus (direcciones comprobadas por búsqueda web)
    "discapacidad_empleo":  "https://www.ine.es/dyngs/INEbase/es/operacion.htm?c=Estadistica_C&cid=1254736055502&menu=resultados&idp=1254735573175",
    "discapacidad_salario": "https://www.ine.es/dyngs/INEbase/es/operacion.htm?c=Estadistica_C&cid=1254736176911&menu=resultados&idp=1254735976596",
    "discapacidad_salario_tablas": "https://www.ine.es/dynt3/inebase/es/index.htm?padre=1422&capsel=1426",
    "epa_modulos":          "https://www.ine.es/dyngs/INEbase/es/operacion.htm?c=Estadistica_C&cid=1254736176918&menu=resultados&secc=1254736195124&idp=1254735976595",
    "eada":                 "https://www.ine.es/dyngs/INEbase/es/operacion.htm?c=Estadistica_C&cid=1254736176759&menu=resultados&idp=1254735573113",
    "eilu":                 "https://www.ine.es/dyngs/INEbase/es/operacion.htm?c=Estadistica_C&cid=1254736176991&menu=resultados&idp=1254735976597",
    "etefil":               "https://www.ine.es/dyngs/INEbase/es/operacion.htm?c=Estadistica_C&cid=1254736056996&menu=resultados&idp=1254735573113",
    "salud_europea":        "https://www.ine.es/dyngs/INEbase/es/operacion.htm?c=Estadistica_C&cid=1254736176784&menu=resultados&idp=1254735573175",
    "tic_empresas":         "https://www.ine.es/dyngs/INEbase/es/operacion.htm?c=Estadistica_C&cid=1254736176743&menu=resultados&idp=1254735576799",
}
INEBASE_MAX_PAGINAS = 350  # ~6 s por página en GitHub Actions: cabe en el límite del workflow
# en las páginas de categoría solo se entra en operaciones cuyo nombre encaje con esto
INEBASE_OPERACIONES = re.compile(
    r"discapacidad|aprendizaje|inserci[óo]n laboral|transici[óo]n educativ|empleo del tiempo|tiempo de trabajo|"
    r"poblaci[óo]n activa|tasas de actividad|TIC y (del )?comercio|europea de salud|salari|coste laboral|"
    r"precios del trabajo|recursos humanos en ciencia|movilidad laboral|flujos de la poblaci", re.I)

# --- Webs con ficheros
WEBS = {
    "mites": {
        "semillas": ["https://www.mites.gob.es/es/estadisticas/index.htm",
                     "https://www.mites.gob.es/es/estadisticas/novedades/todas/index.htm",
                     "https://www.mites.gob.es/es/estadisticas/anuarios/2025/index.htm"],
        "dentro": re.compile(r"^https?://(www\.)?mites\.gob\.es/(es/)?estadisticas/", re.I),
        "max": 900,
    },
    "sepe": {
        "semillas": ["https://sede.sepe.gob.es/portalSede/datos-abiertos/catalogo-de-datos-del-SEPE.html",
                     "https://www.sepe.es/HomeSepe/que-es-el-sepe/estadisticas.html"],
        "dentro": re.compile(r"^https?://(sede\.sepe\.gob\.es/portalSede/datos-abiertos|www\.sepe\.es/HomeSepe/(es/)?que-es-el-sepe/estadisticas)", re.I),
        "max": 300,
    },
    "seguridad_social": {
        "semillas": ["https://www.seg-social.es/wps/portal/wss/internet/EstadisticasPresupuestosEstudios/Estadisticas"],
        "dentro": re.compile(r"^https?://(www\.)?seg-social\.es/wps/portal/wss/internet/EstadisticasPresupuestosEstudios/Estadisticas", re.I),
        "max": 400,
    },
    "aeat": {
        "semillas": ["https://sede.agenciatributaria.gob.es/Sede/datosabiertos/catalogo/hacienda/Mercado_de_Trabajo_y_Pensiones_en_las_Fuentes_Tributarias.shtml",
                     "https://sede.agenciatributaria.gob.es/Sede/estadisticas/estadisticas-impuesto/mercado-trabajo-pensiones-fuentes-tributarias.html"],
        "dentro": re.compile(r"^https?://sede\.agenciatributaria\.gob\.es/(Sede/(datosabiertos|estadisticas)|AEAT/Contenidos_Comunes/La_Agencia_Tributaria/Estadisticas/Publicaciones/sites/mercado)", re.I),
        "max": 300,
    },
}
EXT_FICHERO = re.compile(r"\.(xlsx?|csv|px|json|zip|ods|pdf)(\?|$)", re.I)

# --- datos.gob.es
DATOSGOB = "https://datos.gob.es/apidata/"
PUBLICADORES = re.compile(r"Servicio P[úu]blico de Empleo|SEPE|Seguridad Social|Inclusi[óo]n|Ministerio de Trabajo|Agencia (Estatal de Administraci[óo]n )?Tributaria", re.I)


_CTX = {}


RAICES_FIJADAS = Path(__file__).resolve().parent / "raices_fijadas.txt"


def raices_fijadas():
    """Huellas SHA-256 (hex) de raíces que se aceptan aunque el sistema no las traiga. Una por línea; «#» comenta."""
    try:
        return {l.split("#")[0].strip().lower().replace(":", "") for l in RAICES_FIJADAS.read_text().splitlines() if l.split("#")[0].strip()}
    except OSError:
        return set()


def huellas(cert):
    """(SHA-256, SHA-1) en hexadecimal del certificado: sirven para compararlas con las que publica la entidad."""
    import hashlib
    from cryptography.hazmat.primitives.serialization import Encoding
    der = cert.public_bytes(Encoding.DER)
    return hashlib.sha256(der).hexdigest(), hashlib.sha1(der).hexdigest()


def cadena_confiable(intermedios, raices, fijadas=frozenset()):
    """True si `intermedios` (de abajo arriba: el emisor del certificado del servidor, su emisor…) forman una cadena firmada
    y la última la firma una raíz de `raices`, es una de ellas, o tiene una huella de `fijadas`. Un certificado descargado por
    HTTP no se acepta por sí solo."""
    if not intermedios:
        return False
    try:
        for hijo, padre in zip(intermedios, intermedios[1:]):
            hijo.verify_directly_issued_by(padre)
        ultimo = intermedios[-1]
        if huellas(ultimo)[0] in fijadas:
            return True
        for raiz in raices:
            if raiz == ultimo:
                return True
            try:
                ultimo.verify_directly_issued_by(raiz)
                return True
            except Exception:
                continue
    except Exception:
        return False
    return False


def contexto(host):
    """Contexto TLS verificado. Si el servidor no envía su certificado intermedio (le pasa a mites.gob.es y a fundae.es),
    se descarga desde la URL 'CA Issuers' (AIA) del propio certificado. Se confía en esa cadena si termina en una raíz del
    sistema o con huella fijada en raices_fijadas.txt. Si termina en una raíz que no está en ninguno de los dos sitios (hoy,
    la raíz de servidores seguros de la FNMT), se sigue aceptando como hasta ahora PERO con un aviso y sus huellas en el log,
    para compararlas con las que publica la FNMT y fijarlas."""
    if host in _CTX:
        return _CTX[host]
    ctx = ssl.create_default_context()
    try:
        with ssl.create_connection((host, 443), timeout=20) as sock, ctx.wrap_socket(sock, server_hostname=host):
            pass
    except ssl.SSLCertVerificationError:
        try:
            from cryptography import x509
            from cryptography.hazmat.primitives.serialization import Encoding
            from cryptography.x509.oid import AuthorityInformationAccessOID, ExtensionOID
            raices = []
            for c in ctx.get_ca_certs(binary_form=True):
                try:
                    raices.append(x509.load_der_x509_certificate(c))
                except Exception:
                    continue
            fijadas = raices_fijadas()
            cert = x509.load_pem_x509_certificate(ssl.get_server_certificate((host, 443)).encode())
            intermedios = []
            for _ in range(4):  # sube hasta 4 niveles
                if cert.issuer == cert.subject:
                    break
                aia = cert.extensions.get_extension_for_oid(ExtensionOID.AUTHORITY_INFORMATION_ACCESS).value
                url = next(d.access_location.value for d in aia if d.access_method == AuthorityInformationAccessOID.CA_ISSUERS)
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                    datos = r.read()
                cert = x509.load_der_x509_certificate(datos) if not datos.startswith(b"-----") else x509.load_pem_x509_certificate(datos)
                intermedios.append(cert)
                if cadena_confiable(intermedios, raices, fijadas):
                    break
            if intermedios:
                if not cadena_confiable(intermedios, raices, fijadas):
                    s256, s1 = huellas(intermedios[-1])
                    print(f"::warning::{host}: la cadena termina en una raíz que no está en el sistema ni fijada "
                          f"({intermedios[-1].subject.rfc4514_string()}; SHA-256 {s256}; SHA-1 {s1}). Se acepta como hasta ahora: "
                          "compara la huella con la que publica la entidad y añádela a raices_fijadas.txt")
                for c in intermedios:
                    ctx.load_verify_locations(cadata=c.public_bytes(Encoding.PEM).decode())
                    print(f"  {host}: añadido intermedio {c.subject.rfc4514_string()}")
        except Exception as e:
            print(f"  {host}: no se pudo completar la cadena TLS: {type(e).__name__}: {e}")
    except Exception:
        pass
    _CTX[host] = ctx
    return ctx


def get(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    host = urllib.parse.urlparse(url).hostname
    ctx = contexto(host) if url.startswith("https") else None
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
        return r.status, r.read().decode("utf-8", errors="replace"), r.geturl()


def escribir(nombre, cabecera, filas):
    with open(OUT / nombre, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";"); w.writerow(cabecera); w.writerows(filas)


def enlaces(html, base):
    for href, texto in re.findall(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', html, re.S | re.I):
        href = href.replace("&amp;", "&").strip()
        if re.search(r"[\s'<>]|^javascript:|^mailto:", href, re.I):
            continue
        href = urllib.parse.urljoin(base, href)
        yield href, " ".join(re.sub(r"<[^>]+>", " ", texto).split())


def accesibilidad():
    urls = ["https://servicios.ine.es/wstempus/js/ES/OPERACIONES_DISPONIBLES", "https://www.ine.es/",
            "https://datos.gob.es/apidata/catalog/dataset.json?_pageSize=1"]
    for w in WEBS.values():
        urls += w["semillas"]
    filas = []
    for u in urls:
        try:
            st, _, _ = get(u, 30); filas.append([urllib.parse.urlparse(u).netloc, u, st, ""])
        except Exception as e:
            filas.append([urllib.parse.urlparse(u).netloc, u, getattr(e, "code", ""), f"{type(e).__name__}: {e}"])
    escribir("accesibilidad.csv", ["dominio", "url", "http", "error"], filas)


# ---------------------------------------------------------------- INEbase
PAT_TABLA = [
    (re.compile(r"jaxiT3/(?:Tabla|Datos)\.htm\?(?:.*&)?t=(\d+)", re.I), "jaxiT3"),
    (re.compile(r"jaxi/(?:Tabla|Datos)\.htm\?(?:.*&)?tpx=(\d+)", re.I), "jaxi_tpx"),
    (re.compile(r"jaxi/(?:Tabla|Datos)\.htm\?(?:.*&)?path=([^&]+)&(?:.*&)?file=([^&]+)", re.I), "jaxi_path"),
]
PAT_SEGUIR = re.compile(r"ine\.es/(dyngs/INEbase/(es/)?(categoria|operacion)\.htm|dynt3/inebase/(es/)?index\.htm\?)", re.I)


CAB_INEBASE = ["semilla", "operacion", "pagina_titulo", "tipo", "tabla_id", "tabla_nombre", "href", "pagina"]


def inebase():
    vistos, tablas, cola = set(), {}, deque()
    for nombre, u in INEBASE_SEMILLAS.items():
        cola.append((u, nombre, "", 0))
    paginas = 0
    while cola and paginas < INEBASE_MAX_PAGINAS:
        url, semilla, operacion, prof = cola.popleft()
        if url in vistos:
            continue
        vistos.add(url); paginas += 1
        try:
            _, html, _ = get(url)
        except Exception as e:
            print(f"  INEbase error {url}: {e}"); continue
        m = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
        titulo = " ".join(m.group(1).split()) if m else ""
        if "operacion.htm" in url or not operacion:
            operacion = titulo
        for href, texto in enlaces(html, url):
            for pat, tipo in PAT_TABLA:
                mt = pat.search(href)
                if mt:
                    tid = mt.group(1) if tipo != "jaxi_path" else urllib.parse.unquote(mt.group(1)).strip("/") + "/" + mt.group(2)
                    tablas.setdefault((tipo, tid), [semilla, operacion, titulo, tipo, tid, texto, href, url])
                    break
            else:
                if "operacion.htm" in href and "operacion.htm" not in url and not INEBASE_OPERACIONES.search(texto):
                    continue  # desde una categoría, solo operaciones de RRHH
                if "categoria.htm" in href:
                    continue  # no saltar a otras categorías
                if "operacion.htm" in href and "operacion.htm" in url and \
                        re.search(r"cid=(\d+)", href) and re.search(r"cid=(\d+)", url) and \
                        re.search(r"cid=(\d+)", href).group(1) != re.search(r"cid=(\d+)", url).group(1):
                    continue  # desde una operación, no saltar a otra
                if PAT_SEGUIR.search(href) and prof < 4 and href not in vistos:
                    # operacion.htm: ir a la pestaña de resultados
                    if "operacion.htm" in href and "menu=" not in href:
                        href += "&menu=resultados"
                    if "operacion.htm" in href and "menu=resultados" not in href:
                        continue
                    cola.append((href, semilla, operacion, prof + 1))
        time.sleep(PAUSA)
        if paginas % 25 == 0:  # guardado parcial por si el workflow se corta
            escribir("ine_inebase_tablas.csv", CAB_INEBASE, list(tablas.values()))
    print(f"INEbase: {paginas} páginas, {len(tablas)} tablas")
    filas = list(tablas.values())
    escribir("ine_inebase_tablas.csv", CAB_INEBASE, filas)

    # Prueba de la API sobre una muestra: 2 tablas por operación y tipo
    muestra, cuenta = [], {}
    for f in filas:
        k = (f[1], f[3]); cuenta[k] = cuenta.get(k, 0) + 1
        if cuenta[k] <= 2:
            muestra.append(f)
    res = []
    for f in muestra[:150]:
        url = f"https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/{f[4]}?nult=1"
        try:
            _, txt, _ = get(url, 90)
            d = json.loads(txt)
            res.append([f[1], f[3], f[4], url, "OK" if isinstance(d, list) else "JSON_INESPERADO",
                        len(d) if isinstance(d, list) else "", "" if isinstance(d, list) else txt[:200]])
        except Exception as e:
            res.append([f[1], f[3], f[4], url, "ERROR", "", f"{type(e).__name__}: {e}"[:200]])
        time.sleep(PAUSA)
    escribir("ine_prueba_api.csv", ["operacion", "tipo", "tabla_id", "url", "estado", "n_series", "detalle"], res)


# ---------------------------------------------------------------- datos.gob.es
def items(url):
    _, txt, _ = get(url, 90)
    d = json.loads(txt)
    return d.get("result", {}).get("items", [])


def texto(v):
    """datos.gob.es devuelve a veces str, a veces dict {_value,_lang} o listas."""
    if isinstance(v, list):
        es = [x for x in v if isinstance(x, dict) and x.get("_lang") == "es"]
        return texto(es[0] if es else (v[0] if v else ""))
    if isinstance(v, dict):
        return v.get("_value") or v.get("value") or v.get("_about") or json.dumps(v, ensure_ascii=False)
    return "" if v is None else str(v)


DATOSGOB_BUSQUEDAS = ["paro registrado", "contratos", "afiliados", "afiliación", "accidentes de trabajo",
                      "convenios colectivos", "empresas de trabajo temporal", "incapacidad temporal",
                      "regulación de empleo", "demandantes de empleo", "huelgas", "enfermedades profesionales"]
DATOSGOB_PUBLICADORES_FIJOS = ["EA0041513"]  # SEPE (visto en datos.gob.es/catalogo/ea0041513-...)


def fila_dataset(pid, pnombre, ds, filas):
    if isinstance(ds, str):
        filas.append([pid, pnombre, ds, "", "", "", "", "item sin detalle (solo URI)"]); return
    pub = texto(ds.get("publisher"))
    dists = ds.get("distribution") or [None]
    if isinstance(dists, dict):
        dists = [dists]
    for di in dists:
        di = di if isinstance(di, dict) else {"accessURL": di}
        filas.append([pid or pub.rsplit("/", 1)[-1], pnombre or pub, texto(ds.get("_about") or ds.get("identifier")),
                      texto(ds.get("title")), texto(di.get("title")), texto(di.get("format")), texto(di.get("accessURL")), ""])


def datosgob():
    # muestra cruda para poder revisar la estructura real de la respuesta
    try:
        _, txt, _ = get(f"{DATOSGOB}catalog/dataset/publisher/EA0041513.json?_pageSize=2", 90)
        (OUT / "datosgob_muestra.json").write_text(txt[:20000], encoding="utf-8")
    except Exception as e:
        print(f"  datos.gob muestra error: {e}")
    pubs, page = [], 0
    while page < 200:
        try:
            its = items(f"{DATOSGOB}catalog/publisher.json?_pageSize=50&_page={page}")
        except Exception as e:
            print(f"  datos.gob publishers error: {e}"); break
        if not its:
            break
        pubs += its; page += 1; time.sleep(PAUSA)
    elegidos = [[p, "", ""] for p in DATOSGOB_PUBLICADORES_FIJOS]
    for p in pubs:
        if isinstance(p, str):
            continue
        nombre = texto(p.get("preferredLabel") or p.get("label") or p.get("title"))
        notation = texto(p.get("notation")) or texto(p.get("_about")).rsplit("/", 1)[-1]
        if PUBLICADORES.search(nombre) and notation not in DATOSGOB_PUBLICADORES_FIJOS:
            elegidos.append([notation, nombre, texto(p.get("_about"))])
    escribir("datosgob_publicadores.csv", ["id", "nombre", "uri"], elegidos)
    print(f"datos.gob: {len(pubs)} publicadores, {len(elegidos)} elegidos")

    filas = []
    for pid, pnombre, _ in elegidos:
        page = 0
        while page < 60:
            try:
                its = items(f"{DATOSGOB}catalog/dataset/publisher/{pid}.json?_pageSize=50&_page={page}")
            except Exception as e:
                filas.append([pid, pnombre, "", "", "", "", "", f"{type(e).__name__}: {e}"]); break
            if not its:
                break
            for ds in its:
                fila_dataset(pid, pnombre, ds, filas)
            page += 1; time.sleep(PAUSA)
    for q in DATOSGOB_BUSQUEDAS:
        for page in range(10):
            try:
                its = items(f"{DATOSGOB}catalog/dataset/title/{urllib.parse.quote(q)}.json?_pageSize=50&_page={page}")
            except Exception as e:
                filas.append(["", f"búsqueda: {q}", "", "", "", "", "", f"{type(e).__name__}: {e}"]); break
            if not its:
                break
            for ds in its:
                fila_dataset("", "", ds, filas)
            time.sleep(PAUSA)
    escribir("datosgob_datasets.csv",
             ["publicador_id", "publicador", "dataset_id", "dataset", "distribucion", "formato", "url_descarga", "error"], filas)


# ---------------------------------------------------------------- webs con ficheros
def rastrear(nombre, conf):
    vistos, ficheros, cola, paginas = set(), {}, deque((u, 0) for u in conf["semillas"]), 0
    while cola and paginas < conf["max"]:
        url, prof = cola.popleft()
        if url in vistos:
            continue
        vistos.add(url); paginas += 1
        try:
            _, html, final = get(url)
        except Exception as e:
            print(f"  {nombre} error {url}: {e}"); continue
        m = re.search(r"<title>(.*?)</title>", html, re.S | re.I)
        titulo = " ".join(m.group(1).split()) if m else ""
        for href, txt in enlaces(html, final):
            if EXT_FICHERO.search(href):
                ext = EXT_FICHERO.search(href).group(1).lower()
                ficheros.setdefault(href, [nombre, ext, txt, href, titulo, url])
            elif conf["dentro"].search(href) and prof < 5 and href not in vistos:
                cola.append((href, prof + 1))
        time.sleep(PAUSA)
    print(f"{nombre}: {paginas} páginas, {len(ficheros)} ficheros")
    escribir(f"ficheros_{nombre}.csv", ["fuente", "formato", "texto_enlace", "url", "pagina_titulo", "pagina"],
             list(ficheros.values()))


def main():
    OUT.mkdir(exist_ok=True)
    pasos = [("accesibilidad", accesibilidad), ("inebase", inebase), ("datosgob", datosgob)]
    pasos += [(n, (lambda n=n, c=c: rastrear(n, c))) for n, c in WEBS.items()]
    elegidos = [a for a in sys.argv[1:] if a != "todos"]
    for nombre, f in pasos:
        if elegidos and nombre not in elegidos:
            continue
        t = time.time()
        try:
            f()
        except Exception as e:
            print(f"FALLO {nombre}: {type(e).__name__}: {e}")
        print(f"[{nombre}] {time.time() - t:.0f}s")
    print("ok")


if __name__ == "__main__":
    sys.exit(main())
