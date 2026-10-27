import pandas as pd
import streamlit as st

from comun import datos, graficos as g, impacto as im, relato as r

r.estilo()
st.title("Mapa país: jóvenes NEET en España")
st.caption("Jóvenes de 15 a 29 años que ni estudian ni trabajan (NEET), en % de la población de esa edad. Fuente: INE, "
           "Encuesta de Población Activa (indicadores de los ODS). Es la definición oficial del INE y de Eurostat: 15-29, "
           "no 16-29.")

if not datos.hay("mart_neet"):
    st.info("Esta carga no incluye todavía los datos de NEET.")
    st.stop()

d = datos.q("""SELECT n.anyo, n.territorio_id, t.nombre, n.desglose, n.categoria, n.grupo_edad, n.porcentaje
               FROM mart_neet n LEFT JOIN dim_territorio t USING (territorio_id)""")
d15 = d[d.grupo_edad == "15-29"]
if d15.empty:
    st.info("Sin datos de NEET en esta carga.")
    st.stop()
ultimo = int(d15.anyo.max())
primero = int(d15.anyo.min())
nac = d15[(d15.desglose == "Comunidad autónoma") & (d15.territorio_id == "N00")].set_index("anyo").porcentaje.sort_index()
sexo = d15[d15.desglose == "Sexo"].pivot_table(index="anyo", columns="categoria", values="porcentaje").sort_index()
nacion = d15[d15.desglose == "Nacionalidad"].pivot_table(index="anyo", columns="categoria", values="porcentaje").sort_index()
ccaa_todas = d15[(d15.desglose == "Comunidad autónoma") & (d15.territorio_id != "N00")].copy()
ccaa_todas["nombre"] = ccaa_todas.nombre.map(g.corto)
act_u = ccaa_todas[ccaa_todas.anyo == ultimo].sort_values("porcentaje")
previo = nac.get(ultimo - 1)

# --- la respuesta en una frase ----------------------------------------------------------------------------------
puntos = []
if previo is not None:
    dif = nac[ultimo] - previo
    puntos.append(f"{'Baja' if dif < 0 else 'Sube'} {g.es(abs(dif), 1)} puntos respecto a {ultimo - 1} ({g.pct(previo)})." if dif
                  else f"Igual que en {ultimo - 1} ({g.pct(previo)}).")
maximo = nac.idxmax()
puntos.append(f"La serie {primero}-{ultimo} tuvo su máximo en {maximo} ({g.pct(nac[maximo])}) y su mínimo en {nac.idxmin()} ({g.pct(nac.min())}).")
if {"Hombres", "Mujeres"} <= set(sexo.columns) and ultimo in sexo.index:
    h, m = sexo.loc[ultimo, "Hombres"], sexo.loc[ultimo, "Mujeres"]
    puntos.append(f"Hombres {g.pct(h)} y mujeres {g.pct(m)} (diferencia de {g.es(abs(h - m), 1)} puntos).")
if not act_u.empty:
    puntos.append(f"Por comunidades, de {g.pct(act_u.iloc[0].porcentaje)} en {act_u.iloc[0].nombre} a {g.pct(act_u.iloc[-1].porcentaje)} "
                  f"en {act_u.iloc[-1].nombre}: {g.es(act_u.iloc[-1].porcentaje - act_u.iloc[0].porcentaje, 1)} puntos de distancia.")
r.respuesta(f"El {g.pct(nac[ultimo])} de los jóvenes de 15 a 29 años ni estudia ni trabaja ({ultimo})", puntos)

# --- cifras clave con su evolución ------------------------------------------------------------------------------
tarjetas = [dict(titulo=f"Jóvenes NEET (15-29), {ultimo}", valor=g.pct(nac[ultimo]), delta=im.delta_pp(nac[ultimo], previo), bueno=(nac[ultimo] <= previo) if previo is not None else None,
                 nota=f"frente a {ultimo - 1}", serie=nac.tolist(), desde=primero, hasta=ultimo)]
