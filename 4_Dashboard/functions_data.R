# ===============================================================================
# Dashboard - Red OTUS Colombia
# ===============================================================================
# Proyecto:     Sistema de Monitoreo de Biodiversidad con Cámaras Trampa
#               Functions
# Autores:      Cristian C. Acevedo - Instituto Humboldt (2025)
#               Angélica Diaz Pulido - Instituto Humboldt (2025)
#               Jorge Ahumada (c) Conservation International (2020)
# Descripción:  Dashboard interactivo Shiny para visualización y análisis de
#               datos de fototrampeo de Wildlife Insights. Soporta análisis
#               multi-evento, vistas consolidadas y exportación de reportes.
# Tecnología:   R Shiny + shinydashboard + Plotly + Leaflet
# Versión:      2.0 - Arquitectura consolidada Parquet
# Licencia:     CC0 1.0 Universal (Public Domain)
# Última mod.:  2026-01-26

# Cómo citar:
# (APA): Acevedo, C. C., & Diaz-Pulido, A. (2026). Dashboard_Monitoreo_Camaras_Trampa_Red_OTUS_Colombia. 
# Instituto de Investigación de Recursos Biológicos Alexander von Humboldt. https://github.com/PEM-Humboldt/dashboard-red-otus
# ===============================================================================

# ===============================================================================
# LIBRERÍAS REQUERIDAS
# ===============================================================================

# Manipulación y transformación de datos
require(tidyverse)
require(dplyr)
require(tidyr)
require(readr)
require(readxl)

# Visualización de datos
require(ggplot2)
require(treemapify)
require(cowplot)
require(gridExtra)
require(plotly)

# Manejo de fechas y tiempos
library(lubridate)

# Procesamiento de imágenes
require(png)
require(magick)

# Mapas interactivos
library(ggmap)
library(leaflet)
library(htmltools)

# Fuentes personalizadas (opcional)
library(extrafont)
# font_import()  # Ejecutar solo una vez para importar fuentes del sistema
# loadfonts()    # Cargar fuentes disponibles

# ===============================================================================
# FUNCIONES AUXILIARES
# ===============================================================================

extract_date_ymd <- function(df) {
  #' Extrae fechas de timestamps de Wildlife Insights
  #'
  #' Convierte timestamps en formato ISO 8601 a objetos Date de R,
  #' eliminando información de hora y zona horaria.
  #'
  #' @param df DataFrame con columnas 'photo_datetime' o 'date'
  #'
  #' @return Vector de objetos Date en formato YYYY-MM-DD
  #'
  #' @examples
  #' extract_date_ymd(df_images)
  #'
  
  col <- if ("photo_datetime" %in% names(df)) df$photo_datetime
  else if ("date" %in% names(df)) df$date
  else return(as.Date(character()))
  
  x <- as.character(col)
  # Conserva solo 'YYYY-MM-DD' (elimina hora, 'T', etc.)
  x <- sub("[ T].*$", "", x)
  suppressWarnings(as.Date(x))
}

# ===============================================================================
# FUNCIONES PARA MANEJO DE EVENTOS DE MUESTREO
# ===============================================================================

obtener_eventos_disponibles <- function() {
  #' Verifica disponibilidad de archivos de datos procesados
  #'
  #' Valida la existencia de los 3 archivos parquet requeridos por la arquitectura
  #' simplificada del dashboard. Genera advertencias detalladas si faltan archivos.
  #'
  #' @details
  #' Archivos requeridos:
  #'   - observations.parquet: Datos de imágenes y detecciones
  #'   - deployments.parquet: Metadata de cámaras y sitios
  #'   - projects.parquet: Información de proyectos
  #'
  #' @return Character vector con "CONSOLIDADO" si todos los archivos existen,
  #'         character(0) si faltan archivos
  #'
  
  data_path <- "dashboard_input_data/"
  
  if (!dir.exists(data_path)) {
    warning(paste("No se encontró la carpeta", data_path))
    return(character(0))
  }
  
  # Verificar que existan los 3 archivos parquet
  archivos_requeridos <- c(
    "observations.parquet",
    "deployments.parquet",
    "projects.parquet"
  )
  
  archivos_existentes <- sapply(archivos_requeridos, function(f) {
    file.exists(file.path(data_path, f))
  })
  
  if (!all(archivos_existentes)) {
    archivos_faltantes <- archivos_requeridos[!archivos_existentes]
    warning(paste(
      "Archivos parquet faltantes en", data_path, ":\n",
      paste("  •", archivos_faltantes, collapse = "\n"),
      "\nEjecute process_RAW_data_WI.py para generar los archivos."
    ))
    return(character(0))
  }
  
  # Retornar CONSOLIDADO (datos están en los 3 archivos parquet)
  return("CONSOLIDADO")
}

# ===============================================================================
# NOTA: Funciones obsoletas eliminadas (2025-12-09)
# ===============================================================================
# Las siguientes funciones fueron eliminadas en la refactorización:
#   - cargar_datos_evento() → Reemplazada por cargar_datos_consolidados()
#   - slotDateinweek(), makedonutplots(), calculateEffort()
#   - makeDeploymentGuideGraph(), makeMapGoogle(), makeMapLeafletOld()
#   - calcular_indice_gini_simpson(), calcular_entropia_shannon()
#
# Backup disponible: functions_data_BACKUP_20251209.R
# ===============================================================================

cargar_datos_consolidados <- function(interval = "30min") {
  #' Carga y procesa datos consolidados de fototrampeo
  #'
  #' Lee archivos parquet procesados y genera estadísticas dinámicas por sitio.
  #' Implementa arquitectura simplificada de 3 archivos.
  #'
  #' @param interval Intervalo temporal para cálculos futuros
  #'        (valores: '5seg', '1min', '30min', '1h', '6h', '24h')
  #'
  #' @return Lista con componentes:
  #'   \describe{
  #'     \item{iavhdata}{DataFrame de observaciones con metadata completa}
  #'     \item{tableSites}{DataFrame de estadísticas agregadas por sitio}
  #'     \item{projects}{DataFrame con información de proyectos}
  #'     \item{evento}{String "CONSOLIDADO" indicando modo de carga}
  #'   }
  #'   Retorna NULL si hay errores en la carga.
  #'
  #' @details
  #' La función ejecuta:
  #'   1. Validación de existencia de archivos parquet
  #'   2. Carga de datos con librería arrow
  #'   3. Generación dinámica de estadísticas por deployment
  #'   4. Cálculo de rankings y métricas agregadas
  #'
  
  data_path <- "dashboard_input_data/"
  
  if (!dir.exists(data_path)) {
    stop(paste("❌ No se encontró la carpeta", data_path))
  }
  
  tryCatch({
    require(arrow)
    
    # Cargar archivos parquet
    obs_path <- file.path(data_path, "observations.parquet")
    if (!file.exists(obs_path)) {
      stop("❌ No se encontró observations.parquet")
    }
    iavhdata <- arrow::read_parquet(obs_path)
    
    dep_path <- file.path(data_path, "deployments.parquet")
    if (!file.exists(dep_path)) {
      stop("❌ No se encontró deployments.parquet")
    }
    deployments <- arrow::read_parquet(dep_path)
    
    proj_path <- file.path(data_path, "projects.parquet")
    if (!file.exists(proj_path)) {
      stop("❌ No se encontró projects.parquet")
    }
    projects <- arrow::read_parquet(proj_path)
    
    # Convertir a data.frame estándar
    iavhdata <- as.data.frame(iavhdata)
    deployments <- as.data.frame(deployments)
    projects <- as.data.frame(projects)
    
    # Enriquecer observations con nombres de proyecto
    if (!"project_short_name" %in% names(iavhdata)) {
      project_names <- projects %>%
        dplyr::select(project_id, project_short_name) %>%
        dplyr::distinct()
      
      iavhdata <- iavhdata %>%
        dplyr::left_join(project_names, by = "project_id")
    }
    
    # Generar estadísticas por sitio desde observaciones
    tableSites <- iavhdata %>%
      dplyr::group_by(project_id, project_short_name, deployment_name, 
                      Corporacion, subproject_name) %>%
      dplyr::summarise(
        n = n(),
        ndepl = 1,
        effort = dplyr::first(deployment_days),
        ospTot = dplyr::n_distinct(sp_binomial[!is.na(sp_binomial) & sp_binomial != ""]),
        ospMamiferos = dplyr::n_distinct(sp_binomial[class == "Mammalia" & !is.na(sp_binomial)]),
        ospAves = dplyr::n_distinct(sp_binomial[class == "Aves" & !is.na(sp_binomial)]),
        lat = dplyr::first(latitude),
        lon = dplyr::first(longitude),
        .groups = "drop"
      ) %>%
      dplyr::rename(
        site_name = deployment_name,
        departamento = Corporacion
      )
    
    # Calcular rankings por métrica
    tableSites <- tableSites %>%
      dplyr::mutate(
        rank_images = rank(-n, ties.method = "first"),
        rank_ndepl = 1,
        rank_effort = rank(-effort, ties.method = "first", na.last = "keep"),
        rank_onsp = rank(-ospTot, ties.method = "first"),
        rank_onMamiferos = rank(-ospMamiferos, ties.method = "first"),
        rank_onAves = rank(-ospAves, ties.method = "first"),
        collector = project_short_name,
        row = dplyr::row_number()
      )
    
    # Mapear subproject_name a evento_muestreo para compatibilidad
    if ("subproject_name" %in% names(iavhdata) && !"evento_muestreo" %in% names(iavhdata)) {
      iavhdata$evento_muestreo <- iavhdata$subproject_name
    }
    
    if ("subproject_name" %in% names(tableSites) && !"evento_muestreo" %in% names(tableSites)) {
      tableSites$evento_muestreo <- tableSites$subproject_name
    }
    
    # Agregar administradores de proyecto
    if ("project_admin" %in% names(projects)) {
      project_admins <- projects %>%
        dplyr::select(project_id, project_admin) %>%
        dplyr::distinct()
      
      tableSites <- tableSites %>%
        dplyr::left_join(project_admins, by = "project_id")
    }
    
    cat("✅ Datos cargados exitosamente:\n")
    cat(sprintf("   • %d observaciones\n", nrow(iavhdata)))
    cat(sprintf("   • %d sitios\n", nrow(tableSites)))
    cat(sprintf("   • %d proyectos\n", length(unique(iavhdata$project_id))))
    cat(sprintf("   • %d eventos\n", length(unique(iavhdata$subproject_name[!is.na(iavhdata$subproject_name)]))))
    
    return(list(
      iavhdata = iavhdata,
      tableSites = tableSites,
      projects = projects,
      evento = "CONSOLIDADO"
    ))
    
  }, error = function(e) {
    cat("❌ Error al cargar archivos Parquet:", conditionMessage(e), "\n")
    return(NULL)
  })
}

