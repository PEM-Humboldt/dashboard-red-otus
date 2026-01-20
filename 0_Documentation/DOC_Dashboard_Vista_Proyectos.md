# Documentación: Dashboard_Vista_Proyectos.R

## Información General

**Archivo:** `Dashboard_Vista_Proyectos.R`  
**Proyecto:** Dashboard IaVH - Red OTUS Colombia  
**Sistema:** Sistema de Monitoreo de Biodiversidad con Cámaras Trampa  
**Autor original:** Jorge Ahumada - Conservation International (2020)  
**Adaptación:** Cristian C. Acevedo - Instituto Humboldt (2025)  
**Tecnología:** R Shiny + shinydashboard + Plotly + Leaflet  
**Versión:** 2.0 - Arquitectura consolidada Parquet  
**Licencia:** CC0 1.0 Universal (Public Domain)  
**Última modificación:** 2025-12-09  

---

## Descripción

Dashboard interactivo desarrollado en **R Shiny** para la visualización y análisis de datos de fototrampeo provenientes de **Wildlife Insights**. El sistema permite:

- ✅ Análisis multi-evento y multi-proyecto
- ✅ Vistas consolidadas y filtradas
- ✅ Visualizaciones interactivas (gráficos, mapas, tablas)
- ✅ Exportación de reportes en formato PNG y CSV
- ✅ Galería multimedia de imágenes destacadas

---

## Arquitectura del Sistema

### Tecnologías Utilizadas

| Componente | Librería | Función |
|------------|----------|---------|
| Framework web | `shiny`, `shinydashboard` | Aplicación reactiva y estructura de dashboard |
| Temas visuales | `dashboardthemes`, `shinyjs` | Personalización de UI y control dinámico |
| Gráficos interactivos | `plotly` | Patrón de actividad circadiana |
| Mapas | `leaflet` | Ubicación geográfica de cámaras |
| Carrusel | `slickR` | Galería de imágenes favoritas |
| Tablas | `DT` (DataTables) | Tablas interactivas con búsqueda y ordenamiento |
| Procesamiento | `dplyr`, `tidyr` | Manipulación de datos |
| Imágenes | `magick` | Procesamiento de archivos multimedia |
| Gráficos estáticos | `cowplot`, `ggplot2` | Curvas de acumulación y ocupación |

### Flujo de Datos

```
[Archivos Parquet] → [Carga inicial] → [Estado reactivo global]
                                              ↓
                                    [Filtros de UI (proyecto/evento)]
                                              ↓
                                    [Datos filtrados reactivos]
                                              ↓
                           [Visualizaciones + Tablas + Indicadores]
                                              ↓
                                    [Exportación (PNG/CSV)]
```

---

## Estructura del Dashboard

### Layout General

El dashboard utiliza `shinydashboard` con estructura de cuerpo único (sin header ni sidebar):

```
┌──────────────────────────────────────────────────────┐
│ SECCIÓN 1: ENCABEZADO                                 │
│   • Título del reporte                                │
│   • Nombre dinámico del proyecto/evento              │
└──────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────┐
│ SECCIÓN 2: CONTROLES Y METADATOS                      │
│   • Selectores de proyecto y evento                  │
│   • Botones: Aplicar selección / Limpiar             │
│   • Metadatos: Administrador, Rango de fechas        │
└──────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────┐
│ SECCIÓN 3: INDICADORES CLAVE (Value Boxes)            │
│   • 🗂️ Imágenes  📸 Cámaras  📅 Días-cámara         │
│   • 🏞️ Especies  🐆 Mamíferos  🦅 Aves               │
└──────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────┐
│ SECCIÓN 4: TABLA DE ESPECIES                          │
│   • Ranking de especies por eventos independientes   │
│   • Búsqueda y descarga CSV                          │
└──────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────┐
│ SECCIÓN 5: GRÁFICOS DE ANÁLISIS                       │
│   Fila 1: Ocupación + Curva de acumulación           │
│   Fila 2: Patrón de actividad + Mapa                 │
└──────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────┐
│ SECCIÓN 6: GALERÍA MULTIMEDIA                         │
│   • Carrusel con imágenes favoritas                  │
└──────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────┐
│ SECCIÓN 7: EXPORTACIÓN Y CRÉDITOS                     │
│   • Botón de captura de pantalla                     │
│   • Logos institucionales                            │
└──────────────────────────────────────────────────────┘
```

---

## Configuración Inicial

### Variables Globales

```r
# Galería de imágenes
MAX_FAVORITES <- 40                    # Límite de imágenes en carrusel
IMG_PATTERN <- "\\.(jpe?g|png)$"       # Formatos válidos

# Suprimir mensajes de Plotly
options(
  plotly.message = FALSE,
  plotly.warning = FALSE,
  plotly.verbose = FALSE
)
```

