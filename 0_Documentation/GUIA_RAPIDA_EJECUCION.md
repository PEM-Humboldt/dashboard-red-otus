# Guía Rápida de Ejecución - Dashboard Red OTUS Colombia

## 📋 Descripción General

Este documento describe el flujo completo de operación del Dashboard de Monitoreo de Cámaras Trampa, desde la carga de datos crudos de Wildlife Insights hasta la visualización interactiva en R Shiny.

**Tiempo estimado total:** 30-45 minutos (primera ejecución)

---

## 🎯 Flujo de Operación

```
┌─────────────────────────────────────────────────────────────────────┐
│ FASE 1: CARGA DE DATOS CRUDOS (Manual - 5 min)                     │
│   └─ Descargar CSVs desde Wildlife Insights                        │
│   └─ Copiar archivos a carpeta 1_Data_RAW_WI/                      │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ FASE 2: CONFIGURACIÓN PYTHON (Primera vez - 10 min)                │
│   └─ Crear/activar entorno virtual                                 │
│   └─ Instalar dependencias (requirements.txt)                      │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ FASE 3: PROCESAMIENTO ETL (Automático - 5-10 min)                  │
│   └─ Ejecutar process_RAW_data_WI.py                               │
│   └─ Generar archivos Parquet (observations, deployments, projects)│
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ FASE 4: VALIDACIÓN (Opcional - 2 min)                              │
│   └─ Ejecutar analyze_parquet_files.py                             │
│   └─ Revisar estadísticas y calidad de datos                       │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ FASE 5: CONFIGURACIÓN R (Primera vez - 10-15 min)                  │
│   └─ Instalar RStudio                                              │
│   └─ Instalar paquetes R (shiny, dplyr, plotly, leaflet, etc.)     │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ FASE 6: VISUALIZACIÓN (Interactivo - ∞)                            │
│   └─ Abrir Dashboard_Vista_Proyectos.R o Dashboard_Vista_Corporaciones.R│
│   └─ Click en "Run App" → Dashboard interactivo en navegador       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📁 FASE 1: Carga de Datos Crudos (Manual)

### Paso 1.1: Descargar datos desde Wildlife Insights

1. Ingresar a [Wildlife Insights](https://www.wildlifeinsights.org/)
2. Navegar a tu proyecto → "Download Data"
3. Seleccionar formato **CSV** para las siguientes tablas:
   - `projects.csv`
   - `cameras.csv`
   - `deployments.csv`
   - `images_XXXXXXX.csv` (uno por proyecto/deployment)
   - `sequences.csv`

### Paso 1.2: Organizar archivos en el proyecto

```
Dashboard_Monitoreo_Camaras_Trampa_Red_OTUS_Colombia/
└── 1_Data_RAW_WI/
    ├── projects.csv
    ├── cameras.csv
    ├── deployments.csv
    ├── sequences.csv
    ├── images_2002517.csv    ← Ejemplo: ID de proyecto
    ├── images_2008342.csv
    └── images_XXXXXXX.csv    ← Tantos como proyectos tengas
```

**💡 IMPORTANTE:**
- Los archivos `images_*.csv` **deben** seguir el formato `images_PROJECTID.csv`
- NO renombrar los archivos descargados de Wildlife Insights
- Asegurarse de que todos los CSVs estén en codificación UTF-8

---

## 🐍 FASE 2: Configuración de Entorno Python

### Opción A: Usar entorno virtual incluido (Recomendado)

Si el proyecto incluye la carpeta `3_processing_pipeline/venv_otus_pipeline/`:

**Windows (CMD):**
```cmd
cd 3_processing_pipeline
venv_otus_pipeline\Scripts\activate
```

**Windows (PowerShell):**
```powershell
cd 3_processing_pipeline
.\venv_otus_pipeline\Scripts\Activate.ps1
```

**macOS/Linux:**
```bash
cd 3_processing_pipeline
source venv_otus_pipeline/bin/activate
```

✅ **Verificar que el entorno está activo:**
- Deberías ver `(venv_otus_pipeline)` al inicio de la línea de comandos

### Opción B: Crear nuevo entorno virtual

Si NO existe `venv_otus_pipeline/` o prefieres crear uno nuevo:

**Paso 2.1: Crear entorno virtual**

```bash
cd 3_processing_pipeline
python -m venv venv_otus_pipeline
```

**Paso 2.2: Activar entorno (ver comandos en Opción A)**

**Paso 2.3: Instalar dependencias**

```bash
pip install -r requirements.txt
```

**📦 Librerías instaladas:**
- `numpy` - Cálculos numéricos
- `pandas` - Manipulación de datos
- `pyarrow` - Lectura/escritura de archivos Parquet
- `pillow` - Procesamiento de imágenes
- `geopandas` - Análisis geoespacial
- `shapely` - Geometrías espaciales

**Tiempo de instalación:** 3-5 minutos (depende de la conexión a internet)

---

## ⚙️ FASE 3: Procesamiento ETL (Pipeline Python)

### Paso 3.1: Ejecutar pipeline principal

**Asegúrate de que:**
1. El entorno virtual está activado (`(venv_otus_pipeline)` visible)
2. Estás en la carpeta `3_processing_pipeline/`
3. Los archivos CSV están en `../1_Data_RAW_WI/`

**Ejecutar:**

```bash
python process_RAW_data_WI.py
```

### Paso 3.2: Monitorear progreso

El script mostrará mensajes de progreso en cada fase:

```
📊 PIPELINE DE PROCESAMIENTO DE DATOS WILDLIFE INSIGHTS
========================================================

