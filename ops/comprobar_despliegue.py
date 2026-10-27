#!/usr/bin/env python3
"""
ops/comprobar_despliegue.py — Mide en la app DESPLEGADA el ancho de la barra lateral para saber si ya está publicada la
versión con la barra mínima (unos 76 px; la antigua mide ~300 px). Lo ejecuta, a mano, comprobar_despliegue.yml.

Uso: python ops/comprobar_despliegue.py https://<tu-app>.streamlit.app/
Sale con 0 si la barra es la mínima, con 1 si es la antigua o si no se puede medir.
"""
import os, sys

from playwright.sync_api import sync_playwright

URL = sys.argv[1]
DESPERTAR = ("get this app back up", "Yes, get this app back up")
MEDIR = """() => { const s = document.querySelector('[data-testid="stSidebar"]');
  return s ? {ancho: Math.round(s.getBoundingClientRect().width), texto: s.innerText.replace(/\\s+/g, ' ').trim().slice(0, 80)} : null; }"""


def medir(pag):
    for f in pag.frames:
        try:
            r = f.evaluate(MEDIR)
        except Exception:
            continue
        if r:
            return r
    return None


def main():
    with sync_playwright() as p:
        nav = p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH"))
        pag = nav.new_page(viewport={"width": 1280, "height": 900})
        try:
            pag.goto(URL, wait_until="domcontentloaded", timeout=120_000)
        except Exception as e:
            print(f"{URL}: no responde ({type(e).__name__})")
            return 1
        pag.wait_for_timeout(15_000)
        for t in DESPERTAR:
            b = pag.get_by_role("button", name=t)
            if b.count():
                print("La app estaba dormida: se despierta.")
                b.first.click()
                pag.wait_for_timeout(90_000)
                break
        r = None
        for _ in range(12):  # hasta 60 s a que pinte la barra
            r = medir(pag)
            if r:
                break
            pag.wait_for_timeout(5_000)
        if not r:
            print(f"{URL}: no se ve la barra lateral (¿la app no ha cargado?)")
            return 1
        nueva = r["ancho"] <= 100
        print(f"{URL}: barra de {r['ancho']} px ({r['ancho'] / 37.8:.1f} cm) → {'BARRA NUEVA' if nueva else 'BARRA ANTIGUA'} · texto: «{r['texto']}»")
        return 0 if nueva else 1


if __name__ == "__main__":
    sys.exit(main())
