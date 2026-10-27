"""
graficos.py — Gráficos Altair con un mismo estilo: barras horizontales, líneas y columnas.

Colores de marca (Fundación Gi Group): predominan el azul marino y el dorado, sobre blanco. Los otros dos dorados sirven de
rampa de intensidad y de fondos suaves, no como series distintas (entre sí no se distinguen: ΔE ≈ 5). Para más de dos series
hay cuatro tonos derivados de los dos principales (marino suave, dorado oscuro, marino claro). Orden fijo, nunca rotado. Con
más de 6 series la paleta se repite: la leyenda y el tooltip las distinguen. Números con formato español (1.234,5).
Textos en azul marino. Validado con validate_palette.js (las 6 series): pasa la separación entre series, también con daltonismo;
NO pasa la banda de luminosidad ni el croma mínimo (el marino es muy oscuro y los tonos derivados, apagados: es propio de la
marca), y el dorado tiene poco contraste sobre blanco (2,1:1). Por eso se limita a 4-5 series por gráfico y todos llevan
etiquetas visibles, leyenda y tooltip.
"""
import altair as alt
import pandas as pd
import streamlit as st

MARINO, ORO, ORO_CLARO, ORO_PALIDO, BLANCO = "#00145a", "#d9ab42", "#e1bc68", "#e8cd8e", "#ffffff"  # paleta de marca
MARINO_SUAVE, ORO_OSCURO, MARINO_CLARO = "#6b79b0", "#9a7312", "#aab3d8"  # derivados: más de dos series, «por debajo de la media»
FONDO_ORO, BORDE_ORO = "#fbf6e9", "#eadfbd"  # fondos y bordes muy suaves de tarjetas y recuadros (dorado al 15-25 %)
C1, C2, C3 = MARINO, ORO, MARINO_SUAVE
PALETA = [MARINO, ORO, MARINO_SUAVE, ORO_OSCURO, MARINO_CLARO, ORO_PALIDO]
ESCALA = ("#e6e9f4", MARINO)  # magnitud (mapas y mapas de calor): del blanco azulado al azul marino
RAMPA = ["#dfe3f1", MARINO_CLARO, MARINO_SUAVE, "#2f3f85", MARINO]  # categorías ordenadas (edad, estudios): 5 pasos del marino
# semáforo de la tabla comparativa del Dashboard 2 (petición expresa: verde y rojo, fuera de la paleta de marca) y gris de la media
VERDE, ROJO, GRIS_MEDIA = "#7cc48a", "#ec8f86", "#d9d9d9"
TEXTO, TEXTO_SUAVE = MARINO, "#4a5585"  # azul marino y su versión atenuada (ejes, notas)


def es_movil():
    """True si se abre desde un móvil (por el navegador que lo pide): ejes y tablas de calor más compactos."""
    try:
        ua = st.context.headers.get("User-Agent", "") or ""
    except Exception:
        return False
    return any(k in ua for k in ("Mobi", "Android", "iPhone"))


def _lim(normal):
    """Ancho máximo de las etiquetas de los ejes (en el móvil se recortan para dejar sitio a las barras)."""
    return 110 if es_movil() else normal


def colores(n):
    """n colores en orden fijo; si hay más de 12 series se repite la paleta (la leyenda y el tooltip las distinguen)."""
    return [PALETA[i % len(PALETA)] for i in range(n)]
LOCALE = {"number": {"decimal": ",", "thousands": ".", "grouping": [3], "currency": ["", " €"]},
          "time": {"dateTime": "%A, %e de %B de %Y, %X", "date": "%d/%m/%Y", "time": "%H:%M:%S",
                   "periods": ["AM", "PM"],
                   "days": ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"],
                   "shortDays": ["dom", "lun", "mar", "mié", "jue", "vie", "sáb"],
                   "months": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
                              "octubre", "noviembre", "diciembre"],
                   "shortMonths": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]}}


