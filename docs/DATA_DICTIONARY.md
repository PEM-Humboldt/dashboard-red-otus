# Diccionario de datos de la publicación 2026

## 1. Convenciones

- Los archivos analíticos se almacenan en Parquet.
- Los identificadores se manejan como texto para evitar pérdidas de ceros o conversiones.
- Las proporciones se guardan entre 0 y 1. El dashboard las presenta como porcentajes.
- Las fechas normalizadas usan tipos temporales; `timestamp_original` conserva el valor recibido.
- `source_file` y `source_row` permiten regresar al registro de origen.
- `ALL` identifica una selección consolidada.
- `interval_minutes = 0` representa datos sin filtro de independencia.

## 2. Inventario lógico de la publicación

| Capa | Archivo | Granularidad | Función principal |
|---|---|---|---|
| Validada | `fact_observation.parquet` | Una observación publicada | Observaciones y trazabilidad. |
| Validada | `dim_project.parquet` | Un proyecto | Proyectos e iniciativa. |
| Validada | `dim_event.parquet` | Un proyecto y evento | Eventos disponibles por proyecto. |
| Validada | `dim_deployment.parquet` | Un periodo de instalación | Instalaciones y esfuerzo. |
| Validada | `dim_taxon.parquet` | Un taxón utilizable | Clasificación taxonómica. |
| Validada | `bridge_deployment_corporation.parquet` | Una relación instalación-corporación | Asignación territorial. |
| Dashboard | `filter_catalog.parquet` | Una combinación de filtros | Opciones válidas de consulta. |
| Dashboard | `indicator_summary.parquet` | Un alcance, evento e intervalo | Indicadores resumidos. |
| Dashboard | `species_metrics.parquet` | Una especie, alcance, evento e intervalo | Ranking y métricas por especie. |
| Dashboard | `activity_hour.parquet` | Una especie, hora, alcance, evento e intervalo | Actividad horaria. |
| Dashboard | `map_deployment.parquet` | Una instalación | Cámaras y atributos del mapa. |

Los conteos de filas pertenecen a cada ejecución y se consultan en
`manifest.json`. Esta separación mantiene vigente el diccionario cuando se
actualizan los insumos.

## 3. Datos validados

### 3.1 dim_project.parquet

Una fila por proyecto.

| Campo | Descripción |
|---|---|
| `project_id` | Identificador del proyecto en Wildlife Insights. |
| `project_short_name` | Nombre corto usado en filtros y mapa. |
| `project_name` | Nombre completo del proyecto. |
| `project_admin` | Persona administradora. |
| `project_admin_email` | Correo de contacto. |
| `project_admin_organization` | Organización administradora. |
| `initiative_id` | Identificador de la iniciativa. |
| `initiative_name` | Nombre de la iniciativa. |
| `Corporacion` | Corporación asignada al proyecto. |

### 3.2 dim_event.parquet

Una fila por combinación de proyecto y evento.

| Campo | Descripción |
|---|---|
| `project_id` | Proyecto asociado. |
| `event_id` | Código normalizado del evento. |
| `event_year` | Año interpretado desde el código. |

### 3.3 dim_deployment.parquet

Una fila por periodo de instalación de una cámara.

| Grupo | Campos principales | Descripción |
|---|---|---|
| Identificación | `project_id`, `deployment_id`, `deployment_key` | Claves del proyecto y la instalación. |
| Evento | `subproject_name` | Evento de muestreo asociado. |
| Ubicación | `placename`, `longitude`, `latitude`, `Corporacion` | Información espacial. |
| Periodo declarado | `start_date`, `end_date` | Fechas recibidas en el archivo fuente. |
| Periodo observado | `observed_min_date`, `observed_max_date` | Extremos encontrados en observaciones. |
| Periodo efectivo | `effective_start_date`, `effective_end_date`, `deployment_days` | Periodo utilizado en cálculos. |
| Cámara | `camera_id`, `camera_name`, `camera_functioning` | Información del equipo. |
| Trazabilidad | `source_file`, `source_row` | Ubicación en el archivo de origen. |

También conserva `bait_type`, `bait_description`, `feature_type`,
`feature_type_methodology`, `sensor_height`, `height_other`,
`sensor_orientation`, `orientation_other`, `plot_treatment`,
`plot_treatment_description`, `detection_distance`, `recorded_by`, `remarks` y
los metadatos disponibles de cámara y evento.

