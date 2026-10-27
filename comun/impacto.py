"""
impacto.py — Componentes visuales de más impacto, con el mismo estilo que graficos.py: tarjetas de cifra con minigráfico,
barras con deslizante de año dentro del gráfico (sin recargar la página), gráfico de mancuernas, áreas apiladas y
líneas con la etiqueta al final. Solo Altair y SVG: sin dependencias nuevas.
"""
from html import escape
from itertools import count

import altair as alt
import pandas as pd
import streamlit as st

from comun import graficos as g

MARINO, ORO = g.MARINO, g.ORO
TENUE = g.MARINO_CLARO  # extremo «de partida» de las mancuernas y trazos de apoyo
_ids = count()

CSS = """<style>
@keyframes im-sube{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
@keyframes im-traza{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}
@keyframes im-aparece{from{opacity:0}to{opacity:1}}
.im-fila{display:grid;grid-template-columns:repeat(auto-fit,minmax(175px,1fr));gap:0.9rem;margin:0.4rem 0 1.2rem 0}
.im-t{background:linear-gradient(160deg,#ffffff 0%,#fbf6e9 100%);border:1px solid #eadfbd;border-top:3px solid #d9ab42;border-radius:14px;
  padding:0.9rem 1.1rem 0.7rem 1.1rem;box-shadow:0 1px 2px rgba(0,20,90,.05),0 6px 18px rgba(0,20,90,.06);
  animation:im-sube .6s ease-out both}
.im-t-tit{color:#4a5585;font-size:0.82rem;line-height:1.25;min-height:2.05em}
.im-t-val{color:#00145a;font-size:2.15rem;font-weight:700;line-height:1.15;margin:0.1rem 0 0.25rem 0;letter-spacing:-0.02em}
.im-t-pie{display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;font-size:0.78rem;color:#4a5585;min-height:1.5em}
.im-pill{border-radius:999px;padding:0.05rem 0.55rem;font-weight:600;white-space:nowrap}
.im-pill.bueno{background:#00145a;color:#ffffff}
.im-pill.malo{background:#d9ab42;color:#00145a}
.im-pill.neutro{background:#eef0f8;color:#00145a}
.im-spark{width:100%;height:42px;display:block;margin-top:0.35rem;overflow:visible}
.im-spark .l{fill:none;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:1;animation:im-traza 1.4s .15s ease-out both}
.im-spark .a{animation:im-aparece 1.2s .5s ease-out both}
.im-spark .p{animation:im-aparece .4s 1.3s ease-out both}
.im-rango{display:flex;justify-content:space-between;color:#7a84ad;font-size:0.7rem;margin-top:0.1rem}
.im-t.im-doble{padding:0;display:flex;flex-direction:column}
.im-mitad{flex:1;display:grid;grid-template-columns:1.15fr 1fr;gap:0.5rem;align-items:center;padding:0.55rem 1rem}
.im-mitad+.im-mitad{border-top:1px solid #eadfbd}
.im-mitad .im-t-tit{min-height:0}
.im-mitad .im-t-val{font-size:1.65rem;margin:0.05rem 0 0.2rem 0}
.im-mitad .im-spark{height:38px;margin-top:0}
.im-lectura{border-left:6px solid #d9ab42;background:linear-gradient(90deg,#fbf6e9,#ffffff);border-radius:10px;padding:0.8rem 1.1rem;margin:0.4rem 0 1.2rem 0}
.im-lectura h4{margin:0 0 0.35rem 0;color:#00145a;font-size:1.05rem}
.im-lectura ul{margin:0.1rem 0 0 1.1rem;padding:0}
.im-lectura li{margin:0.2rem 0;line-height:1.45}
@media (prefers-reduced-motion:reduce){.im-t,.im-spark .l,.im-spark .a,.im-spark .p{animation:none;stroke-dashoffset:0}}
</style>"""


def estilo():
    st.markdown(CSS, unsafe_allow_html=True)


