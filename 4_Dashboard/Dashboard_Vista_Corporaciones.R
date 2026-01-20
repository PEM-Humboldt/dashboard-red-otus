# ===============================================================================
# Dashboard IaVH - Red OTUS Colombia
# ===============================================================================
# Proyecto:     Sistema de Monitoreo de Biodiversidad con Cámaras Trampa
# Autores:      Jorge Ahumada (c) Conservation International (2020)
#               Cristian C. Acevedo - Instituto Humboldt (2025)
# Descripción:  Dashboard interactivo Shiny para visualización y análisis de
#               datos de fototrampeo de Wildlife Insights. Soporta análisis
#               multi-evento, vistas consolidadas y exportación de reportes.
# Tecnología:   R Shiny + shinydashboard + Plotly + Leaflet
# Versión:      2.0 - Arquitectura consolidada Parquet
# Licencia:     CC0 1.0 Universal (Public Domain)
# Última mod.:  2025-12-09
# ===============================================================================

# ===============================================================================
# LIBRERÍAS REQUERIDAS
# ===============================================================================

# Framework Shiny
library(shiny)
library(shinydashboard)
library(dashboardthemes)
library(shinyjs)

# Visualización de datos
library(plotly)          # Gráficos interactivos (patrón de actividad)
library(leaflet)         # Mapas interactivos
library(sf)              # Manejo de datos espaciales (shapefiles)

# Componentes multimedia
library(slickR)          # Carrusel de imágenes
library(magick)          # Procesamiento de imágenes
library(cowplot)         # Composición de gráficos

# Tablas interactivas (crítico)
if (!requireNamespace("DT", quietly = TRUE)) {
  stop("Paquete requerido 'DT' no instalado.\n",
       "Instalación: install.packages('DT')\n",
       "Consulte INSTALL_DT.md para detalles.")
}
library(DT)

# Autenticación (opcional - futuro)
library(shinymanager)

# NOTA: Librerías adicionales futuras
# library(webshot2)      # Exportación HTML a imagen (requiere configuración adicional)
# library(iNEXT)         # Análisis avanzado de diversidad

# ===============================================================================
# CONFIGURACIÓN GLOBAL
# ===============================================================================

# Suprimir mensajes de Plotly durante inicialización
options(warn = -1)
options(
  plotly.message = FALSE,
  plotly.warning = FALSE,
  plotly.verbose = FALSE
)

# Cargar funciones de análisis personalizadas
source("functions_data.R")

# Restaurar warnings
options(warn = 0)

# ===============================================================================
# FUNCIONES AUXILIARES DEL DASHBOARD
# ===============================================================================

consolidar_estadisticas_sitios <- function(tableSites, nombre_proyecto) {
  #' Agrega estadísticas de múltiples sitios
  #'
  #' Consolida métricas operacionales y de biodiversidad de todos los sitios
  #' de una vista (corporación/evento), generando totales agregados.
  #'
  #' @param tableSites DataFrame con columnas: n, ndepl, effort, ospTot, etc.
  #' @param nombre_proyecto String identificador de la vista (corporación-evento)
  #'
  #' @return DataFrame con fila única de totales consolidados
  #'
  #' @details
  #' Filtra registros válidos (n > 0) y suma:
  #'   - Imágenes totales
  #'   - Número de deployments
  #'   - Días-cámara acumulados
  #'   - Especies totales (Mammalia, Aves, Total)
  #'
  require(dplyr)
  
  # Filtrar registros válidos (excluye encabezados y valores nulos)
  datos_validos <- tableSites[!is.na(tableSites$n) & tableSites$n > 0, ]
  
  if (nrow(datos_validos) == 0) {
    # Retornar estructura vacía con valores por defecto
    return(data.frame(
      project_short_name = nombre_proyecto,
      site_name = "Consolidado",
      n = 0,
      ndepl = 0,
      effort = 0,
      ospTot = 0,
      ospMamiferos = 0,
      ospAves = 0,
      # Rankings (valores por defecto)
      rank_images = 1,
      rank_ndepl = 1,
      rank_effort = 1,
      rank_onsp = 1,
      rank_onMamiferos = 1,
      rank_onAves = 1,
      collector = "Múltiples",
      departamento = "Colombia",
      stringsAsFactors = FALSE
    ))
  }
  
  # Agregar totales por columna
  consolidado <- data.frame(
    project_short_name = nombre_proyecto,
    site_name = "Consolidado",
    n = sum(datos_validos$n, na.rm = TRUE),
    ndepl = sum(datos_validos$ndepl, na.rm = TRUE),
    effort = sum(datos_validos$effort, na.rm = TRUE),
    ospTot = sum(datos_validos$ospTot, na.rm = TRUE),
    ospMamiferos = sum(datos_validos$ospMamiferos, na.rm = TRUE),
    ospAves = sum(datos_validos$ospAves, na.rm = TRUE),
    # Rankings (no aplican a consolidados)
    rank_images = 1,
    rank_ndepl = 1,
    rank_effort = 1,
    rank_onsp = 1,
    rank_onMamiferos = 1,
    rank_onAves = 1,
    collector = nombre_proyecto,
    departamento = paste(unique(datos_validos$departamento[!is.na(datos_validos$departamento)]), collapse = ", "),
    stringsAsFactors = FALSE
  )
  
  return(consolidado)
}



# ===============================================================================
# CARGA DE DATOS (ARQUITECTURA PARQUET)
# ===============================================================================
# Archivos requeridos en dashboard_input_data/:
#   - observations.parquet: Detecciones con metadata (Corporacion, subproject_name)
#   - deployments.parquet: Configuración de cámaras
#   - projects.parquet: Catálogo de corporaciones y eventos
#
# Las estadísticas se calculan dinámicamente según filtros seleccionados.
# ===============================================================================

# Validar existencia de archivos
eventos_disponibles <- obtener_eventos_disponibles()

if (length(eventos_disponibles) == 0) {
  stop("Archivos parquet no encontrados en dashboard_input_data/\n",
       "Ejecute process_RAW_data_WI.py para generar archivos.")
}

# Cargar datos consolidados
message("📂 Cargando datos desde Parquet...")
datos_iniciales <- cargar_datos_consolidados(interval = "30min")

if (is.null(datos_iniciales)) {
  stop("Error crítico al cargar archivos parquet.")
}

# Cargar shapefile de CARs
message("🗺️ Cargando shapefile de corporaciones...")
shapefile_path <- file.path("shapefiles_cars", "CAR_MPIO.shp")
if (file.exists(shapefile_path)) {
  car_shapefile <- sf::st_read(shapefile_path, quiet = TRUE)
  # Transformar a WGS84 (EPSG:4326) para compatibilidad con Leaflet
  car_shapefile <- sf::st_transform(car_shapefile, 4326)
} else {
  warning("Shapefile de CARs no encontrado en: ", shapefile_path)
  car_shapefile <- NULL
}

# ===============================================================================
# PREPARACIÓN DE DATOS PARA DASHBOARD
# ===============================================================================

# Extraer componentes principales
iavhdata <- datos_iniciales$iavhdata
tableSites <- datos_iniciales$tableSites
projects_data <- datos_iniciales$projects

# CRÍTICO: Arrow carga subproject_name como 'category' (factor)
# Convertir a character para compatibilidad con selectores Shiny
if ("subproject_name" %in% names(iavhdata)) {
  iavhdata$subproject_name <- as.character(iavhdata$subproject_name)
}

