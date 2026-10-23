# Entrega y explotación de los datos RRHH 360

> **Documento heredado de `Datos_INE`.** Describe el proyecto anterior: las menciones a la app `streamlit_app/`, al
> registro de accesos, al repositorio público `datos-rrhh-publicos` y al artefacto con `rrhh.duckdb` (30 días) **no
> aplican a este repositorio**. Las tablas, fuentes y el procedimiento general siguen siendo válidos. Para el estado
> actual, ver `README.md` y `docs/guia_puesta_en_marcha.md`.


**Fecha:** 4 de octubre de 2026 · Complementa a [proyecto_rrhh360.md](proyecto_rrhh360.md) (arquitectura) y [catalogo_apis.md](catalogo_apis.md) (fuentes).

## 1. Qué se entrega y dónde

| Qué | Dónde | Formato | Frecuencia |
|---|---|---|---|
| **Modelo de datos** | Repositorio público `javiermcb/datos-rrhh-publicos`, carpeta `modelo/` | Parquet (y CSV salvo las tablas grandes) | Cada carga (días laborables, 06:17 UTC, cuando la rama esté en `main`) |
| **Diccionario** de tablas y columnas | `modelo/diccionario.csv` | CSV | Cada carga |
| **Metadatos** (fecha de generación, último periodo por tabla) | `modelo/metadatos.json` y `README.md` | JSON / Markdown | Cada carga |
| **Alertas** de la carga | `modelo/alertas.csv` (público) y `resultados/pipeline/alertas.md` (rama `calidad` de este repositorio) | CSV / Markdown | Cada carga |
| **Calidad** (carga por tabla, variables sin mapear, territorios sin resolver) | `resultados/pipeline/` en la rama `calidad` de este repositorio (privado) | CSV | Cada carga |
| **Base de datos para SQL** | `rrhh.duckdb`, dentro del artefacto `modelo-rrhh` de cada ejecución del workflow | DuckDB | Cada carga (se guarda 30 días) |

**Mientras no estén el token y la variable** (`RRHH_PUBLICO_TOKEN`, `RRHH_PUBLICO_REPO`), nada se publica en el repositorio público. Todo queda en el artefacto descargable de cada ejecución: Actions → Pipeline RRHH → la ejecución → *Artifacts*.

## 2. Estructura de tablas

```
                      dim_tiempo (fecha)                    dim_territorio (territorio_id)
                            │                    N00 España · Cxx CCAA · Pxx provincia · Mxxxxx municipio
                            │                                 │
   ┌────────────────────────┼─────────────────────────────────┼──────────────────────────┐
   │  TABLAS POR TEMA (marts/) — recomendadas para informes                              │
   │  1 Salarios   mart_salarios_ees · mart_salarios_ees_detalle · mart_salarios_eaes · mart_deciles_epa · mart_limites_deciles
   │  2 Coste y    mart_coste_laboral · mart_coste_actividad · mart_tiempo_trabajo · mart_tiempo_trabajo_actividad
   │    absentismo mart_it_despido · mart_horas_extra · mart_teletrabajo · fact_incapacidad_temporal
   │               fact_accidentes · fact_accidentes_detalle
   │  3 Talento    mart_poblacion_actividad · mart_ocupados_sector · mart_ocupados_ccaa · mart_tasas_epa · mart_flujos
   │               mart_temporalidad_motivo · mart_vacantes · mart_vacantes_actividad · fact_regulacion_empleo
   │               fact_sepe_paro_municipio · fact_sepe_contratos_municipio · fact_ss_afiliacion
   │    ETT y CPD  fact_cpd_actividad · fact_ett_mensual · fact_ett_territorio · fact_ett_actividad · fact_ett_resumen · mart_epa_ett
   │  4 Revisión   mart_precios (IPC, IPT) · fact_convenios · fact_convenios_detalle
   │  5 Igualdad   mart_brecha_genero (+ sexo en salarios, EPA, ETT, accidentes y ERTE)
   │  6 Contexto   mart_empresas
   └───────────────────────────────────────────────────────────────────────────────────────┘
   fact_ine (+ dim_tabla): todo el INE en formato largo, para explorar o crear tablas nuevas
```