### Carga de Datos

```r
# 1. Validar archivos Parquet
eventos_disponibles <- obtener_eventos_disponibles()

# 2. Cargar datos consolidados
datos_iniciales <- cargar_datos_consolidados(interval = "30min")

# 3. Extraer componentes
iavhdata <- datos_iniciales$iavhdata
tableSites <- datos_iniciales$tableSites
projects_data <- datos_iniciales$projects

# 4. Convertir categorías Arrow a character (crítico para Shiny)
iavhdata$subproject_name <- as.character(iavhdata$subproject_name)
tableSites$subproject_name <- as.character(tableSites$subproject_name)
```

### Preparación de Selectores UI

**Selector de eventos:**
```r
eventos_unicos <- unique(as.character(iavhdata$subproject_name))
eventos_unicos <- sort(eventos_unicos, decreasing = TRUE)

eventos_choices <- c(
  setNames("", "-- Seleccione un evento --"),
  setNames("TODOS", "Todos los eventos"),
  setNames(eventos_unicos, eventos_unicos)
)
```

**Selector de proyectos:**
```r
proyectos_df <- iavhdata %>%
  select(project_id, project_short_name) %>%
  distinct() %>%
  arrange(project_short_name)

project_choices <- c(
  setNames("", "-- Seleccione un proyecto --"),
  setNames("TODOS", "Todos los proyectos"),
  setNames(
    proyectos_df$project_id,
    paste0(proyectos_df$project_id, "_", proyectos_df$project_short_name)
  )
)
```

---

## Componentes Reactivos

### Estado Reactivo Global

```r
datos_actuales <- reactiveValues(
  tableSites = tableSites,          # Estadísticas por sitio
  iavhdata = iavhdata,              # Observaciones completas
  projects = projects_data,          # Catálogo de proyectos
  datos_filtrados = FALSE           # Bandera de estado
)

# Variables de control de filtros
evento_aplicado <- reactiveVal("")
proyecto_aplicado <- reactiveVal("")
intervalo_aplicado <- reactiveVal("30min")
```

### Observadores de Eventos

#### 1. Control de habilitación de botón "Aplicar selección"

```r
observe({
  tiene_seleccion <- (
    !is.null(input$evento) && input$evento != "" ||
    !is.null(input$project) && input$project != ""
  )
  
  shinyjs::toggleState("aplicarSeleccion", condition = tiene_seleccion)
})
```

#### 2. Control de botones de exportación

```r
observe({
  hay_datos <- datos_actuales$datos_filtrados && nrow(subRawData()) > 0
  
  shinyjs::toggleState("captureScreen", condition = hay_datos)
  shinyjs::toggleState("downloadSpeciesTable", condition = hay_datos)
})
```

#### 3. Botón "Limpiar selección"

```r
observeEvent(input$limpiarSeleccion, {
  # Resetear selectores
  updateSelectInput(session, "evento", selected = "")
  updateSelectInput(session, "project", selected = "")
  
  # Restaurar datos originales
  datos_actuales$tableSites <- tableSites
  datos_actuales$iavhdata <- iavhdata
  datos_actuales$datos_filtrados <- FALSE
  
  # Resetear variables de control
  evento_aplicado("")
  proyecto_aplicado("")
})
```

#### 4. Botón "Aplicar selección"

**Lógica de filtrado:**

```r
observeEvent(input$aplicarSeleccion, {
  # Capturar valores de input
  evento_selec <- input$evento
  proyecto_selec <- input$project
  
  # Almacenar valores aplicados
  evento_aplicado(evento_selec)
  proyecto_aplicado(proyecto_selec)
  
  # Inicializar con datos completos
  datos_filtrados <- iavhdata
  sitios_filtrados <- tableSites
  
  # PASO 1: Filtrar por proyecto (si aplica)
  if (!is.null(proyecto_selec) && proyecto_selec != "" && proyecto_selec != "TODOS") {
    proyecto_num <- as.numeric(proyecto_selec)
    datos_filtrados <- datos_filtrados %>%
      filter(project_id == proyecto_num)
    sitios_filtrados <- sitios_filtrados %>%
      filter(project_id == proyecto_num)
  }
  
  # PASO 2: Filtrar por evento (si aplica)
  if (!is.null(evento_selec) && evento_selec != "" && evento_selec != "TODOS") {
    datos_filtrados <- datos_filtrados %>%
      filter(subproject_name == evento_selec)
    sitios_filtrados <- sitios_filtrados %>%
      filter(subproject_name == evento_selec)
  }
  
  # PASO 3: Actualizar estado reactivo
  datos_actuales$iavhdata <- datos_filtrados
  datos_actuales$tableSites <- sitios_filtrados
  datos_actuales$datos_filtrados <- TRUE
})
```

