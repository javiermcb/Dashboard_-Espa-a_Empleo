import pandas as pd
import streamlit as st

from comun import datos, graficos as g, impacto as im, relato as r

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
    return g.es(v / 1e6, d) + " M"


def por_categoria(serie, medida):
    """Formato largo (anyo, categoria, valor) de una medida de una serie FUNDAE."""
    return datos.q("SELECT anyo, categoria, valor FROM fact_fundae WHERE serie = ? AND medida = ?", [serie, medida])


def total_anual(serie, medida, categoria="Total"):
    """Serie anual (índice año) de una medida, tomando la fila «Total» de la serie FUNDAE indicada."""
    d = por_categoria(serie, medida)
    return d[d.categoria == categoria].set_index("anyo").valor.sort_index()


def reparto(serie, medida, categorias, total="Total"):
    """% de cada categoría sobre el total de SU PROPIA serie, año a año (formato largo: anyo, categoria, pct, valor)."""
    d = por_categoria(serie, medida)
    tot = d[d.categoria == total].set_index("anyo").valor
    d = d[d.categoria.isin(categorias)].copy()
    d["pct"] = d.valor / d.anyo.map(tot) * 100
    return d.dropna(subset=["pct"])


def fecha(df):
    return df.assign(fecha=df.anyo.astype(str) + "-01-01")


# totales anuales: participantes y horas (serie 10, por modalidad), crédito dispuesto y empresas formadoras (serie 38)
part, horas = total_anual("10", "Participantes"), total_anual("10", "Horas de formación")
credito, empresas = total_anual("38", "Crédito dispuesto"), total_anual("38", "Empresas formadoras")
part38 = total_anual("38", "Participantes")
if part.empty:
    st.info("Sin datos de FUNDAE en esta carga.")
    st.stop()
ultimo = int(part.index.max())
BASE = 2019  # último año antes de la pandemia, para comparar

# --- la respuesta en una frase ----------------------------------------------------------------------------------
def var(a, b):
    """Variación relativa con signo: +3,4 %."""
    return g.sig((a / b - 1) * 100)


puntos = []
if (ultimo - 1) in part.index:
    puntos.append(f"Participantes: {var(part[ultimo], part[ultimo - 1])} frente a {ultimo - 1} ({millones(part[ultimo - 1])}).")
if BASE in part.index and ultimo != BASE:
    partes = [f"participantes {var(part[ultimo], part[BASE])}"]
    if BASE in horas.index and ultimo in horas.index:
        partes.append(f"horas {var(horas[ultimo], horas[BASE])}")
    if BASE in credito.index and ultimo in credito.index:
        partes.append(f"crédito dispuesto {var(credito[ultimo], credito[BASE])}")
    puntos.append(f"Frente a {BASE}: " + ", ".join(partes) + ".")
if ultimo in credito.index and ultimo in part38.index:
    puntos.append(f"El crédito dispuesto fue de {millones(credito[ultimo])}€: {g.es(credito[ultimo] / part38[ultimo], 0)} € por participante "
                  f"y {g.es(horas[ultimo] / part[ultimo], 1)} horas de formación por participante.")
mod = reparto("10", "Participantes", ["Presencial", "Teleformación", "Mixta", "A distancia"])
tele = mod[mod.categoria == "Teleformación"].set_index("anyo").pct
if ultimo in tele.index:
    puntos.append(f"La teleformación concentra el {g.pct(tele[ultimo])} de los participantes"
                  + (f" (en {BASE}, el {g.pct(tele[BASE])})." if BASE in tele.index and ultimo != BASE else "."))
jov = reparto("01", "Participantes", ["De 16 a 25"]).set_index("anyo").pct
if ultimo in jov.index:
    puntos.append(f"Los participantes de 16 a 25 años son el {g.pct(jov[ultimo])} del total"
                  + (f" (en {BASE}, el {g.pct(jov[BASE])})." if BASE in jov.index and ultimo != BASE else "."))
r.respuesta(f"La formación bonificada llegó a {millones(part[ultimo])} de participantes en {ultimo}", puntos)