# ===============================================================================
# FUNCIONES DE VISUALIZACIÓN Y ANÁLISIS
# ===============================================================================

# NOTA: Funciones obsoletas eliminadas en refactorización 2025-12-09
# Las siguientes funciones de versiones anteriores NO se utilizan actualmente:
#   - drawInfoBoxes(), makeInfoPanel(), drawSpeciesDiversityBox(), makeSpeciesPanel()
#   - makeSpeciesGraph() (reemplazada por tabla interactiva HTML)
#
# El dashboard actual utiliza componentes HTML personalizados en lugar de
# gráficos con iconos PNG. Ver app.R sección "Indicadores Clave".
# Backup: functions_data_BACKUP_20251209.R

makeSpeciesTable <- function(subset, interval = 30, unit = "minutes", species_stats = NULL) {
  #' Genera tabla de ranking de especies por eventos independientes
  #'
  #' Calcula registros independientes aplicando filtro temporal para eliminar
  #' duplicados (imágenes del mismo taxón en el mismo sitio dentro del intervalo).
  #' Soporta modo optimizado con estadísticas pre-calculadas.
  #'
  #' @param subset DataFrame de observaciones con columnas:
  #'   - sp_binomial: Nombre científico
  #'   - class: Clase taxonómica (Aves, Mammalia, etc.)
  #'   - deployment_name: Identificador del sitio
  #'   - photo_datetime: Timestamp de captura
  #' @param interval Intervalo temporal para eliminar duplicados (default: 30)
  #' @param unit Unidad de tiempo ('seconds', 'minutes', 'hours', 'days')
  #' @param species_stats DataFrame pre-calculado con estadísticas (opcional)
  #'
  #' @return data.frame con columnas:
  #'   - Ranking: Posición por número de registros independientes
  #'   - Especie: Nombre científico
  #'   - Numero imagenes: Total de imágenes capturadas
  #'   - Registros independientes: Eventos únicos tras filtro temporal
  #'   - Tipo: Categoría taxonómica (Ave, Mamifero, Otro)
  #'
  #' @details
  #' Modos de operación:
  #'   - Optimizado: Usa species_stats pre-calculado (rápido)
  #'   - Tradicional: Ejecuta remove_duplicates en tiempo real (fallback)
  #'
  
  # RUTA OPTIMIZADA: Usar datos pre-calculados si están disponibles
  if (!is.null(species_stats) && nrow(species_stats) > 0) {
    # Filtrar species_stats según los datos del subset actual
    # Identificar proyecto/evento del subset
    project_ids <- unique(subset$project_id[!is.na(subset$project_id)])
    eventos <- unique(subset$subproject_name[!is.na(subset$subproject_name)])
    
    # Filtrar species_stats
    stats_filtrado <- species_stats
    
    # Si hay filtro específico de proyecto
    if (length(project_ids) > 0 && !all(is.na(project_ids))) {
      if ("TODOS" %in% project_ids || length(project_ids) > 1) {
        # Vista consolidada - usar registro "TODOS"
        stats_filtrado <- species_stats %>% dplyr::filter(project_id == "TODOS")
      } else {
        # Proyecto específico
        stats_filtrado <- species_stats %>% dplyr::filter(project_id %in% project_ids)
      }
    }
    
    # Si hay filtro de evento
    if (length(eventos) > 0 && !all(is.na(eventos))) {
      if (!("TODOS" %in% eventos) && length(eventos) == 1) {
        stats_filtrado <- stats_filtrado %>% dplyr::filter(subproject_name %in% eventos)
      }
    }
    
    # Si no quedaron datos, usar vista TODOS
    if (nrow(stats_filtrado) == 0) {
      stats_filtrado <- species_stats %>% 
        dplyr::filter(project_id == "TODOS" & subproject_name == "TODOS")
    }
    
    # Mapear clase a tipo
    stats_filtrado <- stats_filtrado %>%
      dplyr::mutate(
        Tipo = dplyr::case_when(
          class == "Aves" ~ "Ave",
          class == "Mammalia" ~ "Mamifero",
          TRUE ~ "Otro"
        )
      ) %>%
      dplyr::arrange(desc(eventos_independientes))
    
    # Crear tabla final
    return(data.frame(
      Ranking = seq_len(nrow(stats_filtrado)),
      Especie = stats_filtrado$sp_binomial,
      "Numero imagenes" = stats_filtrado$total_imagenes,
      "Registros independientes" = stats_filtrado$eventos_independientes,
      Tipo = stats_filtrado$Tipo,
      stringsAsFactors = FALSE,
      check.names = FALSE
    ))
  }
  
  # RUTA TRADICIONAL: Procesar datos en vivo (fallback)
  # Validar datos
  if (is.null(subset) || nrow(subset) == 0) {
    return(data.frame(
      Ranking = integer(0),
      Especie = character(0),
      "Numero imagenes" = integer(0),
      "Registros independientes" = integer(0),
      Tipo = character(0),
      stringsAsFactors = FALSE,
      check.names = FALSE
    ))
  }
  
  # Contar imágenes totales por especie (sin filtrar)
  imagenes_totales <- subset %>%
    dplyr::group_by(sp_binomial) %>%
    dplyr::summarise(total_imagenes = n(), .groups = 'drop')
  
  # Aplicar filtro de duplicados para obtener eventos independientes
  subset_filtrado <- tryCatch({
    suppressMessages(
      remove_duplicates(subset, interval = interval, unit = unit)
    )
  }, error = function(e) {
    # Si falla el filtro, usar datos originales
    warning(paste("Error aplicando remove_duplicates:", e$message))
    subset
  })
  
  # Agrupar por especie y clase, contar eventos independientes
  tabla_especies <- subset_filtrado %>%
    dplyr::group_by(sp_binomial, class) %>%
    dplyr::summarise(eventos = n(), .groups = 'drop') %>%
    dplyr::left_join(imagenes_totales, by = "sp_binomial") %>%
    dplyr::arrange(desc(eventos))
  
  # Mapear clase a tipo simplificado (Ave/Mamífero/Otro)
  tabla_especies <- tabla_especies %>%
    dplyr::mutate(
      Tipo = dplyr::case_when(
        class == "Aves" ~ "Ave",
        class == "Mammalia" ~ "Mamifero",  # Sin tilde para evitar problemas de codificación
        TRUE ~ "Otro"
      )
    )
  
  # Crear tabla final con ranking
  tabla_final <- data.frame(
    Ranking = seq_len(nrow(tabla_especies)),
    Especie = tabla_especies$sp_binomial,
    "Numero imagenes" = tabla_especies$total_imagenes,
    "Registros independientes" = tabla_especies$eventos,
    Tipo = tabla_especies$Tipo,
    stringsAsFactors = FALSE,
    check.names = FALSE
  )
  
  return(tabla_final)
} # Función para generar tabla de ranking de especies (eventos independientes)

# ===============================================================================
# FUNCIÓN DE GRÁFICO DE OCUPACIÓN
# ===============================================================================

