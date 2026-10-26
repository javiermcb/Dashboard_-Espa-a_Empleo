import pandas as pd
import streamlit as st

from comun import datos, graficos as g, impacto as im, relato as r

r.estilo()
st.title("Empleo, actividad y sectores con más oportunidad")
st.caption("Tasas de actividad, empleo y paro de la población joven por comunidad autónoma. Fuente: INE, Encuesta de Población "
           "Activa (medias anuales). La EPA no publica el grupo 16-29: se usan sus grupos de edad más jóvenes.")

if not datos.hay("mart_tasas_epa"):
    st.info("Esta carga no incluye todavía las tasas de la EPA.")
    st.stop()

EDADES = {"Menores de 25 años": "16-24 años", "De 16 a 19 años": "16-19 años", "De 20 a 24 años": "20-24 años"}
ETIQUETA_EDAD = {**EDADES, "De 25 a 54 años": "25-54 años", "De 55 y más años": "55 y más años", "Total": "Total (16 y más)"}
edad = st.radio("Grupo de edad", list(EDADES), format_func=EDADES.get, horizontal=True)
etiqueta = EDADES[edad]
INDICADORES = ("Tasa de actividad", "Tasa de empleo", "Tasa de paro")

todo = datos.q("""SELECT e.anyo, e.territorio_id, t.nombre, e.indicador, e.edad, e.sexo, e.tasa
                  FROM mart_tasas_epa e LEFT JOIN dim_territorio t USING (territorio_id)""")
d = todo[(todo.edad == edad) & (todo.sexo == "Ambos sexos")]
if d.empty:
    st.info("Sin datos para este grupo de edad en esta carga.")
    st.stop()
ultimo = int(d.anyo.max())
nac = d[d.territorio_id == "N00"].pivot_table(index="anyo", columns="indicador", values="tasa").sort_index()
ccaa = d[d.territorio_id != "N00"].copy()
ccaa["nombre"] = ccaa.nombre.map(g.corto)
nac_total = todo[(todo.edad == "Total") & (todo.sexo == "Ambos sexos") & (todo.territorio_id == "N00")].pivot_table(
    index="anyo", columns="indicador", values="tasa").sort_index()
primero = int(nac.index.min())

# --- la respuesta en una frase ----------------------------------------------------------------------------------
paro = nac.get("Tasa de paro")
puntos = []
if paro is not None and ultimo in paro.index:
    veces = paro[ultimo] / nac_total.loc[ultimo, "Tasa de paro"] if "Tasa de paro" in nac_total and ultimo in nac_total.index else None
    frase = f"La tasa de paro de los {etiqueta} es del {g.pct(paro[ultimo])} ({ultimo})"
    if veces:
        frase += f", {g.es(veces, 1)} veces la del conjunto de la población ({g.pct(nac_total.loc[ultimo, 'Tasa de paro'])})"
    if paro.get(ultimo - 1) is not None:
        dif = paro[ultimo] - paro[ultimo - 1]
        puntos.append(f"{'Baja' if dif < 0 else 'Sube'} {g.es(abs(dif), 1)} puntos respecto a {ultimo - 1} ({g.pct(paro[ultimo - 1])})." if dif
                      else f"Igual que en {ultimo - 1}.")
    puntos.append(f"En la serie {primero}-{ultimo}, el máximo fue del {g.pct(paro.max())} ({paro.idxmax()}) y el mínimo del {g.pct(paro.min())} ({paro.idxmin()}).")
    sx = todo[(todo.edad == edad) & (todo.territorio_id == "N00") & (todo.indicador == "Tasa de paro") & (todo.anyo == ultimo)].set_index("sexo").tasa
    if {"Hombres", "Mujeres"} <= set(sx.index):
        puntos.append(f"Por sexo: hombres {g.pct(sx['Hombres'])} y mujeres {g.pct(sx['Mujeres'])}.")
    pu = ccaa[(ccaa.anyo == ultimo) & (ccaa.indicador == "Tasa de paro")].dropna(subset=["tasa"]).sort_values("tasa")
    if len(pu) > 1:
        puntos.append(f"Por comunidades, de {g.pct(pu.iloc[0].tasa)} en {pu.iloc[0].nombre} a {g.pct(pu.iloc[-1].tasa)} en {pu.iloc[-1].nombre}.")
    r.respuesta(frase, puntos)

# --- cifras clave con su evolución ------------------------------------------------------------------------------
tarjetas = []
for ind in INDICADORES:
    if ind in nac and ultimo in nac.index:
        s = nac[ind].dropna()
        p = s.get(ultimo - 1)
        malo_sube = ind == "Tasa de paro"
        tarjetas.append(dict(titulo=f"{ind}, {etiqueta}, {ultimo}", valor=g.pct(s[ultimo]), delta=im.delta_pp(s[ultimo], p),
                             bueno=None if p is None else ((s[ultimo] <= p) if malo_sube else (s[ultimo] >= p)),
                             nota=f"frente a {ultimo - 1}", serie=s.tolist(), desde=int(s.index.min()), hasta=ultimo))
if paro is not None and "Tasa de paro" in nac_total:
    cociente = (paro / nac_total["Tasa de paro"]).dropna()
    if ultimo in cociente.index:
        tarjetas.append(dict(titulo=f"Paro de los {etiqueta} frente al paro total, {ultimo}", valor=f"{g.es(cociente[ultimo], 1)} ×",
                             nota="veces la tasa de todos", serie=cociente.tolist(), desde=int(cociente.index.min()), hasta=ultimo))
im.tarjetas(tarjetas)