- **Columnas comunes:** todas las tablas comparten `territorio_id` y `fecha` (salvo `fact_convenios`, que es nacional y va por `anyo_efectos`/`mes_registro`, y `fact_accidentes`, acumulado hasta `periodo_hasta`). Así se cruzan fuentes distintas: por ejemplo, paro EPA, paro registrado del SEPE, afiliación y coste laboral de una misma provincia o comunidad.
- **Totales y desgloses conviven** en cada tabla (España + comunidades, Ambos sexos + Hombres/Mujeres, Total + sectores). Hay que filtrar siempre un nivel de territorio y un valor de cada dimensión que no se esté desglosando.
- El detalle de cada columna está en `modelo/diccionario.csv`.

## 3. Cómo se explota

### 3.1 Power BI (informes recurrentes)

**Montaje (una vez):**
1. Power BI Desktop → Transformar datos → crear las consultas de [`pipeline/powerbi/consultas.pq`](../pipeline/powerbi/consultas.pq). Hay una función `LeerParquet` y una línea por tabla.
2. Vista de modelo → relaciones `territorio_id` → `dim_territorio` y `fecha` → `dim_tiempo`.
3. Crear las medidas de [`pipeline/powerbi/medidas.dax`](../pipeline/powerbi/medidas.dax).
4. Publicar en el área de trabajo. En el conjunto de datos: credenciales **Anónimo** y actualización programada (con Pro, hasta 8 al día; con 1 diaria después de las 07:30 basta).

**Páginas propuestas.** El prototipo `docs/prototipo_informe_rrhh360_v2.html` (datos reales) muestra cómo puede quedar cada una:

| Página | Visuales | Tablas |
|---|---|---|
| **Resumen** | Cifras clave, conclusiones automáticas, alertas | `alertas` y las tablas de cada tema |
| **Ficha de provincia** | Selector de provincia; cada indicador frente a España (paro, contratos indefinidos, afiliación, temporalidad, CPD, accidentes, IT, convenios, empresas, coste y horas de su CCAA) | `fact_sepe_*`, `fact_ss_afiliacion`, `mart_poblacion_actividad`, `fact_ett_territorio`, `fact_accidentes`, `fact_incapacidad_temporal`, `fact_convenios_detalle`, `mart_empresas` |
| **CPD y ETT** | CPD mensuales por modalidad; cambio tras la reforma (2016–); CPD por CCAA con variación oficial; provincias y % de fijos discontinuos; divisiones CNAE; CPD por 100 afiliados del sector; perfil (edad, sexo, nacionalidad); % de asalariados vía ETT (EPA) | `fact_ett_*`, `fact_cpd_actividad`, `fact_ss_afiliacion`, `mart_epa_ett` |
| **Absentismo y horas** | Bajas por IT por provincia (incidencia y duración); peso de la IT por sector; horas no trabajadas por CCAA; horas efectivas por sector; coste por día de IT y por despido; horas extra pagadas y no pagadas por sexo; teletrabajo | `fact_incapacidad_temporal`, `mart_tiempo_trabajo*`, `mart_it_despido`, `mart_horas_extra`, `mart_teletrabajo` |
| **Accidentes** | Índice por provincia y sector; hombres y mujeres por edad; gravedad y forma; ocupaciones | `fact_accidentes`, `fact_accidentes_detalle` |
| **Convenios** | Subida pactada frente a IPC y poder adquisitivo acumulado; por sector y su evolución; por CCAA (subida y jornada); empresa frente a sector; tramos de jornada; cláusula de garantía | `fact_convenios`, `fact_convenios_detalle`, `mart_precios` |
| **Mercado de trabajo** | Paro registrado; % de contratos indefinidos; afiliación temporal y fija discontinua; afiliados por sector; paro EPA por sexo y CCAA; motivos de la temporalidad; ERE y ERTE | `fact_sepe_*`, `fact_ss_afiliacion`, `mart_tasas_epa`, `mart_temporalidad_motivo`, `fact_regulacion_empleo` |
| **Salarios e igualdad** | Salario por antigüedad y sexo; por CCAA y sexo; por ocupación y sexo; brecha por edad; coste laboral por sector; empresas por tamaño | `mart_salarios_ees*`, `mart_brecha_genero`, `mart_coste_actividad`, `mart_empresas` |

> El fichero `.pbix` no se puede generar desde aquí, porque es un formato binario de Power BI Desktop. Las consultas y medidas están listas para pegar.

### 3.2 Consultas puntuales (SQL)