### 3.4 dim_taxon.parquet

Una fila por taxón utilizable.

| Campo | Descripción |
|---|---|
| `sp_binomial` | Nombre científico utilizado como clave analítica. |
| `wi_taxon_id` | Identificador taxonómico de Wildlife Insights. |
| `class` | Clase. |
| `order` | Orden. |
| `family` | Familia. |
| `genus` | Género. |
| `species` | Epíteto específico. |
| `common_name` | Nombre común disponible. |

### 3.5 fact_observation.parquet

Una fila por observación publicada.

| Grupo | Campos principales | Descripción |
|---|---|---|
| Imagen | `image_id`, `filename`, `location` | Identificación del archivo observado. |
| Contexto | `project_id`, `deployment_id`, `deployment_key`, `subproject_name` | Proyecto, instalación y evento. |
| Tiempo | `timestamp`, `timestamp_original`, `photo_datetime` | Valores original y normalizado. |
| Detección | `is_blank`, `number_of_objects`, `age`, `sex`, `behavior` | Características registradas. |
| Taxonomía | `sp_binomial`, `wi_taxon_id`, `class`, `order`, `family`, `genus`, `species` | Identificación biológica. |
| Ubicación | `placename`, `longitude`, `latitude`, `Corporacion` | Contexto espacial. |
| Proyecto | `project_short_name`, `project_name`, `project_admin`, `project_admin_email` | Metadatos para visualización. |
| Trazabilidad | `source_file`, `source_row` | Archivo y fila de origen. |

Además conserva los campos de Wildlife Insights disponibles para la detección:
`is_blank`, `identified_by`, `uncertainty`, `number_of_objects`, `age`, `sex`,
`animal_recognizable`, `individual_id`, `individual_animal_notes`, `behavior`,
`highlighted`, `markings`, `cv_confidence`, `license`, `bounding_boxes` y
`sequence_id`. Los campos de texto se almacenan como cadenas; `photo_datetime`
usa un tipo temporal y `source_row` un entero.

### 3.6 bridge_deployment_corporation.parquet

Relación entre instalaciones y corporaciones.

| Campo | Descripción |
|---|---|
| `project_id` | Proyecto de la instalación. |
| `deployment_id` | Identificador de la instalación. |
| `Corporacion` | Corporación resultante de la asignación espacial o manual. |

## 4. Resultados del dashboard

### 4.1 filter_catalog.parquet

Define combinaciones válidas de filtros.

| Campo | Descripción |
|---|---|
| `scope_type` | `global`, `project` o `corporation`. |
| `scope_id` | Identificador de la entidad o `ALL`. |
| `event_id` | Evento disponible o `ALL`. |

### 4.2 indicator_summary.parquet

Una fila por alcance, evento e intervalo de independencia.

| Campo | Descripción |
|---|---|
| `event_id` | Evento o consolidado. |
| `images` | Observaciones incluidas. |
| `independent_records` | Registros independientes conservados para el intervalo. |
| `cameras` | Instalaciones consideradas. |
| `camera_days` | Suma de días efectivos de instalación. |
| `species` | Riqueza de especies. |
| `mammals` | Riqueza de mamíferos. |
| `birds` | Riqueza de aves. |
| `hill1`, `hill2`, `hill3` | Números de Hill publicados por la solución. |
| `scope_type`, `scope_id` | Alcance del resumen. |
| `interval_minutes` | Intervalo aplicado: 0, 30, 60 o 1440 minutos. |

### 4.3 species_metrics.parquet

Una fila por especie, alcance, selección, evento e intervalo.

| Grupo | Campos |
|---|---|
| Ranking | `ranking`, `image_count`, `independent_count` |
| Taxonomía | `sp_binomial`, `class`, `order`, `family`, `genus`, `species`, `common_name` |
| Ocupación | `occupancy`, `detected_deployments`, `eligible_deployments` |
| Frecuencia | `frequency`, `detected_occasions`, `total_occasions` |
| Diurnalidad | `diurnality`, `day_independent_records`, `independent_records_24h` |
| Selección | `metric_event`, `selection_event`, `scope_type`, `scope_id`, `interval_minutes` |