---

## Datos Filtrados Reactivos

### 1. subRawData()

**Observaciones filtradas según selección:**

```r
subRawData <- reactive({
  datos <- datos_actuales$iavhdata
  evento_actual <- evento_aplicado()
  proyecto_actual <- proyecto_aplicado()
  
  # Aplicar filtros (si no se aplicaron con el botón)
  if (!datos_actuales$datos_filtrados) {
    if (!is.null(proyecto_actual) && proyecto_actual != "" && proyecto_actual != "TODOS") {
      datos <- datos %>% filter(project_id == as.numeric(proyecto_actual))
    }
    
    if (!is.null(evento_actual) && evento_actual != "" && evento_actual != "TODOS") {
      datos <- datos %>% filter(subproject_name == evento_actual)
    }
  }
  
  return(datos)
})
```

### 2. subTableData()

**Estadísticas consolidadas por sitio:**

```r
subTableData <- reactive({
  datos_sitios <- datos_actuales$tableSites
  evento_actual <- evento_aplicado()
  proyecto_actual <- proyecto_aplicado()
  
  # Aplicar filtros
  if (!datos_actuales$datos_filtrados) {
    # [Lógica similar a subRawData]
  }
  
  # Consolidar estadísticas
  nombre_vista <- if (evento_actual == "TODOS" && proyecto_actual == "TODOS") {
    "Red OTUS - Consolidado"
  } else if (proyecto_actual != "" && proyecto_actual != "TODOS") {
    paste0("Proyecto ", proyecto_actual)
  } else {
    evento_actual
  }
  
  consolidar_estadisticas_sitios(datos_sitios, nombre_vista)
})
```

### 3. subSitesData()

**Datos de sitios para mapas:**

```r
subSitesData <- reactive({
  datos_sitios <- datos_actuales$tableSites
  
  # [Aplicar filtros similares]
  
  return(datos_sitios)
})
```

---

## Outputs Principales

### 1. Tabla de Especies (speciesTable)

**Tipo:** `DT::renderDataTable()`

**Código:**
```r
output$speciesTable <- DT::renderDataTable({
  tabla <- makeSpeciesTable(
    subset = subRawData(),
    interval = 30,
    unit = "minutes"
  )
  
  DT::datatable(
    tabla,
    options = list(
      pageLength = 15,
      searching = TRUE,
      ordering = TRUE,
      dom = 'ftp'
    ),
    rownames = FALSE,
    colnames = c(
      "Ranking" = "Ranking",
      "Especie" = "Especie",
      "Núm. Imágenes" = "Numero imagenes",
      "Registros Independientes" = "Registros independientes",
      "Tipo" = "Tipo"
    )
  )
})
```

**Características:**
- Búsqueda en tiempo real
- Ordenamiento por columnas
- Paginación (15 registros por página)
- Descarga CSV disponible

---

### 2. Descarga de Tabla (downloadSpeciesTable)

**Tipo:** `downloadHandler()`

**Código:**
```r
output$downloadSpeciesTable <- downloadHandler(
  filename = function() {
    proyecto <- proyecto_aplicado()
    evento <- evento_aplicado()
    timestamp <- format(Sys.time(), "%Y%m%d_%H%M%S")
    
    nombre_base <- if (proyecto != "" && proyecto != "TODOS") {
      paste0("Especies_Proyecto_", proyecto)
    } else if (evento != "" && evento != "TODOS") {
      paste0("Especies_Evento_", gsub(" ", "_", evento))
    } else {
      "Especies_Consolidado"
    }
    
    paste0(nombre_base, "_", timestamp, ".csv")
  },
  content = function(file) {
    tabla <- makeSpeciesTable(
      subset = subRawData(),
      interval = 30,
      unit = "minutes"
    )
    write.csv(tabla, file, row.names = FALSE, fileEncoding = "UTF-8")
  }
)
```

---

### 3. Gráfico de Ocupación (occupancyPlot)

**Tipo:** `renderPlot()`

**Código:**
```r
output$occupancyPlot <- renderPlot({
  grafico <- makeOccupancyGraph(
    subset = subRawData(),
    top_n = 15,
    interval = 30,
    unit = "minutes"
  )
  
  print(grafico)
})
```

**Visualización:**
- Barras horizontales con porcentaje de ocupación
- Top 15 especies más detectadas
- Colores por clase taxonómica

---

### 4. Curva de Acumulación (accumulationCurve)

**Tipo:** `renderPlot()`