- [`pipeline/consultas/ejemplos.sql`](../pipeline/consultas/ejemplos.sql) tiene 9 consultas de ejemplo: coste por CCAA, horas no trabajadas, brecha por ocupación, provincias donde más sube el paro, CPD por sector, convenios frente a IPC, paro y contratos por municipio, afiliación por CNAE y catálogo de tablas.
- Se ejecutan con DuckDB, sobre `rrhh.duckdb` o leyendo los Parquet del repositorio público por URL, sin descargar nada.
- También se pueden pedir en este repositorio a Claude, que consulta el modelo.

### 3.3 Proactividad (alertas)

Cada carga ejecuta [`pipeline/alertas.py`](../pipeline/alertas.py):

| Regla | Qué mira | Nivel |
|---|---|---|
| Novedades | Tablas con un periodo nuevo desde la carga anterior | novedad |
| Convenios frente a IPC | Último acumulado de subida pactada frente al IPC interanual | aviso si la subida es menor que el IPC |
| Coste laboral frente a IPC | Variación interanual del coste por trabajador (total ETCL) frente al IPC | info |
| Paro EPA por provincia | Las 5 mayores subidas interanuales | aviso si ≥ 10 % |
| Horas no trabajadas | Las 5 CCAA con mayor subida interanual del % sobre pactadas | aviso si ≥ 0,5 puntos |
| Siniestralidad | Las 5 provincias con mayor índice de incidencia (acumulado del año) | info |
| CPD | Acumulado del año frente al mismo periodo del año anterior | info |
| Vacantes | Último trimestre frente al mismo del año anterior | info |

- Los umbrales están al principio del script y son ajustables.
- Las alertas quedan en `resultados/pipeline/alertas.md` (rama `calidad`) y en `modelo/alertas.csv` (página de portada de Power BI).

## 4. Fuentes que entran en el modelo

| Fuente | Tabla | Detalle | Cobertura |
|---|---|---|---|
| INE (24 tablas, API JSON) | `fact_ine` y `mart_*` | Nacional, CCAA y provincia | Según tabla (ver `dim_tabla`) |
| SEPE: paro registrado | `fact_sepe_paro_municipio` | Municipio, mensual | Desde 2019 (configurable con `--desde`) |
| SEPE: contratos | `fact_sepe_contratos_municipio` | Municipio, mensual | Desde 2019 |
| Seguridad Social: afiliación (4 consultas PX-Web) | `fact_ss_afiliacion` | Provincia o CCAA, mensual | Desde 2009 (según consulta) |
| Seguridad Social: incapacidad temporal | `fact_incapacidad_temporal` | CCAA y provincia | Último ejercicio (enero al último mes) y cierre del anterior |
| Ministerio de Trabajo: CPD por sección (ETT-E2) | `fact_cpd_actividad` | Sección CNAE, mensual | Año en curso y anterior |
| Ministerio de Trabajo: ETT (E1, E3, E4, ETT-1, ETT-2, R1–R4) | `fact_ett_mensual`, `fact_ett_territorio`, `fact_ett_actividad`, `fact_ett_resumen` | Modalidad, perfil, CCAA y provincia, división CNAE | Serie desde 2016 (E1); detalle del año en curso con variación oficial |
| Ministerio de Trabajo: convenios (CCT-2.1) | `fact_convenios` | Nacional, anual + acumulado mensual | Desde 2013 |
| Ministerio de Trabajo: convenios en detalle (CCT-2.3 a 2.8) | `fact_convenios_detalle` | Sector, CCAA y provincia, ámbito, jornada, cláusula | Año en curso y cierres de diciembre desde 2023 |
| Ministerio de Trabajo: accidentes (ATR-I1.1) | `fact_accidentes` | CCAA y provincia | Acumulado del año del último avance |
| Ministerio de Trabajo: accidentes en detalle (ATR) | `fact_accidentes_detalle` | Gravedad, actividad, ocupación, sexo y edad, índices | Acumulado del año con variación oficial |
| Ministerio de Trabajo: regulación de empleo (REG) | `fact_regulacion_empleo` | Tipo (despido colectivo, ERTE, reducción), sexo, actividad, territorio, causa, tamaño | Últimos 10 meses |