if ("subproject_name" %in% names(tableSites)) {
  tableSites$subproject_name <- as.character(tableSites$subproject_name)
}

# CRÍTICO: Arrow también carga Corporacion como 'category' (factor)
# Convertir a character para correcta visualización en selectores
if ("Corporacion" %in% names(iavhdata)) {
  iavhdata$Corporacion <- as.character(iavhdata$Corporacion)
}

if ("Corporacion" %in% names(tableSites)) {
  tableSites$Corporacion <- as.character(tableSites$Corporacion)
}

# Mapear evento_muestreo para retrocompatibilidad
if ("subproject_name" %in% names(iavhdata) && !("evento_muestreo" %in% names(iavhdata))) {
  iavhdata$evento_muestreo <- iavhdata$subproject_name
}

if ("subproject_name" %in% names(tableSites) && !("evento_muestreo" %in% names(tableSites))) {
  tableSites$evento_muestreo <- tableSites$subproject_name
}

generar_nombre_consolidado <- function(evento) {
  #' Genera nombre estandarizado para vistas consolidadas
  #'
  #' @param evento String identificador (no usado en arquitectura actual)
  #' @return String "Red OTUS - Consolidado"
  return("Red OTUS - Consolidado")
}

# ===============================================================================
# PREPARACIÓN DE SELECTORES UI
# ===============================================================================

# Selector de eventos (períodos de muestreo)
if ("subproject_name" %in% names(iavhdata)) {
  eventos_unicos <- unique(as.character(iavhdata$subproject_name))
  eventos_unicos <- eventos_unicos[!is.na(eventos_unicos) & eventos_unicos != ""]
  eventos_unicos <- sort(eventos_unicos, decreasing = TRUE)
} else {
  eventos_unicos <- character(0)
}

eventos_choices <- c(
  setNames("", "-- Seleccione un evento --"),
  setNames("TODOS", "Todos los eventos"),
  setNames(eventos_unicos, eventos_unicos)
)

# Selector de corporaciones (CARs)
if ("Corporacion" %in% names(iavhdata)) {
  corporaciones_df <- iavhdata %>% 
    dplyr::select(Corporacion) %>%
    dplyr::distinct() %>%
    dplyr::filter(!is.na(Corporacion) & Corporacion != "")
  
  corporaciones_unicas <- corporaciones_df$Corporacion
  corporaciones_labels <- corporaciones_unicas
  
  orden <- order(corporaciones_labels)
  corporaciones_unicas <- corporaciones_unicas[orden]
  corporaciones_labels <- corporaciones_labels[orden]
} else if ("departamento" %in% names(tableSites)) {
  # Fallback: usar departamento si Corporacion no existe
  corporaciones_df <- tableSites %>% 
    dplyr::select(departamento) %>%
    dplyr::distinct() %>%
    dplyr::filter(!is.na(departamento) & departamento != "")
  
  corporaciones_unicas <- corporaciones_df$departamento
  corporaciones_labels <- corporaciones_unicas
  
  orden <- order(corporaciones_labels)
  corporaciones_unicas <- corporaciones_unicas[orden]
  corporaciones_labels <- corporaciones_labels[orden]
} else {
  corporaciones_unicas <- character(0)
  corporaciones_labels <- character(0)
}

corporacion_choices <- c("", "TODAS", corporaciones_unicas)
names(corporacion_choices) <- c("-- Seleccione una corporación --", "Todas las corporaciones", corporaciones_labels)

# Ajustar numeración de filas si existe columna
if ("row" %in% names(tableSites)) {
  tableSites$row <- tableSites$row + 1
}

# ===============================================================================
# INTERFAZ DE USUARIO (UI)
# ===============================================================================

