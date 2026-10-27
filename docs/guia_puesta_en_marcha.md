# Guía de puesta en marcha: de cero a tener todo completo

Esta guía recorre, en orden, todo lo que hay que hacer a mano para que los **tres dashboards** (jóvenes NEET, empleo y
actividad juvenil, FUNDAE) estén publicados, con datos al día y sin que se duerman. Cada paso dice **dónde** pulsar,
**qué** escribir y **cómo comprobar** que ha salido bien.

Convenciones: `así` es algo que se escribe o se pulsa tal cual; «así» es el texto de un botón o menú (los nombres de
los botones de GitHub y Streamlit pueden cambiar un poco con el tiempo).

---

## 0. El mapa: qué es cada cosa

| Pieza | Qué es | Dónde |
|---|---|---|
| Repositorio de los dashboards | Código del pipeline, de los 3 dashboards y de la carga diaria | `github.com/javiermcb/Dashboard_-Espa-a_Empleo` |
| Carga diaria («Pipeline RRHH») | Descarga INE, SEPE, Seguridad Social, Ministerio de Trabajo y FUNDAE, construye el modelo y lo publica | Pestaña **Actions** del repositorio; se ejecuta sola de lunes a viernes a las 06:17 UTC |
| Rama `datos-modelo` | Los datos ya preparados (ficheros Parquet). **La crea la primera carga correcta en `main`** | Rama del mismo repositorio |
| Dashboard 1 | Jóvenes NEET (15-29) | `dashboards/dashboard_1/app.py` |
| Dashboard 2 | Empleo, actividad y paro juvenil por comunidad (EPA) | `dashboards/dashboard_2/app.py` |
| Dashboard 3 | Formación bonificada FUNDAE | `dashboards/dashboard_3/app.py` |
| «Mantener las apps activas» | Abre cada dashboard cada 4 horas para que Streamlit no lo duerma | Pestaña **Actions** |
| Proyecto original `Datos_INE` | La app anterior (`deep-rrhh-stats`) y su propia carga diaria. Es independiente | `github.com/javiermcb/Datos_INE` |

Flujo de los datos: `webs oficiales → carga diaria → rama datos-modelo → los 3 dashboards`.

---

## 1. Estado de partida (lo que ya está hecho)

- Los cuatro PRs están fusionados en `main`: pipeline, capa común, y los tres dashboards.
- Los dashboards son públicos: no tienen acceso con email ni registro de visitas (el código antiguo de acceso está
  apartado en `_apartado/acceso/`).
- La carga diaria corre en `main` y **ya ha publicado** la rama `datos-modelo` (23/10/2026, 07:00 UTC): 46 tablas, con
  ERE/ERTE y 16 de las 18 series de FUNDAE (faltan la 07 y la 02, que los dashboards no usan).
- La cuota de almacenamiento de Actions está resuelta (sección 3).
- **Falta**: crear las apps en Streamlit y configurar los avisos (secciones 4 a 6).

---

## 2. Comprobar que la carga diaria publica los datos

> **Estado a 23/10/2026: hecho.** La primera carga en `main` falló por un timeout transitorio del Ministerio de Trabajo
> (sin copia anterior, el control de calidad exige todas las tablas) y la siguiente, con la caché ya guardada, publicó.
> Esta sección sirve para repetir la comprobación o diagnosticar una carga futura.

La carga empezó sola al fusionar los PRs. Hay que confirmar que termina bien y que crea la rama `datos-modelo`.

1. Abre `github.com/javiermcb/Dashboard_-Espa-a_Empleo` → pestaña **Actions**.
2. En la izquierda, pulsa **Pipeline RRHH**.
3. Mira las ejecuciones con la rama `main`. Una carga completa tarda unos **25 minutos** (el INE tarda unos 8 y las
   otras fuentes entre 10 y 15).
4. Abre la más reciente y mira el resultado:
   - **Verde**: bien. Pasa al punto 6.
   - **Roja**: abre el job `pipeline` y busca el paso en rojo. Los casos conocidos:
     - *«Guardar la publicación como artefacto»* en rojo pero el job continúa: es la cuota de almacenamiento (ver
       sección 3). **No impide publicar.**
     - *«Control de calidad antes de publicar»* en rojo con el texto «falta `fact_regulacion_empleo`» (u otra tabla):
       una descarga del Ministerio ha fallado de forma transitoria. **Reintenta una vez**: en la parte superior
       derecha de la ejecución pulsa «Re-run jobs» → «Re-run failed jobs». Reutiliza lo ya descargado y solo
       repite lo que falló. La primera carga en `main` empieza con la caché vacía, por eso es la más propensa.