def _cfg(ch):
    return (ch.configure(locale=LOCALE, font="system-ui, -apple-system, Segoe UI, sans-serif")
              .configure_axis(grid=True, gridColor="#e1e0d966", domainColor="#c3c2b7", labelColor=TEXTO_SUAVE,
                              titleColor=TEXTO_SUAVE, labelFontSize=11, titleFontSize=11, tickColor="#c3c2b7")
              .configure_view(stroke=None)
              .configure_legend(orient="top", title=None, labelFontSize=12, symbolType="square", labelLimit=_lim(320), labelColor=TEXTO,
                                columns=6))


def top(df, col, defecto, clave, asc=False):
    """Los `defecto` primeros por `col`, con un selector para ver más o todos (los gráficos no se limitan a unos pocos)."""
    n = len(df)
    if n <= defecto:
        return df.sort_values(col, ascending=asc)
    opciones = sorted({defecto, *[x for x in (10, 20, 30, 50) if x < n]}) + ["Todos"]
    elegido = st.select_slider("Mostrar", opciones, value=defecto, key=f"top_{clave}")
    d = df.sort_values(col, ascending=asc)
    return d if elegido == "Todos" else d.head(elegido)


def mostrar(ch):
    st.altair_chart(_cfg(ch), width="stretch", theme=None)


def barras(df, cat, val, fmt=",.0f", color=None, resaltar=None, tooltip=None, orden_desc=True, alto_fila=22, titulo_val=None,
           orden_cat=None):
    """Barras horizontales ordenadas. resaltar: serie booleana -> dorado (p. ej. 'por encima de la media').
    orden_cat: orden fijo de las categorías (p. ej. tramos de tamaño), en lugar de ordenar por el valor."""
    if df.empty:
        st.info("Sin datos en esta carga.")
        return
    d = df.copy()
    d["_color"] = C1
    if resaltar is not None:
        d.loc[resaltar.values, "_color"] = C2
    # orden explícito (con varias capas, sort="-x" no siempre se respeta y salen por orden alfabético)
    orden = orden_cat or list(dict.fromkeys(d.sort_values(val, ascending=not orden_desc)[cat].tolist()))
    tt = tooltip or [alt.Tooltip(f"{cat}:N", title=""), alt.Tooltip(f"{val}:Q", format=fmt, title=titulo_val or val)]
    base = alt.Chart(d).encode(y=alt.Y(f"{cat}:N", sort=orden, title=None, axis=alt.Axis(labelLimit=_lim(260))),
                               x=alt.X(f"{val}:Q", title=titulo_val, axis=alt.Axis(format=fmt)))
    barras_ = base.mark_bar(cornerRadiusEnd=4, height=max(8, alto_fila - 8)).encode(
        color=alt.Color("_color:N", scale=None), tooltip=tt)
    # la cifra va al final de cada barra positiva; en las negativas, junto al cero
    txt = dict(fontSize=11, color=TEXTO)
    pos = base.transform_filter(f"datum['{val}'] >= 0").mark_text(align="left", dx=4, **txt).encode(text=alt.Text(f"{val}:Q", format=fmt))
    neg = base.transform_filter(f"datum['{val}'] < 0").mark_text(align="left", dx=4, **txt).encode(
        x=alt.datum(0), text=alt.Text(f"{val}:Q", format=fmt))  # junto al eje del cero, sin tapar las etiquetas
    mostrar((barras_ + pos + neg).properties(height=max(120, alto_fila * len(d))))