**Código:**
```r
output$accumulationCurve <- renderPlot({
  curva <- makeAccumulationCurve(
    subset = subRawData(),
    interval = 30,
    unit = "minutes"
  )
  
  print(curva)
})
```

**Visualización:**
- Curva de acumulación de especies por sitio
- Línea de asíntota (riqueza total)
- Basado en método de Ugland et al. (2003)

---

### 5. Patrón de Actividad (activityPattern)

**Tipo:** `renderPlotly()`

**Código:**
```r
output$activityPattern <- renderPlotly({
  patron <- makeActivityPattern(
    subset = subRawData(),
    interval = 30,
    unit = "minutes"
  )
  
  patron
})
```

**Visualización:**
- Gráfico interactivo de densidad circadiana
- Área rellena bajo la curva
- Etiquetas de períodos (🌙 Nocturno / ☀️ Diurno)
- Tooltips con valores exactos

---

### 6. Mapa de Ubicaciones (map)

**Tipo:** `renderLeaflet()`

**Código:**
```r
output$map <- renderLeaflet({
  # Límites geográficos de Colombia
  bounds <- data.frame(
    Norte = 12.5,
    Sur = -4.5,
    Este = -66.8,
    Oeste = -79.0
  )
  
  mapa <- makeMapLeaflet(
    subset = subSitesData(),
    mapBounds = bounds
  )
  
  mapa
})
```

**Características:**
- Marcadores circulares con tamaño proporcional a riqueza
- Popups con información detallada
- Capa base OpenStreetMap
- Zoom automático a Colombia

---

### 7. Galería de Imágenes (cameraTrapImages)

**Tipo:** `renderSlickR()`

**Selección de imágenes:**
```r
favorite_images <- reactive({
  if (!datos_actuales$datos_filtrados || nrow(subRawData()) == 0) {
    return(character(0))
  }
  
  # Obtener proyectos únicos en subset
  proyectos_en_subset <- unique(subRawData()$project_id)
  
  # Buscar imágenes favoritas
  carpeta_base <- "www/images/favorites/"
  imagenes <- c()
  
  for (proj_id in proyectos_en_subset) {
    carpeta_proyecto <- file.path(carpeta_base, as.character(proj_id))
    
    if (dir.exists(carpeta_proyecto)) {
      imgs_proyecto <- list.files(
        carpeta_proyecto,
        pattern = IMG_PATTERN,
        full.names = TRUE,
        recursive = FALSE,
        ignore.case = TRUE
      )
      imagenes <- c(imagenes, imgs_proyecto)
    }
  }
  
  # Limitar a MAX_FAVORITES (aleatorio)
  if (length(imagenes) > MAX_FAVORITES) {
    imagenes <- sample(imagenes, MAX_FAVORITES)
  }
  
  return(imagenes)
})
```

**Renderizado:**
```r
output$cameraTrapImages <- renderSlickR({
  imgs <- favorite_images()
  
  if (!length(imgs)) return(NULL)
  
  slickR::slickR(imgs, slideId = "favoriteSlider") +
    slickR::settings(
      slidesToShow = 5,
      slidesToScroll = 5,
      dots = FALSE,
      arrows = TRUE,
      autoplay = TRUE,
      autoplaySpeed = 3000,
      speed = 500,
      cssEase = "ease-in-out",
      infinite = TRUE,
      responsive = list(
        list(breakpoint = 1024, settings = list(slidesToShow = 3)),
        list(breakpoint = 768, settings = list(slidesToShow = 2)),
        list(breakpoint = 480, settings = list(slidesToShow = 1))
      )
    )
})
```

**Características:**
- Carrusel responsivo (5 imágenes en escritorio, 1 en móvil)
- Autoplay con velocidad configurable
- Navegación con flechas
- Transiciones suaves

---

### 8. Metadatos y Textos Informativos

#### Administrador del Proyecto (collector)

```r
output$collector <- renderText({
  if (nrow(subTableData()) == 0) return("–")
  
  proyecto_actual <- proyecto_aplicado()
  
  # Vista consolidada
  if (proyecto_actual == "" || proyecto_actual == "TODOS") {
    return("Múltiples proyectos")
  }
  
  # Buscar project_admin en projects_data
  proyecto_num <- as.numeric(proyecto_actual)
  project_admin <- datos_actuales$projects %>%
    filter(project_id == proyecto_num) %>%
    pull(project_admin) %>%
    unique() %>%
    head(1)
  
  if (length(project_admin) > 0 && !is.na(project_admin)) {
    return(as.character(project_admin))
  } else {
    return(paste0(subTableData()$collector))
  }
})
```

#### Rango de Fechas (dateRange)

