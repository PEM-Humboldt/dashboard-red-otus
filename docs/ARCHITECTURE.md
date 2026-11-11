# Arquitectura del Dashboard Red OTUS 2026

## 1. Propósito

La arquitectura 2026 separa el procesamiento de los datos y su visualización. Esta separación permite validar una publicación antes de exponerla, reducir las operaciones ejecutadas por R y mantener tiempos de respuesta más estables cuando aumenta el volumen de información.

La solución está formada por:

- Un pipeline en Python para lectura, control de calidad, normalización, cálculo y publicación.
- Una interfaz gráfica PySide6 para usuarios que no necesitan operar comandos.
- Un modelo de datos Parquet organizado en datos validados y resultados precalculados.
- Un dashboard unificado en R Shiny con vistas por proyecto y corporación.
- Pruebas automáticas del pipeline y verificaciones de integridad de la publicación.

## 2. Organización del proyecto

```text
dashboard-red-otus/
├── README.md
├── LICENSE
├── docs/
│   ├── ARCHITECTURE.md
│   ├── PROCESSING_WORKFLOW.md
│   ├── DATA_DICTIONARY.md
│   └── OPERATION_MANUAL.md
├── processing/
│   ├── input/
│   │   ├── favorites_originals/
│   │   ├── raw/
│   │   └── spatial/
│   ├── red_otus_pipeline/
│   │   ├── resources/
│   │   ├── cli.py
│   │   ├── config.py
│   │   ├── engine.py
│   │   ├── gallery.py
│   │   ├── gui.py
│   │   ├── input_inspection.py
│   │   ├── packaging.py
│   │   ├── deployment.py
│   │   ├── quality.py
│   │   ├── reports.py
│   │   └── validation.py
│   ├── tests/
│   ├── run_gui.py
│   ├── run_cli.py
│   ├── pyproject.toml
│   ├── requirements.lock.txt
│   └── validate_release.py
├── processing_reports/
│   ├── quality_report.html
│   ├── quality_report.json
│   ├── quality_issues.parquet
│   ├── quality_issues.csv
│   ├── gallery_optimization.json
│   ├── gallery_optimization.csv
│   └── project_summary.csv
└── dashboard/
    ├── app.R
    ├── dashboard_functions.R
    ├── dashboard_red_otus_2026.Rproj
    ├── renv.lock
    ├── data/
    │   ├── validated_data/
    │   └── dashboard_outputs/
    ├── spatial/
    └── www/
```

## 3. Flujo general

```text
Wildlife Insights
       │
       ▼
CSV y límites geográficos
       │
       ▼
Validación y parametrización en la GUI
       │
       ▼
Normalización y control de calidad
       │
       ├──► Datos validados
       ├──► Productos precalculados
       ├──► Informes locales en processing_reports/
       └──► Publicación aprobada en dashboard/data/
                    │
                    ▼
             Dashboard R Shiny
```

Cuando la publicación local ha sido revisada, la GUI construye un paquete de
actualización con manifiesto y huellas SHA-256. El cliente de despliegue lo
transfiere por SSH al servidor autorizado, donde un actualizador institucional
valida, activa y conserva la release anterior para recuperación. Los scripts y
la configuración particulares del servidor se mantienen fuera del repositorio
público.

## 4. Capas de información

### 4.1 Entrada

Contiene los CSV descargados de Wildlife Insights y el shapefile usado para asociar instalaciones de cámaras con corporaciones. Los archivos de entrada se conservan sin modificaciones para mantener trazabilidad.

### 4.2 Datos validados

Los archivos de `dashboard/data/validated_data/` forman el modelo analítico base:

- Una tabla de hechos con observaciones.
- Dimensiones de proyecto, evento, instalación y taxonomía.
- Una relación entre instalaciones y corporaciones.

Esta capa conserva el detalle necesario para auditoría y consultas controladas.
Los conteos de cada actualización se registran en `manifest.json`; no son una
restricción del modelo ni se fijan en la documentación.

### 4.3 Resultados del dashboard

Los archivos de `dashboard/data/dashboard_outputs/` contienen resultados precalculados para:

- Catálogo de filtros.
- Indicadores operativos y de biodiversidad.
- Ranking y métricas por especie.
- Patrones horarios de actividad.
- Información de cámaras para el mapa.

El dashboard evita reconstruir estos cálculos en cada interacción.

### 4.4 Control de publicación

El manifiesto ubicado en `dashboard/data/` registra:

- Versión del pipeline y de la estructura de datos.
- Parámetros de la ejecución.
- Archivos fuente y huellas SHA-256.
- Conteos de entrada y salida.
- Métricas de tiempo, CPU y memoria.
- Resumen de situaciones de calidad y decisiones aplicadas.

Los reportes detallados y el resumen operativo se publican por separado en
`processing_reports/`. Esta separación evita incorporarlos al despliegue del
dashboard y mantiene la trazabilidad disponible para la GUI y la revisión local.

## 5. Componentes de procesamiento

| Módulo | Responsabilidad |
|---|---|
| `config.py` | Define parámetros y valida combinaciones permitidas. |
| `input_inspection.py` | Revisa archivos mínimos y construye el catálogo de proyectos. |
| `engine.py` | Ejecuta transformación, cálculos y publicación. |
| `quality.py` | Clasifica y registra situaciones de calidad. |
| `reports.py` | Genera resúmenes y el reporte HTML. |
| `validation.py` | Comprueba integridad, relaciones, rangos y cobertura. |
| `gui.py` | Presenta el flujo operativo mediante PySide6. |
| `cli.py` | Permite la ejecución no interactiva por comandos. |
| `packaging.py` | Valida y empaqueta una publicación aprobada. |
| `deployment.py` | Transfiere y activa paquetes mediante un cliente SSH restringido. |

## 6. Componentes del dashboard

- `app.R` define la interfaz, filtros, reactividad, descargas y composición visual.
- `dashboard_functions.R` reúne validación de insumos, preparación de tablas, mapas y gráficas.
- `data/` contiene exclusivamente la publicación requerida por la aplicación.
- `spatial/` contiene los límites empleados en el mapa.
- `www/` almacena estilos, fuentes, logos, galería y recursos del navegador.

La aplicación ofrece una misma distribución para proyectos y corporaciones, cambiando únicamente el nivel de agrupación seleccionado.

## 7. Decisiones de diseño

### Preprocesamiento

Los productos analíticos se calculan en Python para evitar repetir operaciones costosas en cada sesión R.

### Formato Parquet

Parquet reduce espacio, conserva tipos y permite leer columnas específicas. Esto disminuye memoria y tiempo de lectura frente a archivos planos equivalentes.

### Publicación transaccional

La ejecución se construye primero en un directorio temporal. Solo después de validar contratos y productos se reemplaza la publicación anterior. Si el proceso falla o se cancela, los datos vigentes permanecen disponibles.

La activación sigue esta secuencia:

1. Python crea directorios `staging` separados para datos e informes.
2. Escribe los productos y calcula tamaño y SHA-256.
3. Valida archivos, columnas, claves, rangos y cobertura analítica.
4. Renombra temporalmente la publicación vigente como respaldo.
5. Activa los nuevos directorios mediante una operación de reemplazo.
6. Si falla cualquiera de los dos reemplazos, restaura ambos respaldos.
7. Elimina los directorios temporales y el respaldo cuando la activación concluye.

El dashboard solo acepta un manifiesto con estado `approved`. Esta combinación
evita que una ejecución parcial quede visible y permite que la publicación
anterior continúe funcionando durante casi todo el procesamiento.

### Trazabilidad

Las observaciones conservan `source_file` y `source_row`. El manifiesto incorpora huellas de archivos para detectar cambios o daños posteriores.

### Calidad orientada al usuario

Las situaciones se presentan como exclusión por inconsistencia, exclusión por
criterios de análisis, procesamiento con limitación, resolución automática o
configuración aplicada. El detalle técnico permanece disponible sin saturar la
interfaz principal.

## 8. Límites de despliegue

El pipeline se ejecuta en un entorno local autorizado y publica los datos de la
aplicación en `dashboard/data/`; los informes permanecen en
`processing_reports/`. El despliegue del dashboard debe incluir:

- `app.R`
- `dashboard_functions.R`
- `.Rprofile`
- `renv.lock`
- `data/`
- `spatial/`
- `www/`

La carpeta `processing/` no es necesaria para ejecutar una publicación ya
generada en Posit Connect o Shiny Server, pero sí para producir futuras
actualizaciones. La carpeta `processing_reports/` tampoco debe incluirse en el
despliegue.

La configuración particular de la infraestructura institucional -Docker,
Shiny Server, Nginx, DNS, HTTPS, usuarios y automatizaciones de actualización-
se administra como documentación y configuración operativa interna. No forma
parte del código público porque depende del servidor autorizado y puede contener
información sensible.

## 9. Distribución del trabajo entre Python y R

Python ejecuta la lectura masiva, normalización temporal y taxonómica,
asociación con instalaciones, asignación de corporación, intervalos de
independencia, números de Hill, ocupación, frecuencia, diurnalidad, actividad
horaria, rankings, control de calidad y publicación. Estos resultados se
materializan por alcance global, proyecto y corporación, por evento y por
intervalo.

R valida el manifiesto, lee únicamente las columnas necesarias, aplica los
filtros seleccionados y compone la presentación. La aplicación genera las
tablas, gráficas, mapa, galería, archivos CSV y libro Excel a partir de los
productos publicados. El mapa y la galería utilizan recursos locales de
`spatial/` y `www/images/favorites/`.

La galería resuelve las fotografías en tiempo de ejecución. Las vistas
globales leen `www/images/favorites/General/`, las vistas de proyecto leen la
carpeta cuyo nombre coincide con el `project_id` y las vistas de corporación
combinan las carpetas de sus proyectos. Esta convención permite incorporar
proyectos nuevos sin modificar el código. Cuando no existe contenido para el
alcance aplicado, la interfaz informa la ruta que el operador debe preparar.
Al iniciar la aplicación, un inventario se escribe en la consola de R: resume
los proyectos con y sin fotografías y cuenta los archivos disponibles en cada
carpeta. Este diagnóstico no interrumpe ni ocupa espacio en la interfaz web.

Los originales seleccionados se conservan fuera del paquete desplegable, en
`processing/input/favorites_originals/`. El módulo `gallery.py` crea las copias
web optimizadas y mantiene una huella de los originales para evitar
recompresiones sucesivas. El dashboard continúa leyendo únicamente
`www/images/favorites/`, por lo que esta preparación no añade trabajo al
servidor R durante la navegación.

## 10. Versionamiento, responsabilidades y licencia

- Versión funcional: `v2026.1.0`.
- Versión de la estructura de datos: `2.2.0`.
- Versión del paquete Python: `2026.1.0`, sin el prefijo visual `v` por la convención PEP 440.
- Desarrollo: Cristian C. Acevedo, Ingeniero de Soluciones.
- Supervisión: Angélica Diaz Pulido, Investigador Adjunto, Centro Estudios Socioecológicos y Cambio Global, Dirección de Conocimiento, Instituto Humboldt.
- Licencia del código: MIT.

## 11. Reproducibilidad de entornos

Python utiliza dos niveles complementarios:

- `pyproject.toml` declara compatibilidad mínima y metadatos del paquete.
- `processing/requirements.lock.txt` fija las versiones exactas validadas para `v2026.1.0`.

R utiliza `renv`:

- `dashboard/renv.lock` registra R 4.5.2 y todas las dependencias transitivas.
- `dashboard/.Rprofile` activa automáticamente el entorno del proyecto.
- `dashboard/renv/activate.R` habilita la restauración sin versionar la biblioteca instalada.
- `slickR` está fijado a un commit inmutable de su repositorio oficial porque ya no se encuentra disponible en el índice principal de CRAN.

Las bibliotecas locales se excluyen de Git. Cada equipo debe reconstruirlas desde los archivos de bloqueo.

## 12. Separación entre código público y datos privados

El repositorio público conserva únicamente código, documentación y configuración. Se excluyen los CSV de Wildlife Insights, publicaciones Parquet, reportes derivados, límites espaciales y fotografías. Estos recursos deben mantenerse en almacenamiento institucional con acceso limitado.
