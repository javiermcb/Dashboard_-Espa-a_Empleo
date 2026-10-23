// Consultas de Power Query (M) para Power BI Desktop.
// Uso: Inicio > Transformar datos > Nueva consulta > Consulta en blanco > Editor avanzado, y pegar UNA consulta por bloque.
//
// Web.Contents con RelativePath permite el refresco programado en Power BI Service
// (una URL construida concatenando texto se considera "origen dinámico" y no se puede programar).
// Credenciales en Power BI Service: Anónimo. Nivel de privacidad: Público.

// ---- Consulta: Ruta (texto) ----
"javiermcb/datos-rrhh-publicos/main/modelo/"

// ---- Consulta: LeerParquet (función) ----
// Se invoca con el nombre del fichero, p. ej. LeerParquet("fact_ine.parquet") o LeerParquet("marts/mart_coste_laboral.parquet")
(fichero as text) as table =>
    Parquet.Document(Binary.Buffer(Web.Contents("https://raw.githubusercontent.com", [RelativePath = Ruta & fichero])))

// ---- Dimensiones (una consulta cada una) ----
// dim_territorio = LeerParquet("dim_territorio.parquet")
// dim_tiempo     = LeerParquet("dim_tiempo.parquet")
// dim_tabla      = LeerParquet("dim_tabla.parquet")

// ---- Tablas por tema (recomendadas para los informes) ----
// mart_salarios_ees        = LeerParquet("marts/mart_salarios_ees.parquet")
// mart_salarios_eaes       = LeerParquet("marts/mart_salarios_eaes.parquet")
// mart_deciles_epa         = LeerParquet("marts/mart_deciles_epa.parquet")
// mart_limites_deciles     = LeerParquet("marts/mart_limites_deciles.parquet")
// mart_coste_laboral       = LeerParquet("marts/mart_coste_laboral.parquet")
// mart_tiempo_trabajo      = LeerParquet("marts/mart_tiempo_trabajo.parquet")
// mart_it_despido          = LeerParquet("marts/mart_it_despido.parquet")
// mart_vacantes            = LeerParquet("marts/mart_vacantes.parquet")
// mart_poblacion_actividad = LeerParquet("marts/mart_poblacion_actividad.parquet")
// mart_ocupados_sector     = LeerParquet("marts/mart_ocupados_sector.parquet")
// mart_tasas_epa           = LeerParquet("marts/mart_tasas_epa.parquet")
// mart_flujos              = LeerParquet("marts/mart_flujos.parquet")
// mart_precios             = LeerParquet("marts/mart_precios.parquet")
// mart_brecha_genero       = LeerParquet("marts/mart_brecha_genero.parquet")
// mart_empresas            = LeerParquet("marts/mart_empresas.parquet")
// mart_tiempo_trabajo_actividad = LeerParquet("marts/mart_tiempo_trabajo_actividad.parquet")   (horas de IT y vacaciones por sección)
// mart_coste_actividad     = LeerParquet("marts/mart_coste_actividad.parquet")
// mart_vacantes_actividad  = LeerParquet("marts/mart_vacantes_actividad.parquet")
// mart_epa_ett             = LeerParquet("marts/mart_epa_ett.parquet")
// mart_temporalidad_motivo = LeerParquet("marts/mart_temporalidad_motivo.parquet")
// mart_horas_extra         = LeerParquet("marts/mart_horas_extra.parquet")
// mart_ocupados_ccaa       = LeerParquet("marts/mart_ocupados_ccaa.parquet")
// mart_teletrabajo         = LeerParquet("marts/mart_teletrabajo.parquet")
// mart_salarios_ees_detalle = LeerParquet("marts/mart_salarios_ees_detalle.parquet")

// ---- Fuentes fuera del INE ----
// fact_sepe_paro_municipio      = LeerParquet("fact_sepe_paro_municipio.parquet")
// fact_sepe_contratos_municipio = LeerParquet("fact_sepe_contratos_municipio.parquet")
// fact_ss_afiliacion            = LeerParquet("fact_ss_afiliacion.parquet")
// fact_cpd_actividad            = LeerParquet("fact_cpd_actividad.parquet")
// fact_convenios                = LeerParquet("fact_convenios.parquet")
// fact_accidentes               = LeerParquet("fact_accidentes.parquet")
// fact_ett_mensual              = LeerParquet("fact_ett_mensual.parquet")         (CPD por modalidad, cesiones, perfil)
// fact_ett_territorio           = LeerParquet("fact_ett_territorio.parquet")      (CPD por CCAA y provincia)
// fact_ett_actividad            = LeerParquet("fact_ett_actividad.parquet")       (CPD por división CNAE)
// fact_ett_resumen              = LeerParquet("fact_ett_resumen.parquet")         (variación oficial interanual)
// fact_convenios_detalle        = LeerParquet("fact_convenios_detalle.parquet")   (sector, territorio, jornada, cláusula)
// fact_accidentes_detalle       = LeerParquet("fact_accidentes_detalle.parquet")  (formato largo: cuadro, medida, valor)
// fact_regulacion_empleo        = LeerParquet("fact_regulacion_empleo.parquet")   (ERE/ERTE, 10 meses)
// fact_incapacidad_temporal     = LeerParquet("fact_incapacidad_temporal.parquet") (IT por provincia)

// ---- Alertas de la última carga (CSV) ----
// alertas =
let
    Origen = Csv.Document(Web.Contents("https://raw.githubusercontent.com", [RelativePath = Ruta & "alertas.csv"]),
                          [Delimiter = ";", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Cabecera = Table.PromoteHeaders(Origen, [PromoteAllScalars = true])
in
    Cabecera

// ---- Tabla genérica (todo el INE en formato largo, para exploración) ----
// fact_ine = LeerParquet("fact_ine.parquet")

// RELACIONES (Vista de modelo), todas de varios a uno y filtro en una dirección:
//   <tabla>[territorio_id] -> dim_territorio[territorio_id]     (todas las mart_*, fact_ine, fact_sepe_*, fact_ss_afiliacion, fact_accidentes,
//                                                               fact_ett_territorio, fact_incapacidad_temporal; en las de detalle puede estar vacío)
//   <tabla>[fecha]         -> dim_tiempo[fecha]                 (todas salvo fact_convenios y fact_accidentes)
//   fact_ine[tabla_id]     -> dim_tabla[tabla_id]
// Jerarquía de territorio en dim_territorio: ccaa_nombre > nombre (filtrar nivel = "Provincia" o "Municipio" según la página).
// fact_convenios no tiene territorio (dato nacional) y se analiza por anyo_efectos / mes_registro.