```r
output$dateRange <- renderText({
  if (nrow(subRawData()) == 0) return("–")
  
  fechas <- extract_date_ymd(subRawData())
  
  if (!length(fechas) || all(is.na(fechas))) return("–")
  
  paste0(min(fechas, na.rm = TRUE), " - ", max(fechas, na.rm = TRUE))
})
```

#### Nombre del Proyecto (project_name)

```r
output$project_name <- renderUI({
  evento_actual <- evento_aplicado()
  proyecto_actual <- proyecto_aplicado()
  
  # Validar selección
  if (is.null(evento_actual) || is.null(proyecto_actual) ||
      (evento_actual == "" && proyecto_actual == "")) {
    return(tags$span(
      style = "text-align: center; color: #7f8c8d;",
      "Por favor seleccione proyecto y/o evento para visualizar datos"
    ))
  }
  
  # Generar título
  titulo_proyecto <- if (proyecto_actual == "" || proyecto_actual == "TODOS") {
    "Todos los proyectos"
  } else {
    # Buscar nombre en iavhdata
    nombre <- iavhdata %>%
      filter(project_id == as.numeric(proyecto_actual)) %>%
      pull(project_short_name) %>%
      unique() %>%
      head(1)
    
    paste0("Proyecto ", proyecto_actual, " - ", nombre)
  }
  
  titulo_evento <- if (evento_actual == "" || evento_actual == "TODOS") {
    "Todos los eventos"
  } else {
    evento_actual
  }
  
  # Agregar departamento
  dpto <- if (nrow(subTableData()) > 0 && !is.null(subTableData()$departamento)) {
    paste0(", ", subTableData()$departamento)
  } else {
    ""
  }
  
  tags$span(
    style = "text-align: center;",
    paste0(titulo_proyecto, " - ", titulo_evento, dpto)
  )
})
```

---

### 9. Tabla de Indicadores Consolidados

**Tipo:** `DT::renderDataTable()`

**Código:**
```r
output$indicadores_consolidado_table <- DT::renderDataTable({
  evento_actual <- evento_aplicado()
  proyecto_actual <- proyecto_aplicado()
  
  # Validar selección
  if (is.null(evento_actual) || is.null(proyecto_actual) ||
      (evento_actual == "" && proyecto_actual == "")) {
    return(DT::datatable(
      data.frame(Mensaje = "Seleccione un proyecto y/o evento"),
      options = list(dom = 't', ordering = FALSE, paging = FALSE),
      rownames = FALSE
    ))
  }
  
  # Filtrar datos
  sites_datos <- datos_actuales$tableSites
  iavh_datos <- datos_actuales$iavhdata
  
  if (proyecto_actual != "TODOS") {
    proyecto_num <- as.numeric(proyecto_actual)
    sites_datos <- sites_datos %>% filter(project_id == proyecto_num)
    iavh_datos <- iavh_datos %>% filter(project_id == proyecto_num)
  }
  
  if (evento_actual != "TODOS") {
    sites_datos <- sites_datos %>% filter(subproject_name == evento_actual)
    iavh_datos <- iavh_datos %>% filter(subproject_name == evento_actual)
  }
  
  # Calcular indicadores por período
  mostrar_consolidado <- (evento_actual == "TODOS")
  
  tabla_periodos <- calcular_indicadores_por_periodo(
    tableSites = sites_datos,
    iavhdata = iavh_datos,
    consolidado = mostrar_consolidado
  )
  
  # Renderizar tabla
  DT::datatable(
    tabla_periodos,
    options = list(
      dom = 't',
      ordering = FALSE,
      paging = FALSE,
      columnDefs = list(
        list(width = '20%', targets = 0),
        list(width = '9.7%', targets = 1:9)
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
    class = 'cell-border stripe hover compact'
  ) %>%
    DT::formatStyle(
      'Evento',
      fontWeight = DT::styleEqual('CONSOLIDADO', 'bold'),
      backgroundColor = DT::styleEqual('CONSOLIDADO', '#e8f4f8')
    ) %>%
    DT::formatCurrency(
      c("🗂️ Imágenes", "📸 Cámaras", "📅 Trampas/noche"),
      currency = "",
      digits = 0,
      mark = ","
    ) %>%
    DT::formatRound(
      c("🌿 Hill 1", "🌱 Hill 2", "🌳 Hill 3"),
      digits = 2
    )
})
```

**Características:**
- Tabla consolidada por períodos (subproject_name)
- Fila "CONSOLIDADO" destacada en negrita con fondo azul
- Formatos numéricos:
  - Enteros con separador de miles
  - Números de Hill con 2 decimales
- Sin paginación (todas las filas visibles)

---

### 10. Indicadores Numéricos (Value Boxes)