# --- cifras clave con su evolución ------------------------------------------------------------------------------
tarjetas = []
for titulo, s, fmt in (("Participantes formados", part, millones), ("Crédito dispuesto", credito, lambda v: millones(v) + "€"),
                       ("Horas de formación", horas, millones), ("Empresas formadoras", empresas, lambda v: g.es(v, 0))):
    if ultimo in s.index:
        p = s.get(ultimo - 1)
        tarjetas.append(dict(titulo=f"{titulo}, {ultimo}", valor=fmt(s[ultimo]), delta=im.delta_rel(s[ultimo], p),
                             bueno=None if p is None else s[ultimo] >= p, nota=f"frente a {ultimo - 1}",
                             serie=s.tolist(), desde=int(s.index.min()), hasta=ultimo))
im.tarjetas(tarjetas)
st.caption("FUNDAE publica el crédito «dispuesto» (el que las empresas han utilizado); no hay en estas series el crédito "
           "asignado, así que no se puede calcular el crédito disponible ni el % consumido.")

# --- 01 familias y distribución por comunidad ------------------------------------------------------------------
anyos = sorted(datos.q("SELECT DISTINCT anyo FROM fact_fundae WHERE serie IN ('14', '30')").anyo.tolist(), reverse=True)
anyo = st.selectbox("Año de las familias y de las comunidades", anyos, index=0, help="Familias profesionales y comunidades autónomas se publican desde 2019 y 2016.")

st.subheader("Familias formativas más activas")
fam = datos.q("SELECT categoria, valor FROM fact_fundae WHERE serie = '14' AND medida = 'Participantes' AND anyo = ?", [anyo])
tot = fam[fam.categoria == "Total"].valor
fam = fam[fam.categoria != "Total"]
if tot.empty or fam.empty:
    st.info("Sin datos de familias profesionales para este año.")
else:
    fam["pct"] = fam.valor / tot.iloc[0] * 100
    g.barras(g.top(fam[["categoria", "pct"]], "pct", 10, "fam")[["categoria", "pct"]], "categoria", "pct", fmt=",.1f", titulo_val="% de los participantes")

# --- contenidos formativos más frecuentes (serie 13 de FUNDAE, bonificada) -------------------------------------------
con = datos.q("SELECT categoria, valor FROM fact_fundae WHERE serie = '13' AND medida = 'Participantes' AND anyo = ? AND categoria <> 'Total'", [anyo])
if not con.empty:
    st.subheader("En qué se forman: contenidos más frecuentes")
    g.barras(g.top(con[["categoria", "valor"]], "valor", 10, "contenidos")[["categoria", "valor"]], "categoria", "valor", fmt=",.0f", titulo_val="Participantes formados")
    st.caption("Contenido formativo de la acción, en número de participantes (formación bonificada). No se expresa en % porque no se ha comprobado si un "
               "participante cuenta en más de un contenido. La formación subvencionada para desempleados no está en estas series.")

# --- 02 distribución por comunidad autónoma ---------------------------------------------------------------------
st.subheader("Distribución por comunidad autónoma")
cc = datos.q("""SELECT f.ccaa_id AS territorio_id, t.nombre, f.valor FROM fact_fundae f
                LEFT JOIN dim_territorio t ON t.territorio_id = f.ccaa_id
                WHERE f.serie = '30' AND f.medida = 'Participantes' AND f.anyo = ? AND f.ccaa_id IS NOT NULL""", [anyo])
tot_cc = datos.q("SELECT valor FROM fact_fundae WHERE serie = '30' AND medida = 'Participantes' AND anyo = ? AND categoria = 'Total'", [anyo])
if cc.empty or tot_cc.empty:
    st.info("Sin datos por comunidad autónoma para este año.")
