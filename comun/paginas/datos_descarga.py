import pandas as pd
import streamlit as st

from comun import datos

st.title("Datos y descargas")
st.caption("Las tablas del modelo que usa este dashboard, con filtros y descarga en CSV (separador ';' para abrirlo en Excel en español).")
st.caption("Al reutilizar estos datos hay que citar la fuente («Elaboración propia con datos extraídos del sitio web del "
           "INE (www.ine.es), del SEPE, de la Seguridad Social, del Ministerio de Trabajo y Economía Social, de FUNDAE "
           "(www.fundae.es) y de Eurostat (ec.europa.eu/eurostat)», según la fuente de cada tabla), no "
           "desvirtuar su sentido, indicar su fecha de actualización (en «Estado de los datos») y no dar a entender que "
           "estos organismos participan en el uso que se haga.")

_, disponibles, _ = datos.conexion()
DESCR = {
    "fact_sepe_paro_municipio": "SEPE · paro registrado por municipio y mes",
    "fact_sepe_demandantes_municipio": "SEPE · demandantes de empleo por municipio y mes",
    "fact_sepe_contratos_municipio": "SEPE · contratos por municipio y mes",
    "fact_ss_afiliacion": "Seguridad Social · afiliación",
    "fact_incapacidad_temporal": "Seguridad Social · incapacidad temporal por provincia",
    "fact_ett_mensual": "ETT · CPD por modalidad, cesiones y perfil (mensual)",
    "fact_ett_territorio": "ETT · CPD por CCAA y provincia",
    "fact_ett_actividad": "ETT · CPD por división CNAE",
    "fact_ett_resumen": "ETT · acumulado del año con variación oficial",
    "fact_cpd_actividad": "ETT · CPD por sección y mes",
    "fact_convenios": "Convenios · serie nacional",
    "fact_convenios_detalle": "Convenios · sector, territorio, jornada y cláusula",
    "fact_accidentes": "Accidentes · por CCAA y provincia",
    "fact_accidentes_detalle": "Accidentes · detalle (gravedad, sector, sexo y edad…)",
    "fact_regulacion_empleo": "ERE y ERTE · últimos 10 meses",
    "fact_fundae": "FUNDAE · formación bonificada por año natural",
    "fact_eurostat": "Eurostat · empleo, paro y NEET, España y UE-27",
    "mart_neet": "INE · jóvenes NEET (15-29) por territorio",
    "mart_tasas_epa": "INE · EPA: tasas de actividad, empleo y paro",
    "mart_sectores_empleo": "Seguridad Social · afiliados por sector (CNAE)",
    "mart_oportunidad_ccaa": "SEPE · demandantes y contratos por comunidad",
    "fact_sepe_demandantes_nivel": "SEPE · parados registrados por nivel formativo",
    "fact_sepe_contratos_nivel": "SEPE · contratos por nivel formativo",
}
# Qué mide cada tabla y qué no (el detalle está en «Cómo leer estos datos»)
NOTAS = {
    "fact_fundae": "«Participantes» son participaciones en cursos: una persona que hace varios suma varias veces. Formación bonificada y permisos; "
                   "no incluye la subvencionada para desempleados. Crédito «dispuesto» (utilizado), no asignado. Los últimos años pueden revisarse.",
    "fact_eurostat": "Indicadores de la Encuesta de Población Activa europea (muestra): pueden tener error muestral. Algunos NEET por nivel son cálculos propios.",
    "mart_neet": "Jóvenes de 15 a 29 años que ni estudian ni trabajan, en % de su población. No existe una cifra oficial de 16 a 29.",
    "mart_tasas_epa": "EPA (encuesta a hogares), medias anuales. No coincide con el paro registrado del SEPE. En comunidades pequeñas y grupos de edad estrechos el error muestral puede ser grande.",
    "mart_sectores_empleo": "Afiliados medios, todas las edades, años completos y variación anual. Muestra dónde ha crecido el empleo; no es una previsión ni mide la oportunidad para jóvenes.",
    "mart_oportunidad_ccaa": "Los contratos son episodios, no personas; los demandantes incluyen a quien ya trabaja y busca cambiar. Sirve para comparar territorios, no para medir oportunidad.",
    "fact_sepe_demandantes_nivel": "Paro registrado (inscritos como demandantes parados), nacional y mensual, sin la fila «Total». No comparable con el paro de la EPA.",
    "fact_sepe_contratos_nivel": "Contratos registrados (episodios, no personas), nacional y mensual, sin la fila «Total». Tienen estacionalidad.",
}
for _t in ("fact_sepe_paro_municipio", "fact_sepe_demandantes_municipio", "fact_sepe_contratos_municipio"):
    NOTAS[_t] = "SEPE por municipio y mes. Los valores inferiores a 5 los oculta el SEPE por secreto estadístico y no se suman."