**Outputs de texto formateados:**

```r
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
```

---

### 11. Números de Hill (Diversidad)

**Outputs de índices de diversidad:**

```r
output$stat_hill1 <- renderText({
  tryCatch({
    indice <- calcular_numeros_hill(subRawData(), q = 0)
    if (is.na(indice)) return("—")
    format(indice, big.mark = ",", scientific = FALSE)
  }, error = function(e) "—")
})

output$stat_hill2 <- renderText({
  tryCatch({
    indice <- calcular_numeros_hill(subRawData(), q = 1)
    if (is.na(indice)) return("—")
    format(round(indice, 2), big.mark = ",", scientific = FALSE)
  }, error = function(e) "—")
})

output$stat_hill3 <- renderText({
  tryCatch({
    indice <- calcular_numeros_hill(subRawData(), q = 2)
    if (is.na(indice)) return("—")
    format(round(indice, 2), big.mark = ",", scientific = FALSE)
  }, error = function(e) "—")
})
```

**Significado:**
- **Hill 0:** Riqueza de especies (sensible a raras)
- **Hill 1:** Diversidad exponencial de Shannon (comunes + raras)
- **Hill 2:** Diversidad inversa de Simpson (comunes)

---

## Exportación de Dashboard

### Captura de Pantalla

**Observador del botón:**

```r
observeEvent(input$captureScreen, {
  # Generar nombre descriptivo
  proyecto_nombre <- if (is.null(input$project) || input$project == "" || input$project == "TODOS") {
    "Todos_proyectos"
  } else {
    gsub(" ", "_", input$project)
  }
  
  evento_nombre <- if (is.null(input$evento) || input$evento == "" || input$evento == "TODOS") {
    "Todos_eventos"
  } else {
    gsub(" ", "_", input$evento)
  }
  
  timestamp <- format(Sys.time(), "%Y%m%d_%H%M%S")
  filename <- paste0("Dashboard_", proyecto_nombre, "_", evento_nombre, "_", timestamp)
  
  # Enviar mensaje a JavaScript
  session$sendCustomMessage("capture_dashboard", list(filename = filename))
})
```

**Control de notificaciones:**

```r
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
```

### Código JavaScript (html2canvas)

**Funcionalidad:**

```javascript
Shiny.addCustomMessageHandler('capture_dashboard', function(message) {
  var filename = message.filename || 'Dashboard_Fototrampeo';
  
  html2canvas(document.body, {
    backgroundColor: '#ffffff',
    scale: 2,
    logging: false,
    useCORS: true,
    allowTaint: true
  }).then(function(canvas) {
    try {
      // Convertir a Blob
      canvas.toBlob(function(blob) {
        // Crear enlace temporal
        var url = URL.createObjectURL(blob);
        var link = document.createElement('a');
        link.href = url;
        link.download = filename + '.png';
        
        // Ejecutar descarga
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // Notificar éxito
        Shiny.setInputValue('capture_status', 'exitoso', {priority: 'event'});
      });
    } catch(error) {
      // Notificar error
      Shiny.setInputValue('capture_status', 'error: ' + error.message, {priority: 'event'});
    }
  }).catch(function(error) {
    Shiny.setInputValue('capture_status', 'error: ' + error.message, {priority: 'event'});
  });
});
```

**Características:**
- Renderiza todo el `<body>` del dashboard
- Resolución 2x (alta calidad)
- Soporte para imágenes externas (CORS)
- Descarga automática del archivo PNG
- Notificaciones de éxito/error a Shiny

---

## Inicialización de la Aplicación

**Código de lanzamiento:**

```r
shinyApp(
  ui = tagList(
    dashboardPage(
      dashboardHeader(disable = TRUE),
      dashboardSidebar(disable = TRUE),
      body
    ),
    # Inyectar JavaScript para captura
    tags$script(HTML(js_capture))
  ),
  server = server
)
```

**Configuración:**
- Layout sin header ni sidebar (dashboard de cuerpo completo)
- JavaScript personalizado inyectado en el HTML

---

## Flujo de Interacción del Usuario

### Caso 1: Visualización de un Proyecto Específico

1. Usuario selecciona proyecto en dropdown (ej: "2008342_Proyecto Guaviare")
2. Usuario hace clic en "Aplicar selección"
3. `observeEvent(input$aplicarSeleccion)` se dispara
4. Datos filtrados se almacenan en `datos_actuales`
5. Todos los reactivos (`subRawData()`, `subTableData()`, etc.) se actualizan
6. Visualizaciones se regeneran automáticamente:
   - Tabla de especies
   - Gráficos (ocupación, acumulación, actividad)
   - Mapa
   - Indicadores numéricos
   - Galería de imágenes

