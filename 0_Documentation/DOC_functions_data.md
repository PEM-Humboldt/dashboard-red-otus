# Documentación: functions_data.R

## Información General

**Archivo:** `functions_data.R`  
**Proyecto:** Dashboard IaVH - Red OTUS Colombia  
**Autor original:** Jorge Ahumada (Conservation International)  
**Adaptación:** Instituto Alexander von Humboldt (IaVH)  
**Colaborador:** Cristian C. Acevedo - Contratista Instituto Humboldt  
**Versión:** 2.0 - Arquitectura consolidada multi-evento  
**Última modificación:** 2025-12-09  

---

## Descripción

Este archivo contiene el conjunto de funciones de análisis y visualización para procesar datos de fototrampeo provenientes de **Wildlife Insights**. El código está optimizado para trabajar con la arquitectura Parquet consolidada del dashboard, soportando análisis multi-evento y multi-proyecto.

---

## Arquitectura de Datos

### Archivos Parquet Requeridos

El sistema utiliza 3 archivos consolidados en formato Parquet ubicados en `dashboard_input_data/`:

1. **observations.parquet**
   - Detecciones de fauna con metadata completa
   - Columnas clave: `project_id`, `subproject_name`, `deployment_name`, `sp_binomial`, `class`, `photo_datetime`

2. **deployments.parquet**
   - Configuración de cámaras trampa y sitios de muestreo
   - Columnas clave: `deployment_name`, `latitude`, `longitude`, `deployment_days`

3. **projects.parquet**
   - Catálogo de proyectos de la Red OTUS
   - Columnas clave: `project_id`, `project_short_name`, `project_admin`

---

## Funciones Principales

### 1. Funciones Auxiliares

#### `extract_date_ymd(df)`

**Descripción:** Extrae fechas de timestamps de Wildlife Insights en formato ISO 8601.

**Parámetros:**
- `df`: DataFrame con columnas `photo_datetime` o `date`

**Retorno:**
- Vector de objetos Date en formato `YYYY-MM-DD`

**Uso:**
```r
fechas <- extract_date_ymd(df_images)
```

---

### 2. Funciones de Manejo de Eventos

#### `obtener_eventos_disponibles()`

**Descripción:** Verifica la existencia de los archivos Parquet requeridos por el dashboard.

**Parámetros:** Ninguno

**Retorno:**
- `"CONSOLIDADO"`: Si todos los archivos existen
- `character(0)`: Si faltan archivos (con advertencias detalladas)

**Uso:**
```r
eventos <- obtener_eventos_disponibles()
if (length(eventos) == 0) {
  stop("Archivos parquet no encontrados")
}
```

**Advertencias generadas:**
- Carpeta `dashboard_input_data/` no encontrada
- Archivos `.parquet` faltantes
- Instrucciones para ejecutar `process_RAW_data_WI.py`

---

#### `cargar_datos_consolidados(interval = "30min")`

**Descripción:** Carga y procesa datos consolidados de fototrampeo desde archivos Parquet, generando estadísticas dinámicas por sitio.

**Parámetros:**
- `interval`: Intervalo temporal para cálculos futuros (valores válidos: '5seg', '1min', '30min', '1h', '6h', '24h')

**Retorno:**
Lista con 4 componentes:
- `iavhdata`: DataFrame de observaciones con metadata completa
- `tableSites`: DataFrame de estadísticas agregadas por sitio (imágenes, esfuerzo, especies)
- `projects`: DataFrame con información de proyectos
- `evento`: String "CONSOLIDADO" indicando modo de carga

Retorna `NULL` si hay errores en la carga.

**Uso:**
```r
datos <- cargar_datos_consolidados(interval = "30min")
observaciones <- datos$iavhdata
estadisticas_sitios <- datos$tableSites
proyectos <- datos$projects
```

**Operaciones ejecutadas:**
1. Validación de archivos Parquet
2. Carga con librería `arrow`
3. Enriquecimiento con nombres de proyecto
4. Cálculo de estadísticas por deployment:
   - Número de imágenes (`n`)
   - Número de deployments (`ndepl`)
   - Esfuerzo en días-cámara (`effort`)
   - Especies totales (`ospTot`)
   - Mamíferos (`ospMamiferos`)
   - Aves (`ospAves`)
5. Generación de rankings por métrica
6. Mapeo de compatibilidad (`subproject_name` → `evento_muestreo`)

**Salida en consola:**
```
✅ Datos cargados exitosamente:
   • 45821 observaciones
   • 156 sitios
   • 8 proyectos
   • 12 eventos
```