5. Si hay varias cargas seguidas (una por cada PR fusionado), GitHub cancela las intermedias; basta con la última.
6. **Comprueba que se ha publicado**: en la página principal del repositorio pulsa el desplegable de ramas
   («main»). Debe aparecer `datos-modelo`. Ábrela: debe tener una carpeta `modelo/` con ficheros `.parquet`,
   `metadatos.json` y `diccionario.csv`. Abre `modelo/metadatos.json`: el campo `generado` es la fecha de la carga.
7. Para lanzar una carga a mano cuando quieras: **Actions → Pipeline RRHH → «Run workflow»**, rama `main`.

Si en algún momento la carga falla de forma persistente, GitHub abre sola una *issue* llamada «Incidencias de carga del
pipeline RRHH» (y te llega por correo). Se cierra sola cuando una carga termina sin fallos de fuentes.

---

## 3. La cuota de almacenamiento de Actions (artefactos)

> **Estado a 23/10/2026: resuelto.** Se borraron 51 de los 56 artefactos de `Datos_INE` (quedan 5, 246 MB: los del 12 al
> 16/10), la retención es de **3 días** en los dos repositorios y el paso del artefacto **no bloquea** la publicación.

**Qué pasaba**: cada carga guarda una copia de seguridad (un «artefacto») de unos 49 MB. Con 30 días de retención y una
carga por cada push de desarrollo, se acumularon 56 (1,86 GB) y la cuota de la cuenta se llenó. El paso fallaba y, al
estar antes del control de calidad, se saltaba la publicación: `Datos_INE` no publicó nada desde el 16/10.

**Si vuelve a aparecer** el aviso `Artifact storage quota has been hit`:
1. Lista los artefactos: `gh api "repos/javiermcb/<repo>/actions/artifacts?per_page=100" --jq '.artifacts[] | [.id,.name,.created_at] | @tsv'`.
2. Borra los que no necesites: `gh api -X DELETE repos/javiermcb/<repo>/actions/artifacts/<ID>`
   (o en la web: **Actions** → la ejecución → sección **Artifacts** → papelera).
3. GitHub recalcula el uso cada **6 a 12 horas**, así que el espacio no se libera al instante.

---

## 4. Repositorio público o privado

Los dashboards leen los datos de la rama `datos-modelo`. Hay dos formas:

### Opción A — Repositorio público (la más sencilla)
Los datos son de fuentes oficiales y las apps son públicas, así que no hay problema en que el repositorio lo sea.
Antes de hacerlo ten en cuenta que el **historial de commits** queda visible, incluido el correo con el que se
hicieron los commits.

1. Repositorio → **Settings** → baja hasta **Danger Zone**.
2. **Change repository visibility** → **Make public**.
3. Escribe el nombre del repositorio para confirmar.

Con el repositorio público **no hace falta ningún token**.

### Opción B — Repositorio privado
Cada app necesita un token de solo lectura:
1. GitHub → tu foto → **Settings** → **Developer settings** → **Personal access tokens** → **Fine-grained tokens**
   → **Generate new token**.
2. *Token name*: `dashboards-datos`. *Expiration*: elige una fecha (anótala: al caducar, las apps dejan de leer
   datos y muestran «acceso denegado»).
3. *Resource owner*: `javiermcb`. *Repository access*: **Only select repositories** → elige solo
   `Dashboard_-Espa-a_Empleo`.
4. *Permissions* → *Repository permissions* → **Contents**: **Read-only**. Nada más.
5. **Generate token** y **copia el valor ahora** (no se vuelve a mostrar). Empieza por `github_pat_`.

**Importante**: comprueba en la documentación de Streamlit Community Cloud qué admite el plan gratuito con
repositorios privados antes de decidir.

---

## 5. Crear las tres apps en Streamlit Community Cloud