else:
    cc["pct"] = cc.valor / tot_cc.valor.iloc[0] * 100
    cc["nombre"] = cc.nombre.map(g.corto)
    izq, der = st.columns([3, 2])
    with izq:
        g.mapa_ccaa(cc, "pct", fmt=",.1f", titulo="% de los participantes", escala=g.ESCALA)
    with der:
        g.barras(g.top(cc[["nombre", "pct"]], "pct", 10, "cc")[["nombre", "pct"]], "nombre", "pct", fmt=",.1f", titulo_val="% de los participantes", alto_fila=24)
    st.caption("Comunidad autónoma del participante. Cada comunidad en % del total nacional de participantes; no está "
               "corregido por población ni por número de trabajadores.")
# --- dónde puede haber oportunidades: demandantes jóvenes, contratos y formación, por comunidad ----------------------
op = (datos.q("""SELECT o.fecha, o.territorio_id, t.nombre, o.demandantes, o.demandantes_menores_25, o.contratos
                 FROM mart_oportunidad_ccaa o LEFT JOIN dim_territorio t USING (territorio_id)""")
      if datos.hay("mart_oportunidad_ccaa") else pd.DataFrame())
if not op.empty:
    st.subheader("Dónde puede haber oportunidades")
    op["fecha"] = pd.to_datetime(op.fecha)
    ult_op = op.fecha.max()
    ventana = op[op.fecha > ult_op - pd.DateOffset(months=12)]
    dem = op[op.fecha == ult_op].set_index("territorio_id")
    contr = ventana.groupby("territorio_id").contratos.sum(min_count=1)
    form = datos.q("SELECT ccaa_id AS territorio_id, valor FROM fact_fundae WHERE serie = '30' AND medida = 'Participantes' AND anyo = ? AND ccaa_id IS NOT NULL",
                   [anyo]).set_index("territorio_id").valor
    C1, C2, C3, C4 = ("Demandantes <25", "<25 (% demandantes)", "Contratos/año por demandante", f"Formación FUNDAE {anyo}")
    ccaa_op = pd.DataFrame({"Territorio": dem.nombre.map(g.corto), C1: dem.demandantes_menores_25, C2: dem.demandantes_menores_25 / dem.demandantes * 100,
                            C3: contr.reindex(dem.index) / dem.demandantes, C4: form.reindex(dem.index)}).dropna(subset=[C1, C2])
    total = pd.DataFrame([{"Territorio": "España", C1: dem.demandantes_menores_25.sum(), C2: dem.demandantes_menores_25.sum() / dem.demandantes.sum() * 100,
                           C3: contr.sum() / dem.demandantes.sum(), C4: form.reindex(dem.index).sum(min_count=1)}])
    tabla_op = pd.concat([total, ccaa_op.sort_values(C1, ascending=False)], ignore_index=True)
    st.dataframe(g.tabla_semaforo(tabla_op, "Territorio", "España", bajo_es_bueno=(C2,), sin_calor=(C1, C4),
                                  formatos={C1: lambda v: g.es(v), C3: lambda v: g.es(v, 2), C4: lambda v: g.es(v)}),
                 hide_index=True, width="stretch", height=min(35 * (len(tabla_op) + 1) + 3, 780))
    mejor, peor = ccaa_op.dropna(subset=[C3]).sort_values(C3).iloc[[-1, 0]].Territorio.tolist()
    st.caption(f"En gris, el total de España. En verde, mejor que ese total; en rojo, peor, y más intenso cuanto más se aleja. Menos jóvenes entre los demandantes "
               f"y más contratos por demandante se leen como más oportunidad. Hoy, {mejor} es la comunidad con más contratos por demandante y {peor} la que menos. "
               f"Demandantes: SEPE, {ult_op.strftime('%m/%Y')}; contratos: suma de los últimos 12 meses del SEPE. Participantes: FUNDAE, comunidad del participante. "
               "Los demandantes menores de 25 son los de la estadística del SEPE por municipio, que no da el nivel de estudios. Las series de FUNDAE que usamos "
               "son de formación bonificada y permisos: no hemos cargado la formación subvencionada para desempleados, así que la columna de formación no mide "
               "lo que reciben los demandantes. Los valores que el SEPE oculta por secreto estadístico (menos de 5) no se suman.")