tablas = sorted([t for t in disponibles if t not in ("dim_tiempo", "alertas")], key=lambda t: (t.startswith("dim_"), t))
nombre = st.selectbox("Tabla", tablas, format_func=lambda t: f"{t} — {DESCR.get(t, '')}".rstrip(" —"))
assert nombre in tablas  # el nombre de tabla no puede ir como parámetro: solo se admiten los de la lista
st.caption(NOTAS.get(nombre, "Definiciones y límites de las cifras: página «Cómo leer estos datos».") + " Más en «Cómo leer estos datos».")
cols = datos.q(f"SELECT * FROM {nombre} LIMIT 0").columns.tolist()
n_total = int(datos.q(f"SELECT count(*) AS n FROM {nombre}").n.iloc[0])

filtros, params = [], []
c = st.columns(3)
if "territorio_id" in cols:
    terr = datos.territorios()
    elegidos = c[0].multiselect("Territorio", terr.territorio_id, placeholder="Todos", format_func=lambda k: terr.set_index("territorio_id").loc[k, "nombre"])
    if elegidos:
        filtros.append(f"territorio_id IN ({','.join('?' * len(elegidos))})"); params += elegidos
if "provincia_id" in cols and nombre.startswith("fact_sepe"):
    terr = datos.territorios()
    pv = c[1].selectbox("Provincia (municipios)", [""] + terr[terr.nivel == "Provincia"].territorio_id.tolist(),
                        format_func=lambda k: "Todas" if not k else terr.set_index("territorio_id").loc[k, "nombre"])
    if pv:
        filtros.append("provincia_id = ?"); params.append(pv)
if "fecha" in cols:
    rango = datos.q(f"SELECT min(fecha) AS a, max(fecha) AS b FROM {nombre}")
    if not rango.empty and pd.notna(rango.a.iloc[0]):
        a, b = pd.Timestamp(rango.a.iloc[0]).date(), pd.Timestamp(rango.b.iloc[0]).date()
        desde = c[2].date_input("Desde", value=max(a, b.replace(year=b.year - 2)), min_value=a, max_value=b)
        filtros.append("fecha >= ?"); params.append(desde)
where = (" WHERE " + " AND ".join(filtros)) if filtros else ""
n = int(datos.q(f"SELECT count(*) AS n FROM {nombre}{where}", params).n.iloc[0])
st.caption(f"{n:,} filas con estos filtros (de {n_total:,}).".replace(",", "."))
LIMITE = 200_000
df = datos.q(f"SELECT * FROM {nombre}{where} LIMIT {LIMITE}", params)
st.dataframe(df.head(1000), hide_index=True, width="stretch")
if n > LIMITE:
    st.warning(f"La descarga se limita a {LIMITE:,} filas: añade filtros para bajar el resto.".replace(",", "."))
st.download_button("Descargar CSV", df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"), file_name=f"{nombre}.csv", mime="text/csv")