makeOccupancyGraph <- function(subset, top_n = 15, interval = 30, unit = "minutes", occupancy_stats = NULL) {
  # Genera gráfico mejorado de ocupación de especies con métricas adicionales
  # 
  # VERSIÓN MEJORADA 2.0: Inspirada en análisis de ocupación con unmarked,
  # incorpora métricas adicionales de frecuencia y distribución espacial.
  # 
  # Calcula y visualiza:
  #   1. Ocupación naive: proporción de sitios donde fue detectada la especie
  #   2. Frecuencia de detección: eventos promedio por sitio ocupado
  #   3. Distribución espacial: número de sitios con presencia
  # 
  # El gráfico muestra barras con ocupación, coloreadas por frecuencia de detección,
  # permitiendo identificar especies ampliamente distribuidas vs concentradas.
  # 
  # Basado en:
  #   - MacKenzie et al. (2002): Estimating site occupancy rates
  #   - Mejoras conceptuales de análisis con historias de detección
  # 
  # Parámetros:
  #   subset: DataFrame con registros de imágenes que debe contener:
  #           - deployment_name: identificador del sitio/cámara
  #           - sp_binomial: nombre científico de la especie
  #           - class: clase taxonómica (Aves, Mammalia, etc.)
  #           - photo_datetime: timestamp de captura
  #   top_n: Número de especies a visualizar (default: 15)
  #   interval: Intervalo temporal para eliminar duplicados (default: 30)
  #   unit: Unidad de tiempo para el intervalo (default: 'minutes')
  # 
  # Retorna:
  #   ggplot: Gráfico de barras con ocupación, frecuencia y clasificación taxonómica
  
  library(dplyr)
  library(ggplot2)
  
  # RUTA OPTIMIZADA: Usar datos pre-calculados si están disponibles
  if (!is.null(occupancy_stats) && nrow(occupancy_stats) > 0) {
    # Filtrar occupancy_stats según proyecto/evento del subset
    project_names <- unique(subset$project_short_name[!is.na(subset$project_short_name)])
    eventos <- unique(subset$subproject_name[!is.na(subset$subproject_name)])
    
    stats_filtrado <- occupancy_stats
    
    # Filtro por PROYECTO (usando project_name)
    if (length(project_names) > 0 && !all(is.na(project_names))) {
      if (length(project_names) == 1 && project_names[1] != "TODOS") {
        if ("project_name" %in% names(stats_filtrado)) {
          stats_filtrado <- stats_filtrado %>% dplyr::filter(project_name %in% project_names)
        }
      }
    }
    
    # Filtro por EVENTO
    if (length(eventos) > 0 && !all(is.na(eventos))) {
      if (length(eventos) == 1 && eventos[1] != "TODOS") {
        if ("subproject_name" %in% names(stats_filtrado)) {
          stats_filtrado <- stats_filtrado %>% dplyr::filter(subproject_name == eventos[1])
        }
      }
    }
    
    # Fallback: vista global si no hay datos
    if (nrow(stats_filtrado) == 0) {
      if ("project_id" %in% names(occupancy_stats) && "subproject_name" %in% names(occupancy_stats)) {
        stats_filtrado <- occupancy_stats %>% 
          dplyr::filter(project_id == "TODOS" & subproject_name == "TODOS")
      } else {
        stats_filtrado <- occupancy_stats
      }
    }
    
    # Ordenar por eventos independientes y tomar top_n
    ocupacion_especies <- stats_filtrado %>%
      dplyr::arrange(desc(eventos_independientes)) %>%
      dplyr::slice_head(n = top_n) %>%
      dplyr::mutate(
        tipo = dplyr::case_when(
          grepl("Aves", sp_binomial, ignore.case = TRUE) ~ "Ave",
          grepl("Mammalia|Mamifero", sp_binomial, ignore.case = TRUE) ~ "Mamífero",
          TRUE ~ "Otro"
        )
      )
    
    # Reordenar factor
    ocupacion_especies$sp_binomial <- factor(
      ocupacion_especies$sp_binomial,
      levels = ocupacion_especies$sp_binomial[order(ocupacion_especies$ocupacion_naive)]
    )
    
    # Crear gráfico
    p <- ggplot(ocupacion_especies, aes(x = ocupacion_naive, y = sp_binomial, fill = tipo)) +
      geom_col(width = 0.7) +
      scale_fill_manual(
        values = c("Ave" = "#E69F00", "Mamífero" = "#56B4E9", "Otro" = "#999999"),
        name = "Tipo"
      ) +
      scale_x_continuous(
        labels = scales::percent_format(),
        expand = c(0, 0),
        limits = c(0, max(ocupacion_especies$ocupacion_naive, na.rm = TRUE) * 1.1)
      ) +
      labs(
        title = "Ocupación Naive por Especie",
        subtitle = paste("Top", top_n, "especies más detectadas"),
        x = "Proporción de sitios con detecciones",
        y = NULL,
        caption = "Ocupación naive = (# sitios con presencia) / (# sitios totales)"
      ) +
      theme_minimal(base_size = 12) +
      theme(
        plot.title = element_text(face = "bold", hjust = 0),
        plot.subtitle = element_text(color = "gray40", hjust = 0),
        plot.caption = element_text(color = "gray50", size = 9, hjust = 0),
        axis.text.y = element_text(face = "italic", size = 10),
        panel.grid.major.y = element_blank(),
        panel.grid.minor = element_blank(),
        legend.position = "top"
      )
    
    return(p)
  }
  
  # RUTA TRADICIONAL: Procesamiento en vivo (fallback)
  # Validar datos
  if (is.null(subset) || nrow(subset) == 0) {
    return(ggplot() + theme_void() +
             annotate("text", x = 0.5, y = 0.5, 
                      label = "Sin datos para calcular ocupación", size = 5))
  }
  
  # Verificar columnas requeridas
  required_cols <- c("deployment_name", "sp_binomial")
  if (!all(required_cols %in% names(subset))) {
    return(ggplot() + theme_void() +
             annotate("text", x = 0.5, y = 0.5, 
                      label = "Faltan columnas requeridas:\ndeployment_name, sp_binomial", 
                      size = 5))
  }
  
  # Filtrar registros con especie identificada
  datos_validos <- subset %>%
    filter(!is.na(sp_binomial), sp_binomial != "", sp_binomial != "NA")
  
  if (nrow(datos_validos) == 0) {
    return(ggplot() + theme_void() +
             annotate("text", x = 0.5, y = 0.5, 
                      label = "Sin especies identificadas", size = 5))
  }
  
  # Aplicar filtro de duplicados para obtener eventos independientes
  datos_filtrados <- tryCatch({
    suppressMessages(
      remove_duplicates(datos_validos, interval = interval, unit = unit)
    )
  }, error = function(e) {
    # Si falla el filtro, usar datos originales
    warning(paste("Error aplicando remove_duplicates en ocupación:", e$message))
    datos_validos
  })
  
  # Calcular número total de sitios únicos
  total_sitios <- datos_filtrados %>%
    summarise(n_sitios = n_distinct(deployment_name)) %>%
    pull(n_sitios)
  
  if (total_sitios == 0) {
    return(ggplot() + theme_void() +
             annotate("text", x = 0.5, y = 0.5, 
                      label = "Sin sitios de muestreo", size = 5))
  }
  
  # Calcular ocupación naive por especie usando eventos independientes
  ocupacion_especies <- datos_filtrados %>%
    group_by(sp_binomial) %>%
    summarise(
      # Sitios donde la especie fue detectada
      sitios_ocupados = n_distinct(deployment_name),
      # Total de eventos independientes (para ordenar por abundancia)
      n_detecciones = n(),
      # Clase taxonómica (tomar la primera si hay inconsistencias)
      clase = if("class" %in% names(datos_filtrados)) first(class) else "Desconocido",
      .groups = 'drop'
    ) %>%
    mutate(
      # Proporción de sitios ocupados (0-1)
      ocupacion_naive = sitios_ocupados / total_sitios,
      # Porcentaje de ocupación (0-100)
      ocupacion_pct = round(ocupacion_naive * 100, 1),
      # Frecuencia de detección: eventos promedio por sitio ocupado
      # Métrica inspirada en análisis de historias de detección
      frecuencia_deteccion = round(n_detecciones / sitios_ocupados, 1)
    ) %>%
    # Ordenar por número de detecciones (especies más comunes primero)
    arrange(desc(n_detecciones)) %>%
    # Seleccionar top N especies
    head(top_n)
  
  # Mapear clase a tipo simplificado
  ocupacion_especies <- ocupacion_especies %>%
    mutate(
      tipo = case_when(
        clase == "Aves" ~ "Ave",
        clase == "Mammalia" ~ "Mamífero",
        TRUE ~ "Otro"
      )
    )
  
  # Reordenar factor por ocupación para gráfico
  ocupacion_especies$sp_binomial <- factor(
    ocupacion_especies$sp_binomial,
    levels = ocupacion_especies$sp_binomial[order(ocupacion_especies$ocupacion_naive)]
  )
  
  # Crear gráfico de barras horizontales con gradiente de frecuencia
  # Concepto inspirado en análisis de ocupación con unmarked:
  # - Largo de barra = ocupación espacial (% sitios)
  # - Color = intensidad de uso (frecuencia de detección por sitio)
  p <- ggplot(ocupacion_especies, aes(x = ocupacion_naive, y = sp_binomial)) +
    # Barras coloreadas por frecuencia de detección
    geom_col(aes(fill = frecuencia_deteccion), width = 0.75, alpha = 0.95) +
    # Etiquetas con ocupación %
    geom_text(
      aes(label = paste0(ocupacion_pct, "%")), 
      hjust = -0.15, 
      size = 3.2, 
      fontface = "bold", 
      color = "#2c3e50"
    ) +
    # Gradiente de color: azul claro (baja frecuencia) a azul oscuro (alta frecuencia)
    scale_fill_gradient(
      low = "#a8dadc",      # Azul claro para especies ocasionales
      high = "#1d3557",     # Azul oscuro para especies frecuentes
      name = "Frecuencia\n(eventos/sitio)",
      breaks = pretty,
      guide = guide_colorbar(
        barwidth = 1.5,
        barheight = 8,
        title.position = "top",
        title.hjust = 0.5
      )
    ) +
    # Escala X de 0 a 1 con extensión para etiquetas
    scale_x_continuous(
      limits = c(0, 1.15),
      breaks = seq(0, 1, 0.2),
      labels = scales::percent_format(accuracy = 1),
      expand = c(0, 0)
    ) +
    # Etiquetas y título
    labs(
      title = paste0("Ocupación y Frecuencia de Especies (Top ", top_n, ")"),
      subtitle = paste0(
        "Largo de barra = % sitios ocupados  •  Color = frecuencia de detección\n",
        "Total de sitios: ", total_sitios, "  •  Método: ocupación naive + eventos independientes"
      ),
      x = "Proporción de Sitios Ocupados",
      y = NULL,
      caption = "Frecuencia = eventos independientes / sitios ocupados"
    ) +
    # Tema moderno
    theme_minimal(base_size = 12) +
    theme(
      plot.title = element_text(face = "bold", size = 14, hjust = 0, color = "#1a5490"),
      plot.subtitle = element_text(size = 10, color = "#7f8c8d", hjust = 0, lineheight = 1.3),
      plot.caption = element_text(size = 8, color = "#95a5a6", hjust = 0, margin = margin(t = 10)),
      axis.text.y = element_text(face = "italic", size = 10, color = "#2c3e50"),
      axis.text.x = element_text(size = 10, color = "#34495e"),
      axis.title.x = element_text(size = 11, face = "bold", color = "#2c3e50", margin = margin(t = 10)),
      legend.position = "right",
      legend.title = element_text(face = "bold", size = 9),
      legend.text = element_text(size = 8),
      legend.margin = margin(l = 10),
      panel.grid.major.y = element_blank(),
      panel.grid.minor = element_blank(),
      panel.grid.major.x = element_line(color = "#ecf0f1", linewidth = 0.5),
      plot.background = element_rect(fill = "white", color = NA),
      panel.background = element_rect(fill = "white", color = NA),
      plot.margin = margin(15, 15, 15, 15)
    )
  
  return(p)
  
} # Función para crear gráfico de ocupación naive por especie