body <- dashboardBody(
  # Inicializar shinyjs para control dinámico de UI
  shinyjs::useShinyjs(),
  
  # CSS personalizado y librerías JavaScript
  tags$head(
    tags$link(rel = "stylesheet", type = "text/css", href = "css/style.css"),
    # Librería html2canvas para captura de pantalla
    tags$script(src = "https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js")
  ),
  
  # ===========================================================================
  # SECCIÓN 1: ENCABEZADO
  # ===========================================================================
  # Título del reporte y nombre dinámico de la corporación/evento seleccionado
  fluidRow(
    column(12,
      box(
        width = NULL, 
        title = NULL,
        tags$div(
          class = "section-box-title",
          tags$h1(
            class = "report-title", 
            "Reporte de datos de fototrampeo – Red OTUS"
          ),
          tags$h2(
            class = "report-subtitle",
            tags$strong("Corporación: "), 
            uiOutput("project_name", inline = TRUE)
          )
        )
      )
    )
  ),
  
  # ===========================================================================
  # SECCIÓN 2: CONTROLES Y METADATOS
  # ===========================================================================
  
  fluidRow(
    column(12,
      box(
        width = NULL, 
        title = "1. Selección parámetros de visualización",
        fluidRow(
          # Selector: Corporación (PRIMERO)
          column(4,
            tags$div(
              class = "filter-item",
              tags$label(class = "filter-label", "Corporación Ambiental Regional (CAR)"),
              selectInput(
                "corporacion", 
                NULL, 
                choices = corporacion_choices,
                selected = ""  # Inicio sin selección
              )
            )
          ),
          
          # Selector: Evento de muestreo (SEGUNDO)
          column(4,
            tags$div(
              class = "filter-item",
              tags$label(class = "filter-label", "Evento de muestreo"),
              selectInput(
                "evento", 
                NULL, 
                choices = eventos_choices,
                selected = ""  # Inicio sin selección
              )
            )
          ),
          
          # Selector: Filtro de registros independientes (TERCERO)
          column(4,
            tags$div(
              class = "filter-item",
              tags$label(
                class = "filter-label",
                "Filtro de registros independientes",
                tags$span(
                  class = "info-tooltip",
                  title = "Elimina detecciones repetidas del mismo taxón en el mismo sitio dentro del intervalo seleccionado. 30 minutos es el estándar ecológico recomendado. Útil para eliminar ráfagas fotográficas y re-visitas cercanas.",
                  "ℹ️"
                )
              ),
              selectInput(
                "duplicateInterval",
                NULL,
                choices = c(
                  "1 minuto" = "1min",
                  "30 minutos (Valor sugerido)" = "30min",
                  "1 hora" = "1h",
                  "6 horas" = "6h",
                  "12 horas" = "12h"
                ),
                selected = "30min"  # Default: 30 minutos
              )
            )
          )
        ),
        
        # Botones de control
        fluidRow(
          column(12,
            tags$div(
              class = "control-buttons-container",
              actionButton(
                "aplicarSeleccion",
                "Aplicar selección",
                icon = icon("check-circle"),
                class = "btn-primary btn-apply-selection",
                disabled = TRUE  # Iniciar deshabilitado
              ),
              actionButton(
                "limpiarSeleccion",
                "Limpiar selección",
                icon = icon("times-circle"),
                class = "btn-secondary btn-clear-selection",
                disabled = TRUE  # Iniciar deshabilitado
              )
            )
          )
        )
      )
    )
  ),
  
  # ===========================================================================
  # SECCIÓN 3: INDICADORES CLAVE
  # ===========================================================================
  fluidRow(
    column(12,
      box(
        width = NULL, 
        title = "2. Indicadores operacionales y de biodiversidad",
        # Información de la corporación (Administrador y Fechas)
        fluidRow(
          column(6,
            tags$div(
              class = "filter-item info-project-meta",
              tags$label(class = "filter-label", "Administrador"),
              tags$div(
                class = "info-text",
                tags$span(class = "info-label", "Datos gestionados por:"),
                tags$h4(class = "info-value", textOutput("collector"))
              )
            )
          ),
          column(6,
            tags$div(
              class = "filter-item info-project-meta",
              tags$label(class = "filter-label", "Rango de fechas"),
              tags$div(
                class = "info-text",
                tags$span(class = "info-label", "Fechas:"),
                tags$h4(class = "info-value", textOutput("dateRange"))
              )
            )
          )
        ),
        # Tabla de indicadores
        uiOutput("indicadores_table_ui")
      )
    )
  ),
  
  # ===========================================================================
  # SECCIÓN 4: TABLA DE ESPECIES
  # ===========================================================================
  fluidRow(
    column(12,
      box(
        width = NULL,
        title = "3. Ranking detallado de especies fotografiadas",
        # Contenedor de tabla con scroll
        tags$div(
          class = "species-table-container",
          DT::dataTableOutput("speciesTable")
        ),
        # Botón de descarga
        tags$div(
          class = "download-button-container",
          downloadButton(
            "downloadSpeciesTable",
            "Descargar tabla (CSV)",
            class = "btn-primary btn-sm"
          ) %>% tagAppendAttributes(disabled = NA)
        )
      )
    )
  ),
  
  # ===========================================================================
  # SECCIÓN 5: GRÁFICOS DE ANÁLISIS
  # ===========================================================================
  fluidRow(
    column(6,
      box(
        width = NULL, 
        class = "box-xl", 
        title = "4.1. Ocupación de Especies",
        tags$p(
          class = "box-description", 
          "Proporción de sitios donde cada especie fue detectada (ocupación naive)."
        ),
        plotOutput("occupancyPlot", height = "380px")
      )
    ),
    column(6,
      box(
        width = NULL, 
        class = "box-xl", 
        title = "4.2. Curva de acumulación de especies",
        tags$p(
          class = "box-description", 
          "Incremento en riqueza de especies a través del tiempo."
        ),
        plotOutput("accumulationCurve", height = "380px")
      )
    )
  ),
  
  # Fila 2: Actividad circadiana + Mapa de ubicación
  fluidRow(
    column(6,
      box(
        width = NULL, 
        class = "box-lg", 
        title = "4.3. Patrón de actividad por hora del día",
        tags$p(
          class = "box-description", 
          "Distribución de la actividad de las especies más frecuentes a lo largo de las 24 horas."
        ),
        plotlyOutput("activityPattern")
      )
    ),
    column(6,
      box(
        width = NULL, 
        class = "box-lg", 
        title = "4.4. Mapa de ubicación de cámaras trampa",
        tags$p(
          class = "box-description", 
          "Localización geográfica de las cámaras instaladas."
        ),
        leafletOutput("map", height = "340px")
      )
    )
  ),
  
  # ===========================================================================
  # SECCIÓN 6: GALERÍA MULTIMEDIA
  # ===========================================================================
  fluidRow(
    column(12,
      box(
        width = NULL, 
        class = "box-md", 
        title = "5. Imágenes destacadas del muestreo",
        uiOutput("galeria_ui")
      )
    )
  ),
  
  # ===========================================================================
  # SECCIÓN 7: EXPORTACIÓN
  # ===========================================================================
  fluidRow(
    column(12,
      box(
        width = NULL,
        class = "export-section-compact",
        title = NULL,
        tags$div(
          class = "export-buttons-compact",
          actionButton(
            "captureScreen",
            "Exportar vista como PNG",
            class = "btn-export-compact",
            icon = icon("camera")
          ) %>% tagAppendAttributes(disabled = NA)
        )
      )
    )
  ),
  
  # ===========================================================================
  # SECCIÓN 7: CRÉDITOS
  # ===========================================================================
  # Logos de instituciones colaboradoras
  fluidRow(
    column(12,
      box(
        width = NULL,
        title = NULL,
        class = "footer-logos-box",
        tags$img(
          src = "images/Logos/Logos_instituciones.png", 
          alt = "Logos institucionales",
          class = "footer-logos-img"
        )
      )
    )
  )
)

# ===============================================================================
# CONFIGURACIÓN DE COMPONENTES
# ===============================================================================

MAX_FAVORITES <- 40                    # Límite de imágenes en carrusel
IMG_PATTERN <- "\\.(jpe?g|png)$"        # Formato de archivos válidos

# ===============================================================================
# LÓGICA DEL SERVIDOR (REACTIVIDAD)
# ===============================================================================