for categoria in ("Hombres", "Mujeres"):
    if categoria in sexo and ultimo in sexo.index:
        s = sexo[categoria].dropna()
        p = s.get(ultimo - 1)
        tarjetas.append(dict(titulo=f"{categoria}, {ultimo}", valor=g.pct(s[ultimo]), delta=im.delta_pp(s[ultimo], p),
                             bueno=(s[ultimo] <= p) if p is not None else None, nota=f"frente a {ultimo - 1}", serie=s.tolist(), desde=int(s.index.min()), hasta=ultimo))
if len(act_u) > 1:
    brecha = (act_u.porcentaje.max() - act_u.porcentaje.min())
    tarjetas.append(dict(titulo=f"Distancia entre comunidades, {ultimo}", valor=g.es(brecha, 1, " p.p."),
                         nota=f"{act_u.iloc[0].nombre} frente a {act_u.iloc[-1].nombre}",
                         serie=ccaa_todas.groupby("anyo").porcentaje.apply(lambda x: x.max() - x.min()).sort_index().tolist(), desde=primero, hasta=ultimo))
im.tarjetas(tarjetas)
st.caption("Pendientes de fuente (no hay en el modelo una tabla con el grupo 16-29 o 15-29): volumen de población joven, "
           "tasa de actividad y tasa de empleo.")

# --- 01 mapa y 05 comparativa con la media ----------------------------------------------------------------------
anyos = sorted(ccaa_todas.anyo.unique(), reverse=True)
anyo = st.selectbox("Año del mapa y de la comparativa", anyos, index=0)
act = ccaa_todas[ccaa_todas.anyo == anyo].copy()
media = nac.get(anyo)

izq, der = st.columns([3, 2])
with izq:
    st.subheader("01 · Jóvenes NEET por comunidad autónoma")
    g.mapa_ccaa(act, "porcentaje", fmt=",.1f", titulo="% jóvenes NEET (15-29)", escala=g.ESCALA)
with der:
    st.subheader("05 · Frente a la media de España")
    if media is not None:
        dv = act[["nombre", "porcentaje"]].assign(diferencia=act.porcentaje - media)
        im.divergentes(dv, "nombre", "diferencia", media, fmt="+.1f", titulo=f"Puntos respecto a la media nacional ({g.pct(media)})")
        st.caption("En dorado, las comunidades por encima de la media nacional; en marino suave, por debajo.")

# --- recorrer los años ------------------------------------------------------------------------------------------
st.subheader("Recorre los años")
st.caption("Mueve el deslizante del gráfico: el ranking de comunidades cambia al instante. En dorado, por encima de la media de "
           "España de ese año; en marino suave, por debajo; en azul marino, la propia media.")
im.barras_anuales(ccaa_todas[["nombre", "anyo", "porcentaje"]], "nombre", "porcentaje", "anyo", ref=nac.to_dict(), fmt=",.1f",
                  titulo_val="% jóvenes NEET (15-29)")

# --- dónde y cuándo: mapa de calor ------------------------------------------------------------------------------
st.subheader("Dónde y cuándo: cada comunidad, año a año")
calor = ccaa_todas.copy()
orden = act_u.sort_values("porcentaje", ascending=False).nombre.tolist()
g.mapa_calor(calor, "nombre", "anyo", "porcentaje", fmt=",.1f", orden_filas=orden, titulo="% jóvenes NEET (15-29)",
             escala=g.ESCALA)
st.caption(f"Ordenadas por su valor en {ultimo}. Cuanto más oscuro, mayor es la proporción de jóvenes NEET.")