---

### 3. Funciones de Visualización y Análisis

#### `makeSpeciesTable(subset, interval = 30, unit = "minutes", species_stats = NULL)`

**Descripción:** Genera tabla de ranking de especies por eventos independientes, eliminando duplicados temporales.

**Parámetros:**
- `subset`: DataFrame de observaciones con columnas:
  - `sp_binomial`: Nombre científico
  - `class`: Clase taxonómica (Aves, Mammalia, etc.)
  - `deployment_name`: Identificador del sitio
  - `photo_datetime`: Timestamp de captura
- `interval`: Intervalo temporal para eliminar duplicados (default: 30)
- `unit`: Unidad de tiempo ('seconds', 'minutes', 'hours', 'days')
- `species_stats`: DataFrame pre-calculado con estadísticas (opcional, modo optimizado)

**Retorno:**
DataFrame con columnas:
- `Ranking`: Posición por número de registros independientes
- `Especie`: Nombre científico
- `Numero imagenes`: Total de imágenes capturadas
- `Registros independientes`: Eventos únicos tras filtro temporal
- `Tipo`: Categoría taxonómica (Ave, Mamífero, Otro)

**Uso:**
```r
# Modo tradicional (procesa en tiempo real)
tabla <- makeSpeciesTable(
  subset = observaciones_filtradas,
  interval = 30,
  unit = "minutes"
)

# Modo optimizado (usa estadísticas pre-calculadas)
tabla <- makeSpeciesTable(
  subset = observaciones_filtradas,
  species_stats = stats_precalculadas
)
```

**Modos de operación:**
1. **Optimizado:** Usa `species_stats` pre-calculado (rápido, recomendado)
2. **Tradicional:** Ejecuta `remove_duplicates()` en tiempo real (fallback)

---

#### `makeOccupancyGraph(subset, top_n = 15, interval = 30, unit = "minutes", occupancy_stats = NULL)`

**Descripción:** Genera gráfico de ocupación naive para especies más detectadas.

**Parámetros:**
- `subset`: DataFrame de observaciones
- `top_n`: Número de especies a visualizar (default: 15)
- `interval`: Intervalo temporal para duplicados (default: 30)
- `unit`: Unidad de tiempo (default: 'minutes')
- `occupancy_stats`: DataFrame pre-calculado (opcional)

**Retorno:**
- Objeto `ggplot` con gráfico de barras horizontales

**Uso:**
```r
grafico <- makeOccupancyGraph(
  subset = observaciones,
  top_n = 15,
  interval = 30
)
plot(grafico)
```

**Métrica calculada:**
```
Ocupación naive = (# sitios con detecciones) / (# sitios totales)
```

**Referencia:**
- MacKenzie et al. (2002) - Estimating site occupancy rates

**Características del gráfico:**
- Barras horizontales ordenadas por ocupación
- Escala de 0% a 100%
- Colores diferenciados por clase taxonómica (Aves/Mamíferos/Otros)
- Nombres científicos en cursiva
- Título dinámico según filtros aplicados

---

#### `makeMapLeaflet(subset, mapBounds)`

**Descripción:** Genera mapa interactivo con ubicación de cámaras trampa usando Leaflet.

**Parámetros:**
- `subset`: DataFrame con estadísticas de sitios que debe contener:
  - `site_name`: Nombre del sitio
  - `lat`, `lon`: Coordenadas geográficas
  - `n`: Número de imágenes
  - `ospTot`: Número de especies detectadas
  - `departamento`: Corporación ambiental regional (CAR)
- `mapBounds`: DataFrame con límites geográficos (Norte, Sur, Este, Oeste)

**Retorno:**
- Objeto `leaflet` con mapa interactivo

**Uso:**
```r
# Definir límites de Colombia
bounds <- data.frame(
  Norte = 12.5,
  Sur = -4.5,
  Este = -66.8,
  Oeste = -79.0
)

mapa <- makeMapLeaflet(
  subset = datos_sitios,
  mapBounds = bounds
)
mapa
```

**Características del mapa:**
- Capa base: OpenStreetMap
- Marcadores circulares con tamaño proporcional al número de especies
- Colores:
  - Azul: Sitios con detecciones
  - Gris: Sitios sin detecciones (NA)
- Popups con información detallada:
  - Nombre del sitio
  - Número de imágenes
  - Número de especies
  - Departamento/CAR
- Zoom automático a región de Colombia
- Controles de navegación

---

#### `makeAccumulationCurve(subset, interval = 30, unit = "minutes")`

