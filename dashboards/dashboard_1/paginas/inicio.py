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

# Eurostat (tabla opcional): población, tasa de empleo, NEET por nivel de formación y por urbanización
eu = datos.q("SELECT serie, anyo, sexo, categoria, valor, estado FROM fact_eurostat") if datos.hay("fact_eurostat") else pd.DataFrame()


def serie_eu(nombre, categoria="Total", sexo="Total"):
    """Serie anual de Eurostat (índice: año); vacía si la tabla o la serie no están en la carga."""
    if eu.empty:
        return pd.Series(dtype=float)
    f = eu[(eu.serie == nombre) & (eu.categoria == categoria) & (eu.sexo == sexo)]
    return f.set_index("anyo").valor.sort_index()


poblacion, empleo = serie_eu("poblacion_16_29"), serie_eu("tasa_empleo_15_29")

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
partes = []
for categoria in ("Hombres", "Mujeres"):
    if categoria in sexo and ultimo in sexo.index:
        s_ = sexo[categoria].dropna()
        p = s_.get(ultimo - 1)
        partes.append(dict(titulo=f"{categoria}, {ultimo}", valor=g.pct(s_[ultimo]), delta=im.delta_pp(s_[ultimo], p),
                           bueno=(s_[ultimo] <= p) if p is not None else None, serie=s_.tolist()))
if partes:
    tarjetas.append(dict(partes=partes))
if len(act_u) > 1:
    brecha = (act_u.porcentaje.max() - act_u.porcentaje.min())
    tarjetas.append(dict(titulo=f"Distancia entre comunidades, {ultimo}", valor=g.es(brecha, 1, " p.p."),
                         nota=f"{act_u.iloc[0].nombre} frente a {act_u.iloc[-1].nombre}",
                         serie=ccaa_todas.groupby("anyo").porcentaje.apply(lambda x: x.max() - x.min()).sort_index().tolist(), desde=primero, hasta=ultimo))
if not poblacion.empty:
    pu, pp = poblacion.index.max(), poblacion.get(poblacion.index.max() - 1)
    tarjetas.insert(0, dict(titulo=f"Población de 16 a 29 años, 1 de enero de {pu}", valor=g.es(poblacion[pu] / 1e6, 2, " M"),
                            delta=im.delta_rel(poblacion[pu], pp), nota=f"frente a {pu - 1} · {g.es(poblacion[pu])} personas",
                            serie=poblacion.tolist(), desde=int(poblacion.index.min()), hasta=int(pu)))
if not empleo.empty:
    eu_u, ep = empleo.index.max(), empleo.get(empleo.index.max() - 1)
    tarjetas.insert(1, dict(titulo=f"Tasa de empleo, 15 a 29 años, {eu_u}", valor=g.pct(empleo[eu_u]), delta=im.delta_pp(empleo[eu_u], ep),
                            bueno=None if ep is None else bool(empleo[eu_u] >= ep), nota=f"frente a {eu_u - 1}",
                            serie=empleo.tolist(), desde=int(empleo.index.min()), hasta=int(eu_u)))
im.tarjetas(tarjetas)
if not poblacion.empty or not empleo.empty:
    st.caption("Población: INE (vía Eurostat, suma de las edades de 16 a 29). Tasa de empleo: INE, EPA "
               "(vía Eurostat); Eurostat no publica el grupo 16-29, solo 15-29. Si el último año lleva la marca «d», Eurostat avisa de un cambio de definición.")

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

# --- 02 nivel educativo de los NEET (rosco) y 03 entorno urbano / rural -----------------------------------------
NIVELES = ["Primaria y primera etapa de secundaria", "Segunda etapa de secundaria y postsecundaria", "Educación superior"]
izq, der = st.columns(2)
with izq:
    st.subheader("02 · Nivel educativo de los NEET")
    tasa_n = eu[eu.serie == "neet_nivel"].pivot_table(index="anyo", columns="categoria", values="valor") if not eu.empty else pd.DataFrame()
    pob_n = eu[eu.serie == "poblacion_nivel"].pivot_table(index="anyo", columns="categoria", values="valor") if not eu.empty else pd.DataFrame()
    comunes = [a for a in tasa_n.index if a in pob_n.index and set(NIVELES) <= set(tasa_n.columns) and set(NIVELES) <= set(pob_n.columns)]
    if comunes:
        a_n = st.select_slider("Año", options=sorted(comunes), value=max(comunes), key="anyo_nivel")
        nivel = pd.DataFrame({"nivel": NIVELES, "neet": [tasa_n.loc[a_n, n] / 100 * pob_n.loc[a_n, n] for n in NIVELES]})
        corto_n = {NIVELES[0]: "Hasta 1.ª secundaria", NIVELES[1]: "2.ª secundaria", NIVELES[2]: "Educación superior"}
        nivel["nivel"] = [f"{corto_n[n]} · {g.pct(v / nivel.neet.sum() * 100, 0)}" for n, v in zip(nivel.nivel, nivel.neet)]
        im.rosco(nivel, "nivel", "neet", orden=nivel.nivel.tolist(), colores=[g.MARINO, g.ORO, g.MARINO_CLARO], centro=g.es(nivel.neet.sum() / 1e3, 0, " mil"),
                 sub="jóvenes NEET", fmt=".1%", alto=330)
        st.caption("Reparto de los NEET de 15 a 29 años por nivel de formación. Es un cálculo propio: la tasa de NEET de cada nivel "
                   "(Eurostat) por la población de 15-29 de ese nivel (Eurostat). Eurostat no publica este reparto directamente; "
                   "hay datos desde 2021.")
    else:
        st.info("Esta carga no incluye todavía el nivel de formación de los NEET.")
with der:
    st.subheader("03 · Entorno: ciudad, periferia o rural")
    urb = eu[eu.serie == "neet_urbanizacion"] if not eu.empty else pd.DataFrame()
    if not urb.empty:
        orden_u = ["Ciudades", "Pueblos y periferias", "Zonas rurales"]
        urb = urb.drop(columns="serie").rename(columns={"categoria": "serie"}).assign(fecha=lambda x: x.anyo.astype(str) + "-01-01")
        im.lineas_etiquetadas(urb[["fecha", "valor", "serie"]], "fecha", "valor", "serie", fmt=",.1f", titulo_y="% jóvenes NEET (15-29)",
                              orden_series=[o for o in orden_u if o in set(urb.serie)], alto=330)
        st.caption("Tasa de NEET (15-29) según el grado de urbanización del lugar de residencia (Eurostat, a partir de la EPA). Son tasas dentro de "
                   "cada entorno, no un reparto: Eurostat no publica cuántos jóvenes NEET viven en cada uno.")
    else:
        st.info("Esta carga no incluye todavía la tasa de NEET por entorno.")
