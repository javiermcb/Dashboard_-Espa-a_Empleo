# Dashboard 1 · Jóvenes NEET en España — revisión de fuentes

Estado a 2026-10-22. Revisión hecha sin acceso directo a INE, ILOSTAT, Eurostat ni Banco Mundial (el entorno bloquea esos
dominios): lo «comprobado en el modelo» sale de `resultados/dev_modelo`; lo «visto en búsqueda» son fichas publicadas por
las propias fuentes y **no está verificado descargando los datos**.

## Panel a panel

| Panel de la maqueta | Fuente | Estado |
|---|---|---|
| 01 Mapa NEET por CCAA y 05 Comparativa por CCAA | INE tabla 62285 (NEET 15-29 por CCAA, 2015-2025) | Comprobado en el modelo. Las CCAA solo vienen en `serie_nombre` (no en `territorio_id`): hay que mapearlas a `dim_territorio` (incl. Ceuta y Melilla) |
| 04 Evolución temporal | INE 62285 (total nacional), 2015-2025 | Comprobado en el modelo |
| KPI % NEET | INE 62285 / 59513 | Comprobado. Es **15-29** |
| NEET por sexo y nacionalidad (complemento) | INE 59513, 59514, 49508 | Comprobado en el modelo (59513 y 59514: 15-29; 49508: 15-24) |
| KPI tasa de actividad y de empleo 16-29 | EPA INE 66023 / 66031 | **No sirve**: solo trae «16-19», «20-24», «25-54»… sin 25-29 ni 16-29 |
| KPI volumen de población 16-29 | Injuve publica «EPA resultados 16 a 29» (tablas PDF trimestrales, a partir de la EPA) | Visto en búsqueda; formato PDF, sin API verificada |
| 02 Nivel educativo de los NEET | datos.gob.es: «Población joven (15 a 29 años) que ni estudia ni trabaja por sexo, CCAA, nivel de formación y año» (desde 2002, EPA) | Visto en búsqueda; falta localizar la tabla INE de origen |
| 03 Urbano / rural | Eurostat `edat_lfse_36` (NEET por sexo, edad, nacionalidad y grado de urbanización) | Visto en búsqueda; grado de urbanización a nivel nacional, no se ha verificado que incluya España ni 15-29. ILOSTAT: sin ficha de España con urbano/rural encontrada |

## Edad: 16-29 frente a 15-29

- La EPA mide desde los 16 años. El INE publica el NEET en **15-29** (indicador ODS 8.6.1.2, también el del Pilar Europeo
  de Derechos Sociales); el 8.6.1.1 es 15-24.
- Injuve publica cifras de 16-29 a partir de la EPA (su NEET ronda 13,3 % en 2022, 12,8 % en 2023 y 11,9 % en 2024, según
  la búsqueda; sin verificar). No se han localizado en forma de tabla descargable automáticamente.
- Con los datos agregados que carga hoy el pipeline no se puede construir un NEET 16-29 ni tasas 16-29.

## Pendiente de verificar con acceso de red

Dominios a permitir: `servicios.ine.es`, `www.ine.es`, `rplumber.ilo.org`, `ec.europa.eu`, `www.injuve.es`, `datos.gob.es`.
1. Tabla INE de NEET por nivel de formación (origen del conjunto de datos.gob.es).
2. Tabla EPA con grupo 16-29 (actividad, empleo, población).
3. Si Eurostat `edat_lfse_36` (u otra) da urbano/rural para España en el grupo de edad necesario.
4. Si ILOSTAT ofrece algo adicional para España (no se ha localizado nada).
