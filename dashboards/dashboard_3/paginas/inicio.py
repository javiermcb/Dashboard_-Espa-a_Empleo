import streamlit as st

from comun import datos, graficos as g, relato as r

r.estilo()
st.title("Formación bonificada y ecosistema FUNDAE")
st.caption("Formación programada por las empresas y bonificada a través de FUNDAE (Fundación Estatal para la Formación en el "
           "Empleo). Fuente: series estadísticas de FUNDAE, años naturales. «Participantes» son los participantes formados "
           "que cuenta FUNDAE.")

if not datos.hay("fact_fundae"):
    st.info("Esta carga no incluye todavía los datos de FUNDAE (su web falla a menudo y las series se completan en cargas "
            "sucesivas).")
    st.stop()


def millones(v, d=1):
    return f"{v / 1e6:.{d}f}".replace(".", ",") + " M"


def total_anual(serie, medida, categoria="Total"):
    """Serie anual (índice año) de una medida, tomando la fila «Total» de la serie FUNDAE indicada."""
    d = datos.q("SELECT anyo, valor FROM fact_fundae WHERE serie = ? AND medida = ? AND categoria = ? ORDER BY anyo",
                [serie, medida, categoria])
    return d.set_index("anyo").valor


# totales anuales: participantes y horas (serie 10, por modalidad), crédito dispuesto (serie 38, por tamaño de empresa)
part, horas, credito = total_anual("10", "Participantes"), total_anual("10", "Horas de formación"), total_anual("38", "Crédito dispuesto")
if part.empty:
    st.info("Sin datos de FUNDAE en esta carga.")
    st.stop()
ultimo = int(part.index.max())

# --- cifras clave -----------------------------------------------------------------------------------------------
c = st.columns(3)
for col, titulo, s, fmt in ((c[0], "Participantes formados", part, millones), (c[1], "Crédito dispuesto", credito, lambda v: millones(v) + "€"),
                            (c[2], "Horas de formación", horas, millones)):
    if ultimo in s.index:
        previo = s.get(ultimo - 1)
        col.metric(f"{titulo}, {ultimo}", fmt(s[ultimo]),
                   f"{(s[ultimo] / previo - 1) * 100:+.1f} %".replace(".", ",") + f" frente a {ultimo - 1}" if previo else None)
st.caption("FUNDAE publica el crédito «dispuesto» (el que las empresas han utilizado); no hay en estas series el crédito "
           "asignado, así que no se puede calcular el crédito disponible ni el % consumido.")

anyos = sorted(datos.q("SELECT DISTINCT anyo FROM fact_fundae WHERE serie IN ('14', '30')").anyo.tolist(), reverse=True)
anyo = st.selectbox("Año", anyos, index=0, help="Familias profesionales y comunidades autónomas se publican desde 2019 y 2016.")

# --- 01 familias y 03 modalidad ---------------------------------------------------------------------------------
izq, der = st.columns(2)
with izq:
    st.subheader("01 · Familias formativas más activas")
    fam = datos.q("SELECT categoria, valor FROM fact_fundae WHERE serie = '14' AND medida = 'Participantes' AND anyo = ?", [anyo])
    tot = fam[fam.categoria == "Total"].valor
    fam = fam[fam.categoria != "Total"].nlargest(8, "valor")
    if tot.empty or fam.empty:
        st.info("Sin datos de familias profesionales para este año.")
    else:
        fam["pct"] = fam.valor / tot.iloc[0] * 100
        g.barras(fam[["categoria", "pct"]], "categoria", "pct", fmt=",.1f", titulo_val="% de los participantes")
with der:
    st.subheader("03 · Modalidad de impartición")
    mod = datos.q("SELECT categoria, valor FROM fact_fundae WHERE serie = '10' AND medida = 'Participantes' AND anyo = ?", [anyo])
    tot = mod[mod.categoria == "Total"].valor
    mod = mod[(mod.categoria != "Total") & (mod.valor > 0)]
    if tot.empty or mod.empty:
        st.info("Sin datos de modalidad para este año.")
    else:
        mod["pct"] = mod.valor / tot.iloc[0] * 100
        g.barras(mod[["categoria", "pct"]], "categoria", "pct", fmt=",.1f", titulo_val="% de los participantes")

# --- 02 distribución por comunidad autónoma ---------------------------------------------------------------------
st.subheader("02 · Distribución por comunidad autónoma")
cc = datos.q("""SELECT f.ccaa_id AS territorio_id, t.nombre, f.valor FROM fact_fundae f
                LEFT JOIN dim_territorio t ON t.territorio_id = f.ccaa_id
                WHERE f.serie = '30' AND f.medida = 'Participantes' AND f.anyo = ? AND f.ccaa_id IS NOT NULL""", [anyo])
tot_cc = datos.q("SELECT valor FROM fact_fundae WHERE serie = '30' AND medida = 'Participantes' AND anyo = ? AND categoria = 'Total'", [anyo])
if cc.empty or tot_cc.empty:
    st.info("Sin datos por comunidad autónoma para este año.")
else:
    cc["pct"] = cc.valor / tot_cc.valor.iloc[0] * 100
    cc["nombre"] = cc.nombre.map(g.corto)
    g.mapa_ccaa(cc, "pct", fmt=",.1f", titulo="% de los participantes", escala=("#fde8d7", "#b83a0b"))
    st.caption("Comunidad autónoma del participante. Cada comunidad en % del total nacional de participantes; no está "
               "corregido por población ni por número de trabajadores.")

# --- 04 tendencias ----------------------------------------------------------------------------------------------
st.subheader("04 · Tendencias y evolución")
t = st.columns(3)
for col, titulo, s, fmt in ((t[0], "Participantes formados", part, ",.0f"), (t[1], "Horas de formación", horas, ",.0f"),
                            (t[2], "Crédito dispuesto (€)", credito, ",.0f")):
    with col:
        st.caption(titulo)
        e = s.rename("valor").reset_index().assign(serie=titulo, fecha=lambda x: x.anyo.astype(str) + "-01-01")
        g.lineas(e, "fecha", "valor", serie="serie", fmt=fmt, x_fmt="%Y", alto=220)
st.caption("La caída de 2020 coincide con la pandemia; los saltos de horas entre 2015 y 2016 y de 2023 a 2024 son de las "
           "propias series de FUNDAE (no se ha investigado su causa).")
