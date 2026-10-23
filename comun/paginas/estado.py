import pandas as pd
import streamlit as st

from comun import datos

st.title("Estado de los datos")
st.caption("Qué fuentes se actualizaron en la última carga diaria, hasta qué periodo llega cada tabla y si la app ha "
           "podido descargarlas. Una fuente que falla un día no deja la tabla vacía: se usa su última carga buena.")

carga = datos.fecha_carga()
st.metric("Última carga del pipeline", carga or "desconocida")

errores = datos.errores_descarga()
if errores:
    st.subheader("Descargas fallidas en la app")
    st.warning("La app no ha podido descargar estas tablas en su último refresco; muestra la copia anterior si la tenía.")
    st.dataframe(pd.DataFrame(sorted(errores.items()), columns=["Tabla", "Motivo"]), hide_index=True, width="stretch")

ESTADOS = {"OK": "✅ Actualizada", "ANTERIOR": "🟠 Última carga buena (la web falló)", "AVISO": "🟡 Actualizada con avisos",
           "ERROR": "🔴 Sin datos"}

st.subheader("Fuentes SEPE, Seguridad Social y Ministerio de Trabajo")
F = datos.csv_extra("fuentes_carga.csv")
if F.empty:
    st.info("Esta carga no incluye el informe de fuentes (se publica a partir de la próxima carga del pipeline).")
else:
    F["Estado"] = F.estado.map(ESTADOS).fillna(F.estado)
    c = st.columns(4)
    for i, (k, v) in enumerate(ESTADOS.items()):
        c[i].metric(v.split(" ", 1)[1], int((F.estado == k).sum()))
    st.dataframe(F[["tabla", "Estado", "filas", "desde", "hasta", "tiempo", "detalle"]].rename(
        columns={"tabla": "Fuente", "filas": "Filas", "desde": "Desde", "hasta": "Hasta", "tiempo": "Tiempo", "detalle": "Detalle"}),
        hide_index=True, width="stretch")

st.subheader("Tablas del INE")
I = datos.csv_extra("ine_carga.csv")
if I.empty:
    st.info("Esta carga no incluye el informe del INE (se publica a partir de la próxima carga del pipeline).")
else:
    I["Estado"] = I.estado.map(ESTADOS).fillna(I.estado)
    st.caption(f"{int((I.estado == 'OK').sum())} de {len(I)} tablas actualizadas.")
    st.dataframe(I[["tabla_id", "tema", "Estado", "fecha_min", "fecha_max", "error"]].rename(
        columns={"tabla_id": "Tabla INE", "tema": "Tema", "fecha_min": "Desde", "fecha_max": "Hasta", "error": "Error"}),
        hide_index=True, width="stretch")

st.subheader("Periodo que cubre cada tabla del modelo")
R = datos.csv_extra("resumen_fuentes.csv")
meta = datos.metadatos().get("ficheros", {})
if not R.empty:
    st.dataframe(R.rename(columns={"tabla": "Tabla", "filas": "Filas", "desde": "Desde", "hasta": "Hasta",
                                   "sin_territorio": "Filas sin territorio"}), hide_index=True, width="stretch")
elif meta:
    st.dataframe(pd.DataFrame([{"Tabla": k, "Filas": v.get("filas")} for k, v in meta.items()]), hide_index=True, width="stretch")
