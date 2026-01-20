# 📷 Sistema de Monitoreo de Biodiversidad con Cámaras Trampa - Red OTUS Colombia

<div align="center">

![Estado](https://img.shields.io/badge/Estado-Producción-brightgreen)
![Versión](https://img.shields.io/badge/Versión-2.0-blue)
![Licencia](https://img.shields.io/badge/Licencia-CC0%201.0-lightgrey)
![R](https://img.shields.io/badge/R-4.0+-276DC3?logo=r)
![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python)

**Plataforma completa de procesamiento, análisis y visualización de datos de fototrampeo**  
*Wildlife Insights → Pipeline ETL → Dashboards Interactivos*

[Instalación](#-instalación) • [Uso](#-uso-rápido) • [Documentación](#-documentación) • [Arquitectura](#-arquitectura)

</div>

---

## 📋 Tabla de Contenidos

- [Descripción](#-descripción)
- [Características](#-características-principales)
- [Requisitos del Sistema](#-requisitos-del-sistema)
- [Instalación](#-instalación)
- [Uso Rápido](#-uso-rápido)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Flujo de Trabajo](#-flujo-de-trabajo)
- [Dashboards Disponibles](#-dashboards-disponibles)
- [Documentación](#-documentación)
- [Arquitectura Técnica](#-arquitectura-técnica)
- [Contribuir](#-contribuir)
- [Licencia](#-licencia)
- [Autoría](#-autoría)
- [Créditos](#-créditos)

---

## 🎯 Descripción

El **Sistema de Monitoreo de Biodiversidad con Cámaras Trampa** es una plataforma integral desarrollada para la **Red OTUS Colombia** (Red de Observación de la Biodiversidad con Cámaras Trampa). El sistema permite:

- **Procesar** datos masivos de fototrampeo desde Wildlife Insights
- **Transformar** archivos CSV a formato Parquet optimizado
- **Analizar** métricas operacionales y de biodiversidad
- **Visualizar** resultados en dashboards interactivos
- **Exportar** reportes en formatos PNG y CSV

### 🌟 ¿Qué Incluye?

| Componente | Descripción | Tecnología |
|------------|-------------|------------|
| **Pipeline ETL** | Procesamiento de datos crudos de Wildlife Insights | Python 3.8+ |
| **Dashboard por Proyectos** | Visualización de datos por proyecto individual | R Shiny |
| **Dashboard por Corporaciones** | Análisis consolidado por CARs (Corporaciones Autónomas Regionales) | R Shiny |
| **Análisis Espacial** | Asignación automática de jurisdicciones CARs por coordenadas | GeoPandas |
| **Exportación** | Generación de reportes visuales y tablas de datos | html2canvas, DT |

---

## ✨ Características Principales

### 🔄 Pipeline de Procesamiento (Python)

- ✅ **Carga masiva** de archivos CSV desde Wildlife Insights
- ✅ **Validación automática** de formatos y calidad de datos
- ✅ **Filtrado inteligente** por eventos de muestreo (formato YYYY_N)
- ✅ **Enriquecimiento de datos** con taxonomía y metadata administrativa
- ✅ **Análisis geoespacial** con asignación de CARs por polígonos
- ✅ **Generación de Parquet** optimizado para lectura rápida
- ✅ **Reportes de calidad** con estadísticas detalladas

### 📊 Dashboards Interactivos (R Shiny)

**Análisis Operacional:**
- 🗂️ Número total de imágenes capturadas
- 📸 Cantidad de cámaras trampa desplegadas
- 📅 Esfuerzo de muestreo (trampas/noche)
- 🏞️ Riqueza de especies observadas (total, mamíferos, aves)

**Indicadores de Biodiversidad:**
- 🌿 **Números de Hill** (q=0, q=1, q=2) para diversidad efectiva
- 📈 **Curva de acumulación** de especies a través del tiempo
- 📊 **Ocupación naive** (proporción de sitios con detección)
- 🕒 **Patrón de actividad circadiano** (distribución 24 horas)

**Visualizaciones:**
- 🗺️ **Mapa interactivo Leaflet** con ubicación de cámaras y polígonos de CARs
- 📋 **Tabla de especies** con búsqueda, ordenamiento y exportación CSV
- 📸 **Galería multimedia** con carrusel de imágenes destacadas
- 📊 **Gráficos interactivos Plotly** con zoom y tooltips

**Funcionalidades Avanzadas:**
- 🎚️ **Filtros jerárquicos** (Corporación → Evento → Intervalo de independencia)
- 🔄 **Análisis multi-evento** con vistas consolidadas
- 🖼️ **Exportación de dashboard completo** a imagen PNG
- 📥 **Descarga de tablas** en formato CSV con timestamp

---

## 💻 Requisitos del Sistema

### Software Base

| Componente | Versión Mínima | Recomendado |
|------------|----------------|-------------|
| **Python** | 3.8 | 3.10+ |
| **R** | 4.0.0 | 4.3+ |
| **RStudio** | Cualquiera | 2023.06+ |
| **RAM** | 4 GB | 8 GB+ |
| **Espacio en Disco** | 2 GB | 5 GB+ |

### Sistema Operativo

- ✅ Windows 10/11

---

## 🚀 Instalación

### 1️⃣ Clonar el Repositorio

```bash
git clone https://github.com/[USUARIO]/Dashboard_Monitoreo_Camaras_Trampa_Red_OTUS_Colombia.git
cd Dashboard_Monitoreo_Camaras_Trampa_Red_OTUS_Colombia
```

### 2️⃣ Configurar Entorno Python

**Opción A: Usando venv (recomendado)**

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno (Windows)
venv\Scripts\activate

# Activar entorno (macOS/Linux)
source venv/bin/activate

# Instalar dependencias
pip install -r 3_processing_pipeline/requirements.txt
```

**Opción B: Usando conda**

```bash
conda create -n otus python=3.10
conda activate otus
pip install -r 3_processing_pipeline/requirements.txt
```

**Dependencias Python:**
```
numpy
pandas
pyarrow
pillow
geopandas
shapely
```

### 3️⃣ Configurar Entorno R

**Instalar librerías requeridas:**

```r
# Ejecutar en consola R o RStudio
install.packages(c(
  # Framework Shiny
  "shiny", "shinydashboard", "dashboardthemes", "shinyjs", "shinymanager",
  
  # Visualización
  "plotly", "leaflet", "sf", "DT",
  
  # Multimedia
  "slickR", "magick", "cowplot",
  
  # Procesamiento de datos
  "dplyr", "tidyr", "arrow"
))
```

**Nota crítica sobre DT:**  
Si el paquete `DT` no se instala correctamente, consultar `0_Documentation/INSTALL.md` para solución de problemas.

### 4️⃣ Verificar Instalación

**Python:**
```bash
python --version
pip list | grep -E "pandas|pyarrow|geopandas"
```

**R:**
```r
# En consola R
R.version.string
packageVersion("shiny")
packageVersion("DT")
```

---

## ⚡ Uso Rápido

### Procesamiento de Datos (Pipeline Python)

```bash
# 1. Colocar archivos CSV de Wildlife Insights en 1_Data_RAW_WI/
#    Archivos requeridos:
#      - projects.csv
#      - deployments.csv
#      - cameras.csv
#      - images_*.csv (uno o múltiples archivos)

# 2. Activar entorno virtual
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# 3. Ejecutar pipeline
cd 3_processing_pipeline
python process_RAW_data_WI.py

# 4. Verificar archivos Parquet generados
ls ../4_Dashboard/dashboard_input_data/*.parquet
```

**Salida esperada:**
```
✓ observations.parquet   (~500 KB - 5 MB según volumen de datos)
✓ deployments.parquet    (~50 KB - 200 KB)
✓ projects.parquet       (~10 KB - 50 KB)
```

### Visualización en Dashboard (R Shiny)

**Opción 1: Desde RStudio (recomendado)**

1. Abrir `4_Dashboard/Dashboard_Vista_Corporaciones.R` o `4_Dashboard/Dashboard_Vista_Proyectos.R`
2. Hacer clic en **"Run App"** (esquina superior derecha)
3. Seleccionar **"Run in Window"** para mejor experiencia

**Opción 2: Desde consola R**

```r
# Dashboard por Corporaciones
setwd("4_Dashboard")
shiny::runApp("Dashboard_Vista_Corporaciones.R")

# Dashboard por Proyectos
shiny::runApp("Dashboard_Vista_Proyectos.R")
```

**Opción 3: Desde terminal**

```bash
cd 4_Dashboard
Rscript -e "shiny::runApp('Dashboard_Vista_Corporaciones.R')"
```

---

## 📁 Estructura del Proyecto

```
Dashboard_Monitoreo_Camaras_Trampa_Red_OTUS_Colombia/
│
├── 0_Documentation/                    # 📚 Documentación técnica
│   ├── README.md                       # Este archivo
│   ├── INSTALL.md                      # Guía de instalación detallada
│   ├── ARCHITECTURE.md                 # Arquitectura del sistema
│   ├── PIPELINE.md                     # Documentación del pipeline Python
│   ├── Dashboard_Vista_Corporaciones.md   # Docs del dashboard por CARs
│   ├── Dashboard_Vista_Proyectos.md       # Docs del dashboard por proyectos
│   ├── DOC_functions_data.md           # Funciones de análisis R
│   └── DOC_style_css.md                # Estilos CSS del dashboard
│
├── 1_Data_RAW_WI/                      # 📥 Datos crudos de Wildlife Insights
│   ├── projects.csv                    # Catálogo de proyectos
│   ├── deployments.csv                 # Despliegues de cámaras
│   ├── cameras.csv                     # Metadata de cámaras
│   ├── sequences.csv                   # Secuencias de imágenes
│   └── images_*.csv                    # Imágenes por proyecto (múltiples archivos)
│
├── 2_Data_Shapefiles_CARs/             # 🗺️ Shapefiles de jurisdicciones
│   ├── CAR_MPIO.shp                    # Polígonos de CARs
│   ├── CAR_MPIO.shx
│   ├── CAR_MPIO.dbf
│   └── CAR_MPIO.prj
│
├── 3_processing_pipeline/              # 🔧 Pipeline ETL en Python
│   ├── process_RAW_data_WI.py          # Script principal de procesamiento
│   ├── requirements.txt                # Dependencias Python
│   └── src/                            # Módulos del pipeline
│       ├── __init__.py
│       ├── utils.py                    # Funciones de carga y filtrado
│       ├── transformations.py          # Transformaciones de datos
│       ├── generate_parquets.py        # Generación de archivos Parquet
│       └── validation.py               # Validación de calidad
│
├── 4_Dashboard/                        # 📊 Dashboards R Shiny
│   ├── Dashboard_Vista_Corporaciones.R # Dashboard por CARs (principal)
│   ├── Dashboard_Vista_Proyectos.R     # Dashboard por proyectos
│   ├── functions_data.R                # Funciones de análisis y visualización
│   │
│   ├── dashboard_input_data/           # 💾 Datos procesados (Parquet)
│   │   ├── observations.parquet        # Observaciones de fauna
│   │   ├── deployments.parquet         # Metadata de despliegues
│   │   └── projects.parquet            # Catálogo de proyectos
│   │
│   └── www/                            # 🎨 Recursos web
│       ├── css/
│       │   └── style.css               # Estilos personalizados
│       ├── images/
│       │   ├── favorites/              # Galería de imágenes destacadas
│       │   │   ├── General/            # Imágenes consolidadas
│       │   │   ├── [NOMBRE_CAR]/       # Imágenes por corporación
│       │   │   └── ...
│       │   └── Logos/
│       │       └── Logos_instituciones.png
│       └── fonts/
│
└── .gitignore                          # Archivos excluidos de Git
```

---

## 🔄 Flujo de Trabajo

```
┌─────────────────────────────────────────────────────────────────────┐
│                     WILDLIFE INSIGHTS                                │
│  (Plataforma global de gestión de datos de cámaras trampa)          │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
                    📥 Descarga de archivos CSV
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│                  1_Data_RAW_WI/ (Datos crudos)                       │
│  • projects.csv                                                      │
│  • deployments.csv                                                   │
│  • cameras.csv                                                       │
│  • images_*.csv (múltiples archivos por proyecto)                   │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│         🔧 PIPELINE ETL (3_processing_pipeline/)                     │
│                                                                      │
│  1. Carga de datos crudos (concatenación de images_*.csv)          │
│  2. Validación y filtrado (subproject_name, registros CV)          │
│  3. Enriquecimiento (taxonomía, metadata administrativa)           │
│  4. Análisis geográfico (asignación de CARs por coordenadas)       │
│  5. Generación de Parquet (observations, deployments, projects)    │
│  6. Validación de calidad (reportes de estadísticas)               │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────────┐
│       💾 DATOS PROCESADOS (4_Dashboard/dashboard_input_data/)       │
│  • observations.parquet  (20 columnas, datos granulares)           │
│  • deployments.parquet   (15 columnas, metadata de despliegues)    │
│  • projects.parquet      (10 columnas, catálogo de proyectos)      │
└─────────────────────────────────────────────────────────────────────┘
                                ↓
                    ┌───────────┴───────────┐
                    ↓                       ↓
┌────────────────────────────┐  ┌──────────────────────────────┐
│  📊 DASHBOARD CORPORACIONES │  │  📊 DASHBOARD PROYECTOS       │
│  (Vista consolidada CARs)   │  │  (Vista individual proyectos)│
│                             │  │                               │
│  • Filtro por corporación   │  │  • Filtro por proyecto       │
│  • Filtro por evento        │  │  • Filtro por evento         │
│  • Polígonos jurisdicciones │  │  • Análisis detallado        │
│  • Análisis consolidados    │  │  • Exportación de reportes   │
└────────────────────────────┘  └──────────────────────────────┘
                    ↓                       ↓
┌─────────────────────────────────────────────────────────────────────┐
│                   📤 EXPORTACIONES                                   │
│  • Tablas CSV (ranking de especies con timestamp)                  │
│  • Imágenes PNG (captura completa del dashboard)                   │
│  • Reportes de calidad (validación de pipeline Python)             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Dashboards Disponibles

### 1. Dashboard por Corporaciones (`Dashboard_Vista_Corporaciones.R`)

**Propósito:** Análisis consolidado por Corporaciones Autónomas Regionales (CARs)

**Características:**
- 🏛️ **Filtro primario por corporación** (AMVA, CAM, CARDIQUE, CORPOCALDAS, etc.)
- 📅 **Filtro secundario por evento de muestreo** (formato YYYY_N: 2024_2, 2025_1)
- 🗺️ **Visualización de polígonos jurisdiccionales** en mapa interactivo
- 📊 **Tabla de indicadores por período** con fila consolidada
- 📈 **Análisis multi-evento** para comparación temporal

**Uso típico:**
- Reportes administrativos para CARs
- Análisis de tendencias temporales por jurisdicción
- Comparación de esfuerzo de muestreo entre eventos

**Ejecutar:**
```r
shiny::runApp("4_Dashboard/Dashboard_Vista_Corporaciones.R")
```

### 2. Dashboard por Proyectos (`Dashboard_Vista_Proyectos.R`)

**Propósito:** Análisis detallado de proyectos individuales

**Características:**
- 📋 **Filtro por proyecto específico** (según project_id)
- 🔍 **Análisis granular** de sitios de muestreo
- 📊 **Métricas operacionales** por deployment
- 🎯 **Enfoque en protocolos de campo** individuales

**Uso típico:**
- Análisis de campo por investigadores
- Validación de calidad de datos por proyecto
- Generación de reportes técnicos específicos

**Ejecutar:**
```r
shiny::runApp("4_Dashboard/Dashboard_Vista_Proyectos.R")
```

### Comparación de Dashboards

| Característica | Vista Corporaciones | Vista Proyectos |
|----------------|---------------------|-----------------|
| **Nivel de agregación** | CAR → Evento | Proyecto → Evento |
| **Polígonos en mapa** | ✅ Jurisdicción CAR | ❌ No aplica |
| **Tabla consolidada** | ✅ Por períodos | ⚠️ Limitada |
| **Uso principal** | Administrativo | Técnico/Investigación |
| **Exportación PNG** | ✅ Dashboard completo | ✅ Dashboard completo |
| **Exportación CSV** | ✅ Ranking de especies | ✅ Ranking de especies |

---

## 📚 Documentación

### Documentación Técnica Completa

| Documento | Descripción | Ubicación |
|-----------|-------------|-----------|
| **INSTALL.md** | Guía detallada de instalación y configuración de entorno | `0_Documentation/` |
| **ARCHITECTURE.md** | Arquitectura del sistema, diagramas de flujo, decisiones de diseño | `0_Documentation/` |
| **PIPELINE.md** | Documentación técnica del pipeline Python (módulos, funciones, validación) | `0_Documentation/` |
| **Dashboard_Vista_Corporaciones.md** | Funcionalidad, uso y código del dashboard por CARs | `0_Documentation/` |
| **Dashboard_Vista_Proyectos.md** | Funcionalidad, uso y código del dashboard por proyectos | `0_Documentation/` |
| **DOC_functions_data.md** | Documentación de funciones de análisis R (occupancy, activity, Hill numbers) | `0_Documentation/` |
| **DOC_style_css.md** | Guía de estilos CSS, paleta de colores, componentes visuales | `0_Documentation/` |

### Recursos Externos

- **Wildlife Insights:** https://www.wildlifeinsights.org/
- **Camtrap DP Standard:** https://camtrap-dp.tdwg.org/
- **R Shiny Documentation:** https://shiny.rstudio.com/
- **Apache Arrow (Parquet):** https://arrow.apache.org/docs/python/parquet.html
- **Leaflet for R:** https://rstudio.github.io/leaflet/

---

## 🏗️ Arquitectura Técnica

### Tecnologías Utilizadas

#### Backend (Python)

- **pandas** 🐼 - Manipulación y transformación de datos
- **pyarrow** 🏹 - Lectura/escritura de archivos Parquet
- **geopandas** 🗺️ - Análisis geoespacial (asignación de CARs)
- **shapely** 📐 - Operaciones geométricas (point-in-polygon)
- **numpy** 🔢 - Cálculos numéricos eficientes
- **pillow** 🖼️ - Procesamiento de imágenes (futuro)

#### Frontend (R Shiny)

- **shiny** ⚡ - Framework web reactivo
- **shinydashboard** 📊 - Componentes de dashboard
- **plotly** 📈 - Gráficos interactivos
- **leaflet** 🗺️ - Mapas interactivos
- **DT** 📋 - Tablas interactivas (DataTables)
- **sf** 🌍 - Datos espaciales (shapefiles)
- **slickR** 🎠 - Carrusel de imágenes
- **html2canvas** 📸 - Captura de pantalla (JavaScript)

#### Formato de Datos

- **Apache Parquet** 📦
  - Compresión columnar eficiente (Snappy)
  - Lectura 10-100x más rápida que CSV
  - Preservación de tipos de datos
  - Tamaño ~70% menor que CSV equivalente

### Arquitectura Modular del Pipeline

```
3_processing_pipeline/
├── process_RAW_data_WI.py          # Orquestador principal
└── src/
    ├── utils.py                    # Carga, filtrado, limpieza
    ├── transformations.py          # Enriquecimiento de datos
    ├── generate_parquets.py        # Generación de archivos Parquet
    └── validation.py               # Validación de calidad
```

**Principios de diseño:**
- ✅ **Separación de responsabilidades** (cada módulo tiene una función clara)
- ✅ **Reutilización de código** (funciones genéricas en utils)
- ✅ **Validación exhaustiva** (checks en cada etapa del pipeline)
- ✅ **Trazabilidad** (logs detallados de cada operación)

### Arquitectura Reactiva de Dashboards

```
UI (selectores) → observeEvent → reactiveValues → reactive() → renderOutput()
                      ↓
                Validación de filtros
                      ↓
                Aplicación de filtros
                      ↓
              Cálculo de estadísticas
                      ↓
              Renderizado de visualizaciones
```

**Ventajas:**
- ⚡ **Actualizaciones automáticas** cuando cambian los filtros
- 🎯 **Cálculos eficientes** (solo se recalcula lo necesario)
- 🔒 **Estado consistente** (reactiveValues sincronizados)
- 🖱️ **Experiencia fluida** para el usuario

---

## 🤝 Contribuir

### Reportar Problemas

Si encuentras un bug o tienes una sugerencia:

1. Revisa los [Issues existentes](https://github.com/[USUARIO]/Dashboard_Monitoreo_Camaras_Trampa_Red_OTUS_Colombia/issues)
2. Si no existe, crea un nuevo Issue con:
   - **Descripción clara** del problema
   - **Pasos para reproducir**
   - **Comportamiento esperado vs. observado**
   - **Captura de pantalla** (si aplica)
   - **Versión de R/Python** y sistema operativo

### Proponer Mejoras

Para solicitar nuevas funcionalidades:

1. Abre un Issue con etiqueta `enhancement`
2. Describe el caso de uso y beneficio esperado
3. Proporciona ejemplos de cómo se usaría la funcionalidad

### Contribuir con Código

1. **Fork** el repositorio
2. Crea una **rama** para tu funcionalidad (`git checkout -b feature/nueva-funcionalidad`)
3. **Commit** tus cambios (`git commit -m 'Agregar nueva funcionalidad'`)
4. **Push** a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un **Pull Request** con descripción detallada

**Guías de estilo:**
- **Python:** Seguir PEP 8
- **R:** Seguir tidyverse style guide
- **Comentarios:** En español para consistencia del proyecto
- **Documentación:** Actualizar archivos .md correspondientes

---

## 📄 Licencia

Este proyecto está licenciado bajo **CC0 1.0 Universal (Public Domain Dedication)**.

Puedes copiar, modificar, distribuir y ejecutar el trabajo, incluso con fines comerciales, sin pedir permiso.

Ver detalles completos en: https://creativecommons.org/publicdomain/zero/1.0/

---

## 👥 Autoría

**Desarrollo principal:**  
Cristian C. Acevedo

**Coordinación científica:**  
Angélica Diaz-Pulido

**Institución:**  
Instituto de Investigación de Recursos Biológicos Alexander von Humboldt – Red OTUS

**Proyecto:**  
Contrato 25-064 
Desarrollo de Software CamTrapFlow (CTF) y Dashboards

**Año:** 2025

---

## 🏆 Créditos

### Desarrollo

- **Jorge Ahumada** - Conservation International (2020)
  - Concepto original y funciones de análisis
  - Algoritmos de diversidad y ocupación

- **Cristian C. Acevedo** - Instituto Humboldt (2025)
  - Adaptación a arquitectura Parquet
  - Desarrollo de dashboards por corporaciones
  - Pipeline modular Python
  - Documentación técnica

### Instituciones

- **Instituto de Investigación de Recursos Biológicos Alexander von Humboldt**
  - Coordinación técnica de la Red OTUS Colombia
  - Validación científica de indicadores

- **Red OTUS Colombia**
  - Provisión de datos de fototrampeo
  - Retroalimentación de usuarios finales

- **Corporaciones Autónomas Regionales (CARs)**
  - Trabajo de campo y recolección de datos
  - Validación de análisis territoriales

### Agradecimientos

- **Wildlife Insights** por la plataforma de gestión de datos
- Comunidad de **R Shiny** y **tidyverse**
- Desarrolladores de **Apache Arrow** y **Leaflet**

---

<div align="center">
  <em>Instituto de Investigación de Recursos Biológicos Alexander von Humboldt</em><br>
  <strong>Comprometidos con la conservación y el conocimiento de la biodiversidad colombiana</strong>
</div>