### Caso 2: Visualización de Evento Específico

1. Usuario selecciona evento (ej: "2024_2")
2. Usuario hace clic en "Aplicar selección"
3. [Flujo similar al Caso 1]
4. Datos filtrados solo incluyen observaciones de ese período

### Caso 3: Vista Consolidada de Todos los Proyectos y Eventos

1. Usuario selecciona "Todos los proyectos" y "Todos los eventos"
2. Usuario hace clic en "Aplicar selección"
3. Dashboard muestra estadísticas agregadas de toda la Red OTUS
4. Tabla de indicadores incluye fila "CONSOLIDADO" con totales

### Caso 4: Exportación de Reporte

1. Usuario configura filtros deseados
2. Usuario hace clic en "📸 Capturar dashboard"
3. JavaScript ejecuta `html2canvas()`
4. Navegador descarga archivo PNG con nombre descriptivo:
   - `Dashboard_Proyecto_2008342_Evento_2024_2_20251209_153045.png`
5. Notificación de éxito aparece en pantalla

---

## Buenas Prácticas Implementadas

### 1. Reactividad Eficiente

✅ **Uso de `reactiveValues()` para estado global**
- Evita recalcular datos filtrados en cada output
- Centraliza la lógica de filtrado

✅ **Uso de `reactiveVal()` para variables de control**
- Almacena valores aplicados (no valores actuales de input)
- Previene actualizaciones indeseadas

### 2. Manejo de Errores

✅ **`tryCatch()` en cálculos de diversidad**
```r
tryCatch({
  indice <- calcular_numeros_hill(subRawData(), q = 0)
  if (is.na(indice)) return("—")
  format(indice, big.mark = ",", scientific = FALSE)
}, error = function(e) "—")
```

✅ **Validaciones de existencia de datos**
```r
if (nrow(subRawData()) == 0) {
  return(data.frame(Mensaje = "Sin datos"))
}
```

### 3. Rendimiento

✅ **Supresión de mensajes de Plotly**
```r
options(
  plotly.message = FALSE,
  plotly.warning = FALSE
)
```

✅ **Límite de imágenes en carrusel**
```r
if (length(imagenes) > MAX_FAVORITES) {
  imagenes <- sample(imagenes, MAX_FAVORITES)
}
```

### 4. Experiencia de Usuario

✅ **Deshabilitación de botones según contexto**
```r
shinyjs::toggleState("aplicarSeleccion", condition = tiene_seleccion)
```

✅ **Mensajes informativos cuando no hay datos**
```r
tags$p(
  style = "text-align: center; color: #7f8c8d;",
  "Seleccione un proyecto y/o evento para visualizar datos"
)
```

✅ **Notificaciones de acciones**
```r
showNotification(
  "Dashboard exportado exitosamente como imagen PNG",
  type = "message",
  duration = 3
)
```

### 5. Accesibilidad

✅ **Emojis descriptivos en indicadores**
```
🗂️ Imágenes  📸 Cámaras  📅 Días-cámara
🏞️ Especies  🐆 Mamíferos  🦅 Aves
🌿 Hill 1  🌱 Hill 2  🌳 Hill 3
```

✅ **Nombres científicos en cursiva**
```css
font-style: italic;
```

---

## Estructura de Archivos del Proyecto

```
Dashboard_Monitoreo_Camaras_Trampa_Red_OTUS_Colombia/
├── 0_Documentation/
│   ├── README.md
│   ├── DOC_functions_data.md           # Este archivo
│   └── DOC_Dashboard_Vista_Proyectos.md  # Documentación del dashboard
│
├── 1_Data_RAW_WI/
│   ├── cameras.csv
│   ├── deployments.csv
│   ├── images_*.csv                     # 55 archivos
│   ├── projects.csv
│   └── sequences.csv
│
├── 2_Data_Shapefiles_CARs/
│   └── CAR_MPIO.*                        # Shapefiles de CARs
│
├── 3_processing_pipeline/
│   ├── process_RAW_data_WI.py           # Script de procesamiento
│   ├── requirements.txt
│   └── src/
│
├── 4_Dashboard/
│   ├── app.R                            # (Deprecado - usar Dashboard_Vista_Proyectos.R)
│   ├── Dashboard_Vista_Proyectos.R      # ← ARCHIVO PRINCIPAL
│   ├── functions_data.R                 # Funciones de análisis
│   ├── dashboard_input_data/
│   │   ├── observations.parquet         # Datos consolidados
│   │   ├── deployments.parquet
│   │   └── projects.parquet
│   └── www/
│       ├── css/
│       │   └── style.css                # Estilos personalizados
│       ├── fonts/
│       └── images/
│           ├── favorites/
│           │   ├── 2008342/             # Imágenes por proyecto
│           │   ├── 2008382/
│           │   └── ...
│           └── Logos/
```