makeMapLeaflet <- function(data, selected_sites, nprojects, bounds, input_site) {
  #' Crea mapa interactivo de sitios de muestreo con popups informativos
  #'
  #' Genera mapa Leaflet con marcadores diferenciados para sitios seleccionados
  #' y no seleccionados. Incluye popups con información detallada de cada sitio.
  #'
  #' @param data DataFrame con información de sitios (requiere lat, lon, site_name, 
  #'             n, effort, ospTot, ospMamiferos, ospAves, departamento)
  #' @param selected_sites DataFrame con sitios seleccionados para resaltar
  #' @param nprojects Número total de proyectos (heredado, no usado)
  #' @param bounds Lista con límites del mapa (lon/lat mín/máx)
  #' @param input_site Nombre del proyecto/sitio seleccionado
  #'
  #' @return leaflet Mapa interactivo con marcadores de sitios y popups
  #'
  #' @details
  #' Lógica de colores:
  #'   - Proyectos consolidados ("Red OTUS - "): marcadores rojos
  #'   - Proyectos individuales: marcadores azules
  #'   - Sitios no seleccionados: marcadores negros pequeños
  #'
  #' Información en popups:
  #'   - Nombre del sitio
  #'   - Ubicación (departamento)
  #'   - Total de imágenes capturadas
  #'   - Esfuerzo de muestreo (días-cámara)
  #'   - Riqueza de especies (total, mamíferos, aves)
  #'
    
    # Filtrar datos con coordenadas válidas (eliminar valores NA o cero)
    data_valid <- data[!is.na(data$lat) & !is.na(data$lon) & 
                       data$lat != 0 & data$lon != 0, ]
    
    if (nrow(data_valid) == 0) {
        # Si no hay coordenadas válidas, crear mapa vacío centrado en los bounds
        return(leaflet() %>% 
               addTiles() %>% 
               fitBounds(lng1 = bounds$lon[1], lat1 = bounds$lat[2], 
                        lng2 = bounds$lon[3], lat2 = bounds$lat[4]) %>%
               addScaleBar("bottomleft") %>%
               addControl(html = "<div style='background-color: white; padding: 10px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.2);'>
                              <strong>⚠️ No hay ubicaciones con coordenadas válidas</strong></div>",
                         position = "topright"))
    }
    
    # Configurar colores y tamaños base para todos los marcadores
    # Paleta de azules coherente con el diseño del dashboard
    color <- rep("#7fa3c4", nrow(data_valid))  # Color por defecto: azul grisáceo claro
    size <- rep(6, nrow(data_valid))            # Tamaño por defecto: 6
    
    # Identificar sitios seleccionados con coordenadas válidas
    selected_rows <- which(data_valid$site_name %in% selected_sites$site_name)

    # Aplicar lógica de colores según tipo de proyecto (paleta de azules)
    if (grepl("^Red OTUS - ", input_site)) {
        # Para proyectos consolidados: azul oscuro institucional
        color[selected_rows] <- "#1a5490"  # Azul secundario del dashboard
        size[selected_rows] <- 10
    } else {
        # Para proyectos específicos: azul primario vibrante
        color[selected_rows] <- "#0397d6"  # Azul primario del dashboard
        size[selected_rows] <- 10
    }
    
    # ============================================================================
    # NUEVO: Generar popups informativos con HTML personalizado
    # ============================================================================
    
    # Generar popups para todos los sitios usando loop
    popups <- character(nrow(data_valid))
    
    for (i in 1:nrow(data_valid)) {
        # Extraer datos del sitio actual
        site_name <- ifelse(is.na(data_valid$site_name[i]), "Sin nombre", as.character(data_valid$site_name[i]))
        departamento <- ifelse(is.na(data_valid$departamento[i]), "No especificado", as.character(data_valid$departamento[i]))
        n_images <- ifelse(is.na(data_valid$n[i]), 0, as.numeric(data_valid$n[i]))
        effort <- ifelse(is.na(data_valid$effort[i]), 0, as.numeric(data_valid$effort[i]))
        osp_total <- ifelse(is.na(data_valid$ospTot[i]), 0, as.numeric(data_valid$ospTot[i]))
        osp_mamiferos <- ifelse(is.na(data_valid$ospMamiferos[i]), 0, as.numeric(data_valid$ospMamiferos[i]))
        osp_aves <- ifelse(is.na(data_valid$ospAves[i]), 0, as.numeric(data_valid$ospAves[i]))
        lat_value <- as.numeric(data_valid$lat[i])
        lon_value <- as.numeric(data_valid$lon[i])
        
        # Calcular tasa de captura (imágenes por día-cámara)
        capture_rate <- ifelse(effort > 0, round(n_images / effort, 2), 0)
        
        # Construir HTML del popup con estilo mejorado
        popups[i] <- paste0(
            "<div style='font-family: Arial, sans-serif; min-width: 250px;'>",
            
            # Encabezado con nombre del sitio
            "<div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); ",
            "color: white; padding: 10px 12px; margin: -10px -10px 10px -10px; ",
            "border-radius: 4px 4px 0 0; font-weight: bold; font-size: 14px;'>",
            "📍 ", site_name,
            "</div>",
            
            # Ubicación
            "<div style='margin-bottom: 8px; color: #555; font-size: 12px;'>",
            "<strong>📌 Ubicación:</strong> ", departamento,
            "</div>",
            
            # Separador
            "<hr style='margin: 10px 0; border: none; border-top: 1px solid #e0e0e0;'>",
            
            # Sección: Esfuerzo de muestreo
            "<div style='margin-bottom: 10px;'>",
            "<div style='color: #0397d6; font-weight: bold; margin-bottom: 5px; font-size: 11px;'>",
            "🎥 ESFUERZO DE MUESTREO",
            "</div>",
            "<div style='display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px;'>",
            "<span style='color: #666;'>Total de imágenes:</span>",
            "<span style='font-weight: bold; color: #2c3e50;'>", format(n_images, big.mark = ","), "</span>",
            "</div>",
            "<div style='display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px;'>",
            "<span style='color: #666;'>Días-cámara:</span>",
            "<span style='font-weight: bold; color: #2c3e50;'>", format(effort, big.mark = ","), "</span>",
            "</div>",
            "<div style='display: flex; justify-content: space-between; font-size: 12px;'>",
            "<span style='color: #666;'>Tasa de captura:</span>",
            "<span style='font-weight: bold; color: #27ae60;'>", capture_rate, " img/día</span>",
            "</div>",
            "</div>",
            
            # Separador
            "<hr style='margin: 10px 0; border: none; border-top: 1px solid #e0e0e0;'>",
            
            # Sección: Biodiversidad
            "<div style='margin-bottom: 5px;'>",
            "<div style='color: #27ae60; font-weight: bold; margin-bottom: 5px; font-size: 11px;'>",
            "🦎 BIODIVERSIDAD REGISTRADA",
            "</div>",
            "<div style='display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px;'>",
            "<span style='color: #666;'>🔢 Total de especies:</span>",
            "<span style='font-weight: bold; color: #2c3e50;'>", osp_total, "</span>",
            "</div>",
            "<div style='display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px;'>",
            "<span style='color: #666;'>🐾 Mamíferos:</span>",
            "<span style='font-weight: bold; color: #e74c3c;'>", osp_mamiferos, "</span>",
            "</div>",
            "<div style='display: flex; justify-content: space-between; font-size: 12px;'>",
            "<span style='color: #666;'>🦜 Aves:</span>",
            "<span style='font-weight: bold; color: #3498db;'>", osp_aves, "</span>",
            "</div>",
            "</div>",
            
            # Coordenadas (footer opcional)
            "<div style='margin-top: 10px; padding-top: 8px; border-top: 1px solid #e0e0e0; ",
            "font-size: 10px; color: #999; text-align: center;'>",
            "Lat: ", round(lat_value, 5), " | Lon: ", round(lon_value, 5),
            "</div>",
            
            "</div>"
        )
    }
    
    # ============================================================================
    # Crear el mapa interactivo con marcadores y popups
    # ============================================================================
    
    map <- leaflet(data_valid) %>% 
        fitBounds(lng1 = bounds$lon[1], lat1 = bounds$lat[2], 
                  lng2 = bounds$lon[3], lat2 = bounds$lat[4]) %>% 
        addTiles() %>% 
        addCircleMarkers(
            ~lon, ~lat, 
            color = color, 
            radius = size,
            fillOpacity = 0.7,
            weight = 2,
            popup = popups,  # Agregar popups
            label = ~site_name,  # Mostrar nombre del sitio al pasar el cursor
            labelOptions = labelOptions(
                style = list(
                    "font-weight" = "bold",
                    "font-size" = "12px",
                    "padding" = "3px 8px",
                    "background-color" = "rgba(255, 255, 255, 0.9)",
                    "border" = "1px solid #ccc",
                    "border-radius" = "4px"
                ),
                direction = "top"
            )
        ) %>% 
        addScaleBar("bottomleft")
    
    return(map)
} # Función para crear mapas interactivos con popups informativos

# ===============================================================================
# FUNCIÓN DE CURVA DE ACUMULACIÓN DE ESPECIES
# ===============================================================================

