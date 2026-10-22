import pandas as pd
import streamlit as st

from comun import datos, graficos as g, relato as r

r.estilo()
st.title("Mapa país: jóvenes NEET en España")
st.caption("Jóvenes de 15 a 29 años que ni estudian ni trabajan (NEET), en % de la población de esa edad. Fuente: INE, "
           "Encuesta de Población Activa (indicadores de los ODS). Es la definición oficial del INE y de Eurostat: 15-29, "
           "no 16-29.")

if not datos.hay("mart_neet"):
    st.info("Esta carga no incluye todavía los datos de NEET.")
    st.stop()

d = datos.q("""SELECT n.anyo, n.territorio_id, t.nombre, n.desglose, n.categoria, n.grupo_edad, n.porcentaje
               FROM mart_neet n LEFT JOIN dim_territorio t USING (territorio_id) WHERE n.grupo_edad = '15-29'""")
if d.empty:
    st.info("Sin datos de NEET en esta carga.")
    st.stop()
ultimo = int(d.anyo.max())
nac = d[(d.desglose == "Comunidad autónoma") & (d.territorio_id == "N00")].set_index("anyo").porcentaje
sexo = d[d.desglose == "Sexo"].pivot_table(index="anyo", columns="categoria", values="porcentaje")

# --- cifras clave -----------------------------------------------------------------------------------------------
c = st.columns(3)
variacion = f"{nac[ultimo] - nac[ultimo - 1]:+.1f}".replace(".", ",") + f" p.p. frente a {ultimo - 1}" if ultimo - 1 in nac else None
c[0].metric(f"% jóvenes NEET (15-29), {ultimo}", f"{nac[ultimo]:.1f} %".replace(".", ","), variacion, delta_color="inverse")
for col, categoria in zip(c[1:], ("Hombres", "Mujeres")):
    if categoria in sexo and ultimo in sexo.index:
        col.metric(f"{categoria}, {ultimo}", f"{sexo.loc[ultimo, categoria]:.1f} %".replace(".", ","))
st.caption("Pendientes de fuente (no hay en el modelo una tabla con el grupo 16-29 o 15-29): volumen de población joven, "
           "tasa de actividad y tasa de empleo.")

# --- 01 mapa y 05 comparativa por comunidad ---------------------------------------------------------------------
ccaa = d[(d.desglose == "Comunidad autónoma") & (d.territorio_id != "N00")]
anyos = sorted(ccaa.anyo.unique(), reverse=True)
anyo = st.selectbox("Año", anyos, index=0)
act = ccaa[ccaa.anyo == anyo].copy()
act["nombre"] = act.nombre.map(g.corto)

izq, der = st.columns([3, 2])
with izq:
    st.subheader("01 · Jóvenes NEET por comunidad autónoma")
    g.mapa_ccaa(act, "porcentaje", fmt=",.1f", titulo="% jóvenes NEET (15-29)", escala=("#fde8d7", "#b83a0b"))
with der:
    st.subheader("05 · Comparativa por comunidad")
    media = nac.get(anyo)
    g.barras(act[["nombre", "porcentaje"]], "nombre", "porcentaje", fmt=",.1f", titulo_val="% jóvenes NEET (15-29)",
             resaltar=act.porcentaje.reset_index(drop=True) > media if media is not None else None, alto_fila=24)
    if media is not None:
        st.caption(f"En naranja, las comunidades por encima de la media nacional ({media:.1f} %).".replace(".", ","))

# --- 04 evolución -----------------------------------------------------------------------------------------------
st.subheader("04 · Evolución")
series = {"Total": nac, **{k: sexo[k].dropna() for k in ("Hombres", "Mujeres") if k in sexo}}
ev = pd.concat([s.rename("porcentaje").reset_index().assign(serie=k) for k, s in series.items()], ignore_index=True)
ev["fecha"] = ev.anyo.astype(str) + "-01-01"
g.lineas(ev, "fecha", "porcentaje", serie="serie", fmt=",.1f", x_fmt="%Y", titulo_y="% jóvenes NEET (15-29)")

# --- nacionalidad -----------------------------------------------------------------------------------------------
st.subheader("Por nacionalidad")
nacion = d[(d.desglose == "Nacionalidad") & (d.anyo == ultimo)]
g.barras(nacion[["categoria", "porcentaje"]], "categoria", "porcentaje", fmt=",.1f", titulo_val=f"% jóvenes NEET (15-29), {ultimo}")

# --- paneles sin fuente -----------------------------------------------------------------------------------------
st.subheader("Pendientes de fuente")
p = st.columns(2)
p[0].info("**02 · Nivel educativo de los NEET.** Existe el desglose por nivel de formación (EPA, desde 2002), pero aún no "
          "está localizada la tabla del INE que lo publica.")
p[1].info("**03 · Entorno urbano / rural.** Eurostat lo publica por grado de urbanización; falta confirmar que cubra España "
          "con esta edad. Detalle en `docs/dashboard_1_fuentes.md`.")