# --- nivel de estudios de los parados registrados (SEPE, nacional) --------------------------------------------------
nf = (datos.q("SELECT fecha, nivel, hombres, mujeres, total FROM fact_sepe_demandantes_nivel")
      if datos.hay("fact_sepe_demandantes_nivel") else pd.DataFrame())
if not nf.empty:
    st.subheader("Nivel de estudios de las personas paradas")
    nf["fecha"] = pd.to_datetime(nf.fecha)
    mes_nf = nf.fecha.max()
    ult_nf = nf[(nf.fecha == mes_nf) & (nf.nivel != "Indeterminado")]
    ORDEN_NF = ult_nf.nivel.tolist()
    por_sexo = pd.concat([(ult_nf.hombres / ult_nf.hombres.sum() * 100).rename("pct").to_frame().assign(nivel=ult_nf.nivel, sexo="Hombres"),
                          (ult_nf.mujeres / ult_nf.mujeres.sum() * 100).rename("pct").to_frame().assign(nivel=ult_nf.nivel, sexo="Mujeres")])
    g.barras_grupo(por_sexo, "nivel", "sexo", "pct", fmt=",.1f", orden_series=["Hombres", "Mujeres"], orden_cat=ORDEN_NF,
                   titulo_val="% de las personas paradas de cada sexo", alto_fila=56)
    basico = ult_nf[ult_nf.nivel.str.startswith(("Estudios primarios", "Educación secundaria"))].total.sum() / ult_nf.total.sum() * 100
    univ = ult_nf[ult_nf.nivel == "Universitario"].total.sum() / ult_nf.total.sum() * 100
    st.caption(f"Parados registrados en el SEPE, {mes_nf.strftime('%m/%Y')} ({g.es(ult_nf.total.sum())} personas): el {g.pct(basico)} tiene como máximo la ESO y "
               f"el {g.pct(univ)}, estudios universitarios. Cada barra es el % sobre el total de su sexo. Es el conjunto de las personas paradas registradas, "
               "a nivel nacional: el SEPE no publica este dato por edad ni por comunidad (para los jóvenes, ver el paro por estudios del Dashboard 2). "
               "No se muestra el grupo «Indeterminado» (menos del 0,1 %).")

# --- 03 modalidad a lo largo del tiempo -------------------------------------------------------------------------
st.subheader("Cómo se forma: presencial, teleformación y mixta")
if not mod.empty:
    izq, der = st.columns([3, 2])
    with izq:
        im.apiladas(fecha(mod[mod.valor > 0].assign(serie=lambda x: x.categoria)), "fecha", "serie", "valor", orden_series=["Presencial", "Teleformación", "Mixta", "A distancia"],
                    titulo_y="% de los participantes", alto=260, cols_leyenda=4)
    with der:
        ult = mod[mod.anyo == ultimo]
        im.rosco(ult, "categoria", "valor", orden=["Presencial", "Teleformación", "Mixta", "A distancia"], centro=str(ultimo), sub="participantes")
    st.caption("Reparto de los participantes por modalidad de impartición, año a año (cada año suma el 100 %). Ojo con 2016: «A distancia» "
               "solo tiene participantes hasta 2015 y «Mixta» cae de 430.154 a 71.221 entre 2015 y 2016, a la vez que suben «Presencial» y "
               "«Teleformación»; parece un cambio de clasificación de FUNDAE (no se ha investigado), así que conviene no comparar antes y "
               "después de 2016 sin comprobarlo.")

# --- tendencias: base 100 ---------------------------------------------------------------------------------------
st.subheader("Tendencias y evolución")
st.markdown(f"**Participantes, horas, crédito y empresas, con {BASE} = 100**")
indices = {"Participantes": part, "Horas": horas, "Crédito dispuesto": credito, "Empresas formadoras": empresas}
ev = pd.concat([(s / s[BASE] * 100).rename("indice").reset_index().assign(serie=n) for n, s in indices.items() if BASE in s.index], ignore_index=True)
ev = fecha(ev[ev.anyo >= BASE])
im.lineas_etiquetadas(ev, "fecha", "indice", "serie", fmt=",.0f", titulo_y=f"Índice ({BASE} = 100)", orden_series=[n for n in indices if n in set(ev.serie)])
st.caption("La caída de 2020 coincide con la pandemia; los saltos de horas entre 2015 y 2016 y de 2023 a 2024 son de las propias series de "
           "FUNDAE (no se ha investigado su causa).")
