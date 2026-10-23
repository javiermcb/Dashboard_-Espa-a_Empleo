# Catálogo de APIs y ficheros para RRHH 360

> **Documento heredado de `Datos_INE`.** Describe el proyecto anterior: las menciones a la app `streamlit_app/`, al
> registro de accesos, al repositorio público `datos-rrhh-publicos` y al artefacto con `rrhh.duckdb` (30 días) **no
> aplican a este repositorio**. Las tablas, fuentes y el procedimiento general siguen siendo válidos. Para el estado
> actual, ver `README.md` y `docs/guia_puesta_en_marcha.md`.


**Fecha:** 3 de octubre de 2026
**Complementa a:** [investigacion_ine_rrhh360.md](investigacion_ine_rrhh360.md) e [inventario_fuentes_laborales_no_ine.md](inventario_fuentes_laborales_no_ine.md)

Este documento explica **cómo conectarse** a cada fuente y dónde están **todos los códigos** de tabla y URLs.

## 1. Ficheros del catálogo

| Fichero | Qué contiene |
|---|---|
| [`resultados/catalogo_rrhh.csv`](../resultados/catalogo_rrhh.csv) | **Una fila por tabla o fichero**. Columnas: punto de RRHH, organismo, fuente, operación, **código**, nombre, tipo de acceso, formato, **URL de datos**, URL web y cómo se verificó. Separador `;`, UTF-8 con BOM |
| [`resultados/catalogo_rrhh_series.csv`](../resultados/catalogo_rrhh_series.csv) | Los ficheros de las webs agrupados en **series**: el mismo fichero publicado cada mes o año. Ejemplo: `MUNI_A_CORUNA_#.xls`. Incluye el último fichero visto y su URL |
| `resultados/exploracion/tablas_operaciones.csv` | Catálogo completo de tablas de la API del INE (todas las operaciones consultadas, no solo las de RRHH) |
| `resultados/fuentes/*.csv` | Resultados en bruto del rastreo (`catalogo_fuentes.py`) |
| [`resultados/prueba_descarga/`](../resultados/prueba_descarga/) | Registro de la **prueba real de descarga** desde GitHub Actions |

**Puntos de RRHH** (columna `punto`): 1 Benchmark salarial · 2 Coste laboral y absentismo · 3 Mercado de talento · 4 Revisión salarial · 5 Igualdad y diversidad · 6 Contexto de mercado. Si está vacío, el fichero no se ha podido asignar a un punto o no encaja en ninguno.

## 2. Cómo se conecta a cada fuente

| Fuente | Tipo de acceso | URL / patrón | Prueba de descarga (3-oct-2026) |
|---|---|---|---|
| **INE, tablas de la API** | **API JSON**, sin clave | `https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/{código}` · `?nult=N` = últimos N periodos · `?tip=AM` = formato con metadatos (lo usa `ine_descarga.py`) | **OK** (5 de 5: tablas 6061, 36830, 37624, 66254, 10888) |
| **INE, tablas INEbase** (fuera de la lista de la API) | **La misma API JSON** | `DATOS_TABLA/{número}` o `DATOS_TABLA/{ruta .px}` (p. ej. `t22/e308/meto_05/modulo/base_2011/2003/l0/01001.px`) | **OK**: 120 de 120 tablas probadas (75, 10 y 32 en tres rastreos, y 3 en la prueba de descarga), con código numérico y con ruta `.px` |
| **INE, descubrir tablas** | API JSON | `OPERACIONES_DISPONIBLES`, `TABLAS_OPERACION/{id_operación}` | OK (es lo que usa `ine_explorar.py`) |
| **datos.gob.es** (SEPE, Seguridad Social, Educación) | **API de catálogo**, sin clave. Devuelve las URLs de descarga | `https://datos.gob.es/apidata/catalog/dataset/publisher/{id}.json?_pageSize=50&_page=N` · `.../catalog/dataset/title/{texto}.json` | OK |
| **SEPE** (vía datos.gob.es) | Ficheros CSV/XLS con nombre por periodo | `https://sede.sepe.gob.es/es/portaltrabaja/resources/sede/datos_abiertos/datos/{Nombre}_{AAAAMM}_xls.xls` | **OK** |
| **SEPE** (web de estadísticas) | Ficheros XLS | Paro y contratos por municipio: `https://www.sepe.es/HomeSepe/dam/jcr:{uuid}/MUNI_{PROVINCIA}_{MMAA}.xls`. El `uuid` cambia en cada fichero, así que **hay que leer la página cada mes** | **OK** |
| **Seguridad Social** (PX-Web) | Consultas guardadas que devuelven **CSV** | `https://w6.seg-social.es/PXWeb/sq/{uuid}` (114 consultas: afiliación, ERTE…) | **OK** |
| **Seguridad Social** (web de estadísticas) | Ficheros XLSX/XLS | `https://www.seg-social.es/wps/wcm/connect/wss/{uuid}/{nombre}.xlsx`. El `uuid` no es predecible: **hay que leer la página** | **OK** |
| **Ministerio de Trabajo** | Ficheros XLSX/XLS con **ruta predecible** por estadística y periodo | p. ej. `https://www.mites.gob.es/estadisticas/Ett/ett26JulAv/ETT_07_2026.xlsx`, `.../eat/eat24_10/ATR_10_2024.xlsx`, `.../reg/reg26jul/reg_07_2026.xlsx`. Su servidor **no envía el certificado intermedio**: ver la nota del apartado 4 | **OK** (con la cadena completada) |
| **Ministerio de Educación** (vía datos.gob.es) | Ficheros PX, CSV y XLS | `https://estadisticas.educacion.gob.es/EducaJaxiPx/files/_px/es/px/laborales/insercion/...px?nocab=1` | No probado |
| **Agencia Tributaria** | Ficheros XLSX | Solo se localizaron 2 anexos de metodología | OK, pero **cobertura insuficiente** (ver apartado 5) |

