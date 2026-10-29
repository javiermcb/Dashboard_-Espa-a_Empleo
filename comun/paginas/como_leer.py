import streamlit as st

st.title("Cómo leer estos datos")
st.caption("Definiciones y límites de las cifras de los tres dashboards, para no compararlas mal. Son cálculos propios a partir de "
           "fuentes oficiales (INE, Eurostat, SEPE, Seguridad Social, Ministerio de Trabajo y FUNDAE); no son una publicación de esos organismos.")

st.subheader("Fecha de carga y periodo del dato")
st.markdown(
    "- La fecha que aparece en la barra lateral y en el pie es la **última carga**: cuándo el sistema descargó las fuentes. "
    "No es la fecha de los datos.\n"
    "- El **periodo** de cada dato está en su gráfico y en «Estado de los datos». Los organismos publican con retraso: el SEPE por "
    "nivel formativo lleva unos cuatro meses, y FUNDAE llega hasta el último año que ha publicado.\n"
    "- Los últimos años de FUNDAE pueden revisarse cuando cierre sus datos.")

st.subheader("Paro: EPA frente a paro registrado")
st.markdown(
    "- **EPA (INE):** encuesta a hogares. Mide quién está sin trabajo, lo busca y está disponible, se haya inscrito o no. "
    "Los dashboards 1 y 2 usan sus medias anuales.\n"
    "- **Paro registrado (SEPE):** personas inscritas como demandantes parados. Lo usa el Dashboard 3.\n"
    "- Son definiciones distintas con cifras distintas. **No se pueden comparar entre sí** ni mezclar en una misma cuenta.")

st.subheader("Cifras de una encuesta: el error muestral")
st.markdown(
    "La EPA es una muestra. En comunidades pequeñas y en grupos de edad estrechos el margen de error puede ser grande: "
    "una diferencia de pocas décimas, o un cambio de puesto en un ranking, no significa necesariamente que algo haya cambiado.")

st.subheader("Jóvenes NEET")
st.markdown(
    "- Jóvenes de **15 a 29 años** que ni estudian ni trabajan, en % de la población de esa edad (definición del INE y de Eurostat). "
    "No existe una cifra oficial de 16 a 29.\n"
    "- El reparto de los NEET por nivel de formación es un **cálculo propio** (tasa de Eurostat por nivel × población por nivel).")

st.subheader("Formación bonificada (FUNDAE)")
st.markdown(
    "- «Participantes» son las **participaciones en cursos**: una persona que hace varios cursos cuenta varias veces. "
    "No es el número de personas distintas.\n"
    "- Son datos de formación **bonificada y permisos**, por años naturales. No incluyen la formación subvencionada para desempleados.\n"
    "- FUNDAE publica el crédito «dispuesto» (el que las empresas han utilizado). No hay crédito asignado, así que no se calcula el % consumido.\n"
    "- Las horas de formación tienen saltos en las propias series de FUNDAE entre 2015 y 2016 y entre 2023 y 2024; están señalados en los gráficos.")

st.subheader("Demandantes, contratos y afiliados")
st.markdown(
    "- Los **contratos** son episodios: una persona puede firmar varios, y en lugares con mucha estacionalidad abundan los contratos cortos. "
    "Contratos por demandante compara territorios; no mide cuánta oportunidad tiene una persona.\n"
    "- Los **demandantes** incluyen a quien ya trabaja y busca cambiar de empleo.\n"
    "- El SEPE oculta los valores inferiores a 5 por secreto estadístico; esos valores no se suman.\n"
    "- Los **afiliados** a la Seguridad Social por sector son de todas las edades y muestran dónde ha crecido el empleo, "
    "no una previsión ni dónde hay más oportunidad para jóvenes.\n"
    "- El SEPE por nivel formativo solo tiene cargados los meses recientes: es una foto, no una tendencia, y los contratos tienen estacionalidad.")

st.subheader("Si una cifra no coincide con otra publicación")
st.markdown(
    "Comprueba primero el periodo, la definición (arriba) y si es una media anual o un mes. "
    "El sistema contrasta cada carga con varias cifras oficiales publicadas y avisa a los responsables cuando alguna deja de coincidir. "
    "Las tablas completas se pueden descargar en «Datos y descargas».")