medida = st.radio("Serie completa desde 2004", list(indices), horizontal=True)
im.area_gradiente(fecha(indices[medida].rename("valor").reset_index()), "fecha", "valor", fmt=",.0f", titulo_y=medida)

# --- perfil del participante ------------------------------------------------------------------------------------
st.subheader("Quién se forma")
izq, der = st.columns(2)
with izq:
    st.markdown("**Por edad**")
    cats = ["De 16 a 25", "De 26 a 35", "De 36 a 45", "De 46 a 55", "Mayores de 55"]
    ed = reparto("01", "Participantes", cats)
    if not ed.empty:
        im.apiladas(fecha(ed.assign(serie=ed.categoria)), "fecha", "serie", "valor", orden_series=cats, colores=g.RAMPA, titulo_y="% de los participantes", alto=300, cols_leyenda=2, paso_x=4)
with der:
    st.markdown("**Por nivel de estudios**")
    cats = ["Estudios primarios", "Estudios secundarios", "Estudios terciarios", "Otras titulaciones"]
    es_ = reparto("04", "Participantes", cats)
    if not es_.empty:
        im.apiladas(fecha(es_.assign(serie=es_.categoria)), "fecha", "serie", "valor", orden_series=cats, colores=[g.RAMPA[0], g.RAMPA[2], g.RAMPA[4], g.ORO_PALIDO],
                    titulo_y="% de los participantes", alto=300, cols_leyenda=2, paso_x=4)
if not jov.empty:
    st.markdown("**Participantes de 16 a 25 años, en % del total**")
    im.area_gradiente(fecha(jov.rename("valor").reset_index()), "fecha", "valor", fmt=".1f", titulo_y="% de los participantes", color=g.C2, alto=200)
    st.caption("Es el único grupo de edad joven que publica FUNDAE (de 16 a 25): no hay un corte 16-29.")

# --- empresas: pymes frente a grandes ---------------------------------------------------------------------------
st.subheader("Empresas: quién forma y quién gasta el crédito")
TAM = ["De 1 a 9", "De 10 a 49", "De 50 a 249", "Más de 249"]
em, cr = reparto("38", "Empresas formadoras", TAM), reparto("38", "Crédito dispuesto", TAM)
if not em.empty and not cr.empty:
    ult_t = int(min(em.anyo.max(), cr.anyo.max()))
    ambos = pd.concat([em[em.anyo == ult_t].assign(serie="% de las empresas formadoras"), cr[cr.anyo == ult_t].assign(serie="% del crédito dispuesto")])
    g.barras_grupo(ambos.rename(columns={"categoria": "tamaño"}), "tamaño", "serie", "pct", fmt=",.1f", orden_series=["% de las empresas formadoras", "% del crédito dispuesto"],
                   titulo_val=f"%, {ult_t}", orden_cat=TAM, alto_fila=78)
    micro, grande = em[(em.anyo == ult_t) & (em.categoria == TAM[0])].pct, em[(em.anyo == ult_t) & (em.categoria == TAM[-1])].pct
    cmi, cgr = cr[(cr.anyo == ult_t) & (cr.categoria == TAM[0])].pct, cr[(cr.anyo == ult_t) & (cr.categoria == TAM[-1])].pct
    if not (micro.empty or grande.empty or cmi.empty or cgr.empty):
        st.caption(f"En {ult_t}, las empresas de 1 a 9 trabajadores son el {g.pct(micro.iloc[0])} de las que forman y se llevan el {g.pct(cmi.iloc[0])} del "
                   f"crédito dispuesto; las de más de 249 son el {g.pct(grande.iloc[0])} y utilizan el {g.pct(cgr.iloc[0])}.")