server <- function(input, output, session) {
  
  # =============================================================================
  # ESTADO REACTIVO GLOBAL
  # =============================================================================
  
  # Almacena datos filtrados y estado de selección
  datos_actuales <- reactiveValues(
    tableSites = tableSites,
    iavhdata = iavhdata,
    projects = projects_data,
    datos_filtrados = FALSE
  )
  
  # Variables de control de filtros aplicados
  evento_aplicado <- reactiveVal("")
  corporacion_aplicada <- reactiveVal("")
  intervalo_aplicado <- reactiveVal("30min")
  
  # =============================================================================
  # OBSERVADORES DE EVENTOS UI
  # =============================================================================
  
  # Control de habilitación del botón "Aplicar selección"
  observe({
    tiene_seleccion <- (!is.null(input$corporacion) && input$corporacion != "") || 
                       (!is.null(input$evento) && input$evento != "")
    
    if (tiene_seleccion) {
      shinyjs::enable("aplicarSeleccion")
    } else {
      shinyjs::disable("aplicarSeleccion")
    }
  })
  
  # Control de habilitación de botones de exportación
  observe({
    tiene_datos <- datos_actuales$datos_filtrados && 
                   (nrow(subRawData()) > 0 || nrow(subTableData()) > 0)
    
    if (tiene_datos) {
      shinyjs::enable("downloadSpeciesTable")
      shinyjs::enable("captureScreen")
      shinyjs::enable("limpiarSeleccion")
    } else {
      shinyjs::disable("downloadSpeciesTable")
      shinyjs::disable("captureScreen")
      shinyjs::disable("limpiarSeleccion")
    }
  })
  
  # Botón: Limpiar selección
  observeEvent(input$limpiarSeleccion, {
    updateSelectInput(session, "corporacion", selected = "")
    updateSelectInput(session, "evento", selected = "")
    updateSelectInput(session, "duplicateInterval", selected = "30min")
    
    evento_aplicado("")
    corporacion_aplicada("")
    intervalo_aplicado("30min")
    datos_actuales$datos_filtrados <- FALSE
    
    shinyjs::disable("aplicarSeleccion")
    shinyjs::disable("limpiarSeleccion")
    shinyjs::disable("downloadSpeciesTable")
    shinyjs::disable("captureScreen")
    
    showNotification(
      "Selección limpiada. Seleccione corporación y/o evento.",
      type = "message", duration = 3
    )
  })
  
  # Botón aplicar selección
  observeEvent(input$aplicarSeleccion, {
    if ((is.null(input$corporacion) || input$corporacion == "") && 
        (is.null(input$evento) || input$evento == "")) {
      showNotification(
        "Por favor seleccione al menos una corporación o evento antes de aplicar.",
        type = "warning", duration = 4
      )
      return()
    }
    
    evento_aplicado(input$evento)
    corporacion_aplicada(input$corporacion)
    intervalo_aplicado(input$duplicateInterval)  # Aplicar intervalo seleccionado
    datos_actuales$datos_filtrados <- TRUE
    
    interval_name <- switch(
      as.character(input$duplicateInterval),
      "1min" = "1 minuto",
      "30min" = "30 minutos (Valor sugerido)",
      "1h" = "1 hora",
      "6h" = "6 horas",
      "12h" = "12 horas",
      "30 minutos"  # Default
    )
    
    corporacion_msg <- if (is.null(input$corporacion) || input$corporacion == "" || input$corporacion == "TODAS") {
      "Todas las corporaciones"
    } else {
      paste0("Corporación: ", input$corporacion)
    }
    
    evento_msg <- if (is.null(input$evento) || input$evento == "" || input$evento == "TODOS") {
      "Todos los eventos"
    } else {
      paste0("Evento: ", input$evento)
    }
    
    showNotification(
      HTML(paste0(
        "<strong>✓ Selección aplicada</strong><br/>",
        corporacion_msg, "<br/>", evento_msg, "<br/>",
        "Intervalo: ", interval_name
      )),
      type = "message", duration = 4
    )
  })
  
  # =============================================================================
  # VARIABLES AUXILIARES REACTIVAS
  # =============================================================================
  
  # Número de sitios únicos filtrados
  nsites <- reactive({
    sitios_filtrados <- subSitesData()
    if (nrow(sitios_filtrados) == 0) return(0)
    max(nrow(sitios_filtrados) - 1, 0)
  })
  
  # Límites geográficos de Colombia para mapa
  bounds <- data.frame(
    lat = c(1.683247, 12.665921, 1.248316, -4.322823), 
    lon = c(-79.137686, -71.675299, -66.744664, -69.937127)
  )
  
  # =============================================================================
  # DATOS FILTRADOS REACTIVOS
  # =============================================================================
  
  # Observaciones filtradas por corporación y evento
  subRawData <- reactive({
    evento_actual <- evento_aplicado()
    corporacion_actual <- corporacion_aplicada()
    
    if (is.null(evento_actual) || is.null(corporacion_actual) || 
        (evento_actual == "" && corporacion_actual == "")) {
      return(data.frame())
    }
    
    datos <- datos_actuales$iavhdata
    
    # Filtrar por corporación primero (más selectivo)
    if (!is.null(corporacion_actual) && corporacion_actual != "" && corporacion_actual != "TODAS") {
      # Corporacion es string, no requiere conversión numérica
      if ("Corporacion" %in% names(datos)) {
        datos <- datos %>% dplyr::filter(Corporacion == corporacion_actual)
      }
    }
    
    # Filtrar por evento después
    if (!is.null(evento_actual) && evento_actual != "" && evento_actual != "TODOS") {
      # Usar subproject_name directamente (siempre existe)
      datos <- datos %>% dplyr::filter(subproject_name == evento_actual)
    }
    
    return(datos)
  })
  
  subTableData <- reactive({
    evento_actual <- evento_aplicado()
    corporacion_actual <- corporacion_aplicada()
    
    if (is.null(evento_actual) || is.null(corporacion_actual) || 
        (evento_actual == "" && corporacion_actual == "")) {
      return(data.frame())
    }
    
    datos_sitios <- datos_actuales$tableSites
    
    # Filtrar por corporación primero (más selectivo)
    if (!is.null(corporacion_actual) && corporacion_actual != "" && corporacion_actual != "TODAS") {
      # Corporacion es string, no requiere conversión numérica
      # IMPORTANTE: tableSites usa 'departamento' (renombrado desde Corporacion)
      if ("departamento" %in% names(datos_sitios)) {
        datos_sitios <- datos_sitios %>% dplyr::filter(departamento == corporacion_actual)
      }
    }
    
    # Filtrar por evento después
    if (!is.null(evento_actual) && evento_actual != "" && evento_actual != "TODOS") {
      # Usar subproject_name directamente (siempre existe)
      datos_sitios <- datos_sitios %>% dplyr::filter(subproject_name == evento_actual)
    }
    
    nombre_vista <- paste(
      if (is.null(corporacion_actual) || corporacion_actual == "" || corporacion_actual == "TODAS") {
        "Todas las corporaciones"
      } else {
        corporacion_actual
      },
      "-",
      if (is.null(evento_actual) || evento_actual == "" || evento_actual == "TODOS") {
        "Todos los eventos"
      } else {
        evento_actual
      }
    )
    
    consolidar_estadisticas_sitios(datos_sitios, nombre_vista)
  })
  
  # Reactivo para datos de sitios filtrados (para mapa)
  subSitesData <- reactive({
    evento_actual <- evento_aplicado()
    corporacion_actual <- corporacion_aplicada()
    
    if (is.null(evento_actual) || is.null(corporacion_actual) || 
        (evento_actual == "" && corporacion_actual == "")) {
      return(data.frame())
    }
    
    datos_sitios <- datos_actuales$tableSites
    
    # Filtrar por corporación primero (más selectivo)
    if (!is.null(corporacion_actual) && corporacion_actual != "" && corporacion_actual != "TODAS") {
      # Corporacion es string, no requiere conversión numérica
      # IMPORTANTE: tableSites usa 'departamento' (renombrado desde Corporacion)
      if ("departamento" %in% names(datos_sitios)) {
        datos_sitios <- datos_sitios %>% dplyr::filter(departamento == corporacion_actual)
      }
    }
    
    # Filtrar por evento después
    if (!is.null(evento_actual) && evento_actual != "" && evento_actual != "TODOS") {
      # Usar subproject_name directamente (siempre existe)
      datos_sitios <- datos_sitios %>% dplyr::filter(subproject_name == evento_actual)
    }
    
    return(datos_sitios)
  })
  
  # =============================================================================
  # OUTPUTS: VISUALIZACIONES PRINCIPALES
  # =============================================================================
  
  # Tabla interactiva de especies
  output$speciesTable <- DT::renderDataTable({
    # Validar que hay datos filtrados
    if (nrow(subRawData()) == 0) {
      # Retornar tabla vacía con mensaje
      return(DT::datatable(
        data.frame(Mensaje = "Seleccione una corporación y/o evento para ver el ranking de especies"),
        options = list(dom = 't', ordering = FALSE, searching = FALSE),
        rownames = FALSE,
        selection = 'none'
      ))
    }
    
    # Convertir selector a intervalo y unidad
    interval_config <- switch(
      as.character(input$duplicateInterval),
      "1min" = list(interval = 1, unit = "minutes"),
      "30min" = list(interval = 30, unit = "minutes"),
      "1h" = list(interval = 1, unit = "hours"),
      "6h" = list(interval = 6, unit = "hours"),
      "12h" = list(interval = 12, unit = "hours"),
      list(interval = 30, unit = "minutes")  # Default
    )
    
    tabla_datos <- makeSpeciesTable(
      subRawData(), 
      interval = interval_config$interval,
      unit = interval_config$unit,
      species_stats = NULL
    )
    
    DT::datatable(
      tabla_datos,
      options = list(
        pageLength = nrow(tabla_datos),  # Mostrar todas las filas
        searching = TRUE,
        ordering = TRUE,
        order = list(list(0, 'asc')),  # Ordenar por ranking ascendente
        scrollX = TRUE,
        scrollY = "150px",  # Altura reducida (aprox 3 filas)
        scrollCollapse = FALSE,
        paging = FALSE,  # Desactivar paginación
        info = FALSE,  # Ocultar información de registros
        dom = 'ft',  # Solo filtro y tabla (sin paginación ni info)
        language = list(
          search = "Buscar:",
          lengthMenu = "Mostrar _MENU_ registros",
          info = "Mostrando _START_ a _END_ de _TOTAL_ especies",
          infoEmpty = "No hay registros disponibles",
          infoFiltered = "(filtrado de _MAX_ especies totales)",
          paginate = list(
            first = "Primero",
            last = "Último",
            `next` = "Siguiente",
            previous = "Anterior"
          ),
          zeroRecords = "No se encontraron especies",
          emptyTable = "No hay datos disponibles en la tabla"
        )
      ),
      rownames = FALSE,
      class = 'cell-border stripe hover',
      selection = 'none'
    ) %>%
      DT::formatCurrency(c("Numero imagenes", "Registros independientes"), 
                         currency = "", 
                         digits = 0, 
                         mark = ",")
  })
  
  # Exportación: Tabla de especies en CSV
  output$downloadSpeciesTable <- downloadHandler(
    filename = function() {
      corporacion_nombre <- if (is.null(input$corporacion) || input$corporacion == "" || input$corporacion == "TODAS") {
        "Todas_corporaciones"
      } else {
        gsub(" ", "_", input$corporacion)
      }
      
      evento_nombre <- if (is.null(input$evento) || input$evento == "" || input$evento == "TODOS") {
        "Todos_eventos"
      } else {
        gsub(" ", "_", input$evento)
      }
      
      timestamp <- format(Sys.time(), "%Y%m%d_%H%M%S")
      paste0("Ranking_Especies_", corporacion_nombre, "_", evento_nombre, "_", timestamp, ".csv")
    },
    content = function(file) {
      # Aplicar mismo filtro que en tabla
      interval_config <- switch(
        as.character(intervalo_aplicado()),
        "1min" = list(interval = 1, unit = "minutes"),
        "30min" = list(interval = 30, unit = "minutes"),
        "1h" = list(interval = 1, unit = "hours"),
        "6h" = list(interval = 6, unit = "hours"),
        "12h" = list(interval = 12, unit = "hours"),
        list(interval = 30, unit = "minutes")  # Default
      )
      
      tabla_datos <- makeSpeciesTable(
        subRawData(),
        interval = interval_config$interval,
        unit = interval_config$unit,
        species_stats = NULL
      )
      write.csv(tabla_datos, file, row.names = FALSE, fileEncoding = "UTF-8")
    }
  )
  
  # Gráfico: Ocupación de especies
  output$occupancyPlot <- renderPlot({
    if (nrow(subRawData()) == 0) {
      plot.new()
      text(0.5, 0.5, "Seleccione una corporación y/o evento\npara ver la ocupación de especies",
           cex = 1.5, col = "#7f8c8d", font = 2)
      return()
    }
    
    # Convertir selector a intervalo y unidad
    interval_config <- switch(
      as.character(intervalo_aplicado()),
      "1min" = list(interval = 1, unit = "minutes"),
      "30min" = list(interval = 30, unit = "minutes"),
      "1h" = list(interval = 1, unit = "hours"),
      "6h" = list(interval = 6, unit = "hours"),
      "12h" = list(interval = 12, unit = "hours"),
      list(interval = 30, unit = "minutes")  # Default
    )
    
    makeOccupancyGraph(
      subRawData(), 
      top_n = 15,
      interval = interval_config$interval,
      unit = interval_config$unit,
      occupancy_stats = NULL
    )
  })
  
  # Gráfico: Curva de acumulación de especies
  output$accumulationCurve <- renderPlot({
    if (nrow(subRawData()) == 0) {
      plot.new()
      text(0.5, 0.5, "Seleccione una corporación y/o evento\npara ver la curva de acumulación",
           cex = 1.5, col = "#7f8c8d", font = 2)
      return()
    }
    
    makeAccumulationCurve(
      subRawData(), 
      smooth_curve = TRUE,
      accumulation_curve = NULL
    )
  })
  
  # Gráfico 4.3: Patrón de actividad (CON PLOTLY - interactivo)
  output$activityPattern <- renderPlotly({
    # Validar que hay datos filtrados
    if (nrow(subRawData()) == 0) {
      # Retornar plotly vacío con mensaje (especificar tipo para evitar warnings)
      return(
        plot_ly(type = 'scatter', mode = 'markers') %>%
          layout(
            title = list(text = "Seleccione una corporación y/o evento para ver el patrón de actividad",
                        font = list(size = 16, color = "#7f8c8d"))
          )
      )
    } else {
      # Convertir selector a intervalo y unidad
      interval_config <- switch(
        as.character(intervalo_aplicado()),
        "1min" = list(interval = 1, unit = "minutes"),
        "30min" = list(interval = 30, unit = "minutes"),
        "1h" = list(interval = 1, unit = "hours"),
        "6h" = list(interval = 6, unit = "hours"),
        "12h" = list(interval = 12, unit = "hours"),
        list(interval = 30, unit = "minutes")  # Default
      )
      
      # Suprimir todos los mensajes de Plotly con capture.output anidado
      invisible(capture.output({
        invisible(capture.output({
          resultado <- suppressMessages(suppressWarnings({
            makeActivityPattern(
              subRawData(), 
              top_n = 10,
              interval = interval_config$interval,
              unit = interval_config$unit,
              interactive = TRUE,
              activity_pattern = NULL
            )
          }))
        }, type = "message"))
      }, type = "output"))
      
      resultado
    }
  })
  
  # Mapa 4.4: Ubicación de cámaras
  output$map <- renderLeaflet({
    # Validar que hay datos filtrados
    if (nrow(subRawData()) == 0) {
      # Mostrar mapa por defecto de Colombia con mensaje
      leaflet() %>%
        addTiles() %>%
        setView(lng = -74.0721, lat = 4.7110, zoom = 5) %>%
        addControl(html = "<div style='background-color: white; padding: 10px; border-radius: 5px;'>
                          <strong>Seleccione una corporación y/o evento para ver las ubicaciones</strong></div>",
                   position = "topright")
    } else {
      # Usar valores aplicados
      evento_actual <- evento_aplicado()
      corporacion_actual <- corporacion_aplicada()
      
      # Generar descripción de la vista actual para el mapa
      vista_descripcion <- paste(
        ifelse(corporacion_actual == "TODAS", "Todas las corporaciones", corporacion_actual),
        ifelse(evento_actual == "TODOS", "(todos los períodos)", paste0("(período ", evento_actual, ")"))
      )
      
      # Crear mapa base
      mapa <- makeMapLeaflet(
        subSitesData(),
        subTableData(), 
        nsites(), 
        bounds, 
        vista_descripcion
      )
      
      # Agregar polígono de corporación si está disponible el shapefile y se seleccionó una CAR específica
      if (!is.null(car_shapefile) && !is.null(corporacion_actual) && 
          corporacion_actual != "" && corporacion_actual != "TODAS") {
        
        # Buscar polígono de la corporación en el shapefile
        # Intentar diferentes nombres de columnas comunes
        columna_car <- NULL
        if ("NOMBRE_CAR" %in% names(car_shapefile)) {
          columna_car <- "NOMBRE_CAR"
        } else if ("CAR" %in% names(car_shapefile)) {
          columna_car <- "CAR"
        } else if ("Nombre" %in% names(car_shapefile)) {
          columna_car <- "Nombre"
        } else if ("NOMBRE" %in% names(car_shapefile)) {
          columna_car <- "NOMBRE"
        } else if ("corporacion" %in% names(car_shapefile)) {
          columna_car <- "corporacion"
        }
        
        if (!is.null(columna_car)) {
          # Filtrar polígono de la corporación seleccionada
          car_poligono <- car_shapefile[car_shapefile[[columna_car]] == corporacion_actual, ]
          
          # Si se encontró el polígono, agregarlo al mapa
          if (nrow(car_poligono) > 0) {
            mapa <- mapa %>%
              addPolygons(
                data = car_poligono,
                fillColor = "#ADD8E6",      # Azul claro
                fillOpacity = 0.25,         # 25% de opacidad para ver el mapa debajo
                color = "#4682B4",          # Borde azul acero
                weight = 2.5,               # Grosor del borde
                opacity = 0.8,              # Opacidad del borde
                dashArray = "5, 5",         # Línea punteada para mejor visibilidad
                group = "Límite CAR",
                label = paste0("Límite jurisdiccional: ", corporacion_actual),
                labelOptions = labelOptions(
                  style = list("font-weight" = "bold", "font-size" = "14px"),
                  textsize = "14px",
                  direction = "auto"
                ),
                highlightOptions = highlightOptions(
                  weight = 4,
                  color = "#0066CC",
                  fillOpacity = 0.4,
                  bringToFront = FALSE
                )
              ) %>%
              addLayersControl(
                overlayGroups = c("Límite CAR"),
                options = layersControlOptions(collapsed = FALSE)
              )
          }
        }
      }
      
      mapa
    }
  })
  
  # Selector de imágenes favoritas para galería
  favorite_images <- reactive({
    # Usar valores aplicados
    corporacion_actual <- corporacion_aplicada()
    
    # Lógica para seleccionar imágenes según filtros:
    # - Si corporación es "TODAS" o vacío → carpeta "favorites/General/"
    # - Si corporación es específica → carpeta de la corporación por nombre
    
    if (is.null(corporacion_actual) || corporacion_actual == "" || corporacion_actual == "TODAS") {
      # Vista consolidada: buscar en carpeta General
      carpeta_general <- file.path("www", "images", "favorites", "General")
      
      if (dir.exists(carpeta_general)) {
        imgs <- list.files(
          carpeta_general,
          pattern = IMG_PATTERN,
          recursive = FALSE,
          full.names = TRUE
        )
        # Convertir rutas absolutas a relativas para web
        imgs_rel <- gsub("^www/", "", imgs)
        
        # Validar que las imágenes existan
        imgs_validas <- imgs_rel[file.exists(file.path("www", imgs_rel))]
        return(imgs_validas)
      } else {
        # Si no existe carpeta General, buscar recursivamente en todas las carpetas
        imgs <- list.files(
          file.path("www", "images", "favorites"),
          pattern = IMG_PATTERN,
          recursive = TRUE,
          full.names = TRUE
        )
        imgs_rel <- gsub("^www/", "", imgs)
        imgs_validas <- imgs_rel[file.exists(file.path("www", imgs_rel))]
        return(imgs_validas)
      }
    } else {
      # Corporación específica: buscar en carpeta de la corporación por nombre
      carpeta_corporacion <- file.path("www", "images", "favorites", corporacion_actual)
      
      if (dir.exists(carpeta_corporacion)) {
        imgs <- list.files(carpeta_corporacion, pattern = IMG_PATTERN, full.names = TRUE)
        imgs_rel <- gsub("^www/", "", imgs)
        imgs_validas <- imgs_rel[file.exists(file.path("www", imgs_rel))]
        return(imgs_validas)
      } else {
        # Fallback: buscar en carpeta General si no existe carpeta específica de la corporación
        carpeta_general <- file.path("www", "images", "favorites", "General")
        
        if (dir.exists(carpeta_general)) {
          imgs <- list.files(
            carpeta_general,
            pattern = IMG_PATTERN,
            recursive = FALSE,
            full.names = TRUE
          )
          imgs_rel <- gsub("^www/", "", imgs)
          imgs_validas <- imgs_rel[file.exists(file.path("www", imgs_rel))]
          return(imgs_validas)
        } else {
          return(character(0))
        }
      }
    }
  })
  
  # UI condicional para galería de imágenes
  output$galeria_ui <- renderUI({
    # Verificar si hay datos aplicados
    if (!datos_actuales$datos_filtrados || nrow(subRawData()) == 0) {
      # Mostrar mensaje inicial
      return(
        tags$div(
          style = "text-align: center; padding: 80px 20px; color: #7f8c8d;",
          tags$p(
            style = "font-size: 16px; margin: 0;",
            "Seleccione una corporación y/o evento para ver las imágenes destacadas"
          )
        )
      )
    } else {
      # Verificar si hay imágenes disponibles
      imgs <- favorite_images()
      
      if (is.null(imgs) || length(imgs) == 0) {
        # Mostrar mensaje de no imágenes disponibles
        return(
          tags$div(
            style = "text-align: center; padding: 80px 20px; color: #7f8c8d;",
            tags$p(
              style = "font-size: 16px; margin-bottom: 10px;",
              "📷 No hay imágenes destacadas disponibles para esta selección"
            ),
            tags$p(
              style = "font-size: 14px; color: #95a5a6; margin: 0;",
              "Las imágenes deben estar ubicadas en: www/images/favorites/General/ o www/images/favorites/[corporacion]/"
            )
          )
        )
      } else {
        # Mostrar carrusel de imágenes
        return(slickROutput("cameraTrapImages", height = "240px"))
      }
    }
  })
  
  output$cameraTrapImages <- renderSlickR({
    imgs <- favorite_images()
    
    # Validar que existan imágenes
    if (is.null(imgs) || length(imgs) == 0) {
      return(NULL)
    }
    
    # Filtrar imágenes que realmente existen
    imgs_existentes <- imgs[file.exists(file.path("www", imgs))]
    
    if (length(imgs_existentes) == 0) {
      return(NULL)
    }
    
    # Limitar cantidad de imágenes al máximo permitido
    if (length(imgs_existentes) > MAX_FAVORITES) {
      imgs_existentes <- sample(imgs_existentes, MAX_FAVORITES)
    }
    
    # Configurar carrusel con validación de errores
    tryCatch({
      slickR::slickR(imgs_existentes, slideId = "favoriteSlider") + 
        slickR::settings(
          slidesToShow = 5,
          slidesToScroll = 5,
          autoplay = TRUE,
          autoplaySpeed = 4000,
          dots = TRUE,
          arrows = TRUE,
          adaptiveHeight = FALSE,
          infinite = TRUE,
          pauseOnHover = TRUE
        )
    }, error = function(e) {
      message("Error al crear carrusel: ", e$message)
      return(NULL)
    })
  })
  
  # =============================================================================
  # OUTPUTS: METADATOS Y TEXTO INFORMATIVO
  # =============================================================================
  
  # =============================================================================
  # OUTPUTS: METADATOS Y TEXTO INFORMATIVO
  # =============================================================================
  
  # Administrador / Colector de la corporación
  output$collector <- renderText({
    if (nrow(subTableData()) == 0) {
      return("–")
    }
    
    # Usar corporación aplicada
    corporacion_actual <- corporacion_aplicada()
    
    # Si es "TODAS" o vacío, mostrar "Múltiples corporaciones - escala nacional"
    if (is.null(corporacion_actual) || corporacion_actual == "" || corporacion_actual == "TODAS") {
      return("Múltiples corporaciones - escala nacional")
    }
    
    # Mostrar el nombre de la corporación seleccionada
    return(as.character(corporacion_actual))
  })
  
  # Rango temporal del muestreo
  output$dateRange <- renderText({
    if (nrow(subRawData()) == 0) {
      return("–")
    }
    d <- extract_date_ymd(subRawData())
    if (!length(d) || all(is.na(d))) return("–")
    paste0(min(d, na.rm = TRUE), " - ", max(d, na.rm = TRUE))
  })
  
  output$project_name <- renderUI({
    # Usar valores aplicados
    evento_actual <- evento_aplicado()
    corporacion_actual <- corporacion_aplicada()
    
    # Verificar si hay selección válida
    if (is.null(evento_actual) || is.null(corporacion_actual) || 
        (evento_actual == "" && corporacion_actual == "")) {
      return(tags$span(
        style = "text-align: center !important; display: inline; color: #7f8c8d;",
        "Por favor seleccione corporación y/o evento para visualizar datos"
      ))
    }
    
    # Generar título descriptivo según filtros activos
    titulo_corporacion <- if (is.null(corporacion_actual) || corporacion_actual == "" || corporacion_actual == "TODAS") {
      "Todas las corporaciones"
    } else {
      corporacion_actual  # Mostrar nombre de la CAR (ej: "CORPOCALDAS")
    }
    
    # Mostrar subproject_name directamente (ejemplo: 2024_2, 2025_1)
    titulo_evento <- if (is.null(evento_actual) || evento_actual == "" || evento_actual == "TODOS") {
      "Todos los eventos"
    } else {
      evento_actual  # Mostrar el valor directo (2024_2, no "Evento 2024_2")
    }
    
    tags$span(
      style = "text-align: center !important; display: inline;",
      paste0(titulo_corporacion, " - ", titulo_evento)
    )
  })
  
  # =============================================================================
  # OUTPUT: TABLA DE INDICADORES CONSOLIDADOS
  # =============================================================================
  # Arquitectura Parquet: Siempre muestra tabla consolidada por períodos
  # No hay vistas individuales de eventos en esta versión
  
  output$indicadores_table_ui <- renderUI({
    tagList(
      tags$div(
        style = "overflow-x: auto; margin-bottom: 10px;",
        DT::dataTableOutput("indicadores_consolidado_table")
      )
    )
  })
  
  # Tabla DT con indicadores por período
  output$indicadores_consolidado_table <- DT::renderDataTable({
    evento_actual <- evento_aplicado()
    corporacion_actual <- corporacion_aplicada()
    
    # Validar si hay selección
    if (is.null(evento_actual) || is.null(corporacion_actual) || 
        (evento_actual == "" && corporacion_actual == "")) {
      # Retornar tabla vacía con mensaje
      mensaje_df <- data.frame(
        Mensaje = "Seleccione una corporación y/o evento para ver los indicadores consolidados"
      )
      return(DT::datatable(
        mensaje_df,
        options = list(
          dom = 't',
          ordering = FALSE,
          paging = FALSE,
          info = FALSE
        ),
        rownames = FALSE,
        colnames = c("Sin seleccion" = "Mensaje"),
        selection = 'none'
      ))
    }
    
    # Aplicar filtros a los datos
    sites_datos <- datos_actuales$tableSites
    iavh_datos <- datos_actuales$iavhdata
    
    # Filtro por corporación primero (más selectivo)
    if (corporacion_actual != "TODAS") {
      # Corporacion es string, no requiere conversión numérica
      # IMPORTANTE: tableSites usa 'departamento' (renombrado desde Corporacion)
      if ("departamento" %in% names(sites_datos)) {
        sites_datos <- sites_datos %>% dplyr::filter(departamento == corporacion_actual)
      }
      if ("Corporacion" %in% names(iavh_datos)) {
        iavh_datos <- iavh_datos %>% dplyr::filter(Corporacion == corporacion_actual)
      }
    }
    
    # Filtro por evento después
    if (evento_actual != "TODOS") {
      sites_datos <- sites_datos %>% dplyr::filter(subproject_name == evento_actual)
      iavh_datos <- iavh_datos %>% dplyr::filter(subproject_name == evento_actual)
    }
    
    # Calcular indicadores por período
    mostrar_consolidado <- (evento_actual == "TODOS")
    
    tabla_periodos <- calcular_indicadores_por_periodo(
      sites_datos,
      iavh_datos,
      mostrar_consolidado = mostrar_consolidado
    )
    
    # Detectar si solo hay 1 período (sin fila CONSOLIDADO)
    num_filas <- nrow(tabla_periodos)
    
    # CASO 1: Evento específico seleccionado (SIN columna Evento, formato horizontal)
    # Solo ocultar columna si el usuario seleccionó UN evento específico (no "TODOS")
    if (num_filas == 1 && evento_actual != "TODOS") {
      # Eliminar columna Periodo para vista de evento específico
      tabla_sin_periodo <- tabla_periodos %>% dplyr::select(-Periodo)
      
      return(DT::datatable(
        tabla_sin_periodo,
        options = list(
          pageLength = 1,
          searching = FALSE,
          ordering = FALSE,
          paging = FALSE,
          info = FALSE,
          dom = 't',
          scrollX = FALSE,
          scrollY = FALSE,
          autoWidth = TRUE,
          columnDefs = list(
            list(className = 'dt-center', targets = 0:8)
          )
        ),
        rownames = FALSE,
        colnames = c(
          "🗂️ Imágenes" = "Imagenes",
          "📸 Cámaras" = "Camaras",
          "📅 Trampas/noche" = "Dias_camara",
          "🏞️ Especies" = "Especies",
          "🐆 Mamíferos" = "Mamiferos",
          "🦅 Aves" = "Aves",
          "🌿 Hill 1" = "Hill1",
          "🌱 Hill 2" = "Hill2",
          "🌳 Hill 3" = "Hill3"
        ),
        class = 'cell-border stripe hover compact',
        selection = 'none',
        escape = FALSE
      ) %>%
        DT::formatStyle(
          columns = c("🗂️ Imágenes", "📸 Cámaras", "📅 Trampas/noche", "🏞️ Especies", 
                      "🐆 Mamíferos", "🦅 Aves"),
          textAlign = 'center'
        ) %>%
        DT::formatCurrency(c("🗂️ Imágenes", "📸 Cámaras", "📅 Trampas/noche", "🏞️ Especies", 
                             "🐆 Mamíferos", "🦅 Aves"),
                           currency = "",
                           digits = 0,
                           mark = ",") %>%
        DT::formatRound(c("🌿 Hill 1", "🌱 Hill 2", "🌳 Hill 3"),
                        digits = 2,
                        mark = ","))
    }
    
    # CASO 2: "Todos los eventos" (CON columna Evento - siempre mostrar)
    # Incluye: 1 evento disponible o múltiples eventos (con/sin CONSOLIDADO)
    DT::datatable(
      tabla_periodos,
      options = list(
        pageLength = nrow(tabla_periodos),
        searching = FALSE,
        ordering = FALSE,
        paging = FALSE,
        info = FALSE,
        dom = 't',
        scrollX = FALSE,
        scrollY = FALSE,
        autoWidth = TRUE,
        columnDefs = list(
          list(className = 'dt-center', targets = 1:9),
          list(className = 'dt-left', targets = 0),
          list(width = '12%', targets = 0),
          list(width = '9.7%', targets = 1:9)
        ),
        language = list(
          emptyTable = "No hay datos disponibles",
          zeroRecords = "No se encontraron eventos"
        )
      ),
      rownames = FALSE,
      colnames = c(
        "Evento" = "Periodo",
        "🗂️ Imágenes" = "Imagenes",
        "📸 Cámaras" = "Camaras",
        "📅 Trampas/noche" = "Dias_camara",
        "🏞️ Especies" = "Especies",
        "🐆 Mamíferos" = "Mamiferos",
        "🦅 Aves" = "Aves",
        "🌿 Hill 1" = "Hill1",
        "🌱 Hill 2" = "Hill2",
        "🌳 Hill 3" = "Hill3"
      ),
      class = 'cell-border stripe hover compact',
      selection = 'none',
      escape = FALSE
    ) %>%
      DT::formatStyle(
        'Evento',
        target = 'row',
        fontWeight = DT::styleEqual('CONSOLIDADO', 'bold'),
        backgroundColor = DT::styleEqual('CONSOLIDADO', '#e8f4f8'),
        color = DT::styleEqual('CONSOLIDADO', '#1a5490')
      ) %>%
      DT::formatCurrency(c("🗂️ Imágenes", "📸 Cámaras", "📅 Trampas/noche", "🏞️ Especies", 
                           "🐆 Mamíferos", "🦅 Aves"),
                         currency = "",
                         digits = 0,
                         mark = ",") %>%
      DT::formatRound(c("🌿 Hill 1", "🌱 Hill 2", "🌳 Hill 3"),
                      digits = 2,
                      mark = ",")
  })
  
  # =============================================================================
  # OUTPUTS: INDICADORES NUMÉRICOS (VALUE BOXES)
  # =============================================================================
  
  output$stat_images <- renderText({
    format(subTableData()$n, big.mark = ",", scientific = FALSE)
  })
  
  output$stat_cameras <- renderText({
    format(subTableData()$ndepl, big.mark = ",", scientific = FALSE)
  })
  
  output$stat_effort <- renderText({
    format(subTableData()$effort, big.mark = ",", scientific = FALSE)
  })
  
  output$stat_species <- renderText({
    format(subTableData()$ospTot, big.mark = ",", scientific = FALSE)
  })
  
  output$stat_mammals <- renderText({
    format(subTableData()$ospMamiferos, big.mark = ",", scientific = FALSE)
  })
  
  output$stat_birds <- renderText({
    format(subTableData()$ospAves, big.mark = ",", scientific = FALSE)
  })
  
  # =============================================================================
  # OUTPUTS: ÍNDICES DE DIVERSIDAD (NÚMEROS DE HILL)
  # =============================================================================
  
  output$stat_hill1 <- renderText({
    tryCatch({
      indice <- calcular_numeros_hill(subRawData(), q = 0)
      if (is.na(indice)) return("—")
      format(indice, big.mark = ",", scientific = FALSE)
    }, error = function(e) {
      "—"
    })
  })
  
  output$stat_hill2 <- renderText({
    tryCatch({
      indice <- calcular_numeros_hill(subRawData(), q = 1)
      if (is.na(indice)) return("—")
      format(round(indice, 2), big.mark = ",", scientific = FALSE)
    }, error = function(e) {
      "—"
    })
  })
  
  output$stat_hill3 <- renderText({
    tryCatch({
      indice <- calcular_numeros_hill(subRawData(), q = 2)
      if (is.na(indice)) return("—")
      format(round(indice, 2), big.mark = ",", scientific = FALSE)
    }, error = function(e) {
      "—"
    })
  })
  
  # =============================================================================
  # OUTPUTS: EXPORTACIÓN DE DASHBOARD
  # =============================================================================
  
  observeEvent(input$captureScreen, {
    # Generar nombre descriptivo: Dashboard_Corporacion_Evento_Timestamp.png
    corporacion_nombre <- if (is.null(input$corporacion) || input$corporacion == "" || input$corporacion == "TODAS") {
      "Todas_corporaciones"
    } else {
      gsub(" ", "_", input$corporacion)
    }
    
    evento_nombre <- if (is.null(input$evento) || input$evento == "" || input$evento == "TODOS") {
      "Todos_eventos"
    } else {
      gsub(" ", "_", input$evento)
    }
    
    timestamp <- format(Sys.time(), "%Y%m%d_%H%M%S")
    filename <- paste0("Dashboard_", corporacion_nombre, "_", evento_nombre, "_", timestamp)
    
    session$sendCustomMessage("capture_dashboard", list(filename = filename))
  })
  
  # Control de notificaciones de estado
  observeEvent(input$capture_status, {
    if (grepl("^error:", input$capture_status)) {
      showNotification(
        paste("Error al capturar dashboard:", gsub("^error: ", "", input$capture_status)),
        type = "error",
        duration = 5
      )
    } else if (input$capture_status == "exitoso") {
      showNotification(
        "Dashboard exportado exitosamente como imagen PNG",
        type = "message",
        duration = 3
      )
    }
  }, ignoreInit = TRUE)
}