def dispersion(df, x, y, etiqueta, ref_x=None, ref_y=None, resaltar=None, fmt_x=",.1f", fmt_y=",.1f", titulo_x=None, titulo_y=None,
               tamano=None, alto=420, etiquetar_todos=False):
    """Puntos con líneas de referencia (p. ej. la media de España) que dividen el gráfico en cuadrantes.
    resaltar: columna booleana -> dorado; el resto en azul marino. tamano: columna que da el tamaño del punto."""
    if df.empty:
        st.info("Sin datos en esta carga.")
        return
    d = df.copy()
    d["_color"] = C1
    if resaltar is not None:
        d.loc[d[resaltar].astype(bool).values, "_color"] = C2
    tt = [alt.Tooltip(f"{etiqueta}:N", title=""), alt.Tooltip(f"{x}:Q", format=fmt_x, title=titulo_x or x),
          alt.Tooltip(f"{y}:Q", format=fmt_y, title=titulo_y or y)]
    enc = dict(x=alt.X(f"{x}:Q", title=titulo_x, axis=alt.Axis(format=fmt_x), scale=alt.Scale(zero=False)),
               y=alt.Y(f"{y}:Q", title=titulo_y, axis=alt.Axis(format=fmt_y), scale=alt.Scale(zero=False)),
               color=alt.Color("_color:N", scale=None), tooltip=tt)
    if tamano:
        enc["size"] = alt.Size(f"{tamano}:Q", legend=None, scale=alt.Scale(range=[40, 900]))
        tt.append(alt.Tooltip(f"{tamano}:Q", format=",.0f", title=tamano))
    capas = alt.Chart(d).mark_circle(opacity=0.8, stroke="#ffffff", strokeWidth=1, size=90).encode(**enc)
    if ref_x is not None:
        capas += alt.Chart(pd.DataFrame({"v": [ref_x]})).mark_rule(color=TEXTO_SUAVE, strokeDash=[4, 4]).encode(x="v:Q")
    if ref_y is not None:
        capas += alt.Chart(pd.DataFrame({"v": [ref_y]})).mark_rule(color=TEXTO_SUAVE, strokeDash=[4, 4]).encode(y="v:Q")
    if not es_movil():  # nombre junto a los puntos resaltados (o junto a todos, si son pocos)
        capas += alt.Chart(d if etiquetar_todos else d[d["_color"] == C2]).mark_text(align="left", dx=7, fontSize=10, color=TEXTO).encode(
            x=f"{x}:Q", y=f"{y}:Q", text=f"{etiqueta}:N")
    mostrar(capas.properties(height=alto))


def barras_grupo(df, cat, serie, val, fmt=",.0f", orden_series=None, alto_fila=30, titulo_val=None, orden_cat=None):
    """Barras horizontales agrupadas (p. ej. hombres / mujeres). `orden_cat`: orden fijo de las categorías (p. ej. tramos de tamaño)."""
    if df.empty:
        st.info("Sin datos en esta carga.")
        return
    series = orden_series or sorted(df[serie].dropna().unique().tolist())
    ch = alt.Chart(df).mark_bar(cornerRadiusEnd=3).encode(
        y=alt.Y(f"{cat}:N", title=None, sort=orden_cat or "-x", axis=alt.Axis(labelLimit=_lim(260))),
        yOffset=alt.YOffset(f"{serie}:N", sort=series),
        x=alt.X(f"{val}:Q", title=titulo_val, axis=alt.Axis(format=fmt)),
        color=alt.Color(f"{serie}:N", scale=alt.Scale(domain=series, range=colores(len(series)))),
        tooltip=[alt.Tooltip(f"{cat}:N", title=""), alt.Tooltip(f"{serie}:N", title=""), alt.Tooltip(f"{val}:Q", format=fmt, title=titulo_val or val)])
    mostrar(ch.properties(height=max(140, alto_fila * df[cat].nunique())))


