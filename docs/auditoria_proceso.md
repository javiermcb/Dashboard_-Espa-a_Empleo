# Auditoría crítica del proceso (23/10/2026)

Revisión de todo lo hecho para llevar la lógica de `Datos_INE` a un repositorio con una carga común y tres dashboards.
Cada hallazgo indica **evidencia**, **estado** y **qué hacer**. Lo que no se pudo comprobar está en la sección 5 y no se
da por bueno.

## 1. Resumen

| Área | Valoración | En una línea |
|---|---|---|
| Carga de datos | Funciona, con arranque en frío frágil | Publica 46 tablas desde `main`; la primera carga falló por un timeout y un defecto mío |
| Dashboards | Funcionan con lo que hay | Paneles con datos reales; 5 paneles sin fuente (2 del Dashboard 1, 3 del 2) y uno solo parcial |
| Eficiencia | **Mal** | Pipeline duplicado en dos repos; cada app descarga 43 tablas para usar 2 o 3 |
| Pruebas | Insuficientes | Detectan que una página no falla, no que la cifra sea correcta |
| Seguridad y privacidad | Aceptable | Sin secretos en el código ni en el historial; repositorio público desde el 26/10 |
| Documentación | Mejorable | Parte heredada desfasada (marcada ya como tal) |

## 2. Lo que está bien (con evidencia)

- **La carga completa publica**: run 12 en `main` (23/10, 07:00 UTC) publicó `datos-modelo` con 46 tablas; ERE/ERTE cargó
  19.060 filas y FUNDAE 7.302 (16 de 18 series).
- **El control de calidad funciona como diseñado**: la primera carga no publicó porque faltaban 4 tablas exigidas; no
  llegó nada incompleto a los dashboards.
- **Las acciones están fijadas por SHA** y el workflow declara permisos explícitos (`contents` e `issues` en escritura,
  necesarios para publicar `datos-modelo` y abrir avisos).
- **Sin secretos en el código**: búsqueda de patrones habituales (tokens `github_pat_`/`ghp_`, claves AWS, claves privadas,
  contraseñas) sin resultados en los ficheros actuales.
- **Las cifras mostradas son reales**, no las de las maquetas (que eran ejemplos): NEET 11,5 % en 2025, actividad
  16-24 del 37,6 %, 6,76 M de participantes FUNDAE.
- **Se respeta el secreto estadístico**: el SEPE oculta valores `<5` y el pipeline los deja vacíos.

## 3. Hallazgos

### Alta

**H1 · Pipeline duplicado en dos repositorios** — *aceptado (decisión del 26/10/2026)*
- Evidencia: `Datos_INE` y este repo ejecutan cada día laborable la misma carga contra las mismas webs. Una carga completa
  dura entre 15 y 29 minutos (medido: 26, 15, 29 y 18).
- Riesgo: el doble de minutos de Actions y de carga sobre las webs oficiales; los dos conjuntos de datos pueden diverger;
  dos sitios que mantener cuando una web cambia de formato.
- Decisión: `Datos_INE` y este repositorio son **proyectos distintos** y conviven, cada uno con su carga. Se acepta el
  coste duplicado. Si en el futuro se unifican, la opción coherente sería que este repo haga la carga y la app original
  lea de aquí.

**H2 · `Datos_INE` sin publicar desde el 16/10** — *corregido, sin verificar*
- Evidencia: la carga del 22/10 falla en «Guardar la publicación como artefacto» y se salta el control y la publicación
  (comprobado en sus pasos). Las del 19, 20 y 21/10 también terminan en fallo; no se revisó la causa de cada una, pero
  coincide con la cuota llena.