**Límites a tener en cuenta**
- **`fact_cpd_actividad` (verificado el 4-oct-2026):** 20 secciones CNAE, dos de ellas agrupadas por el propio Ministerio («P y V», «T y U»). La suma de secciones cuadra con el total en todos los meses (diferencia 0,00 %). El control se repite en cada carga (`resultados/pipeline/fuentes_carga.csv`).
- **Paro EPA por provincia:** en provincias pequeñas la muestra de la EPA es reducida y las variaciones interanuales pueden ser muy grandes (p. ej., Segovia +68,6 % en la carga del 4-oct-2026). Conviene contrastarlas con el paro registrado del SEPE antes de sacar conclusiones.
- **Variaciones interanuales del Ministerio de Trabajo:** se usan las que publica el propio ministerio (ETT-R1/R2, ATR-R1), calculadas con datos revisados. No se comparan avances de hace un año: eran provisionales (ene-jul 2025: 2.422.730 CPD en el avance frente a 2.551.192 revisados, que daría +12,8 % en vez del +7,1 % oficial). Por eso no hay variación de CPD por provincia.
- **Índice de incidencia de accidentes:** es la media mensual de accidentes en jornada por 100.000 afiliados (no el acumulado del periodo).
- **Convenios:** el año en curso solo incluye los convenios registrados hasta el último mes y se completa con el tiempo; los años anteriores se toman del cierre de diciembre de cada año. No hay datos de convenios por sexo.
- **Incapacidad temporal:** se lee la hoja «Estadística» del fichero del sistema (todos los regímenes y contingencias; comprobado con la hoja de datos mensuales). El año en curso (enero–último mes) y el año completo anterior no son el mismo periodo: se comparan con cautela.
- **CNAE 2025:** desde enero de 2026 la Seguridad Social, el Ministerio de Trabajo (ETT, accidentes) y la ETCL clasifican con la CNAE-2025. Algunas secciones cambian de letra respecto a la CNAE-2009 (J, K…).
- **Columnas del SEPE:** se toman de su cabecera. Si el SEPE cambia una columna entre años, el lector para y lo indica en `fuentes_carga.csv`, en lugar de mezclar columnas.

## 5. Flujo de actualización y explotación

```
06:17 UTC L-V  GitHub Actions · Pipeline RRHH
  1. Recupera de la caché la última carga buena de cada fuente
  2. Descarga INE · SEPE · Seguridad Social · Ministerio de Trabajo
       └─ si una fuente falla: se reutiliza su última versión buena (estado ANTERIOR) en vez de dejar la tabla vacía
  3. Guarda la carga en la caché para la próxima ejecución
  4. Modelo + controles de calidad
  5. Alertas (datos nuevos, indicadores, estado de la carga)
  6. Notifica por issue de GitHub (llega por correo) SOLO lo nuevo:
       · issue «Incidencias de carga del pipeline RRHH» (etiqueta pipeline-fallo)
       · issue «Alertas RRHH 360» (etiqueta alertas)
  7. Publica en el repositorio público (README y metadatos indican qué tablas no se han actualizado)
~08:00 hora de España  Power BI Service refresca el informe (actualización programada)
```

| Capa | Quién | Cuándo | Qué hace |
|---|---|---|---|
| Automática | GitHub Actions | Días laborables | Pasos 1 a 7 |
| Revisión por excepción | Análisis (alertas) y mantenimiento (fallos) | Al recibir el correo de la issue | Valorar el aviso o corregir el lector (mientras tanto se publica lo último bueno) |
| Explotación mensual | Análisis | Tras los datos nuevos de SEPE, Seguridad Social, IPC y Ministerio de Trabajo | Boletín de mercado de talento, revisión salarial, accidentes |
| Explotación trimestral | Análisis | Tras EPA y ETCL | Coste laboral, absentismo, paro por provincia, vacantes |
| Explotación anual | Análisis | Tras EAES, deciles EPA, DIRCE e IPT (EES cada 4 años) | Benchmark salarial, brecha, empresas |
| Puntual | Cualquiera | A demanda | SQL con DuckDB o pregunta a Claude en el repositorio |

**Correos de GitHub:** llegan a quien «vigila» el repositorio (el propietario por defecto). Se configura en GitHub → *Watch* → *All activity* o *Custom → Issues*, y en Settings → Notifications → Email. Para comprobarlo: Actions → Pipeline RRHH → *Run workflow* → marcar «Enviar un aviso de prueba».

**Caché:** GitHub conserva la caché unos días sin uso. Con la carga diaria se renueva sola. Si se borrara, la siguiente carga parte de cero, y una fuente que fallara ese día aparecería como ERROR (sin datos) hasta la siguiente carga buena.