🔍 1. CARGA DE ARCHIVOS CRUDOS
  ✓ Cargando projects.csv...
  ✓ Cargando cameras.csv...
  ✓ Cargando deployments.csv...
  ✓ Cargando images_*.csv (58 archivos)...
  ✓ Total registros: 157,569

🧹 2. FILTRADO Y VALIDACIÓN
  ✓ Filtrados 3,661 registros con fechas inconsistentes (2.3%)
  ✓ Registros válidos: 153,908

🌍 3. ENRIQUECIMIENTO GEOGRÁFICO
  ✓ Asignadas corporaciones por ubicación (CAR)
  ✓ Agregados departamentos

💾 4. GENERACIÓN DE ARCHIVOS PARQUET
  ✓ observations.parquet: 21.02 MB (153,908 registros)
  ✓ deployments.parquet: 0.08 MB (1,021 registros)
  ✓ projects.parquet: 0.04 MB (58 proyectos)

✅ PROCESAMIENTO COMPLETADO EXITOSAMENTE
```

**⏱️ Tiempo estimado:**
- Proyectos pequeños (< 50k registros): 2-3 minutos
- Proyectos medianos (50k-200k): 5-8 minutos
- Proyectos grandes (> 200k): 10-15 minutos

### Paso 3.3: Verificar archivos generados

```
4_Dashboard/dashboard_input_data/
├── observations.parquet    ← Detecciones de especies
├── deployments.parquet     ← Configuración de cámaras
└── projects.parquet        ← Catálogo de proyectos
```

**💡 IMPORTANTE:**
- Estos archivos Parquet **reemplazan** los datos anteriores
- Si el pipeline falla, los archivos antiguos permanecen intactos
- **NO** editar manualmente los archivos Parquet

---

## ✅ FASE 4: Validación de Datos (Opcional)

### Paso 4.1: Ejecutar script de análisis

```bash
python analyze_parquet_files.py
```

### Paso 4.2: Revisar reporte generado

El script mostrará:

```
📊 ANÁLISIS DE ARCHIVOS PARQUET
================================

📁 observations.parquet (21.02 MB)
  • Registros: 153,908
  • Columnas: 71
  • Especies únicas: 310
  • Proyectos: 58
  • Eventos (subproject_name): 5
  • Rango de fechas: 2020-01-15 - 2025-05-27

📁 deployments.parquet (0.08 MB)
  • Registros: 1,021
  • Cámaras únicas: 804
  • Proyectos: 58

📁 projects.parquet (0.04 MB)
  • Proyectos: 58
  • Corporaciones (CARs): 12
  • Departamentos: 18

✅ Validación completada. Archivos listos para dashboard.
```

**🔍 Verificaciones automáticas:**
- ✅ Archivos existen y son legibles
- ✅ Columnas requeridas presentes
- ✅ Tipos de datos correctos
- ✅ Rangos de fechas coherentes
- ✅ IDs de proyectos consistentes

---

## 📊 FASE 5: Configuración de RStudio

### Paso 5.1: Instalar R y RStudio (si no están instalados)

**Descargar R:**
- Windows/macOS: https://cran.r-project.org/
- Linux: `sudo apt install r-base` (Ubuntu/Debian)

**Descargar RStudio:**
- https://posit.co/download/rstudio-desktop/
- Seleccionar versión para tu sistema operativo

### Paso 5.2: Instalar paquetes R requeridos

**Abrir RStudio** y ejecutar en la consola:

```r
# Framework Shiny
install.packages(c("shiny", "shinydashboard", "dashboardthemes", "shinyjs", "shinymanager"))