**Descripción:** Genera curva de acumulación de especies usando el método de Ugland et al. (2003).

**Parámetros:**
- `subset`: DataFrame de observaciones con columnas:
  - `deployment_name`: Sitio de muestreo
  - `sp_binomial`: Nombre científico
  - `photo_datetime`: Timestamp
- `interval`: Intervalo para eventos independientes (default: 30)
- `unit`: Unidad de tiempo (default: 'minutes')

**Retorno:**
- Objeto `ggplot` con curva de acumulación

**Uso:**
```r
curva <- makeAccumulationCurva(
  subset = observaciones,
  interval = 30,
  unit = "minutes"
)
plot(curva)
```

**Algoritmo:**
1. Eliminar duplicados temporales (eventos independientes)
2. Crear matriz presencia/ausencia por sitio
3. Calcular especies acumuladas secuencialmente por sitio
4. Generar curva de acumulación

**Referencia:**
- Ugland et al. (2003) - The species-accumulation curve and estimation of species richness

**Características del gráfico:**
- Eje X: Número de sitios muestreados
- Eje Y: Número de especies acumuladas
- Línea azul con marcadores circulares
- Línea discontinua horizontal indicando asíntota (riqueza total)

---

#### `makeActivityPattern(subset, interval = 30, unit = "minutes")`

**Descripción:** Genera gráfico de patrón de actividad circadiano usando densidad kernel.

**Parámetros:**
- `subset`: DataFrame de observaciones con columna `photo_datetime`
- `interval`: Intervalo para eventos independientes (default: 30)
- `unit`: Unidad de tiempo (default: 'minutes')

**Retorno:**
- Objeto `plotly` interactivo con patrón circadiano

**Uso:**
```r
patron <- makeActivityPattern(
  subset = observaciones,
  interval = 30
)
patron
```

**Algoritmo:**
1. Filtrar eventos independientes
2. Extraer hora decimal del día (0.0 - 23.999)
3. Calcular densidad kernel con bandwidth automático
4. Normalizar densidad a escala 0-100%

**Características del gráfico:**
- Área rellena bajo la curva (azul degradado)
- Eje X: Hora del día (0-24h)
- Eje Y: Densidad de actividad (0-100%)
- Marcas horarias cada 3 horas
- Etiquetas de periodo:
  - 🌙 Nocturno (18:00 - 06:00)
  - ☀️ Diurno (06:00 - 18:00)
- Interactividad Plotly:
  - Zoom
  - Pan
  - Tooltips con valores exactos

---

#### `calcular_numeros_hill(subset, q = 0)`

**Descripción:** Calcula índices de diversidad efectiva (Números de Hill).

**Parámetros:**
- `subset`: DataFrame de observaciones con columnas:
  - `sp_binomial`: Nombre científico
  - `deployment_name`: Sitio
  - `photo_datetime`: Timestamp
- `q`: Orden del índice (0, 1, o 2)
  - `q = 0`: Riqueza de especies (sensible a especies raras)
  - `q = 1`: Diversidad exponencial de Shannon (especies comunes y raras)
  - `q = 2`: Diversidad inversa de Simpson (especies comunes)

**Retorno:**
- Valor numérico de diversidad efectiva
- `NA` si hay errores o datos insuficientes

**Uso:**
```r
# Riqueza de especies (Hill 0)
hill0 <- calcular_numeros_hill(observaciones, q = 0)

# Diversidad de Shannon (Hill 1)
hill1 <- calcular_numeros_hill(observaciones, q = 1)

# Diversidad de Simpson (Hill 2)
hill2 <- calcular_numeros_hill(observaciones, q = 2)
```

**Fórmulas:**

**Hill q=0 (Riqueza):**
```
⁰D = S
```
Donde S = número total de especies

**Hill q=1 (Shannon):**
```
¹D = exp(H')
H' = -Σ(pᵢ × ln(pᵢ))
```
Donde pᵢ = proporción de registros de especie i

**Hill q=2 (Simpson):**
```
²D = 1 / Σ(pᵢ²)
```

**Referencias:**
- Hill (1973) - Diversity and evenness: A unifying notation
- Jost (2006) - Entropy and diversity

**Interpretación:**
- Valores más altos = Mayor diversidad
- Hill 0 > Hill 1 > Hill 2 (siempre)
- Hill 1 y Hill 2 penalizan dominancia de pocas especies

---

#### `remove_duplicates(data, interval = 30, unit = "minutes")`

