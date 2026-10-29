# Política de seguridad

## Cómo avisar de una vulnerabilidad

No abras una issue pública con detalles de una vulnerabilidad. Usa **Security → Report a vulnerability** de este repositorio
(avisos privados de GitHub; si el botón no aparece, aún no está activado: ver `docs/gobierno_y_propiedad.md`, sección 4) o escribe
a la persona responsable indicada en ese mismo documento.

## Qué hay en el alcance

- Los tres dashboards públicos de Streamlit (`dashboards/`, `comun/`).
- El pipeline de carga y publicación (`pipeline/`, `.github/workflows/`).
- Los datos publicados en la rama `datos-modelo`.

## Qué no contiene este proyecto

- No hay contraseñas, claves ni tokens en el código ni en el historial (se revisó antes de hacerlo público).
- No se tratan datos personales: las cifras son agregados por territorio, edad, sexo y sector procedentes de fuentes oficiales.
- Las apps no recogen estadísticas de uso (`gatherUsageStats = false`).

## Medidas que ya existen

- Acciones de GitHub fijadas por commit y permisos mínimos por workflow.
- La carga se divide en dos trabajos: el que lee ficheros de terceros solo puede leer el repositorio; solo el de publicación escribe.
- Dependabot propone actualizaciones mensuales de acciones y librerías.
- Las apps leen los datos con una conexión DuckDB limitada a su carpeta y bloqueada.

## Qué se espera de quien avise

Descripción, pasos para reproducirlo y su impacto. Se responderá en cuanto sea posible; este proyecto lo mantiene una persona, sin
plazos garantizados (ver `docs/gobierno_y_propiedad.md`).