def lineas(df, x, y, serie=None, fmt=",.0f", x_tipo="T", x_fmt="%b %Y", orden_series=None, cero=False, alto=260, titulo_y=None,
           orden_x=None):
    """Líneas con cruceta: al pasar el ratón muestra todos los valores de esa fecha. `orden_x`: orden de un eje no temporal
    (p. ej. los meses)."""
    if df.empty:
        st.info("Sin datos en esta carga.")
        return
    series = orden_series or (sorted(df[serie].dropna().unique().tolist()) if serie else None)
    if x_tipo == "O" and orden_x is None:  # eje ordinal (p. ej. años): en orden, no en el de las filas
        orden_x = sorted(df[x].dropna().unique().tolist())
    enc_x = alt.X(f"{x}:{x_tipo}", title=None, sort=orden_x,
                  axis=alt.Axis(format=x_fmt) if x_tipo == "T" else alt.Axis(labelAngle=0, labelOverlap="greedy"))
    enc_y = alt.Y(f"{y}:Q", title=titulo_y, axis=alt.Axis(format=fmt), scale=alt.Scale(zero=cero))
    color = alt.Color(f"{serie}:N", scale=alt.Scale(domain=series, range=colores(len(series)))) if serie else alt.value(C1)
    base = alt.Chart(df).encode(x=enc_x)
    linea = base.mark_line(strokeWidth=2).encode(y=enc_y, color=color)
    sel = alt.selection_point(fields=[x], nearest=True, on="pointerover", empty=False, clear="pointerout")
    tt = [alt.Tooltip(f"{x}:{x_tipo}", title="", format=x_fmt if x_tipo == "T" else "")]
    if serie:
        ancho = df.pivot_table(index=x, columns=serie, values=y, aggfunc="first").reset_index()
        tt += [alt.Tooltip(f"{s}:Q", format=fmt) for s in series if s in ancho.columns]
        regla = alt.Chart(ancho).mark_rule(color="#c3c2b7").encode(x=enc_x, opacity=alt.condition(sel, alt.value(1), alt.value(0)),
                                                                     tooltip=tt).add_params(sel)
    else:
        tt.append(alt.Tooltip(f"{y}:Q", format=fmt, title=titulo_y or y))
        regla = base.mark_rule(color="#c3c2b7").encode(opacity=alt.condition(sel, alt.value(1), alt.value(0)), tooltip=tt).add_params(sel)
    puntos = base.mark_point(size=60, filled=True).encode(y=enc_y, color=color, opacity=alt.condition(sel, alt.value(1), alt.value(0)))
    mostrar((linea + regla + puntos).properties(height=alto))


def columnas(df, cat, val, serie=None, fmt=",.0f", orden_cat=None, orden_series=None, alto=240, titulo_val=None):
    if df.empty:
        st.info("Sin datos en esta carga.")
        return
    series = orden_series or (sorted(df[serie].dropna().unique().tolist()) if serie else None)
    enc = dict(x=alt.X(f"{cat}:N", sort=orden_cat, title=None, axis=alt.Axis(labelAngle=0)),
               y=alt.Y(f"{val}:Q", title=titulo_val, axis=alt.Axis(format=fmt)),
               tooltip=[alt.Tooltip(f"{cat}:N", title="")] + ([alt.Tooltip(f"{serie}:N", title="")] if serie else [])
                       + [alt.Tooltip(f"{val}:Q", format=fmt, title=titulo_val or val)])
    if serie:
        enc.update(xOffset=alt.XOffset(f"{serie}:N", sort=series),
                   color=alt.Color(f"{serie}:N", scale=alt.Scale(domain=series, range=colores(len(series)))))
    else:
        enc.update(color=alt.value(C1))
    mostrar(alt.Chart(df).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(**enc).properties(height=alto))


def tabla(df, nombre_fichero, formatos=None):
    """Tabla con descarga en CSV (punto y coma, para Excel en español)."""
    with st.expander("Ver tabla y descargar"):
        st.dataframe(df, width="stretch", hide_index=True, column_config=formatos)
        st.download_button("Descargar CSV", df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                           file_name=f"{nombre_fichero}.csv", mime="text/csv")


