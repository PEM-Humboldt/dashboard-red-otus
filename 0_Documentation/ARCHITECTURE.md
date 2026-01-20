# Arquitectura del Sistema - Red OTUS Colombia

## 📋 Tabla de Contenidos

- [Información General](#-información-general)
- [Visión General del Sistema](#-visión-general-del-sistema)
- [Arquitectura de Datos](#-arquitectura-de-datos)
- [Arquitectura de Componentes](#-arquitectura-de-componentes)
- [Flujo Completo de Datos](#-flujo-completo-de-datos)
- [Tecnologías y Stack](#-tecnologías-y-stack)
- [Patrones de Diseño](#-patrones-de-diseño)
- [Decisiones de Arquitectura](#-decisiones-de-arquitectura)
- [Escalabilidad y Rendimiento](#-escalabilidad-y-rendimiento)
- [Seguridad y Privacidad](#-seguridad-y-privacidad)

---

## 📌 Información General

**Sistema:** Plataforma de Monitoreo de Biodiversidad con Cámaras Trampa  
**Proyecto:** Red OTUS Colombia  
**Versión:** 2.0 (Arquitectura Consolidada Parquet)  
**Última actualización:** Enero 2025

### Propósito del Documento

Este documento describe la arquitectura técnica completa del sistema, incluyendo:
- Flujo de datos desde Wildlife Insights hasta dashboards
- Tecnologías utilizadas y justificación
- Decisiones de diseño y trade-offs
- Patrones arquitectónicos implementados

---

## 🎯 Visión General del Sistema

### Descripción de Alto Nivel

El sistema es una **plataforma integral de procesamiento, análisis y visualización** de datos de fototrampeo que transforma datos crudos de Wildlife Insights en dashboards interactivos para análisis de biodiversidad.

```
┌─────────────────────────────────────────────────────────────────┐
│                      WILDLIFE INSIGHTS                          │
│          (Plataforma global de cámaras trampa)                  │
└─────────────────────────────────────────────────────────────────┘
                             ↓ CSV Export
┌─────────────────────────────────────────────────────────────────┐
│                   CAPA DE ALMACENAMIENTO                         │
│                    (1_Data_RAW_WI/)                             │
│  • projects.csv                                                  │
│  • deployments.csv                                               │
│  • images_*.csv (múltiples archivos)                            │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                   CAPA DE PROCESAMIENTO                          │
│               (3_processing_pipeline/ - Python)                  │
│                                                                  │
│  Pipeline ETL Modular:                                           │
│    1. Extracción (concatenación de CSVs)                        │
│    2. Transformación (enriquecimiento, validación)              │
│    3. Carga (generación de Parquet)                             │
│                                                                  │
│  Módulos:                                                        │
│    • src/utils.py           (carga y filtrado)                  │
│    • src/transformations.py (enriquecimiento)                   │
│    • src/generate_parquets.py (generación Parquet)              │
│    • src/validation.py      (control de calidad)                │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                   CAPA DE DATOS PROCESADOS                       │
│              (4_Dashboard/dashboard_input_data/)                 │
│  • observations.parquet  (20 columnas, 500KB-5MB)               │
│  • deployments.parquet   (15 columnas, 50KB-200KB)              │
│  • projects.parquet      (10 columnas, 10KB-50KB)               │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                   CAPA DE PRESENTACIÓN                           │
│                  (4_Dashboard/ - R Shiny)                        │
│                                                                  │
│  ┌────────────────────┐          ┌────────────────────┐         │
│  │ Dashboard          │          │ Dashboard          │         │
│  │ Corporaciones      │          │ Proyectos          │         │
│  │ (Vista CARs)       │          │ (Vista Individual) │         │
│  └────────────────────┘          └────────────────────┘         │
│                                                                  │
│  Componentes Comunes:                                            │
│    • functions_data.R (análisis y visualización)                │
│    • www/css/style.css (estilos)                                │
│    • www/images/ (galería multimedia)                           │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                   CAPA DE USUARIO FINAL                          │
│  • Analistas de biodiversidad                                   │
│  • Administradores de CARs                                      │
│  • Investigadores                                                │
│  • Público general (futuro)                                     │
└─────────────────────────────────────────────────────────────────┘
```

### Principios de Diseño

1. **Separación de responsabilidades**
   - Pipeline Python: Procesamiento pesado de datos
   - Dashboards R: Visualización y análisis interactivo

2. **Modularidad**
   - Componentes independientes con interfaces claras
   - Facilita mantenimiento y testing

3. **Optimización de rendimiento**
   - Formato Parquet para lectura rápida
   - Cálculos precalculados en pipeline
   - Reactividad eficiente en Shiny

4. **Validación exhaustiva**
   - Control de calidad en cada etapa
   - Reportes automáticos de errores

5. **Extensibilidad**
   - Fácil agregar nuevas visualizaciones
   - Estructura preparada para nuevos análisis

---

## 📊 Arquitectura de Datos

### Modelo de Datos Conceptual

```
┌─────────────────────────────────────────────────────────────────┐
│                    MODELO CONCEPTUAL                             │
└─────────────────────────────────────────────────────────────────┘

                        PROJECT
                   ┌───────────────┐
                   │ project_id    │ PK
                   │ project_name  │
                   │ project_admin │
                   │ country       │
                   └───────┬───────┘
                           │ 1
                           │
                           │ N
                   ┌───────┴────────┐
                   │  DEPLOYMENT    │
                   ├────────────────┤
                   │ deployment_id  │ PK
                   │ project_id     │ FK
                   │ placename      │
                   │ latitude       │
                   │ longitude      │
                   │ start_date     │
                   │ end_date       │
                   └───────┬────────┘
                           │ 1
                           │
                           │ N
                   ┌───────┴────────────┐
                   │  OBSERVATION       │
                   ├────────────────────┤
                   │ observation_id     │ PK (implícito)
                   │ deployment_id      │ FK
                   │ sp_binomial        │
                   │ genus              │
                   │ species            │
                   │ class              │
                   │ common_name        │
                   │ photo_datetime     │
                   └────────────────────┘

        ┌────────────────────────────────────┐
        │         CORPORACION (CAR)          │
        │  (Asignada geográficamente)        │
        ├────────────────────────────────────┤
        │ NOMBRE_CAR                         │ PK
        │ geometry (POLYGON)                 │
        └──────────┬─────────────────────────┘
                   │ 1
                   │ contiene
                   │ N
           ┌───────┴─────────┐
           │   DEPLOYMENT    │
           │  (por coords)   │
           └─────────────────┘
```

### Esquema Lógico (Archivos Parquet)

#### `observations.parquet` (Tabla Principal)

**Grano:** Una fila por fotografía de fauna

**Columnas (20):**

| Columna | Tipo | Descripción | Ejemplo |
|---------|------|-------------|---------|
| `project_id` | int64 | ID del proyecto WI | 2008342 |
| `project_name` | string | Nombre del proyecto | "Fototrampeo CORPOCALDAS" |
| `Corporacion` | string | CAR asignada geográficamente | "CORPOCALDAS" |
| `subproject_name` | string | Evento de muestreo (YYYY_N) | "2024_2" |
| `deployment_name` | string | ID del sitio de muestreo | "CAM_Site001" |
| `placename` | string | Nombre descriptivo del sitio | "Bosque La Pradera" |
| `latitude` | float64 | Coordenada latitud WGS84 | 4.6542 |
| `longitude` | float64 | Coordenada longitud WGS84 | -74.1234 |
| `sp_binomial` | string | Nombre científico | "Panthera onca" |
| `genus` | string | Género taxonómico | "Panthera" |
| `species` | string | Epíteto específico | "onca" |
| `class` | string | Clase taxonómica | "Mammalia" |
| `common_name` | string | Nombre común | "Jaguar" |
| `photo_datetime` | datetime64 | Timestamp de captura | 2024-04-12 14:35:22 |
| `photo_date` | date32 | Fecha (sin hora) | 2024-04-12 |
| `hour` | int8 | Hora del día (0-23) | 14 |
| `deployment_days` | int16 | Días de funcionamiento | 45 |
| `admin_name` | string | Administrador del proyecto | "Juan Pérez" |
| `organization` | string | Organización responsable | "Instituto Humboldt" |
| `identified_by` | string | Tipo de identificación | "Human" / "Machine" |

**Índices (implícitos en Parquet):**
- Row groups por `project_id` (optimización de lectura)
- Estadísticas min/max por columna (predicate pushdown)

#### `deployments.parquet` (Metadata de Sitios)

**Grano:** Una fila por deployment (instalación de cámara)

**Columnas (15):**

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `deployment_id` | string | ID único del deployment |
| `deployment_name` | string | Nombre del sitio |
| `project_id` | int64 | FK a projects |
| `Corporacion` | string | CAR asignada |
| `subproject_name` | string | Evento de muestreo |
| `placename` | string | Nombre descriptivo |
| `latitude` | float64 | Coordenada lat |
| `longitude` | float64 | Coordenada lon |
| `deployment_start` | datetime64 | Fecha inicio |
| `deployment_end` | datetime64 | Fecha fin |
| `deployment_days` | int16 | Duración en días |
| `camera_id` | string | ID de la cámara física |
| `feature_type` | string | Tipo de hábitat |
| `bait` | string | Uso de cebo (Yes/No) |
| `quiet_period` | int16 | Período de silencio (segundos) |

#### `projects.parquet` (Catálogo de Proyectos)

**Grano:** Una fila por proyecto

**Columnas (10):**

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `project_id` | int64 | PK |
| `project_name` | string | Nombre del proyecto |
| `project_admin` | string | Responsable |
| `project_country` | string | País |
| `metadata_license` | string | Licencia de metadata |
| `embargo` | bool | Datos bajo embargo |
| `observation_license` | string | Licencia de observaciones |
| `sensor_height` | float32 | Altura del sensor (cm) |
| `sensor_orientation` | string | Orientación (N, S, E, W) |
| `detection_distance` | float32 | Distancia de detección (m) |

### Formato Parquet: Ventajas Técnicas

**1. Almacenamiento Columnar**

```
CSV (row-based):
Row 1: project_id=2008342, deployment_name=CAM001, genus=Panthera, ...
Row 2: project_id=2008342, deployment_name=CAM002, genus=Tapirus, ...
Row 3: project_id=2008342, deployment_name=CAM001, genus=Panthera, ...

Parquet (column-based):
Column project_id:       [2008342, 2008342, 2008342, ...]
Column deployment_name:  [CAM001, CAM002, CAM001, ...]
Column genus:            [Panthera, Tapirus, Panthera, ...]
```

**Ventajas:**
- ✅ Solo lee columnas necesarias (I/O reducido)
- ✅ Compresión más eficiente (valores similares juntos)
- ✅ Mejor cache locality (CPU)

**2. Compresión Snappy**

| Formato | Tamaño Típico | Ratio vs CSV |
|---------|---------------|--------------|
| CSV sin comprimir | 15 MB | 1.0x |
| CSV gzip | 3 MB | 5.0x |
| Parquet Snappy | 4.5 MB | 3.3x |

**Trade-off:** Snappy prioriza velocidad sobre máxima compresión
- ✅ 10x más rápido que gzip en descompresión
- ⚠️ ~30% menos compresión que gzip
- ✅ Ideal para dashboards interactivos

**3. Predicate Pushdown**

```r
# R código - lectura optimizada
library(arrow)

# Solo lee filas donde Corporacion == "CORPOCALDAS"
# Evita cargar datos innecesarios
obs <- read_parquet(
  "observations.parquet",
  col_select = c("common_name", "photo_datetime"),
  as_data_frame = TRUE
) %>%
  filter(Corporacion == "CORPOCALDAS")

# Parquet Statistics permiten filtrar sin leer todos los row groups
```

---

## 🧩 Arquitectura de Componentes

### Componente 1: Pipeline ETL (Python)

**Ubicación:** `3_processing_pipeline/`

**Responsabilidades:**
- Extraer datos de múltiples CSVs de Wildlife Insights
- Transformar y enriquecer datos (taxonomía, geografía, metadata)
- Validar calidad de datos
- Generar archivos Parquet optimizados

**Módulos:**

```
process_RAW_data_WI.py (Orquestador)
    ├─ Fase 0: Preparación entorno
    ├─ Fase 1: Carga de datos crudos
    ├─ Fase 2: Filtrado y limpieza
    ├─ Fase 3: Enriquecimiento
    ├─ Fase 4: Análisis geográfico
    ├─ Fase 5: Generación de Parquet
    └─ Fase 6: Validación de calidad

src/utils.py
    ├─ concatenar_archivos_csv()
    ├─ procesar_timestamps()
    ├─ filtrar_por_subproject_valido()
    └─ limpiar_registros_cv()

src/transformations.py
    ├─ crear_nombre_cientifico()
    ├─ agregar_metadata_administrativa()
    ├─ merge_images_deployments()
    ├─ merge_with_projects()
    ├─ asignar_corporacion_geografica()
    └─ calcular_deployment_days()

src/generate_parquets.py
    ├─ generar_observations_parquet()
    ├─ generar_deployments_parquet()
    ├─ generar_projects_parquet()
    └─ generar_todas_las_tablas()

src/validation.py
    ├─ validar_observations_parquet()
    ├─ validar_deployments_parquet()
    ├─ validar_projects_parquet()
    └─ generar_reporte_calidad()
```

**Dependencias:**
- `pandas` - Manipulación de datos
- `pyarrow` - Lectura/escritura Parquet
- `geopandas` - Análisis geoespacial
- `shapely` - Operaciones geométricas

### Componente 2: Capa de Análisis (R - functions_data.R)

**Ubicación:** `4_Dashboard/functions_data.R`

**Responsabilidades:**
- Cargar datos desde Parquet
- Calcular estadísticas de biodiversidad
- Generar visualizaciones
- Proporcionar API a dashboards

**Funciones Principales:**

```
Carga de Datos:
├─ obtener_eventos_disponibles()
├─ cargar_datos_consolidados(interval)
└─ extract_date_ymd(df)

Estadísticas de Biodiversidad:
├─ calcular_numeros_hill(data, q)
├─ calcular_ocupacion_naive(data)
├─ calcular_registros_independientes(data, interval, unit)
└─ calcular_indicadores_por_periodo(sites_datos, iavh_datos)

Visualizaciones:
├─ makeSpeciesTable(data, interval, unit)
├─ makeOccupancyGraph(data, top_n)
├─ makeAccumulationCurve(data, smooth_curve)
├─ makeActivityPattern(data, top_species)
└─ makeMapLeaflet(sites_data, table_data, nsites, bounds)

Utilidades:
└─ consolidar_estadisticas_sitios(tableSites, nombre_proyecto)
```

**Dependencias:**
- `arrow` - Lectura de Parquet
- `dplyr` - Manipulación de datos
- `plotly` - Gráficos interactivos
- `leaflet` - Mapas
- `sf` - Datos espaciales

### Componente 3: Dashboard por Corporaciones

**Ubicación:** `4_Dashboard/Dashboard_Vista_Corporaciones.R`

**Arquitectura Shiny:**

```
UI (shinydashboard)
├─ SECCIÓN 1: Encabezado
│   └─ Título dinámico
├─ SECCIÓN 2: Controles
│   ├─ Selector: Corporación (primario)
│   ├─ Selector: Evento de muestreo (secundario)
│   ├─ Selector: Intervalo de independencia
│   ├─ Botón: Aplicar selección
│   └─ Botón: Limpiar selección
├─ SECCIÓN 3: Indicadores
│   └─ Tabla DT: Indicadores por período
├─ SECCIÓN 4: Tabla de Especies
│   ├─ DT interactiva con búsqueda
│   └─ Botón: Descargar CSV
├─ SECCIÓN 5: Gráficos
│   ├─ Ocupación de especies
│   ├─ Curva de acumulación
│   ├─ Patrón de actividad (Plotly)
│   └─ Mapa Leaflet (con polígonos de CARs)
├─ SECCIÓN 6: Galería
│   └─ Carrusel SlickR
└─ SECCIÓN 7: Exportación
    └─ Botón: Captura de pantalla (PNG)

Server (reactive programming)
├─ Estado Reactivo Global
│   ├─ datos_actuales (reactiveValues)
│   ├─ evento_aplicado (reactiveVal)
│   ├─ corporacion_aplicada (reactiveVal)
│   └─ intervalo_aplicado (reactiveVal)
├─ Observadores de Eventos
│   ├─ Control habilitación de botones
│   ├─ Aplicar selección
│   └─ Limpiar selección
├─ Datos Filtrados Reactivos
│   ├─ subRawData() - Observaciones filtradas
│   ├─ subTableData() - Estadísticas consolidadas
│   └─ subSitesData() - Sitios para mapa
└─ Outputs Reactivos
    ├─ renderDataTable (tabla especies, indicadores)
    ├─ renderPlot (ocupación, acumulación)
    ├─ renderPlotly (actividad)
    ├─ renderLeaflet (mapa)
    ├─ renderSlickR (galería)
    └─ downloadHandler (CSV export)
```

**Patrón Reactivo:**

```r
# Flujo de reactividad
UI Input (selectInput) 
    → observeEvent (validar y aplicar filtros)
        → reactiveVal updated (corporacion_aplicada, evento_aplicado)
            → reactive() re-ejecuta (subRawData, subTableData)
                → renderOutput() re-renderiza (tablas, gráficos)
                    → UI Display actualizado
```

### Componente 4: Dashboard por Proyectos

**Ubicación:** `4_Dashboard/Dashboard_Vista_Proyectos.R`

**Diferencias clave vs Dashboard Corporaciones:**

| Característica | Vista Corporaciones | Vista Proyectos |
|----------------|---------------------|-----------------|
| **Filtro primario** | Corporación (CAR) | Proyecto individual |
| **Polígonos en mapa** | ✅ Jurisdicción CAR | ❌ No aplica |
| **Tabla consolidada** | Por períodos (eventos) | Limitada |
| **Uso principal** | Análisis administrativo | Análisis técnico |
| **Nivel de agregación** | CAR → Eventos | Proyecto → Eventos |

---

## 🔄 Flujo Completo de Datos

### Flujo End-to-End Detallado

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. ORIGEN: WILDLIFE INSIGHTS                                    │
│    Usuario exporta datos de proyectos Red OTUS                  │
│    Formato: CSV (Camtrap DP standard)                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓ Download
┌─────────────────────────────────────────────────────────────────┐
│ 2. ALMACENAMIENTO LOCAL: 1_Data_RAW_WI/                         │
│    • projects.csv           (~50 KB, 12 proyectos)              │
│    • deployments.csv        (~500 KB, 1200 deployments)         │
│    • cameras.csv            (~100 KB, metadata de cámaras)      │
│    • images_2008342.csv     (~5 MB, proyecto individual)        │
│    • images_2008382.csv                                         │
│    • ... (45 archivos images_*.csv)                             │
│    TOTAL: ~150 MB de CSVs crudos                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. PIPELINE PYTHON: process_RAW_data_WI.py                      │
│                                                                  │
│  FASE 1: Carga                                                   │
│    ├─ Leer projects.csv → DataFrame (12 filas)                  │
│    ├─ Leer deployments.csv → DataFrame (1200 filas)             │
│    └─ Concatenar images_*.csv → DataFrame (250,000 filas)       │
│        Tiempo: ~5 segundos                                       │
│                                                                  │
│  FASE 2: Filtrado                                                │
│    ├─ Procesar timestamps (ISO 8601 → datetime64)               │
│    ├─ Limpiar registros CV (Machine → descartados)              │
│    │   250,000 → 230,000 registros                              │
│    └─ Filtrar subproject_name inválidos                         │
│        230,000 → 175,000 registros                              │
│        Tiempo: ~3 segundos                                       │
│                                                                  │
│  FASE 3: Enriquecimiento                                         │
│    ├─ Crear sp_binomial (Genus + species)                       │
│    ├─ Agregar metadata administrativa                           │
│    ├─ Merge images + deployments (por deployment_id)            │
│    └─ Merge con projects (por project_id)                       │
│        Tiempo: ~8 segundos                                       │
│                                                                  │
│  FASE 4: Análisis Geográfico                                    │
│    ├─ Cargar shapefile CAR_MPIO.shp (geopandas)                 │
│    ├─ Crear geometrías Point(lon, lat)                          │
│    ├─ Spatial join (point-in-polygon)                           │
│    │   1200 deployments → 1150 con CAR asignada                 │
│    └─ Agregar columna Corporacion a observations                │
│        Tiempo: ~18 segundos (fase más lenta)                     │
│                                                                  │
│  FASE 5: Generación Parquet                                     │
│    ├─ Seleccionar 20 columnas → observations.parquet            │
│    │   175,000 filas × 20 cols = 3.5 MB (snappy)                │
│    ├─ Seleccionar 15 columnas → deployments.parquet             │
│    │   1200 filas × 15 cols = 185 KB                            │
│    └─ Seleccionar 10 columnas → projects.parquet                │
│        12 filas × 10 cols = 12 KB                               │
│        Tiempo: ~2 segundos                                       │
│                                                                  │
│  FASE 6: Validación                                             │
│    ├─ Verificar columnas obligatorias                           │
│    ├─ Validar completitud (% nulos)                             │
│    ├─ Verificar rangos de valores                               │
│    └─ Generar reporte de calidad                                │
│        Tiempo: ~1 segundo                                        │
│                                                                  │
│  TOTAL: ~45 segundos para 175,000 observaciones                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. DATOS PROCESADOS: dashboard_input_data/                      │
│    • observations.parquet   (3.5 MB)   ✓                        │
│    • deployments.parquet    (185 KB)   ✓                        │
│    • projects.parquet       (12 KB)    ✓                        │
│    TOTAL: ~3.7 MB (reducción 97.5% vs CSVs crudos)             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. DASHBOARD R SHINY: Inicio de Aplicación                      │
│                                                                  │
│  Carga Inicial (una sola vez al abrir dashboard):               │
│    ├─ library(shiny, arrow, dplyr, plotly, leaflet)             │
│    ├─ source("functions_data.R")                                │
│    ├─ cargar_datos_consolidados(interval="30min")               │
│    │   ├─ read_parquet("observations.parquet")                  │
│    │   │   → 175,000 filas cargadas en ~0.8 segundos            │
│    │   ├─ read_parquet("deployments.parquet")                   │
│    │   │   → 1200 filas cargadas en ~0.1 segundos               │
│    │   └─ read_parquet("projects.parquet")                      │
│    │       → 12 filas cargadas en ~0.05 segundos                │
│    ├─ Convertir factor → character (subproject_name, Corporacion)│
│    ├─ Cargar shapefile CAR_MPIO.shp (sf)                        │
│    │   → Transformar a WGS84 (st_transform)                     │
│    └─ Preparar selectores UI (eventos, corporaciones)           │
│        Tiempo total carga: ~2.5 segundos                         │
│                                                                  │
│  Estado Inicial Dashboard:                                       │
│    ├─ Selectores habilitados, sin datos filtrados               │
│    └─ Visualizaciones muestran mensaje "Seleccione filtros"     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. INTERACCIÓN USUARIO: Aplicar Filtros                         │
│                                                                  │
│  Usuario selecciona:                                             │
│    ├─ Corporación: "CORPOCALDAS"                                │
│    ├─ Evento: "2024_2"                                          │
│    └─ Intervalo: "30min"                                        │
│                                                                  │
│  Click en "Aplicar selección":                                   │
│    ├─ observeEvent() detecta click                              │
│    ├─ Actualiza reactiveValues:                                 │
│    │   corporacion_aplicada("CORPOCALDAS")                      │
│    │   evento_aplicado("2024_2")                                │
│    │   intervalo_aplicado("30min")                              │
│    │   datos_actuales$datos_filtrados <- TRUE                   │
│    └─ Muestra notificación "Selección aplicada"                 │
│        Tiempo: <100 ms                                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 7. PROCESAMIENTO REACTIVO: Filtrado de Datos                    │
│                                                                  │
│  subRawData() reactive se ejecuta:                               │
│    ├─ data <- datos_actuales$iavhdata (175,000 filas)           │
│    ├─ Filtrar: Corporacion == "CORPOCALDAS"                     │
│    │   175,000 → 45,000 filas                                   │
│    ├─ Filtrar: subproject_name == "2024_2"                      │
│    │   45,000 → 12,000 filas                                    │
│    └─ return(data)                                              │
│        Tiempo: ~200 ms                                           │
│                                                                  │
│  subTableData() reactive se ejecuta:                             │
│    ├─ Aplicar mismos filtros a tableSites                       │
│    ├─ consolidar_estadisticas_sitios()                          │
│    │   → Sumar imágenes, deployments, especies                  │
│    └─ return(DataFrame con fila única)                          │
│        Tiempo: ~50 ms                                            │
│                                                                  │
│  subSitesData() reactive se ejecuta:                             │
│    ├─ Filtrar tableSites por corporación + evento               │
│    └─ return(DataFrame con sitios individuales para mapa)       │
│        Tiempo: ~30 ms                                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 8. RENDERIZADO DE VISUALIZACIONES                               │
│                                                                  │
│  Tabla de Especies (renderDataTable):                           │
│    ├─ makeSpeciesTable(subRawData(), interval=30, unit="minutes")│
│    │   ├─ Calcular registros independientes (30 min)            │
│    │   ├─ Agrupar por sp_binomial                               │
│    │   ├─ Calcular ocupación naive (% sitios)                   │
│    │   └─ Ordenar por ranking                                   │
│    ├─ DT::datatable() con opciones interactivas                 │
│    └─ Tiempo: ~300 ms para 87 especies                          │
│                                                                  │
│  Gráfico de Ocupación (renderPlot):                             │
│    ├─ makeOccupancyGraph(subRawData(), top_n=15)                │
│    │   ├─ Calcular % ocupación por especie                      │
│    │   ├─ Seleccionar top 15                                    │
│    │   └─ ggplot2 barplot horizontal                            │
│    └─ Tiempo: ~400 ms                                            │
│                                                                  │
│  Curva de Acumulación (renderPlot):                             │
│    ├─ makeAccumulationCurve(subRawData(), smooth=TRUE)          │
│    │   ├─ Ordenar por fecha                                     │
│    │   ├─ Acumular especies únicas                              │
│    │   └─ Suavizar con loess                                    │
│    └─ Tiempo: ~500 ms                                            │
│                                                                  │
│  Patrón de Actividad (renderPlotly):                            │
│    ├─ makeActivityPattern(subRawData(), top_species=5)          │
│    │   ├─ Extraer hora del día                                  │
│    │   ├─ Agrupar por especie + hora                            │
│    │   └─ plotly::plot_ly() interactivo                         │
│    └─ Tiempo: ~600 ms                                            │
│                                                                  │
│  Mapa Leaflet (renderLeaflet):                                  │
│    ├─ makeMapLeaflet(subSitesData(), ...)                       │
│    │   ├─ Crear marcadores de deployments                       │
│    │   └─ addTiles() capa base                                  │
│    ├─ Agregar polígono de CORPOCALDAS                           │
│    │   ├─ Filtrar car_shapefile por NOMBRE_CAR                  │
│    │   └─ addPolygons(fillColor="#ADD8E6", opacity=0.25)        │
│    └─ Tiempo: ~800 ms                                            │
│                                                                  │
│  Galería (renderSlickR):                                         │
│    ├─ Buscar imágenes en www/images/favorites/CORPOCALDAS/      │
│    ├─ Seleccionar aleatoriamente max 40 imágenes                │
│    └─ slickR() con autoplay                                     │
│        Tiempo: ~200 ms                                           │
│                                                                  │
│  TOTAL RENDERIZADO: ~2.8 segundos                               │
│  (Usuario percibe <1 segundo por progresividad)                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 9. USUARIO FINAL: Dashboard Completo Visible                    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ 🏛️ CORPOCALDAS - 2024_2                                     │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │ 📊 Indicadores:                                             │ │
│  │   • Imágenes: 12,234                                        │ │
│  │   • Cámaras: 45                                             │ │
│  │   • Especies: 87                                            │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │ 📋 Tabla de Especies (87 registros)                        │ │
│  │   [Búsqueda interactiva, ordenamiento, descarga CSV]       │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │ 📈 Gráficos:                                                │ │
│  │   • Ocupación de especies (top 15)                         │ │
│  │   • Curva de acumulación (87 especies)                     │ │
│  │   • Patrón de actividad (5 especies más frecuentes)        │ │
│  │   • Mapa con 45 cámaras + polígono CORPOCALDAS             │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │ 🎠 Galería: 40 imágenes destacadas (autoplay)              │ │
│  ├────────────────────────────────────────────────────────────┤ │
│  │ 📤 Exportar:                                                │ │
│  │   • [Descargar Tabla CSV]                                  │ │
│  │   • [Capturar Dashboard PNG]                               │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 10. EXPORTACIÓN: Usuario descarga resultados                    │
│                                                                  │
│  Opción A: Descargar Tabla CSV                                  │
│    ├─ makeSpeciesTable() genera DataFrame                       │
│    ├─ write.csv() con encoding UTF-8                            │
│    ├─ Nombre: Ranking_Especies_CORPOCALDAS_2024_2_20250109.csv │
│    └─ Descarga automática                                       │
│        Tiempo: ~500 ms                                           │
│                                                                  │
│  Opción B: Capturar Dashboard PNG                               │
│    ├─ JavaScript: html2canvas(document.body)                    │
│    ├─ Renderizar dashboard completo a canvas                    │
│    │   (Limitación: Leaflet tiles pueden no capturarse)         │
│    ├─ Convertir canvas a PNG (base64)                           │
│    ├─ Nombre: Dashboard_CORPOCALDAS_2024_2_20250109.png         │
│    └─ Descarga automática                                       │
│        Tiempo: ~3-5 segundos (depende de complejidad)           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 💡 Patrones de Diseño

### 1. ETL Pipeline (Extract, Transform, Load)

**Implementación:** `process_RAW_data_WI.py`

**Patrón:**
```python
def main():
    # Extract
    data = extract_from_sources()
    
    # Transform
    data = transform_and_enrich(data)
    
    # Load
    load_to_parquet(data)
```

**Beneficios:**
- ✅ Separación clara de responsabilidades
- ✅ Facilita testing unitario
- ✅ Permite paralelización futura

### 2. Reactive Programming (Shiny)

**Implementación:** Dashboards R

**Patrón:**
```r
# Estado reactivo
datos_actuales <- reactiveValues(...)

# Observador de eventos
observeEvent(input$aplicar, {
    datos_actuales$filtrado <- TRUE
})

# Cálculo reactivo
subData <- reactive({
    filter(datos_actuales$data, ...)
})

# Renderizado reactivo
output$table <- renderDataTable({
    makeTable(subData())
})
```

**Beneficios:**
- ✅ Actualización automática de UI
- ✅ Evita cálculos innecesarios
- ✅ Código declarativo y mantenible

### 3. Repository Pattern (Capa de Datos)

**Implementación:** `functions_data.R`

**Patrón:**
```r
# Interfaz de acceso a datos
cargar_datos_consolidados <- function(interval) {
    # Abstrae fuente de datos (Parquet)
    obs <- arrow::read_parquet("observations.parquet")
    deps <- arrow::read_parquet("deployments.parquet")
    
    # Retorna estructura consistente
    list(
        iavhdata = obs,
        tableSites = deps
    )
}
```

**Beneficios:**
- ✅ Cambio de fuente de datos sin afectar dashboards
- ✅ Consistencia en estructura de datos
- ✅ Facilita mocking en tests

### 4. Strategy Pattern (Cálculo de Intervalos)

**Implementación:** `functions_data.R`

**Patrón:**
```r
calcular_registros_independientes <- function(data, interval, unit) {
    # Estrategia configurable para filtrado temporal
    switch(unit,
        "minutes" = filtrar_por_minutos(data, interval),
        "hours" = filtrar_por_horas(data, interval),
        "days" = filtrar_por_dias(data, interval)
    )
}
```

**Beneficios:**
- ✅ Fácil agregar nuevos criterios
- ✅ Configuración dinámica desde UI
- ✅ Testing independiente de cada estrategia

---

## 🎨 Decisiones de Arquitectura

### Decisión 1: Python para ETL, R para Visualización

**Contexto:**
- Datos crudos requieren procesamiento pesado
- Visualizaciones necesitan ser interactivas

**Opciones Consideradas:**
1. Todo en R (R + shiny + data.table)
2. Todo en Python (pandas + Dash/Streamlit)
3. **Híbrido: Python ETL + R Shiny** ✅

**Decisión:** Híbrido

**Justificación:**
- ✅ Python pandas: Mejor rendimiento en transformaciones masivas
- ✅ GeoPandas: Análisis geoespacial robusto
- ✅ R Shiny: Ecosistema maduro de visualización ecológica
- ✅ Comunidad R: Más familiaridad en ecólogos/analistas

**Trade-offs:**
- ⚠️ Dos lenguajes aumentan complejidad de setup
- ⚠️ Requiere mantener dos entornos

### Decisión 2: Parquet sobre CSV/RDS

**Contexto:**
- Dashboards deben cargar rápido (<3 segundos)
- Datos moderadamente grandes (100K-1M registros)

**Opciones Consideradas:**
1. CSV (formato original Wildlife Insights)
2. RDS (formato nativo R)
3. SQLite (base de datos embebida)
4. **Parquet** ✅

**Decisión:** Parquet

**Justificación:**
- ✅ 70% más pequeño que CSV
- ✅ 10-100x más rápido en lectura que CSV
- ✅ Compatible con Python (pyarrow) y R (arrow)
- ✅ Preserva tipos de datos
- ✅ Soporta filtrado columnar (predicate pushdown)

**Trade-offs:**
- ⚠️ No es human-readable (vs CSV)
- ⚠️ Requiere librería específica (arrow)

### Decisión 3: Dashboards Separados (Corporaciones vs Proyectos)

**Contexto:**
- Usuarios diferentes: administradores CARs vs investigadores
- Necesidades de análisis diferentes

**Opciones Consideradas:**
1. Dashboard único con switch de modo
2. **Dos dashboards independientes** ✅

**Decisión:** Dashboards separados

**Justificación:**
- ✅ Código más simple y mantenible
- ✅ UX especializada por usuario
- ✅ Permite optimizaciones específicas
- ✅ Facilita testing independiente

**Trade-offs:**
- ⚠️ Duplicación de código común (mitigado con functions_data.R)

### Decisión 4: Análisis Geoespacial en Pipeline Python

**Contexto:**
- Asignación de CARs requiere spatial join
- Se ejecuta una sola vez (no por usuario)

**Opciones Consideradas:**
1. Cálculo en dashboard R (sf package)
2. **Precálculo en pipeline Python** ✅
3. Servicio web externo

**Decisión:** Precálculo en pipeline

**Justificación:**
- ✅ GeoPandas más rápido que sf
- ✅ No afecta tiempo de carga del dashboard
- ✅ Resultado almacenado en Parquet (columna Corporacion)
- ✅ Un cálculo para miles de visualizaciones

**Trade-offs:**
- ⚠️ Cambios en shapefile requieren re-ejecutar pipeline

### Decisión 5: html2canvas sobre webshot2 para Exportación

**Contexto:**
- Usuarios solicitan exportar dashboard completo
- webshot2 dio timeout en sesión Shiny activa

**Opciones Consideradas:**
1. webshot2 (R, backend Chrome)
2. **html2canvas (JavaScript, cliente)** ✅
3. Exportación manual (screenshot del OS)

**Decisión:** html2canvas

**Justificación:**
- ✅ Funciona sin configuración adicional
- ✅ No requiere dependencias del servidor
- ✅ Captura estado actual del DOM
- ✅ Implementación simple (50 líneas JS)

**Trade-offs:**
- ⚠️ No captura perfectamente mapas Leaflet (limitación técnica)
- ⚠️ Calidad inferior a webshot2

**Documentado en:**
- `Dashboard_Vista_Corporaciones.md` línea ~1615
- Comentario explícito sobre limitación

---

## 🚀 Escalabilidad y Rendimiento

### Capacidad Actual

| Métrica | Capacidad Actual | Límite Práctico |
|---------|------------------|-----------------|
| **Observaciones** | 175,000 | ~1,000,000 |
| **Proyectos** | 12 | ~100 |
| **Eventos** | 8 | ~50 |
| **Deployments** | 1,200 | ~10,000 |
| **Usuarios Concurrentes** | 1 (local) | 5-10 (servidor) |

### Bottlenecks Identificados

**1. Análisis Geoespacial (Pipeline)**
- Tiempo: ~18 segundos (40% del pipeline)
- Escalabilidad: O(n × m) donde n=deployments, m=polígonos
- **Solución futura:** Usar índice espacial R-tree explícito

**2. Renderizado Inicial de Dashboard**
- Tiempo: ~2.5 segundos
- Escalabilidad: Lineal con tamaño de Parquet
- **Solución futura:** Lazy loading de visualizaciones

**3. Filtrado Reactivo**
- Tiempo: ~200 ms por filtro aplicado
- Escalabilidad: Lineal con número de observaciones
- **Solución actual:** Adecuado hasta 1M registros

### Estrategias de Optimización

**Implementadas:**
- ✅ Formato Parquet columnar
- ✅ Filtrado temprano en pipeline
- ✅ Conversión factor → character (evita warnings)
- ✅ Reactive caching en Shiny

**Planificadas:**
- 🔄 Particionamiento de Parquet por proyecto_id
- 🔄 Pre-agregación de estadísticas comunes
- 🔄 Implementación de Shiny Server para múltiples usuarios
- 🔄 CDN para assets estáticos (imágenes, CSS)

---

## 🔒 Seguridad y Privacidad

### Consideraciones Actuales

**1. Datos de Biodiversidad**
- ⚠️ Coordenadas exactas de especies amenazadas
- ✅ Embargo support en projects.parquet (columna `embargo`)
- ⚠️ No implementado fuzzing de coordenadas sensibles

**2. Licenciamiento**
- ✅ CC0 para código (public domain)
- ✅ Respeto a licenses de Wildlife Insights
- ✅ Columnas `metadata_license` y `observation_license` preservadas

**3. Acceso a Datos**
- ⚠️ Dashboards actuales no tienen autenticación
- ✅ Infraestructura lista para `shinymanager` (librería cargada)

### Roadmap de Seguridad

**Corto plazo:**
1. Implementar autenticación con `shinymanager`
2. Fuzzing automático de coordenadas para especies en IUCN Red List

**Mediano plazo:**
3. Sistema de permisos por corporación
4. Audit log de accesos

**Largo plazo:**
5. Encriptación de datos sensibles en reposo
6. API con OAuth2 para acceso programático

---

<div align="center">

**Última actualización:** Enero 2025  
**Versión de arquitectura:** 2.0 (Arquitectura Consolidada Parquet)

</div>