## 3. Qué hay de cada organismo en el catálogo

| Organismo | Filas | Contenido principal |
|---|---|---|
| INE (API) | 3.291 | EES, EAES, ETCL, EACL, ICLA, EPA (incluido el decil de salarios), EFPA, EMLG, IPT, IPC, MYH, DIRCE, ADRH… |
| INE (INEbase) | 8.103 | EILU (2.322), ETEFIL (2.216), **módulos y otras tablas EPA** que no están en la API (1.470), EADA (711), Encuesta Europea de Salud (651), **empleo y salario de las personas con discapacidad** (357 + 311), TIC en empresas (37), tiempo de trabajo y proyecciones de tasas de actividad |
| Ministerio de Trabajo | 1.875 ficheros | Accidentes de trabajo, convenios, regulación de empleo (ERE/ERTE), **empresas de trabajo temporal (CPD)**, prestaciones por desempleo, **empresas inscritas en la Seguridad Social**, **despidos y su coste**, autónomos, huelgas, **Encuesta de Formación Profesional para el Empleo en Empresas** (2010, 2015, 2020), Encuesta Anual Laboral y anuarios |
| SEPE | 1.365 ficheros web + 228 en datos.gob.es | Paro registrado y contratos (también por municipio), demandantes, prestaciones |
| Seguridad Social | 2.265 ficheros web + 114 consultas PX-Web | Afiliación (municipio, CNAE, régimen), ERTE y otros. Unos 2.000 ficheros tienen nombres poco descriptivos y **quedan sin clasificar** |
| Ministerio de Educación | 513 | Afiliación e inserción laboral de titulados de FP por cohorte |
| Agencia Tributaria | 2 | Anexos de metodología |

Estadísticas del Ministerio de Trabajo que no estaban en el inventario anterior: **Empresas Inscritas en la Seguridad Social**, **Despidos y su coste**, **Prestaciones por Desempleo**, **Autónomos**, **Encuesta Anual Laboral** y la **Encuesta de Formación Profesional para el Empleo en Empresas**. Esta última resuelve la duda del inventario del INE: la produce el Ministerio de Trabajo.

## 4. Cómo descargar

```bash
# Ver qué hay (sin descargar)
python descarga_catalogo.py --punto 4 --solo-listar

# INE: tablas concretas, últimos 8 periodos
python descarga_catalogo.py --codigo 6061 37624 --nult 8

# Ministerio de Trabajo: últimos ficheros de ETT y convenios
pip install cryptography   # necesario para mites.gob.es
python descarga_catalogo.py --organismo "Ministerio de Trabajo" --buscar "Empresas de Trabajo Temporal|Convenios" --max 5
```

- Las descargas van a `salida_catalogo/`, con un `registro.csv` del resultado de cada una.
- **Nota sobre el Ministerio de Trabajo:** su servidor no envía el certificado intermedio de su cadena TLS, por eso un cliente normal falla con `CERTIFICATE_VERIFY_FAILED`. `catalogo_fuentes.contexto()` descarga ese intermedio desde la URL «CA Issuers» del propio certificado y lo añade. **La verificación sigue activa.** Necesita el paquete `cryptography`.

**Para regenerar el catálogo:**
1. Ejecutar `ine_explorar.py` (tablas de la API del INE).
2. Ejecutar `catalogo_fuentes.py`, o lanzar el workflow «Catálogo de fuentes» (INEbase, datos.gob.es y webs).
3. Ejecutar `catalogo_rrhh.py`, que une todo.

## 5. Limitaciones y huecos

- **Ficheros web sin API** (SEPE, Seguridad Social, Ministerio de Trabajo): para automatizar hay que **leer la página cada periodo** o seguir el patrón de nombre. En la Seguridad Social y en los ficheros municipales del SEPE la URL lleva un identificador que cambia, así que no se puede construir de antemano.
- **Clasificación por punto**: es automática, por palabras clave y carpetas. Unas 2.800 filas quedan sin punto, casi todas de la Seguridad Social y de los anuarios del Ministerio de Trabajo.
- **Agencia Tributaria**: no se encontró el acceso a las tablas de «Mercado de Trabajo y Pensiones en las Fuentes Tributarias». La página principal de la estadística respondió con error 404. **Pendiente.**
- **MCVL** (microdatos de la Seguridad Social): solo para investigación sin fines comerciales. No está en el catálogo.
- **Códigos de publicador de datos.gob.es**: E05072501 y E05230301 se han identificado por el dominio de sus URLs de descarga, no por un nombre oficial.
- Las URLs son las vistas el 3 de octubre de 2026. Los organismos pueden moverlas.
