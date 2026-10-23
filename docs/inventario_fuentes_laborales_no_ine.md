# Fuentes laborales fuera del INE: afiliación, paro, contratos, CPD, accidentes y convenios

**Fecha:** 3 de octubre de 2026
**Complementa a:** [investigacion_ine_rrhh360.md](investigacion_ine_rrhh360.md) · **Códigos y URLs para conectarse:** [catalogo_apis.md](catalogo_apis.md)

## Cómo se ha verificado

- Desde esta sesión **no hay acceso** a seg-social.es, sepe.es, mites.gob.es, datos.gob.es ni agenciatributaria.es (todas bloqueadas por la red).
- Todo lo de este documento sale de **búsquedas web**: publicaciones oficiales, el BOE y, cuando se indica, prensa.
- **No he abierto las tablas.** Sé que cada estadística existe y qué cubre a grandes rasgos, pero no su estructura exacta ni su formato de descarga. Cuando algo no está confirmado, lo indico como *sin verificar*.

---

## 1. Qué es un CPD y por qué es importante

**Contrato de puesta a disposición (CPD):** es el contrato **mercantil entre la empresa de trabajo temporal (ETT) y la empresa usuaria**. Por él, la ETT cede a un trabajador para que preste servicios en la empresa usuaria. No es el contrato laboral del trabajador: ese lo firma el trabajador con la ETT.