# --- quién ha mejorado más --------------------------------------------------------------------------------------
st.subheader("Quién ha mejorado más")
base_a = st.select_slider("Comparar con el año", options=[a for a in sorted(ccaa_todas.anyo.unique()) if a < ultimo], value=primero)
dumb = (ccaa_todas[ccaa_todas.anyo == base_a][["nombre", "porcentaje"]].rename(columns={"porcentaje": "antes"})
        .merge(act_u[["nombre", "porcentaje"]].rename(columns={"porcentaje": "ahora"}), on="nombre"))
im.mancuernas(dumb, "nombre", "antes", "ahora", base_a, ultimo, titulo="% jóvenes NEET (15-29)")
if not dumb.empty:
    cam = dumb.assign(c=dumb.ahora - dumb.antes).sort_values("c")
    mas, menos = cam.iloc[0], cam.iloc[-1]
    st.caption(f"Entre {base_a} y {ultimo}, la mayor bajada es la de {mas.nombre} ({g.es(mas.c, 1)} puntos); "
               f"{'la bajada más pequeña' if menos.c < 0 else 'la mayor subida'} es la de {menos.nombre} ({g.es(menos.c, 1)} puntos).")

# --- 04 evolución -----------------------------------------------------------------------------------------------
st.subheader("04 · Evolución")
series = {"Total": nac, **{k: sexo[k].dropna() for k in ("Hombres", "Mujeres") if k in sexo}}
ev = pd.concat([s.rename("porcentaje").reset_index().assign(serie=k) for k, s in series.items()], ignore_index=True)
ev["fecha"] = ev.anyo.astype(str) + "-01-01"
im.lineas_etiquetadas(ev, "fecha", "porcentaje", "serie", fmt=",.1f", titulo_y="% jóvenes NEET (15-29)", orden_series=list(series), resaltar="Total")

n24 = d[(d.grupo_edad == "15-24") & (d.desglose == "Sexo") & (d.categoria == "Total")].set_index("anyo").porcentaje.sort_index()
if not n24.empty:
    st.markdown("**15-24 y 15-29, juntos**")
    c2 = pd.concat([nac.loc[n24.index].rename("porcentaje").reset_index().assign(serie="15-29 años"),
                    n24.rename("porcentaje").reset_index().assign(serie="15-24 años")], ignore_index=True)
    c2["fecha"] = c2.anyo.astype(str) + "-01-01"
    im.lineas_etiquetadas(c2, "fecha", "porcentaje", "serie", fmt=",.1f", titulo_y="% jóvenes NEET", orden_series=["15-29 años", "15-24 años"], alto=240)
    st.caption(f"El INE publica el grupo 15-24 desde {int(n24.index.min())}.")

# --- nacionalidad -----------------------------------------------------------------------------------------------
st.subheader("Por nacionalidad")
if not nacion.empty:
    nv = nacion.reset_index().melt(id_vars="anyo", var_name="serie", value_name="porcentaje").dropna()
    nv["fecha"] = nv.anyo.astype(str) + "-01-01"
    im.lineas_etiquetadas(nv, "fecha", "porcentaje", "serie", fmt=",.1f", titulo_y="% jóvenes NEET (15-29)", alto=280)
    if ultimo in nacion.index and nacion.loc[ultimo].notna().all():
        mx = nacion.loc[ultimo].idxmax()
        st.caption(f"En {ultimo}, el valor más alto es el de «{mx}» ({g.pct(nacion.loc[ultimo, mx])}) y el más bajo el de "
                   f"«{nacion.loc[ultimo].idxmin()}» ({g.pct(nacion.loc[ultimo].min())}).")

# --- paneles sin fuente -----------------------------------------------------------------------------------------
st.subheader("Pendientes de fuente")
p = st.columns(2)
p[0].info("**02 · Nivel educativo de los NEET.** Existe el desglose por nivel de formación (EPA, desde 2002), pero aún no "
          "está localizada la tabla del INE que lo publica.")
p[1].info("**03 · Entorno urbano / rural.** Eurostat lo publica por grado de urbanización; falta confirmar que cubra España "
          "con esta edad. Detalle en `docs/dashboard_1_fuentes.md`.")