makeAccumulationCurve <- function(data, smooth_curve = TRUE, accumulation_curve = NULL) {
  #' Genera curva de acumulación de especies
  #'
  #' Visualiza cómo se acumulan especies nuevas a lo largo del tiempo de muestreo.
  #' Aplica suavizado semilogarítmico según Ugland et al. (2003).
  #'
  #' @param data DataFrame con columnas photo_datetime y sp_binomial
  #' @param smooth_curve Boolean para aplicar suavizado (default: TRUE)
  #' @param accumulation_curve DataFrame pre-calculado (opcional)
  #'
  #' @return ggplot Curva de acumulación con modelo semilogarítmico
  #'
  #' @details
  #' Metodología:
  #'   - Modelo: S = a * ln(t+1) + b (Ugland et al. 2003)
  #'   - Ordenamiento cronológico de detecciones
  #'   - Identificación de primeros registros por especie
  #'   - Ajuste de curva semilogarítmica
  #'
  #' @references
  #' Ugland, K.I., Gray, J.S., Ellingsen, K.E. (2003).
  #' The species-accumulation curve and estimation of species richness.
  #' Journal of Animal Ecology, 72(5), 888-897.
  #'
  
  # Validación de datos
  if (is.null(data) || nrow(data) == 0) {
    return(ggplot() + theme_void() + 
           annotate("text", x = 0.5, y = 0.5, label = "Sin datos para generar curva", size = 5))
  }
  
  # RUTA OPTIMIZADA: Usar datos pre-calculados si están disponibles
  if (!is.null(accumulation_curve) && nrow(accumulation_curve) > 0) {
    # Filtrar accumulation_curve según proyecto/evento del data
    project_names <- unique(data$project_short_name[!is.na(data$project_short_name)])
    eventos <- unique(data$subproject_name[!is.na(data$subproject_name)])
    
    curve_data <- accumulation_curve
    
    # Filtro por PROYECTO
    if (length(project_names) > 0 && !all(is.na(project_names))) {
      if (length(project_names) == 1 && project_names[1] != "TODOS") {
        if ("project_name" %in% names(curve_data)) {
          curve_data <- curve_data %>% dplyr::filter(project_name %in% project_names)
        }
      }
    }
    
    # Filtro por EVENTO
    if (length(eventos) > 0 && !all(is.na(eventos))) {
      if (length(eventos) == 1 && eventos[1] != "TODOS") {
        if ("subproject_name" %in% names(curve_data)) {
          curve_data <- curve_data %>% dplyr::filter(subproject_name == eventos[1])
        }
      }
    }
    
    # Fallback: vista global
    if (nrow(curve_data) == 0) {
      if ("project_id" %in% names(accumulation_curve) && "subproject_name" %in% names(accumulation_curve)) {
        curve_data <- accumulation_curve %>% 
          dplyr::filter(project_id == "TODOS" & subproject_name == "TODOS")
      } else {
        curve_data <- accumulation_curve
      }
    }
    
    # Convertir date a Date si es string
    if (is.character(curve_data$date)) {
      curve_data$date <- as.Date(curve_data$date)
    }
    
    # Ordenar por fecha
    curve_data <- curve_data %>% dplyr::arrange(date)
    
    # Información estadística
    final_richness <- max(curve_data$especies_acumuladas, na.rm = TRUE)
    total_days <- nrow(curve_data)
    rate <- if (total_days > 0) final_richness / total_days else 0
    
    # Crear gráfico con datos pre-calculados
    p <- ggplot(curve_data, aes(x = date, y = especies_acumuladas)) +
      geom_ribbon(aes(ymin = 0, ymax = especies_acumuladas), alpha = 0.2, fill = "#3498db") +
      geom_line(linewidth = 2.5, color = "#2980b9", alpha = 0.95) +
      geom_point(size = 2.5, alpha = 0.5, color = "#2c3e50", shape = 16) +
      labs(
        title = "Curva de acumulación de especies",
        subtitle = paste0("Total: ", final_richness, " especies en ", total_days, " días (tasa: ", 
                         sprintf("%.2f", rate), " sp/día)"),
        x = "Fecha",
        y = "Riqueza de especies (S)"
      ) +
      theme_minimal(base_size = 12) +
      theme(
        plot.title = element_text(face = "bold", size = 13, hjust = 0),
        plot.subtitle = element_text(color = "gray50", size = 10, hjust = 0),
        panel.grid.minor = element_blank(),
        panel.grid.major = element_line(color = "gray90"),
        axis.title = element_text(face = "bold", size = 11),
        axis.text = element_text(size = 10),
        plot.margin = margin(15, 15, 15, 15)
      ) +
      scale_y_continuous(expand = expansion(mult = c(0, 0.1))) +
      scale_x_date(date_labels = "%b %Y", date_breaks = "2 months")
    
    return(p)
  }
  
  # RUTA TRADICIONAL: Procesamiento en vivo
  # Preparar datos temporales
  data <- data %>%
    mutate(
      timestamp = as.POSIXct(photo_datetime, format = "%Y-%m-%d %H:%M:%S"),
      date = as.Date(timestamp)
    ) %>%
    filter(!is.na(timestamp), !is.na(sp_binomial), sp_binomial != "")
  
  if (nrow(data) == 0) {
    return(ggplot() + theme_void() + 
           annotate("text", x = 0.5, y = 0.5, label = "No hay datos válidos", size = 5))
  }
  
  # Rango completo de fechas
  start_date <- min(data$date, na.rm = TRUE)
  end_date <- max(data$date, na.rm = TRUE)
  date_range <- seq.Date(start_date, end_date, by = "day")
  
  # Agrupar especies por día
  species_by_day <- data %>%
    group_by(date) %>%
    summarise(species = list(unique(sp_binomial[!is.na(sp_binomial)])), .groups = "drop")
  
  # Calcular acumulación día por día
  seen_species <- c()
  richness_discrete <- numeric(length(date_range))
  
  for (i in seq_along(date_range)) {
    current_date <- date_range[i]
    day_species <- species_by_day %>% 
      filter(date == current_date) %>% 
      pull(species)
    
    if (length(day_species) > 0) {
      seen_species <- unique(c(seen_species, unlist(day_species)))
    }
    richness_discrete[i] <- length(seen_species)
  }
  
  # Preparar datos para gráfico
  curve_data <- data.frame(
    date = date_range,
    richness = richness_discrete
  )
  
  # Crear gráfico base
  p <- ggplot(curve_data, aes(x = date, y = richness))
  
  # Aplicar suavizado semilogarítmico si está habilitado
  if (smooth_curve && length(richness_discrete) > 3) {
    tryCatch({
      # Convertir fechas a números para el ajuste
      days_numeric <- as.numeric(date_range - start_date)
      log_days <- log(days_numeric + 1)
      
      # Filtrar valores válidos
      valid_mask <- richness_discrete > 0
      if (sum(valid_mask) > 3) {
        # Ajuste semilogarítmico: S = a * ln(t + 1) + b
        model <- lm(richness_discrete[valid_mask] ~ log_days[valid_mask])
        a <- coef(model)[2]
        b <- coef(model)[1]
        
        # Generar curva suavizada
        days_smooth <- seq(0, max(days_numeric), length.out = length(date_range) * 3)
        log_days_smooth <- log(days_smooth + 1)
        richness_smooth <- pmax(a * log_days_smooth + b, 0)
        date_smooth <- start_date + days_smooth
        
        smooth_data <- data.frame(
          date = date_smooth,
          richness = richness_smooth
        )
        
        # Gráfico con curva suavizada - colores modernos
        p <- p + 
          geom_ribbon(data = smooth_data, aes(ymin = 0, ymax = richness), 
                     alpha = 0.2, fill = "#3498db") +
          geom_line(data = smooth_data, linewidth = 2.5, color = "#2980b9", alpha = 0.95) +
          geom_point(data = curve_data, size = 2.5, alpha = 0.5, color = "#2c3e50", shape = 16)
      } else {
        # Fallback a curva discreta
        p <- p + 
          geom_ribbon(aes(ymin = 0, ymax = richness), alpha = 0.2, fill = "#3498db") +
          geom_line(linewidth = 2, color = "#2980b9") +
          geom_point(size = 2.5, alpha = 0.5, color = "#2c3e50")
      }
    }, error = function(e) {
      # Si falla el suavizado, usar curva original
      p <<- p + 
        geom_ribbon(aes(ymin = 0, ymax = richness), alpha = 0.2, fill = "#3498db") +
        geom_line(linewidth = 2, color = "#2980b9") +
        geom_point(size = 2.5, alpha = 0.5, color = "#2c3e50")
    })
  } else {
    # Curva discreta sin suavizado
    p <- p + 
      geom_ribbon(aes(ymin = 0, ymax = richness), alpha = 0.2, fill = "#3498db") +
      geom_line(linewidth = 2, color = "#2980b9") +
      geom_point(size = 2.5, alpha = 0.5, color = "#2c3e50")
  }
  
  # Información estadística
  final_richness <- tail(richness_discrete, 1)
  total_days <- length(date_range)
  rate <- if (total_days > 0) final_richness / total_days else 0
  
  info_label <- sprintf("Total: %d especies\n%d días\nTasa: %.2f sp/día", 
                       final_richness, total_days, rate)
  
  # Aplicar tema moderno
  p <- p +
    labs(
      title = "Curva de acumulación de especies",
      subtitle = paste0("Total: ", final_richness, " especies en ", total_days, " días (tasa: ", 
                       sprintf("%.2f", rate), " sp/día)"),
      x = "Fecha",
      y = "Riqueza de especies (S)"
    ) +
    theme_minimal(base_size = 12) +
    theme(
      plot.title = element_text(size = 14, face = "bold", hjust = 0, color = "#2c3e50"),
      plot.subtitle = element_text(size = 11, hjust = 0, color = "#7f8c8d", margin = margin(b = 10)),
      axis.title = element_text(size = 11, face = "bold", color = "#2c3e50"),
      axis.text = element_text(size = 10, color = "#34495e"),
      panel.grid.major = element_line(color = "#ecf0f1", linewidth = 0.5),
      panel.grid.minor = element_blank(),
      panel.background = element_rect(fill = "white", color = NA),
      plot.background = element_rect(fill = "white", color = NA),
      plot.margin = margin(15, 15, 15, 15)
    ) +
    scale_y_continuous(expand = expansion(mult = c(0, 0.1))) +
    scale_x_date(date_breaks = "1 month", date_labels = "%b %Y")
  
  return(p)
} # Función para generar curva de acumulación de especies con suavizado semilog

# ===============================================================================
# FUNCIÓN DE PATRÓN DE ACTIVIDAD TEMPORAL
# ===============================================================================

