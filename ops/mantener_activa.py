#!/usr/bin/env python3
"""
ops/mantener_activa.py — Abre la app con un navegador sin pantalla para que Streamlit Community Cloud no la duerma
por inactividad y, si ya está dormida, pulsa el botón para despertarla. Lo ejecuta el workflow mantener_apps_activas.yml.

Uso: python ops/mantener_activa.py https://<tu-app>.streamlit.app/
Sale con error (y el workflow avisa) si la app no responde o si solo se ve una pantalla de inicio de sesión de
Streamlit (app privada: un robot sin cuenta no puede entrar ni mantenerla despierta).
"""
import os, sys

from playwright.sync_api import sync_playwright

URL = sys.argv[1]
DESPERTAR = ("get this app back up", "Yes, get this app back up")
SENALES = ("Dashboard", "Email", "Inicio")  # pantalla de entrada o páginas de la app
# textos con los que Streamlit muestra un fallo del código de la app (no de la plataforma)
ERRORES_APP = ("Traceback", "Error running app", "ModuleNotFoundError", "AttributeError", "KeyError", "Oh no.")
DIAGNOSTICO = "diagnostico_app.txt"  # el workflow lo copia en el aviso


def _diagnostico(texto):
    """Deja escrito dónde está el fallo para el aviso por correo."""
    with open(DIAGNOSTICO, "a", encoding="utf-8") as f:
        f.write(f"{URL}: {texto}\n")
    print("::error::" + texto)


def _texto(marco):
    try:
        return marco.inner_text("body", timeout=5_000)[:2000]
    except Exception:
        return ""


def main():
    with sync_playwright() as p:
        nav = p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH"))  # en local, el Chromium instalado
        pag = nav.new_page()
        try:
            resp = pag.goto(URL, wait_until="domcontentloaded", timeout=120_000)
        except Exception as e:
            _diagnostico(f"PLATAFORMA (Streamlit): la dirección no responde ({type(e).__name__}). No es un fallo del código ni "
                         "de los datos; suele ser una caída de Streamlit Community Cloud. Comprobar https://www.streamlitstatus.com/")
            return 1
        if resp is not None and resp.status >= 500:
            _diagnostico(f"PLATAFORMA (Streamlit): responde con error HTTP {resp.status}. No es un fallo del código ni de los datos.")
            return 1
        pag.wait_for_timeout(15_000)
        texto = pag.inner_text("body")[:2000]
        boton = next((pag.get_by_role("button", name=t) for t in DESPERTAR if pag.get_by_role("button", name=t).count()), None)
        if boton is not None:
            print("La app estaba dormida: se despierta.")
            boton.first.click()
            pag.wait_for_timeout(90_000)  # arrancar el contenedor tarda
            texto = pag.inner_text("body")[:2000]
        # la app (en su iframe) muestra la pantalla de entrada o las páginas; se mira en todos los marcos hasta 60 s
        marcos = ""
        for _ in range(12):
            marcos = " ".join(_texto(f) for f in pag.frames if f.url.startswith("http"))
            if any(t in marcos for t in ERRORES_APP):
                _diagnostico("CÓDIGO DE LA APP: Streamlit arranca pero la app muestra un error. Texto: "
                             + " ".join(marcos.split())[:400] + " · Revisar el último cambio publicado en la rama principal.")
                return 1
            if any(t in marcos for t in SENALES):
                print("App activa:", URL)
                return 0
            pag.wait_for_timeout(5_000)
        if "sign in" in texto.lower() or "log in" in texto.lower():
            _diagnostico("CONFIGURACIÓN DE STREAMLIT: pide iniciar sesión (la app está en modo privado); el robot no puede "
                         "entrar. Revisar Settings → Sharing en share.streamlit.io.")
            return 1
        _diagnostico("SIN IDENTIFICAR: la página carga pero no se ve la app ni un error reconocible. Texto: "
                     + " ".join((texto + " " + marcos).split())[:400])
        return 1


if __name__ == "__main__":
    sys.exit(main())
