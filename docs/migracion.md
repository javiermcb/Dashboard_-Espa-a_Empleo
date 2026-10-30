# Migración a otra cuenta de GitHub y de Streamlit

Todo se hace desde el navegador, sin terminal. El código no depende del propietario: los workflows usan
`github.repository` y no hay secretos. Lo que cambia es la configuración, las apps de Streamlit y unos textos.
Los menús de GitHub y Streamlit pueden cambiar de nombre; si algo no coincide, se anota y se ajusta.

## 0. Datos que hay que facilitar (se rellenan antes de empezar)

| Dato | Valor |
|---|---|
| Propietario nuevo en GitHub (`NUEVO_OWNER`) | |
| Nombre del repositorio nuevo (`NUEVO_REPO`) | |
| Subdominio nuevo de la app 1 | `https://________.streamlit.app/` |
| Subdominio nuevo de la app 2 | `https://________.streamlit.app/` |
| Subdominio nuevo de la app 3 | `https://________.streamlit.app/` |
| Buzón de contacto para `SECURITY.md` (corporativo; el repo es público) | |

Con estos datos se prepara una PR que sustituye todas las referencias antiguas (sección 7).

## 1. Copiar el repositorio sin terminal

Opción A, **transferir** (conserva todo y la URL antigua redirige): Settings → General → Danger zone →
*Transfer*. Solo sirve si el destino acepta la transferencia.

Opción B, **importar** a un repositorio nuevo: `https://github.com/new/import`.
1. En *Your old repository's clone URL* pon `https://github.com/javiermcb/Dashboard_-Espa-a_Empleo`.
2. Elige `NUEVO_OWNER`, `NUEVO_REPO` y visibilidad **Public**.
3. Al terminar, comprueba en el repo nuevo que existen las ramas `main`, `datos-modelo` y `calidad` y las
   etiquetas `datos-AAAA-MM`. Si faltan `datos-modelo` o `calidad`, el pipeline las crea solo en su primera carga.

## 2. Configuración del repositorio nuevo (Settings)

1. **Actions → General**: permitir Actions; *Workflow permissions* = *Read and write*.
2. **General → Features**: Issues activado.
3. **General → Pull Requests**: *Automatically delete head branches*.
4. **Code security**: Dependabot alerts y security updates, secret scanning, push protection,
   *Private vulnerability reporting*.
5. **Rules → Rulesets** sobre `main`: PR obligatoria y checks `paginas` y `pruebas`. No bloquear el force-push
   en `datos-modelo` ni en `calidad`: el pipeline las reescribe.
6. **Secrets and variables → Actions → Variables**: `APP_URL_1`, `APP_URL_2`, `APP_URL_3` (tras la sección 5).
   `RRHH_PUBLICO_REPO` solo si los datos se publican en otro repo. No hay secretos que crear.

## 3. Primera carga

Actions → *Pipeline RRHH* → *Run workflow* en `main`. Si la caché está vacía, la fuente FUNDAE puede necesitar
2 o 3 ejecuciones. Comprobar: rama `datos-modelo` con `modelo/metadatos.json`, rama `calidad`, etiqueta
`datos-AAAA-MM` y *Prueba tras publicar* en verde.

## 4. Cuenta nueva de Streamlit

`https://share.streamlit.io` → *Continue with GitHub* con la cuenta nueva y autorizar el acceso al repo nuevo.

## 5. Desplegar las 3 apps

*Create app* → *Deploy a public app from GitHub*, una vez por dashboard:

| App | Main file path |
|---|---|
| 1 | `dashboards/dashboard_1/app.py` |
| 2 | `dashboards/dashboard_2/app.py` |
| 3 | `dashboards/dashboard_3/app.py` |

Repository `NUEVO_OWNER/NUEVO_REPO`, rama `main`, Python 3.11. En *Advanced settings → Secrets*:

```
RRHH_DATOS = "https://raw.githubusercontent.com/NUEVO_OWNER/NUEVO_REPO/datos-modelo/modelo/"
```

Respetar mayúsculas y minúsculas y acabar en `/`. `RRHH_DATOS_TOKEN` solo si el repo fuese privado.

## 6. Cerrar el circuito (todo desde Actions)

1. Guardar las 3 URL en `APP_URL_1..3`.
2. Ejecutar *Mantener las apps activas* y *Comprobar el despliegue* (manual).
3. Abrir cada app y ver «Última carga» con fecha reciente.

## 7. Textos con la cuenta antigua

Referencias que hay que sustituir (inventario por búsqueda en el repo):

| Fichero | Qué |
|---|---|
| `README.md` | enlace a `Datos_INE` y valor de `RRHH_DATOS` |
| `docs/guia_puesta_en_marcha.md` | enlaces, cuenta de Streamlit, valor de `RRHH_DATOS` |
| `docs/gobierno_y_propiedad.md` | tabla de propiedad |
| `docs/explotacion.md` | repositorio de datos |
| `pipeline/powerbi/consultas.pq` | URL base de los datos |
| `pipeline/consultas/ejemplos.sql` | URL de ejemplo |
| `SECURITY.md` | contacto |

`Datos_INE` es un repositorio aparte; solo se cambia el enlace si también se migra.

## 8. Verificación y cierre

- [ ] Las 3 apps cargan con «Última carga» reciente.
- [ ] La carga programada (06:17 UTC, días laborables) se ejecuta; si GitHub la retrasa, lanzarla a mano.
- [ ] Se crean los issues de calidad y de cifras oficiales.
- [ ] 2FA en todos los miembros y ruleset de `main` verificada.
- [ ] Enlaces o iframes externos actualizados.
- [ ] Solo después de lo anterior, borrar o desactivar repo y apps antiguos.

Mientras tanto, repo y apps antiguos siguen activos: es el rollback.