makeActivityPattern <- function(data, top_n = 10, interval = 30, unit = "minutes", interactive = FALSE, activity_pattern = NULL) {
  # Genera gráfica de densidad de actividad temporal por especie
  # 
  # VERSIÓN OPTIMIZADA: Si se proporciona activity_pattern pre-calculado, usa esos datos.
  # 
  # Crea curvas de densidad que muestran los patrones circadianos de actividad
  # de las especies más fotografiadas basándose en eventos independientes
  # (sin duplicados temporales). Usa Kernel Density Estimation (KDE) para
  # suavizar los datos y mostrar probabilidad de actividad por hora del día.
  # 
  # Parámetros:
  #   data: DataFrame con columnas 'photo_datetime' y 'sp_binomial'
  #   top_n: Número de especies más abundantes a incluir (por defecto 10)
  #   interval: Intervalo temporal para eliminar duplicados (default: 30)
  #   unit: Unidad de tiempo para el intervalo (default: 'minutes')
  #   interactive: Si TRUE, retorna gráfico plotly interactivo (default: FALSE)
  # 
  # Retorna:
  #   ggplot o plotly: Gráfico con curvas de densidad de actividad por hora
  
  # Validación de datos
  if (is.null(data) || nrow(data) == 0) {
    return(ggplot() + theme_void() + 
           annotate("text", x = 0.5, y = 0.5, label = "Sin datos para generar patrón", size = 5))
  }
  
  # RUTA OPTIMIZADA: Usar datos pre-calculados si están disponibles
  if (!is.null(activity_pattern) && nrow(activity_pattern) > 0) {
    # Filtrar activity_pattern según proyecto/evento del data
    project_names <- unique(data$project_short_name[!is.na(data$project_short_name)])
    eventos <- unique(data$subproject_name[!is.na(data$subproject_name)])
    
    pattern_data <- activity_pattern
    
    # Filtro por PROYECTO
    if (length(project_names) > 0 && !all(is.na(project_names))) {
      if (length(project_names) == 1 && project_names[1] != "TODOS") {
        if ("project_name" %in% names(pattern_data)) {
          pattern_data <- pattern_data %>% dplyr::filter(project_name %in% project_names)
        }
      }
    }
    
    # Filtro por EVENTO
    if (length(eventos) > 0 && !all(is.na(eventos))) {
      if (length(eventos) == 1 && eventos[1] != "TODOS") {
        if ("subproject_name" %in% names(pattern_data)) {
          pattern_data <- pattern_data %>% dplyr::filter(subproject_name == eventos[1])
        }
      }
    }
    
    # Fallback: vista global
    if (nrow(pattern_data) == 0) {
      if ("project_id" %in% names(activity_pattern) && "subproject_name" %in% names(activity_pattern)) {
        pattern_data <- activity_pattern %>% 
          dplyr::filter(project_id == "TODOS" & subproject_name == "TODOS")
      } else {
        pattern_data <- activity_pattern
      }
    }
    
    # Identificar top N especies por total de eventos
    top_species_data <- pattern_data %>%
      dplyr::group_by(sp_binomial) %>%
      dplyr::summarise(total = sum(count, na.rm = TRUE), .groups = 'drop') %>%
      dplyr::arrange(desc(total)) %>%
      dplyr::slice_head(n = top_n)
    
    # Filtrar pattern_data con top especies
    pattern_filtered <- pattern_data %>%
      dplyr::filter(sp_binomial %in% top_species_data$sp_binomial)
    
    if (nrow(pattern_filtered) == 0) {
      return(ggplot() + theme_void() + 
             annotate("text", x = 0.5, y = 0.5, label = "No hay datos de actividad", size = 5))
    }
    
    # Crear gráfico con datos pre-calculados
    colors_pal <- c("#E74C3C", "#3498DB", "#2ECC71", "#F39C12", "#9B59B6",
                    "#1ABC9C", "#E67E22", "#34495E", "#16A085", "#D35400")
    
    # Si modo interactivo, usar plotly
    if (interactive) {
      library(plotly)
      
      species_list <- unique(pattern_filtered$sp_binomial)
      color_map <- setNames(colors_pal[seq_along(species_list)], species_list)
      
      p_interactive <- plot_ly()
      
      for (sp in species_list) {
        sp_data <- pattern_filtered %>% dplyr::filter(sp_binomial == sp)
        
        p_interactive <- p_interactive %>%
          add_trace(
            data = sp_data,
            x = ~hour,
            y = ~count,
            type = "scatter",
            mode = "lines+markers",
            fill = "tozeroy",
            fillcolor = paste0(color_map[sp], "33"),
            line = list(color = color_map[sp], width = 2.5),
            marker = list(size = 4, color = color_map[sp]),
            name = sp,
            hovertemplate = paste0(
              "<b>", sp, "</b><br>",
              "Hora: %{x}h<br>",
              "Eventos: %{y}<extra></extra>"
            )
          )
      }
      
      p_interactive <- p_interactive %>%
        layout(
          title = list(
            text = paste0("<b>Patrón de actividad por hora del día</b><br>",
                         "<sub>Top ", length(species_list), " especies más detectadas</sub>"),
            font = list(size = 14, color = "#2c3e50")
          ),
          xaxis = list(
            title = "Hora del día (0-24)",
            range = c(0, 24),
            dtick = 3,
            gridcolor = "#ecf0f1",
            titlefont = list(size = 11, color = "#2c3e50")
          ),
          yaxis = list(
            title = "Eventos independientes",
            gridcolor = "#ecf0f1",
            titlefont = list(size = 11, color = "#2c3e50"),
            rangemode = "tozero"
          ),
          plot_bgcolor = "white",
          paper_bgcolor = "white",
          margin = list(l = 60, r = 140, t = 60, b = 70),
          hovermode = "closest",
          legend = list(
            orientation = "v",
            x = 1.01,
            y = 1,
            xanchor = "left",
            yanchor = "top",
            font = list(size = 9),
            bgcolor = "rgba(255,255,255,0.8)",
            bordercolor = "#ecf0f1",
            borderwidth = 1
          ),
          autosize = TRUE
        ) %>%
        config(
          displayModeBar = TRUE, 
          displaylogo = FALSE,
          modeBarButtonsToRemove = c("pan2d", "lasso2d", "select2d", "autoScale2d"),
          responsive = TRUE
        )
      
      return(p_interactive)
    } else {
      # Gráfico estático con ggplot
      p <- ggplot(pattern_filtered, aes(x = hour, y = count, color = sp_binomial, fill = sp_binomial)) +
        geom_area(alpha = 0.2, position = "identity") +
        geom_line(linewidth = 1.5) +
        scale_color_manual(values = colors_pal) +
        scale_fill_manual(values = colors_pal) +
        scale_x_continuous(
          breaks = seq(0, 24, 3),
          limits = c(0, 24),
          expand = c(0.01, 0)
        ) +
        scale_y_continuous(expand = expansion(mult = c(0, 0.1))) +
        labs(
          title = "Patrón de actividad circadiana por especie",
          subtitle = paste("Top", length(species_list), "especies más detectadas"),
          x = "Hora del día (0-24)",
          y = "Eventos independientes",
          color = "Especie",
          fill = "Especie"
        ) +
        theme_minimal(base_size = 12) +
        theme(
          plot.title = element_text(size = 14, face = "bold", hjust = 0, color = "#2c3e50"),
          plot.subtitle = element_text(size = 11, hjust = 0, color = "#7f8c8d", margin = margin(b = 10)),
          axis.title = element_text(size = 11, face = "bold", color = "#2c3e50"),
          axis.text = element_text(size = 10, color = "#34495e"),
          legend.position = "right",
          legend.title = element_text(face = "bold", size = 10),
          legend.text = element_text(face = "italic", size = 9),
          panel.grid.major = element_line(color = "#ecf0f1", linewidth = 0.5),
          panel.grid.minor = element_blank(),
          panel.background = element_rect(fill = "white", color = NA),
          plot.background = element_rect(fill = "white", color = NA),
          plot.margin = margin(15, 10, 15, 15)
        )
      
      return(p)
    }
  }
  
  # RUTA TRADICIONAL: Procesamiento en vivo (fallback)
  # Preparar datos temporales
  data <- data %>%
    mutate(
      timestamp = as.POSIXct(photo_datetime, format = "%Y-%m-%d %H:%M:%S"),
      hour = lubridate::hour(timestamp)
    ) %>%
    filter(!is.na(timestamp), !is.na(sp_binomial), sp_binomial != "", !is.na(hour))
  
  if (nrow(data) == 0) {
    return(ggplot() + theme_void() + 
           annotate("text", x = 0.5, y = 0.5, label = "No hay datos válidos de hora", size = 5))
  }
  
  # Aplicar filtro de duplicados para obtener eventos independientes
  data_filtrado <- tryCatch({
    suppressMessages(
      remove_duplicates(data, interval = interval, unit = unit)
    )
  }, error = function(e) {
    # Si falla el filtro, usar datos originales
    warning(paste("Error aplicando remove_duplicates en actividad:", e$message))
    data
  })
  
  # Seleccionar las especies más abundantes basado en eventos independientes
  top_species <- data_filtrado %>%
    count(sp_binomial, sort = TRUE) %>%
    head(top_n) %>%
    pull(sp_binomial)
  
  if (length(top_species) == 0) {
    return(ggplot() + theme_void() + 
           annotate("text", x = 0.5, y = 0.5, label = "No hay especies suficientes", size = 5))
  }
  
  # Filtrar solo las especies seleccionadas (usar datos filtrados)
  data_filtered <- data_filtrado %>%
    filter(sp_binomial %in% top_species)
  
  # Crear gráfico base
  p <- ggplot(data_filtered, aes(x = hour, color = sp_binomial, fill = sp_binomial))
  
  # Intentar aplicar densidad kernel
  tryCatch({
    # Paleta de colores vibrante
    colors_pal <- c("#E74C3C", "#3498DB", "#2ECC71", "#F39C12", "#9B59B6",
                    "#1ABC9C", "#E67E22", "#34495E", "#16A085", "#D35400")
    
    # Usar geom_density para crear curvas suavizadas
    p <- p + 
      geom_density(alpha = 0.2, linewidth = 1.5, adjust = 1.5) +
      scale_color_manual(values = colors_pal) +
      scale_fill_manual(values = colors_pal) +
      scale_x_continuous(
        breaks = seq(0, 24, 3),
        limits = c(0, 24),
        expand = c(0.01, 0)
      ) +
      scale_y_continuous(expand = expansion(mult = c(0, 0.1))) +
      labs(
        title = "Patrón de actividad circadiana por especie",
        subtitle = paste("Top", length(top_species), "especies más fotografiadas"),
        x = "Hora del día (0-24)",
        y = "Densidad de actividad",
        color = "Especie",
        fill = "Especie"
      ) +
      theme_minimal(base_size = 12) +
      theme(
        plot.title = element_text(size = 14, face = "bold", hjust = 0, color = "#2c3e50"),
        plot.subtitle = element_text(size = 11, hjust = 0, color = "#7f8c8d", margin = margin(b = 10)),
        axis.title = element_text(size = 11, face = "bold", color = "#2c3e50"),
        axis.text = element_text(size = 10, color = "#34495e"),
        legend.position = "right",
        legend.title = element_text(face = "bold", size = 10),
        legend.text = element_text(face = "italic", size = 9),
        panel.grid.major = element_line(color = "#ecf0f1", linewidth = 0.5),
        panel.grid.minor = element_blank(),
        panel.background = element_rect(fill = "white", color = NA),
        plot.background = element_rect(fill = "white", color = NA),
        plot.margin = margin(15, 10, 15, 15)
      )
    
    # Convertir a plotly si se solicita modo interactivo
    if (interactive) {
      library(plotly)
      
      # FILTRAR especies con menos de 3 observaciones ANTES de calcular densidades
      # Esto evita el warning: "Groups with fewer than two data points have been dropped"
      especies_validas <- data_filtered %>%
        group_by(sp_binomial) %>%
        summarise(n_obs = n(), .groups = 'drop') %>%
        filter(n_obs >= 3) %>%
        pull(sp_binomial)
      
      data_filtered <- data_filtered %>%
        filter(sp_binomial %in% especies_validas)
      
      # Calcular densidades manualmente para plotly (solo especies con >=3 obs)
      density_data <- data_filtered %>%
        group_by(sp_binomial) %>%
        group_modify(~ {
          # Ya sabemos que tiene >= 3 observaciones
          dens <- density(.x$hour, adjust = 1.5, from = 0, to = 24, n = 200)
          data.frame(hour = dens$x, density = dens$y)
        }) %>%
        ungroup()
      
      if (nrow(density_data) > 0) {
        # Asignar colores a especies
        species_list <- unique(density_data$sp_binomial)
        color_map <- setNames(colors_pal[seq_along(species_list)], species_list)
        
        # Crear plotly vacío (sin warnings sobre tipo de trace)
        p_interactive <- plot_ly(type = 'scatter', mode = 'lines')
        
        for (sp in species_list) {
          sp_data <- density_data %>% filter(sp_binomial == sp)
          
          # Especificar EXPLÍCITAMENTE type y mode para evitar mensajes
          p_interactive <- p_interactive %>%
            add_trace(
              data = sp_data,
              x = ~hour,
              y = ~density,
              type = 'scatter',      # Explícito
              mode = 'lines',        # Explícito
              fill = 'tozeroy',
              fillcolor = paste0(color_map[sp], "33"),
              line = list(color = color_map[sp], width = 2.5),
              name = sp,
              hovertemplate = paste0(
                "<b>", sp, "</b><br>",
                "Hora: %{x:.1f}h<br>",
                "Densidad: %{y:.3f}<extra></extra>"
              )
            )
        }
        
        p_interactive <- p_interactive %>%
          layout(
            title = list(
              text = paste0("<b>Patrón de actividad por hora del día</b><br>",
                           "<sub>Top ", length(top_species), " especies más fotografiadas</sub>"),
              font = list(size = 14, color = "#2c3e50")
            ),
            xaxis = list(
              title = "Hora del día (0-24)",
              range = c(0, 24),
              dtick = 3,
              gridcolor = "#ecf0f1",
              titlefont = list(size = 11, color = "#2c3e50")
            ),
            yaxis = list(
              title = "Densidad de actividad",
              gridcolor = "#ecf0f1",
              titlefont = list(size = 11, color = "#2c3e50"),
              rangemode = "tozero"
            ),
            plot_bgcolor = "white",
            paper_bgcolor = "white",
            margin = list(l = 60, r = 140, t = 60, b = 70),
            hovermode = "closest",
            legend = list(
              orientation = "v",
              x = 1.01,
              y = 1,
              xanchor = "left",
              yanchor = "top",
              font = list(size = 9),
              bgcolor = "rgba(255,255,255,0.8)",
              bordercolor = "#ecf0f1",
              borderwidth = 1
            ),
            autosize = TRUE
          ) %>%
          config(
            displayModeBar = TRUE, 
            displaylogo = FALSE,
            modeBarButtonsToRemove = c("pan2d", "lasso2d", "select2d", "autoScale2d"),
            responsive = TRUE
          )
        
        return(p_interactive)
      }
    }
    
    # Si hay muchas especies, ajustar leyenda
    if (length(top_species) > 6) {
      p <- p + guides(
        color = guide_legend(ncol = 1, override.aes = list(linewidth = 2, alpha = 1)),
        fill = guide_legend(ncol = 1)
      )
    }
    
  }, error = function(e) {
    # Si falla la densidad, usar histograma simple
    p <<- ggplot(data_filtered, aes(x = hour, fill = sp_binomial)) +
      geom_histogram(alpha = 0.6, position = "identity", bins = 24) +
      scale_x_continuous(breaks = seq(0, 24, 2), limits = c(0, 24)) +
      labs(
        title = "Patrón de actividad por especie",
        x = "Hora del día",
        y = "Frecuencia",
        fill = "Especie"
      ) +
      theme_minimal()
  })
  
  return(p)
} # Función para generar patrón de actividad circadiana por especie