# --- 01 por territorio, con el deslizante de año dentro del gráfico ---------------------------------------------
st.subheader("01 · Por comunidad autónoma, año a año")
indicador = st.radio("Indicador", INDICADORES, horizontal=True, index=0, key="ind_ccaa")
st.caption("Mueve el deslizante del gráfico para cambiar de año. En naranja, por encima de la media de España de ese año; "
           "en azul marino, la propia media.")
sub = ccaa[ccaa.indicador == indicador].dropna(subset=["tasa"])
im.barras_anuales(sub[["nombre", "anyo", "tasa"]], "nombre", "tasa", "anyo", ref=nac[indicador].dropna().to_dict(), fmt=",.1f",
                  titulo_val=f"% de la población de {etiqueta}")

# --- 02 evolución de los tres indicadores -----------------------------------------------------------------------
st.subheader("02 · Evolución de la actividad, el empleo y el paro")
ev = nac[[i for i in INDICADORES if i in nac]].reset_index().melt(id_vars="anyo", var_name="serie", value_name="tasa").dropna()
ev["fecha"] = ev.anyo.astype(str) + "-01-01"
im.lineas_etiquetadas(ev, "fecha", "tasa", "serie", fmt=",.1f", titulo_y=f"% de la población de {etiqueta}", orden_series=[i for i in INDICADORES if i in nac], cero=True)
st.caption("Falta la serie de la UE-27 para compararla (Eurostat, sin descargar todavía).")

# --- la brecha de edad ------------------------------------------------------------------------------------------
st.subheader("La brecha de edad: el paro según la edad")
ORDEN_E = ["De 16 a 19 años", "De 20 a 24 años", "De 25 a 54 años", "De 55 y más años", "Total"]
por_edad = todo[(todo.territorio_id == "N00") & (todo.sexo == "Ambos sexos") & (todo.indicador == "Tasa de paro") & todo.edad.isin(ORDEN_E)].dropna(subset=["tasa"]).copy()
por_edad["serie"] = por_edad.edad.map(ETIQUETA_EDAD)
por_edad["fecha"] = por_edad.anyo.astype(str) + "-01-01"
im.lineas_etiquetadas(por_edad, "fecha", "tasa", "serie", fmt=",.1f", titulo_y="Tasa de paro (%)", orden_series=[ETIQUETA_EDAD[e] for e in ORDEN_E],
                      resaltar="Total (16 y más)", alto=340)
u = por_edad[por_edad.anyo == ultimo].set_index("edad").tasa
if {"De 16 a 19 años", "De 55 y más años"} <= set(u.index):
    st.caption(f"En {ultimo}, la tasa de paro va del {g.pct(u['De 55 y más años'])} entre los de 55 y más años al {g.pct(u['De 16 a 19 años'])} entre los de 16 a 19.")

# --- la brecha de género ----------------------------------------------------------------------------------------
st.subheader(f"La brecha entre hombres y mujeres ({etiqueta})")
bg = todo[(todo.territorio_id == "N00") & (todo.edad == edad) & (todo.sexo.isin(["Hombres", "Mujeres"]))].copy()
sel_ind = st.radio("Indicador", INDICADORES, horizontal=True, index=2, key="ind_sexo")
bg = bg[bg.indicador == sel_ind].dropna(subset=["tasa"]).rename(columns={"sexo": "serie"})
bg["fecha"] = bg.anyo.astype(str) + "-01-01"
im.lineas_etiquetadas(bg, "fecha", "tasa", "serie", fmt=",.1f", titulo_y=f"{sel_ind} (%)", orden_series=["Hombres", "Mujeres"], alto=280)

# --- dónde y cuándo: mapa de calor del paro ---------------------------------------------------------------------
st.subheader(f"Dónde y cuándo: paro de los {etiqueta}, comunidad a comunidad")
calor = ccaa[ccaa.indicador == "Tasa de paro"].dropna(subset=["tasa"])
orden = calor[calor.anyo == ultimo].sort_values("tasa", ascending=False).nombre.tolist()
g.mapa_calor(calor, "nombre", "anyo", "tasa", fmt=",.0f", orden_filas=orden, orden_cols=sorted(calor.anyo.unique()), titulo="Tasa de paro (%)", escala=("#fde8d7", "#b83a0b"))
st.caption(f"Ordenadas por su valor en {ultimo}. Cuanto más oscuro, mayor es el paro.")

# --- comparativa territorial: actividad frente a paro, y tabla --------------------------------------------------
st.subheader("03 · Comparativa territorial")
anyos = sorted(ccaa.anyo.unique(), reverse=True)
anyo = st.selectbox("Año", anyos, index=0)
tabla = ccaa[ccaa.anyo == anyo].pivot_table(index="nombre", columns="indicador", values="tasa").reset_index()
if {"Tasa de actividad", "Tasa de paro"} <= set(tabla.columns) and anyo in nac.index:
    st.markdown("**Actividad frente a paro**")
    g.dispersion(tabla, "Tasa de actividad", "Tasa de paro", "nombre", ref_x=nac.loc[anyo, "Tasa de actividad"], ref_y=nac.loc[anyo, "Tasa de paro"],
                 resaltar=None, fmt_x=",.1f", fmt_y=",.1f", titulo_x=f"Tasa de actividad (%), {etiqueta}", titulo_y=f"Tasa de paro (%), {etiqueta}",
                 etiquetar_todos=True, alto=440)
    st.caption("Las líneas discontinuas marcan la media de España. Arriba a la izquierda: poca actividad y mucho paro; abajo a la derecha: "
               "mucha actividad y poco paro.")
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
