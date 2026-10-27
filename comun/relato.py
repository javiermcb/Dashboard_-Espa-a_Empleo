"""
relato.py — Piezas comunes de los apartados pregunta: la respuesta en una frase, los puntos que la apoyan y qué significa
para el negocio de ETT. Mismo estilo en todas las páginas para que se lean igual.
"""
from html import escape

import streamlit as st

CSS = """<style>
.rr-resp{border-left:6px solid #d9ab42;background:#fbf6e9;border-radius:10px;padding:1rem 1.2rem;margin:0.4rem 0 1.2rem 0}
.rr-resp h3{margin:0 0 0.5rem 0;font-size:1.35rem;line-height:1.35;color:#00145A}
.rr-resp ul{margin:0.2rem 0 0 1.1rem;padding:0}
.rr-resp li{margin:0.2rem 0;line-height:1.45}
.rr-impl{border:1px solid #d9ab42;background:#fbf6e9;border-radius:10px;padding:0.8rem 1.1rem;margin:0.6rem 0 1.2rem 0}
.rr-impl b{color:#00145A}
.rr-nota{color:#4a5585;font-size:0.85rem}
.rr-resumen{border-left:4px solid #00145A;background:#f5f6fb;border-radius:8px;padding:0.6rem 1rem;margin:0.2rem 0 1rem 0}
.rr-resumen ul{margin:0.1rem 0 0 1.1rem;padding:0}
.rr-resumen li{margin:0.15rem 0;line-height:1.4}
.rr-pie{border-top:1px solid #eadfbd;margin-top:2rem;padding-top:0.6rem;color:#4a5585;font-size:0.8rem;line-height:1.9}
.rr-pie span{display:inline-block;border:1px solid #eadfbd;border-radius:999px;padding:0 0.55rem;margin:0 0.25rem 0.25rem 0;background:#fff;white-space:nowrap}
.rr-pie b{color:#00145A;font-weight:600}
</style>"""


def estilo():
    st.markdown(CSS, unsafe_allow_html=True)


def respuesta(frase, puntos):
    """La respuesta a la pregunta en una frase (título que afirma) y los 2-4 datos que la sostienen."""
    lis = "".join(f"<li>{escape(p)}</li>" for p in puntos if p)
    st.markdown(f"<div class='rr-resp'><h3>{escape(frase)}</h3><ul>{lis}</ul></div>", unsafe_allow_html=True)


def implicacion(texto):
    """Qué significa para una ETT (recuadro dorado)."""
    st.markdown(f"<div class='rr-impl'><b>Qué significa para la ETT.</b> {escape(texto)}</div>", unsafe_allow_html=True)


def nota(texto):
    st.markdown(f"<div class='rr-nota'>{escape(texto)}</div>", unsafe_allow_html=True)


def resumen(puntos):
    """Resumen breve al principio de una página de Estadísticas: 2-4 cifras clave con su periodo."""
    lis = "".join(f"<li>{escape(p)}</li>" for p in puntos if p)
    if lis:
        estilo()
        st.markdown(f"<div class='rr-resumen'><b>En resumen</b><ul>{lis}</ul></div>", unsafe_allow_html=True)


def pie_periodos(periodos):
    """Pie de todas las páginas: hasta qué periodo llega cada fuente."""
    if not periodos:
        return
    chips = "".join(f"<span>{escape(n)}: <b>{escape(p)}</b></span>" for n, p in periodos)
    st.markdown("<div class='rr-pie'>Datos actualizados hasta el último periodo publicado por cada fuente. "
                f"Cada cifra corresponde al periodo de su fuente:<br>{chips}</div>", unsafe_allow_html=True)


def lista(items):
    """['a', 'b', 'c'] -> 'a, b y c'."""
    items = [str(i) for i in items if i]
    return items[0] if len(items) == 1 else (", ".join(items[:-1]) + " y " + items[-1]) if items else ""