def _spark(valores, color):
    """Minigráfico SVG (línea que se traza, relleno degradado y punto final) de una lista de números."""
    v = [float(x) for x in valores if pd.notna(x)]
    if len(v) < 2:
        return ""
    ancho, alto, pad = 120.0, 36.0, 4.0
    lo, hi = min(v), max(v)
    rango = (hi - lo) or 1.0
    pts = [(pad + i * (ancho - 2 * pad) / (len(v) - 1), pad + (hi - x) / rango * (alto - 2 * pad)) for i, x in enumerate(v)]
    linea = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = linea + f" L{pts[-1][0]:.1f},{alto} L{pts[0][0]:.1f},{alto} Z"
    gid = f"im-g{next(_ids)}"
    return (f"<svg class='im-spark' viewBox='0 0 {ancho:.0f} {alto:.0f}' preserveAspectRatio='none' role='img' "
            "aria-label='Evolución de la serie'>"
            f"<defs><linearGradient id='{gid}' x1='0' y1='0' x2='0' y2='1'><stop offset='0' stop-color='{color}' stop-opacity='.28'/>"
            f"<stop offset='1' stop-color='{color}' stop-opacity='0'/></linearGradient></defs>"
            f"<path class='a' d='{area}' fill='url(#{gid})'/>"
            f"<path class='l' pathLength='1' d='{linea}' stroke='{color}'/>"
            f"<circle class='p' cx='{pts[-1][0]:.1f}' cy='{pts[-1][1]:.1f}' r='3.4' fill='{color}' stroke='#fff' stroke-width='1.5'/></svg>")


def _pie_y_color(it):
    """(pie con la variación y la nota, color del minigráfico) de una cifra."""
    clase = {True: "bueno", False: "malo"}.get(it.get("bueno"), "neutro")
    pie = ""
    if it.get("delta"):
        pie += f"<span class='im-pill {clase}'>{escape(it['delta'])}</span>"
    if it.get("nota"):
        pie += f"<span>{escape(it['nota'])}</span>"
    return pie, {True: MARINO, False: ORO}.get(it.get("bueno"), MARINO)


def _mitad(it):
    """Una mitad de tarjeta doble: rótulo, cifra y variación a la izquierda; minigráfico a la derecha."""
    pie, color = _pie_y_color(it)
    return (f"<div class='im-mitad'><div><div class='im-t-tit'>{escape(it['titulo'])}</div><div class='im-t-val'>{escape(it['valor'])}</div>"
            f"<div class='im-t-pie'>{pie}</div></div>{_spark(it.get('serie') or [], color)}</div>")


def tarjetas(items):
    """Fila de tarjetas de cifra. Cada item es un dict: titulo, valor (texto ya formateado), delta (texto, opcional),
    bueno (True/False/None: color de la variación, pastilla marino si mejora y dorada si empeora; la flecha y el signo van siempre, no solo el color), nota (texto tras
    la variación), serie (lista de números para el minigráfico), desde / hasta (rótulos bajo el minigráfico).
    Un item con `partes` (lista de dicts como los anteriores) es una tarjeta doble: ocupa el hueco de una y se divide por la
    mitad horizontal, una parte encima de otra (p. ej. hombres y mujeres)."""
    estilo()
    html = []
    for i, it in enumerate(items):
        if it.get("partes"):
            html.append(f"<div class='im-t im-doble' style='animation-delay:{i * 0.08:.2f}s'>{''.join(_mitad(p) for p in it['partes'])}</div>")
            continue
        pie, color = _pie_y_color(it)  # mejora: marino; empeora: dorado (la flecha y el signo van siempre)
        rango = ""
        if it.get("serie") is not None and it.get("desde") is not None:
            rango = f"<div class='im-rango'><span>{escape(str(it['desde']))}</span><span>{escape(str(it.get('hasta', '')))}</span></div>"
        html.append(f"<div class='im-t' style='animation-delay:{i * 0.08:.2f}s'><div class='im-t-tit'>{escape(it['titulo'])}</div>"
                    f"<div class='im-t-val'>{escape(it['valor'])}</div><div class='im-t-pie'>{pie}</div>"
                    f"{_spark(it.get('serie') if it.get('serie') is not None else [], color)}{rango}</div>")
    st.markdown(f"<div class='im-fila'>{''.join(html)}</div>", unsafe_allow_html=True)


