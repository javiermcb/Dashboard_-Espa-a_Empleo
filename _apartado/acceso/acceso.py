"""
acceso.py — Entrada por email con lista de autorizados, solicitudes de acceso y registro de entradas en GitHub.

- Se entra escribiendo el email. Solo pasan los autorizados; el resto puede pulsar «Solicitar acceso» y el
  administrador la aprueba o la rechaza. El email NO se verifica (no hay contraseña); el del administrador pide además
  una clave (secretos de Streamlit) y se bloquea 15 minutos tras 5 claves erróneas.
- Seudonimización (indicación del DPO): los emails no se guardan en claro. Se guarda su huella HMAC-SHA256 con la clave
  RRHH_HASH_CLAVE (sin clave: SHA-256 simple, que se puede revertir probando emails conocidos). Excepción: una solicitud
  pendiente guarda el email en claro, porque el administrador tiene que saber quién pide acceso; al resolverla se
  sustituye por su huella y se borra el motivo. La lista de autorizados guarda además una pista («j•••@empresa.com»)
  para que el administrador reconozca cada entrada.
- Registro mínimo: solo la fecha y hora de cada entrada y la huella del usuario (no los apartados que visita), durante
  RRHH_RETENCION_MESES meses (por defecto 3). Nada de esto se muestra en la app salvo en «Administración».

Secretos de Streamlit:
  RRHH_LOG_TOKEN    token fine-grained del repositorio del registro: Contents Read and write (+ Issues Read and write)
  RRHH_LOG_REPO     usuario/repositorio del registro (javiermcb/Datos_INE_registro)
  RRHH_LOG_RAMA     rama (por defecto registro-accesos; debe existir)
  RRHH_ADMIN_EMAIL / RRHH_ADMIN_CLAVE   administrador
  RRHH_HASH_CLAVE   clave de la seudonimización. NO cambiarla: las huellas guardadas dejarían de coincidir y habría que
                    volver a dar de alta a todos
  RRHH_RETENCION_MESES  meses que se conserva el registro de entradas y las solicitudes resueltas (por defecto 3)
  RRHH_SESION_MIN   minutos sin actividad tras los que hay que volver a entrar (por defecto 60)

Ficheros (rama del registro):
  registro/autorizados.csv      huella;pista;fecha_alta;origen
  registro/solicitudes.csv      fecha_utc;email;motivo;estado      email en claro solo mientras está pendiente
  registro/accesos_AAAA-MM.csv  fecha_utc;email;evento;detalle;sesion   (email = huella; solo entradas)

Sesión: al entrar se guarda en el navegador una cookie con un identificador aleatorio (no lleva el email); al recargar la
página se entra sin volver a escribir el email. El identificador solo vale en memoria del servidor (si la app se reinicia
hay que volver a entrar) y caduca tras RRHH_SESION_MIN minutos sin usar la app (por defecto 60) o a las 12 horas.
«Cerrar sesión» lo anula. Al recuperar la sesión se vuelve a comprobar que el email sigue autorizado.

Si GitHub no confirma que ha guardado una entrada, se vuelve a pedir el email. Una vez al día (y con el botón de
Administración): se seudonimiza lo que quedara en claro de versiones anteriores, se borra lo que supera el plazo y se
compacta el historial de la rama para que lo borrado no quede en versiones anteriores. Los mensajes de cada cambio y
los avisos de solicitud no llevan el email.
Sin RRHH_LOG_TOKEN / RRHH_LOG_REPO (pruebas o desarrollo) no hay lista: entra cualquier email y nada se guarda.
"""
import base64, hashlib, hmac, json, re, secrets, threading, time, urllib.error, urllib.request
from datetime import datetime, timedelta, timezone

import streamlit as st

from comun.datos import _ajuste

TITULO = "Centro de estadísticas públicas"
CABECERA = "fecha_utc;email;evento;detalle;sesion\n"
CAB_AUTORIZADOS = "huella;pista;fecha_alta;origen\n"
CAB_SOLICITUDES = "fecha_utc;email;motivo;estado\n"
RX_EMAIL = re.compile(r"^[^@\s;]+@[^@\s;]+\.[a-z]{2,}$", re.I)
RX_ACCESOS = re.compile(r"accesos_(\d{4})-(\d{2})\.csv")


