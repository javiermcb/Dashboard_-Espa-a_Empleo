import pandas as pd
import streamlit as st

from comun import acceso

st.title("Administración de accesos")
if not (st.session_state.get("usuario") or {}).get("admin"):
    st.error("Solo para el administrador.")
    st.stop()
st.caption("Emails con acceso y solicitudes. Todo se guarda en el repositorio privado del registro en GitHub y solo se ve aquí.")
if acceso.autorizados() is None:
    st.warning("El registro no está configurado (faltan RRHH_LOG_TOKEN y RRHH_LOG_REPO en los secretos): ahora entra cualquier email.")
    st.stop()


def hecho(ok, texto):
    if ok:
        st.toast(texto)
        st.rerun()
    st.error("GitHub no ha confirmado el cambio. Vuelve a intentarlo.")


st.subheader("Solicitudes pendientes")
pend = [s for s in acceso.solicitudes() if s.get("estado") == "pendiente"]
if not pend:
    st.info("No hay solicitudes pendientes.")
for s in pend:
    c = st.columns([3, 3, 1, 1])
    c[0].markdown(f"**{s['email']}**  \n{s['fecha_utc']} UTC")
    c[1].write(s.get("motivo") or "—")
    if c[2].button("Aprobar", key=f"ok_{s['email']}", type="primary"):
        hecho(acceso.resolver(s["email"], "aprobada"), f"{s['email']} ya tiene acceso")
    if c[3].button("Rechazar", key=f"no_{s['email']}"):
        hecho(acceso.resolver(s["email"], "rechazada"), f"Solicitud de {s['email']} rechazada")

st.subheader("Dar acceso a un email")
with st.form("alta", clear_on_submit=True):
    nuevo = st.text_input("Email").strip().lower()
    if st.form_submit_button("Dar acceso", type="primary"):
        if not acceso.RX_EMAIL.match(nuevo):
            st.error("Escribe un email válido.")
        else:
            hecho(acceso.autorizar(nuevo), f"{nuevo} ya tiene acceso")

st.subheader("Emails con acceso")
st.caption("Los emails se guardan seudonimizados: aquí se ve solo una pista de cada uno. Para quitar a alguien cuyo "
           "email conoces, también puedes usar «Borrar todos los datos de un email» más abajo.")
lista = sorted(acceso.autorizados() or [], key=lambda f: f.get("pista", ""))
if not lista:
    st.info("Todavía no hay emails autorizados (además del tuyo).")
for f in lista:
    c = st.columns([4, 2, 1])
    c[0].write(f.get("pista") or "—")
    c[1].caption(f"Alta {str(f.get('fecha_alta', ''))[:10]} · {f.get('origen', '')}")
    if c[2].button("Quitar", key=f"quitar_{f['huella']}"):
        hecho(acceso.quitar(f["huella"]), f"Acceso retirado a {f.get('pista')}")

with st.expander("Historial de solicitudes"):
    st.dataframe(pd.DataFrame(acceso.solicitudes()), hide_index=True, width="stretch")

st.subheader("Protección de datos")
st.caption(f"Solo se anota la fecha y hora de cada entrada, con el email seudonimizado. Ese registro y las solicitudes "
           f"resueltas se borran solos a los {acceso.meses_retencion()} meses (una vez al día, con el primer acceso; "
           "secreto RRHH_RETENCION_MESES). El botón aplica la limpieza ahora: seudonimiza lo que quedara en claro, borra "
           "lo antiguo y compacta el historial.")
if st.button("Aplicar ahora la limpieza"):
    try:
        st.toast(f"Retención aplicada: {acceso.purgar()} registros mensuales borrados")
    except Exception as e:
        st.error(f"No se ha podido aplicar: {type(e).__name__}")
with st.form("supresion", clear_on_submit=True):
    st.markdown("**Borrar todos los datos de un email** (si alguien ejerce su derecho de supresión): lo quita de la "
                "lista de autorizados, de las solicitudes y de todos los registros de accesos. No se puede deshacer.")
    borrar = st.text_input("Email a borrar").strip().lower()
    seguro = st.checkbox("Entiendo que no se puede deshacer")
    if st.form_submit_button("Borrar sus datos"):
        if not acceso.RX_EMAIL.match(borrar):
            st.error("Escribe un email válido.")
        elif not seguro:
            st.error("Marca la casilla para confirmar.")
        else:
            hecho(acceso.suprimir(borrar), f"Datos de {borrar} borrados")