def lectura(titulo, puntos):
    """Recuadro «Lo que dicen los datos»: frases calculadas a partir de las propias series (nunca texto fijo con cifras)."""
    estilo()
    lis = "".join(f"<li>{escape(p)}</li>" for p in puntos if p)
    if lis:
        st.markdown(f"<div class='im-lectura'><h4>{escape(titulo)}</h4><ul>{lis}</ul></div>", unsafe_allow_html=True)


def _num(x, d=1):
    """Número con signo y coma decimal: +0,5 / -1,2."""
    return f"{x:+.{d}f}".replace(".", ",")


def delta_pp(actual, previo, d=1):
    """'-0,5 p.p.' con signo y flecha (▲ sube, ▼ baja); None si falta alguno."""
    if previo is None or pd.isna(previo) or pd.isna(actual):
        return None
    dif = actual - previo
    if round(dif, d) == 0:
        return f"■ {g.es(0, d)} p.p."
    return f"{'▲' if dif > 0 else '▼'} {_num(dif, d)} p.p."


def delta_rel(actual, previo, d=1):
    """'+3,4 %' con signo y flecha, variación relativa."""
    if not previo or pd.isna(previo) or pd.isna(actual):
        return None
    dif = (actual / previo - 1) * 100
    flecha = "▲" if dif > 0 else "▼" if dif < 0 else "■"
    return f"{flecha} {_num(dif, d)} %"


# ------------------------------------------------------------------------------------------------ gráficos
def barras_anuales(df, cat, val, anyo, ref=None, fmt=",.1f", titulo_val=None, alto_fila=24, nombre_ref="España"):
    """Barras por categoría (p. ej. comunidad) con un deslizante de año DENTRO del gráfico: cambia al instante, sin recargar
    la página. df en formato largo (cat, anyo, val). `ref` = serie {año: valor} de referencia (p. ej. la media nacional): se
    dibuja como una barra más en azul marino y el resto va en dorado si supera la referencia de ese año y en marino suave si no.
    El puesto de cada barra se calcula antes, año a año, para que el ranking se reordene al mover el deslizante."""
    if df.empty:
        st.info("Sin datos en esta carga.")
        return
    d = df[[cat, anyo, val]].copy()
    d["_c"] = "igual"
    if ref is not None:
        r = pd.Series(ref)
        d["_c"] = ["mayor" if v > r.get(a, float("inf")) else "menor" for a, v in zip(d[anyo], d[val])]
        d = pd.concat([d, pd.DataFrame({cat: nombre_ref, anyo: r.index, val: r.values, "_c": "ref"})], ignore_index=True)
    d["_puesto"] = d.groupby(anyo)[val].rank(method="first", ascending=False).astype(int)
    anyos = sorted(d[anyo].unique())
    p = alt.param(name="anyo_sel", value=int(anyos[-1]),
                  bind=alt.binding_range(min=int(anyos[0]), max=int(anyos[-1]), step=1, name="Año: "))
    escala = alt.Scale(domain=["mayor", "menor", "ref", "igual"], range=[ORO, g.MARINO_SUAVE, MARINO, MARINO])
    base = alt.Chart(d).add_params(p).transform_filter(alt.datum[anyo] == p).encode(y=alt.Y("_puesto:O", axis=None, sort="ascending"))
    barras = base.mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, size=alto_fila * 0.62).encode(
        x=alt.X(f"{val}:Q", title=titulo_val, axis=alt.Axis(format=fmt), scale=alt.Scale(domain=[0, float(d[val].max()) * 1.12])),
        color=alt.Color("_c:N", scale=escala, legend=None),
        tooltip=[alt.Tooltip(f"{cat}:N", title=""), alt.Tooltip(f"{anyo}:O", title="Año"), alt.Tooltip(f"{val}:Q", format=fmt, title=titulo_val or val)])
    nombres = base.mark_text(align="right", dx=-8, fontSize=11, color=g.TEXTO_SUAVE).encode(x=alt.value(0), text=f"{cat}:N")
    txt = base.mark_text(align="left", dx=4, fontSize=11, color=g.TEXTO).encode(x=alt.X(f"{val}:Q"), text=alt.Text(f"{val}:Q", format=fmt))
    g.mostrar((barras + nombres + txt).properties(height=alto_fila * d[cat].nunique(), padding={"left": 120 if g.es_movil() else 150}))


