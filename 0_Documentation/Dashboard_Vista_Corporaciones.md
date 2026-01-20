# Dashboard Vista por Corporaciones - Red OTUS Colombia

## Información General

**Archivo:** `4_Dashboard/Dashboard_Vista_Corporaciones.R`  
**Versión:** 2.0 - Arquitectura consolidada Parquet  
**Fecha última modificación:** 2025-12-09  
**Autores:**  
- Jorge Ahumada © Conservation International (2020)  
- Cristian C. Acevedo - Instituto Humboldt (2025)

**Licencia:** CC0 1.0 Universal (Public Domain)

---

## Descripción

Dashboard interactivo desarrollado en R Shiny para la visualización y análisis de datos de fototrampeo de la **Red OTUS Colombia** (Red de Observación de la Biodiversidad con Cámaras Trampa). 

Esta vista permite analizar datos consolidados por **Corporaciones Autónomas Regionales (CARs)** y eventos de muestreo, proporcionando métricas operacionales, indicadores de biodiversidad y visualizaciones interactivas.

---

## Características Principales

### 1. Filtros Jerárquicos

El dashboard implementa un sistema de filtros en cascada:

1. **Corporación (filtro primario)**
   - Permite seleccionar una CAR específica o "Todas las corporaciones"
   - Valores disponibles: AMVA, CAM, CARDIQUE, CORPOCALDAS, etc.
   - Filtra automáticamente los datos espaciales y estadísticas

2. **Evento de muestreo (filtro secundario)**
   - Períodos temporales de muestreo (ejemplo: 2024_2, 2025_1)
   - Opción "Todos los eventos" para análisis consolidados
   - Se adapta a la corporación seleccionada

3. **Intervalo de independencia (filtro terciario)**
   - Opciones: 1 minuto, 30 minutos, 1 hora, 6 horas, 12 horas
   - Por defecto: 30 minutos (estándar ecológico)
   - Afecta el cálculo de registros independientes

### 2. Indicadores Operacionales y de Biodiversidad

**Métricas consolidadas:**
- 🗂️ **Imágenes totales**: Número total de fotografías capturadas
- 📸 **Cámaras**: Número de deployments (instalaciones de cámaras)
- 📅 **Trampas/noche**: Esfuerzo de muestreo en días-cámara
- 🏞️ **Especies totales**: Riqueza de especies observadas
- 🐆 **Mamíferos**: Especies de la clase Mammalia
- 🦅 **Aves**: Especies de la clase Aves

**Índices de diversidad (Números de Hill):**
- 🌿 **Hill 1 (q=0)**: Riqueza de especies (sin ponderación)
- 🌱 **Hill 2 (q=1)**: Especies efectivas (Shannon exponencial)
- 🌳 **Hill 3 (q=2)**: Especies muy abundantes (Simpson inverso)

### 3. Visualizaciones Interactivas

#### 3.1. Ranking de Especies
- Tabla interactiva con búsqueda y ordenamiento
- Columnas: Ranking, Nombre común, Nombre científico, Clase taxonómica
- Métricas: Número de imágenes, Registros independientes, Ocupación naive (% de sitios)
- Exportable a CSV con timestamp

#### 3.2. Gráfico de Ocupación
- Top 15 especies por ocupación naive
- Visualización horizontal de barras
- Colores por clase taxonómica (Mammalia, Aves, Otros)

#### 3.3. Curva de Acumulación de Especies
- Incremento de riqueza a través del tiempo
- Opción de suavizado de curva
- Visualización del esfuerzo de muestreo

#### 3.4. Patrón de Actividad Circadiano
- Gráfico interactivo Plotly (zoom, pan, tooltips)
- Distribución de actividad por hora del día (0-24h)
- Especies más frecuentes con códigos de color

#### 3.5. Mapa Geográfico Leaflet
- **Puntos de cámaras trampa**: Ubicación exacta de cada deployment
  - Marcadores circulares con borde blanco
  - Popup con información del sitio
  - Agrupación automática (clustering)

