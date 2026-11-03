# Flujo de procesamiento de datos

## 1. Objetivo

El pipeline transforma exportaciones de Wildlife Insights en una publicación validada y optimizada para el Dashboard Red OTUS 2026. El usuario puede operarlo mediante la interfaz gráfica o por línea de comandos.

## 2. Insumos

### Archivos CSV

La carpeta `processing/input/raw/` debe contener, como mínimo:

- `projects.csv`
- `deployments.csv`
- Uno o más archivos `images_<project_id>.csv`

Los archivos adicionales de una descarga, como cámaras o secuencias, pueden conservarse en la carpeta aunque no todos intervengan directamente en los productos actuales.

### Información espacial

`processing/input/spatial/` debe contener los componentes del shapefile:

- `CAR_MPIO.shp`
- `CAR_MPIO.dbf`
- `CAR_MPIO.shx`
- `CAR_MPIO.prj`
- `CAR_MPIO.cpg`

### Fotografías originales de la galería

`processing/input/favorites_originals/` conserva las fotografías seleccionadas
por el usuario en máxima resolución. `General/` corresponde a las vistas
consolidadas y cada carpeta `<project_id>/` corresponde a un proyecto. Se
admiten JPG, JPEG y PNG.

## 3. Operación mediante la GUI

### 3.1 Validación de carpetas

La primera sección confirma:

- Existencia de archivos requeridos.
- Proyectos presentes en los CSV.
- Disponibilidad del archivo espacial.
- Corporación inferida para cada proyecto cuando existe información suficiente.

El procesamiento no se habilita hasta completar esta validación.

### 3.2 Parametrización

El usuario define:

- Nombre de la iniciativa almacenado como metadato de procedencia en los datos.
- Texto visible que acompaña el título principal del dashboard.
- Fecha inicial y fecha final.
- Uno o varios intervalos de independencia.
- Todos los proyectos o una selección.
- Reasignaciones manuales de corporación cuando existe una corrección conocida.

Los selectores de proyecto y corporación de la reasignación manual permiten
buscar escribiendo cualquier fragmento del identificador, nombre o sigla.

La zona horaria operativa es `America/Bogota`.

### 3.3 Intervalos de independencia

Se admiten cuatro opciones:

| Valor | Interpretación |
|---:|---|
| 0 minutos | Conserva todos los registros válidos. |
| 30 minutos | Conserva registros separados por al menos 30 minutos. |
| 60 minutos | Conserva registros separados por al menos una hora. |
| 1440 minutos | Conserva registros separados por al menos 24 horas. |

La comparación se realiza por proyecto, evento, instalación y especie, tomando como referencia el último registro conservado.

### 3.4 Optimización de la galería

La opción **Optimizar y publicar imágenes** funciona de manera independiente
al procesamiento analítico. Corrige la orientación EXIF, reduce el lado mayor
a 1.600 píxeles sin ampliar fotografías pequeñas, guarda JPEG progresivo con
calidad 82 % y conserva PNG únicamente cuando requiere transparencia. Las
copias se preparan en una carpeta temporal. Al terminar sin errores, la carpeta
completa `dashboard/www/images/favorites/` se reemplaza de manera atómica. La
fuente es autoritativa: archivos eliminados de los originales no permanecen en
la publicación siguiente.

Un manifiesto privado dentro de la carpeta publicada conserva la huella SHA-256
de cada original y evita recomprimir archivos sin cambios. La operación produce
`gallery_optimization.json` y `gallery_optimization.csv` en
`processing_reports/` con pesos, dimensiones, reducción y errores.

La cancelación cooperativa o cualquier imagen defectuosa impide activar la
nueva carpeta y conserva íntegra la galería publicada anteriormente.

## 4. Etapas internas

### 4.1 Lectura

El pipeline lee proyectos, instalaciones y archivos de imágenes. Cada registro recibe información de archivo y fila de origen.

### 4.2 Normalización

Se estandarizan identificadores, textos, coordenadas, fechas, eventos y campos taxonómicos. Las fechas se interpretan con la zona horaria configurada.

### 4.3 Selección temporal

Solo se publican observaciones dentro del periodo indicado por el usuario. Los
registros fuera del rango quedan documentados como exclusiones por criterios de
análisis.

### 4.4 Asociación con instalaciones

Cada observación se relaciona con una instalación compatible. El control
distingue entre una combinación de proyecto y cámara inexistente en
`deployments.csv` y una instalación existente cuyo campo `subproject_name` está
vacío. Cuando existen periodos superpuestos, el pipeline aplica una decisión
conservadora basada en fechas y registra la situación.

### 4.5 Asignación de corporación

Las coordenadas de las instalaciones se cruzan con los polígonos de corporaciones. Las reasignaciones manuales autorizadas tienen prioridad y quedan registradas.

### 4.6 Validación taxonómica

Los registros sin género y especie utilizables se conservan en el reporte de
calidad con su archivo y fila de origen. No se incorporan a
`fact_observation.parquet` ni a los indicadores, rankings o gráficas de
biodiversidad.

### 4.7 Construcción de datos validados

Se generan seis archivos en `validated_data/`:

- `fact_observation.parquet`
- `dim_project.parquet`
- `dim_event.parquet`
- `dim_deployment.parquet`
- `dim_taxon.parquet`
- `bridge_deployment_corporation.parquet`

### 4.8 Cálculo de resultados

Se generan cinco archivos en `dashboard_outputs/`:

- `filter_catalog.parquet`
- `indicator_summary.parquet`
- `species_metrics.parquet`
- `activity_hour.parquet`
- `map_deployment.parquet`