def mancuernas(df, cat, v0, v1, e0, e1, fmt=",.1f", titulo=None, alto_fila=24, unidad="p.p."):
    """Gráfico de mancuernas: cada fila une el valor en el año de partida (`e0`, tenue) con el del año final (`e1`, marino),
    ordenado por el valor final, con la variación escrita al final de la barra."""
    if df.empty:
        st.info("Sin datos en esta carga.")
        return
    e0, e1 = (str(int(e)) if isinstance(e, (int, float)) and float(e).is_integer() else str(e) for e in (e0, e1))
    d = df[[cat, v0, v1]].dropna().copy()
    d["_dif"] = d[v1] - d[v0]
    d["_txt"] = [f"{_num(x)} {unidad}" for x in d["_dif"]]
    d["_max"] = d[[v0, v1]].max(axis=1)
    orden = d.sort_values(v1, ascending=False)[cat].tolist()
    y = alt.Y(f"{cat}:N", sort=orden, title=None, axis=alt.Axis(labelLimit=g._lim(260)))
    base = alt.Chart(d).encode(y=y)
    regla = base.mark_rule(strokeWidth=3, color="#c9d0e8").encode(x=alt.X(f"{v0}:Q", title=titulo, scale=alt.Scale(zero=False)), x2=f"{v1}:Q")
    p0 = base.mark_circle(size=90, color=TENUE, opacity=1).encode(
        x=f"{v0}:Q", tooltip=[alt.Tooltip(f"{cat}:N", title=""), alt.Tooltip(f"{v0}:Q", format=fmt, title=e0), alt.Tooltip(f"{v1}:Q", format=fmt, title=e1),
                              alt.Tooltip("_txt:N", title="Variación")])
    p1 = base.mark_circle(size=130, color=MARINO, opacity=1, stroke="#ffffff", strokeWidth=2).encode(
        x=f"{v1}:Q", tooltip=[alt.Tooltip(f"{cat}:N", title=""), alt.Tooltip(f"{v0}:Q", format=fmt, title=e0), alt.Tooltip(f"{v1}:Q", format=fmt, title=e1),
                              alt.Tooltip("_txt:N", title="Variación")])
    txt = base.mark_text(align="left", dx=10, fontSize=11, color=g.TEXTO).encode(x="_max:Q", text="_txt:N")
    # leyenda manual (dos extremos): un punto tenue (año de partida) y uno marino (año final)
    leyenda = pd.DataFrame({"e": [str(e0), str(e1)]})
    ley = alt.Chart(leyenda).mark_circle(size=90, opacity=1, clip=True).encode(
        x=alt.value(-60), y=alt.value(-60), color=alt.Color("e:N", scale=alt.Scale(domain=[str(e0), str(e1)], range=[TENUE, MARINO]), legend=alt.Legend(orient="top", title=None)))
    g.mostrar((regla + p0 + p1 + txt + ley).properties(height=alto_fila * len(d)))