- **Polígono de jurisdicción CAR**: Visualización del área de competencia
  - Color: Azul claro (#ADD8E6) con 25% de opacidad
  - Borde: Línea punteada azul oscuro
  - Solo visible cuando se selecciona una corporación específica
  - Fuente: Shapefile `2_Data_Shapefiles_CARs/CAR_MPIO.shp`

### 4. Galería Multimedia

- Carrusel interactivo de imágenes destacadas (SlickR)
- Organización por carpetas:
  - **General**: `www/images/favorites/General/` (cuando se selecciona "Todas las corporaciones")
  - **Por CAR**: `www/images/favorites/{NOMBRE_CAR}/` (cuando se selecciona una corporación específica)
- Configuración:
  - Máximo 40 imágenes aleatorias por sesión
  - Autoplay cada 4 segundos
  - 5 imágenes visibles simultáneamente
  - Navegación con flechas y puntos indicadores

### 5. Exportación de Datos

#### 5.1. Descarga de Tabla de Especies (CSV)
- Formato: UTF-8 con separador de coma
- Nombre del archivo: `Ranking_Especies_{Corporacion}_{Evento}_{Timestamp}.csv`
- Incluye todas las columnas de la tabla interactiva

#### 5.2. Captura de Dashboard Completo (PNG)
- Tecnología: `html2canvas` (JavaScript, lado cliente)
- Resolución: 2x (alta calidad)
- Nombre del archivo: `Dashboard_{Corporacion}_{Evento}_{Timestamp}.png`
- **Limitación conocida**: Los tiles del mapa base de Leaflet y los polígonos SVG pueden no capturarse perfectamente debido a restricciones de html2canvas con contenido externo y canvas dinámicos

---

## Arquitectura de Datos

### Fuentes de Datos (Formato Parquet)

El dashboard consume tres archivos principales generados por `3_processing_pipeline/process_RAW_data_WI.py`:

1. **`dashboard_input_data/observations.parquet`**
   - Detecciones individuales de fauna
   - Columnas clave:
     - `Corporacion`: Sigla de la CAR (string)
     - `subproject_name`: Evento de muestreo (string, convertido desde factor)
     - `common_name`, `scientific_name`, `class`: Taxonomía
     - `timestamp`: Fecha y hora de detección
     - `latitude`, `longitude`: Coordenadas geográficas
     - `deployment_id`, `location`: Identificadores de sitio

2. **`dashboard_input_data/deployments.parquet`**
   - Configuración de cámaras trampa
   - Metadata de instalaciones (fechas, coordenadas, configuración)

3. **`dashboard_input_data/projects.parquet`**
   - Catálogo de corporaciones y eventos
   - Información de administradores y períodos temporales

### Shapefile de Corporaciones

**Archivo:** `2_Data_Shapefiles_CARs/CAR_MPIO.shp`

- **Proyección original**: Variable (generalmente MAGNA-SIRGAS Colombia)
- **Proyección transformada**: WGS84 (EPSG:4326) para compatibilidad con Leaflet
- **Columna clave**: `NOMBRE_CAR` (contiene siglas: AMVA, CAM, CARDIQUE, etc.)
- **Uso**: Visualización de límites jurisdiccionales en el mapa

### Flujo de Datos Reactivo

```
Selección de filtros (UI)
    ↓
Validación y habilitación de botón "Aplicar selección"
    ↓
Aplicación de filtros (observeEvent)
    ↓
Actualización de reactiveValues (evento_aplicado, corporacion_aplicada, intervalo_aplicado)
    ↓
Filtrado de datos (subRawData, subTableData, subSitesData)
    ↓
Cálculo de estadísticas consolidadas (consolidar_estadisticas_sitios)
    ↓
Renderizado de visualizaciones (tablas, gráficos, mapa, galería)
```

---

## Funciones Principales

### Funciones Internas del Dashboard

#### `consolidar_estadisticas_sitios(tableSites, nombre_proyecto)`

Consolida métricas operacionales y de biodiversidad de múltiples sitios.

**Parámetros:**
- `tableSites`: DataFrame con estadísticas por sitio (columnas: n, ndepl, effort, ospTot, etc.)
- `nombre_proyecto`: String identificador de la vista consolidada (formato: "Corporación - Evento")

**Retorna:**
- DataFrame con una fila única de totales consolidados:
  - Sumas: Imágenes, deployments, días-cámara, especies (total, mamíferos, aves)
  - Metadata: Nombre de vista, colector, departamento(s)
  - Rankings: No aplican (valores fijos en 1)

**Detalles:**
- Filtra registros válidos (`n > 0`)
- Maneja casos de datos vacíos (retorna estructura por defecto)
- Concatena departamentos únicos con separador de coma

#### `generar_nombre_consolidado(evento)`

Genera nombre estandarizado para vistas consolidadas.

**Parámetros:**
- `evento`: String identificador (no usado en arquitectura actual)

**Retorna:**
- String: "Red OTUS - Consolidado"

### Funciones Externas (functions_data.R)

#### `obtener_eventos_disponibles()`
Lista los eventos de muestreo disponibles en archivos parquet.

#### `cargar_datos_consolidados(interval)`
Carga y procesa archivos parquet con el intervalo de independencia especificado.

**Parámetros:**
- `interval`: String ("1min", "30min", "1h", "6h", "12h")

**Retorna:**
- Lista con elementos: `iavhdata`, `tableSites`, `projects`

#### `makeSpeciesTable(data, interval, unit, species_stats)`
Genera tabla de ranking de especies con métricas calculadas.

**Parámetros:**
- `data`: DataFrame de observaciones filtradas
- `interval`: Valor numérico de intervalo
- `unit`: Unidad de tiempo ("minutes", "hours")
- `species_stats`: NULL (cálculo automático) o DataFrame precalculado

#### `makeOccupancyGraph(data, top_n, interval, unit, occupancy_stats)`
Crea gráfico de barras horizontales de ocupación de especies.

#### `makeAccumulationCurve(data, smooth_curve, accumulation_curve)`
Genera curva de acumulación de especies a través del tiempo.

#### `makeActivityPattern(data, top_species, interval, unit, activity_stats)`
Crea gráfico Plotly de patrón de actividad circadiano (24h).

#### `makeMapLeaflet(sites_data, table_data, nsites, bounds, vista_descripcion)`
Renderiza mapa interactivo Leaflet con ubicación de cámaras.

**Parámetros:**
- `sites_data`: DataFrame con coordenadas y metadata de sitios
- `table_data`: DataFrame consolidado con estadísticas
- `nsites`: Número de sitios únicos
- `bounds`: DataFrame con límites geográficos (lat, lon)
- `vista_descripcion`: String descriptivo de la vista actual

#### `calcular_numeros_hill(data, q)`
Calcula índices de diversidad de Hill.

**Parámetros:**
- `data`: DataFrame de observaciones
- `q`: Orden del número de Hill (0, 1, 2)

**Retorna:**
- Valor numérico del índice (NA si no hay datos suficientes)

#### `calcular_indicadores_por_periodo(sites_datos, iavh_datos, mostrar_consolidado)`
Genera tabla de indicadores agrupados por evento de muestreo.

**Parámetros:**
- `sites_datos`: DataFrame de estadísticas de sitios (filtrado)
- `iavh_datos`: DataFrame de observaciones (filtrado)
- `mostrar_consolidado`: Boolean (TRUE = agregar fila CONSOLIDADO)

**Retorna:**
- DataFrame con columnas: Periodo, Imagenes, Camaras, Dias_camara, Especies, Mamiferos, Aves, Hill1, Hill2, Hill3

---

## Dependencias del Sistema

### Librerías R Requeridas

**Framework Shiny:**
```r
library(shiny)           # Framework web reactivo
library(shinydashboard)  # Componentes de dashboard
library(dashboardthemes) # Temas visuales
library(shinyjs)         # Control dinámico de UI
library(shinymanager)    # Autenticación (opcional - futuro)
```

**Visualización:**
```r
library(plotly)          # Gráficos interactivos (patrón de actividad)
library(leaflet)         # Mapas interactivos
library(sf)              # Manejo de datos espaciales (shapefiles)
library(DT)              # Tablas interactivas (CRÍTICO - ver INSTALL_DT.md)
```

**Multimedia:**
```r
library(slickR)          # Carrusel de imágenes
library(magick)          # Procesamiento de imágenes
library(cowplot)         # Composición de gráficos
```

**Procesamiento de datos:**
```r
library(dplyr)           # Manipulación de datos (implícito en functions_data.R)
library(arrow)           # Lectura de archivos Parquet (implícito)
```

### Instalación de Dependencias

```r
# Script de instalación completo
install.packages(c(
  "shiny", "shinydashboard", "dashboardthemes", "shinyjs", "shinymanager",
  "plotly", "leaflet", "sf", "DT",
  "slickR", "magick", "cowplot",
  "dplyr", "arrow"
))
```

**Nota crítica sobre DT:**
Si el paquete `DT` no está instalado, el dashboard **no funcionará**. Consultar `INSTALL_DT.md` para instrucciones detalladas.

### Librerías Opcionales (Futuro)

```r
# library(webshot2)      # Exportación HTML a imagen de alta calidad
# library(chromote)      # Backend de Chrome para webshot2
# library(iNEXT)         # Análisis avanzado de diversidad (extrapolación)
```

**Estado de webshot2:**
- Fue probado para mejorar la exportación de dashboard
- **Error crítico**: Timeout al intentar acceder a sesión Shiny activa
- **Decisión**: Revertido a `html2canvas` (JavaScript, lado cliente)
- **Limitación conocida**: html2canvas no captura perfectamente mapas Leaflet

---

## Configuración y Personalización

### Variables Globales

```r
MAX_FAVORITES <- 40                    # Límite de imágenes en carrusel
IMG_PATTERN <- "\\.(jpe?g|png)$"       # Formato de archivos válidos (JPEG/PNG)
```

### Rutas de Archivos

```r
# Datos procesados
"dashboard_input_data/observations.parquet"
"dashboard_input_data/deployments.parquet"
"dashboard_input_data/projects.parquet"

# Shapefiles
"../2_Data_Shapefiles_CARs/CAR_MPIO.shp"

# Imágenes favoritas
"www/images/favorites/General/"           # Vista consolidada
"www/images/favorites/{NOMBRE_CAR}/"      # Vista por CAR específica

# Logos
"www/images/Logos/Logos_instituciones.png"

# CSS personalizado
"www/css/style.css"
```

### Opciones de Plotly

```r
options(
  plotly.message = FALSE,  # Suprimir mensajes de inicialización
  plotly.warning = FALSE,  # Suprimir warnings
  plotly.verbose = FALSE   # Modo silencioso
)
```

### Estilo Visual del Polígono de CAR

```r
# Configuración en makeMapLeaflet() o renderLeaflet()
addPolygons(
  fillColor = "#ADD8E6",      # Azul claro
  fillOpacity = 0.25,         # 25% de opacidad
  color = "#4682B4",          # Borde azul oscuro
  weight = 2,                 # Grosor de borde
  dashArray = "5, 5",         # Línea punteada (5px línea, 5px espacio)
  highlightOptions = highlightOptions(
    weight = 3,
    color = "#1a5490",
    fillOpacity = 0.4,
    bringToFront = TRUE
  )
)
```

---

## Uso del Dashboard

### Inicio de la Aplicación

**Desde RStudio:**
1. Abrir el archivo `Dashboard_Vista_Corporaciones.R`
2. Hacer clic en el botón **"Run App"** (parte superior derecha del editor)
3. Seleccionar modo de visualización:
   - **"Run in Window"**: Ventana independiente
   - **"Run in Viewer Pane"**: Panel integrado de RStudio
   - **"Run External"**: Navegador web del sistema

**Desde consola R:**
```r
setwd("c:/Users/sense/Documents/Consultoria/Dashboard_Monitoreo_Camaras_Trampa_Red_OTUS_Colombia/4_Dashboard")
shiny::runApp()
```

**Desde terminal (alternativa):**
```bash
cd "c:\Users\sense\Documents\Consultoria\Dashboard_Monitoreo_Camaras_Trampa_Red_OTUS_Colombia\4_Dashboard"
Rscript -e "shiny::runApp()"
```

### Flujo de Trabajo Típico

1. **Seleccionar corporación:**
   - Elegir una CAR específica (ejemplo: CORPOCALDAS) o "Todas las corporaciones"
   - El mapa mostrará el polígono jurisdiccional si se selecciona una CAR específica

2. **Seleccionar evento de muestreo:**
   - Elegir un período temporal (ejemplo: 2024_2) o "Todos los eventos"
   - Para análisis longitudinales, seleccionar "Todos los eventos"

3. **Configurar intervalo de independencia:**
   - Por defecto: 30 minutos (estándar ecológico)
   - Ajustar según protocolo específico (1min, 1h, 6h, 12h)

4. **Aplicar selección:**
   - Hacer clic en el botón **"✓ Aplicar selección"**
   - El sistema carga y procesa los datos filtrados
   - Notificación confirma filtros aplicados

5. **Explorar visualizaciones:**
   - **Indicadores consolidados**: Revisar métricas operacionales y de biodiversidad
   - **Tabla de especies**: Buscar, ordenar y analizar ranking
   - **Gráficos**: Interpretar ocupación, acumulación y actividad
   - **Mapa**: Verificar ubicación de cámaras y polígono de CAR
   - **Galería**: Visualizar imágenes destacadas del muestreo

6. **Exportar resultados:**
   - **Tabla CSV**: Descargar ranking completo con timestamp
   - **Dashboard PNG**: Capturar vista completa para reportes

7. **Limpiar selección:**
   - Hacer clic en **"✕ Limpiar selección"** para restablecer filtros
   - El dashboard vuelve al estado inicial

### Casos de Uso Específicos

#### Análisis de una CAR específica (ejemplo: CORPOCALDAS)
1. Corporación: CORPOCALDAS
2. Evento: Todos los eventos
3. Intervalo: 30 minutos
4. **Resultado**: Consolidado histórico de CORPOCALDAS con polígono jurisdiccional visible

#### Comparación entre eventos
1. Corporación: CORPOCALDAS
2. Evento: Todos los eventos
3. **Resultado**: Tabla de indicadores mostrará filas separadas por evento + fila CONSOLIDADO

#### Análisis puntual de un muestreo
1. Corporación: CAM (Corporación Autónoma Regional del Alto Magdalena)
2. Evento: 2025_1
3. Intervalo: 30 minutos
4. **Resultado**: Vista detallada de un evento específico con polígono de CAM

#### Vista consolidada nacional
1. Corporación: Todas las corporaciones
2. Evento: Todos los eventos
3. **Resultado**: Estadísticas agregadas de toda la Red OTUS (sin polígono en mapa)

---

## Estructura del Código

### Organización del Archivo (1,717 líneas)

```
Líneas 1-15:      Encabezado y metadata del proyecto
Líneas 16-67:     Carga de librerías y configuración global
Líneas 68-143:    Funciones auxiliares (consolidar_estadisticas_sitios, generar_nombre_consolidado)
Líneas 144-193:   Carga de datos Parquet y shapefile
Líneas 194-246:   Preparación y conversión de tipos de datos (factor → character)
Líneas 247-281:   Preparación de selectores UI (eventos, corporaciones)
Líneas 282-597:   Definición de UI (body, boxes, controles, visualizaciones)
Líneas 598-1717:  Lógica del servidor (server function)
  Líneas 598-634:    Estado reactivo global (reactiveValues)
  Líneas 635-735:    Observadores de eventos UI (botones, validaciones)
  Líneas 736-854:    Datos filtrados reactivos (subRawData, subTableData, subSitesData)
  Líneas 855-1117:   Outputs de visualizaciones (tablas, gráficos, mapa, galería)
  Líneas 1118-1292:  Outputs de indicadores numéricos y tabla consolidada
  Líneas 1293-1580:  Outputs de metadatos y texto informativo
  Líneas 1581-1610:  Outputs de exportación (CSV, PNG)
Líneas 1611-1680:  Código JavaScript (html2canvas para captura de pantalla)
Líneas 1681-1717:  Inicialización de la aplicación Shiny
```

### Componentes Principales

#### Variables Reactivas (reactiveValues)

```r
datos_actuales <- reactiveValues(
  tableSites = tableSites,       # DataFrame de estadísticas de sitios
  iavhdata = iavhdata,           # DataFrame de observaciones individuales
  projects = projects_data,      # Catálogo de proyectos
  datos_filtrados = FALSE        # Flag de estado de filtros
)

evento_aplicado <- reactiveVal("")         # Evento actualmente visualizado
corporacion_aplicada <- reactiveVal("")    # Corporación actualmente visualizada
intervalo_aplicado <- reactiveVal("30min") # Intervalo de independencia activo
```

#### Observadores Clave

1. **Control de habilitación de botón "Aplicar selección":**
   - Habilita si hay corporación y/o evento seleccionado
   - Deshabilita si ambos están vacíos

2. **Control de habilitación de botones de exportación:**
   - Habilita si `datos_filtrados = TRUE` y hay registros
   - Deshabilita si no hay selección aplicada

3. **Botón "Limpiar selección":**
   - Resetea selectores a estado inicial
   - Limpia reactiveValues
   - Deshabilita todos los botones de acción

4. **Botón "Aplicar selección":**
   - Valida que al menos un filtro esté seleccionado
   - Actualiza reactiveValues con valores aplicados
   - Muestra notificación con resumen de filtros

#### Reactivos de Datos Filtrados

```r
subRawData() <- reactive({
  # 1. Validar que hay selección
  # 2. Filtrar por corporación (primaria)
  # 3. Filtrar por evento (secundaria)
  # 4. Retornar DataFrame de observaciones filtradas
})

subTableData() <- reactive({
  # 1. Aplicar mismos filtros que subRawData
  # 2. Consolidar estadísticas de sitios
  # 3. Retornar DataFrame con fila única de totales
})

subSitesData() <- reactive({
  # 1. Aplicar filtros a tableSites
  # 2. Retornar sitios individuales (no consolidados)
  # 3. Usado para mapa de ubicaciones
})
```

#### Outputs de Visualización

- **`output$speciesTable`**: Tabla DT interactiva con ranking de especies
- **`output$occupancyPlot`**: Gráfico de barras de ocupación (renderPlot)
- **`output$accumulationCurve`**: Curva de acumulación de especies (renderPlot)
- **`output$activityPattern`**: Patrón circadiano (renderPlotly)
- **`output$map`**: Mapa Leaflet con cámaras y polígono de CAR (renderLeaflet)
- **`output$cameraTrapImages`**: Carrusel de imágenes (renderSlickR)

---

## Resolución de Problemas

### Error: "Paquete requerido 'DT' no instalado"

**Causa:** La librería `DT` no está disponible.

**Solución:**
```r
install.packages("DT")
```

Consultar `INSTALL_DT.md` para detalles adicionales.

### Error: "Archivos parquet no encontrados"

**Causa:** No se ejecutó el pipeline de procesamiento de datos.

**Solución:**
1. Navegar a `3_processing_pipeline/`
2. Ejecutar:
   ```bash
   python process_RAW_data_WI.py
   ```
3. Verificar que se crearon los archivos en `4_Dashboard/dashboard_input_data/`

### Error: "Shapefile de CARs no encontrado"

**Causa:** El archivo `CAR_MPIO.shp` no está en la ruta esperada.

**Solución:**
1. Verificar que existe `2_Data_Shapefiles_CARs/CAR_MPIO.shp`
2. Confirmar que todos los archivos complementarios están presentes:
   - CAR_MPIO.shp
   - CAR_MPIO.shx
   - CAR_MPIO.dbf
   - CAR_MPIO.prj

**Impacto:** El dashboard funcionará sin el shapefile, pero no mostrará polígonos de CARs en el mapa.

### Warning: "Tipo de dato 'category' detectado"

**Causa:** Arrow carga columnas de texto como factores (`category`).

**Solución:** Ya implementada en el código:
```r
# Conversión automática a character
if ("subproject_name" %in% names(iavhdata)) {
  iavhdata$subproject_name <- as.character(iavhdata$subproject_name)
}
```

### Tabla de indicadores no se muestra correctamente

**Causa:** Problemas con filtros o datos vacíos.

**Diagnóstico:**
1. Verificar en consola R:
   ```r
   nrow(subRawData())    # Debe ser > 0
   nrow(subTableData())  # Debe ser >= 1
   ```
2. Confirmar que `datos_actuales$datos_filtrados == TRUE`

### Mapa no muestra polígono de CAR

**Verificar:**
1. ¿Se seleccionó una corporación específica? (No "Todas las corporaciones")
2. ¿El shapefile tiene la columna `NOMBRE_CAR`?
3. ¿El valor de la corporación coincide exactamente con el shapefile?

**Ejemplo:**
```r
# En iavhdata:
"CORPOCALDAS"

# En shapefile (CAR_MPIO$NOMBRE_CAR):
"CORPOCALDAS"  # Debe coincidir exactamente (case-sensitive)
```

### Exportación PNG no captura mapa completo

**Causa:** Limitación de `html2canvas` con mapas Leaflet.

**Soluciones alternativas:**
1. **Captura manual:**
   - Windows: `Win + Shift + S` (Recorte de pantalla)
   - Mac: `Cmd + Shift + 4`

2. **Exportación desde navegador:**
   - Botón derecho en mapa → "Inspeccionar"
   - Usar herramientas de desarrollo para captura completa

3. **Futuro (en desarrollo):**
   - Implementación de `webshot2` con servidor Shiny externo
   - Requiere configuración adicional de Chromote

---

## Notas de Desarrollo

### Historial de Versiones

**Versión 2.0 (2025-12-09):**
- Adaptación completa a vista por corporaciones (CARs)
- Implementación de polígonos jurisdiccionales en mapa
- Corrección de selectores y variables (conversión factor → character)
- Exportación de dashboard con html2canvas
- Reversión de webshot2 (timeout con sesiones Shiny)
- Actualización de comentarios inline para reflejar funcionalidad actual

**Versión 1.x (2020-2024):**
- Dashboard original por proyectos individuales
- Desarrollo de funciones de análisis (Jorge Ahumada)

### Decisiones de Diseño

#### ¿Por qué filtro jerárquico (Corporación → Evento)?

La estructura refleja la organización administrativa de la Red OTUS:
- **Corporación**: Entidad responsable (CAR)
- **Evento**: Período temporal de muestreo
- **Intervalo**: Parámetro metodológico

Este orden permite análisis flexibles:
- Consolidados por CAR (todos los eventos)
- Consolidados temporales (todas las CARs)
- Vista puntual (CAR específica + evento específico)

#### ¿Por qué usar `nombre_proyecto` si es vista de corporaciones?

**Motivo histórico:** Compatibilidad con `functions_data.R` original.

**Solución documentada:**
- Parámetro se mantiene como `nombre_proyecto` para no romper dependencias
- Comentarios aclarados: "identificador de la vista (corporación-evento)"
- Valor real: Concatenación `"Corporación - Evento"`

#### ¿Por qué html2canvas en lugar de webshot2?

**Pruebas realizadas:**
1. **html2canvas (JavaScript, lado cliente):**
   - ✅ Funciona sin configuración adicional
   - ✅ No requiere dependencias del servidor
   - ⚠️ Limitación: No captura mapas Leaflet perfectamente
   - ✅ Decisión: Solución estable para uso general

2. **webshot2 (R, lado servidor):**
   - ❌ Error: "Chromote: timed out waiting for response to command Page.navigate"
   - ❌ Causa: No puede acceder a URL temporal de sesión Shiny activa
   - ❌ Requiere configuración compleja de Chromote
   - ❌ Decisión: Revertido, no viable para entorno actual

### Pendientes y Mejoras Futuras

1. **Autenticación de usuarios:**
   - Implementar `shinymanager` para control de acceso
   - Roles diferenciados (administrador, analista, visitante)

2. **Exportación mejorada:**
   - Resolver captura de mapas Leaflet (investigar alternativas a html2canvas)
   - Exportación de reportes PDF completos

3. **Análisis avanzado de diversidad:**
   - Integrar librería `iNEXT` para extrapolación de curvas
   - Comparaciones estadísticas entre corporaciones/eventos

4. **Optimización de rendimiento:**
   - Cacheo de cálculos intensivos (números de Hill, curvas de acumulación)
   - Carga diferida de imágenes en galería

5. **Visualizaciones adicionales:**
   - Gráficos de comparación temporal (evolución de riqueza por año)
   - Mapas de calor de ocupación espacial
   - Análisis de co-ocurrencia de especies

---

## Referencias

### Fuentes de Datos

- **Wildlife Insights:** Plataforma global de gestión de datos de cámaras trampa
  - URL: https://www.wildlifeinsights.org/
  - Estructura de datos: Estándar Camtrap DP (Camera Trap Data Package)

### Metodología

- **Intervalo de independencia:** O'Brien, T. G., Kinnaird, M. F., & Wibisono, H. T. (2003). Crouching tigers, hidden prey: Sumatran tiger and prey populations in a tropical forest landscape. *Animal Conservation*, 6(2), 131-139.

- **Números de Hill:** Chao, A., Chiu, C. H., & Jost, L. (2014). Unifying species diversity, phylogenetic diversity, functional diversity, and related similarity and differentiation measures through Hill numbers. *Annual Review of Ecology, Evolution, and Systematics*, 45, 297-324.

### Tecnologías

- **R Shiny:** Chang, W., Cheng, J., Allaire, J., Xie, Y., & McPherson, J. (2021). *shiny: Web Application Framework for R*. R package version 1.7.1. https://CRAN.R-project.org/package=shiny

- **Leaflet:** Cheng, J., Karambelkar, B., & Xie, Y. (2021). *leaflet: Create Interactive Web Maps with the JavaScript 'Leaflet' Library*. R package version 2.0.4.1. https://CRAN.R-project.org/package=leaflet

- **Apache Arrow (Parquet):** Apache Software Foundation. (2021). *Apache Arrow*. https://arrow.apache.org/

---

## Contacto y Soporte

**Desarrollo y mantenimiento:**
- Cristian C. Acevedo - Instituto Humboldt
- Email: [Pendiente de actualizar]

**Proyecto Red OTUS Colombia:**
- Instituto de Investigación de Recursos Biológicos Alexander von Humboldt
- URL: [Pendiente de actualizar]

---

**Última actualización de esta documentación:** 2025-12-09