**CPD y contrato fijo discontinuo:**
- Desde la reforma laboral ([RDL 32/2021](https://www.boe.es/buscar/doc.php?id=BOE-A-2021-21788)), las ETT pueden contratar a trabajadores como **fijos discontinuos** para cubrir CPD vinculados a necesidades temporales de distintas empresas usuarias.
- El trabajador es indefinido en la ETT, y cada llamamiento suele corresponder a una cesión mediante un CPD.
- Por eso un mismo trabajador fijo discontinuo puede generar **muchos CPD al año**. Contar CPD no es lo mismo que contar personas ni empleos.

**Cambio en el registro desde el 1 de diciembre de 2024:**
- La [Orden TES/1324/2024](https://www.boe.es/buscar/doc.php?id=BOE-A-2024-24517) aprobó nuevos modelos oficiales del CPD y de la **relación mensual de CPD** que las ETT comunican a la autoridad laboral.
- Según [la prensa](https://www.eleconomista.es/economia/noticias/13262065/03/25/nuevo-lio-con-los-fijos-discontinuos-trabajo-borra-el-60-de-los-que-gestionan-las-etts.html), tras el cambio, los CPD cubiertos por fijos discontinuos cayeron un 60 % en un mes.
- **Consecuencia práctica:** puede haber una **ruptura de serie** en diciembre de 2024. Antes de comparar CPD de fijos discontinuos antes y después de esa fecha, hay que leer la nota metodológica.

**Fijos discontinuos y paro registrado:**
- Los fijos discontinuos en periodo de inactividad **no cuentan como parados registrados**. Figuran como demandantes no parados ([SEPE / Maldita](https://maldita.es/malditateexplica/20220602/contratos-fijos-discontinuos-estadistica-paro/)).
- Según [la prensa (mayo de 2026)](https://www.eleconomista.es/economia/noticias/13940643/05/26/diaz-borra-el-unico-dato-oficial-de-fijos-discontinuos-apuntados-al-paro-que-trabajo-publicaba-desde-2007.html), el Ministerio de Trabajo **ha dejado de publicar** la tabla MLR-18 del anuario, que recogía a esos demandantes. **No lo he comprobado en la fuente oficial.**

---

## 2. Inventario por organismo

### 2.1 Ministerio de Trabajo y Economía Social (MITES)

| Estadística | Qué ofrece | Frecuencia | Estado |
|---|---|---|---|
| **Empresas de Trabajo Temporal (ETT)** | Número de ETT autorizadas, **CPD celebrados**, trabajadores contratados por ETT para ser cedidos y afiliados de las ETT. Por sección de actividad y comunidad autónoma. Datos 2025 (avance): 217 ETT y 4.368.114 CPD, un 7,2 % más que en 2024 ([avance ene–dic 2025](https://www.mites.gob.es/estadisticas/Ett/ett25DicAv/Avance_ETT_(enero-diciembre_2025).pdf)). La fuente son las relaciones mensuales de CPD que envían las ETT ([notas metodológicas](https://www.mites.gob.es/estadisticas/Ett/notas_metodologicas.pdf)) | Avances mensuales acumulados y dato anual definitivo | Existe. **Sin verificar** el resto de desgloses: supuesto de utilización, duración, ocupación y modalidad del contrato del trabajador cedido (fijo discontinuo u otro) |
| **Accidentes de Trabajo (ATR)** | Accidentes con baja por gravedad, actividad (CNAE), territorio, etc. **Índices de incidencia** por actividad (en 2025, construcción 5.510,4 por cada 100.000 trabajadores) ([resumen 2025](https://www.mites.gob.es/estadisticas/eat/eat25_12/ATR_12_2025_Resumen.pdf), [metodología](https://www.mites.gob.es/estadisticas/eat/Informe_Metodologico_Estadarizado_ATR.pdf)) | Avance mensual (hacia el día 13 de m+2) y anual definitivo | Existe |
| **Enfermedades Profesionales (EPR)** | Partes de enfermedad profesional | Avances mensuales | Existe. Contenido sin verificar |
| **Convenios Colectivos de Trabajo (CCT)** | **Variación salarial pactada**, jornada pactada, convenios, empresas y trabajadores afectados, por ámbito del convenio. En abril de 2026, los convenios de ámbito estatal o interautonómico pactaban un **2,96 %** ([avance abril 2026](https://www.mites.gob.es/estadisticas/cct/cct26abrav/Resumen_resultados_CCT_abril-26.pdf)). La fuente es el registro **REGCON** | Avance mensual y anual | Existe. La [Orden TES/1573/2025](https://www.laboral-social.com/orden-tes-1573-2025-actualiza-hojas-estadisticas-regcon-convenios-colectivos) amplía las variables (salarios, jornada, igualdad, digitalización): habrá datos más ricos, pero posible ruptura de serie |
| **Regulación de Empleo (REG)** | ERE y ERTE | Periódica | Existe. Contenido sin verificar |
| **Huelgas y Cierres Patronales (HUE)** | Huelgas, trabajadores implicados y jornadas no trabajadas | Periódica | Existe |
| **Movimiento Laboral Registrado (MLR)** | Anuario con los datos de paro y contratos del SEPE ([notas](https://www.mites.gob.es/estadisticas/MLR/Notas_metodologicas.pdf)) | Anual | Existe. Ver la nota sobre la tabla MLR-18 en el apartado 1 |

Todas aparecen en el [Anuario de Estadísticas del MITES](https://www.mites.gob.es/es/estadisticas/anuarios/2025/index.htm).

### 2.2 SEPE (Servicio Público de Empleo Estatal)

| Estadística | Qué ofrece | Estado |
|---|---|---|
| **Paro registrado** | Por **municipio**, sexo, edad y sector. Mensual. No incluye a los fijos discontinuos inactivos | Existe ([estadísticas por municipio](https://www.sepe.es/HomeSepe/que-es-el-sepe/estadisticas/datos-estadisticos.html&lang=es)) |
| **Contratos registrados** | Por municipio, sexo, **tipo de contrato** y sector. Mensual. Incluye las comunicaciones de contratación de las empresas | Existe. **Sin verificar** el desglose por **ocupación** |
| **Catálogo de datos abiertos** | Descarga de paro y contratos | Existe ([catálogo](https://sede.sepe.gob.es/portalSede/en/datos-abiertos/catalogo-de-datos-del-SEPE)). Formato sin verificar |
| Observatorio de las Ocupaciones | Informes de mercado por ocupación y provincia | **Sin verificar en esta sesión** |

### 2.3 Seguridad Social (Ministerio de Inclusión, Seguridad Social y Migraciones)

| Estadística | Qué ofrece | Estado |
|---|---|---|
| **Afiliación** | Afiliados medios y del último día, por régimen, **CNAE a 2 dígitos**, sexo, comunidad autónoma, provincia y **municipio**. Según el Inventario de Operaciones Estadísticas ([ficha 58015](https://www.ine.es/dyngs/IOE/operacion.htm?numinv=58015)), también por edad, nacionalidad, **tipo de contrato, jornada, grupo de cotización y tamaño de empresa** | Existe. También en [datos.gob.es](https://datos.gob.es/en/catalogo/a06004074-afiliacion-a-la-seguridad-social-media-mensual). Desgloses cruzados sin verificar |
| **Incapacidad temporal (IT)** | Procesos iniciados, **incidencia por cada 1.000 trabajadores protegidos**, prevalencia, **duración media** y gasto. Contingencias comunes por **CNAE a 2 dígitos** | Existe, mensual ([estadísticas IT](https://www.seg-social.es/wps/portal/wss/internet/EstadisticasPresupuestosEstudios/Estadisticas/EST45/EST46/EST328)) |
| Empresas inscritas | Empresas y cuentas de cotización por tamaño | **Sin verificar en esta sesión** |
| **MCVL** (Muestra Continua de Vidas Laborales) | Microdatos anónimos de trayectorias laborales | Existe ([portal](https://portaldatos.seg-social.gob.es/mcvl)). **Solo para investigación sin fines comerciales**: lo más probable es que no se pueda usar en un producto de una empresa |

### 2.4 Agencia Tributaria (AEAT)

| Estadística | Qué ofrece | Estado |
|---|---|---|
| **Mercado de Trabajo y Pensiones en las Fuentes Tributarias** | Salarios a partir del modelo 190: es un **censo**, no una muestra. Por sexo, edad, comunidad autónoma, actividad, **tamaño de empresa**, **deciles y centiles salariales**. Último año localizado: 2023 | Existe ([datos abiertos](https://sede.agenciatributaria.gob.es/Sede/datosabiertos/catalogo/hacienda/Mercado_de_Trabajo_y_Pensiones_en_las_Fuentes_Tributarias.shtml)). Desglose por municipio sin verificar |

---

## 3. Qué añaden a los 6 puntos

| Punto | Lo que da el INE | Lo que añaden estas fuentes |
|---|---|---|
| **1. Benchmark salarial** | EES y EAES (encuestas, con retraso) | **AEAT**: salarios censales por deciles, actividad y tamaño. **Convenios**: subida pactada. Permite comparar salario real con salario pactado |
| **2. Coste y absentismo** | ETCL: horas no trabajadas y coste de IT | **IT de la Seguridad Social**: incidencia y duración media por actividad, cada mes. **Accidentes** y **enfermedades profesionales** con índices de incidencia. Es el núcleo de un informe de absentismo y siniestralidad |
| **3. Mercado de talento** | EPA trimestral, por comunidad autónoma | **Afiliación, paro y contratos** mensuales por municipio. **ETT y CPD**: actividad de la cesión de trabajadores por sector y comunidad autónoma |
| **4. Revisión salarial** | IPT e IPC | **Convenios**: variación salarial pactada mensual por ámbito |
| **5. Igualdad y diversidad** | MYH, discapacidad | Afiliación y contratos por sexo, edad y nacionalidad. AEAT por sexo y edad |
| **6. Contexto comercial** | DIRCE | Afiliación por tamaño de empresa y municipio. **Estadística de ETT** para dimensionar el mercado de la cesión de trabajadores |

### Para el negocio de ETT en particular

Un informe de **cesión de trabajadores (CPD)** podría cruzar:
- **CPD** por sector y comunidad autónoma (estadística ETT);
- **contratos registrados** por tipo de contrato, incluido el fijo discontinuo (SEPE);
- **afiliados** de las ETT y por tipo de contrato (Seguridad Social, estadística ETT);
- **ERTE** y regulación de empleo (MITES), como señal de ajustes de plantilla.

Antes hay que confirmar si la estadística ETT publica el CPD según la modalidad del contrato del trabajador cedido, y cómo afecta el cambio de diciembre de 2024.

---

## 4. Precauciones

1. **Definiciones distintas:**
   - Paro registrado (SEPE) no es lo mismo que paro EPA (INE).
   - Afiliaciones no son personas: alguien con dos empleos cuenta dos veces.
   - Contratos no son empleos.
   - CPD no son trabajadores.
2. **Rupturas de serie conocidas:** los modelos de CPD cambiaron en diciembre de 2024 (Orden TES/1324/2024); las hojas estadísticas de REGCON, con la Orden TES/1573/2025; y, según la prensa, se ha suprimido la tabla MLR-18.
3. **Fijos discontinuos:** según la fuente, aparecen o no. Están en afiliación solo cuando trabajan; no aparecen en el paro registrado durante la inactividad. Hay que documentarlo en cada informe.
4. **Datos agregados:** los microdatos (MCVL) tienen restricciones de uso.
5. **Acceso:** varias fuentes se publican en PDF o en tablas web. Hay que confirmar en cada caso si hay descarga estructurada (CSV o API) antes de automatizar.

## 5. Siguientes pasos propuestos

1. Desde un equipo con acceso a esas webs (o ampliando el workflow de GitHub Actions, si esas webs son accesibles desde allí), **descargar una muestra de cada fuente** y documentar su estructura real, como se hizo con el INE.
2. Prioridad sugerida: **ETT/CPD**, **convenios**, **IT** y **afiliación**. Son las que más diferencian frente a los datos del INE.
3. Preparar una tabla de equivalencias de sector (CNAE), territorio y ocupación (CNO) común a todas las fuentes.
