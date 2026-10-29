# Matriz RACI y objetivos de servicio (propuesta)

**Es una propuesta para validar, no un compromiso firmado.** Los nombres de cada rol los asigna la Fundación (ver `docs/gobierno_y_propiedad.md`, sección 2).
Los objetivos se han puesto con lo que el sistema hace hoy y con lo observado en las cargas de esta semana; ajustarlos antes de comunicarlos a nadie.

## 1. Roles

| Rol | Quién (por asignar) | Qué hace |
|---|---|---|
| **Titular** | Fundación Gi Group (persona por nombrar) | Decide y responde del proyecto; firma cesiones y autorizaciones |
| **Resp. técnico** | [ ] | Código, pipeline, despliegue, incidencias técnicas |
| **Suplente técnico** | [ ] | Cubre al responsable técnico (ausencias) |
| **Resp. contenido** | [ ] | Valida definiciones, textos y cifras; decide qué se publica |
| **Asesoría legal / privacidad** | [ ] | Revisa avisos legales, reutilización de fuentes, marca y derechos |
| **Fuentes (terceros)** | INE, Eurostat, SEPE, Seguridad Social, Ministerio, FUNDAE, GitHub, Streamlit | Publican los datos y la plataforma; fuera de nuestro control |
| **Personas usuarias** | Quien consulta los dashboards o los incrusta | Reciben el servicio; pueden avisar de errores |

R = responsable de hacerlo · A = quien responde del resultado (uno solo por fila) · C = se le consulta antes · I = se le informa después.

## 2. Matriz RACI

| Actividad | Titular | Resp. técnico | Suplente | Resp. contenido | Legal | Usuarios |
|---|---|---|---|---|---|---|
| Carga diaria y publicación de datos | I | **A/R** | C | I | – | – |
| Resolver una carga rota o dashboard caído | I | **A/R** | R (si el titular técnico no está) | I | – | I |
| Control de calidad y cifras oficiales de referencia (alta de filas nuevas) | – | R | – | **A** / C | – | – |
| Definiciones y textos de los dashboards | I | C | – | **A/R** | C | I |
| Descargo de responsabilidad y atribución de fuentes | A | R | – | C | **R** | I |
| Condiciones de FUNDAE, Eurostat, Streamlit y reutilización | A | C | – | C | **R** | – |
| Derechos del código y autorización de marca | **A** | I | – | I | R | – |
| Vulnerabilidades y ajustes de seguridad de GitHub | I | **A/R** | R | – | C | I (si les afecta) |
| Actualizaciones de librerías (Dependabot) | – | **A/R** | C | – | – | – |
| Cambios en el código o en los workflows | I | **A/R** | C (revisión) | C (si cambia lo que se ve) | – | – |
| Corregir una cifra publicada errónea | I | R | – | **A** | C | I |
| Migración a la organización de GitHub | **A** | R | C | C | C | I (nuevas URL) |
| Revisión mensual (issues, Dependabot, workflows activos) | I | **A/R** | R | – | – | – |
| Alta, baja y permisos de quien escribe en el repositorio | **A** | R | C | – | – | – |

Hoy hay una sola persona en «Resp. técnico» y nadie asignado como suplente: es el principal riesgo de continuidad.
Y el responsable técnico es también quien aprueba sus cambios: la columna «Suplente: C (revisión)» sirve para que alguien más los vea.

## 3. Objetivos de servicio (SLA/SLO) propuestos

Son **objetivos de mejor esfuerzo**, no garantías. La plataforma (Streamlit Community Cloud gratuito) y GitHub no ofrecen SLA, y los datos dependen de organismos externos.

### Datos

| Indicador | Objetivo | Cómo se mide hoy |
|---|---|---|
| Frescura: carga publicada cada día laborable | Antes de las 18:00 UTC | Hora del run de «Pipeline RRHH». Programada a las 06:17 UTC, GitHub la ha lanzado entre 12:21 y 13:11 UTC esta semana, y la carga dura unos 20-25 min |
| Aviso de datos viejos | Aviso automático si pasan más de 96 h sin carga | Ya existe (issue `datos-viejos`) |
| Calidad antes de publicar | 100 % de las cargas pasan el control de calidad; si no pasa, no se publica y se conserva la última buena | Ya existe (bloqueante) |
| Contraste con cifras oficiales | 20 de 20 coinciden; una desviación se revisa en 5 días laborables | Ya existe (issue `cifras-oficiales`) |
| Retraso de las fuentes (SEPE ~4 meses, FUNDAE anual) | **Fuera del objetivo**: es de cada organismo | Periodo del dato visible en «Estado de los datos» |

### Dashboards

| Indicador | Objetivo | Cómo se mide hoy |
|---|---|---|
| Disponibilidad mensual | 99 % **sin contar** incidencias de la plataforma | Una visita automática cada 4 h es una medida gruesa (no mide minutos de caída); si se quiere un 99 % real hace falta una monitorización externa |
| Errores de la plataforma (HTTP 500 de Streamlit) | Se registran y se esperan; no se pueden resolver desde aquí | Issue `app-caida` |

### Respuesta a incidencias (días laborables)

| Incidencia | Acuse | Resolución objetivo |
|---|---|---|
| Carga rota (issue `pipeline-fallo`) | 1 día | 3 días (mientras, las apps siguen con la última carga buena) |
| Dashboard caído por nuestro código | 1 día | 1 día |
| Cifra errónea publicada | 1 día (aviso o retirada) | 3 días |
| Vulnerabilidad notificada | 3 días | 7 días si es crítica; 30 días el resto |
| Actualización de Dependabot | – | Revisar en 30 días; las de seguridad en 7 |

### Conservación

| Qué | Objetivo |
|---|---|
| Historial de datos publicados | Una copia al mes (etiqueta `datos-AAAA-MM`), las últimas 12 |
| Informes de calidad | Rama `calidad` (última carga) |
| Artefacto de la carga entre trabajos | 3 días |

## 4. Qué haría falta para cumplirlo de verdad

1. Nombrar a las personas de la sección 1, sobre todo el suplente técnico.
2. Decidir si 99 % de disponibilidad es un compromiso: entonces monitorización externa y, quizá, otra plataforma de alojamiento.
3. Que el responsable de contenido reciba las issues de datos (`cifras-oficiales`, `datos-viejos`), no solo el técnico.
4. Revisar estos objetivos con la asesoría legal antes de comunicarlos fuera de la Fundación.
