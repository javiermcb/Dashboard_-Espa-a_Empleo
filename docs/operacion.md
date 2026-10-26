# Operación · qué hacer cuando algo falla

> **Documento heredado de `Datos_INE`.** Describe el proyecto anterior: las menciones a la app `streamlit_app/`, al
> registro de accesos, al repositorio público `datos-rrhh-publicos` y al artefacto con `rrhh.duckdb` (30 días) **no
> aplican a este repositorio**. Las tablas, fuentes y el procedimiento general siguen siendo válidos. Para el estado
> actual, ver `README.md` y `docs/guia_puesta_en_marcha.md`.


| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| Correo / issue **«Incidencias de carga»** con «La carga se ha interrumpido» | Un paso del pipeline ha fallado (código o configuración) | Abrir el enlace de la ejecución, ver el paso en rojo. La app sigue con los datos de la última carga buena. Corregir y lanzar *Actions → Pipeline RRHH → Run workflow*. La issue se cierra sola con la siguiente carga sin fallos. |
| Issue **«Incidencias de carga»**: «No se han publicado los datos de hoy: no superan el control de calidad» | Falta una tabla de la app, está vacía, pierde más de la mitad de sus filas, una tabla mensual de SEPE pierde más de un 5 % o el último periodo de una tabla retrocede | La app sigue con la carga anterior. Ver qué tabla indica la issue y su fuente en `datos/qa/fuentes_carga.csv` (rama `calidad`). Si la caída es legítima (la fuente ha cambiado de alcance), lanzar a mano *Actions → Pipeline RRHH → Run workflow* con «Caída de filas máxima» más alta (p. ej. 0.9). |
| Issue **«Incidencias de carga»** con fuentes «ANTERIOR» | Una web oficial no respondía o cambió su fichero | Si se repite varios días: revisar la web de la fuente (URL o formato nuevo) y adaptar el lector en `pipeline/fuentes.py` o `pipeline/mites_detalle.py`. |
| La app dice **«No se han podido cargar los datos: acceso denegado»** | Ha caducado `RRHH_DATOS_TOKEN` | Crear token nuevo (solo lectura, Contents, repo Datos_INE) y cambiarlo en *Streamlit → Settings → Secrets*. |
| Nadie puede entrar: **«No se ha podido comprobar el acceso»** | Ha caducado o falla `RRHH_LOG_TOKEN` | Token nuevo (Contents + Issues, *Read and write*, solo `Datos_INE_registro`) y cambiarlo en los secretos. |
| **Entrada de administración bloqueada** | 5 claves erróneas seguidas | Esperar 15 minutos. Si no has sido tú, cambiar `RRHH_ADMIN_CLAVE`. |
| Falla **«Pruebas de la app»** tras un cambio | El cambio rompe una página | No publicar hasta que esté en verde; el log dice qué página y por qué. |
| Falla **«Mantener la app activa»** | App caída o privada | Abrir la app; si está dormida, despertarla; comprobar que sigue pública en *Share*. |
| Issue **«Los datos publicados están desactualizados»** (etiqueta `datos-viejos`) | La carga publicada en `datos-modelo` tiene más de 4 días: el workflow del pipeline está desactivado, el cron se ha parado o falla sin avisar | Mirar *Actions → Pipeline RRHH*: si está desactivado, reactivarlo; si no ha corrido, lanzarlo con *Run workflow*. La issue se cierra sola cuando los datos vuelven a estar al día. |
| Issue **«Un dashboard falla con los datos publicados»** (etiqueta `prueba-publicacion`) | Tras publicar, alguna página lanza un error con los datos reales | Abrir la ejecución de *Prueba tras publicar los datos* y ver la página y el error. Los datos ya están publicados y las apps los leen: corregir la página o, si el fallo es de los datos, la tabla. Se cierra sola cuando vuelve a pasar. |
| La app muestra un dato raro | Fuente revisada / cambio de metodología | Página **«Estado de los datos»**: fecha y periodo de cada fuente; contrastar con la web oficial. |

Calendario: renovar los dos tokens antes de su fecha de caducidad (apuntarla al crearlos).