# ===============================================================================
# FUNCIONES PARA CÁLCULO DE ÍNDICES DE DIVERSIDAD
# ===============================================================================

calcular_numeros_hill <- function(data, q = 1) {
  #' Calcula Números de Hill (diversidad efectiva)
  #'
  #' Generaliza índices clásicos de diversidad mediante el parámetro q que
  #' controla sensibilidad a especies raras vs comunes.
  #'
  #' @param data DataFrame con columna sp_binomial
  #' @param q Parámetro de orden (0, 1 o 2)
  #'
  #' @return numeric Número de especies efectivas
  #'
  #' @details
  #' Parámetro q:
  #'   - q = 0: Riqueza de especies (todas pesan igual)
  #'   - q = 1: Exponencial de Shannon (peso proporcional a abundancia)
  #'   - q = 2: Inverso de Simpson (especies abundantes pesan más)
  #'
  #' Fórmulas:
  #'   - q = 0: ^0D = S (número de especies)
  #'   - q = 1: ^1D = exp(-Σ p_i * ln(p_i))
  #'   - q ≠ 0,1: ^qD = (Σ p_i^q)^(1/(1-q))
  #'
  #' @references
  #' Hill, M.O. (1973). Diversity and evenness: A unifying notation.
  #' Ecology, 54(2), 427-432.
  #'
  #' Jost, L. (2006). Entropy and diversity. Oikos, 113(2), 363-375.
  #'
  
  # Validar datos
  if (!("sp_binomial" %in% names(data)) || nrow(data) == 0) {
    return(NA)
  }
  
  # Contar individuos por especie
  conteos <- data %>%
    filter(!is.na(sp_binomial)) %>%
    count(sp_binomial, name = "n_individuos")
  
  if (nrow(conteos) == 0) {
    return(NA)
  }
  
  # Calcular total de individuos
  total <- sum(conteos$n_individuos)
  
  # Calcular proporciones (p_i)
  proporciones <- conteos$n_individuos / total
  
  # Eliminar proporciones cero
  proporciones <- proporciones[proporciones > 0]
  
  # Calcular según el valor de q
  if (q == 0) {
    # q = 0: Riqueza de especies (simplemente el número de especies)
    hill <- length(proporciones)
    
  } else if (q == 1) {
    # q = 1: Exponencial de Shannon
    # ^1D = exp(-Σ p_i * ln(p_i))
    shannon <- -sum(proporciones * log(proporciones))
    hill <- exp(shannon)
    
  } else {
    # q > 0 y q ≠ 1: Fórmula general
    # ^qD = (Σ p_i^q)^(1/(1-q))
    suma_potencias <- sum(proporciones^q)
    hill <- suma_potencias^(1/(1-q))
  }
  
  return(round(hill, 2))
} # Función para calcular Números de Hill

# ===============================================================================
# FUNCIÓN PARA FILTRADO DE EVENTOS INDEPENDIENTES
# ===============================================================================

remove_duplicates <- function(data, interval = 30, unit = "minutes") {
  #' Filtra eventos independientes en datos de cámaras trampa
  #'
  #' Elimina registros duplicados del mismo taxón en el mismo sitio dentro de
  #' un intervalo temporal especificado. Usado para convertir ráfagas de fotos
  #' en eventos independientes.
  #'
  #' @param data DataFrame con columnas:
  #'   - deployment_name: Identificador del sitio/cámara
  #'   - photo_datetime: Timestamp de captura
  #'   - sp_binomial: Nombre científico de la especie
  #' @param interval Número de unidades de tiempo (default: 30)
  #' @param unit Unidad temporal ('seconds', 'minutes', 'hours', 'days', 'weeks')
  #'
  #' @return DataFrame Observaciones filtradas (solo eventos independientes)
  #'
  #' @details
  #' Algoritmo:
  #'   1. Agrupa por deployment_name y sp_binomial
  #'   2. Ordena cronológicamente por photo_datetime
  #'   3. Calcula diferencia temporal entre registros consecutivos
  #'   4. Conserva primer registro + registros fuera del intervalo
  #'   5. Preserva todos los registros sin identificación (NA)
  #'
  #' @examples
  #' # Eliminar ráfagas (mismo taxón en 30 minutos)
  #' data_clean <- remove_duplicates(data, interval = 30, unit = "minutes")
  #'
  #' # Filtro estricto (10 segundos)
  #' data_clean <- remove_duplicates(data, interval = 10, unit = "seconds")
  #'
  #' @note
  #' Registros sin identificación taxonómica (sp_binomial = NA) se preservan
  #' automáticamente sin aplicar filtro temporal.
  #'
  
  require(dplyr)
  require(lubridate)
  
  # Validar datos de entrada
  if (is.null(data) || nrow(data) == 0) {
    warning("DataFrame vacío proporcionado a remove_duplicates")
    return(data)
  }
  
  # Verificar columnas requeridas
  required_cols <- c("deployment_name", "photo_datetime", "sp_binomial")
  missing_cols <- setdiff(required_cols, names(data))
  
  if (length(missing_cols) > 0) {
    stop(paste("Columnas faltantes en el DataFrame:", paste(missing_cols, collapse = ", ")))
  }
  
  # Convertir intervalo a segundos según la unidad especificada
  interval_seconds <- switch(
    tolower(unit),
    "seconds" = interval,
    "minutes" = interval * 60,
    "hours" = interval * 3600,
    "days" = interval * 86400,
    "weeks" = interval * 604800,
    stop(paste("Unidad no reconocida:", unit, 
               ". Use: 'seconds', 'minutes', 'hours', 'days', 'weeks'"))
  )
  
  # Separar registros con y sin identificación taxonómica
  data_with_taxon <- data %>% filter(!is.na(sp_binomial) & sp_binomial != "")
  data_without_taxon <- data %>% filter(is.na(sp_binomial) | sp_binomial == "")
  
  # Si no hay registros con taxón, retornar datos originales
  if (nrow(data_with_taxon) == 0) {
    message("No hay registros con identificación taxonómica para filtrar")
    return(data)
  }
  
  # Convertir photo_datetime a POSIXct si no lo está
  data_with_taxon <- data_with_taxon %>%
    mutate(
      timestamp = as.POSIXct(photo_datetime, format = "%Y-%m-%d %H:%M:%S")
    )
  
  # Verificar conversión de timestamp
  if (all(is.na(data_with_taxon$timestamp))) {
    warning("No se pudo convertir photo_datetime a timestamp válido")
    return(data)
  }
  
  # Agrupar por deployment y taxón, ordenar por tiempo
  data_grouped <- data_with_taxon %>%
    group_by(deployment_name, sp_binomial) %>%
    arrange(timestamp) %>%
    mutate(
      # Calcular diferencia en segundos con el registro anterior del mismo grupo
      time_diff = as.numeric(difftime(timestamp, lag(timestamp), units = "secs")),
      # Marcar primer registro o registros fuera del intervalo
      keep_record = is.na(time_diff) | time_diff > interval_seconds
    ) %>%
    ungroup()
  
  # Filtrar solo registros a mantener
  data_filtered <- data_grouped %>%
    filter(keep_record) %>%
    select(-timestamp, -time_diff, -keep_record)  # Eliminar columnas auxiliares
  
  # Combinar con registros sin taxón (que se preservan todos)
  data_final <- bind_rows(data_filtered, data_without_taxon)
  
  # Reordenar por deployment y fecha original
  data_final <- data_final %>%
    arrange(deployment_name, photo_datetime)
  
  # Mensaje informativo
  n_original <- nrow(data)
  n_final <- nrow(data_final)
  n_removed <- n_original - n_final
  pct_removed <- round((n_removed / n_original) * 100, 2)
  
  message(sprintf(
    "Eliminados %d registros duplicados (%.2f%%) - Intervalo: %d %s",
    n_removed, pct_removed, interval, unit
  ))
  message(sprintf(
    "Registros originales: %d | Registros finales: %d",
    n_original, n_final
  ))
  
  return(data_final)
  
} # Función para eliminar registros duplicados por intervalo temporal

# ===============================================================================
# FUNCIÓN PARA CALCULAR INDICADORES POR PERÍODO (VISTA CONSOLIDADA)
# ===============================================================================