# Manipulación de datos
install.packages(c("dplyr", "tidyr", "lubridate", "arrow"))

# Visualización
install.packages(c("plotly", "leaflet", "ggplot2", "cowplot"))

# Tablas interactivas
install.packages("DT")

# Multimedia
install.packages(c("slickR", "magick"))

# Geoespacial
install.packages(c("sf", "sp"))
```

**⏱️ Tiempo estimado:** 10-15 minutos (primera instalación)

**💡 IMPORTANTE:**
- Si aparecen errores de compilación en Windows, instalar **Rtools**: https://cran.r-project.org/bin/windows/Rtools/
- En macOS, puede requerir **Xcode Command Line Tools**: `xcode-select --install`
- En Linux, instalar dependencias del sistema: `sudo apt install libgdal-dev libgeos-dev libproj-dev`

### Paso 5.3: Verificar instalación de paquetes

```r
# Ejecutar en consola de RStudio
library(shiny)
library(dplyr)
library(plotly)
library(leaflet)
library(DT)
library(arrow)

# Si no hay errores, ¡estás listo!
```

---

## 🚀 FASE 6: Ejecución de Dashboards

### Opción 1: Vista por Proyectos

**Paso 6.1:** Navegar en RStudio:
```
File → Open File → 4_Dashboard/Dashboard_Vista_Proyectos.R
```

**Paso 6.2:** Click en **"Run App"** (botón verde superior derecho)

**Paso 6.3:** El dashboard se abrirá automáticamente en el navegador

**🎯 Funcionalidades:**
- Filtrar por **Proyecto** (ID + Nombre)
- Filtrar por **Evento** (período de muestreo: 2020_2, 2021_2, 2025_1)
- Ajustar **intervalo de independencia** (30 min sugerido)
- Visualizar:
  - Indicadores consolidados (imágenes, cámaras, especies)
  - Ranking de especies
  - Ocupación naive de especies
  - Curva de acumulación
  - Patrón de actividad circadiano
  - Mapa de ubicación de cámaras
  - Galería de imágenes destacadas

### Opción 2: Vista por Corporaciones (CARs)

**Paso 6.1:** Navegar en RStudio:
```
File → Open File → 4_Dashboard/Dashboard_Vista_Corporaciones.R
```

**Paso 6.2:** Click en **"Run App"**

**🎯 Funcionalidades:**
- Filtrar por **Corporación Autónoma Regional** (ej: CORPORINOQUIA, CORPOCALDAS)
- Filtrar por **Evento**
- Mapa con **polígonos de jurisdicción** de CARs (shapefile integrado)
- Mismas visualizaciones que Vista por Proyectos

### Controles del Dashboard

**Selectores principales:**

| Control | Descripción | Valores |
|---------|-------------|---------|
| **Proyecto/Corporación** | Entidad a visualizar | ID del proyecto o nombre de CAR |
| **Evento** | Período de muestreo | 2020_2, 2021_2, 2025_1, etc. |
| **Intervalo** | Filtro de independencia | 1 min, 30 min (sugerido), 1h, 6h, 12h |

**Botones de acción:**

- **Aplicar selección** ✅: Ejecutar filtros y cargar datos
- **Limpiar selección** 🔄: Resetear filtros a estado inicial
- **Descargar tabla** 📥: Exportar ranking de especies a CSV
- **Capturar pantalla** 📸: Guardar dashboard completo como PNG

---

## 🔧 Resolución de Problemas Comunes

### Problema 1: "No such file or directory" al ejecutar Python

**Causa:** Ruta incorrecta o archivos CSV faltantes

**Solución:**
```bash
# Verificar que estás en la carpeta correcta
pwd  # (macOS/Linux)
cd   # (Windows)

# Debe mostrar: .../3_processing_pipeline

