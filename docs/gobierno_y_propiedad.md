# Gobierno y propiedad del proyecto

Documento para cerrar quién es responsable de qué. **Lo que está entre «[ ]» lo tiene que rellenar una persona: no se ha dado por
sabido.** Última revisión: 29/10/2026.

## 1. Qué existe y dónde vive hoy

| Pieza | Dónde está hoy | Quién la controla hoy |
|---|---|---|
| Repositorio `Dashboard_-Espa-a_Empleo` (público) | cuenta personal de GitHub `javiermcb` | `javiermcb` |
| 3 dashboards (D1, D2, D3) | Streamlit Community Cloud, desplegados desde `main` | cuenta de Streamlit de `javiermcb` |
| Carga diaria y avisos | GitHub Actions del mismo repositorio | `javiermcb` |
| Datos publicados | rama `datos-modelo` (se reescribe en cada carga) y etiquetas mensuales `datos-AAAA-MM` | `javiermcb` |
| Proyecto `Datos_INE` | repositorio aparte, independiente de este | `javiermcb` |

Variables de Actions que usa el proyecto (no son secretos): `APP_URL_1`, `APP_URL_2`, `APP_URL_3`, `RRHH_PUBLICO_REPO` (opcional).
En Streamlit: `RRHH_DATOS` (URL de los datos). No hay claves ni tokens.

## 2. Responsables

| Rol | Nombre | Contacto |
|---|---|---|
| Titular de los derechos del código y del diseño | [ ] | [ ] |
| Responsable técnico (cambios y despliegue) | [ ] | [ ] |
| Suplente técnico | [ ] | [ ] |
| Responsable del contenido (valida cifras y textos) | [ ] | [ ] |
| Quien recibe los avisos de fallo (issues y correo) | [ ] | [ ] |

Sin suplente, si la persona responsable no está, nadie puede arreglar una carga rota ni un despliegue caído.

## 3. Migración prevista a una cuenta de organización

Decidido: el proyecto pasará a una cuenta de organización cuando esté todo validado. Lista de pasos (hacerlos en este orden):

1. Cerrar antes lo pendiente de validación: titularidad de los derechos, autorización de uso de marca, condiciones de reutilización de FUNDAE y Eurostat (sección 5).
2. Crear la organización con **al menos dos propietarios** y autenticación en dos pasos obligatoria.
3. Transferir el repositorio (Settings → Transfer). GitHub redirige la URL antigua, pero **la URL de los datos cambia**: actualizar `RRHH_DATOS` en cada app de Streamlit y la variable `RRHH_PUBLICO_REPO` si se usa.
4. Volver a desplegar las tres apps desde el repositorio de la organización y actualizar `APP_URL_1..3` en las variables de Actions.
5. Volver a activar: *Automatically delete head branches*, Dependabot, escaneo de secretos con protección de subida, y las reglas de rama (sección 4).
6. Lanzar «Pipeline RRHH» y «Comprobar el despliegue de la barra lateral» a mano y comprobar que dan verde.
7. Avisar a quien tenga los dashboards incrustados (los iframes apuntan a las URL de `streamlit.app`, que cambian si se redespliegan con otro nombre).

## 4. Ajustes de seguridad que hay que activar en GitHub (no se pueden fijar desde el código)

- Autenticación en dos pasos (preferible llave de acceso) en todas las cuentas con permiso de escritura.
- Reglas de rama o conjunto de reglas para `main` y `datos-modelo`: sin push directo ni force-push salvo el workflow de publicación, y pull request obligatorio en `main`.
- Quién tiene permiso de escritura: revisar la lista de colaboradores. Quien pueda escribir puede cambiar los datos que ven las apps.
- *Private vulnerability reporting* y *Secret scanning / Push protection* en Settings → Code security.

**Estado:** no se ha podido comprobar desde el código cuáles de estos ajustes están activos hoy. Marcarlos aquí cuando se confirmen: [ ] 2FA · [ ] reglas de rama · [ ] colaboradores revisados · [ ] avisos privados · [ ] escaneo de secretos.

## 5. Pendientes que dependen de terceros (no son de código)

| Tema | Qué falta | De quién depende |
|---|---|---|
| Derechos del código y del diseño | Cesión o autorización por escrito si el trabajo se hizo en un máster o unas prácticas | Titular, centro formativo y Fundación |
| Marca | Autorización de uso de los colores y el nombre de la Fundación Gi Group | Fundación Gi Group |
| FUNDAE | Revisar su aviso legal sobre la extracción automática y la redistribución de sus series; confirmar si 2025 es «definitivo» | FUNDAE / asesoría legal |
| Eurostat, SEPE, INE, Seguridad Social | Citar la fuente tal y como piden; la página «Datos y descargas» hoy no cita FUNDAE ni Eurostat | Responsable de contenido |
| Streamlit Community Cloud | Confirmar que sus condiciones permiten el uso previsto y la visita automática que mantiene las apps despiertas | Responsable técnico |
| Descargo de responsabilidad | Texto «no es estadística oficial; los organismos no participan» en los tres dashboards | Responsable de contenido y asesoría legal |

## 6. Qué hacer si algo falla

- Carga rota: issue `Incidencias de carga del pipeline RRHH` (llega por correo a quien siga el repositorio). Las apps siguen con la última carga buena.
- Dashboard caído: issue `Un dashboard no responde`. Si es error 500 de la plataforma, esperar y reintentar.
- Datos viejos: issue `Los datos publicados están desactualizados` (aviso si pasan más de 96 horas).
- Cifras que no cuadran con las oficiales: issue `Cifras del modelo que no cuadran con las oficiales`.
- Saber qué mostraba un dashboard un mes concreto: etiqueta `datos-AAAA-MM` (se conservan las 12 últimas).
- Guía paso a paso: `docs/guia_puesta_en_marcha.md`.

## 7. Revisión periódica

Mensual: pull requests de Dependabot, issues abiertas, y comprobar que «Pipeline RRHH» y «Mantener las apps activas» siguen ejecutándose
(GitHub desactiva los workflows programados de un repositorio público tras 60 días sin actividad).
Cuando haya datos nuevos oficiales (EPA, FUNDAE, SEPE): añadir filas a `pipeline/referencias_oficiales.csv`.
