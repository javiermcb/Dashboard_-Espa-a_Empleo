import pandas as pd
import streamlit as st

from comun import datos, graficos as g, relato as r

r.estilo()
st.title("Empleo, actividad y sectores con más oportunidad")
st.caption("Tasas de actividad, empleo y paro de la población joven por comunidad autónoma. Fuente: INE, Encuesta de Población "
           "Activa (medias anuales). La EPA no publica el grupo 16-29: se usan sus grupos de edad más jóvenes.")

if not datos.hay("mart_tasas_epa"):
    st.info("Esta carga no incluye todavía las tasas de la EPA.")
    st.stop()

EDADES = {"Menores de 25 años": "16-24 años", "De 16 a 19 años": "16-19 años", "De 20 a 24 años": "20-24 años"}
edad = st.radio("Grupo de edad", list(EDADES), format_func=EDADES.get, horizontal=True)
etiqueta = EDADES[edad]

d = datos.q("""SELECT e.anyo, e.territorio_id, t.nombre, e.indicador, e.tasa
               FROM mart_tasas_epa e LEFT JOIN dim_territorio t USING (territorio_id)
               WHERE e.edad = ? AND e.sexo = 'Ambos sexos'""", [edad])
if d.empty:
    st.info("Sin datos para este grupo de edad en esta carga.")
    st.stop()
ultimo = int(d.anyo.max())
nac = d[d.territorio_id == "N00"].pivot_table(index="anyo", columns="indicador", values="tasa")
ccaa = d[d.territorio_id != "N00"]

# --- cifras clave -----------------------------------------------------------------------------------------------
c = st.columns(3)
for col, ind in zip(c, ("Tasa de actividad", "Tasa de empleo", "Tasa de paro")):
    if ind in nac and ultimo in nac.index:
        previo = nac[ind].get(ultimo - 1)
        variacion = f"{nac.loc[ultimo, ind] - previo:+.1f}".replace(".", ",") + f" p.p. frente a {ultimo - 1}" if previo is not None else None
        col.metric(f"{ind} {etiqueta}, {ultimo}", f"{nac.loc[ultimo, ind]:.1f} %".replace(".", ","), variacion,
                   delta_color="inverse" if ind == "Tasa de paro" else "normal")

# --- 01 actividad por territorio y 02 evolución del empleo ------------------------------------------------------
anyos = sorted(ccaa.anyo.unique(), reverse=True)
izq, der = st.columns(2)
with izq:
    st.subheader("01 · Tasa de actividad por territorio")
    anyo = st.selectbox("Año", anyos, index=0)
    act = ccaa[(ccaa.anyo == anyo) & (ccaa.indicador == "Tasa de actividad")][["nombre", "tasa"]].copy()
    act["nombre"] = act.nombre.map(g.corto)
    media = nac["Tasa de actividad"].get(anyo)
    if media is not None:
        act = pd.concat([act, pd.DataFrame([{"nombre": "España", "tasa": media}])], ignore_index=True)
    g.barras(act, "nombre", "tasa", fmt=",.1f", titulo_val=f"% de la población de {etiqueta}",
             resaltar=act.nombre == "España", alto_fila=24)
    st.caption("En naranja, el total de España.")
with der:
    st.subheader("02 · Tasa de empleo juvenil")
    ev = nac["Tasa de empleo"].dropna().rename("tasa").reset_index().assign(serie="España")
    ev["fecha"] = ev.anyo.astype(str) + "-01-01"
    g.lineas(ev, "fecha", "tasa", serie="serie", fmt=",.1f", x_fmt="%Y", titulo_y=f"% de la población de {etiqueta}")
    st.caption("Falta la serie de la UE-27 para compararla (Eurostat, sin descargar todavía).")

# --- 03 comparativa territorial ---------------------------------------------------------------------------------
st.subheader("03 · Comparativa territorial")
tabla = ccaa[ccaa.anyo == anyo].pivot_table(index="nombre", columns="indicador", values="tasa").reset_index()
tabla["nombre"] = tabla.nombre.map(g.corto)
tot = nac.loc[[anyo]].reset_index(drop=True).assign(nombre="España") if anyo in nac.index else None
if tot is not None:
    tabla = pd.concat([tot, tabla.sort_values("Tasa de actividad", ascending=False)], ignore_index=True)
tabla = tabla.rename(columns={"nombre": "Territorio"})[["Territorio", "Tasa de actividad", "Tasa de empleo", "Tasa de paro"]]
cfg = {k: st.column_config.NumberColumn(k, format="%.1f %%") for k in tabla.columns[1:]}
st.dataframe(tabla, hide_index=True, width="stretch", column_config=cfg)

# --- paneles sin fuente -----------------------------------------------------------------------------------------
st.subheader("Pendientes de fuente")
p = st.columns(3)
p[0].info("**04 · Sectores con mayor potencial.** Hace falta una previsión de empleo por sector: las proyecciones de "
          "Cedefop (Skills Forecast, España a 2035) son la candidata; falta confirmar que se pueden descargar por sector.")
p[1].info("**05 · Competencias más demandadas.** No hay fuente abierta con porcentajes por competencia: el SEPE publica "
          "informes de competencias y necesidades formativas, no una serie de datos.")
p[2].info("**06 · Empleo por tipo de contrato.** No hay en el modelo una tabla de contrato indefinido, temporal y parcial por "
          "grupo de edad.")