# Verificar que existen los archivos CSV
ls ../1_Data_RAW_WI/*.csv  # (macOS/Linux)
dir ..\1_Data_RAW_WI\*.csv  # (Windows)
```

### Problema 2: "ModuleNotFoundError: No module named 'pandas'"

**Causa:** Entorno virtual no activado o dependencias no instaladas

**Solución:**
```bash
# Activar entorno virtual
# Windows (CMD)
venv_otus_pipeline\Scripts\activate

# Windows (PowerShell)
.\venv_otus_pipeline\Scripts\Activate.ps1

# macOS/Linux
source venv_otus_pipeline/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### Problema 3: "Error in library(DT) : there is no package called 'DT'"

**Causa:** Paquete R no instalado

**Solución en RStudio:**
```r
install.packages("DT")
library(DT)  # Verificar instalación
```

### Problema 4: Dashboard muestra "Archivos parquet no encontrados"

**Causa:** Pipeline Python no ejecutado o archivos no en la ubicación correcta

**Solución:**
```bash
# Verificar existencia de archivos Parquet
ls 4_Dashboard/dashboard_input_data/*.parquet  # (macOS/Linux)
dir 4_Dashboard\dashboard_input_data\*.parquet  # (Windows)

# Si no existen, ejecutar pipeline:
cd 3_processing_pipeline
python process_RAW_data_WI.py
```

### Problema 5: "Error: fechas inconsistentes filtradas: 3,661 (2.3%)"

**Causa:** Esto es **NORMAL**. El pipeline detectó y eliminó registros con fechas incorrectas (ej: evento 2025_1 con timestamps de 2019).

**Acción:** Ninguna. El pipeline funcionó correctamente.

### Problema 6: Dashboard carga muy lento

**Causa:** Archivos Parquet muy grandes o computador con recursos limitados

**Soluciones:**
1. Filtrar por proyecto/evento específico en lugar de "TODOS"
2. Cerrar otras aplicaciones que consuman RAM
3. Reducir intervalo de independencia (usar 1h o 6h en lugar de 30min)

---

## 📚 Recursos Adicionales

### Documentación del Proyecto

| Archivo | Descripción |
|---------|-------------|
| `ARCHITECTURE.md` | Arquitectura técnica completa |
| `PIPELINE.md` | Detalles del proceso ETL |
| `INSTALL.md` | Guía de instalación detallada |
| `MANUAL_OPERACION.md` | Manual técnico de operación |
| `DOC_Dashboard_Vista_Proyectos.md` | Documentación del dashboard de proyectos |
| `Dashboard_Vista_Corporaciones.md` | Documentación del dashboard de CARs |

### Enlaces Útiles

- **Wildlife Insights:** https://www.wildlifeinsights.org/
- **Documentación de Shiny:** https://shiny.posit.co/
- **Apache Arrow (Parquet):** https://arrow.apache.org/docs/python/parquet.html
- **Guía de dplyr:** https://dplyr.tidyverse.org/
- **Leaflet para R:** https://rstudio.github.io/leaflet/

---

## 📞 Contacto y Soporte

**Desarrolladores:**
- Jorge Ahumada - Conservation International (2020)
- Cristian C. Acevedo - Instituto Humboldt (2025)

**Institución:**
- Instituto de Investigación de Recursos Biológicos Alexander von Humboldt
- Red OTUS Colombia

**Licencia:** CC0 1.0 Universal (Dominio Público)

---

## ✨ Resumen de Comandos Rápidos

### Primera Ejecución (Configuración Completa)

```bash
# 1. Copiar archivos CSV a 1_Data_RAW_WI/

# 2. Configurar Python
cd 3_processing_pipeline
python -m venv venv_otus_pipeline
venv_otus_pipeline\Scripts\activate  # Windows CMD
pip install -r requirements.txt

# 3. Ejecutar pipeline
python process_RAW_data_WI.py

# 4. Validar (opcional)
python analyze_parquet_files.py
```

```r
# 5. Configurar R (en RStudio)
install.packages(c("shiny", "shinydashboard", "dplyr", "plotly", "leaflet", "DT", "arrow"))

# 6. Abrir y ejecutar dashboard
# File → Open → 4_Dashboard/Dashboard_Vista_Proyectos.R
# Click "Run App"
```

### Ejecuciones Posteriores (Solo Actualizar Datos)

```bash
# 1. Actualizar archivos CSV en 1_Data_RAW_WI/

# 2. Activar entorno Python
cd 3_processing_pipeline
venv_otus_pipeline\Scripts\activate  # Windows CMD

# 3. Re-ejecutar pipeline
python process_RAW_data_WI.py

# 4. Abrir dashboard en RStudio (sin reinstalar paquetes)
```

---

**🎉 ¡Listo! Dashboard operativo en menos de 45 minutos**

Si encuentras problemas no documentados aquí, revisa `INSTALL.md` para detalles técnicos avanzados o contacta al equipo de desarrollo.