Los resultados se calculan para alcance global, proyectos, corporaciones, eventos e intervalos solicitados. `indicator_summary.parquet` conserva el total de observaciones, agrega el total de registros independientes y publica los números de Hill calculados para cada intervalo.

### 4.9 Control de calidad

Cada situación contiene etapa, nivel, regla, entidad, valor original, acción, archivo y fila. La interfaz resume los casos y el reporte HTML permite filtrarlos.

Las reglas vigentes cubren identificadores duplicados, coordenadas inválidas,
fechas no interpretables o fuera del periodo, instalaciones ambiguas o sin
correspondencia, códigos de evento inválidos, diferencias entre el año de la
captura y el evento, taxonomía incompleta, periodos de instalación invertidos o
fuera del rango y reasignaciones manuales de corporación. Cada regla informa si
el dato fue excluido por una inconsistencia o por un criterio de análisis, se
procesó con limitaciones, se resolvió automáticamente o corresponde a una
configuración aplicada por el usuario.

### 4.10 Validación y publicación

Antes de activar la salida se comprueban:

- Presencia de todos los archivos.
- Unicidad de claves de instalaciones.
- Integridad entre observaciones e instalaciones.
- Intervalos solicitados.
- Métricas dentro del rango de 0 a 1.
- Existencia de resultados para alcances representativos.
- Tamaño y SHA-256 de cada Parquet.

La publicación nueva reemplaza la anterior únicamente si supera estas comprobaciones.

### 4.11 Activación sin interrupción crítica

Los datos y los informes se escriben en directorios temporales independientes.
La publicación vigente se mantiene intacta durante lectura, limpieza, cálculo y
validación. El cambio de versión ocurre al final mediante reemplazos de
directorios; si uno falla, el pipeline restaura el respaldo anterior. La
cancelación solicitada desde la GUI también ocurre antes de exponer productos
incompletos.

## 5. Archivos de control

El manifiesto requerido por el dashboard permanece en `dashboard/data/`. Los
demás archivos de control se guardan en `processing_reports/` y no forman parte
del paquete desplegado con la aplicación.

| Archivo | Finalidad |
|---|---|
| `manifest.json` | Identifica ejecución, parámetros, conteos, rendimiento y huellas. |
| `quality_report.html` | Presenta el reporte completo en navegador. |
| `quality_report.json` | Alimenta el resumen de la GUI. |
| `quality_issues.parquet` | Conserva detalle estructurado de calidad. |
| `quality_issues.csv` | Facilita revisión fuera de herramientas analíticas. |
| `project_summary.csv` | Resume proyectos, corporaciones, cámaras, eventos y observaciones. |
| `gallery_optimization.json` | Resume la optimización y la reducción de peso de la galería. |
| `gallery_optimization.csv` | Detalla el resultado de cada fotografía procesada. |

`dashboard/data/` contiene únicamente `manifest.json`, seis Parquet de datos
validados y cinco Parquet para la vista. Esta separación evita que los reportes
de revisión, en especial el CSV detallado de calidad, aumenten innecesariamente
el paquete enviado al servicio de visualización.

## 6. Ejecución

### Interfaz gráfica

```text
processing/launch_gui.bat
```

### Línea de comandos

Ejecutado desde la raíz:

```powershell
python processing/run_cli.py \
  --raw processing/input/raw \
  --output dashboard/data \
  --reports processing_reports \
  --shapefile processing/input/spatial/CAR_MPIO.shp \
  --initiative "Red OTUS" \
  --dashboard-title "Red OTUS" \
  --start-date 2020-01-01 \
  --cutoff 2026-09-30 \
  --intervals 0 30 60 1440
```

### Validación independiente

```powershell
python processing/validate_release.py --output dashboard/data
```

## 7. Cancelación y recuperación

El botón de detener solicita una cancelación cooperativa. El pipeline elimina el directorio temporal cuando es posible. Si Windows mantiene un archivo abierto, la operación reintenta antes de reportar el bloqueo. La publicación anterior no se elimina hasta confirmar la nueva.

## 8. Recomendaciones

- Procese siempre una descarga completa y coherente.
- Cierre exploradores o programas que estén usando `dashboard/data/` o `processing_reports/`.
- Revise el reporte de calidad antes de desplegar.
- Corrija en Wildlife Insights los problemas de origen cuando sea posible.
- Archive externamente manifiesto y reportes si necesita conservar historial.

## 9. Entorno reproducible de Python

`processing/requirements.lock.txt` contiene las versiones exactas probadas con Python 3.13.11. Para reconstruir el entorno:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r processing/requirements.lock.txt
python -m pip install -e processing --no-deps
python -m pip check
```

`pyproject.toml` se mantiene como declaración de compatibilidad. El archivo de bloqueo es la referencia operativa para reproducir `v2026.1.0`.

## 10. Evidencia de cada actualización

Los resultados operativos no se fijan en este documento porque cambian con los
insumos. Para cada ejecución conserve, en un espacio institucional autorizado:

- El `run_id` y el estado `approved` de `manifest.json`.
- Los conteos de entrada, publicación y exclusión.
- Los intervalos, periodo, duración, CPU y memoria registrados.
- El resultado de `validate_release.py`.
- El reporte de calidad y, cuando corresponda, el reporte de galería.

Las pruebas automatizadas cubren la regla acumulativa de independencia, el
intervalo sin filtro, los números de Hill, la cancelación cooperativa, los
reintentos ante bloqueos de Windows, el reporte de calidad y la publicación
atómica.