Repite el bloque entero **tres veces**, una por dashboard (cambia el fichero principal y el nombre de la URL).

### 5.1 Entrar
1. Ve a `share.streamlit.io` y entra con **Continue with GitHub** (con la cuenta `javiermcb`).
2. Si tu repositorio es privado, GitHub pedirá autorizar a Streamlit el acceso a los repositorios: acepta e incluye
   `Dashboard_-Espa-a_Empleo`.

### 5.2 Crear la app
1. Pulsa **Create app** (arriba a la derecha) y elige la opción de desplegar **desde un repositorio de GitHub**.
2. Rellena:

   | Campo | Dashboard 1 | Dashboard 2 | Dashboard 3 |
   |---|---|---|---|
   | Repository | `javiermcb/Dashboard_-Espa-a_Empleo` | igual | igual |
   | Branch | `main` | `main` | `main` |
   | Main file path | `dashboards/dashboard_1/app.py` | `dashboards/dashboard_2/app.py` | `dashboards/dashboard_3/app.py` |
   | App URL | por ejemplo `neet-jovenes-espana` | por ejemplo `empleo-juvenil-espana` | por ejemplo `fundae-formacion` |

   El nombre de la URL (subdominio) lo eliges tú: queda `https://<nombre>.streamlit.app/`. **Apúntalo**, lo necesitas
   en la sección 6.
3. Pulsa **Advanced settings** y completa:
   - **Python version**: `3.11` (es la versión con la que se prueba el código en GitHub).
   - **Secrets**: pega este texto (formato TOML), **cambiando solo lo que se indica**:

     Si el repositorio es **público**:
     ```toml
     RRHH_DATOS = "https://raw.githubusercontent.com/javiermcb/Dashboard_-Espa-a_Empleo/datos-modelo/modelo/"
     ```
     Si es **privado**, añade también el token de la sección 4:
     ```toml
     RRHH_DATOS = "https://raw.githubusercontent.com/javiermcb/Dashboard_-Espa-a_Empleo/datos-modelo/modelo/"
     RRHH_DATOS_TOKEN = "github_pat_PEGA_AQUI_TU_TOKEN"
     ```
     La URL debe terminar en `modelo/` **con la barra final**. No lleva comillas raras ni espacios.
4. Pulsa **Deploy**. La primera vez instala las dependencias (`requirements.txt` de la raíz) y tarda unos minutos.

### 5.3 Qué debes ver
1. Se abre la app con el título de su dashboard y una barra lateral estrecha (unos 2 cm) que solo lleva la fecha de los datos.
2. **Dashboard 1**: el título «Mapa país: jóvenes NEET en España», tres cifras, un mapa y barras por comunidad.
3. **Dashboard 2**: «Empleo, actividad y sectores con más oportunidad», selector de edad y tabla comparativa.
4. **Dashboard 3**: «Formación bonificada y ecosistema FUNDAE», cifras y mapa.
5. En la barra lateral debe poner «Datos» con una fecha reciente (día/mes/año y hora UTC). En el pie de la página, los enlaces a «Estado de los datos» y «Datos y descargas», la fecha completa de la carga y los avisos de las fuentes.

### 5.4 Si algo sale mal

| Lo que ves | Causa probable | Qué hacer |
|---|---|---|
| «No se han podido cargar los datos: acceso denegado (HTTP 401/403)» | Repo privado y token mal puesto, caducado o sin permiso | Rehacer el token (sección 4B) y actualizarlo en Secrets de la app |
| «No se han podido cargar los datos: no encontrado (HTTP 404)» | La rama `datos-modelo` aún no existe, o la URL está mal escrita | Comprobar la sección 2 (punto 6) y que la URL termine en `modelo/` |
| Página vacía con «Tablas no disponibles en esta carga» | La carga publicó sin alguna tabla | Mira «Estado de los datos» en el menú de la app |
| Error al instalar dependencias | Versión de Python distinta | En Advanced settings, Python 3.11 |
| `ModuleNotFoundError: comun` | Fichero principal mal escrito | Debe ser `dashboards/dashboard_N/app.py` (con la ruta completa) |

Para cambiar **Secrets** después: en `share.streamlit.io` abre la app → menú **⋮** → **Settings** → **Secrets**.

---