- Corregido: paso no bloqueante y retención de 3 días (PR #19 de `Datos_INE`), y borrado de 51 de 56 artefactos.
- Falta: **ver una carga programada posterior** terminar en verde. Aún no ha ocurrido.

**H3 · Tres defectos míos en el traslado, hallados por la carga real, no por las pruebas** — *corregidos*
- Faltaba `catalogo_fuentes.py`: `fuentes.py` no arrancaba y no se cargaban SEPE, Seguridad Social, Ministerio ni FUNDAE.
- El paso del informe de calidad suponía que la rama `calidad` existía (PR #11).
- `datos.py` importaba `calculos_informe` con el nombre antiguo (código sin uso, ya eliminado).
- Causa común: se declaró «hecho» tras pruebas locales sobre una muestra. La prueba que habría evitado los dos primeros
  era ejecutar la carga completa antes de fusionar, y eso solo se hizo después de abrir los PR.
- Hacer: antes de dar por bueno un traslado de pipeline, una carga completa en una rama y la lista de «cosas que solo
  existen en producción» (ramas, secretos, caché, ficheros fuera de la carpeta copiada).

**H4 · Cada app descarga 43 tablas para usar 2 o 3** — *corregido el 26/10/2026 (PR #18)*
- Evidencia: `comun/datos.py` carga `TABLAS` + `OPCIONALES` (43) al arrancar. Dashboard 1 usa `mart_neet`, Dashboard 2
  `mart_tasas_epa` y Dashboard 3 `fact_fundae`, más `dim_territorio`. Solo 5 tablas del SEPE, la Seguridad Social y
  el INE pesan unos **36 MB**.
- Riesgo: arranques en frío lentos y más memoria en el plan gratuito de Streamlit (límites **sin comprobar**), y más
  descargas desde GitHub cada 6 horas por app (la caché dura 6 h).
- Hecho: cada dashboard declara sus tablas en `arrancar(..., tablas=[...])` y `datos.py` descarga y abre solo esas. El
  control de calidad del pipeline sigue exigiendo la lista completa. Con los datos publicados, el Dashboard 1 abre
  `dim_territorio` y `mart_neet` (unos 0,1 MB) más las alertas, sin tablas «no disponibles». **Sin verificar** el
  efecto en el arranque en frío y la memoria de las apps desplegadas.

### Media

**H5 · Arranque en frío frágil** — *mitigado*
- Evidencia: el timeout de `www.mites.gob.es` en 4 tablas bloqueó la primera publicación. La siguiente carga, con la
  caché de la anterior, publicó.
- Hacer: asumir que la primera carga en cualquier repositorio nuevo puede necesitar un reintento (está en la guía).

**H6 · Edad distinta de la pedida y paneles sin fuente** — *abierto, documentado en pantalla*
- Dashboard 1: NEET en **15-29** (la definición del INE), no 16-29. Con las tablas actuales no se puede construir 16-29.
- Dashboard 2: tablas EPA por grupos 16-19, 20-24 y «menores de 25» (16-24); no hay 16-29.
- Paneles sin fuente: nivel educativo y urbano/rural (D1); UE-27, sectores, competencias y tipo de contrato (D2).
  Las fuentes candidatas (Eurostat, Cedefop, Injuve) se localizaron **solo por búsqueda web**: no se descargó ni verificó
  ninguna, porque el entorno bloquea esos dominios.

**H7 · Posible año incompleto en FUNDAE** — *sin verificar*
- Los KPIs de 2025 comparan con 2024 (horas −6,6 %). No se ha comprobado si 2025 es un año cerrado o provisional; si
  fuera parcial, esa variación sería un artefacto. Además, «participantes» es lo que cuenta FUNDAE y puede incluir a la
  misma persona más de una vez: no es «personas distintas».
- Hacer: confirmarlo en la metodología de FUNDAE antes de difundir esas cifras.

**H8 · Atribución de fuentes incompleta** — *corregido en este PR*
- El aviso lateral citaba INE, SEPE, Seguridad Social y Ministerio, pero **no FUNDAE**, que es la fuente del Dashboard 3.
  Ahora lo incluye.
- Pendiente: cada dashboard debería citar solo sus fuentes. Hoy el pie de página lista el periodo de 14 fuentes en los
  tres, aunque cada uno usa una o dos.

**H9 · Pruebas que no verifican cifras** — *abierto*
- Las pruebas abren cada página y comprueban que no hay excepción; el CI no comprueba que un porcentaje sea correcto,
  que un mapa pinte las comunidades correctas ni que la publicación funcione de extremo a extremo.
- Lo que sí hay: pruebas de `mart_neet` (las 20 unidades territoriales se resuelven) y de `mart_tasas_epa`, y desde este
  PR una que importa todos los módulos comunes (habría detectado el import roto de H3).
- Hacer: 2 o 3 pruebas de cifras de referencia (p. ej. el total nacional de NEET frente al dato oficial) y una carga de
  ensayo mensual.

**H10 · Seguridad y privacidad** — *resuelto en lo principal*
- Repositorio **público desde el 26/10/2026**. Antes de publicarlo se buscaron credenciales en **todo el historial**
  (27 commits, 13 ramas) y en los ficheros: sin coincidencias, ni ficheros sensibles versionados. El correo personal con
  el que se firmaron los commits es visible.
- Los dashboards son públicos y sin acceso: es lo pedido. Los datos son agregados por territorio y sector.
- Revisar: `catalogo_fuentes.py` completa la cadena TLS del Ministerio descargando un certificado intermedio por HTTP
  desde `cert.fnmt.es`. No se ha revisado en profundidad; conviene confirmar que la cadena se valida contra raíces de
  confianza.

### Baja

**H11 · Ruido operativo** — *parcialmente corregido*
- Cada push a `claude/**` que toca `pipeline/` o el workflow lanza una carga completa de ensayo (hasta 29 min), y cada
  fusión en `main` con esos cambios otra. Cuatro fusiones así generaron cuatro cargas; dos se cancelaron por la cola.
- El mensaje «La carga del pipeline RRHH se ha interrumpido… la app sigue mostrando la última carga correcta» se emitió
  en una carga que **sí había publicado** (el fallo era del paso posterior). Corregido con el PR #11.
- Hacer: limitar el ensayo en ramas a ejecución manual o a cambios en `pipeline/`.

**H12 · Documentación heredada desfasada** — *marcada*
- `explotacion.md`, `operacion.md`, `catalogo_apis.md` e `inventario_fuentes_laborales_no_ine.md` describen el proyecto
  anterior (app `streamlit_app/`, registro de accesos, repo público, `rrhh.duckdb` en el artefacto). Llevan ahora un aviso.
  `rrhh.duckdb` probablemente ya no va en el artefacto (por el código de `publicacion.py`), pero no se pudo comprobar.

**H13 · Ramas, PR y dependencias** — *parcialmente corregido*
- Seis ramas `claude/*` ya fusionadas siguen en el repositorio (el borrado dio 403 desde la sesión).
- Dependabot resuelto el 26/10: `upload-artifact 7.0.2` fusionado (#5); Streamlit 1.66.1 subido con el PR #17 (el de
  Dependabot, #6, se cerró solo); `pyarrow 26.0.0` subido con el PR #21 (#7 cerrado). pandas 3.1.0 subido en el PR #24.
  Sin adoptar: DuckDB 2.0.0 (versión mayor; el SQL ya es compatible, falta una carga completa con ella) y Playwright
  1.64.1 (hoy 1.63.0; no se puede probar contra las apps desde el entorno).
- El PR #1 conserva en su descripción «cuatro dashboards», anterior a la decisión de dejar tres.

**H14 · `exploracion_dev.yml` depende del artefacto** — *abierto, en `Datos_INE`*
- Descarga el modelo del último artefacto de la última carga correcta de cualquier rama. Con el paso del artefacto no
  bloqueante, una carga puede salir verde sin artefacto y ese workflow fallaría.

**H15 · Marca y accesibilidad** — *abierto; la marca se deja para más adelante por decisión del 26/10/2026*
- Los títulos siguen siendo «Dashboard 1/2/3»; las maquetas son «Foundation Lab | Dashboard N». Sin logo ni nombre final.
- Solo se revisó la vista de escritorio. No se ha comprobado el móvil ni la accesibilidad (contraste, lectores).

**H16 · Tablas mensuales de SEPE cortadas sin que el control lo detectara** — *control corregido; origen sin corregir*
- Evidencia: en la carga publicada del 26/10, `fact_sepe_paro_municipio` y `fact_sepe_contratos_municipio` tenían solo un
  mes de 2026 (11 y 7 filas, cuando cada mes trae ~8.000), mientras que `fact_sepe_demandantes_municipio` llegaba a
  septiembre. La pérdida no llegaba al 50 % que exigía el control.
- Hecho (PR #16): el control rechaza una carga si una tabla mensual de SEPE pierde más de un 5 % de filas o si el último
  periodo de una tabla con fecha retrocede.
- Falta: leer cada año del CSV de SEPE con copia de la última versión buena (hoy un CSV anual cortado deja la tabla
  cortada). Ninguno de los tres dashboards usa estas tablas.

**H17 · Vigilancia de datos viejos y de dashboards rotos tras publicar** — *añadido el 26/10/2026 (PR #23 y #24)*
- Job `frescura` (issue `datos-viejos` si la carga publicada supera 96 h) y workflow `prueba_tras_publicar.yml` (issue
  `prueba-publicacion` si una página falla con los datos publicados). Probados en local; **su primera ejecución real en
  GitHub está pendiente de verificar**.

## 4. Proceso

- **PR apilados**: funcionaron, pero obligaron a redirigir cada PR a `main` tras fusionar el anterior. Para trabajo
  futuro conviene una sola rama o PR pequeños sobre `main`.
- **Limpieza de artefactos**: se pidió criterio; se aplicó uno explícito (último de cada uno de los 5 días recientes de
  `main`) y se verificó el resultado consultando a GitHub.
- **Dos incidencias propias de comunicación**: conté la carga como «verde» tras una prueba en rama antes de que `main`
  hubiera publicado, y di por hecho que los PR estaban «listos» antes de la carga completa. Ambos casos están en H3.

## 5. Lo que no se pudo comprobar

- Acceso a INE, ILOSTAT, Eurostat, Injuve, datos.gob.es y Banco Mundial: bloqueado por la red del entorno.
- Contenido de los artefactos (la descarga está bloqueada), por tanto si `rrhh.duckdb` está dentro.
- Límites de memoria y de apps del plan gratuito de Streamlit Community Cloud, y si admite repositorios privados.
- Si una carga programada de `Datos_INE` publica tras el arreglo.
- Cómo se ven las apps desplegadas: están publicadas desde el 26/10 y un robot comprobó que responden sin errores de
  código, pero **no se han verificado cifras ni gráficos** desde aquí (la red del entorno bloquea `*.streamlit.app`).
- Si FUNDAE 2025 es un año cerrado (H7).

## 6. Plan de acción priorizado

1. **Hecho el 26/10**: repositorio público (H10), las 3 apps creadas y vigiladas cada 4 horas, y decidido que las dos
   cargas conviven (H1). **Falta**: ver una carga programada verde en `Datos_INE` con el artefacto ya subiéndose (H2).
2. **Antes de difundir**: confirmar H7 (año de FUNDAE) y completar la atribución por dashboard (H8).
3. **Mejora de eficiencia**: ensayo de ramas solo manual (H11), pruebas de cifras (H9), lector de SEPE con copia buena por año (H16). *Hecho: tablas por dashboard (H4).*
4. **Cuando haya acceso de red**: localizar y cargar las fuentes de los paneles pendientes (H6).
5. **Limpieza**: borrar ramas fusionadas (H13; Dependabot ya resuelto); título y marca definitivos (H15, aplazado).

## 7. Seguimiento y auditoría de salida a producción (27/10/2026)

Estado de los hallazgos de arriba tras las últimas fusiones (PR #32 a #50) y lo encontrado al repasarlos.

| Hallazgo | Estado a 27/10/2026 |
|---|---|
| H4 · tablas por dashboard | Cerrado: cada app declara las suyas (D3 incluye ahora `fact_sepe_demandantes_nivel` y `fact_sepe_contratos_nivel`, opcionales) |
| H6 · paneles sin fuente | Reducido: D1 (nivel educativo, urbano/rural, población, empleo) y D2 (UE-27, paro por estudios, tipo de contrato, sectores de ocupación) ya cargan Eurostat/EPA. Desde el 28/10 D2 muestra dónde crece más el empleo por sector (afiliación a la Seguridad Social, no es una previsión). Siguen sin fuente: previsión por sector y competencias (D2) y 16-29 para los NEET (D1) |
| H7 · año de FUNDAE | Sin confirmar en la metodología de FUNDAE. Dato a favor: en la carga publicada, los participantes de 2025 (13,52 M) están por encima de los de 2024 (13,11 M); un año parcial habría mostrado una caída |
| H8 · atribución | Cerrado por diseño: la barra lateral y el pie solo muestran la fecha de la carga; cada gráfico cita su fuente en el texto de debajo |
| H9 · pruebas de cifras | Abierto: las pruebas abren todas las páginas y validan lectores y marts con ficheros reales, pero no comparan cifras con datos oficiales |
| H11 · ensayo en ramas | Se mantiene a propósito: un push a `claude/**` que toca `pipeline/` lanza la carga completa de ensayo, que se usa como comprobación antes de fusionar |
| H13 · ramas | Abierto, depende de ti: quedan unas 40 ramas `claude/*` y 3 `dependabot/*` ya fusionadas o sustituidas (las sesiones de Claude no pueden borrarlas; ver sección 10 de la guía) |
| H16 · SEPE cortado | El control de publicación está; en la carga publicada las tres tablas de SEPE por municipio llegan a 2026-09 |
| H17 · vigilancia | Verificado en GitHub: `frescura` y `prueba_tras_publicar` se han ejecutado en verde. El vigilante de apps daba falsa alarma («SIN IDENTIFICAR») porque buscaba textos que ya no existen en las páginas; ahora reconoce la app por su contenedor y título |

Encontrado y corregido en esta revisión:
- **Vigilante de apps con falsa alarma** desde que se simplificó el diseño: mantenía abierta la issue «Un dashboard no responde» y habría tapado una caída real.
- **Serie 13 de FUNDAE sin cargar**: el lector recorría siempre las series en el mismo orden y cortaba a los 420 s; la serie más nueva (la última de la lista) se quedaba sin turno en una carga lenta (441 s). En la carga siguiente las 19 series entraron en 194 s, así que la causa de fondo es la lentitud intermitente del servidor de FUNDAE. Ahora van primero las series sin copia y luego las de copia más antigua.
- **SEPE por nivel formativo perdía meses**: el fichero de un mes falla a ratos (abril de contratos faltó en una carga) y el lector reescribía el CSV solo con lo descargado ese día. Ahora conserva los meses ya guardados y añade los nuevos. Test nuevo.
- **Archivos retirados**: `_apartado/` (acceso por email, ya sin uso; sigue en el historial de git) y `ops/explorar_fuentes.py` con su workflow manual (herramienta de exploración de fuentes de un solo uso).
- **Documentación**: README y guía de puesta en marcha actualizados (estado real de las apps, fuentes, paneles pendientes).

Descartado: leer la formación subvencionada de los PDF de FUNDAE (una ficha por convocatoria, sin serie anual ni comunidades, y con
el texto en columnas mezcladas); los informes «Navega por tu CCAA» y «Datos a día de hoy» son Power BI sin descarga.