def es(v, d=0, sufijo=""):
    """Número con formato español."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "–"
    s = f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s + sufijo


def pct(v, d=1):
    return es(v, d, " %")


def sig(v, d=1):
    return "–" if v is None or pd.isna(v) else ("+" if v > 0 else "") + es(v, d, " %")


MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
MESES_L = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def mes(f):
    f = pd.Timestamp(f)
    return f"{MESES[f.month - 1]} {f.year}"


def trim(f):
    f = pd.Timestamp(f)
    return f"T{(f.month - 1) // 3 + 1} {f.year}"


def corto(s):
    """Nombres cortos y uniformes de sectores y territorios ('Navarra (C. Foral de)', 'Navarra, Comunidad Foral de' -> 'Navarra';
    'Palmas (las)', 'Palmas, Las' -> 'Las Palmas'; 'Castilla - La Mancha' -> 'Castilla-La Mancha')."""
    import re
    s = str(s or "")
    s = re.sub(r"\s*\(excepto[^)]*\)", "", s, flags=re.I)
    s = re.sub(r";.*$", "", s)
    # territorio con la coletilla entre paréntesis o tras una coma: 'Asturias (Principado de)', 'Madrid, Comunidad de'
    s = re.sub(r"\s*\((C\. Foral|Comunidad Foral|Comunidad|Principado|Región)( de)?\)$", "", s, flags=re.I)
    s = re.sub(r", (Comunidad Foral|Comunidad|Principado|Región) de$", "", s)
    # artículo detrás: 'Balears (Illes)', 'Palmas (las)', 'Coruña (a)', 'Rioja, La', 'Balears, Illes'
    m = re.match(r"^(.+?)\s*\((Illes|La|Las|Los|A|Les|El|O)\)$", s, flags=re.I) or re.match(r"^(.+), (Illes|La|Las|Los|A|Les|El|O)$", s, flags=re.I)
    if m:
        s = f"{m.group(2).capitalize()} {m.group(1)}"
    s = re.sub(r"Castilla\s*-\s*La Mancha", "Castilla-La Mancha", s, flags=re.I)
    s = {"Rioja": "La Rioja", "Baleares": "Illes Balears", "Balears": "Illes Balears"}.get(s.strip(), s)
    return s.strip()


def bonito(s):
    """'MADRID (COMUNIDAD DE)' -> 'Madrid (comunidad de)'; 'ARABA/ÁLAVA' -> 'Araba/Álava'; deja igual lo que ya está en minúsculas."""
    import re
    s = str(s or "").strip()
    if s != s.upper():
        return s
    s = " ".join(w if w in ("de", "del", "la", "las", "los", "y") else w.capitalize() for w in s.lower().split())
    return re.sub(r"([/-])(\w)", lambda m: m.group(1) + m.group(2).upper(), s)


# Mapa de comunidades en mosaico (una casilla por CCAA en su posición aproximada): no necesita ficheros externos
# y se lee mejor que un mapa real para comparar comunidades pequeñas (La Rioja, Cantabria) con las grandes.
MOSAICO = {"C12": (0, 0, "GAL"), "C03": (1, 0, "AST"), "C06": (2, 0, "CNT"), "C16": (3, 0, "PV"), "C15": (4, 0, "NAV"),
           "C07": (1, 1, "CyL"), "C17": (3, 1, "RIO"), "C02": (4, 1, "ARA"), "C09": (5, 1, "CAT"),
           "C11": (1, 2, "EXT"), "C13": (2, 2, "MAD"), "C08": (3, 2, "CLM"), "C10": (4, 2, "VAL"), "C04": (6, 2, "BAL"),
           "C01": (2, 3, "AND"), "C14": (3, 3, "MUR"),
           "C05": (0, 4, "CAN"), "C18": (2, 4, "CEU"), "C19": (3, 4, "MEL"), "C1819": (2, 4, "C+M")}


@st.cache_data
def _contornos():
    import json
    from pathlib import Path
    return json.loads((Path(__file__).parent / "recursos" / "ccaa.geojson").read_text())["features"]


def mapa_ccaa(df, val, fmt=",.1f", titulo=None, clave=None, nombre="nombre", escala=ESCALA):
    """Mapa de CCAA coloreado por `val` (df con territorio_id y `nombre`): geográfico por defecto, o en mosaico si
    st.session_state["vista_mapa"] == "Mosaico" (ya no hay selector en pantalla). Con `clave`, permite hacer clic en una comunidad y devuelve su territorio_id (o None)."""
    d = df[df.territorio_id.isin(MOSAICO)].dropna(subset=[val]).copy()
    if d.empty:
        st.info("Sin datos por comunidad en esta carga.")
        return None
    if st.session_state.get("vista_mapa", "Geográfico") == "Geográfico":
        return _mapa_geo(d, val, fmt, titulo, clave, nombre, escala)
    d["x"] = d.territorio_id.map(lambda k: MOSAICO[k][0])
    d["y"] = d.territorio_id.map(lambda k: MOSAICO[k][1])
    d["abr"] = d.territorio_id.map(lambda k: MOSAICO[k][2])
    d["Comunidad"] = d[nombre].map(corto)
    medio = (d[val].min() + d[val].max()) / 2
    sel = alt.selection_point(fields=["territorio_id"], name="ccaa") if clave else None
    base = alt.Chart(d).encode(x=alt.X("x:O", axis=None), y=alt.Y("y:O", axis=None))
    casillas = base.mark_rect(cornerRadius=6, stroke="white", strokeWidth=3).encode(
        color=alt.Color(f"{val}:Q", scale=escala_c, title=titulo, legend=alt.Legend(orient="bottom", format=fmt)),
        tooltip=[alt.Tooltip("Comunidad:N"), alt.Tooltip(f"{val}:Q", format=fmt, title=titulo or val)])
    if sel is not None:
        casillas = casillas.add_params(sel).encode(opacity=alt.condition(sel, alt.value(1), alt.value(0.45)))
    etiqueta = alt.condition(f"datum['{val}'] > {medio}", alt.value("white"), alt.value(TEXTO))
    abr = base.mark_text(dy=-8, fontSize=12, fontWeight="bold").encode(text="abr:N", color=etiqueta)
    cifra = base.mark_text(dy=9, fontSize=11).encode(text=alt.Text(f"{val}:Q", format=fmt), color=etiqueta)
    ch = (casillas + abr + cifra).properties(height=340)
    if not clave:
        mostrar(ch)
        return None
    ev = st.altair_chart(_cfg(ch), width="stretch", theme=None, on_select="rerun", key=clave, selection_mode="ccaa")
    pts = (ev or {}).get("selection", {}).get("ccaa") or []
    return pts[0].get("territorio_id") if pts else None


def mapa_calor(df, fila, columna, val, fmt=",.1f", orden_filas=None, orden_cols=None, titulo=None, escala=ESCALA,
               centro=None, recorte_movil=True):
    """Tabla de calor (p. ej. sector × año) con la cifra en cada celda. Con `centro` la escala es divergente: el primer color
    por debajo del centro, blanco en el centro y el segundo por encima (p. ej. índice con media 100)."""
    if df.empty:
        st.info("Sin datos en esta carga.")
        return
    if es_movil() and recorte_movil:  # en el móvil, solo las últimas columnas (p. ej. los 4 últimos años) para que se lean las cifras
        cols = orden_cols or sorted(df[columna].dropna().unique().tolist())
        if len(cols) > 4:
            cols = cols[-4:]
            df = df[df[columna].isin(cols)]
            st.caption("En el móvil se muestran las 4 últimas columnas; en el ordenador se ven todas.")
        orden_cols = cols
    medio = df[val].min() + 0.55 * (df[val].max() - df[val].min())  # a partir de aquí la celda es oscura: texto blanco
    if centro is not None:
        lejos = max(centro - df[val].min(), df[val].max() - centro) or 1
        escala_c = alt.Scale(domain=[centro - lejos, centro, centro + lejos], range=[escala[0], BLANCO, escala[1]])
        oscuro = f"abs(datum['{val}'] - {centro}) > {lejos * 0.55}"
    else:
        escala_c = alt.Scale(range=list(escala))
        oscuro = f"datum['{val}'] > {medio}"
    base = alt.Chart(df).encode(x=alt.X(f"{columna}:O", sort=orden_cols, title=None, axis=alt.Axis(orient="top", labelAngle=0)),
                                y=alt.Y(f"{fila}:N", sort=orden_filas, title=None, axis=alt.Axis(labelLimit=_lim(320))))
    rect = base.mark_rect(stroke="white", strokeWidth=1.5).encode(
        color=alt.Color(f"{val}:Q", scale=escala_c, title=titulo, legend=alt.Legend(orient="bottom", format=fmt)),
        tooltip=[alt.Tooltip(f"{fila}:N", title=""), alt.Tooltip(f"{columna}:O", title=""), alt.Tooltip(f"{val}:Q", format=fmt, title=titulo or val)])
    txt = base.mark_text(fontSize=8 if es_movil() and not recorte_movil else 11).encode(text=alt.Text(f"{val}:Q", format=fmt),
                                             color=alt.condition(oscuro, alt.value("white"), alt.value(TEXTO)))
    mostrar((rect + txt).properties(height=max(160, 26 * df[fila].nunique())))


def _mapa_geo(d, val, fmt, titulo, clave, nombre, escala):
    """Mapa geográfico (contornos simplificados; Canarias desplazada junto a la península)."""
    d = d.assign(Comunidad=d[nombre].map(corto))[["territorio_id", "Comunidad", val]]
    fondo = alt.Chart(alt.Data(values=_contornos())).mark_geoshape(fill="#eef1f8", stroke="white", strokeWidth=0.8)
    sel = alt.selection_point(fields=["territorio_id"], name="ccaa") if clave else None
    capa = (alt.Chart(alt.Data(values=_contornos()))
            .transform_calculate(territorio_id="datum.properties.territorio_id")
            .transform_lookup(lookup="territorio_id", from_=alt.LookupData(d, "territorio_id", ["Comunidad", val]))
            .mark_geoshape(stroke="white", strokeWidth=0.8)
            .encode(color=alt.Color(f"{val}:Q", scale=alt.Scale(range=list(escala)), title=titulo,
                                    legend=alt.Legend(orient="bottom", format=fmt)),
                    tooltip=[alt.Tooltip("Comunidad:N"), alt.Tooltip(f"{val}:Q", format=fmt, title=titulo or val)]))
    if sel is not None:
        capa = capa.add_params(sel).encode(opacity=alt.condition(sel, alt.value(1), alt.value(0.45)))
    ch = (fondo + capa).project(type="mercator").properties(height=360)
    if not clave:
        mostrar(ch)
        return None
    ev = st.altair_chart(_cfg(ch), width="stretch", theme=None, on_select="rerun", key=clave, selection_mode="ccaa")
    pts = (ev or {}).get("selection", {}).get("ccaa") or []
    return pts[0].get("territorio_id") if pts else None


def _mezcla(c1, c2, t):
    """Color intermedio entre dos #rrggbb (t = 0: c1; t = 1: c2)."""
    a, b = [[int(c[i:i + 2], 16) for i in (1, 3, 5)] for c in (c1, c2)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def tabla_semaforo(df, nombre, ref, bajo_es_bueno=()):
    """Tabla (Styler) con mapa de calor por columna respecto a una fila de referencia (p. ej. la media de España): la fila de
    referencia va en gris y negrita; el resto, de blanco a verde si está mejor que ella y a rojo si peor, con más intensidad
    cuanto más se aleja (con tope en el percentil 90 de cada columna). `bajo_es_bueno`: columnas donde un valor más bajo es mejor (el paro).
    Las cifras se escriben siempre: el color no es la única señal."""
    cols = [c for c in df.columns if c != nombre]
    pos = int(df.index[df[nombre] == ref][0])

    def por_columna(col):
        d = col.astype(float) - float(col.iloc[pos])
        tope = d.drop(index=d.index[pos]).abs().quantile(0.9)  # el percentil 90, no el máximo: un valor extremo (Melilla) apagaría el resto
        tope = tope if tope and tope == tope else 1.0
        est = []
        for i, x in enumerate(d):
            if i == pos:
                est.append(f"background-color:{GRIS_MEDIA};color:{MARINO};font-weight:700")
            elif x != x:
                est.append("")
            else:
                bueno = x < 0 if col.name in bajo_es_bueno else x > 0
                est.append(f"background-color:{_mezcla(BLANCO, VERDE if bueno else ROJO, min(abs(x) / tope, 1) * 0.9)};color:{MARINO}")
        return est

    def fila_ref(col):
        return [f"background-color:{GRIS_MEDIA};color:{MARINO};font-weight:700" if i == pos else "" for i in range(len(col))]

    return (df.style.apply(por_columna, subset=cols).apply(fila_ref, subset=[nombre])
            .format(lambda v: pct(v), subset=cols))