## 6. Que las apps no se duerman

Streamlit duerme las apps sin visitas. Un aviso automático las abre cada 4 horas. Hay que decirle sus direcciones.

1. Repositorio `Dashboard_-Espa-a_Empleo` → **Settings**.
2. A la izquierda: **Secrets and variables** → **Actions**.
3. Pestaña **Variables** (no la pestaña «Secrets») → **New repository variable**.
4. Crea tres variables:

   | Name | Value |
   |---|---|
   | `APP_URL_1` | `https://<nombre-del-dashboard-1>.streamlit.app/` |
   | `APP_URL_2` | `https://<nombre-del-dashboard-2>.streamlit.app/` |
   | `APP_URL_3` | `https://<nombre-del-dashboard-3>.streamlit.app/` |

5. **Comprobar**: **Actions** → «Mantener las apps activas» → **Run workflow**. Debe terminar en verde (tarda unos minutos).
6. Si falla, se abre una *issue* «Un dashboard no responde» con el motivo. Casos habituales: la URL está mal
   escrita, o la app se creó como **privada** en Streamlit (un robot sin cuenta no puede entrar). Las apps deben
   ser públicas.

---

## 7. Comprobación final de cada dashboard

Abre cada URL en el navegador (también en el móvil) y comprueba:

**Dashboard 1 — jóvenes NEET**
- [ ] Cifra «% jóvenes NEET (15-29)» con variación frente al año anterior.
- [ ] Mapa por comunidades (geográfico).
- [ ] Selector de año y comparativa por comunidad.
- [ ] Evolución 2015-2025 y desglose por nacionalidad.
- [ ] Dos recuadros azules «Pendientes de fuente» (nivel educativo y urbano/rural): es lo esperado.

**Dashboard 2 — empleo y actividad juvenil**
- [ ] Tres cifras (actividad, empleo, paro) y selector de grupo de edad (16-24, 16-19, 20-24).
- [ ] Barras de actividad por comunidad, con España en naranja, y gráfico de evolución.
- [ ] Tabla comparativa territorial.
- [ ] Tres recuadros «Pendientes de fuente» (sectores, competencias, contrato): esperado.

**Dashboard 3 — FUNDAE**
- [ ] Cifras de participantes, crédito dispuesto y horas.
- [ ] Familias formativas, modalidad, mapa por comunidad y tres gráficos de evolución.
- [ ] Si faltan datos, aparece un aviso (la web de FUNDAE falla a veces; se completa en las cargas siguientes).

**En todos**: menú «Datos» → «Estado de los datos» (qué fuentes se actualizaron) y «Datos y descargas».

---

## 8. Dar a Claude acceso a las fuentes que faltan (red del entorno)

Para localizar y descargar las fuentes de los paneles «pendientes de fuente», el entorno de trabajo de Claude necesita
poder acceder a estos dominios: `servicios.ine.es`, `www.ine.es`, `rplumber.ilo.org`, `ec.europa.eu`,
`www.injuve.es`, `datos.gob.es`.

1. En la sesión de Claude Code (web), abre el **menú del entorno en la barra de título**.
2. Pulsa **Edit**.
3. En **Network access** elige un nivel más amplio, o (con nivel «Limited») añade los dominios en
   **Allowed domains**. Deja marcada la casilla de gestores de paquetes.
4. Guarda y empieza una sesión nueva si hace falta.

Documentación: `https://code.claude.com/docs/en/cloud-environments#network-access`.

Después, pide a Claude que continúe con los paneles pendientes:

| Dashboard | Panel pendiente | Qué se busca |
|---|---|---|
| 1 | 02 Nivel educativo de los NEET | La tabla del INE de NEET por nivel de formación |
| 1 | 03 Urbano / rural | Eurostat `edat_lfse_36` (o equivalente) para España |
| 1 | Población, actividad y empleo | Cifras de Injuve (16-29) o una tabla del INE con ese grupo |
| 2 | 02 comparación con la UE-27 | Eurostat `une_rt_a` o `yth_empl_020` |
| 2 | 04 Sectores con potencial | Previsión de Cedefop (Skills Forecast) por sector |
| 2 | 05 Competencias, 06 Tipo de contrato | Fuente abierta por localizar |

---