def area_gradiente(df, x, y, fmt=",.0f", titulo_y=None, x_fmt="%Y", color=MARINO, alto=230):
    """Una serie en área con degradado, cruceta con el valor al pasar el ratón y el último punto marcado."""
    if df.empty:
        st.info("Sin datos en esta carga.")
        return
    grad = alt.Gradient(gradient="linear", stops=[alt.GradientStop(color=color + "55", offset=0), alt.GradientStop(color=color + "00", offset=1)],
                        x1=1, x2=1, y1=0, y2=1)
    base = alt.Chart(df).encode(x=alt.X(f"{x}:T", title=None, axis=alt.Axis(format=x_fmt, tickCount={"interval": "year", "step": 1})))
    area = base.mark_area(line={"color": color, "strokeWidth": 2.2}, color=grad).encode(y=alt.Y(f"{y}:Q", title=titulo_y, axis=alt.Axis(format=fmt)))
    sel = alt.selection_point(fields=[x], nearest=True, on="pointerover", empty=False, clear="pointerout")
    regla = base.mark_rule(color="#c3c2b7").encode(opacity=alt.condition(sel, alt.value(1), alt.value(0)),
                                                   tooltip=[alt.Tooltip(f"{x}:T", title="", format=x_fmt), alt.Tooltip(f"{y}:Q", format=fmt, title=titulo_y or y)]).add_params(sel)
    ultimo = base.transform_window(_n="row_number()", sort=[alt.SortField(x, order="descending")]).transform_filter("datum._n == 1").mark_point(
        size=90, filled=True, color=color, stroke="#ffffff", strokeWidth=2).encode(y=f"{y}:Q")
    g.mostrar((area + regla + ultimo).properties(height=alto))


def apiladas(df, x, serie, val, normalizar=True, orden_series=None, x_fmt="%Y", fmt=".0%", titulo_y=None, alto=280, colores=None, cols_leyenda=6, paso_x=1):
    """Áreas apiladas (por defecto al 100 %: cómo cambia el reparto, p. ej. la modalidad de la formación). df en formato largo.
    `colores`: lista de colores en el orden de las series (p. ej. una rampa de un solo tono para categorías ordenadas, como la edad)."""
    if df.empty:
        st.info("Sin datos en esta carga.")
        return
    series = orden_series or sorted(df[serie].dropna().unique().tolist())
    d = df.copy()
    tot = d.groupby(x)[val].transform("sum")
    d["_pct"] = d[val] / tot
    enc = dict(x=alt.X(f"{x}:T", title=None, axis=alt.Axis(format=x_fmt, tickCount={"interval": "year", "step": paso_x})),
               y=alt.Y(f"{'_pct' if normalizar else val}:Q", title=titulo_y, stack=True, axis=alt.Axis(format=fmt if normalizar else ",.0f")),
               color=alt.Color(f"{serie}:N", scale=alt.Scale(domain=series, range=colores or g.colores(len(series))), sort=series,
                               legend=alt.Legend(orient="top", title=None, columns=cols_leyenda, labelLimit=140)),
               order=alt.Order(f"{serie}:N", sort="ascending"),
               tooltip=[alt.Tooltip(f"{x}:T", title="", format=x_fmt), alt.Tooltip(f"{serie}:N", title=""),
                        alt.Tooltip("_pct:Q", format=".1%", title="% del total"), alt.Tooltip(f"{val}:Q", format=",.0f", title="Valor")])
    g.mostrar(alt.Chart(d).mark_area(opacity=0.95, stroke="#ffffff", strokeWidth=1.5).encode(**enc).properties(height=alto))


def _separar(valores, minimo):
    """Posiciones de las etiquetas finales: se apartan lo justo para que no se pisen (se mantiene el orden)."""
    orden = sorted(range(len(valores)), key=lambda i: valores[i])
    pos = [valores[i] for i in orden]
    for _ in range(40):
        movido = False
        for k in range(1, len(pos)):
            if pos[k] - pos[k - 1] < minimo:
                falta = (minimo - (pos[k] - pos[k - 1])) / 2
                pos[k - 1] -= falta
                pos[k] += falta
                movido = True
        if not movido:
            break
    out = [0.0] * len(valores)
    for k, i in enumerate(orden):
        out[i] = pos[k]
    return out