### 4.4 activity_hour.parquet

Distribución horaria de registros independientes.

| Campo | Descripción |
|---|---|
| `sp_binomial` | Especie. |
| `subproject_name` | Evento de origen. |
| `hour` | Hora entre 0 y 23. |
| `count` | Registros independientes en la hora. |
| `ranking` | Posición de la especie. |
| `selection_event` | Evento solicitado o consolidado. |
| `scope_type`, `scope_id` | Alcance. |
| `interval_minutes` | Intervalo aplicado. |

### 4.5 map_deployment.parquet

Una fila por instalación mostrada en el mapa.

Incluye `project_id`, `deployment_id`, `deployment_key`, `subproject_name`,
`placename`, `latitude`, `longitude`, `Corporacion`, `deployment_days`, `images`,
`species`, `mammals`, `birds`, `project_short_name`, `project_admin` y
`project_admin_email`.

## 5. Definición de métricas

### Registros independientes

Dentro de cada proyecto, evento, instalación y especie, se ordenan los registros por fecha. Se conserva el primero y los siguientes cuya separación frente al último conservado sea igual o superior al intervalo seleccionado.

### Ocupación

```text
instalaciones con detección de la especie / instalaciones elegibles
```

### Frecuencia

Cada periodo de instalación se divide en ocasiones consecutivas de siete días (una semana). La última ocasión se conserva aunque tenga menos de siete días.

```text
ocasiones con al menos una detección / ocasiones disponibles
```

### Diurnalidad

Para cada día se calcula la proporción de registros independientes entre las 06:00 y las 18:00. El valor publicado corresponde al promedio de esas proporciones diarias.

### Actividad

Los registros independientes se agrupan por hora del día, especie, evento, alcance e intervalo.

### Números de Hill

Se calculan a partir de la abundancia relativa de las especies. Los resultados permiten representar riqueza y diversidad efectiva con distinta sensibilidad a las especies dominantes.

## 6. Calidad y control

Los productos de detalle se almacenan en `processing_reports/`. Son insumos de
revisión local y no son necesarios para ejecutar o desplegar el dashboard. El
manifiesto, en cambio, se conserva en `dashboard/data/` porque la aplicación lo
valida antes de leer los Parquet.

### quality_issues.parquet y quality_issues.csv

| Campo | Descripción |
|---|---|
| `stage` | Etapa en la que se identificó la situación. |
| `severity` | Nivel técnico: error, warning o info. |
| `rule` | Código estable de la regla. |
| `entity_type`, `entity_id` | Registro o entidad afectada. |
| `field`, `original_value` | Campo y valor recibido. |
| `action` | Tratamiento aplicado. |
| `source_file`, `source_row` | Ubicación del dato fuente. |

`quality_issues.parquet` conserva el detalle técnico completo. El CSV presenta
el mismo conjunto de hallazgos con nombres y explicaciones orientadas al
usuario: estado, situación, descripción, resultado, recomendación, archivo,
fila, identificador, campo, valor original y acción técnica. Utiliza separador
punto y coma y codificación UTF-8 con BOM para facilitar su apertura en Excel.

### manifest.json

El manifiesto registra versión, ejecución, periodo, intervalos, la ventana de
ocasiones (`occasion_window_days = 7`), conteos, calidad, rendimiento, fuentes
y productos. Cada dataset incluye tamaño y SHA-256.

### project_summary.csv

Presenta una revisión rápida de identificador, nombre, corporación, cámaras, eventos y observaciones por proyecto.

### quality_report.json y quality_report.html

El JSON alimenta las pestañas de la GUI e incluye conteos por regla, estado,
descripción, resultado, recomendación y ejemplos. El HTML presenta el mismo
contenido en un reporte navegable, con una muestra estratificada de hasta 1.000
filas, filtro combinado de estado y situación, búsqueda de texto y comparación
entre las filas visibles y el total disponible en el detalle completo.

## 7. Reglas de consumo

El dashboard solo debe usar una publicación cuyo manifiesto tenga estado
`approved`. Los nombres y tipos de los campos pertenecen a la estructura de
datos versionada `2.2.0`; cualquier cambio requiere actualizar conjuntamente el
pipeline, el dashboard, las pruebas y la documentación.
