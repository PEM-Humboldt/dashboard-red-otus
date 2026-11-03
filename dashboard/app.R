# Dashboard Red OTUS 2026
# Aplicación Shiny unificada para consulta por proyectos y corporaciones.
# Desarrollo: Cristian C. Acevedo, Ingeniero de Soluciones.
# Supervisión: Angélica Diaz Pulido, Investigador Adjunto, Centro Estudios
# Socioecológicos y Cambio Global, Dirección de Conocimiento,
# Instituto de Investigación de Recursos Biológicos Alexander von Humboldt.
# Versión: v2026.1.0. Licencia: MIT; consulte LICENSE en la raíz del proyecto.

# ===============================================================================
# LIBRERÍAS REQUERIDAS
# ===============================================================================

.dashboard_app_packages <- c(
  "arrow", "dplyr", "DT", "ggplot2", "htmltools", "leaflet", "lubridate", "openxlsx", "plotly",
  "scales", "sf", "shiny", "shinydashboard", "shinyjs", "slickR"
)
.dashboard_missing_packages <- .dashboard_app_packages[
  !vapply(.dashboard_app_packages, requireNamespace, logical(1), quietly = TRUE)
]

if (length(.dashboard_missing_packages) > 0) {
  stop(
    "Faltan paquetes requeridos por app.R: ",
    paste(.dashboard_missing_packages, collapse = ", "),
    ". Instálelos antes de iniciar el dashboard.",
    call. = FALSE
  )
}

rm(.dashboard_app_packages, .dashboard_missing_packages)

library(shiny)
library(shinydashboard)
library(shinyjs)

library(plotly)
library(leaflet)
library(slickR)
library(DT)

# ===============================================================================
# CONFIGURACIÓN GLOBAL
# ===============================================================================

options(
  plotly.message = FALSE,
  plotly.warning = FALSE,
  plotly.verbose = FALSE
)

# Localiza la carpeta de la aplicación en RStudio, Rscript o Shiny Server.
resolver_directorio_dashboard <- function() {
  archivos_origen <- vapply(
    sys.frames(),
    function(frame) if (is.null(frame$ofile)) "" else as.character(frame$ofile),
    character(1)
  )
  argumento_archivo <- grep("^--file=", commandArgs(FALSE), value = TRUE)
  if (length(argumento_archivo) > 0) {
    archivos_origen <- c(archivos_origen, sub("^--file=", "", argumento_archivo[[1]]))
  }

  candidatos <- c(
    dirname(archivos_origen[nzchar(archivos_origen)]),
    getwd(),
    file.path(getwd(), "dashboard")
  )
  candidatos <- unique(vapply(
    candidatos,
    function(path) normalizePath(path, winslash = "/", mustWork = FALSE),
    character(1)
  ))
  valido <- candidatos[file.exists(file.path(candidatos, "dashboard_functions.R"))]
  if (length(valido) == 0) {
    stop("No fue posible localizar los archivos de la aplicación 2026.", call. = FALSE)
  }
  valido[[1]]
}

.dashboard_dir <- resolver_directorio_dashboard()
source(file.path(.dashboard_dir, "dashboard_functions.R"))

.data_path_config <- Sys.getenv("RED_OTUS_DATA_PATH", unset = "")
if (!nzchar(trimws(.data_path_config))) {
  .data_path_config <- file.path(.dashboard_dir, "data")
} else if (!grepl("^([A-Za-z]:[/\\\\]|/|\\\\\\\\)", .data_path_config)) {
  .data_path_config <- file.path(.dashboard_dir, .data_path_config)
}
.data_path_config <- normalizePath(.data_path_config, winslash = "/", mustWork = FALSE)

options(
  red_otus.data_path = .data_path_config,
  red_otus.warn_quality = FALSE
)

# Valor de respaldo; se reemplaza automáticamente si los insumos incluyen
# `initiative_name`, `nombre_iniciativa` o `iniciativa`.
NOMBRE_INICIATIVA <- "Red OTUS"

# ===============================================================================
# CARGA DE DATOS
# ===============================================================================
eventos_disponibles <- obtener_eventos_disponibles()

if (length(eventos_disponibles) == 0) {
  stop("Datos 2026 no encontrados en: ", getOption("red_otus.data_path"), "\n",
       "Ejecute el procesador mediante processing/launch_gui.bat.")
}

message("Cargando la publicación 2026 desde: ", getOption("red_otus.data_path"))
datos_iniciales <- cargar_datos()

if (is.null(datos_iniciales)) {
  stop("Error crítico al cargar archivos parquet.")
}

intervalos_manifest <- as.integer(unlist(datos_iniciales$manifest$independence_minutes))
intervalos_catalogo <- c(
  "Sin filtro temporal" = 0L,
  "30 minutos" = 30L,
  "1 hora" = 60L,
  "24 horas" = 1440L
)
intervalos_catalogo <- intervalos_catalogo[intervalos_catalogo %in% intervalos_manifest]
if (length(intervalos_catalogo) == 0) stop("La publicación no contiene intervalos de análisis válidos.", call. = FALSE)
intervalos_choices <- stats::setNames(
  c("sin_filtro", "30min", "1h", "24h")[match(intervalos_catalogo, c(0L, 30L, 60L, 1440L))],
  names(intervalos_catalogo)
)
INTERVALO_DEFAULT <- if ("30min" %in% intervalos_choices) "30min" else unname(intervalos_choices[[1]])

for (datos_meta in list(datos_iniciales$projects, datos_iniciales$iavhdata)) {
  columna_iniciativa <- intersect(
    c("initiative_name", "nombre_iniciativa", "iniciativa"),
    names(datos_meta)
  )
  if (length(columna_iniciativa) > 0) {
    candidatos <- as.character(datos_meta[[columna_iniciativa[[1]]]])
    candidatos <- candidatos[!is.na(candidatos) & nzchar(trimws(candidatos))]
    if (length(candidatos) > 0) {
      NOMBRE_INICIATIVA <- trimws(candidatos[[1]])
      break
    }
  }
}
if (!is.null(datos_iniciales$manifest$dashboard_title) &&
    nzchar(trimws(as.character(datos_iniciales$manifest$dashboard_title)))) {
  NOMBRE_INICIATIVA <- trimws(as.character(datos_iniciales$manifest$dashboard_title))
}

# Límite jurisdiccional usado en la vista de corporaciones.
message("🗺️ Cargando shapefile de corporaciones...")
shapefile_path <- file.path(.dashboard_dir, "spatial", "CAR_MPIO.shp")
if (file.exists(shapefile_path)) {
  car_shapefile <- sf::st_read(shapefile_path, quiet = TRUE)
  car_shapefile <- sf::st_transform(car_shapefile, 4326)
} else {
  warning("Shapefile de CARs no encontrado en: ", shapefile_path)
  car_shapefile <- NULL
}

# ===============================================================================
# PREPARACIÓN DE DATOS PARA DASHBOARD
# ===============================================================================

iavhdata <- datos_iniciales$iavhdata
tableSites <- datos_iniciales$tableSites
projects_data <- datos_iniciales$projects
deployments_data <- datos_iniciales$deployments
gold_data <- datos_iniciales$gold

# Normalizar campos categóricos usados por los filtros.
if ("subproject_name" %in% names(iavhdata)) {
  iavhdata$subproject_name <- as.character(iavhdata$subproject_name)
}

if ("subproject_name" %in% names(tableSites)) {
  tableSites$subproject_name <- as.character(tableSites$subproject_name)
}

if ("subproject_name" %in% names(deployments_data)) {
  deployments_data$subproject_name <- as.character(deployments_data$subproject_name)
}

if ("Corporacion" %in% names(deployments_data)) {
  deployments_data$Corporacion <- as.character(deployments_data$Corporacion)
}

if ("Corporacion" %in% names(iavhdata)) {
  iavhdata$Corporacion <- as.character(iavhdata$Corporacion)
}

if ("Corporacion" %in% names(tableSites)) {
  tableSites$Corporacion <- as.character(tableSites$Corporacion)
}

# Alias requerido por componentes de presentación.
if ("subproject_name" %in% names(iavhdata) && !("evento_muestreo" %in% names(iavhdata))) {
  iavhdata$evento_muestreo <- iavhdata$subproject_name
}

if ("subproject_name" %in% names(tableSites) && !("evento_muestreo" %in% names(tableSites))) {
  tableSites$evento_muestreo <- tableSites$subproject_name
}

# ===============================================================================
# PREPARACIÓN DE SELECTORES UI
# ===============================================================================

# Selector de eventos (períodos de muestreo) - compartido por ambos modos
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

# Selector de corporaciones para la vista territorial.
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
  # Respaldo para publicaciones históricas sin la columna Corporacion.
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

# Selector de proyectos con etiqueta legible y búsqueda por ID o nombre.
if ("project_id" %in% names(iavhdata) && "project_short_name" %in% names(iavhdata)) {
  proyectos_df <- iavhdata %>%
    dplyr::select(project_id, project_short_name) %>%
    dplyr::distinct() %>%
    dplyr::filter(!is.na(project_id) & !is.na(project_short_name) &
                  project_id != "" & project_short_name != "")

  proyectos_unicos <- proyectos_df$project_id
  proyectos_nombres_busqueda <- gsub("[_-]+", " ", proyectos_df$project_short_name)
  proyectos_nombres_busqueda <- trimws(gsub("\\s+", " ", proyectos_nombres_busqueda))
  proyectos_labels <- paste(proyectos_df$project_id, proyectos_nombres_busqueda, sep = " · ")

  orden <- order(proyectos_labels)
  proyectos_unicos <- proyectos_unicos[orden]
  proyectos_labels <- proyectos_labels[orden]
} else {
  proyectos_unicos <- character(0)
  proyectos_labels <- character(0)
}