## 9. La app original (`Datos_INE`, `deep-rrhh-stats`)

- Su carga diaria llevaba **sin publicar desde el 16/10** por la cuota (mismo fallo). El PR #19 de `Datos_INE` (ya
  fusionado) hace el paso del artefacto no bloqueante y baja la retención a 3 días. **Aún no se ha visto una carga
  programada posterior**: comprueba la del próximo día laborable.
- **No tienes que cambiar nada en Streamlit** de esa app: sus secretos siguen valiendo.
- Para comprobarlo: **Actions** de `Datos_INE` → «Pipeline RRHH» → la ejecución de `main` debe terminar en verde, y
  la rama `datos-modelo` de `Datos_INE` debe tener `metadatos.json` con fecha de hoy.

---

## 10. Limpiezas pendientes (cuando quieras)

- **Borrar ramas ya fusionadas** (no se pudo hacer desde la sesión de Claude: GitHub devolvió 403). En el repositorio →
  pestaña **Branches** → papelera junto a cada una, o por terminal `git push origin --delete <rama>`:
  - `Dashboard_-Espa-a_Empleo`: `claude/calidad-primera-vez`, `claude/dashboard-1-fuentes`, `claude/dashboard-2`,
    `claude/dashboard-3`, `claude/dashboards-base`, `claude/guia-y-retencion`, `claude/limpieza-auditoria`
    (cuando se fusione). Conserva `datos-modelo` (son los datos) y `main`.
  - `Datos_INE`: `claude/artefacto-no-bloqueante` (fusionada). Las demás ramas de ese repo son tuyas: no las toco.
- Borrar `_apartado/acceso/` (código de acceso con email que ya no se usa) cuando confirmes que no hace falta.
- Revisar y fusionar las propuestas automáticas de Dependabot (actualizaciones mensuales de librerías).
- *Decidido (26/10/2026)*: `Datos_INE` y este repositorio son proyectos distintos y mantienen cada uno su propia carga.

---

## 11. Resumen de secretos y variables

**Secrets de cada app de Streamlit** (`share.streamlit.io` → app → ⋮ → Settings → Secrets):

| Nombre | Cuándo | Valor |
|---|---|---|
| `RRHH_DATOS` | siempre | `https://raw.githubusercontent.com/javiermcb/Dashboard_-Espa-a_Empleo/datos-modelo/modelo/` |
| `RRHH_DATOS_TOKEN` | solo si el repo es privado | token fine-grained con *Contents: Read-only* solo en este repo |

**Variables del repositorio** (Settings → Secrets and variables → Actions → Variables):

| Nombre | Valor |
|---|---|
| `APP_URL_1`, `APP_URL_2`, `APP_URL_3` | URL de cada dashboard |

**No hacen falta** secretos de registro de accesos (`RRHH_LOG_*`, `RRHH_ADMIN_*`, `RRHH_HASH_CLAVE`): los dashboards
no tienen acceso ni registro.

---

## 12. Mantenimiento: qué mirar y cuándo

| Frecuencia | Qué | Cómo |
|---|---|---|
| Cada día laborable | Que llegue la carga | Si falla, llega un correo («Incidencias de carga…») |
| Cuando llegue un aviso | Una carga fallida | Sección 2, punto 4: reintentar una vez |
| Si una app dice «dormida» | Que el aviso de las 4 horas funcione | Sección 6, punto 5 |
| Cada pocos meses | Que no caduque el token (solo repo privado) | Fecha anotada en la sección 4B |
| Si una web oficial cambia de formato | Una fuente deja de cargar | «Estado de los datos» de cada app muestra qué fuente falla |

---

## Orden recomendado (resumen de una página)

1. Esperar a que la carga de `main` termine y compruebe que existe la rama `datos-modelo` (sección 2).
2. Decidir si el repositorio es público o privado (sección 4) y, si es privado, crear el token.
3. Crear las 3 apps en Streamlit con sus Secrets (sección 5) y comprobar cada una (sección 7).
4. Crear las variables `APP_URL_1..3` y probar «Mantener las apps activas» (sección 6).
5. Borrar artefactos antiguos de `Datos_INE` según el listado (sección 3).
6. Ampliar la red del entorno de Claude y pedirle que complete los paneles pendientes (sección 8).
