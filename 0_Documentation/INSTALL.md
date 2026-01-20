# Guía de Instalación y Configuración de Entorno

## 📋 Tabla de Contenidos

- [Requisitos Previos](#-requisitos-previos)
- [Instalación de Python](#-instalación-de-python)
- [Instalación de R y RStudio](#-instalación-de-r-y-rstudio)
- [Configuración del Proyecto](#-configuración-del-proyecto)
- [Instalación de Dependencias Python](#-instalación-de-dependencias-python)
- [Instalación de Paquetes R](#-instalación-de-paquetes-r)
- [Configuración de Datos](#-configuración-de-datos)
- [Verificación de Instalación](#-verificación-de-instalación)
- [Resolución de Problemas](#-resolución-de-problemas)

---

## 💻 Requisitos Previos

### Especificaciones Mínimas del Sistema

| Componente | Mínimo | Recomendado |
|------------|--------|-------------|
| **Procesador** | Dual-core 2.0 GHz | Quad-core 2.5 GHz+ |
| **RAM** | 4 GB | 8 GB+ |
| **Espacio en Disco** | 2 GB | 5 GB+ (datos + cache) |
| **Sistema Operativo** | Windows 10, macOS 10.15, Ubuntu 20.04 | Windows 11, macOS 13+, Ubuntu 22.04+ |

### Software Requerido

- [ ] **Python 3.8+** (recomendado: 3.10 o 3.11)
- [ ] **R 4.0+** (recomendado: 4.3+)
- [ ] **RStudio** (última versión estable)
- [ ] **Git** (opcional, para clonar repositorio)

---

## 🐍 Instalación de Python

### Windows

**Opción 1: Instalador oficial (recomendado)**

1. Descargar Python desde: https://www.python.org/downloads/
2. Ejecutar instalador `.exe`
3. ✅ **IMPORTANTE:** Marcar "Add Python to PATH"
4. Seleccionar "Install Now"
5. Verificar instalación:
   ```cmd
   python --version
   pip --version
   ```

**Opción 2: Microsoft Store**

```cmd
# Buscar "Python 3.11" en Microsoft Store
# Instalar directamente desde la tienda
```

### macOS

**Opción 1: Homebrew (recomendado)**

```bash
# Instalar Homebrew si no está instalado
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Instalar Python
brew install python@3.11

# Verificar instalación
python3 --version
pip3 --version
```

**Opción 2: Instalador oficial**

1. Descargar desde: https://www.python.org/downloads/mac-osx/
2. Ejecutar instalador `.pkg`
3. Seguir asistente de instalación

### Linux (Ubuntu/Debian)

```bash
# Actualizar repositorios
sudo apt update

# Instalar Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip

# Verificar instalación
python3 --version
pip3 --version
```

---

## 📊 Instalación de R y RStudio

### Paso 1: Instalar R

#### Windows

1. Descargar R desde: https://cran.r-project.org/bin/windows/base/
2. Ejecutar instalador `.exe`
3. Aceptar configuración por defecto
4. Verificar instalación:
   ```cmd
   R --version
   ```

#### macOS

```bash
# Con Homebrew
brew install r

# O descargar instalador desde:
# https://cran.r-project.org/bin/macosx/
```

#### Linux (Ubuntu/Debian)

```bash
# Agregar repositorio CRAN
sudo apt update
sudo apt install --no-install-recommends software-properties-common dirmngr
wget -qO- https://cloud.r-project.org/bin/linux/ubuntu/marutter_pubkey.asc | sudo tee -a /etc/apt/trusted.gpg.d/cran_ubuntu_key.asc

# Agregar repositorio CRAN
sudo add-apt-repository "deb https://cloud.r-project.org/bin/linux/ubuntu $(lsb_release -cs)-cran40/"

# Instalar R
sudo apt install r-base r-base-dev
```

### Paso 2: Instalar RStudio

1. Descargar RStudio Desktop desde: https://posit.co/download/rstudio-desktop/
2. Seleccionar versión según sistema operativo
3. Ejecutar instalador
4. Abrir RStudio y verificar que detecte R correctamente

**Verificación:**
```r
# En consola de RStudio
R.version.string
# Debe mostrar: "R version 4.x.x (YYYY-MM-DD)"
```

---

## 📦 Configuración del Proyecto

### Opción 1: Clonar desde Git (recomendado)

```bash
# Navegar a carpeta de proyectos
cd ~/Documents  # macOS/Linux
cd C:\Users\[TU_USUARIO]\Documents  # Windows

# Clonar repositorio
git clone https://github.com/[USUARIO]/Dashboard_Monitoreo_Camaras_Trampa_Red_OTUS_Colombia.git

# Entrar al directorio
cd Dashboard_Monitoreo_Camaras_Trampa_Red_OTUS_Colombia
```

### Opción 2: Descargar ZIP

1. Descargar archivo ZIP desde GitHub
2. Extraer en carpeta deseada
3. Abrir terminal/consola en la carpeta extraída

### Estructura Verificada

Después de clonar/extraer, verificar que existen estas carpetas:

```
Dashboard_Monitoreo_Camaras_Trampa_Red_OTUS_Colombia/
├── 0_Documentation/
├── 1_Data_RAW_WI/
├── 2_Data_Shapefiles_CARs/
├── 3_processing_pipeline/
└── 4_Dashboard/
```

---

## 🔧 Instalación de Dependencias Python

### Paso 1: Crear Entorno Virtual

**¿Por qué un entorno virtual?**
- ✅ Aísla dependencias del proyecto
- ✅ Evita conflictos con otros proyectos
- ✅ Permite diferentes versiones de librerías

#### Windows

```cmd
# Navegar a carpeta del proyecto
cd Dashboard_Monitoreo_Camaras_Trampa_Red_OTUS_Colombia

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
venv\Scripts\activate

# Verificar activación (debe aparecer "(venv)" en el prompt)
```

#### macOS/Linux

```bash
# Navegar a carpeta del proyecto
cd Dashboard_Monitoreo_Camaras_Trampa_Red_OTUS_Colombia

# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
source venv/bin/activate

# Verificar activación (debe aparecer "(venv)" en el prompt)
```

### Paso 2: Instalar Dependencias

```bash
# Asegurarse de que el entorno virtual esté activado
# Debe aparecer "(venv)" al inicio de la línea de comando

# Actualizar pip (recomendado)
pip install --upgrade pip

# Instalar dependencias desde requirements.txt
pip install -r 3_processing_pipeline/requirements.txt
```

**Dependencias instaladas:**
- `numpy` - Cálculos numéricos
- `pandas` - Manipulación de datos
- `pyarrow` - Lectura/escritura de Parquet
- `pillow` - Procesamiento de imágenes
- `geopandas` - Análisis geoespacial
- `shapely` - Operaciones geométricas

### Paso 3: Verificar Instalación Python

```python
# Ejecutar en terminal con entorno activado
python -c "import pandas; import pyarrow; import geopandas; print('✓ Todas las librerías instaladas correctamente')"
```

**Salida esperada:**
```
✓ Todas las librerías instaladas correctamente
```

---

## 📊 Instalación de Paquetes R

### Paso 1: Instalar Paquetes desde CRAN

**Abrir RStudio y ejecutar en la consola R:**

```r
# Lista completa de paquetes requeridos
paquetes_requeridos <- c(
  # Framework Shiny
  "shiny",
  "shinydashboard",
  "dashboardthemes",
  "shinyjs",
  "shinymanager",
  
  # Visualización
  "plotly",
  "leaflet",
  "sf",
  "DT",
  
  # Multimedia
  "slickR",
  "magick",
  "cowplot",
  
  # Procesamiento de datos
  "dplyr",
  "tidyr",
  "arrow"
)

# Instalar todos los paquetes
install.packages(paquetes_requeridos)
```

**Tiempo estimado:** 10-30 minutos (depende de conexión a internet)

### Paso 2: Instalación Individual (si hay errores)

Si la instalación masiva falla, instalar uno por uno:

```r
# Framework Shiny
install.packages("shiny")
install.packages("shinydashboard")
install.packages("dashboardthemes")
install.packages("shinyjs")

# Visualización (críticos)
install.packages("plotly")
install.packages("leaflet")
install.packages("sf")
install.packages("DT")  # CRÍTICO - ver sección de problemas si falla

# Multimedia
install.packages("slickR")
install.packages("magick")
install.packages("cowplot")

# Procesamiento
install.packages("dplyr")
install.packages("tidyr")
install.packages("arrow")
```

### Paso 3: Verificar Instalación R

```r
# Verificar que todos los paquetes se carguen correctamente
library(shiny)
library(shinydashboard)
library(plotly)
library(leaflet)
library(sf)
library(DT)
library(arrow)
library(dplyr)

# Si no hay errores, mostrar versiones
cat("✓ Shiny version:", as.character(packageVersion("shiny")), "\n")
cat("✓ DT version:", as.character(packageVersion("DT")), "\n")
cat("✓ Arrow version:", as.character(packageVersion("arrow")), "\n")
```

**Salida esperada:**
```
✓ Shiny version: 1.7.x
✓ DT version: 0.x
✓ Arrow version: 13.x
```

---

## 📥 Configuración de Datos

### Paso 1: Preparar Datos Crudos de Wildlife Insights

**Ubicación:** `1_Data_RAW_WI/`

**Archivos requeridos:**
```
1_Data_RAW_WI/
├── projects.csv          # Obligatorio
├── deployments.csv       # Obligatorio
├── cameras.csv           # Obligatorio
├── sequences.csv         # Opcional
└── images_*.csv          # Al menos 1 archivo obligatorio
```

**Fuente de datos:**
1. Acceder a Wildlife Insights: https://www.wildlifeinsights.org/
2. Seleccionar proyecto(s) de la Red OTUS
3. Exportar datos en formato CSV
4. Descargar archivos y colocar en `1_Data_RAW_WI/`

### Paso 2: Verificar Shapefile de CARs

**Ubicación:** `2_Data_Shapefiles_CARs/`

**Archivos requeridos:**
```
2_Data_Shapefiles_CARs/
├── CAR_MPIO.shp    # Geometrías (obligatorio)
├── CAR_MPIO.shx    # Índice espacial (obligatorio)
├── CAR_MPIO.dbf    # Atributos (obligatorio)
└── CAR_MPIO.prj    # Proyección (obligatorio)
```

**Columna crítica en .dbf:**
- `NOMBRE_CAR`: Debe contener siglas de CARs (ejemplo: CORPOCALDAS, CAM, AMVA)

### Paso 3: Ejecutar Pipeline de Procesamiento

```bash
# Activar entorno virtual Python
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# Navegar a carpeta del pipeline
cd 3_processing_pipeline

# Ejecutar procesamiento
python process_RAW_data_WI.py
```

**Salida esperada:**
```
================================================================================
PIPELINE DE PROCESAMIENTO DE DATOS - WILDLIFE INSIGHTS
Arquitectura Modular - Generación de 3 tablas Parquet
================================================================================

FASE 0: PREPARACIÓN DEL ENTORNO
  ✓ Carpeta de salida vacía

FASE 1: CARGA DE DATOS CRUDOS
  ✓ projects.csv cargado: 50 proyectos
  ✓ deployments.csv cargado: 1200 despliegues
  ✓ Concatenando images_*.csv...
  ✓ 45 archivos concatenados: 250000 registros

FASE 2: VALIDACIÓN Y FILTRADO
  ✓ Filtrado por subproject_name válido: 180000 registros
  ✓ Limpieza de registros CV: 175000 registros

FASE 3: ENRIQUECIMIENTO DE DATOS
  ✓ Nombres científicos creados
  ✓ Metadata administrativa agregada

FASE 4: ANÁLISIS GEOGRÁFICO
  ✓ Shapefile de CARs cargado
  ✓ Corporaciones asignadas por coordenadas

FASE 5: GENERACIÓN DE PARQUET
  ✓ observations.parquet generado (3.2 MB)
  ✓ deployments.parquet generado (185 KB)
  ✓ projects.parquet generado (12 KB)

FASE 6: VALIDACIÓN DE CALIDAD
  ✓ Todas las validaciones pasadas

================================================================================
PROCESAMIENTO COMPLETADO EXITOSAMENTE
================================================================================
```

### Paso 4: Verificar Archivos Generados

```bash
# Listar archivos Parquet generados
ls -lh ../4_Dashboard/dashboard_input_data/*.parquet  # macOS/Linux
dir ..\4_Dashboard\dashboard_input_data\*.parquet  # Windows
```

**Archivos esperados:**
```
observations.parquet   (500 KB - 5 MB)
deployments.parquet    (50 KB - 200 KB)
projects.parquet       (10 KB - 50 KB)
```

---

## ✅ Verificación de Instalación

### Checklist Completo

#### Python

- [ ] Python 3.8+ instalado (`python --version`)
- [ ] Entorno virtual creado (`venv/` existe)
- [ ] Dependencias instaladas (`pip list | grep pandas`)
- [ ] Archivos Parquet generados en `4_Dashboard/dashboard_input_data/`

#### R

- [ ] R 4.0+ instalado (`R.version.string`)
- [ ] RStudio instalado y funcional
- [ ] Paquetes Shiny instalados (`library(shiny)` sin errores)
- [ ] Paquete DT instalado (`library(DT)` sin errores)
- [ ] Paquete arrow instalado (`library(arrow)` sin errores)

#### Datos

- [ ] Archivos CSV en `1_Data_RAW_WI/`
- [ ] Shapefile completo en `2_Data_Shapefiles_CARs/`
- [ ] Pipeline ejecutado sin errores
- [ ] Archivos Parquet generados correctamente

### Prueba de Dashboard

**Ejecutar en RStudio:**

```r
# Establecer directorio de trabajo
setwd("4_Dashboard")

# Intentar cargar datos Parquet
library(arrow)
obs <- read_parquet("dashboard_input_data/observations.parquet")
print(paste("✓ Observaciones cargadas:", nrow(obs), "registros"))

# Ejecutar dashboard
shiny::runApp("Dashboard_Vista_Corporaciones.R")
```

**Si el dashboard abre correctamente:**
✅ **¡Instalación exitosa!**

---

## 🔧 Resolución de Problemas

### Problemas Comunes en Python

#### Error: "pip no reconocido como comando"

**Windows:**
```cmd
# Reinstalar Python marcando "Add to PATH"
# O agregar manualmente:
set PATH=%PATH%;C:\Python311\Scripts
```

**macOS/Linux:**
```bash
# Usar pip3 en lugar de pip
pip3 --version
```

#### Error: "ModuleNotFoundError: No module named 'geopandas'"

**Causa:** GeoPandas requiere dependencias del sistema

**Solución Windows:**
```cmd
# Opción 1: Usar conda (más fácil)
conda install geopandas

# Opción 2: Instalar desde wheel precompilado
pip install geopandas
```

**Solución macOS:**
```bash
# Instalar dependencias con Homebrew
brew install gdal
pip install geopandas
```

**Solución Linux:**
```bash
# Instalar dependencias del sistema
sudo apt install gdal-bin libgdal-dev
pip install geopandas
```

#### Error: "FileNotFoundError: CAR_MPIO.shp not found"

**Causa:** Shapefile no está en la ubicación esperada

**Solución:**
1. Verificar que todos los archivos .shp, .shx, .dbf, .prj existen
2. Confirmar ruta en `process_RAW_data_WI.py`:
   ```python
   SHAPEFILE_PATH = os.path.join(PROJECT_ROOT, '2_Data_Shapefiles_CARs', 'CAR_MPIO.shp')
   ```

### Problemas Comunes en R

#### Error: "package 'DT' is not available"

**Causa:** Problema de instalación de DT

**Solución:**
```r
# Opción 1: Instalar desde CRAN con dependencias
install.packages("DT", dependencies = TRUE)

# Opción 2: Instalar versión de desarrollo
install.packages("remotes")
remotes::install_github("rstudio/DT")

# Opción 3: Especificar repositorio CRAN
install.packages("DT", repos = "https://cloud.r-project.org/")
```

#### Error: "unable to load shared object sf.so"

**Causa:** Falta librería del sistema para sf

**Windows:**
- Reinstalar Rtools: https://cran.r-project.org/bin/windows/Rtools/

**macOS:**
```bash
brew install gdal proj geos
```

**Linux:**
```bash
sudo apt install libudunits2-dev libgdal-dev libgeos-dev libproj-dev
```

Luego reinstalar en R:
```r
install.packages("sf", configure.args = "--with-proj-lib=/usr/local/lib/")
```

#### Error: "Error in library(arrow): there is no package called 'arrow'"

**Solución:**
```r
# Arrow puede requerir instalación especial
install.packages("arrow", repos = c(arrow = "https://apache.r-universe.dev", getOption("repos")))
```

#### Error: "Dashboard no muestra datos después de aplicar filtros"

**Diagnóstico:**
```r
# Verificar que archivos Parquet existen
list.files("dashboard_input_data", pattern = "*.parquet")

# Intentar cargar manualmente
library(arrow)
obs <- read_parquet("dashboard_input_data/observations.parquet")
print(nrow(obs))  # Debe ser > 0

# Verificar columnas críticas
print(names(obs))  # Debe incluir: Corporacion, subproject_name, common_name, etc.
```

**Solución:**
- Si `obs` está vacío → Re-ejecutar pipeline Python
- Si faltan columnas → Verificar versión de `process_RAW_data_WI.py`

### Problemas de Rendimiento

#### Dashboard carga lento (> 30 segundos)

**Causas comunes:**
1. Archivos Parquet muy grandes (> 50 MB)
2. RAM insuficiente (< 4 GB)
3. Muchos eventos en selector (> 20)

**Soluciones:**
```r
# 1. Filtrar datos antes de cargar
library(arrow)
obs <- read_parquet(
  "dashboard_input_data/observations.parquet",
  col_select = c("Corporacion", "subproject_name", "common_name", "timestamp")
)

# 2. Reducir tamaño de galería de imágenes
# En Dashboard_Vista_Corporaciones.R, línea ~1200:
MAX_FAVORITES <- 20  # Reducir de 40 a 20

# 3. Deshabilitar autoplay del carrusel
# En slickR settings, línea ~1220:
autoplay = FALSE
```

#### Pipeline Python consume mucha memoria

**Solución:** Procesar datos en chunks

```python
# En process_RAW_data_WI.py, modificar concatenación:
images = pd.concat(
    [pd.read_csv(f, low_memory=False) for f in image_files],
    ignore_index=True
)

# Cambiar a:
chunks = []
for f in image_files:
    chunk = pd.read_csv(f, low_memory=False)
    chunks.append(chunk[chunk['subproject_name'].notna()])  # Filtrar antes
images = pd.concat(chunks, ignore_index=True)
```

---

## 📞 Obtener Ayuda

Si los problemas persisten:

1. **Revisar Issues:** https://github.com/[USUARIO]/Dashboard_Monitoreo_Camaras_Trampa_Red_OTUS_Colombia/issues
2. **Crear nuevo Issue** con:
   - Sistema operativo y versión
   - Versión de Python/R
   - Mensaje de error completo
   - Pasos para reproducir

3. **Consultar documentación adicional:**
   - `0_Documentation/ARCHITECTURE.md` - Arquitectura del sistema
   - `0_Documentation/PIPELINE.md` - Pipeline Python detallado
   - `0_Documentation/Dashboard_Vista_Corporaciones.md` - Dashboard por CARs

---

<div align="center">

**¿Instalación exitosa?** 🎉  
Continúa con la [Guía de Uso Rápido](../README.md#-uso-rápido)

</div>