def _ahora():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _limpio(t, n=60):
    """Texto seguro para el CSV: sin separadores ni saltos de línea y sin fórmulas al abrirlo en Excel."""
    t = " ".join(str(t or "").replace(";", ",").split())[:n]
    return "'" + t if t[:1] in ("=", "+", "-", "@") else t


def _config():
    return _ajuste("RRHH_LOG_TOKEN"), _ajuste("RRHH_LOG_REPO"), _ajuste("RRHH_LOG_RAMA") or "registro-accesos"


def _api(metodo, url, token, cuerpo=None):
    req = urllib.request.Request(url, method=metodo, data=json.dumps(cuerpo).encode() if cuerpo else None,
                                 headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                                          "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "rrhh360-app"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read() or b"{}")


def _leer(ruta, cabecera):
    """(texto, sha) de un fichero del registro; (cabecera, None) si aún no existe."""
    token, repo, rama = _config()
    try:
        actual = _api("GET", f"https://api.github.com/repos/{repo}/contents/{ruta}?ref={rama}", token)
        return base64.b64decode(actual["content"]).decode("utf-8"), actual["sha"]
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        return cabecera, None


def _modificar(ruta, cabecera, cambio, mensaje):
    """Lee el fichero, aplica cambio(texto) -> texto nuevo y lo guarda. Reintenta si otra sesión escribió a la vez (409).
    True si GitHub lo ha guardado, False si ha fallado, None si el registro no está configurado."""
    token, repo, rama = _config()
    if not (token and repo):
        print(f"[registro] sin RRHH_LOG_TOKEN / RRHH_LOG_REPO ({ruta}):", mensaje, flush=True)
        return None
    url = f"https://api.github.com/repos/{repo}/contents/{ruta}"
    for intento in range(4):
        try:
            texto, sha = _leer(ruta, cabecera)
            nuevo = cambio(texto)
            if nuevo == texto:  # nada que cambiar: no se crea un commit vacío (ni un fichero solo con cabecera)
                return True
            cuerpo = {"message": mensaje, "branch": rama, "content": base64.b64encode(nuevo.encode("utf-8")).decode()}
            if sha:
                cuerpo["sha"] = sha
            _api("PUT", url, token, cuerpo)
            return True
        except urllib.error.HTTPError as e:
            if e.code in (409, 422) and intento < 3:
                time.sleep(1 + intento)
                continue
            print(f"[registro] GitHub respondió {e.code} ({ruta}): {mensaje}", flush=True)
            return False
        except Exception as e:
            print(f"[registro] {type(e).__name__}: {e} ({ruta}): {mensaje}", flush=True)
            return False
    return False


def _escribir(*filas):
    """Añade filas al registro de accesos de su mes (fecha_utc al principio de cada fila), un guardado por mes."""
    resultado = None
    for mes in sorted({f[:7] for f in filas}):
        del_mes = "".join(f for f in filas if f[:7] == mes)
        r = _modificar(f"registro/accesos_{mes}.csv", CABECERA, lambda t, d=del_mes: t + d,
                       "Registro de acceso" if del_mes.count("\n") == 1 else f"Registro de acceso ({del_mes.count(chr(10))} eventos)")
        resultado = r if resultado in (None, True) else resultado
    return resultado


def _filas(texto):
    lineas = [l for l in texto.splitlines() if l.strip()]
    cab = lineas[0].split(";") if lineas else []
    return [dict(zip(cab, l.split(";"))) for l in lineas[1:]]


# ------------------------------------------------------------------------------------------------ seudonimización
def huella(email):
    """Huella del email: HMAC-SHA256 con RRHH_HASH_CLAVE ('h:…'); sin clave, SHA-256 simple ('s:…')."""
    e = str(email or "").strip().lower().encode("utf-8")
    clave = _ajuste("RRHH_HASH_CLAVE")
    if clave not in (None, ""):
        return "h:" + hmac.new(str(clave).encode("utf-8"), e, hashlib.sha256).hexdigest()
    return "s:" + hashlib.sha256(e).hexdigest()


def es_huella(v):
    return bool(re.fullmatch(r"[hs]:[0-9a-f]{64}", str(v or "").strip()))


def coincide(email, guardado):
    """¿El valor guardado (huella, o email en claro de versiones anteriores) corresponde a este email?"""
    g = str(guardado or "").strip().lower()
    if not g:
        return False
    if es_huella(g):
        e = str(email or "").strip().lower().encode("utf-8")
        simple = "s:" + hashlib.sha256(e).hexdigest()  # huellas guardadas antes de configurar RRHH_HASH_CLAVE
        return hmac.compare_digest(g, huella(email)) or hmac.compare_digest(g, simple)
    return g == str(email or "").strip().lower()


def pista(email):
    """'javier@empresa.com' -> 'j•••@empresa.com': para reconocer la entrada sin guardar el email."""
    local, _, dominio = str(email).strip().lower().partition("@")
    return f"{local[:1]}•••@{dominio}"


def _seud(v):
    """Email en claro -> huella; lo demás (huellas, vacíos, '(administrador)') se queda igual."""
    v = str(v or "").strip()
    return huella(v) if "@" in v and not es_huella(v) else v


def _autorizados_normal(texto):
    """autorizados.csv en el formato actual (convierte el antiguo email;fecha_alta;origen)."""
    lineas = [l for l in texto.splitlines() if l.strip()]
    if not lineas or lineas[0].startswith("huella;"):
        return texto if lineas else CAB_AUTORIZADOS
    filas = [CAB_AUTORIZADOS]
    for f in _filas(texto):
        e = f.get("email", "").strip().lower()
        if e:
            filas.append(f"{huella(e)};{_limpio(pista(e), 120)};{f.get('fecha_alta', '')};{f.get('origen', '')}\n")
    return "".join(filas)


# ------------------------------------------------------------------------------------------------ autorizados
@st.cache_data(ttl=60, show_spinner=False)
def autorizados():
    """[{huella, pista, fecha_alta, origen}] de la lista de autorizados. None si el registro no está configurado."""
    token, repo, _ = _config()
    if not (token and repo):
        return None
    texto, _ = _leer("registro/autorizados.csv", CAB_AUTORIZADOS)
    return [f for f in _filas(_autorizados_normal(texto)) if f.get("huella")]


def autorizado(email, lista):
    return any(coincide(email, f.get("huella")) for f in lista)


MAX_FALLOS, BLOQUEO_MIN = 5, 15


@st.cache_resource
def _fallos_admin():
    """Intentos fallidos de la clave de administrador, compartidos por todas las sesiones del servidor:
    {'n': fallos seguidos, 'hasta': instante hasta el que está bloqueada}. Así no se puede probar claves a ciegas."""
    return {"n": 0, "hasta": 0.0}


def _admin_bloqueado():
    return time.time() < _fallos_admin()["hasta"]


def _fallo_admin():
    f = _fallos_admin()
    f["n"] += 1
    if f["n"] >= MAX_FALLOS:
        f["hasta"], f["n"] = time.time() + BLOQUEO_MIN * 60, 0
        print(f"[registro] clave de administrador bloqueada {BLOQUEO_MIN} min tras {MAX_FALLOS} intentos fallidos", flush=True)
        threading.Thread(target=registrar_evento_admin, args=("bloqueo_clave_admin",), daemon=True).start()


def _clave_correcta(clave):
    """Compara en tiempo constante. Como bytes UTF-8 para admitir tildes, ñ o símbolos, y con str() por si la clave se
    escribió en los secretos sin comillas (TOML la lee entonces como número)."""
    secreto = _ajuste("RRHH_ADMIN_CLAVE")
    if secreto is None or str(secreto) == "":
        return False
    return hmac.compare_digest(str(clave).encode("utf-8"), str(secreto).encode("utf-8"))


def registrar_evento_admin(evento):
    _escribir(";".join([_ahora(), "(administrador)", _limpio(evento, 40), "", ""]) + "\n")


def es_admin(email):
    admin = (_ajuste("RRHH_ADMIN_EMAIL") or "").strip().lower()
    return bool(admin) and email == admin


def autorizar(email, origen="administrador"):
    email = email.strip().lower()
    def cambio(t):
        t = _autorizados_normal(t)
        if any(coincide(email, f.get("huella")) for f in _filas(t)):
            return t
        return t + f"{huella(email)};{_limpio(pista(email), 120)};{_ahora()};{_limpio(origen, 40)}\n"
    r = _modificar("registro/autorizados.csv", CAB_AUTORIZADOS, cambio, "Alta en la lista de autorizados")
    autorizados.clear()
    return r


def quitar(quien):
    """Quita de la lista por email o por huella (la página de Administración solo conoce la huella)."""
    def cambio(t):
        lineas = _autorizados_normal(t).splitlines(keepends=True)
        fuera = lambda h: h == quien or coincide(quien, h)
        return lineas[0] + "".join(l for l in lineas[1:] if not fuera(l.split(";")[0].strip()))
    r = _modificar("registro/autorizados.csv", CAB_AUTORIZADOS, cambio, "Baja en la lista de autorizados")
    autorizados.clear()
    return r


# ------------------------------------------------------------------------------------------------ solicitudes
def solicitudes():
    token, repo, _ = _config()
    if not (token and repo):
        return []
    texto, _ = _leer("registro/solicitudes.csv", CAB_SOLICITUDES)
    return _filas(texto)


def solicitar(email, motivo):
    """Guarda la solicitud (si no hay otra pendiente del mismo email) y abre un aviso en GitHub (llega por correo)."""
    email = email.strip().lower()
    fila = f"{_ahora()};{_limpio(email, 120)};{_limpio(motivo, 200)};pendiente\n"
    r = _modificar("registro/solicitudes.csv", CAB_SOLICITUDES,
                   lambda t: t if any(f.get("email") == email and f.get("estado") == "pendiente" for f in _filas(t)) else t + fila,
                   "Nueva solicitud de acceso")
    if r:
        threading.Thread(target=_avisar, args=(email,), daemon=True).start()
    return r


def _avisar(email):
    """Comentario en la issue «Solicitudes de acceso» (necesita permiso Issues en el token; si no, no pasa nada)."""
    token, repo, _ = _config()
    try:
        base = f"https://api.github.com/repos/{repo}/issues"
        abiertas = _api("GET", f"{base}?labels=solicitud-acceso&state=open", token)
        texto = f"Nueva solicitud de acceso al {TITULO} ({_ahora()} UTC). Revísala en la página «Administración» de la app."
        if abiertas:
            _api("POST", f"{base}/{abiertas[0]['number']}/comments", token, {"body": texto})
        else:
            _api("POST", base, token, {"title": "Solicitudes de acceso", "body": texto, "labels": ["solicitud-acceso"]})
    except Exception as e:
        print(f"[registro] aviso de solicitud no enviado: {type(e).__name__}: {e}", flush=True)


def resolver(email, estado):
    """Marca las solicitudes pendientes de un email como aprobada / rechazada (y si se aprueba, lo autoriza)."""
    email = email.strip().lower()
    def cambio(t):
        lineas = t.splitlines(keepends=True)
        out = [lineas[0]]
        for l in lineas[1:]:
            p = l.rstrip("\n").split(";")
            if len(p) == 4 and p[1].lower() == email and p[3] == "pendiente":
                p[1], p[2], p[3] = huella(email), "", estado  # resuelta: sin email en claro ni motivo
                l = ";".join(p) + "\n"
            out.append(l)
        return "".join(out)
    r = _modificar("registro/solicitudes.csv", CAB_SOLICITUDES, cambio, f"Solicitud {estado}")
    if r and estado == "aprobada":
        r = autorizar(email, "solicitud")
    return r


# ------------------------------------------------------------------------------------------------ protección de datos
def meses_retencion():
    try:
        return max(1, int(_ajuste("RRHH_RETENCION_MESES") or 3))
    except ValueError:
        return 3


def _ficheros_accesos():
    """[(nombre, ruta, sha)] de los registros mensuales de accesos."""
    token, repo, rama = _config()
    try:
        lista = _api("GET", f"https://api.github.com/repos/{repo}/contents/registro?ref={rama}", token)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return []
        raise
    return [(f["name"], f["path"], f["sha"]) for f in lista if RX_ACCESOS.fullmatch(f.get("name", ""))]


def compactar():
    """Deja la rama del registro con un solo commit (el contenido actual), para que lo borrado no siga en el historial
    de versiones. True si ha compactado, False si no hacía falta o no se pudo, None si no está configurado.
    Si otra sesión escribe entre medias, se reintenta (como mucho 3 veces) para no perder su cambio."""
    token, repo, rama = _config()
    if not (token and repo):
        return None
    base = f"https://api.github.com/repos/{repo}/git"
    for _ in range(3):
        sha = _api("GET", f"{base}/ref/heads/{rama}", token)["object"]["sha"]
        commit = _api("GET", f"{base}/commits/{sha}", token)
        if not commit.get("parents"):
            return False  # ya tiene un solo commit
        nuevo = _api("POST", f"{base}/commits", token,
                     {"message": "Registro de acceso (historial compactado)", "tree": commit["tree"]["sha"], "parents": []})
        if _api("GET", f"{base}/ref/heads/{rama}", token)["object"]["sha"] != sha:
            continue  # alguien ha escrito mientras: se vuelve a empezar con su cambio incluido
        _api("PATCH", f"{base}/refs/heads/{rama}", token, {"sha": nuevo["sha"], "force": True})
        return True
    print("[registro] no se pudo compactar el historial (escrituras simultáneas); se reintentará", flush=True)
    return False


def seudonimizar():
    """Pasa a huella lo que quedara en claro de versiones anteriores: lista de autorizados, solicitudes resueltas (y
    les quita el motivo) y registros de entradas (y quita las visitas a apartados, que ya no se registran)."""
    _modificar("registro/autorizados.csv", CAB_AUTORIZADOS, _autorizados_normal, "Seudonimización")
    def solicitudes_(t):
        lineas = t.splitlines(keepends=True)
        out = lineas[:1]
        for l in lineas[1:]:
            p = l.rstrip("\n").split(";")
            if len(p) == 4 and p[3] != "pendiente" and (p[2] or not es_huella(p[1])):
                p[1], p[2] = _seud(p[1]), ""
                l = ";".join(p) + "\n"
            out.append(l)
        return "".join(out)
    _modificar("registro/solicitudes.csv", CAB_SOLICITUDES, solicitudes_, "Seudonimización")
    def accesos_(t):
        lineas = t.splitlines(keepends=True)
        out = lineas[:1]
        for l in lineas[1:]:
            p = l.rstrip("\n").split(";")
            if len(p) >= 3 and p[2] == "visita":
                continue
            if len(p) >= 5:
                p[1], p[3], p[4] = _seud(p[1]), "", ""
                l = ";".join(p) + "\n"
            out.append(l)
        return "".join(out)
    for _, ruta, _ in _ficheros_accesos():
        _modificar(ruta, CABECERA, accesos_, "Seudonimización")


def purgar(ahora=None):
    """Borra los registros mensuales de accesos de hace más de RRHH_RETENCION_MESES meses y las solicitudes resueltas
    igual de antiguas. Devuelve el número de ficheros borrados (None si el registro no está configurado)."""
    token, repo, rama = _config()
    if not (token and repo):
        return None
    seudonimizar()
    ahora, meses = ahora or datetime.now(timezone.utc), meses_retencion()
    limite = ahora.year * 12 + ahora.month - 1 - meses
    borrados = 0
    for nombre, ruta, sha in _ficheros_accesos():
        m = RX_ACCESOS.fullmatch(nombre)
        if int(m[1]) * 12 + int(m[2]) - 1 < limite:
            _api("DELETE", f"https://api.github.com/repos/{repo}/contents/{ruta}", token,
                 {"message": f"Retención de {meses} meses: borrado {nombre}", "sha": sha, "branch": rama})
            borrados += 1
    corte = (ahora - timedelta(days=round(meses * 30.44))).strftime("%Y-%m-%d %H:%M:%S")
    def cambio(t):
        lineas = t.splitlines(keepends=True)
        return lineas[0] + "".join(l for l in lineas[1:]
                                   if l.rstrip("\n").split(";")[-1] == "pendiente" or l.split(";")[0] >= corte)
    if _modificar("registro/solicitudes.csv", CAB_SOLICITUDES, cambio, f"Retención de {meses} meses: solicitudes antiguas") is False:
        raise RuntimeError("no se han podido limpiar las solicitudes")
    compactar()  # lo borrado tampoco queda en el historial de versiones
    return borrados


@st.cache_resource
def _ultima_purga():
    return {"t": 0.0}


def _purga_diaria():
    """Lanza purgar() en segundo plano como mucho una vez al día por servidor."""
    u = _ultima_purga()
    if time.time() - u["t"] < 86400:
        return
    u["t"] = time.time()
    def tarea():
        try:
            n = purgar()
            if n:
                print(f"[registro] retención: {n} registros mensuales borrados", flush=True)
        except Exception as e:
            u["t"] = 0.0  # se reintenta en el siguiente acceso
            print(f"[registro] retención no aplicada: {type(e).__name__}: {e}", flush=True)
    threading.Thread(target=tarea, daemon=True).start()


def suprimir(email):
    """Borra todos los datos de un email: lista de autorizados, solicitudes y registros de accesos (derecho de supresión).
    True si todo se ha borrado."""
    email = email.strip().lower()
    def sin_email(col, normal=None):
        def cambio(t):
            lineas = (normal(t) if normal else t).splitlines(keepends=True)
            return lineas[0] + "".join(l for l in lineas[1:] if not coincide(email, (l.split(";") + [""] * 3)[col]))
        return cambio
    ok = _modificar("registro/autorizados.csv", CAB_AUTORIZADOS, sin_email(0, _autorizados_normal), "Supresión de datos") is not False
    ok &= _modificar("registro/solicitudes.csv", CAB_SOLICITUDES, sin_email(1), "Supresión de datos") is not False
    try:
        ficheros = _ficheros_accesos()
    except Exception as e:
        print(f"[registro] supresión: no se pudo listar el registro: {type(e).__name__}: {e}", flush=True)
        return False
    for _, ruta, _ in ficheros:
        ok &= _modificar(ruta, CABECERA, sin_email(1), "Supresión de datos") is not False
    autorizados.clear()
    if ok:
        try:
            compactar()
        except Exception as e:
            print(f"[registro] supresión hecha, historial sin compactar: {type(e).__name__}", flush=True)
            return False
    return ok


# ------------------------------------------------------------------------------------------------ eventos
def registrar(evento, esperar=False):
    """Anota un evento (fecha y hora + huella del usuario). Con esperar=True devuelve True / False / None."""
    u = st.session_state.get("usuario") or {}
    fila = ";".join([_ahora(), huella(u.get("email")) if u.get("email") else "", _limpio(evento, 40), "", ""]) + "\n"
    if esperar:
        return _escribir(fila)
    threading.Thread(target=_escribir, args=(fila,), daemon=True).start()


# ------------------------------------------------------------------------------------------------ sesión (recargar sin volver a entrar)
COOKIE, SESION_MAX_H = "rrhh_sesion", 12


def _sesion_min():
    try:
        return max(5, int(_ajuste("RRHH_SESION_MIN") or 60))
    except ValueError:
        return 60


@st.cache_resource(show_spinner=False)
def _sesiones():
    """{identificador: {email, admin, inicio, visto}} compartido por todas las pestañas; solo en memoria."""
    return {}


def _vigente(s, ahora):
    return ahora - s["visto"] < _sesion_min() * 60 and ahora - s["inicio"] < SESION_MAX_H * 3600


def _cookie_js(valor, segundos):
    st.html(f"""<script>document.cookie = "{COOKIE}={valor}; path=/; max-age={segundos}; SameSite=Strict"
            + (location.protocol === "https:" ? "; Secure" : "");</script>""", unsafe_allow_javascript=True)


def _abrir_sesion():
    ahora, ses = time.time(), _sesiones()
    for k in [k for k, s in ses.items() if not _vigente(s, ahora)]:
        ses.pop(k, None)
    token = secrets.token_urlsafe(32)
    u = st.session_state["usuario"]
    ses[token] = {"email": u["email"], "admin": u["admin"], "inicio": ahora, "visto": ahora}
    st.session_state["_sesion"] = token
    st.session_state["_cookie_pendiente"] = token  # se escribe en la siguiente ejecución (st.rerun descarta lo de esta)


def _recuperar_sesion():
    """Entra con la cookie de una sesión vigente. True si la ha recuperado."""
    try:
        token = st.context.cookies.get(COOKIE)
    except Exception:
        token = None
    s = _sesiones().get(token) if token else None
    if not s or not _vigente(s, time.time()):
        return False
    if not s["admin"]:
        try:
            lista = autorizados()
        except Exception:
            return False
        if lista is not None and not autorizado(s["email"], lista):  # le han quitado el acceso
            _sesiones().pop(token, None)
            return False
    st.session_state["usuario"] = {"email": s["email"], "admin": s["admin"]}
    st.session_state["_sesion"] = token
    return True


def cerrar_sesion():
    _sesiones().pop(st.session_state.get("_sesion"), None)
    for k in ("usuario", "_sesion", "_cookie_pendiente"):
        st.session_state.pop(k, None)
    st.session_state["_borrar_cookie"] = True
    st.rerun()


def _sesion_activa():
    """True si la sesión de esta pestaña sigue vigente (y anota la actividad); False si ha caducado por inactividad."""
    token = st.session_state.get("_sesion")
    s = _sesiones().get(token) if token else None
    if token and (not s or not _vigente(s, time.time())):
        _sesiones().pop(token, None)
        for k in ("usuario", "_sesion", "_cookie_pendiente"):
            st.session_state.pop(k, None)
        st.session_state["_caducada"] = True
        return False
    if s:
        s["visto"] = time.time()
    if st.session_state.get("_cookie_pendiente"):
        _cookie_js(st.session_state.pop("_cookie_pendiente"), SESION_MAX_H * 3600)
    return True


# ------------------------------------------------------------------------------------------------ pantalla de entrada
def identificar():
    """Pantalla de entrada. Devuelve True cuando la persona ya ha entrado."""
    if st.session_state.get("usuario") and _sesion_activa():
        return True
    if not st.session_state.get("usuario") and _recuperar_sesion():
        return _sesion_activa()
    if st.session_state.pop("_borrar_cookie", False) or st.session_state.get("_caducada"):
        _cookie_js("", 0)
    _, centro, _ = st.columns([1, 1.3, 1])
    with centro:
        st.title(TITULO)
        st.caption("Datos públicos de empleo en España. Escribe el email con el que tienes acceso.")
        if st.session_state.pop("_caducada", False):
            st.info(f"La sesión se ha cerrado tras {_sesion_min()} minutos sin actividad. Vuelve a escribir tu email.")
        with st.form("acceso", border=True):
            email = st.text_input("Email", max_chars=120, placeholder="nombre@empresa.com").strip().lower()
            clave = st.text_input("Clave de administración", type="password") if es_admin(email) else ""
            entrar = st.form_submit_button("Entrar", type="primary", width="stretch")
        st.caption("Por seguridad se anota la fecha y hora de cada entrada, con el email seudonimizado; "
                   f"se borra a los {meses_retencion()} meses.")
    if st.session_state.get("_solicitud_ok"):
        centro.success(f"Solicitud enviada para {st.session_state.pop('_solicitud_ok')}. Podrás entrar cuando se apruebe.")
    if st.session_state.get("_pedir_acceso"):
        _formulario_solicitud(centro, st.session_state["_pedir_acceso"])
        return False
    if not entrar:
        return False
    if not RX_EMAIL.match(email):
        centro.error("Escribe un email válido.")
        return False
    admin = es_admin(email)
    if admin and _admin_bloqueado():
        centro.error(f"Demasiados intentos fallidos. La entrada de administración está bloqueada {BLOQUEO_MIN} minutos.")
        return False
    if admin and not clave:
        centro.error("Escribe la clave de administración.")
        return False
    if admin and not _clave_correcta(clave):
        _fallo_admin()
        centro.error("Clave de administración incorrecta.")
        return False
    if admin:
        _fallos_admin()["n"] = 0
    try:
        lista = autorizados()
    except Exception as e:
        print(f"[registro] no se pudo leer la lista de autorizados: {type(e).__name__}: {e}", flush=True)
        centro.error("No se ha podido comprobar el acceso. Vuelve a intentarlo.")
        return False
    if lista is not None and not admin and not autorizado(email, lista):
        st.session_state["_pedir_acceso"] = email
        st.rerun()
    st.session_state["usuario"] = {"email": email, "admin": admin}
    with centro, st.spinner("Registrando el acceso…"):
        ok = registrar("acceso", esperar=True)
    if ok is False:  # GitHub no ha confirmado el registro: se vuelve a pedir
        del st.session_state["usuario"]
        centro.error("No se ha podido registrar el acceso. Vuelve a escribir tu email.")
        return False
    if ok:
        _purga_diaria()
    _abrir_sesion()
    st.rerun()


def _formulario_solicitud(centro, email):
    with centro:
        st.warning(f"**{email}** no tiene acceso todavía.")
        motivo = st.text_input("Motivo (opcional)", max_chars=200, key="motivo_solicitud")
        c1, c2 = st.columns(2)
        if c1.button("Solicitar acceso", type="primary", width="stretch"):
            if solicitar(email, motivo) is False:
                st.error("No se ha podido enviar la solicitud. Vuelve a intentarlo.")
            else:
                del st.session_state["_pedir_acceso"]
                st.session_state["_solicitud_ok"] = email
                st.rerun()
        if c2.button("Usar otro email", width="stretch"):
            del st.session_state["_pedir_acceso"]
            st.rerun()