project_choices <- c("", "TODOS", proyectos_unicos)
names(project_choices) <- c("-- Seleccione un proyecto --", "Todos los proyectos", proyectos_labels)

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
    tags$link(rel = "stylesheet", type = "text/css", href = "css/dashboard.css"),
    # Librería html2canvas para captura de pantalla
    tags$script(src = "js/html2canvas.min.js")
  ),

  # ===========================================================================
  # SECCIÓN 1: ENCABEZADO
  # ===========================================================================
  # Título del reporte y nombre dinámico de la corporación/proyecto seleccionado
  fluidRow(
    column(12,
      box(
        width = NULL,
        title = NULL,
        tags$div(
          class = "section-box-title",
          tags$h1(
            class = "report-title",
            paste0("Reporte de Datos de Fototrampeo - ", NOMBRE_INICIATIVA)
          ),
          tags$h2(
            class = "report-subtitle",
            uiOutput("entity_label_ui", inline = TRUE),
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
        title = "1. Parámetros de visualización",
        class = "filters-section",

        # Alternador de modo: Corporaciones <-> Proyectos
        fluidRow(
          column(12,
            tags$div(
              class = "filter-item mode-toggle-item",
              tags$label(class = "filter-label", `for` = "modo_vista", "Tipo de vista"),
              radioButtons(
                "modo_vista",
                NULL,
                choices = c(
                  "Corporaciones (CAR)" = "corporaciones",
                  "Proyectos" = "proyectos"
                ),
                selected = "corporaciones",
                inline = TRUE
              )
            )
          )
        ),

        fluidRow(
          # Selector: Corporación o Proyecto según el modo activo (PRIMERO)
          column(4,
            tags$div(
              class = "filter-item",
              conditionalPanel(
                condition = "input.modo_vista == 'corporaciones'",
                tags$label(class = "filter-label", `for` = "corporacion", "Corporación ambiental regional (CAR)"),
                tags$div(
                  class = "entity-search-select",
                  selectizeInput(
                    "corporacion",
                    NULL,
                    choices = corporacion_choices,
                    selected = "",  # Inicio sin selección
                    options = list(
                      placeholder = "Escriba una sigla o nombre…",
                      create = FALSE,
                      maxOptions = 1000,
                      closeAfterSelect = TRUE,
                      openOnFocus = TRUE,
                      selectOnTab = TRUE,
                      searchField = c("label", "text", "value")
                    )
                  )
                )
              ),
              conditionalPanel(
                condition = "input.modo_vista == 'proyectos'",
                tags$label(class = "filter-label", `for` = "project", "Proyecto"),
                tags$div(
                  class = "entity-search-select",
                  selectizeInput(
                    "project",
                    NULL,
                    choices = project_choices,
                    selected = "",  # Inicio sin selección
                    options = list(
                      placeholder = "Escriba un ID o nombre…",
                      create = FALSE,
                      maxOptions = 1000,
                      closeAfterSelect = TRUE,
                      openOnFocus = TRUE,
                      selectOnTab = TRUE
                    )
                  )
                )
              )
            )
          ),

          # Selector: Evento de muestreo (SEGUNDO) - compartido por ambos modos
          column(4,
            tags$div(
              class = "filter-item",
              tags$label(class = "filter-label", `for` = "evento", "Evento de muestreo"),
              selectInput(
                "evento",
                NULL,
                choices = eventos_choices,
                selected = ""  # Inicio sin selección
              )
            )
          ),

          # Selector: Filtro de registros independientes (TERCERO) - compartido
          column(4,
            tags$div(
              class = "filter-item",
              tags$label(
                class = "filter-label",
                `for` = "duplicateInterval",
                "Intervalo entre registros independientes",
                tags$span(
                  class = "info-tooltip",
                  title = "Elimina detecciones repetidas del mismo taxón en el mismo sitio dentro del intervalo seleccionado. 30 minutos es el estándar ecológico recomendado. Útil para eliminar ráfagas fotográficas y re-visitas cercanas.",
                  "ℹ️"
                )
              ),
              selectInput(
                "duplicateInterval",
                NULL,
                choices = intervalos_choices,
                selected = INTERVALO_DEFAULT
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
                tags$span(class = "button-label", "Aplicar selección"),
                icon = icon("check-circle"),
                class = "btn-primary btn-apply-selection",
                disabled = TRUE  # Iniciar deshabilitado
              ),
              actionButton(
                "limpiarSeleccion",
                tags$span(class = "button-label", "Limpiar selección"),
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
        # Información de la corporación/proyecto (Administrador y Fechas)
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
        uiOutput("indicadores_table_ui"),
        tags$div(
          class = "download-button-container",
          downloadButton(
            "downloadIndicatorsTable",
            "Descargar indicadores (CSV)",
            class = "btn-primary btn-sm"
          ) %>% tagAppendAttributes(disabled = NA)
        )
      )
    )
  ),

  # ===========================================================================
  # SECCIÓN 4: MAPA Y GRÁFICOS DE OPERACIÓN Y BIODIVERSIDAD
# ===========================================================================
  fluidRow(
    column(6,
      box(
        width = NULL,
        class = "box-xl graph-panel",
        title = tags$span(
          "2.1. Mapa de ubicación de cámaras trampa",
          tags$span(
            class = "info-tooltip graph-info-tooltip",
            title = paste(
              "Muestra la ubicación de las cámaras instaladas para la entidad y el evento seleccionados.",
              "Cada marcador permite consultar proyecto, contacto, imágenes, esfuerzo y riqueza de especies.",
              "En la vista por corporación, el límite jurisdiccional se dibuja detrás de las cámaras y puede ocultarse desde el control de capas."
            ),
            "ℹ️"
          )
        ),
        leafletOutput("map", height = "420px")
      )
    ),
    column(6,
      box(
        width = NULL,
        class = "box-xl graph-panel",
        title = tags$span(
          "2.2. Ocupación de especies",
          tags$span(
            class = "info-tooltip graph-info-tooltip",
            title = paste(
              "Ocupación = cámaras donde se detectó la especie / total de cámaras instaladas en el evento.",
              "El intervalo temporal puede cambiar las especies del Top 15, pero no el porcentaje de una especie que continúa en la muestra: conservar una detección por cámara mantiene la cámara como ocupada.",
              "Para un evento se muestra un gráfico de puntos y segmentos; para todos los eventos, una matriz de color con los últimos cinco eventos.",
              "La visualización presenta las 15 especies con más registros independientes, ordenadas de mayor a menor ocupación. Un guion indica que no fue posible calcular el valor."
            ),
            "ℹ️"
          )
        ),
        plotOutput("occupancyPlot", height = "500px")
      )
    )
  ),

  # Actividad y diurnalidad.
  fluidRow(
    column(6,
      box(
        width = NULL,
        class = "box-xl graph-panel",
        title = tags$span(
          "2.3. Patrón de actividad por hora del día",
          tags$span(
            class = "info-tooltip graph-info-tooltip",
            title = paste(
              "Agrupa los registros independientes por hora del día para las especies más detectadas.",
              "Las curvas permiten reconocer las horas con mayor actividad y comparar patrones entre especies."
            ),
            "ℹ️"
          )
        ),
        plotlyOutput("activityPattern")
      )
    ),
    column(6,
      box(
        width = NULL,
        class = "box-xl graph-panel",
        title = tags$span(
          "2.4. Diurnalidad de especies",
          tags$span(
            class = "info-tooltip graph-info-tooltip",
            title = paste(
              "Diurnalidad = registros independientes diurnos (06:00–18:00) / registros independientes del día.",
              "La gráfica muestra el promedio de esa proporción diaria para cada especie.",
              "El cálculo utiliza el intervalo de registros independientes aplicado en los filtros.",
              "Para todos los eventos se utiliza una matriz de color con los últimos cinco eventos y las 15 especies principales, ordenadas de mayor a menor diurnalidad promedio.",
              "Un guion indica que no fue posible calcular el valor."
            ),
            "ℹ️"
          )
        ),
        plotOutput("diurnalityPlot", height = "500px")
      )
    )
  ),

  # ===========================================================================
  # SECCIÓN 5: TABLA DE ESPECIES
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
  # SECCIÓN 6: GALERÍA MULTIMEDIA
  # ===========================================================================
  fluidRow(
    column(12,
      box(
        width = NULL,
        class = "box-md",
        title = "4. Imágenes destacadas del muestreo",
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
            "Exportar vista como imagen (PNG)",
            class = "btn-export-compact",
            icon = icon("camera"),
            disabled = TRUE,
            onclick = "window.captureDashboardFromButton && window.captureDashboardFromButton();"
          ),
          downloadButton(
            "downloadVisualData",
            "Descargar datos de visualizaciones (Excel)",
            class = "btn-export-compact",
            icon = icon("file-excel")
          ) %>% tagAppendAttributes(disabled = NA)
        )
      )
    )
  ),

  # ===========================================================================
  # SECCIÓN 8: CRÉDITOS
  # ===========================================================================
  # Logos de instituciones colaboradoras
  fluidRow(
    column(12,
      box(
        width = NULL,
        title = NULL,
        class = "footer-logos-box",
        tags$div(
          class = "footer-credits",
          tags$img(
            src = "images/Logos/Logos_instituciones.png",
            alt = "Logos institucionales",
            class = "footer-logos-img"
          ),
          tags$p(
            class = "support-message",
            "Con el apoyo de ",
            tags$strong("Wildlife Insights"),
            " y ",
            tags$strong("Google")
          )
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

# Informa una sola vez, al iniciar el proceso de R, qué proyectos disponen de
# fotografías para el carrusel. Este diagnóstico se escribe exclusivamente en
# la consola y no interrumpe la navegación del dashboard.
informar_disponibilidad_imagenes <- function() {
  favorites_root <- file.path(.dashboard_dir, "www", "images", "favorites")
  inventario <- inventariar_imagenes_proyectos(
    proyectos = proyectos_df,
    favorites_root = favorites_root,
    pattern = IMG_PATTERN
  )

  if (nrow(inventario) == 0) {
    message("[Galería] No fue posible construir el inventario de imágenes por proyecto.")
    return(invisible(NULL))
  }

  con_imagenes <- inventario[inventario$image_count > 0, , drop = FALSE]
  sin_imagenes <- inventario[inventario$image_count == 0, , drop = FALSE]
  total_imagenes <- sum(con_imagenes$image_count)
  general_count <- length(listar_imagenes_galeria(
    favorites_root = favorites_root,
    modo = "proyectos",
    entidad = "TODOS",
    pattern = IMG_PATTERN
  ))

  describir_proyecto <- function(datos, mostrar_cantidad = FALSE) {
    if (nrow(datos) == 0) return("  - Ninguno")

    vapply(seq_len(nrow(datos)), function(indice) {
      texto <- paste0(
        "  - ", datos$project_id[[indice]], " · ",
        datos$project_short_name[[indice]]
      )
      if (mostrar_cantidad) {
        cantidad <- datos$image_count[[indice]]
        texto <- paste0(
          texto, " — ", cantidad,
          if (identical(as.integer(cantidad), 1L)) " imagen" else " imágenes"
        )
      }
      texto
    }, character(1))
  }

  lineas_mensaje <- c(
    "",
    "[Galería] Disponibilidad de imágenes destacadas",
    sprintf(
      "[Galería] %d de %d proyectos cuentan con imágenes (%d archivos en total).",
      nrow(con_imagenes), nrow(inventario), total_imagenes
    ),
    sprintf(
      "[Galería] La carpeta General contiene %d imágenes para las vistas consolidadas.",
      general_count
    ),
    sprintf("[Galería] Proyectos sin imágenes disponibles (%d):", nrow(sin_imagenes)),
    describir_proyecto(sin_imagenes),
    sprintf("[Galería] Proyectos con imágenes disponibles (%d):", nrow(con_imagenes)),
    describir_proyecto(con_imagenes, mostrar_cantidad = TRUE),
    "[Galería] Ruta esperada: dashboard/www/images/favorites/{project_id}"
  )
  message(paste(lineas_mensaje, collapse = "\n"))

  invisible(inventario)
}

tryCatch(
  informar_disponibilidad_imagenes(),
  error = function(error) {
    message("[Galería] No fue posible revisar la disponibilidad de imágenes: ", conditionMessage(error))
  }
)

# ===============================================================================
# LÓGICA DEL SERVIDOR (REACTIVIDAD)
# ===============================================================================

# Coordina filtros, salidas analíticas, descargas y estado de la sesión.
server <- function(input, output, session) {

  # =============================================================================
  # ESTADO REACTIVO GLOBAL
  # =============================================================================

  # Almacena datos filtrados y estado de selección
  datos_actuales <- reactiveValues(
    tableSites = tableSites,
    iavhdata = iavhdata,
    deployments = deployments_data,
    projects = projects_data,
    gold = gold_data,
    datos_filtrados = FALSE
  )

  # Variables de control de filtros aplicados
  evento_aplicado <- reactiveVal("")
  corporacion_aplicada <- reactiveVal("")
  proyecto_aplicado <- reactiveVal("")
  intervalo_aplicado <- reactiveVal(INTERVALO_DEFAULT)
  modo_aplicado <- reactiveVal("corporaciones")
  ejecucion_aplicada <- reactiveVal(0L)

  # Contexto común para nombrar todas las descargas de forma trazable.
  entidad_descarga <- function() {
    modo <- modo_aplicado()
    valor <- if (identical(modo, "corporaciones")) corporacion_aplicada() else proyecto_aplicado()

    if (es_seleccion_global_entidad(valor, modo)) {
      return(if (identical(modo, "corporaciones")) "Todas las corporaciones" else "Todos los proyectos")
    }
    if (identical(modo, "proyectos")) {
      nombre <- proyectos_df$project_short_name[as.character(proyectos_df$project_id) == as.character(valor)]
      if (length(nombre) > 0 && !is.na(nombre[[1]]) && nzchar(nombre[[1]])) {
        return(paste0(valor, "_", nombre[[1]]))
      }
    }
    as.character(valor)
  }

  evento_descarga <- function() {
    if (es_seleccion_global_evento(evento_aplicado())) "Todos los eventos" else as.character(evento_aplicado())
  }

  nombre_descarga <- function(seccion, extension) {
    construir_nombre_descarga(
      seccion = seccion,
      entidad = entidad_descarga(),
      evento = evento_descarga(),
      intervalo = intervalo_aplicado(),
      extension = extension
    )
  }

  rendimiento <- reactiveValues(
    activo = FALSE,
    id = 0L,
    inicio = NULL,
    cpu_inicio = NULL,
    memoria_inicio = NA_real_,
    contexto = NULL,
    hitos = list(),
    cierre_programado = FALSE
  )
  hitos_requeridos <- c(
    "indicadores", "ranking", "mapa", "ocupación",
    "actividad", "diurnalidad", "galería"
  )

  iniciar_medicion_rendimiento <- function(modo, entidad, evento, intervalo) {
    gc(verbose = FALSE)
    isolate({
      rendimiento$id <- rendimiento$id + 1L
      rendimiento$activo <- TRUE
      rendimiento$inicio <- Sys.time()
      rendimiento$cpu_inicio <- proc.time()
      rendimiento$memoria_inicio <- memoria_r_mb()
      rendimiento$contexto <- list(
        vista = if (identical(modo, "corporaciones")) "Corporaciones" else "Proyectos",
        entidad = if (es_seleccion_global_entidad(entidad, modo)) etiqueta_todos_entidad(modo) else entidad,
        evento = if (es_seleccion_global_evento(evento)) "Todos los eventos" else evento,
        intervalo = configurar_intervalo_independencia(intervalo)$label
      )
      rendimiento$hitos <- list()
      rendimiento$cierre_programado <- FALSE
    })
  }

  registrar_hito_rendimiento <- function(nombre) {
    isolate({
      if (!isTRUE(rendimiento$activo) || nombre %in% names(rendimiento$hitos)) return(invisible(NULL))

      hitos <- rendimiento$hitos
      hitos[[nombre]] <- as.numeric(difftime(Sys.time(), rendimiento$inicio, units = "secs"))
      rendimiento$hitos <- hitos

      if (all(hitos_requeridos %in% names(hitos)) && !isTRUE(rendimiento$cierre_programado)) {
        rendimiento$cierre_programado <- TRUE
        id_actual <- rendimiento$id
        session$onFlushed(function() {
          session$sendCustomMessage("performance-ready-check", list(id = id_actual))
        }, once = TRUE)
      }
    })
    invisible(NULL)
  }

  observeEvent(input$performance_client_ready, {
    isolate({
      respuesta <- input$performance_client_ready
      if (!isTRUE(rendimiento$activo) || is.null(respuesta$id) ||
          as.integer(respuesta$id) != rendimiento$id) {
        return(invisible(NULL))
      }

      hitos <- rendimiento$hitos
      hitos$interfaz <- as.numeric(difftime(Sys.time(), rendimiento$inicio, units = "secs"))
      rendimiento$hitos <- hitos
      datos_reporte <- list(
        observaciones = subRawData(),
        deployments = subDeploymentsData(),
        sitios = subSitesData(),
        ranking = tabla_especies_datos(),
        indicadores = tabla_indicadores_datos()
      )
      resultado <- imprimir_reporte_rendimiento(
        contexto = rendimiento$contexto,
        inicio = rendimiento$inicio,
        cpu_inicio = rendimiento$cpu_inicio,
        memoria_inicio = rendimiento$memoria_inicio,
        hitos = rendimiento$hitos,
        datos = datos_reporte
      )
      rendimiento$activo <- FALSE
      showNotification(
        sprintf("Vista disponible en %.2f s. Reporte impreso en la consola de R.", resultado$elapsed_seconds),
        type = "message",
        duration = 4
      )
    })
  }, ignoreInit = TRUE)

  seleccion_filtros_valida <- reactive({
    modo <- input$modo_vista
    entidad_valor <- if (identical(modo, "corporaciones")) input$corporacion else input$project

    campos_completos <-
      !is.null(entidad_valor) && length(entidad_valor) == 1 && nzchar(entidad_valor) &&
        !is.null(input$evento) && length(input$evento) == 1 && nzchar(input$evento) &&
        !is.null(input$duplicateInterval) &&
        input$duplicateInterval %in% unname(intervalos_choices)

    if (!campos_completos) return(FALSE)

    # Una selección solo es válida si la combinación real entidad-evento tiene
    # observaciones. Evita aplicar cruces existentes por separado pero vacíos.
    nrow(filtrar_datos_dashboard(
      datos_actuales$iavhdata,
      modo = modo,
      entidad = entidad_valor,
      evento = input$evento,
      columna_corporacion = "Corporacion"
    )) > 0
  })

  # =============================================================================
  # OBSERVADORES DE EVENTOS UI
  # =============================================================================

  # Alternar modo de visualización: reinicia la selección para no mezclar
  # filtros de "corporación" con filtros de "proyecto" entre modos
  observeEvent(input$modo_vista, {
    modo_aplicado(input$modo_vista)
    updateSelectizeInput(session, "corporacion", selected = "", server = FALSE)
    updateSelectizeInput(session, "project", selected = "", server = FALSE)
    updateSelectInput(session, "evento", selected = "")
    updateSelectInput(session, "duplicateInterval", selected = INTERVALO_DEFAULT)

    evento_aplicado("")
    corporacion_aplicada("")
    proyecto_aplicado("")
    intervalo_aplicado(INTERVALO_DEFAULT)
    datos_actuales$datos_filtrados <- FALSE
    rendimiento$activo <- FALSE

    shinyjs::disable("aplicarSeleccion")
    shinyjs::disable("limpiarSeleccion")
    shinyjs::disable("downloadSpeciesTable")
    shinyjs::disable("downloadIndicatorsTable")
    shinyjs::disable("downloadVisualData")
    shinyjs::disable("captureScreen")
  }, ignoreInit = TRUE)

  # El catálogo de eventos depende de la entidad activa. Para selecciones
  # nacionales conserva todos los eventos publicados.
  observeEvent(
    list(input$modo_vista, input$corporacion, input$project),
    {
      modo <- input$modo_vista
      entidad_valor <- if (identical(modo, "corporaciones")) input$corporacion else input$project
      eventos_entidad <- character(0)

      if (!is.null(entidad_valor) && nzchar(entidad_valor)) {
        eventos_entidad <- obtener_eventos_entidad(
          datos_actuales$iavhdata,
          modo = modo,
          entidad = entidad_valor
        )
      }

      opciones <- c(
        setNames("", "-- Seleccione un evento --"),
        if (length(eventos_entidad) > 0) setNames("TODOS", "Todos los eventos"),
        setNames(eventos_entidad, eventos_entidad)
      )
      seleccionado <- isolate(input$evento)
      if (is.null(seleccionado) || !seleccionado %in% unname(opciones)) seleccionado <- ""
      updateSelectInput(session, "evento", choices = opciones, selected = seleccionado)
    },
    ignoreInit = FALSE
  )

  # Habilitar acciones según el estado de los filtros.
  observe({
    if (seleccion_filtros_valida()) {
      shinyjs::enable("aplicarSeleccion")
    } else {
      shinyjs::disable("aplicarSeleccion")
    }

    modo <- input$modo_vista
    entidad_valor <- if (identical(modo, "corporaciones")) input$corporacion else input$project
    hay_seleccion <-
      (!is.null(entidad_valor) && length(entidad_valor) == 1 && nzchar(entidad_valor)) ||
        (!is.null(input$evento) && length(input$evento) == 1 && nzchar(input$evento)) ||
        (!is.null(input$duplicateInterval) && input$duplicateInterval != INTERVALO_DEFAULT) ||
        isTRUE(datos_actuales$datos_filtrados)
    if (hay_seleccion) {
      shinyjs::enable("limpiarSeleccion")
    } else {
      shinyjs::disable("limpiarSeleccion")
    }
  })

  observe({
    tiene_datos <- datos_actuales$datos_filtrados &&
                   (nrow(subRawData()) > 0 || nrow(subTableData()) > 0)

    if (tiene_datos) {
      shinyjs::enable("downloadSpeciesTable")
      shinyjs::enable("downloadIndicatorsTable")
      shinyjs::enable("downloadVisualData")
      shinyjs::enable("captureScreen")
    } else {
      shinyjs::disable("downloadSpeciesTable")
      shinyjs::disable("downloadIndicatorsTable")
      shinyjs::disable("downloadVisualData")
      shinyjs::disable("captureScreen")
    }
  })

  observeEvent(input$limpiarSeleccion, {
    updateSelectizeInput(session, "corporacion", selected = "", server = FALSE)
    updateSelectizeInput(session, "project", selected = "", server = FALSE)
    updateSelectInput(session, "evento", selected = "")
    updateSelectInput(session, "duplicateInterval", selected = INTERVALO_DEFAULT)

    evento_aplicado("")
    corporacion_aplicada("")
    proyecto_aplicado("")
    intervalo_aplicado(INTERVALO_DEFAULT)
    datos_actuales$datos_filtrados <- FALSE
    rendimiento$activo <- FALSE

    shinyjs::disable("aplicarSeleccion")
    shinyjs::disable("limpiarSeleccion")
    shinyjs::disable("downloadSpeciesTable")
    shinyjs::disable("downloadIndicatorsTable")
    shinyjs::disable("downloadVisualData")
    shinyjs::disable("captureScreen")

    showNotification(
      paste0("Selección limpiada. Seleccione ", texto_entidad_articulo(input$modo_vista), " y un evento."),
      type = "message", duration = 3
    )
  })

  # Botón aplicar selección
  observeEvent(input$aplicarSeleccion, {
    modo <- input$modo_vista
    entidad_valor <- if (identical(modo, "corporaciones")) input$corporacion else input$project

    if (!seleccion_filtros_valida()) {
      showNotification(
        paste0(
          "Seleccione ", texto_entidad_articulo(modo),
          ", un evento de muestreo y un intervalo válido antes de aplicar."
        ),
        type = "warning", duration = 4
      )
      return()
    }

    iniciar_medicion_rendimiento(
      modo = modo,
      entidad = entidad_valor,
      evento = input$evento,
      intervalo = input$duplicateInterval
    )

    modo_aplicado(modo)
    evento_aplicado(input$evento)

    if (identical(modo, "corporaciones")) {
      corporacion_aplicada(input$corporacion)
      proyecto_aplicado("")
    } else {
      proyecto_aplicado(input$project)
      corporacion_aplicada("")
    }

    intervalo_aplicado(input$duplicateInterval)
    ejecucion_aplicada(ejecucion_aplicada() + 1L)
    datos_actuales$datos_filtrados <- TRUE

    interval_name <- configurar_intervalo_independencia(input$duplicateInterval)$label

    entidad_msg <- if (is.null(entidad_valor) || entidad_valor == "" || entidad_valor == valor_todos_entidad(modo)) {
      etiqueta_todos_entidad(modo)
    } else {
      paste0(if (identical(modo, "corporaciones")) "Corporación: " else "Proyecto: ", entidad_valor)
    }

    evento_msg <- if (is.null(input$evento) || input$evento == "" || input$evento == "TODOS") {
      "Todos los eventos"
    } else {
      paste0("Evento: ", input$evento)
    }

    showNotification(
      HTML(paste0(
        "<strong>✓ Selección aplicada</strong><br/>",
        entidad_msg, "<br/>", evento_msg, "<br/>",
        "Intervalo: ", interval_name
      )),
      type = "message", duration = 4
    )
  })

  # =============================================================================
  # VARIABLES AUXILIARES REACTIVAS
  # =============================================================================

  # Límites geográficos de Colombia para mapa
  bounds <- data.frame(
    lat = c(1.683247, 12.665921, 1.248316, -4.322823),
    lon = c(-79.137686, -71.675299, -66.744664, -69.937127)
  )

  # =============================================================================
  # DATOS FILTRADOS REACTIVOS
  # =============================================================================
  # Unificados para ambos modos: filtran por Corporacion/departamento (modo
  # "corporaciones") o por project_id (modo "proyectos"), según modo_aplicado().

  # Observaciones filtradas por corporación/proyecto y evento
  subRawData <- reactive({
    ejecucion_aplicada()
    evento_actual <- evento_aplicado()
    modo <- modo_aplicado()
    entidad_actual <- if (identical(modo, "corporaciones")) corporacion_aplicada() else proyecto_aplicado()

    if (is.null(evento_actual) || is.null(entidad_actual) ||
        (evento_actual == "" && entidad_actual == "")) {
      return(data.frame())
    }

    filtrar_datos_dashboard(
      datos_actuales$iavhdata,
      modo = modo,
      entidad = entidad_actual,
      evento = evento_actual,
      columna_corporacion = "Corporacion"
    )
  })

  subDeploymentsData <- reactive({
    ejecucion_aplicada()
    evento_actual <- evento_aplicado()
    modo <- modo_aplicado()
    entidad_actual <- if (identical(modo, "corporaciones")) corporacion_aplicada() else proyecto_aplicado()

    if (is.null(evento_actual) || is.null(entidad_actual) ||
        (evento_actual == "" && entidad_actual == "")) {
      return(data.frame())
    }

    filtrar_datos_dashboard(
      datos_actuales$deployments,
      modo = modo,
      entidad = entidad_actual,
      evento = evento_actual,
      columna_corporacion = "Corporacion"
    )
  })

  subTableData <- reactive({
    ejecucion_aplicada()
    evento_actual <- evento_aplicado()
    modo <- modo_aplicado()
    entidad_actual <- if (identical(modo, "corporaciones")) corporacion_aplicada() else proyecto_aplicado()

    if (is.null(evento_actual) || is.null(entidad_actual) ||
        (evento_actual == "" && entidad_actual == "")) {
      return(data.frame())
    }

    datos_sitios <- filtrar_datos_dashboard(
      datos_actuales$tableSites,
      modo = modo,
      entidad = entidad_actual,
      evento = evento_actual,
      columna_corporacion = "departamento"
    )

    # Una selección entidad/evento puede ser válida por separado pero no tener
    # intersección. No fabricar una fila de ceros: los outputs deben reconocer
    # correctamente el estado "sin datos".
    if (nrow(datos_sitios) == 0) {
      return(data.frame())
    }

    nombre_vista <- paste(
      if (es_seleccion_global_entidad(entidad_actual, modo)) {
        etiqueta_todos_entidad(modo)
      } else {
        entidad_actual
      },
      "-",
      if (es_seleccion_global_evento(evento_actual)) {
        "Todos los eventos"
      } else {
        evento_actual
      }
    )

    consolidar_estadisticas_sitios(datos_sitios, nombre_vista)
  })

  # Reactivo para datos de sitios filtrados (para mapa)
  subSitesData <- reactive({
    ejecucion_aplicada()
    evento_actual <- evento_aplicado()
    modo <- modo_aplicado()
    entidad_actual <- if (identical(modo, "corporaciones")) corporacion_aplicada() else proyecto_aplicado()

    if (is.null(evento_actual) || is.null(entidad_actual) ||
        (evento_actual == "" && entidad_actual == "")) {
      return(data.frame())
    }

    filtrar_datos_dashboard(
      datos_actuales$tableSites,
      modo = modo,
      entidad = entidad_actual,
      evento = evento_actual,
      columna_corporacion = "departamento"
    )
  })

  # =============================================================================
  # SALIDAS ANALÍTICAS
  # =============================================================================

  tabla_especies_datos <- reactive({
    if (nrow(subRawData()) == 0 || nrow(subDeploymentsData()) == 0) {
      return(data.frame())
    }
    tabla_especies_gold(
      datos_actuales$gold$species,
      modo = modo_aplicado(),
      entidad = if (identical(modo_aplicado(), "corporaciones")) corporacion_aplicada() else proyecto_aplicado(),
      evento = evento_aplicado(),
      intervalo_minutos = intervalo_minutos(intervalo_aplicado())
    )
  })

  # Tabla interactiva de especies
  output$speciesTable <- DT::renderDataTable({
    on.exit(registrar_hito_rendimiento("ranking"), add = TRUE)
    if (nrow(subRawData()) == 0) {
      return(DT::datatable(
        data.frame(Mensaje = paste0("Seleccione ", texto_entidad_articulo(input$modo_vista), " y un evento para ver el ranking de especies")),
        options = list(dom = 't', ordering = FALSE, searching = FALSE),
        rownames = FALSE,
        selection = 'none'
      ))
    }

    tabla_datos <- tabla_especies_datos()
    columnas_porcentaje <- grep(
      "^(Ocupaci|Frecuencia|Diurnalidad)",
      names(tabla_datos),
      value = TRUE
    )
    columnas_enteras <- setdiff(
      names(tabla_datos)[vapply(tabla_datos, is.numeric, logical(1))],
      columnas_porcentaje
    )
    porcentaje_targets <- as.integer(match(columnas_porcentaje, names(tabla_datos)) - 1L)
    porcentaje_renderer <- DT::JS(
      "function(data, type, row, meta) {",
      "  if (data === null || data === undefined || data === '' || isNaN(Number(data))) {",
      "    var columnTitle = (meta.settings.aoColumns[meta.col].sTitle || '').replace(/<[^>]*>/g, '');",
      "    var message = columnTitle.indexOf('Diurnalidad') === 0 ? 'Sin detecciones en el evento' : 'Revisar fechas de instalación';",
      "    var detail = columnTitle.indexOf('Diurnalidad') === 0 ? 'La especie no tiene registros independientes en este evento.' : 'Existen detecciones fuera del periodo válido de instalación de la cámara.';",
      "    if (type === 'display') return '<span class=\"metric-not-calculable\" title=\"' + detail + '\">' + message + '</span>';",
      "    if (type === 'filter') return message;",
      "    return null;",
      "  }",
      "  var value = Number(data);",
      "  if (type === 'display' || type === 'filter') {",
      "    return (value * 100).toLocaleString('es-CO', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + ' %';",
      "  }",
      "  return value;",
      "}"
    )

    column_definitions <- list(
      list(className = 'dt-center', targets = '_all')
    )
    if (length(porcentaje_targets) > 0) {
      column_definitions <- append(
        column_definitions,
        list(list(targets = porcentaje_targets, render = porcentaje_renderer))
      )
    }

    tabla_dt <- DT::datatable(
      tabla_datos,
      options = list(
        pageLength = nrow(tabla_datos),
        searching = TRUE,
        ordering = TRUE,
        order = list(list(0, 'asc')),  # Ordenar por ranking ascendente
        scrollX = TRUE,
        scrollY = "340px",  # Permite ver al menos cinco especies
        scrollCollapse = FALSE,
        paging = FALSE,
        info = FALSE,
        dom = 'ft',
        columnDefs = column_definitions,
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
    )

    if (length(columnas_enteras) > 0) {
      tabla_dt <- tabla_dt %>%
        DT::formatRound(
          columnas_enteras,
          digits = 0,
          mark = ".",
          dec.mark = ","
        )
    }

    tabla_dt
  })

  # Exportación: Tabla de especies en CSV
  output$downloadSpeciesTable <- downloadHandler(
    filename = function() {
      nombre_descarga("Ranking_Especies", "csv")
    },
    content = function(file) {
      tabla_datos <- preparar_ranking_para_exportacion(tabla_especies_datos())
      shiny::req(nrow(tabla_datos) > 0)
      escribir_csv_excel(
        tabla_datos,
        archivo = file,
        sep = ";",
        dec = ",",
        na = "Sin información"
      )
    }
  )

  # Gráfico: Ocupación de especies
  output$occupancyPlot <- renderPlot({
    on.exit(registrar_hito_rendimiento("ocupación"), add = TRUE)
    if (nrow(subRawData()) == 0) {
      plot.new()
      text(0.5, 0.5, paste0("Seleccione ", texto_entidad_articulo(modo_aplicado()), "\ny un evento para ver la ocupación de especies"),
           cex = 1.5, col = "#7f8c8d", font = 2)
      return()
    }

    makeSpeciesMetricGraph(
      tabla_especies_datos(),
      metric = "ocupacion",
      selected_event = evento_aplicado(),
      all_events = es_seleccion_global_evento(evento_aplicado()),
      top_n = 15,
      max_events = 5,
      interval_label = configurar_intervalo_independencia(intervalo_aplicado())$label
    )
  })

  # Gráfico: Diurnalidad de especies
  output$diurnalityPlot <- renderPlot({
    on.exit(registrar_hito_rendimiento("diurnalidad"), add = TRUE)
    if (nrow(subRawData()) == 0) {
      plot.new()
      text(0.5, 0.5, paste0("Seleccione ", texto_entidad_articulo(modo_aplicado()), "\ny un evento para ver la diurnalidad de especies"),
           cex = 1.5, col = "#7f8c8d", font = 2)
      return()
    }

    makeSpeciesMetricGraph(
      tabla_especies_datos(),
      metric = "diurnalidad",
      selected_event = evento_aplicado(),
      all_events = es_seleccion_global_evento(evento_aplicado()),
      top_n = 15,
      max_events = 5,
      interval_label = configurar_intervalo_independencia(intervalo_aplicado())$label
    )
  })

  # Patrón de actividad interactivo.
  output$activityPattern <- renderPlotly({
    on.exit(registrar_hito_rendimiento("actividad"), add = TRUE)
    if (nrow(subRawData()) == 0) {
      return(
        plot_ly(type = 'scatter', mode = 'markers') %>%
          layout(
            title = list(text = paste0("Seleccione ", texto_entidad_articulo(input$modo_vista), " y un evento para ver el patrón de actividad"),
                        font = list(size = 16, color = "#7f8c8d"))
          )
      )
    } else {
      activity_data <- actividad_gold(
        datos_actuales$gold$activity,
        modo = modo_aplicado(),
        entidad = if (identical(modo_aplicado(), "corporaciones")) corporacion_aplicada() else proyecto_aplicado(),
        evento = evento_aplicado(),
        intervalo_minutos = intervalo_minutos(intervalo_aplicado())
      )
      activity_plot_data <- activity_data %>%
        dplyr::group_by(sp_binomial, hour) %>%
        dplyr::summarise(count = sum(count, na.rm = TRUE), .groups = "drop")

      # Suprimir todos los mensajes de Plotly con capture.output anidado
      invisible(capture.output({
        invisible(capture.output({
          resultado <- suppressMessages(suppressWarnings({
            makeActivityPattern(
              subRawData(),
              top_n = 10,
              interval = 30,
              unit = "minutes",
              interactive = TRUE,
              activity_pattern = activity_plot_data
            )
          }))
        }, type = "message"))
      }, type = "output"))

      resultado
    }
  })

  # Mapa de cámaras.
  output$map <- renderLeaflet({
    on.exit(registrar_hito_rendimiento("mapa"), add = TRUE)
    if (nrow(subRawData()) == 0) {
      leaflet() %>%
        addTiles(options = tileOptions(crossOrigin = TRUE)) %>%
        setView(lng = -74.0721, lat = 4.7110, zoom = 5) %>%
        addControl(html = paste0("<div style='background-color: white; padding: 10px; border-radius: 5px;'>
                          <strong>Seleccione ", texto_entidad_articulo(input$modo_vista), " y un evento para ver las ubicaciones</strong></div>"),
                   position = "topright")
    } else {
      modo <- modo_aplicado()
      evento_actual <- evento_aplicado()
      entidad_actual <- if (identical(modo, "corporaciones")) corporacion_aplicada() else proyecto_aplicado()

      vista_descripcion <- paste(
        if (es_seleccion_global_entidad(entidad_actual, modo)) etiqueta_todos_entidad(modo) else entidad_actual,
        if (es_seleccion_global_evento(evento_actual)) "(todos los períodos)" else paste0("(período ", evento_actual, ")")
      )

      mapa <- makeMapLeaflet(
        subSitesData(),
        subSitesData(),
        bounds,
        vista_descripcion,
        mode = modo
      )

      # Añadir el límite de la corporación seleccionada.
      if (identical(modo, "corporaciones") && !is.null(car_shapefile) &&
          !is.null(entidad_actual) && entidad_actual != "" && entidad_actual != "TODAS") {

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
          car_poligono <- car_shapefile[car_shapefile[[columna_car]] == entidad_actual, ]

          if (nrow(car_poligono) > 0) {
            mapa <- mapa %>%
              addPolygons(
                data = car_poligono,
                fillColor = "#F4A261",
                fillOpacity = 0.18,
                color = "#C96B17",
                weight = 2.5,
                opacity = 0.9,
                dashArray = "6, 5",
                group = "Límite CAR",
                label = paste0("Límite jurisdiccional: ", entidad_actual),
                labelOptions = labelOptions(
                  style = list("font-weight" = "bold", "font-size" = "14px"),
                  textsize = "14px",
                  direction = "auto"
                ),
                highlightOptions = highlightOptions(
                  weight = 3.5,
                  color = "#9A4B0D",
                  fillOpacity = 0.24,
                  bringToFront = FALSE
                ),
                options = pathOptions(
                  pane = "car-polygons",
                  bubblingMouseEvents = FALSE
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
    modo <- modo_aplicado()
    entidad_actual <- if (identical(modo, "corporaciones")) corporacion_aplicada() else proyecto_aplicado()

    www_root <- normalizePath(
      file.path(.dashboard_dir, "www"),
      winslash = "/",
      mustWork = FALSE
    )
    favorites_root <- file.path(www_root, "images", "favorites")
    rutas_web <- function(paths) {
      paths <- paths[file.exists(paths)]
      if (length(paths) == 0) return(character(0))
      paths <- normalizePath(paths, winslash = "/", mustWork = FALSE)
      prefix <- paste0(www_root, "/")
      paths <- paths[startsWith(paths, prefix)]
      substring(paths, nchar(prefix) + 1L)
    }

    # En vistas consolidadas se usa General. En proyectos se usa la carpeta
    # project_id; en corporaciones se reúnen las carpetas de sus proyectos.
    project_ids <- if (identical(modo, "corporaciones") &&
                       !es_seleccion_global_entidad(entidad_actual, modo)) {
      datos <- subRawData()
      if (nrow(datos) > 0 && "project_id" %in% names(datos)) datos$project_id else character(0)
    } else {
      character(0)
    }

    imgs <- listar_imagenes_galeria(
      favorites_root = favorites_root,
      modo = modo,
      entidad = entidad_actual,
      project_ids = project_ids,
      pattern = IMG_PATTERN
    )
    rutas_web(imgs)
  })

  # UI condicional para galería de imágenes
  output$galeria_ui <- renderUI({
    on.exit(registrar_hito_rendimiento("galería"), add = TRUE)
    if (!datos_actuales$datos_filtrados || nrow(subRawData()) == 0) {
      return(
        tags$div(
          style = "text-align: center; padding: 80px 20px; color: #7f8c8d;",
          tags$p(
            style = "font-size: 16px; margin: 0;",
            paste0("Seleccione ", texto_entidad_articulo(input$modo_vista), " y un evento para ver las imágenes destacadas")
          )
        )
      )
    } else {
      imgs <- favorite_images()

      if (is.null(imgs) || length(imgs) == 0) {
        modo <- modo_aplicado()
        entidad_actual <- if (identical(modo, "corporaciones")) corporacion_aplicada() else proyecto_aplicado()
        instruccion <- if (es_seleccion_global_entidad(entidad_actual, modo)) {
          "Agregue archivos JPG, JPEG o PNG en dashboard/www/images/favorites/General."
        } else if (identical(modo, "proyectos")) {
          paste0(
            "Aún no hay imágenes cargadas para este proyecto. Cree la carpeta ",
            "dashboard/www/images/favorites/", entidad_actual,
            " y agregue allí archivos JPG, JPEG o PNG."
          )
        } else {
          ids <- sort(unique(as.character(subRawData()$project_id)))
          ids <- ids[!is.na(ids) & nzchar(ids)]
          detalle <- if (length(ids) > 0) paste(ids, collapse = ", ") else "los proyectos asociados"
          paste0(
            "Aún no hay imágenes cargadas para los proyectos de esta corporación. ",
            "Agregue archivos JPG, JPEG o PNG en carpetas nombradas con estos project_id: ",
            detalle, "."
          )
        }
        return(
          tags$div(
            style = "text-align: center; padding: 80px 20px; color: #7f8c8d;",
            tags$p(
              style = "font-size: 16px; margin-bottom: 10px;",
              "📷 No hay imágenes destacadas disponibles para esta selección"
            ),
            tags$p(
              style = "font-size: 14px; color: #95a5a6; margin: 0;",
              instruccion
            )
          )
        )
      } else {
        return(slickROutput("cameraTrapImages", height = "240px"))
      }
    }
  })

  output$cameraTrapImages <- renderSlickR({
    imgs <- favorite_images()

    if (is.null(imgs) || length(imgs) == 0) {
      return(NULL)
    }

    imgs_existentes <- imgs[file.exists(file.path(.dashboard_dir, "www", imgs))]

    if (length(imgs_existentes) == 0) {
      return(NULL)
    }

    if (length(imgs_existentes) > MAX_FAVORITES) {
      imgs_existentes <- sample(imgs_existentes, MAX_FAVORITES)
    }

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
  # METADATOS
  # =============================================================================

  # Etiqueta del encabezado ("Corporación: " / "Proyecto: "), refleja el modo
  # activo en vivo (no requiere haber aplicado la selección)
  output$entity_label_ui <- renderUI({
    tags$strong(if (identical(input$modo_vista, "corporaciones")) "Corporación: " else "Proyecto: ")
  })

  # Administrador / Colector de la corporación o proyecto
  output$collector <- renderText({
    if (nrow(subTableData()) == 0) {
      return("–")
    }

    modo <- modo_aplicado()
    entidad_actual <- if (identical(modo, "corporaciones")) corporacion_aplicada() else proyecto_aplicado()

    if (is.null(entidad_actual) || entidad_actual == "" || entidad_actual == valor_todos_entidad(modo)) {
      return(if (identical(modo, "corporaciones")) "Múltiples corporaciones - escala nacional" else "Múltiples proyectos - escala nacional")
    }

    if (identical(modo, "corporaciones")) {
      # Mostrar el nombre de la corporación seleccionada
      return(as.character(entidad_actual))
    }

    # Modo proyectos: buscar project_admin en projects_data
    project_admin <- datos_actuales$projects %>%
      dplyr::filter(as.character(project_id) == as.character(entidad_actual)) %>%
      dplyr::pull(project_admin) %>%
      unique() %>%
      head(1)

    # Si existe project_admin, mostrarlo; si no, mostrar colector desde tableSites
    if (length(project_admin) > 0 && !is.na(project_admin) && project_admin != "") {
      return(as.character(project_admin))
    } else {
      return(paste0(subTableData()$collector))
    }
  })

  # Rango temporal del muestreo
  output$dateRange <- renderText({
    if (nrow(subRawData()) == 0) {
      return("–")
    }
    d <- extract_date_ymd(subRawData())
    if (!length(d) || all(is.na(d))) return("–")
    paste0(
      formatear_fecha_es(min(d, na.rm = TRUE)),
      " a ",
      formatear_fecha_es(max(d, na.rm = TRUE))
    )
  })

  output$project_name <- renderUI({
    if (!isTRUE(datos_actuales$datos_filtrados) || nrow(subRawData()) == 0) {
      modo_pendiente <- input$modo_vista
      return(tags$span(
        style = "text-align: center !important; display: inline; color: #7f8c8d;",
        paste0(
          "Por favor seleccione ", texto_entidad_articulo(modo_pendiente),
          " y un evento para visualizar datos"
        )
      ))
    }

    modo <- modo_aplicado()
    evento_actual <- evento_aplicado()
    entidad_actual <- if (identical(modo, "corporaciones")) corporacion_aplicada() else proyecto_aplicado()

    # Generar título descriptivo según filtros activos
    if (identical(modo, "corporaciones")) {
      titulo_entidad <- if (is.null(entidad_actual) || entidad_actual == "" || entidad_actual == "TODAS") {
        "Todas las corporaciones"
      } else {
        entidad_actual  # Mostrar nombre de la CAR (ej: "CORPOCALDAS")
      }
    } else {
      titulo_entidad <- if (is.null(entidad_actual) || entidad_actual == "" || entidad_actual == "TODOS") {
        "Todos los proyectos"
      } else {
        # Buscar el nombre del proyecto seleccionado
        if ("project_id" %in% names(iavhdata) && "project_short_name" %in% names(iavhdata)) {
          nombre <- iavhdata %>%
            dplyr::filter(as.character(project_id) == as.character(entidad_actual)) %>%
            dplyr::pull(project_short_name) %>%
            unique() %>%
            head(1)
          if (length(nombre) > 0) paste0(entidad_actual, "_", nombre) else entidad_actual
        } else {
          entidad_actual
        }
      }
    }

    # Identificador del evento aplicado.
    titulo_evento <- if (is.null(evento_actual) || evento_actual == "" || evento_actual == "TODOS") {
      "Todos los eventos"
    } else {
      evento_actual
    }

    # La corporación se añade al título de la vista por proyecto.
    dpto <- ""
    if (identical(modo, "proyectos")) {
      mostrar_dpto <- !(es_seleccion_global_entidad(entidad_actual, modo) &&
                         es_seleccion_global_evento(evento_actual))
      if (mostrar_dpto && !is.null(subTableData()$departamento) && nrow(subTableData()) > 0) {
        dpto <- paste0(", ", subTableData()$departamento)
      }
    }

    tags$span(
      style = "text-align: center !important; display: inline;",
      paste0(titulo_entidad, " - ", titulo_evento, dpto)
    )
  })

  # =============================================================================
  # INDICADORES
  # =============================================================================
  # Indicadores por evento y consolidado.

  output$indicadores_table_ui <- renderUI({
    tagList(
      tags$div(
        style = "overflow-x: auto; margin-bottom: 10px;",
        DT::dataTableOutput("indicadores_consolidado_table")
      )
    )
  })

  tabla_indicadores_datos <- reactive({
    if (!datos_actuales$datos_filtrados) {
      return(NULL)
    }

    evento_actual <- evento_aplicado()
    modo <- modo_aplicado()
    entidad_actual <- if (identical(modo, "corporaciones")) corporacion_aplicada() else proyecto_aplicado()

    tabla_indicadores_gold(
      datos_actuales$gold$indicators,
      modo = modo,
      entidad = entidad_actual,
      evento = evento_actual,
      intervalo_minutos = intervalo_minutos(intervalo_aplicado())
    )
  })

  # Tabla DT con indicadores por período
  output$indicadores_consolidado_table <- DT::renderDataTable({
    on.exit(registrar_hito_rendimiento("indicadores"), add = TRUE)
    evento_actual <- evento_aplicado()
    modo <- modo_aplicado()
    entidad_actual <- if (identical(modo, "corporaciones")) corporacion_aplicada() else proyecto_aplicado()

    # Validar si hay selección
    if (is.null(evento_actual) || is.null(entidad_actual) ||
        (evento_actual == "" && entidad_actual == "")) {
      mensaje_df <- data.frame(
        Mensaje = paste0("Seleccione ", texto_entidad_articulo(modo), " y un evento para ver los indicadores consolidados")
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

    tabla_periodos <- tabla_indicadores_datos()

    # Detectar si solo hay 1 período (sin fila CONSOLIDADO)
    num_filas <- nrow(tabla_periodos)

    # Un evento: indicadores en una sola fila.
    if (num_filas == 1 && !es_seleccion_global_evento(evento_actual)) {
      # Eliminar columna Periodo para vista de evento específico
      tabla_sin_periodo <- tabla_periodos %>% dplyr::select(-Periodo)
      names(tabla_sin_periodo) <- c(
        "Imágenes", "Registros independientes", "Cámaras", "Trampas/noche", "Especies", "Mamíferos",
        "Aves", "Hill 1", "Hill 2", "Hill 3"
      )

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
            list(className = 'dt-center', targets = 0:9)
          )
        ),
        rownames = FALSE,
        class = 'cell-border stripe hover compact',
        selection = 'none'
      ) %>%
        DT::formatStyle(
          columns = 1:7,
          textAlign = 'center'
        ) %>%
        DT::formatCurrency(1:7,
                           currency = "",
                           digits = 0,
                           mark = ",") %>%
        DT::formatRound(8:10,
                        digits = 2,
                        mark = ","))
    }

    # Todos los eventos: detalle por periodo y consolidado.
    tabla_periodos_vista <- tabla_periodos
    names(tabla_periodos_vista) <- c(
      "Evento", "Imágenes", "Registros independientes", "Cámaras", "Trampas/noche", "Especies",
      "Mamíferos", "Aves", "Hill 1", "Hill 2", "Hill 3"
    )
    DT::datatable(
      tabla_periodos_vista,
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
          list(className = 'dt-center', targets = 1:10),
          list(className = 'dt-left', targets = 0),
          list(width = '12%', targets = 0),
          list(width = '8.8%', targets = 1:10)
        ),
        language = list(
          emptyTable = "No hay datos disponibles",
          zeroRecords = "No se encontraron eventos"
        )
      ),
      rownames = FALSE,
      class = 'cell-border stripe hover compact',
      selection = 'none'
    ) %>%
      DT::formatStyle(
        1,
        target = 'row',
        fontWeight = DT::styleEqual('CONSOLIDADO', 'bold'),
        backgroundColor = DT::styleEqual('CONSOLIDADO', '#e8f4f8'),
        color = DT::styleEqual('CONSOLIDADO', '#1a5490')
      ) %>%
      DT::formatCurrency(2:8,
                         currency = "",
                         digits = 0,
                         mark = ",") %>%
      DT::formatRound(9:11,
                      digits = 2,
                      mark = ",")
  })

  output$downloadIndicatorsTable <- downloadHandler(
    filename = function() {
      nombre_descarga("Indicadores", "csv")
    },
    content = function(file) {
      tabla_exportar <- tabla_indicadores_datos()
      shiny::req(!is.null(tabla_exportar), nrow(tabla_exportar) > 0)
      names(tabla_exportar)[names(tabla_exportar) == "Periodo"] <- "Evento"
      escribir_csv_excel(
        tabla_exportar,
        archivo = file,
        sep = ",",
        dec = ".",
        na = ""
      )
    }
  )

  # Datos consolidados de las cuatro visualizaciones. Cada reactivo reutiliza
  # exactamente los filtros, intervalos y límites empleados en pantalla.
  datos_metrica_exportacion <- function(metrica) {
    datos <- prepareSpeciesMetricData(
      species_table = tabla_especies_datos(),
      metric = metrica,
      selected_event = evento_aplicado(),
      all_events = es_seleccion_global_evento(evento_aplicado()),
      top_n = 15,
      max_events = 5
    )
    if (nrow(datos) == 0) return(data.frame())

    datos %>%
      dplyr::transmute(
        Ranking = as.integer(Ranking),
        Especie = as.character(Especie),
        Evento = as.character(Evento),
        Valor = as.numeric(Valor),
        Estado = as.character(Estado)
      ) %>%
      dplyr::arrange(Ranking, dplyr::desc(Evento))
  }

  datos_actividad_exportacion <- reactive({
    datos <- actividad_gold(
      datos_actuales$gold$activity,
      modo = modo_aplicado(),
      entidad = if (identical(modo_aplicado(), "corporaciones")) corporacion_aplicada() else proyecto_aplicado(),
      evento = evento_aplicado(),
      intervalo_minutos = intervalo_minutos(intervalo_aplicado())
    )
    if (nrow(datos) == 0) return(data.frame())

    datos %>%
      dplyr::transmute(
        Especie = as.character(sp_binomial),
        Evento = as.character(subproject_name),
        Hora = as.integer(hour),
        Registros_independientes = as.integer(count),
        Ranking = as.integer(ranking)
      ) %>%
      dplyr::arrange(Ranking, Especie, Evento, Hora)
  })

  datos_mapa_exportacion <- reactive({
    datos <- subSitesData()
    if (nrow(datos) == 0) return(data.frame())

    datos %>%
      dplyr::transmute(
        Proyecto_ID = as.character(project_id),
        Proyecto = as.character(project_short_name),
        Evento = as.character(subproject_name),
        Camara = as.character(site_name),
        Corporacion = as.character(departamento),
        Administrador = as.character(project_admin),
        Email = as.character(project_admin_email),
        Latitud = as.numeric(lat),
        Longitud = as.numeric(lon),
        Imagenes = as.integer(n),
        Dias_camara = as.numeric(effort),
        Especies = as.integer(ospTot),
        Mamiferos = as.integer(ospMamiferos),
        Aves = as.integer(ospAves)
      ) %>%
      dplyr::arrange(Evento, Proyecto_ID, Camara)
  })

  output$downloadVisualData <- downloadHandler(
    filename = function() {
      nombre_descarga("Datos_visualizaciones", "xlsx")
    },
    content = function(file) {
      hojas <- list(
        "Mapa" = datos_mapa_exportacion(),
        "Ocupacion" = datos_metrica_exportacion("ocupacion"),
        "Patron actividad" = datos_actividad_exportacion(),
        "Diurnalidad" = datos_metrica_exportacion("diurnalidad")
      )
      writeVisualizationWorkbook(hojas, file)
    }
  )

  # =============================================================================
  # EXPORTACIÓN
  # =============================================================================

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
# Captura solo el contenido, congela las animaciones de Leaflet y libera el
# objeto de descarga después de que el navegador lo haya consumido.
# ===============================================================================

js_capture <- "
Shiny.addCustomMessageHandler('performance-ready-check', function(message) {
  window.requestAnimationFrame(function() {
    window.requestAnimationFrame(function() {
      Shiny.setInputValue(
        'performance_client_ready',
        {id: message.id, timestamp: Date.now()},
        {priority: 'event'}
      );
    });
  });
});

var dashboardCaptureInProgress = false;

function collectLeafletLayouts() {
  var selectors = [
    '.leaflet-tile',
    '.leaflet-pane > svg',
    '.leaflet-pane > canvas',
    '.leaflet-marker-icon',
    '.leaflet-marker-shadow'
  ];

  return Array.from(document.querySelectorAll('.leaflet-container')).map(function(map) {
    var mapRect = map.getBoundingClientRect();
    var elements = {};
    selectors.forEach(function(selector) {
      elements[selector] = Array.from(map.querySelectorAll(selector)).map(function(element) {
        var rect = element.getBoundingClientRect();
        var layout = {
          left: rect.left - mapRect.left,
          top: rect.top - mapRect.top,
          width: rect.width,
          height: rect.height
        };
        if (element.tagName.toLowerCase() === 'svg') {
          var svgCopy = element.cloneNode(true);
          svgCopy.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
          // La posición ya se conserva mediante getBoundingClientRect().
          // Eliminar la traslación de Leaflet evita aplicarla dos veces al
          // convertir el SVG en una imagen para html2canvas.
          svgCopy.classList.remove('leaflet-zoom-animated');
          svgCopy.style.transform = 'none';
          svgCopy.style.webkitTransform = 'none';
          layout.snapshot = 'data:image/svg+xml;charset=utf-8,' +
            encodeURIComponent(new XMLSerializer().serializeToString(svgCopy));
        } else if (element.tagName.toLowerCase() === 'canvas') {
          try { layout.snapshot = element.toDataURL('image/png'); } catch (canvasError) {}
        }
        return layout;
      });
    });
    return {elements: elements};
  });
}

function normalizeLeafletClone(clonedDocument, layouts) {
  var clonedMaps = clonedDocument.querySelectorAll('.leaflet-container');
  clonedMaps.forEach(function(map, mapIndex) {
    var layout = layouts[mapIndex];
    if (!layout) return;

    map.querySelectorAll('.leaflet-map-pane, .leaflet-pane').forEach(function(pane) {
      pane.style.transform = 'none';
    });

    Object.keys(layout.elements).forEach(function(selector) {
      var clonedElements = map.querySelectorAll(selector);
      layout.elements[selector].forEach(function(position, index) {
        var element = clonedElements[index];
        if (!element) return;
        if (position.snapshot) {
          var snapshot = clonedDocument.createElement('img');
          snapshot.src = position.snapshot;
          snapshot.alt = '';
          snapshot.style.position = 'absolute';
          snapshot.style.left = position.left + 'px';
          snapshot.style.top = position.top + 'px';
          snapshot.style.width = position.width + 'px';
          snapshot.style.height = position.height + 'px';
          snapshot.style.maxWidth = 'none';
          snapshot.style.margin = '0';
          snapshot.style.pointerEvents = 'none';
          element.replaceWith(snapshot);
          return;
        }
        element.style.transform = 'none';
        element.style.left = position.left + 'px';
        element.style.top = position.top + 'px';
        element.style.margin = '0';
        if (element.tagName === 'svg' || element.tagName === 'canvas') {
          element.style.width = position.width + 'px';
          element.style.height = position.height + 'px';
        }
      });
    });
  });
}

function executeDashboardCapture(message) {
  Shiny.setInputValue('capture_status', 'iniciando', {priority: 'event'});
  var target = document.querySelector('.content-wrapper') || document.body;
  var button = document.getElementById('captureScreen');
  var originalScrollY = window.scrollY;

  if (dashboardCaptureInProgress) return;

  if (typeof html2canvas !== 'function') {
    Shiny.setInputValue('capture_status', 'error: La librería de captura no está disponible', {priority: 'event'});
    return;
  }

  dashboardCaptureInProgress = true;
  if (button) button.classList.add('capture-in-progress');
  document.documentElement.classList.add('dashboard-capture-mode');
  window.dispatchEvent(new Event('resize'));
  try {
    var leafletWidget = window.HTMLWidgets && HTMLWidgets.find('#map');
    if (leafletWidget && typeof leafletWidget.getMap === 'function') {
      leafletWidget.getMap().invalidateSize(false);
    }
  } catch (leafletError) {
    console.warn('No fue posible recalcular el tamaño del mapa antes de exportar.', leafletError);
  }

  setTimeout(function() {
    Shiny.setInputValue('capture_status', 'capturando', {priority: 'event'});
    var leafletLayouts = collectLeafletLayouts();

    html2canvas(target, {
      scale: 1,
      useCORS: true,
      allowTaint: false,
      logging: false,
      backgroundColor: '#ecf0f5',
      imageTimeout: 15000,
      removeContainer: true,
      width: target.scrollWidth,
      height: target.scrollHeight,
      windowWidth: document.documentElement.clientWidth,
      windowHeight: target.scrollHeight,
      scrollX: 0,
      scrollY: -originalScrollY,
      onclone: function(clonedDocument) {
        clonedDocument.documentElement.classList.add('dashboard-capture-mode');
        clonedDocument.querySelectorAll('.leaflet-container').forEach(function(map) {
          map.classList.remove('leaflet-fade-anim', 'leaflet-zoom-anim');
        });
        normalizeLeafletClone(clonedDocument, leafletLayouts);
      }
    }).then(function(canvas) {
      canvas.toBlob(function(blob) {
        if (blob) {
          var url = URL.createObjectURL(blob);
          var link = document.createElement('a');
          link.download = message.filename + '.png';
          link.href = url;
          link.style.display = 'none';
          document.body.appendChild(link);
          link.click();
          setTimeout(function() {
            link.remove();
            URL.revokeObjectURL(url);
          }, 1500);
          Shiny.setInputValue('capture_status', 'exitoso', {priority: 'event'});
        } else {
          Shiny.setInputValue('capture_status', 'error: No se pudo generar imagen', {priority: 'event'});
        }
      }, 'image/png');
    }).catch(function(error) {
      console.error('Error al exportar el dashboard:', error);
      Shiny.setInputValue('capture_status', 'error: ' + error.message, {priority: 'event'});
    }).finally(function() {
      document.documentElement.classList.remove('dashboard-capture-mode');
      dashboardCaptureInProgress = false;
      if (button) button.classList.remove('capture-in-progress');
    });
  }, 900);
}

window.captureDashboardFromButton = function() {
  function safePart(value, fallback) {
    value = String(value || fallback)
      .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
      .replace(/[<>:\"/\\\\|?*]/g, '_')
      .replace(/\\s+/g, ' ')
      .trim()
      .replace(/[. ]+$/g, '');
    return value || fallback;
  }
  function selectedText(element, fallback) {
    if (!element || element.selectedIndex < 0 || !element.options) return fallback;
    return element.options[element.selectedIndex].text || element.value || fallback;
  }
  var modeInput = document.querySelector('input[name=\"modo_vista\"]:checked');
  var mode = modeInput ? modeInput.value : 'corporaciones';
  var entityInput = document.getElementById(mode === 'corporaciones' ? 'corporacion' : 'project');
  var eventInput = document.getElementById('evento');
  var intervalInput = document.getElementById('duplicateInterval');
  var entity = safePart(selectedText(entityInput, 'Entidad'), 'Entidad');
  var eventName = safePart(selectedText(eventInput, 'Evento'), 'Evento');
  var intervalName = safePart(intervalInput && intervalInput.value, 'intervalo');
  var now = new Date();
  var stamp = String(now.getDate()).padStart(2, '0') + '_' +
    String(now.getMonth() + 1).padStart(2, '0') + '_' +
    now.getFullYear().toString() + '-' +
    String(now.getHours()).padStart(2, '0') + '_' +
    String(now.getMinutes()).padStart(2, '0');
  executeDashboardCapture({
    filename: 'Dashboard-' + entity + '-' + eventName + '-' + intervalName + '-' + stamp
  });
};
"

# ===============================================================================
# INICIALIZACIÓN DE LA APLICACIÓN SHINY
# ===============================================================================

shinyApp(
  ui = dashboardPage(
    dashboardHeader(disable = TRUE),
    dashboardSidebar(disable = TRUE),
    # El controlador debe vivir dentro del body para que el navegador lo
    # ejecute; como hermano de dashboardPage solo aparecía en el DOM.
    htmltools::tagAppendChild(body, tags$script(HTML(js_capture)))
  ),
  server = server
)