---

## Solución de Problemas Comunes

### Error: "Paquete 'DT' no instalado"

**Solución:**
```r
install.packages("DT")
```

### Error: "Archivos parquet no encontrados"

**Solución:**
1. Ejecutar pipeline de procesamiento:
   ```bash
   cd 3_processing_pipeline
   python process_RAW_data_WI.py
   ```
2. Verificar que existan los 3 archivos en `4_Dashboard/dashboard_input_data/`:
   - `observations.parquet`
   - `deployments.parquet`
   - `projects.parquet`

### Problema: Selectores vacíos o con valores incorrectos

**Causa:** Arrow carga `subproject_name` como `category` (factor)

**Solución:** El código ya incluye conversión automática:
```r
iavhdata$subproject_name <- as.character(iavhdata$subproject_name)
```

### Problema: Galería de imágenes no muestra nada

**Verificar:**
1. Estructura de carpetas:
   ```
   www/images/favorites/
   ├── 2008342/
   │   ├── imagen1.jpg
   │   └── imagen2.png
   └── 2008382/
   ```
2. Formato de archivos (solo `.jpg`, `.jpeg`, `.png`)
3. Que el proyecto filtrado tenga carpeta correspondiente

### Problema: Captura de pantalla no funciona

**Verificar:**
1. Librería `html2canvas` cargada en HTML:
   ```html
   <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
   ```
2. Navegador compatible (Chrome, Firefox, Edge)
3. Consola del navegador para errores JavaScript

---

## Optimizaciones Futuras

### 1. Caché de Estadísticas Pre-calculadas

**Problema actual:**
- `makeSpeciesTable()` ejecuta `remove_duplicates()` en cada render
- `makeOccupancyGraph()` calcula ocupación en tiempo real

**Solución propuesta:**
```r
# Generar estadísticas al cargar datos
species_stats <- calcular_estadisticas_especies(iavhdata)
occupancy_stats <- calcular_estadisticas_ocupacion(iavhdata, tableSites)

# Usar en outputs
output$speciesTable <- DT::renderDataTable({
  makeSpeciesTable(
    subset = subRawData(),
    species_stats = species_stats  # ← Pre-calculado
  )
})
```

### 2. Lazy Loading de Imágenes

**Problema actual:**
- `favorite_images()` carga todas las rutas al cambiar filtro

**Solución propuesta:**
```r
# Cargar solo imágenes visibles en viewport
# Usar JavaScript IntersectionObserver
```

### 3. Exportación a PDF

**Tecnología:**
```r
library(webshot2)

# Generar PDF del dashboard
webshot2::webshot(
  url = "http://localhost:PORT",
  file = "Dashboard_Export.pdf",
  vwidth = 1920,
  vheight = 3000
)
```

### 4. Análisis Avanzado con iNEXT

**Integración futura:**
```r
library(iNEXT)

# Curvas de rarefacción/extrapolación
output$inext_plot <- renderPlot({
  datos_inext <- formatear_para_inext(subRawData())
  out <- iNEXT(datos_inext, q = c(0, 1, 2))
  ggiNEXT(out)
})
```

---

## Referencias Técnicas

### Shiny
- [Shiny Official Documentation](https://shiny.rstudio.com/)
- [shinydashboard Guide](https://rstudio.github.io/shinydashboard/)

### Visualización
- [Plotly R](https://plotly.com/r/)
- [Leaflet for R](https://rstudio.github.io/leaflet/)
- [DT Package](https://rstudio.github.io/DT/)

### Análisis de Biodiversidad
- Wildlife Insights: [wildlifeinsights.org](https://www.wildlifeinsights.org/)
- MacKenzie et al. (2002) - Occupancy Estimation
- Hill (1973) - Diversity Numbers
- Jost (2006) - Entropy and Diversity

---

## Créditos

**Desarrollo original:**
- Jorge Ahumada - Conservation International (2020)

**Adaptación y mantenimiento:**
- Cristian C. Acevedo - Instituto Humboldt (2025)

**Financiamiento:**
- Red OTUS Colombia
- Instituto Alexander von Humboldt
- Corporaciones Autónomas Regionales (CARs)

---

## Licencia

CC0 1.0 Universal (Public Domain)

---

## Contacto

**Soporte técnico:**
- Instituto Humboldt: [http://www.humboldt.org.co](http://www.humboldt.org.co)
- Red OTUS Colombia: [https://biodiversidad.co](https://biodiversidad.co)

---

**Última actualización:** 2025-12-09