**Descripción:** Filtra eventos independientes en datos de cámaras trampa, eliminando registros duplicados del mismo taxón en el mismo sitio dentro de un intervalo temporal.

**Parámetros:**
- `data`: DataFrame con columnas:
  - `deployment_name`: Identificador del sitio/cámara
  - `photo_datetime`: Timestamp de captura
  - `sp_binomial`: Nombre científico de la especie
- `interval`: Número de unidades de tiempo (default: 30)
- `unit`: Unidad temporal ('seconds', 'minutes', 'hours', 'days', 'weeks')

**Retorno:**
- DataFrame con observaciones filtradas (solo eventos independientes)

**Uso:**
```r
# Eliminar ráfagas (mismo taxón en 30 minutos)
datos_limpios <- remove_duplicates(
  data = observaciones,
  interval = 30,
  unit = "minutes"
)

# Intervalo de 1 hora
datos_limpios <- remove_duplicates(
  data = observaciones,
  interval = 1,
  unit = "hours"
)
```

**Algoritmo:**
1. Agrupa por `deployment_name` y `sp_binomial`
2. Ordena cronológicamente por `photo_datetime`
3. Calcula diferencia temporal entre registros consecutivos
4. Conserva primer registro + registros fuera del intervalo
5. Preserva todos los registros sin identificación (NA)

**Nota:**
Registros sin identificación taxonómica (`sp_binomial = NA`) se preservan automáticamente sin aplicar filtro temporal.

---

#### `calcular_indicadores_por_periodo(tableSites, iavhdata, consolidado = FALSE)`

**Descripción:** Calcula métricas consolidadas por período de muestreo (subproject_name).

**Parámetros:**
- `tableSites`: DataFrame de estadísticas por sitio
- `iavhdata`: DataFrame de observaciones
- `consolidado`: Booleano indicando si agregar fila total (default: FALSE)

**Retorno:**
DataFrame con columnas:
- `Periodo`: Identificador del evento/período
- `Imagenes`: Total de imágenes capturadas
- `Camaras`: Número de deployments
- `Dias_camara`: Esfuerzo total en días-cámara
- `Especies`: Riqueza total de especies
- `Mamiferos`: Número de especies de mamíferos
- `Aves`: Número de especies de aves
- `Hill1`: Diversidad exponencial de Shannon
- `Hill2`: Diversidad inversa de Simpson
- `Hill3`: (Reservado para futuras métricas)

**Uso:**
```r
# Sin fila consolidada
tabla <- calcular_indicadores_por_periodo(
  tableSites = datos_sitios,
  iavhdata = observaciones,
  consolidado = FALSE
)

# Con fila consolidada total
tabla_consolidada <- calcular_indicadores_por_periodo(
  tableSites = datos_sitios,
  iavhdata = observaciones,
  consolidado = TRUE
)
```

**Características:**
- Agrupa datos por `subproject_name`
- Calcula totales por período
- Calcula Números de Hill (q=0, q=1, q=2) para cada período
- Si `consolidado = TRUE`, agrega fila "CONSOLIDADO" con totales generales
- Ordena períodos cronológicamente (descendente)

---

## Funciones Obsoletas Eliminadas

En la refactorización del 2025-12-09 se eliminaron las siguientes funciones no utilizadas:

### Funciones de carga de datos antiguas:
- `cargar_datos_evento()` → Reemplazada por `cargar_datos_consolidados()`

### Funciones de análisis no utilizadas:
- `slotDateinweek()`
- `makedonutplots()`
- `calculateEffort()`
- `makeDeploymentGuideGraph()`
- `makeMapGoogle()` → Reemplazada por `makeMapLeaflet()`
- `makeMapLeafletOld()` → Versión obsoleta
- `calcular_indice_gini_simpson()` → Integrado en `calcular_numeros_hill()`
- `calcular_entropia_shannon()` → Integrado en `calcular_numeros_hill()`

### Funciones de visualización deprecadas:
- `drawInfoBoxes()`
- `makeInfoPanel()`
- `drawSpeciesDiversityBox()`
- `makeSpeciesPanel()`
- `makeSpeciesGraph()` → Reemplazada por tabla interactiva HTML

**Backup disponible:** `functions_data_BACKUP_20251209.R` (2,239 líneas originales)

---

## Dependencias

### Librerías requeridas:

**Manipulación de datos:**
```r
require(tidyverse)
require(dplyr)
require(tidyr)
require(readr)
require(readxl)
```

**Visualización:**
```r
require(ggplot2)
require(treemapify)
require(cowplot)
require(gridExtra)
require(plotly)
```

