# Dashboard 1 · Jóvenes NEET en España — revisión de fuentes

Estado a 2026-10-27. Eurostat (`ec.europa.eu`) sí se ha podido descargar; INE, ILOSTAT, Injuve y datos.gob.es seguían
bloqueados desde el entorno de desarrollo. Lo «comprobado en el modelo» sale de `resultados/dev_modelo`; lo «visto en
búsqueda» son fichas publicadas por las propias fuentes y **no está verificado descargando los datos**.

## Panel a panel

| Panel de la maqueta | Fuente | Estado |
|---|---|---|
| 01 Mapa NEET por CCAA y 05 Comparativa por CCAA | INE tabla 62285 (NEET 15-29 por CCAA, 2015-2025) | Comprobado en el modelo. Las CCAA solo vienen en `serie_nombre` (no en `territorio_id`): hay que mapearlas a `dim_territorio` (incl. Ceuta y Melilla) |
| 04 Evolución temporal | INE 62285 (total nacional), 2015-2025 | Comprobado en el modelo |
| KPI % NEET | INE 62285 / 59513 | Comprobado. Es **15-29** |
| NEET por sexo y nacionalidad (complemento) | INE 59513, 59514, 49508 | Comprobado en el modelo (59513 y 59514: 15-29; 49508: 15-24) |
| KPI tasa de empleo | EPA INE 66023 / 66031 no sirve (sin 16-29). Eurostat `lfsa_ergan`, España, 15-29 | **Descargado y cargado** (`pipeline/eurostat.py`). Es **15-29**: Eurostat no publica 16-29. Sin tasa de actividad por ahora |
| KPI volumen de población 16-29 | Eurostat `demo_pjan` (población a 1 de enero por edad simple), suma de 16 a 29 | **Descargado y cargado**. Exactamente 16-29 |
| 02 Nivel educativo de los NEET | Eurostat `edat_lfse_21` (tasa de NEET por nivel, 15-29) × `lfsa_pganedm` (población 15-29 por nivel) | **Cargado como cálculo propio**: Eurostat no publica el reparto directamente. Datos 2021-2025. Las tablas del INE siguen sin verificar (el INE sigue bloqueado en este entorno) |
| 03 Urbano / rural | Eurostat `edat_lfse_29` (tasa de NEET por grado de urbanización: ciudades, pueblos y periferias, zonas rurales; 15-29) | **Cargado como tasas**, no como reparto: no se ha localizado la población por grado de urbanización, y sin ella no se puede calcular cuántos NEET viven en cada entorno |

## Edad: 16-29 frente a 15-29

- La EPA mide desde los 16 años. El INE publica el NEET en **15-29** (indicador ODS 8.6.1.2, también el del Pilar Europeo
  de Derechos Sociales); el 8.6.1.1 es 15-24.
- Injuve publica cifras de 16-29 a partir de la EPA (su NEET ronda 13,3 % en 2022, 12,8 % en 2023 y 11,9 % en 2024, según
  la búsqueda; sin verificar). No se han localizado en forma de tabla descargable automáticamente.
- Con los datos agregados que carga hoy el pipeline no se puede construir un NEET 16-29 ni tasas 16-29.

## Pendiente de verificar con acceso de red

Dominios a permitir: `servicios.ine.es`, `www.ine.es`, `rplumber.ilo.org`, `ec.europa.eu`, `www.injuve.es`, `datos.gob.es`.
1. Tabla INE de NEET por nivel de formación (origen del conjunto de datos.gob.es), que daría el reparto directo y por CCAA.
2. Tabla EPA con grupo 16-29 (actividad, empleo, población) para sustituir el 15-29 de Eurostat.
3. Población por grado de urbanización (15-29) para poder repartir los NEET entre entornos.
4. Si ILOSTAT ofrece algo adicional para España (no se ha localizado nada).
