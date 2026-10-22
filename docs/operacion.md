# Operación · qué hacer cuando algo falla

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| Correo / issue **«Incidencias de carga»** con «La carga se ha interrumpido» | Un paso del pipeline ha fallado (código o configuración) | Abrir el enlace de la ejecución, ver el paso en rojo. La app sigue con los datos de la última carga buena. Corregir y lanzar *Actions → Pipeline RRHH → Run workflow*. La issue se cierra sola con la siguiente carga sin fallos. |
| Issue **«Incidencias de carga»**: «No se han publicado los datos de hoy: no superan el control de calidad» | Falta una tabla de la app, está vacía o pierde más de la mitad de sus filas | La app sigue con la carga anterior. Ver qué tabla indica la issue y su fuente en `datos/qa/fuentes_carga.csv` (rama `calidad`). Si la caída es legítima (la fuente ha cambiado de alcance), lanzar a mano *Actions → Pipeline RRHH → Run workflow* con «Caída de filas máxima» más alta (p. ej. 0.9). |
| Issue **«Incidencias de carga»** con fuentes «ANTERIOR» | Una web oficial no respondía o cambió su fichero | Si se repite varios días: revisar la web de la fuente (URL o formato nuevo) y adaptar el lector en `pipeline/fuentes.py` o `pipeline/mites_detalle.py`. |
| La app dice **«No se han podido cargar los datos: acceso denegado»** | Ha caducado `RRHH_DATOS_TOKEN` | Crear token nuevo (solo lectura, Contents, repo Datos_INE) y cambiarlo en *Streamlit → Settings → Secrets*. |
| Nadie puede entrar: **«No se ha podido comprobar el acceso»** | Ha caducado o falla `RRHH_LOG_TOKEN` | Token nuevo (Contents + Issues, *Read and write*, solo `Datos_INE_registro`) y cambiarlo en los secretos. |
| **Entrada de administración bloqueada** | 5 claves erróneas seguidas | Esperar 15 minutos. Si no has sido tú, cambiar `RRHH_ADMIN_CLAVE`. |
| Falla **«Pruebas de la app»** tras un cambio | El cambio rompe una página | No publicar hasta que esté en verde; el log dice qué página y por qué. |
| Falla **«Mantener la app activa»** | App caída o privada | Abrir la app; si está dormida, despertarla; comprobar que sigue pública en *Share*. |
| La app muestra un dato raro | Fuente revisada / cambio de metodología | Página **«Estado de los datos»**: fecha y periodo de cada fuente; contrastar con la web oficial. |

Calendario: renovar los dos tokens antes de su fecha de caducidad (apuntarla al crearlos).