**Manejo de fechas:**
```r
library(lubridate)
```

**Procesamiento de imágenes:**
```r
require(png)
require(magick)
```

**Mapas:**
```r
library(ggmap)
library(leaflet)
library(htmltools)
```

**Formato Parquet:**
```r
library(arrow)
```

**Fuentes (opcional):**
```r
library(extrafont)
# font_import()  # Solo ejecutar una vez
# loadfonts()
```

---

## Notas Técnicas

### Arquitectura de eventos

El sistema soporta dos modos de filtrado:

1. **Evento individual:** Filtra por `subproject_name` específico
2. **Consolidado (TODOS):** Agrega todos los eventos disponibles

### Compatibilidad de columnas

Para asegurar compatibilidad con versiones anteriores, el sistema mapea automáticamente:

```r
subproject_name → evento_muestreo
```

### Manejo de categorías Arrow

Arrow carga columnas de texto como `category` (factor). El sistema convierte automáticamente a `character` para compatibilidad con Shiny:

```r
iavhdata$subproject_name <- as.character(iavhdata$subproject_name)
```

### Intervalo de duplicados

El intervalo estándar de 30 minutos se basa en protocolos de Wildlife Insights para definir eventos independientes. Puede ajustarse según el protocolo específico del proyecto:

- **5 segundos:** Para especies de movimiento rápido
- **1 minuto:** Para análisis de comportamiento
- **30 minutos:** Estándar Wildlife Insights
- **1 hora:** Para especies de baja movilidad
- **24 horas:** Para análisis de presencia diaria

---

## Métricas Calculadas

### Estadísticas por sitio:

| Métrica | Descripción | Cálculo |
|---------|-------------|---------|
| `n` | Número de imágenes | Conteo total de registros |
| `ndepl` | Número de deployments | Siempre 1 (por diseño) |
| `effort` | Días-cámara | Extraído de `deployment_days` |
| `ospTot` | Especies totales | `n_distinct(sp_binomial)` |
| `ospMamiferos` | Especies de mamíferos | `n_distinct()` donde `class == "Mammalia"` |
| `ospAves` | Especies de aves | `n_distinct()` donde `class == "Aves"` |

### Rankings:

Todas las métricas generan rankings con `rank(-valor, ties.method = "first")`:

- `rank_images`: Por número de imágenes
- `rank_effort`: Por días-cámara
- `rank_onsp`: Por riqueza total
- `rank_onMamiferos`: Por riqueza de mamíferos
- `rank_onAves`: Por riqueza de aves

---

## Convenciones de Código

### Estilo de nomenclatura:
- Funciones: `camelCase` (ej: `makeSpeciesTable`)
- Variables: `snake_case` (ej: `datos_actuales`)
- Constantes: `UPPER_SNAKE_CASE` (ej: `MAX_FAVORITES`)

### Documentación:
- Formato: roxygen2-style
- Secciones: `@param`, `@return`, `@details`, `@examples`, `@note`, `@references`

### Comentarios:
- Delimitadores de sección: `# ===` (80 caracteres)
- Comentarios inline: Solo cuando agregan valor esencial
- Referencias bibliográficas: Incluidas cuando aplican métricas científicas

---

## Historial de Versiones

### v2.0 (2025-12-09)
- ✅ Refactorización completa con arquitectura Parquet
- ✅ Eliminación de 9 funciones obsoletas (~450 líneas)
- ✅ Documentación profesional estilo roxygen2
- ✅ Optimización de `makeSpeciesTable` con modo pre-calculado
- ✅ Optimización de `makeOccupancyGraph` con modo pre-calculado
- ✅ Integración de Números de Hill para diversidad

### v1.x (2020-2024)
- Versiones anteriores con arquitectura CSV individual
- Carga separada por evento de muestreo
- Funciones de visualización con iconos PNG

---

## Créditos

**Desarrollo original:**
- Jorge Ahumada - Conservation International (2020)

**Adaptación y mantenimiento:**
- Instituto Alexander von Humboldt (IaVH)
- Cristian C. Acevedo - Contratista Instituto Humboldt (2025)

**Financiamiento:**
- Red OTUS Colombia
- Corporaciones Autónomas Regionales (CARs)

---

## Licencia

CC0 1.0 Universal (Public Domain)

---

## Contacto

Para consultas técnicas o reporte de errores:
- Instituto Humboldt: [Sitio web oficial](http://www.humboldt.org.co)
- Red OTUS Colombia: [Portal de datos](https://biodiversidad.co)

---

**Última actualización:** 2025-12-09