def lineas_etiquetadas(df, x, y, serie, fmt=",.1f", x_fmt="%Y", orden_series=None, cero=False, alto=300, titulo_y=None, resaltar=None):
    """Líneas con el valor al final de cada una (el punto final lleva el color de la serie; el texto, tinta normal) y cruceta
    con todos los valores. Si dos finales están muy cerca, sus etiquetas se separan. `resaltar`: serie que va en dorado y
    más gruesa (p. ej. el total o la referencia); el resto, en la paleta."""
    if df.empty:
        st.info("Sin datos en esta carga.")
        return
    series = orden_series or sorted(df[serie].dropna().unique().tolist())
    otros = iter([c for c in g.PALETA if c != ORO])
    rango = [ORO if s == resaltar else next(otros) for s in series]
    color = alt.Color(f"{serie}:N", scale=alt.Scale(domain=series, range=rango), legend=alt.Legend(orient="top", title=None))
    base = alt.Chart(df).encode(x=alt.X(f"{x}:T", title=None, axis=alt.Axis(format=x_fmt, tickCount={"interval": "year", "step": 1})))
    enc_y = alt.Y(f"{y}:Q", title=titulo_y, axis=alt.Axis(format=fmt), scale=alt.Scale(zero=cero))
    grosor = alt.condition(alt.datum[serie] == (resaltar or ""), alt.value(3.2), alt.value(2))
    linea = base.mark_line(strokeCap="round", strokeJoin="round").encode(y=enc_y, color=color, strokeWidth=grosor)
    fin = df.sort_values(x).groupby(serie, as_index=False).tail(1).reset_index(drop=True)
    fin["_ylab"] = _separar(fin[y].astype(float).tolist(), (df[y].max() - df[y].min()) * 0.06)
    ult = alt.Chart(fin).encode(x=alt.X(f"{x}:T"))
    punto = ult.mark_point(size=70, filled=True, stroke="#ffffff", strokeWidth=2).encode(y=alt.Y(f"{y}:Q"), color=color)
    etiqueta = ult.mark_text(align="left", dx=10, fontSize=11, color=g.TEXTO).encode(y=alt.Y("_ylab:Q"), text=alt.Text(f"{y}:Q", format=fmt))
    sel = alt.selection_point(fields=[x], nearest=True, on="pointerover", empty=False, clear="pointerout")
    ancho = df.pivot_table(index=x, columns=serie, values=y, aggfunc="first").reset_index()
    tt = [alt.Tooltip(f"{x}:T", title="", format=x_fmt)] + [alt.Tooltip(f"{s}:Q", format=fmt) for s in series if s in ancho.columns]
    regla = alt.Chart(ancho).mark_rule(color="#c3c2b7").encode(x=alt.X(f"{x}:T"), opacity=alt.condition(sel, alt.value(1), alt.value(0)),
                                                                tooltip=tt).add_params(sel)
    g.mostrar((linea + punto + etiqueta + regla).properties(height=alto, padding={"right": 46}))