calcular_indicadores_por_periodo <- function(tableSites_consolidado, iavhdata_consolidado, mostrar_consolidado = TRUE) {
  # Calcula indicadores operacionales y de biodiversidad por período de muestreo
  # 
  # Esta función procesa datos consolidados de múltiples eventos y genera
  # una tabla con indicadores calculados por período más una fila de totales.
  # Solo incluye períodos donde existen datos (omite períodos sin registros).
  # 
  # Parámetros:
  #   tableSites_consolidado: DataFrame con datos de sitios (puede ser de todos los eventos
  #                           o filtrado por proyecto). Debe tener columna 'evento_muestreo'
  #   iavhdata_consolidado: DataFrame con datos de imágenes (puede ser de todos los eventos
  #                        o filtrado por proyecto). Debe tener columna 'evento_muestreo'
  #   mostrar_consolidado: Booleano. Si TRUE, agrega fila CONSOLIDADO. Si FALSE, la omite.
  #                        Se usa FALSE cuando: 1) solo hay 1 período con datos, o
  #                        2) se seleccionó un evento específico (no "TODOS")
  # 
  # Retorna:
  #   data.frame: Tabla con columnas Período, Imágenes, Cámaras, Días-cámara,
  #               Especies, Mamíferos, Aves, Hill1, Hill2, Hill3
  #   Solo incluye filas para períodos con datos reales (valores > 0)
  
  require(dplyr)
  
  # Validar que existan datos
  if (is.null(tableSites_consolidado) || nrow(tableSites_consolidado) == 0) {
    # Retornar tabla vacía con estructura correcta
    return(data.frame(
      Periodo = character(),
      Imagenes = numeric(),
      Camaras = numeric(),
      Dias_camara = numeric(),
      Especies = numeric(),
      Mamiferos = numeric(),
      Aves = numeric(),
      Hill1 = numeric(),
      Hill2 = numeric(),
      Hill3 = numeric(),
      stringsAsFactors = FALSE
    ))
  }
  
  # Obtener lista de períodos únicos con datos
  periodos <- unique(tableSites_consolidado$evento_muestreo)
  periodos <- periodos[!is.na(periodos)]  # Eliminar NA
  periodos <- sort(periodos, decreasing = TRUE)  # Más recientes primero
  
  # Si no hay períodos, retornar tabla vacía
  if (length(periodos) == 0) {
    return(data.frame(
      Periodo = character(),
      Imagenes = numeric(),
      Camaras = numeric(),
      Dias_camara = numeric(),
      Especies = numeric(),
      Mamiferos = numeric(),
      Aves = numeric(),
      Hill1 = numeric(),
      Hill2 = numeric(),
      Hill3 = numeric(),
      stringsAsFactors = FALSE
    ))
  }
  
  # Lista para almacenar resultados por período
  resultados <- list()
  
  # Calcular indicadores para cada período (solo períodos con datos)
  for (periodo in periodos) {
    # Filtrar datos del período
    sites_periodo <- tableSites_consolidado %>% filter(evento_muestreo == periodo)
    data_periodo <- iavhdata_consolidado %>% filter(evento_muestreo == periodo)
    
    # Verificar si el período tiene datos reales
    total_imagenes <- sum(sites_periodo$n, na.rm = TRUE)
    
    # Solo incluir período si tiene imágenes (evita filas con puros ceros)
    if (total_imagenes > 0) {
      # Calcular Números de Hill para el período
      hill1 <- tryCatch(calcular_numeros_hill(data_periodo, q = 0), error = function(e) NA)
      hill2 <- tryCatch(calcular_numeros_hill(data_periodo, q = 1), error = function(e) NA)
      hill3 <- tryCatch(calcular_numeros_hill(data_periodo, q = 2), error = function(e) NA)
      
      # CORRECCIÓN: Recalcular especies únicas desde data_periodo en lugar de sumar
      # Esto evita duplicados cuando una especie aparece en múltiples sitios del mismo período
      especies_periodo <- data_periodo %>%
        dplyr::filter(!is.na(sp_binomial) & sp_binomial != "") %>%
        dplyr::pull(sp_binomial) %>%
        unique() %>%
        length()
      
      mamiferos_periodo <- data_periodo %>%
        dplyr::filter(!is.na(sp_binomial) & sp_binomial != "" & 
                      !is.na(class) & class == "Mammalia") %>%
        dplyr::pull(sp_binomial) %>%
        unique() %>%
        length()
      
      aves_periodo <- data_periodo %>%
        dplyr::filter(!is.na(sp_binomial) & sp_binomial != "" & 
                      !is.na(class) & class == "Aves") %>%
        dplyr::pull(sp_binomial) %>%
        unique() %>%
        length()
      
      # Recalcular cámaras únicas desde data_periodo
      camaras_periodo <- data_periodo %>%
        dplyr::filter(!is.na(deployment_name) & deployment_name != "") %>%
        dplyr::pull(deployment_name) %>%
        unique() %>%
        length()
      
      # Crear fila de resultados
      resultados[[periodo]] <- data.frame(
        Periodo = periodo,
        Imagenes = total_imagenes,
        Camaras = camaras_periodo,                                 # RECALCULADO (evita duplicados)
        Dias_camara = sum(sites_periodo$effort, na.rm = TRUE),
        Especies = especies_periodo,                                # RECALCULADO (evita duplicados)
        Mamiferos = mamiferos_periodo,                              # RECALCULADO (evita duplicados)
        Aves = aves_periodo,                                        # RECALCULADO (evita duplicados)
        Hill1 = ifelse(is.na(hill1), 0, hill1),
        Hill2 = ifelse(is.na(hill2), 0, round(hill2, 2)),
        Hill3 = ifelse(is.na(hill3), 0, round(hill3, 2)),
        stringsAsFactors = FALSE
      )
    }
  }
  
  # Verificar que haya resultados
  if (length(resultados) == 0) {
    # No hay períodos con datos: retornar tabla vacía
    return(data.frame(
      Periodo = character(),
      Imagenes = numeric(),
      Camaras = numeric(),
      Dias_camara = numeric(),
      Especies = numeric(),
      Mamiferos = numeric(),
      Aves = numeric(),
      Hill1 = numeric(),
      Hill2 = numeric(),
      Hill3 = numeric(),
      stringsAsFactors = FALSE
    ))
  }
  
  # Combinar resultados de todos los períodos con datos
  tabla_periodos <- do.call(rbind, resultados)
  
  # Determinar si se debe agregar fila CONSOLIDADO
  # Lógica:
  # - Si mostrar_consolidado = FALSE (evento específico seleccionado): NO agregar
  # - Si solo hay 1 período con datos: NO agregar (sería redundante)
  # - Si hay múltiples períodos y mostrar_consolidado = TRUE: SÍ agregar
  
  num_periodos <- nrow(tabla_periodos)
  
  if (mostrar_consolidado && num_periodos > 1) {
    # Calcular fila CONSOLIDADO
    # IMPORTANTE: iavhdata_consolidado ya viene filtrado por proyecto/evento específico
    # Por lo tanto, NO podemos usarlo para recalcular especies únicas ya que solo
    # contiene el subconjunto filtrado, no todos los datos originales.
    # 
    # La solución correcta es recalcular desde los datos completos de todos los períodos
    # para obtener especies únicas sin duplicados entre períodos.
    
    # Recalcular especies únicas desde TODOS los datos filtrados (todos los períodos)
    especies_total <- iavhdata_consolidado %>%
      dplyr::filter(!is.na(sp_binomial) & sp_binomial != "") %>%
      dplyr::pull(sp_binomial) %>%
      unique() %>%
      length()
    
    mamiferos_total <- iavhdata_consolidado %>%
      dplyr::filter(!is.na(sp_binomial) & sp_binomial != "" & 
                    !is.na(class) & class == "Mammalia") %>%
      dplyr::pull(sp_binomial) %>%
      unique() %>%
      length()
    
    aves_total <- iavhdata_consolidado %>%
      dplyr::filter(!is.na(sp_binomial) & sp_binomial != "" & 
                    !is.na(class) & class == "Aves") %>%
      dplyr::pull(sp_binomial) %>%
      unique() %>%
      length()
    
    # Recalcular cámaras únicas desde TODOS los datos filtrados
    camaras_total <- iavhdata_consolidado %>%
      dplyr::filter(!is.na(deployment_name) & deployment_name != "") %>%
      dplyr::pull(deployment_name) %>%
      unique() %>%
      length()
    
    # Calcular Números de Hill desde datos consolidados (TODOS los períodos)
    hill1_total <- tryCatch(calcular_numeros_hill(iavhdata_consolidado, q = 0), error = function(e) NA)
    hill2_total <- tryCatch(calcular_numeros_hill(iavhdata_consolidado, q = 1), error = function(e) NA)
    hill3_total <- tryCatch(calcular_numeros_hill(iavhdata_consolidado, q = 2), error = function(e) NA)
    
    fila_total <- data.frame(
      Periodo = "CONSOLIDADO",
      Imagenes = sum(tabla_periodos$Imagenes, na.rm = TRUE),      # SUMA (no hay duplicados en imágenes)
      Camaras = camaras_total,                                     # RECALCULADO (evita duplicados entre períodos)
      Dias_camara = sum(tabla_periodos$Dias_camara, na.rm = TRUE),# SUMA (no hay duplicados en días)
      Especies = especies_total,                                   # RECALCULADO (evita duplicados entre períodos)
      Mamiferos = mamiferos_total,                                 # RECALCULADO (evita duplicados entre períodos)
      Aves = aves_total,                                           # RECALCULADO (evita duplicados entre períodos)
      Hill1 = ifelse(is.na(hill1_total), 0, hill1_total),         # RECALCULADO desde todos los datos
      Hill2 = ifelse(is.na(hill2_total), 0, round(hill2_total, 2)),# RECALCULADO desde todos los datos
      Hill3 = ifelse(is.na(hill3_total), 0, round(hill3_total, 2)),# RECALCULADO desde todos los datos
      stringsAsFactors = FALSE
    )
    
    # Combinar períodos con datos + total consolidado
    tabla_final <- rbind(tabla_periodos, fila_total)
  } else {
    # No agregar fila CONSOLIDADO (evento específico o solo 1 período)
    tabla_final <- tabla_periodos
  }
  
  return(tabla_final)
  
} # Función para calcular indicadores por período en vista consolidada

# ===============================================================================
# FIN DEL ARCHIVO - functions_data.R
# ===============================================================================
# Total de funciones activas: 11
# Última modificación: 2025-12-09
# Versión: 2.0 - Arquitectura consolidada optimizada
# ===============================================================================