# ===============================================================================
# CÓDIGO JAVASCRIPT: CAPTURA DE PANTALLA CON HTML2CANVAS
# ===============================================================================
# Utiliza html2canvas para renderizar el dashboard completo como imagen PNG
# y generar descarga automática del archivo.
# NOTA: html2canvas tiene limitaciones con mapas Leaflet - puede no capturar
# correctamente los tiles del mapa base ni los polígonos vectoriales.
# ===============================================================================

js_capture <- "
Shiny.addCustomMessageHandler('capture_dashboard', function(message) {
  // Mostrar notificación de inicio
  Shiny.setInputValue('capture_status', 'iniciando', {priority: 'event'});
  
  // Obtener el elemento principal del dashboard (body completo)
  var element = document.body;
  
  // Configuración de html2canvas para máxima calidad
  var options = {
    scale: 2,                    // Resolución 2x (mejor calidad)
    useCORS: true,               // Permitir imágenes de otros dominios
    allowTaint: true,            // Permitir contenido externo
    backgroundColor: '#ffffff',  // Fondo blanco
    logging: false,              // Desactivar logs en consola
    windowWidth: element.scrollWidth,
    windowHeight: element.scrollHeight,
    scrollX: 0,
    scrollY: 0,
    onclone: function(clonedDoc) {
      // Ajustar elementos clonados antes de captura
      var clonedBody = clonedDoc.body;
      clonedBody.style.width = element.scrollWidth + 'px';
      clonedBody.style.height = element.scrollHeight + 'px';
    }
  };
  
  // Ejecutar captura
  html2canvas(element, options).then(function(canvas) {
    try {
      // Convertir canvas a imagen PNG
      var imgData = canvas.toDataURL('image/png');
      
      // Crear link de descarga invisible
      var link = document.createElement('a');
      link.href = imgData;
      link.download = message.filename + '.png';
      link.style.display = 'none';
      
      // Añadir al DOM, ejecutar descarga y limpiar
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // Notificar éxito a Shiny
      Shiny.setInputValue('capture_status', 'exitoso', {priority: 'event'});
    } catch(error) {
      // Notificar error a Shiny
      Shiny.setInputValue('capture_status', 'error: ' + error.message, {priority: 'event'});
    }
  }).catch(function(error) {
    // Notificar error de html2canvas
    Shiny.setInputValue('capture_status', 'error: ' + error.message, {priority: 'event'});
  });
});
"

# ===============================================================================
# INICIALIZACIÓN DE LA APLICACIÓN SHINY
# ===============================================================================

shinyApp(
  ui = tagList(
    dashboardPage(
      dashboardHeader(disable = TRUE),
      dashboardSidebar(disable = TRUE),
      body
    ),
    # Inyectar código JavaScript para captura de pantalla
    tags$script(HTML(js_capture))
  ), 
  server = server
)