def divergentes(df, cat, val, centro, fmt="+.1f", titulo=None, alto_fila=24):
    """Barras que parten de una referencia (p. ej. la media nacional): a la derecha, por encima (dorado); a la izquierda, por
    debajo (marino suave). `val` ya es la diferencia respecto a `centro`; el título del eje dice la referencia."""
    if df.empty:
        st.info("Sin datos en esta carga.")
        return
    d = df[[cat, val]].copy()
    d["_c"] = ["mayor" if v > 0 else "menor" for v in d[val]]
    orden = d.sort_values(val, ascending=False)[cat].tolist()
    lim = float(d[val].abs().max()) * 1.18
    base = alt.Chart(d).encode(y=alt.Y(f"{cat}:N", sort=orden, title=None, axis=alt.Axis(labelLimit=g._lim(260), orient="left", labelPadding=6)))
    barras = base.mark_bar(cornerRadius=3, size=alto_fila * 0.62).encode(
        x=alt.X(f"{val}:Q", title=titulo, scale=alt.Scale(domain=[-lim, lim]), axis=alt.Axis(format=fmt)),
        color=alt.Color("_c:N", scale=alt.Scale(domain=["mayor", "menor"], range=[ORO, g.MARINO_SUAVE]), legend=None),
        tooltip=[alt.Tooltip(f"{cat}:N", title=""), alt.Tooltip(f"{val}:Q", format=fmt, title=titulo or val)])
    txt_pos = base.transform_filter(alt.datum[val] >= 0).mark_text(fontSize=11, color=g.TEXTO, dx=4, align="left").encode(
        x=alt.X(f"{val}:Q"), text=alt.Text(f"{val}:Q", format=fmt))
    txt_neg = base.transform_filter(alt.datum[val] < 0).mark_text(fontSize=11, color=g.TEXTO, dx=-4, align="right").encode(
        x=alt.X(f"{val}:Q"), text=alt.Text(f"{val}:Q", format=fmt))
    txt = txt_pos + txt_neg
    eje = alt.Chart(pd.DataFrame({"c": [0]})).mark_rule(color=g.TEXTO, strokeWidth=1.2).encode(x="c:Q")
    g.mostrar((barras + eje + txt).properties(height=alto_fila * len(d)))


def _rosco(df, cat, val, orden=None, colores=None, centro=None, sub=None, fmt=".1%", alto=300):
    """Gráfico de rosco (donut) de reparto: cada categoría con su % del total, el dato principal escrito en el centro. Devuelve el
    gráfico Altair (mostrar() lo pinta). Solo para repartos de pocas categorías (hasta 5-6): más, mejor barras."""
    d = df[[cat, val]].dropna().copy()
    d = d[d[val] > 0]
    d["_pct"] = d[val] / d[val].sum()
    orden = [c for c in (orden or d[cat].tolist()) if c in set(d[cat])]
    d["_ord"] = d[cat].map({c: i for i, c in enumerate(orden)})
    escala = alt.Scale(domain=orden, range=(colores or g.colores(len(orden)))[:len(orden)])
    arcos = alt.Chart(d).mark_arc(innerRadius=alto * 0.22, outerRadius=alto * 0.36, stroke="#ffffff", strokeWidth=2.5, cornerRadius=3).encode(
        theta=alt.Theta(f"{val}:Q", stack=True), order=alt.Order("_ord:Q"),
        color=alt.Color(f"{cat}:N", scale=escala, sort=orden, legend=alt.Legend(orient="bottom", title=None, columns=2, labelLimit=170)),
        tooltip=[alt.Tooltip(f"{cat}:N", title=""), alt.Tooltip("_pct:Q", format=fmt, title="% del total"), alt.Tooltip(f"{val}:Q", format=",.0f", title="Valor")])
    capas = arcos
    if centro:
        capas += alt.Chart(pd.DataFrame({"t": [centro]})).mark_text(fontSize=alto * 0.11, fontWeight="bold", color=g.TEXTO, dy=-4 if sub else 0).encode(text="t:N")
    if sub:
        capas += alt.Chart(pd.DataFrame({"t": [sub]})).mark_text(fontSize=10.5, color=g.TEXTO_SUAVE, dy=alto * 0.085).encode(text="t:N")
    return capas.properties(height=alto)


def rosco(df, cat, val, **kw):
    """Rosco de reparto (ver _rosco). Con df vacío avisa en vez de pintar un gráfico vacío."""
    if df.empty or not (df[val] > 0).any():
        st.info("Sin datos en esta carga.")
        return
    g.mostrar(_rosco(df, cat, val, **kw))
