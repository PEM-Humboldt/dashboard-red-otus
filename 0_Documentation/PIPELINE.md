# Documentación Técnica del Pipeline Python

## 📋 Tabla de Contenidos

- [Información General](#-información-general)
- [Arquitectura Modular](#-arquitectura-modular)
- [Flujo de Procesamiento](#-flujo-de-procesamiento)
- [Módulos del Pipeline](#-módulos-del-pipeline)
- [Funciones Principales](#-funciones-principales)
- [Formatos de Datos](#-formatos-de-datos)
- [Validación y Control de Calidad](#-validación-y-control-de-calidad)
- [Configuración Avanzada](#-configuración-avanzada)
- [Optimización y Rendimiento](#-optimización-y-rendimiento)
- [Resolución de Problemas](#-resolución-de-problemas)

---

## 📌 Información General

**Archivo principal:** `3_processing_pipeline/process_RAW_data_WI.py`  
**Versión:** 3.0 (Arquitectura Modular)  
**Autor:** Proyecto OTUS - Instituto Humboldt  
**Última actualización:** Enero 2025

### Propósito

Pipeline ETL (Extract, Transform, Load) que procesa datos crudos de cámaras trampa desde Wildlife Insights y genera archivos Parquet optimizados para visualización en dashboards R Shiny.

### Capacidades

- ✅ **Carga masiva** de archivos CSV (múltiples proyectos)
- ✅ **Validación automática** de formato y calidad
- ✅ **Filtrado inteligente** por eventos de muestreo (YYYY_N)
- ✅ **Enriquecimiento** de taxonomía y metadata
- ✅ **Análisis geoespacial** (asignación de CARs por coordenadas)
- ✅ **Generación optimizada** de Parquet (columnar compression)
- ✅ **Reportes de calidad** detallados

---

## 🏗️ Arquitectura Modular

### Estructura de Directorios

```
3_processing_pipeline/
├── process_RAW_data_WI.py       # Orquestador principal (389 líneas)
├── requirements.txt             # Dependencias Python
└── src/                         # Módulos del pipeline
    ├── __init__.py
    ├── utils.py                 # Carga y filtrado de datos
    ├── transformations.py       # Transformaciones y enriquecimiento
    ├── generate_parquets.py     # Generación de archivos Parquet
    └── validation.py            # Validación de calidad
```

### Diagrama de Dependencias

```
process_RAW_data_WI.py (main)
    ↓
┌───────────────────────────────────────────────────┐
│                     src/                          │
├───────────────────────────────────────────────────┤
│                                                   │
│  utils.py                                         │
│    ├─ concatenar_archivos_csv()                   │
│    ├─ procesar_timestamps()                       │
│    ├─ filtrar_por_subproject_valido()             │
│    └─ limpiar_registros_cv()                      │
│                                                   │
│  transformations.py                               │
│    ├─ crear_nombre_cientifico()                   │
│    ├─ agregar_metadata_administrativa()           │
│    ├─ merge_images_deployments()                  │
│    ├─ merge_with_projects()                       │
│    ├─ asignar_corporacion_geografica()            │
│    └─ calcular_deployment_days()                  │
│                                                   │
│  generate_parquets.py                             │
│    ├─ generar_observations_parquet()              │
│    ├─ generar_deployments_parquet()               │
│    ├─ generar_projects_parquet()                  │
│    └─ generar_todas_las_tablas()                  │
│                                                   │
│  validation.py                                    │
│    ├─ validar_observations_parquet()              │
│    ├─ validar_deployments_parquet()               │
│    ├─ validar_projects_parquet()                  │
│    └─ generar_reporte_calidad()                   │
│                                                   │
└───────────────────────────────────────────────────┘
```

---

## 🔄 Flujo de Procesamiento

### Diagrama de Flujo Completo

```
┌─────────────────────────────────────────────────────────────┐
│ FASE 0: PREPARACIÓN DEL ENTORNO                             │
│   • Limpieza de carpeta de salida                           │
│   • Eliminación de archivos Parquet previos                 │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ FASE 1: CARGA DE DATOS CRUDOS                               │
│   1.1 Cargar projects.csv                                   │
│   1.2 Cargar deployments.csv                                │
│   1.3 Concatenar images_*.csv (múltiples archivos)          │
│       → concatenar_archivos_csv()                           │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ FASE 2: FILTRADO Y LIMPIEZA                                 │
│   2.1 Procesar timestamps                                   │
│       → procesar_timestamps()                               │
│   2.2 Limpiar registros Computer Vision (CV)                │
│       → limpiar_registros_cv()                              │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ FASE 3: ENRIQUECIMIENTO Y TRANSFORMACIONES                  │
│   3.1 Crear nombre científico (sp_binomial)                 │
│       → crear_nombre_cientifico()                           │
│   3.2 Agregar metadata administrativa                       │
│       → agregar_metadata_administrativa()                   │
│   3.3 Merge imágenes + deployments                          │
│       → merge_images_deployments()                          │
│   3.4 Filtrar por subproject_name válido (YYYY_N)           │
│       → filtrar_por_subproject_valido()                     │
│   3.5 Merge con projects                                    │
│       → merge_with_projects()                               │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ FASE 4: ANÁLISIS GEOGRÁFICO                                 │
│   4.1 Asignar Corporaciones por coordenadas                 │
│       → asignar_corporacion_geografica()                    │
│         ├─ Cargar shapefile CAR_MPIO.shp                    │
│         ├─ Crear puntos geométricos (lat, lon)              │
│         ├─ Spatial join (point-in-polygon)                  │
│         └─ Asignar NOMBRE_CAR a cada deployment             │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ FASE 4.5: PREPARACIÓN FINAL DE DATOS                        │
│   4.5.1 Calcular deployment_days                            │
│         → calcular_deployment_days()                        │
│   4.5.2 Diagnosticar columnas duplicadas                    │
│   4.5.3 Crear columnas de fecha (photo_date, hour)          │
│   4.5.4 Verificar subproject_name                           │
│   4.5.5 Validar columnas esenciales                         │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ FASE 5: GENERACIÓN DE ARCHIVOS PARQUET                      │
│   5.1 Generar observations.parquet (20 columnas)            │
│       → generar_observations_parquet()                      │
│   5.2 Generar deployments.parquet (15 columnas)             │
│       → generar_deployments_parquet()                       │
│   5.3 Generar projects.parquet (10 columnas)                │
│       → generar_projects_parquet()                          │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ FASE 6: VALIDACIÓN DE CALIDAD                               │
│   6.1 Validar observations.parquet                          │
│       → validar_observations_parquet()                      │
│   6.2 Validar deployments.parquet                           │
│       → validar_deployments_parquet()                       │
│   6.3 Validar projects.parquet                              │
│       → validar_projects_parquet()                          │
│   6.4 Generar reporte consolidado                           │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ SALIDA: 3 ARCHIVOS PARQUET OPTIMIZADOS                      │
│   • observations.parquet   (500 KB - 5 MB)                  │
│   • deployments.parquet    (50 KB - 200 KB)                 │
│   • projects.parquet       (10 KB - 50 KB)                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Módulos del Pipeline

### 1. `src/utils.py` - Utilidades de Carga y Filtrado

**Funciones principales:**

#### `concatenar_archivos_csv(folder_path, patron='images')`

Concatena múltiples archivos CSV de imágenes de Wildlife Insights.

**Parámetros:**
- `folder_path` (str): Ruta a carpeta con archivos CSV
- `patron` (str): Patrón de búsqueda (default: 'images')

**Retorna:**
- `pd.DataFrame`: DataFrame consolidado con todas las imágenes

**Proceso:**
1. Buscar archivos que coincidan con `images_*.csv`
2. Leer cada archivo con `low_memory=False`
3. Concatenar verticalmente con `pd.concat()`
4. Resetear índices

**Ejemplo:**
```python
images = concatenar_archivos_csv(
    folder_path='../1_Data_RAW_WI',
    patron='images'
)
# Output: DataFrame con ~250,000 registros
```

#### `procesar_timestamps(df)`

Convierte columnas de fecha/hora a formato datetime estándar.

**Parámetros:**
- `df` (pd.DataFrame): DataFrame con columnas de tiempo

**Retorna:**
- `pd.DataFrame`: DataFrame con timestamps procesados

**Columnas procesadas:**
- `photo_datetime` → `datetime64[ns]`
- `deployment_start` → `datetime64[ns]`
- `deployment_end` → `datetime64[ns]`

**Manejo de errores:**
- Valores inválidos → `pd.NaT`
- Formatos múltiples → inferencia automática

#### `filtrar_por_subproject_valido(df)`

Filtra registros por eventos de muestreo válidos (formato YYYY_N, año ≥ 2024).

**Parámetros:**
- `df` (pd.DataFrame): DataFrame con columna `subproject_name`

**Retorna:**
- `pd.DataFrame`: DataFrame filtrado

**Criterios de validación:**
```python
# Formato válido: YYYY_N
# Ejemplos válidos:
#   - 2024_1
#   - 2024_2
#   - 2025_1
#
# Rechazados:
#   - 2023_1 (año < 2024)
#   - 2024 (sin sufijo _N)
#   - test_1 (no numérico)
#   - vacío o NaN
```

**Proceso:**
1. Filtrar no nulos
2. Verificar longitud == 6 caracteres
3. Extraer año (primeros 4 caracteres)
4. Validar año >= 2024
5. Verificar formato YYYY_N con regex

#### `limpiar_registros_cv(df)`

Elimina registros generados por Computer Vision (identificaciones automáticas).

**Parámetros:**
- `df` (pd.DataFrame): DataFrame con columna `identified_by`

**Retorna:**
- `pd.DataFrame`: DataFrame sin registros CV

**Criterio de filtrado:**
```python
# Eliminar registros donde:
df = df[df['identified_by'] != 'Machine']
```

---

### 2. `src/transformations.py` - Transformaciones y Enriquecimiento

#### `crear_nombre_cientifico(df)`

Crea columna `sp_binomial` combinando género y especie.

**Parámetros:**
- `df` (pd.DataFrame): DataFrame con columnas `genus` y `species`

**Retorna:**
- `pd.DataFrame`: DataFrame con `sp_binomial` agregada

**Lógica:**
```python
# Caso 1: Género y especie presentes
genus = "Panthera", species = "onca"
→ sp_binomial = "Panthera onca"

# Caso 2: Solo género
genus = "Panthera", species = NaN
→ sp_binomial = "Panthera sp."

# Caso 3: Ambos vacíos
genus = NaN, species = NaN
→ sp_binomial = "Unknown"
```

#### `agregar_metadata_administrativa(df, admin_name, organization)`

Agrega columnas de metadata administrativa.

**Parámetros:**
- `df` (pd.DataFrame): DataFrame de observaciones
- `admin_name` (str): Nombre del administrador
- `organization` (str): Organización responsable

**Retorna:**
- `pd.DataFrame`: DataFrame con columnas agregadas

**Columnas creadas:**
```python
df['admin_name'] = admin_name
df['organization'] = organization
df['processing_date'] = pd.Timestamp.now()
```

#### `merge_images_deployments(images_df, deployments_df)`

Fusiona datos de imágenes con metadata de deployments.

**Parámetros:**
- `images_df` (pd.DataFrame): Observaciones de fauna
- `deployments_df` (pd.DataFrame): Configuración de cámaras

**Retorna:**
- `pd.DataFrame`: DataFrame fusionado

**Columnas clave del merge:**
```python
# Key: deployment_id
# Type: left join (conservar todas las imágenes)
# Columnas agregadas:
#   - latitude, longitude (coordenadas)
#   - placename (nombre del sitio)
#   - deployment_start, deployment_end (fechas)
#   - subproject_name (evento de muestreo)
```

#### `merge_with_projects(data_df, projects_df)`

Fusiona datos con catálogo de proyectos.

**Parámetros:**
- `data_df` (pd.DataFrame): Observaciones enriquecidas
- `projects_df` (pd.DataFrame): Catálogo de proyectos

**Retorna:**
- `pd.DataFrame`: DataFrame con metadata de proyecto

**Columnas agregadas:**
```python
# Key: project_id
# Columnas:
#   - project_name (nombre del proyecto)
#   - project_admin (administrador)
#   - project_country (país)
```

#### `asignar_corporacion_geografica(deployments_df, shapefile_path)`

Asigna Corporaciones Autónomas Regionales (CARs) por análisis geoespacial.

**Parámetros:**
- `deployments_df` (pd.DataFrame): Deployments con coordenadas
- `shapefile_path` (str): Ruta al shapefile de CARs

**Retorna:**
- `pd.DataFrame`: Tabla con `project_id` y `Corporacion`

**Proceso:**
```python
1. Cargar shapefile con geopandas
   → car_gdf = gpd.read_file(shapefile_path)

2. Crear GeoDataFrame de deployments
   → geometry = [Point(lon, lat) for lat, lon in coords]
   → deployments_gdf = gpd.GeoDataFrame(deployments_df, geometry=geometry, crs='EPSG:4326')

3. Spatial join (point-in-polygon)
   → result = gpd.sjoin(deployments_gdf, car_gdf, how='left', predicate='within')

4. Agrupar por project_id (mayoría de deployments)
   → corporacion = result.groupby('project_id')['NOMBRE_CAR'].agg(lambda x: x.mode()[0])

5. Retornar tabla project_id → Corporacion
```

**Manejo de casos especiales:**
- Deployments sin coordenadas → `Corporacion = NaN`
- Punto fuera de polígonos → `Corporacion = "Sin asignar"`
- Múltiples CARs en proyecto → Seleccionar moda (más frecuente)

#### `calcular_deployment_days(df)`

Calcula días de funcionamiento de cada deployment.

**Parámetros:**
- `df` (pd.DataFrame): DataFrame con `deployment_start` y `deployment_end`

**Retorna:**
- `pd.DataFrame`: DataFrame con columna `deployment_days`

**Fórmula:**
```python
deployment_days = (deployment_end - deployment_start).dt.days
```

---

### 3. `src/generate_parquets.py` - Generación de Archivos Parquet

#### `generar_observations_parquet(df, output_path)`

Genera archivo Parquet de observaciones con 20 columnas seleccionadas.

**Parámetros:**
- `df` (pd.DataFrame): DataFrame completo de observaciones
- `output_path` (str): Ruta de salida

**Retorna:**
- `bool`: True si exitoso, False si error

**Columnas incluidas (20):**
```python
columnas_observations = [
    'project_id',          # ID del proyecto
    'project_name',        # Nombre del proyecto
    'Corporacion',         # CAR asignada geográficamente
    'subproject_name',     # Evento de muestreo (YYYY_N)
    'deployment_name',     # ID del deployment
    'placename',           # Nombre del sitio
    'latitude',            # Coordenada latitud
    'longitude',           # Coordenada longitud
    'sp_binomial',         # Nombre científico (Genus species)
    'genus',               # Género taxonómico
    'species',             # Epíteto específico
    'class',               # Clase taxonómica (Mammalia, Aves)
    'common_name',         # Nombre común
    'photo_datetime',      # Timestamp de la fotografía
    'photo_date',          # Fecha (YYYY-MM-DD)
    'hour',                # Hora del día (0-23)
    'deployment_days',     # Días de funcionamiento del deployment
    'admin_name',          # Administrador del proyecto
    'organization',        # Organización responsable
    'identified_by'        # Quién identificó (Human/Machine)
]
```

**Configuración de compresión:**
```python
df[columnas_observations].to_parquet(
    output_path,
    engine='pyarrow',
    compression='snappy',  # Balance velocidad/tamaño
    index=False
)
```

#### `generar_deployments_parquet(df, output_path)`

Genera archivo Parquet de deployments (15 columnas).

**Columnas incluidas:**
```python
columnas_deployments = [
    'deployment_id',
    'deployment_name',
    'project_id',
    'Corporacion',
    'subproject_name',
    'placename',
    'latitude',
    'longitude',
    'deployment_start',
    'deployment_end',
    'deployment_days',
    'camera_id',
    'feature_type',
    'bait',
    'quiet_period'
]
```

#### `generar_projects_parquet(df, output_path)`

Genera archivo Parquet de proyectos (10 columnas).

**Columnas incluidas:**
```python
columnas_projects = [
    'project_id',
    'project_name',
    'project_admin',
    'project_country',
    'metadata_license',
    'embargo',
    'observation_license',
    'sensor_height',
    'sensor_orientation',
    'detection_distance'
]
```

#### `generar_todas_las_tablas(observations_df, deployments_df, projects_df, output_dir)`

Función orquestadora que genera las 3 tablas simultáneamente.

**Parámetros:**
- `observations_df` (pd.DataFrame): Observaciones enriquecidas
- `deployments_df` (pd.DataFrame): Deployments procesados
- `projects_df` (pd.DataFrame): Catálogo de proyectos
- `output_dir` (str): Directorio de salida

**Retorna:**
- `bool`: True si todas exitosas, False si alguna falla

**Proceso:**
```python
1. Verificar/crear directorio de salida
2. Generar observations.parquet
3. Generar deployments.parquet
4. Generar projects.parquet
5. Verificar tamaños de archivos
6. Reportar estadísticas
```

---

### 4. `src/validation.py` - Validación de Calidad

#### `validar_observations_parquet(parquet_path)`

Valida estructura y contenido de observations.parquet.

**Verificaciones:**
```python
✓ Archivo existe
✓ Formato Parquet válido
✓ Número de registros > 0
✓ Columnas esperadas presentes (20 columnas)
✓ Tipos de datos correctos
✓ Valores nulos en columnas críticas < 5%
✓ Rango de fechas válido (> 2020)
✓ Coordenadas en rango Colombia (-5 < lat < 13, -80 < lon < -66)
```

**Output de consola:**
```
✓ observations.parquet cargado: 175,000 registros
✓ Columnas presentes: 20/20
✓ Tipos de datos correctos
⚠ Columna 'common_name' tiene 2.3% valores nulos (aceptable)
✓ Rango de fechas: 2024-01-15 a 2025-12-09
✓ Coordenadas válidas (100% dentro de Colombia)
```

#### `validar_deployments_parquet(parquet_path)`

Valida deployments.parquet.

**Verificaciones:**
```python
✓ Archivo existe
✓ Número de deployments único
✓ Coordenadas válidas
✓ Fechas start < end
✓ deployment_days > 0
✓ No hay duplicados de deployment_id
```

#### `validar_projects_parquet(parquet_path)`

Valida projects.parquet.

**Verificaciones:**
```python
✓ Archivo existe
✓ project_id único (sin duplicados)
✓ Columnas obligatorias presentes
✓ Licencias válidas
```

#### `generar_reporte_calidad(observations_path, deployments_path, projects_path)`

Genera reporte consolidado de calidad de datos.

**Output:**
```
═══════════════════════════════════════════════════════
REPORTE DE CALIDAD DE DATOS - WILDLIFE INSIGHTS
═══════════════════════════════════════════════════════

1. OBSERVATIONS.PARQUET
   • Registros totales: 175,000
   • Especies únicas: 87
   • Proyectos: 12
   • Eventos: 8
   • Rango temporal: 2024-01-15 a 2025-12-09
   • Completitud: 97.8%

2. DEPLOYMENTS.PARQUET
   • Deployments totales: 1,200
   • Proyectos: 12
   • Duración promedio: 45 días
   • Coordenadas válidas: 100%

3. PROJECTS.PARQUET
   • Proyectos totales: 12
   • Corporaciones: 8
   • Países: 1 (Colombia)

VALIDACIÓN GENERAL: ✓ APROBADO
═══════════════════════════════════════════════════════
```

---

## 📊 Formatos de Datos

### Entrada: Archivos CSV de Wildlife Insights

#### `projects.csv`

**Estructura:**
```csv
project_id,project_name,project_admin,project_country,metadata_license,...
2002517,Proyecto CAM Norte,Juan Pérez,Colombia,CC0,...
2008342,Fototrampeo CORPOCALDAS,Ana López,Colombia,CC-BY,...
```

**Columnas clave:**
- `project_id` (int): Identificador único del proyecto
- `project_name` (str): Nombre descriptivo
- `project_admin` (str): Responsable administrativo
- `project_country` (str): País de origen

#### `deployments.csv`

**Estructura:**
```csv
deployment_id,deployment_name,project_id,placename,latitude,longitude,deployment_start,deployment_end,...
d001,CAM_Site001,2002517,Bosque La Pradera,4.6542,-74.1234,2024-03-15,2024-05-20,...
d002,CAM_Site002,2002517,Río Verde,4.7123,-74.0987,2024-03-16,2024-05-21,...
```

**Columnas clave:**
- `deployment_id` (str): ID único del deployment
- `deployment_name` (str): Nombre del sitio
- `latitude`, `longitude` (float): Coordenadas WGS84
- `deployment_start`, `deployment_end` (str): Fechas ISO 8601

#### `images_*.csv` (múltiples archivos)

**Estructura:**
```csv
project_id,deployment_id,genus,species,common_name,photo_datetime,identified_by,...
2002517,d001,Panthera,onca,Jaguar,2024-04-12 14:35:22,Human,...
2002517,d001,Tapirus,terrestris,Danta,2024-04-13 08:12:45,Human,...
```

**Columnas clave:**
- `project_id` (int): Vincula con projects.csv
- `deployment_id` (str): Vincula con deployments.csv
- `genus`, `species` (str): Taxonomía
- `common_name` (str): Nombre común
- `photo_datetime` (str): Timestamp de captura
- `identified_by` (str): Human/Machine

### Salida: Archivos Parquet Optimizados

#### `observations.parquet`

**Esquema:**
```
project_id: int64
project_name: string
Corporacion: string
subproject_name: string
deployment_name: string
placename: string
latitude: float64
longitude: float64
sp_binomial: string
genus: string
species: string
class: string
common_name: string
photo_datetime: datetime64[ns]
photo_date: date32
hour: int8
deployment_days: int16
admin_name: string
organization: string
identified_by: string
```

**Tamaño típico:** 500 KB - 5 MB  
**Compresión:** Snappy (~70% reducción vs CSV)

#### `deployments.parquet`

**Esquema:**
```
deployment_id: string
deployment_name: string
project_id: int64
Corporacion: string
subproject_name: string
placename: string
latitude: float64
longitude: float64
deployment_start: datetime64[ns]
deployment_end: datetime64[ns]
deployment_days: int16
camera_id: string
feature_type: string
bait: string
quiet_period: int16
```

**Tamaño típico:** 50 KB - 200 KB

#### `projects.parquet`

**Esquema:**
```
project_id: int64
project_name: string
project_admin: string
project_country: string
metadata_license: string
embargo: bool
observation_license: string
sensor_height: float32
sensor_orientation: string
detection_distance: float32
```

**Tamaño típico:** 10 KB - 50 KB

---

## ✅ Validación y Control de Calidad

### Criterios de Validación

#### 1. Validación de Formato `subproject_name`

**Regla:** Debe tener formato `YYYY_N` donde YYYY ≥ 2024

**Ejemplos válidos:**
- `2024_1` ✓
- `2024_2` ✓
- `2025_1` ✓

**Ejemplos rechazados:**
- `2023_1` ✗ (año < 2024)
- `2024` ✗ (falta sufijo _N)
- `test_1` ✗ (no numérico)
- ` ` ✗ (vacío)

**Código de validación:**
```python
def es_subproject_valido(subproject_name):
    if pd.isna(subproject_name) or len(str(subproject_name)) != 6:
        return False
    
    try:
        year = int(str(subproject_name)[:4])
        return year >= 2024
    except:
        return False
```

#### 2. Validación de Coordenadas

**Rango válido para Colombia:**
- Latitud: -5° a 13° N
- Longitud: -80° a -66° W

**Código:**
```python
def coordenadas_validas(lat, lon):
    return (-5 <= lat <= 13) and (-80 <= lon <= -66)
```

#### 3. Validación de Fechas

**Criterios:**
- `deployment_start` < `deployment_end`
- Fechas > 2020-01-01
- `photo_datetime` entre `deployment_start` y `deployment_end` (con tolerancia)

#### 4. Validación de Completitud

**Columnas críticas (< 5% nulos permitido):**
- `project_id`
- `deployment_name`
- `sp_binomial`
- `latitude`, `longitude`
- `photo_datetime`

**Columnas opcionales (> 5% nulos permitido):**
- `common_name`
- `identified_by`
- `bait`

### Reportes Automáticos

El pipeline genera reportes detallados al finalizar:

```
═══════════════════════════════════════════════════════
VALIDACIÓN DE OBSERVATIONS.PARQUET
═══════════════════════════════════════════════════════

✓ Archivo cargado exitosamente
✓ Registros totales: 175,234
✓ Columnas presentes: 20/20

COMPLETITUD POR COLUMNA:
  project_id:         100.0%  ✓
  project_name:       100.0%  ✓
  Corporacion:         98.5%  ✓
  sp_binomial:        100.0%  ✓
  common_name:         97.2%  ✓
  latitude:           100.0%  ✓
  longitude:          100.0%  ✓
  photo_datetime:     100.0%  ✓

DISTRIBUCIÓN DE DATOS:
  Especies únicas:             87
  Proyectos:                   12
  Eventos (subproject_name):    8
  Deployments:              1,200
  
RANGO TEMPORAL:
  Fecha mínima:  2024-01-15
  Fecha máxima:  2025-12-09
  Días totales:  329

COORDENADAS:
  Rango latitud:   1.23° a 11.45°  ✓
  Rango longitud: -77.89° a -68.12° ✓
  Fuera de Colombia: 0 registros  ✓

═══════════════════════════════════════════════════════
```

---

## ⚙️ Configuración Avanzada

### Variables de Configuración en `process_RAW_data_WI.py`

```python
# Rutas base
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BASE_RAW_PATH = os.path.join(PROJECT_ROOT, '1_Data_RAW_WI')
BASE_OUTPUT_PATH = os.path.join(PROJECT_ROOT, '4_Dashboard', 'dashboard_input_data')
SHAPEFILE_PATH = os.path.join(PROJECT_ROOT, '2_Data_Shapefiles_CARs', 'CAR_MPIO.shp')
```

**Modificar para estructura diferente:**
```python
# Ejemplo: Carpeta de salida personalizada
BASE_OUTPUT_PATH = os.path.join(PROJECT_ROOT, 'output', 'parquet_files')
```

### Parámetros de Compresión Parquet

```python
# En src/generate_parquets.py
df.to_parquet(
    output_path,
    engine='pyarrow',
    compression='snappy',  # Opciones: 'snappy', 'gzip', 'brotli', 'zstd'
    index=False
)
```

**Comparación de compresiones:**

| Algoritmo | Tamaño | Velocidad Escritura | Velocidad Lectura | Uso Recomendado |
|-----------|--------|---------------------|-------------------|-----------------|
| `snappy` | ~70% reducción | ⚡⚡⚡ Muy rápida | ⚡⚡⚡ Muy rápida | **Dashboard interactivo** ✓ |
| `gzip` | ~80% reducción | ⚡⚡ Moderada | ⚡⚡ Moderada | Archivado a largo plazo |
| `brotli` | ~85% reducción | ⚡ Lenta | ⚡⚡ Moderada | Compresión máxima |
| `zstd` | ~75% reducción | ⚡⚡⚡ Rápida | ⚡⚡⚡ Rápida | Balance óptimo |

**Recomendación:** Mantener `snappy` para dashboards (velocidad > tamaño).

### Configuración de Metadata Administrativa

```python
# En FASE 3.2 de process_RAW_data_WI.py
images = agregar_metadata_administrativa(
    images,
    admin_name="Cristian Acevedo",      # Personalizar
    organization="Instituto Humboldt"   # Personalizar
)
```

---

## 🚀 Optimización y Rendimiento

### Benchmarks de Rendimiento

**Hardware de prueba:**
- CPU: Intel i7-10750H (6 cores)
- RAM: 16 GB
- SSD: NVMe PCIe 3.0

**Tiempos de ejecución:**

| Tamaño de Datos | Tiempo Total | Fase Más Lenta |
|-----------------|--------------|----------------|
| 50,000 registros | ~15 segundos | Análisis geográfico (5s) |
| 175,000 registros | ~45 segundos | Análisis geográfico (18s) |
| 500,000 registros | ~2.5 minutos | Análisis geográfico (1m) |

### Optimizaciones Implementadas

#### 1. Lectura Eficiente de CSV

```python
# Antes (lento):
images = pd.read_csv('images_large.csv')

# Después (optimizado):
images = pd.read_csv('images_large.csv', low_memory=False)
```

#### 2. Concatenación de DataFrames

```python
# Antes (ineficiente - múltiples appends):
result = pd.DataFrame()
for file in files:
    df = pd.read_csv(file)
    result = result.append(df)

# Después (eficiente - una sola concatenación):
dfs = [pd.read_csv(file) for file in files]
result = pd.concat(dfs, ignore_index=True)
```

#### 3. Filtrado Temprano

```python
# Optimización: Filtrar datos innecesarios antes de merge
images = limpiar_registros_cv(images)  # Reducir tamaño antes de merge
data = merge_images_deployments(images, deployments)  # Merge más rápido
```

#### 4. Spatial Join Optimizado

```python
# En asignar_corporacion_geografica()
# Usar índice espacial implícito de geopandas
result = gpd.sjoin(deployments_gdf, car_gdf, how='left', predicate='within')
# GeoPandas usa R-tree index automáticamente
```

### Recomendaciones para Datasets Grandes (> 1M registros)

**1. Procesamiento en Chunks:**

```python
# Modificar concatenar_archivos_csv() para lectura en chunks
chunk_size = 100000
chunks = []
for file in image_files:
    for chunk in pd.read_csv(file, chunksize=chunk_size):
        # Filtrar inmediatamente
        chunk = chunk[chunk['subproject_name'].notna()]
        chunks.append(chunk)

images = pd.concat(chunks, ignore_index=True)
```

**2. Usar Dask para Paralelización:**

```python
import dask.dataframe as dd

# Lectura paralela de múltiples CSVs
ddf = dd.read_csv('../1_Data_RAW_WI/images_*.csv')

# Procesamiento paralelo
ddf = ddf[ddf['identified_by'] != 'Machine']
ddf = ddf.compute()  # Convertir a pandas al final
```

**3. Reducir Uso de Memoria:**

```python
# Especificar tipos de datos eficientes
dtypes = {
    'project_id': 'int32',  # En lugar de int64
    'deployment_name': 'category',  # En lugar de object
    'class': 'category',
    'genus': 'category'
}

images = pd.read_csv('images.csv', dtype=dtypes)
```

---

## 🔧 Resolución de Problemas

### Errores Comunes

#### Error: `FileNotFoundError: CAR_MPIO.shp not found`

**Causa:** Shapefile no está en la ubicación esperada.

**Solución:**
```bash
# Verificar que existen todos los archivos
ls -l 2_Data_Shapefiles_CARs/CAR_MPIO.*

# Debe mostrar:
# CAR_MPIO.shp
# CAR_MPIO.shx
# CAR_MPIO.dbf
# CAR_MPIO.prj
```

Si falta alguno, descargar shapefile completo.

#### Error: `KeyError: 'subproject_name'`

**Causa:** Columna `subproject_name` no existe en deployments.csv.

**Solución:**
1. Verificar que Wildlife Insights exportó el campo correctamente
2. Si no existe, crear columna temporal:
   ```python
   deployments['subproject_name'] = deployments['project_id'].astype(str) + '_1'
   ```

#### Error: `ValueError: No objects to concatenate`

**Causa:** No se encontraron archivos `images_*.csv`.

**Solución:**
```python
# Verificar archivos en carpeta
import glob
files = glob.glob('../1_Data_RAW_WI/images_*.csv')
print(f"Archivos encontrados: {len(files)}")

# Si len(files) == 0:
# - Verificar nombre de archivos (debe empezar con "images_")
# - Verificar extensión (.csv, no .CSV o .txt)
```

#### Error: `MemoryError` durante procesamiento

**Causa:** Dataset muy grande para RAM disponible.

**Solución temporal:**
```python
# 1. Reducir tamaño de chunk en lectura
chunk_size = 50000  # Reducir de 100000

# 2. Liberar memoria después de cada fase
import gc
gc.collect()

# 3. Procesar proyectos individualmente
for project_id in projects['project_id'].unique():
    data_proyecto = images[images['project_id'] == project_id]
    # Procesar y guardar por separado
```

#### Warning: `DtypeWarning: Columns have mixed types`

**Causa:** Pandas infiere tipos incorrectamente.

**Solución:**
```python
# Especificar tipos explícitamente
images = pd.read_csv(
    file,
    dtype={
        'project_id': 'int',
        'deployment_id': 'str',
        'genus': 'str',
        'species': 'str'
    },
    low_memory=False
)
```

### Debugging del Pipeline

**Activar modo verbose:**

```python
# En process_RAW_data_WI.py, agregar después de imports:
import logging
logging.basicConfig(level=logging.DEBUG)

# Las funciones imprimirán información detallada
```

**Inspeccionar datos intermedios:**

```python
# Después de cada fase, agregar:
print(f"\n=== DEBUG: FASE X ===")
print(f"Columnas: {list(data.columns)}")
print(f"Tipos: {data.dtypes}")
print(f"Registros: {len(data)}")
print(f"Valores nulos:\n{data.isnull().sum()}")
print(data.head())
```

**Guardar checkpoints:**

```python
# Después de fases críticas, guardar CSV intermedio
data.to_csv('checkpoint_fase3.csv', index=False)

# Recuperar en caso de error:
data = pd.read_csv('checkpoint_fase3.csv')
```

---

## 📞 Soporte

Para problemas no resueltos en esta documentación:

1. **Revisar Issues:** https://github.com/[USUARIO]/Dashboard_Monitoreo_Camaras_Trampa_Red_OTUS_Colombia/issues
2. **Crear nuevo Issue** con:
   - Versión de Python y librerías (`pip list`)
   - Mensaje de error completo
   - Tamaño aproximado del dataset
   - Sistema operativo

---

<div align="center">

**Última actualización:** Enero 2025  
**Versión del pipeline:** 3.0 (Arquitectura Modular)

</div>
