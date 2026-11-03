# Manual de operación

## 1. Público y alcance

Este manual está dirigido a las personas responsables de actualizar los datos, revisar su calidad y publicar el Dashboard Red OTUS 2026. No se requiere experiencia avanzada en programación para utilizar la interfaz gráfica.

## 2. Requisitos

### Sistema

- Windows 10 o posterior.
- Espacio suficiente para los CSV, los archivos temporales y la publicación.
- Permisos de lectura y escritura sobre el proyecto.

### Python

- Python 3.11, 3.12 o 3.13. La versión validada para este release es Python 3.13.11.
- Dependencias declaradas en `processing/pyproject.toml`.

Instalación recomendada:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r processing/requirements.lock.txt
python -m pip install -e processing --no-deps
python -m pip check
```

### R

R 4.5.2 y los paquetes:

```text
arrow, dplyr, DT, ggplot2, htmltools, jsonlite, leaflet, lubridate,
openxlsx, plotly, scales, sf, shiny, shinydashboard, shinyjs, slickR, tzdb, zip
```

La publicación `v2026.1.0` fue validada con R 4.5.2. Para restaurar exactamente el entorno:

```powershell
Rscript -e "renv::restore(project='dashboard', prompt=FALSE)"
```

No ejecute `renv::snapshot()` durante la operación normal. Este comando modifica el bloqueo y debe reservarse para una actualización técnica planificada.

## 3. Preparación de insumos

### Renovación completa de los CSV

1. Cierre la GUI si se encuentra abierta.
2. Elimine los CSV de la actualización anterior en
   `processing/input/raw/`. Conserve `.gitkeep` si el Explorador de Windows lo
   muestra; este archivo solo mantiene la carpeta en Git y no es un insumo.
3. Solicite desde Wildlife Insights la descarga completa de la iniciativa. La
   plataforma entregará un archivo comprimido ZIP.
4. Descargue el ZIP en una ubicación temporal del equipo y descomprímalo. No
   copie el ZIP a la carpeta de entrada y no intente procesarlo directamente.
5. Copie en `processing/input/raw/` todos los CSV de la descarga descomprimida.
   La carpeta no debe mezclar archivos de descargas anteriores con la nueva.
6. Confirme que existan `projects.csv`, `deployments.csv` y al menos un archivo
   `images_<project_id>.csv`. El procesador también admite `cameras.csv` y
   `sequences.csv` cuando Wildlife Insights los incluye.
7. No modifique manualmente nombres, encabezados, separadores o codificación de
   los CSV. Si un archivo debe corregirse, realice el ajuste en Wildlife
   Insights y genere una nueva descarga.

Antes de abrir la GUI, cierre programas que puedan mantener abiertos
`dashboard/data/` o `processing_reports/`. También confirme que el disco tenga
espacio para los CSV descomprimidos, los archivos temporales y la publicación.

### Nota sobre los límites espaciales

Los límites se mantienen en dos ubicaciones:

- `processing/input/spatial/` para asignar corporaciones durante el procesamiento.
- `dashboard/spatial/` para dibujar los polígonos en el mapa.

Si el límite cambia, reemplace en ambas carpetas los componentes `.shp`, `.dbf`, `.shx`, `.prj` y `.cpg`. No mezcle archivos de fechas o versiones diferentes.

La comprobación debe realizarse sobre el conjunto completo, no solo sobre el
archivo `.shp`. Los cinco componentes deben compartir el mismo nombre base y
pertenecer a la misma versión. Una diferencia entre las dos carpetas puede
producir una asignación de corporación distinta de la geometría mostrada en el
dashboard.

### Preparación de fotografías destacadas

Las imágenes del carrusel no provienen automáticamente de Wildlife Insights.
El usuario selecciona las fotografías autorizadas y conserva los archivos de
máxima resolución en `processing/input/favorites_originals/`. La GUI genera
copias optimizadas en `dashboard/www/images/favorites/`, que es la ubicación
leída por el dashboard.

- `General/` contiene las fotografías de las vistas globales de todas las
  corporaciones o todos los proyectos.
- `<project_id>/` contiene las fotografías propias de un proyecto. El nombre
  de la carpeta debe coincidir exactamente con el identificador disponible en
  `projects.csv`, por ejemplo `2002517`.
- Una vista de corporación reúne automáticamente las fotografías de las
  carpetas de los proyectos que pertenecen a esa corporación y al alcance
  aplicado.

Para incorporar un proyecto nuevo, cree su carpeta con el `project_id` dentro
de `favorites_originals` y copie allí las fotografías autorizadas. No es
necesario modificar el código. Si existen
datos procesados para una selección pero no se encuentran imágenes, el
dashboard muestra una indicación explícita con la carpeta que se debe crear o
revisar; no sustituye esas fotografías con imágenes de otro proyecto.

Al iniciar la aplicación, la consola de R presenta un resumen automático de la
galería: identifica los proyectos sin imágenes, informa cuántos archivos
válidos tiene cada proyecto disponible y reporta el contenido de `General/`.
Este diagnóstico es informativo y no se muestra como ventana emergente en la
vista web.

En la sección **Preparación de imágenes para la galería**, seleccione
**Optimizar y publicar imágenes**. La operación corrige la orientación,
conserva la proporción, limita el lado mayor a 1.600 píxeles, guarda los JPEG
con calidad 82 % y elimina metadatos EXIF de las copias publicadas. Los PNG sin
transparencia se convierten a JPEG; los PNG con transparencia se conservan.
La huella SHA-256 evita volver a procesar originales que no cambiaron.

La carpeta de originales funciona como fuente maestra: cada ejecución construye
una galería completa en un directorio temporal y reemplaza
`dashboard/www/images/favorites/` únicamente cuando todas las fotografías son
válidas. Por ello, un archivo retirado de `favorites_originals` también deja de
publicarse en la siguiente ejecución y no quedan copias antiguas combinadas con
la nueva galería.

El resumen aparece en la interfaz y el detalle se guarda en
`processing_reports/gallery_optimization.json` y
`processing_reports/gallery_optimization.csv`. Un archivo defectuoso se
reporta sin reemplazar su copia publicada anteriormente.

Antes del despliegue, confirme que las fotografías cuentan con autorización de
uso y no contienen información que deba restringirse. Los originales y las
copias publicadas se excluyen de Git. Solo las copias optimizadas de
`dashboard/www/images/favorites/` deben incluirse con `www/` en el despliegue.

Estas carpetas están excluidas de Git. Esta regla protege incorporaciones nuevas, pero no elimina copias presentes en versiones históricas del repositorio; esa revisión debe realizarse antes de una publicación pública.

## 4. Inicio de la GUI

Ejecute:

```text
processing/launch_gui.bat
```

También puede usar:

```powershell
python processing/run_gui.py
```

La GUI detecta automáticamente la raíz del proyecto y propone las rutas estándar.

## 5. Validación de entrada

En **Ubicación y validación de los insumos**:

1. Confirme la carpeta de CSV.
2. Confirme la carpeta de publicación.
3. Confirme el shapefile.
4. Confirme la carpeta independiente `processing_reports/` para los informes.
5. Seleccione **Validar carpetas y cargar proyectos**.

La validación muestra los proyectos disponibles y habilita la parametrización. Si falla, revise el mensaje antes de procesar.

## 6. Parámetros

### Nombre de la iniciativa

Identifica la procedencia institucional del conjunto de información. Se guarda
como metadato en el manifiesto y en la dimensión de proyectos para conservar
la trazabilidad de la publicación; no cambia los filtros, los cálculos ni el
texto visible del encabezado.

### Título del dashboard

Es el texto visible que completa el encabezado “Reporte de Datos de
Fototrampeo”. Su modificación solo cambia la presentación del título.

### Periodo

Seleccione fecha inicial y final. Los registros externos al periodo no se publican y quedan documentados como exclusiones informativas.

### Intervalos

Seleccione por lo menos una opción entre sin filtro, 30 minutos, 1 hora y 24 horas. Elegir más intervalos aumenta el tiempo y el tamaño de los productos. El procesamiento genera para cada opción el total de registros independientes y los indicadores de diversidad asociados.

### Proyectos

Puede procesar todos los proyectos o una selección. La interfaz muestra identificador y nombre.

### Corporación

La asignación se obtiene espacialmente. Use la reasignación manual únicamente cuando exista una corrección confirmada; la decisión queda registrada.
Los selectores de proyecto y corporación permiten escribir cualquier fragmento
del identificador, nombre o sigla para localizar rápidamente una opción.

### Botones de la sección de parámetros

- **Seleccionar proyectos** abre un buscador con identificador, nombre, eventos
  y corporación estimada. Debe conservarse al menos un proyecto.
- **Aplicar reasignación** reemplaza la corporación calculada para el proyecto
  elegido y registra la decisión en el reporte de calidad.
- **Quitar reasignación** elimina la corrección manual del proyecto activo.

## 7. Procesamiento

### Preparación opcional de la galería

Esta operación es independiente del procesamiento de datos y puede ejecutarse
antes o después de una actualización. Organice primero los originales en
`General/` y `<project_id>/`; después seleccione **Optimizar y publicar
imágenes**. La barra informa el avance y al terminar muestra imágenes
optimizadas, omitidas por no tener cambios y archivos con error. No cierre la
GUI mientras esté activa.

**Detener optimización** solicita una cancelación cooperativa. La fotografía que
se esté procesando puede tardar unos segundos en terminar, pero la carpeta
temporal se descarta y la galería anterior continúa disponible sin cambios.

No copie posteriormente los originales de máxima resolución sobre las copias
publicadas, porque volvería a aumentar el paquete del dashboard. Para una
actualización futura, cambie el archivo correspondiente en
`favorites_originals` y ejecute nuevamente la operación.

Seleccione **Procesar y publicar datos**. Durante la ejecución:

- El botón de procesamiento permanece deshabilitado.
- **Detener procesamiento** solicita una cancelación segura.
- La barra muestra el avance.
- La publicación anterior permanece activa hasta finalizar la nueva.

No cierre la aplicación mientras el proceso esté en ejecución.

**Detener procesamiento** solicita una cancelación cooperativa. El proceso
termina en un punto seguro, elimina los temporales cuando es posible y conserva
la publicación anterior. **Limpiar para nueva ejecución** vuelve a habilitar los
parámetros después de finalizar, cancelar o reportar un error. **Abrir carpeta
de datos publicados** se habilita cuando existe un resultado aprobado.

## 8. Revisión de resultados

### Estado del procesamiento

Resume periodo, alcance, intervalos, duración, CPU, memoria, observaciones leídas, publicadas y excluidas.

### Resumen por proyecto

Permite comprobar proyectos, corporaciones, cámaras, eventos y observaciones.

### Resumen de calidad

Agrupa situaciones por estado e informa resultado, registros afectados y recomendación.

### Detalle de calidad

Abre `processing_reports/quality_report.html` en el navegador. El encabezado
identifica el `run_id` y presenta el número de tipos de situación y registros
afectados, separados según el tratamiento aplicado: exclusión, procesamiento
con limitación, resolución automática o configuración del usuario.

La sección **Resumen y acciones sugeridas** explica cada situación, su efecto
en el procesamiento, ejemplos tomados del archivo fuente y la recomendación de
revisión. La sección **Detalle de registros** muestra una muestra navegable de
hasta 1.000 filas, indica cuántos hallazgos existen en el detalle completo y
permite filtrar por la combinación de estado y situación. También dispone de
una búsqueda por archivo, identificador, campo, valor o texto. Para cada caso
informa archivo, fila, identificador, campo, valor original y acción técnica.
Los archivos CSV y Parquet contienen el detalle completo, mientras que el HTML
presenta una muestra estratificada para facilitar su revisión.

Los archivos de soporte se guardan fuera del paquete desplegable, en
`processing_reports/`:

- `quality_report.html`: reporte visual completo que abre la GUI.
- `quality_report.json`: resumen estructurado que alimenta la interfaz.
- `quality_issues.csv`: detalle completo para revisión en herramientas de
  oficina.
- `quality_issues.parquet`: detalle equivalente para análisis técnico.
- `project_summary.csv`: resumen operativo por proyecto.
- `gallery_optimization.json`: resumen estructurado de la preparación de imágenes.
- `gallery_optimization.csv`: detalle por fotografía original y copia publicada.

Cada ejecución aprobada reemplaza el conjunto anterior de informes. Si se
requiere conservar evidencia histórica, copie la carpeta externamente antes de
iniciar un nuevo procesamiento.

Las categorías tienen efectos diferentes:

- **Excluido por inconsistencia** identifica datos que no se publicaron porque
  falta información obligatoria o existen valores incompatibles.
- **Procesado con limitación** identifica datos conservados que no pueden
  utilizarse en una parte de la visualización, por ejemplo en el mapa.
- **Resuelto automáticamente** informa una decisión conservadora aplicada por
  el pipeline, por ejemplo ante duplicados o periodos superpuestos.
- **Excluido por criterios de análisis** documenta datos fuera del periodo o
  sin taxonomía utilizable; no siempre representa un error del archivo fuente.
- **Configuración aplicada** registra una decisión explícita del usuario, como
  la reasignación manual de corporación.

## 9. Criterio de publicación exitosa

Una ejecución es exitosa cuando:

- La barra alcanza 100 %.
- Se informa que los datos fueron publicados.
- `manifest.json` tiene estado `approved`.
- La validación independiente retorna `passed`.
- No existen productos faltantes.

## 10. Ejecución del dashboard

En RStudio:

1. Abra `dashboard/app.R`.
2. Confirme que `dashboard/data/` contiene la publicación.
3. Seleccione **Run App**.

Desde consola R:

```r
shiny::runApp("dashboard")
```

La aplicación encuentra sus recursos sin depender del directorio desde el cual se inició.

## 11. Uso del dashboard

1. Seleccione vista de proyectos o corporaciones.
2. Seleccione la entidad.
3. Seleccione un evento o todos los eventos.
4. Seleccione el intervalo disponible.
5. Aplique la selección.

La aplicación presenta:

- Indicadores operativos y de biodiversidad.
- Mapa de cámaras.
- Ocupación por especie.
- Patrón de actividad.
- Diurnalidad.
- Ranking detallado.
- Galería y opciones de descarga.

En la tabla de indicadores, **Imágenes** representa las observaciones válidas y permanece estable entre intervalos. **Registros independientes** muestra las observaciones conservadas por la regla temporal seleccionada. Los números de Hill se calculan a partir de estos registros independientes.

## 12. Validaciones antes del despliegue

Desde la raíz:

```powershell
python -m unittest discover -s processing/tests -v
python processing/validate_release.py --output dashboard/data
```

## 13. Despliegue de la aplicación

### 13.1 Posit Connect

Publique como directorio de aplicación `dashboard/`. Incluya:

- `app.R`
- `dashboard_functions.R`
- `data/`
- `spatial/`
- `www/`
- `.Rprofile`
- `renv.lock`

No seleccione `processing_reports/`: contiene información de revisión local y
se mantiene fuera de la carpeta desplegable del dashboard.

Tampoco seleccione `.Rhistory`, `.Rproj.user/`, `rsconnect/` ni
`renv/library/`. Estos elementos corresponden al equipo local y no forman parte
de la aplicación reproducible.

`processing/` no es obligatorio para ejecutar el dashboard ya publicado. Sí debe conservarse en el repositorio para futuras actualizaciones de datos.

### 13.2 Servidor institucional

La misma carpeta `dashboard/` puede ejecutarse en Linux mediante Shiny Server.
La instalación concreta -contenedor, proxy, ruta pública, HTTPS, permisos,
respaldo y actualización de releases- debe ajustarse a las decisiones del equipo
de TI y validarse en el servidor de destino.

Los archivos operativos que incluyan nombres de host, rutas institucionales,
certificados, usuarios o scripts de administración no deben publicarse en este
repositorio. El puerto de Shiny tampoco debe exponerse directamente a Internet;
la publicación debe pasar por el proxy y los controles autorizados por TI.

## 14. Solución de problemas

| Situación | Acción recomendada |
|---|---|
| No se detectan proyectos | Revise `projects.csv`, `deployments.csv` y archivos de imágenes. |
| No se encuentra el shapefile | Confirme todos sus componentes y la ruta seleccionada. |
| Acceso denegado al publicar | Cierre exploradores, RStudio u otros procesos que usen `dashboard/data/`. |
| El dashboard informa datos incompletos | Ejecute `validate_release.py` y revise el manifiesto. |
| Faltan paquetes R | Instale los paquetes enumerados en este manual. |
| No aparecen imágenes en un proyecto | Cree o revise `processing/input/favorites_originals/<project_id>/`, agregue archivos JPG, JPEG o PNG y ejecute **Optimizar y publicar imágenes**. |
| No aparecen imágenes en una vista global | Revise `processing/input/favorites_originals/General/` y vuelva a optimizar; el uso de mayúscula inicial es obligatorio en Linux y Posit Connect. |
| No aparecen imágenes en una corporación | Confirme que al menos uno de sus proyectos tenga una carpeta `<project_id>` con imágenes. |
| Una imagen no se optimiza | Revise `processing_reports/gallery_optimization.csv`; confirme que el archivo pueda abrirse y no esté dañado. |
| La corporación no corresponde | Revise coordenadas y límites; use reasignación solo con soporte técnico. |
| La carpeta de resultados está bloqueada | Cierre el Explorador, el reporte HTML o una sesión del dashboard que mantenga archivos abiertos y repita la ejecución. |

## 15. Conservación y actualización

El pipeline mantiene una sola publicación activa y un solo conjunto vigente de
informes en `processing_reports/`. Si se requiere historial, copie externamente
`manifest.json` y la carpeta de informes antes de ejecutar una actualización.

No edite manualmente los Parquet. Las correcciones deben aplicarse en Wildlife Insights, en los parámetros autorizados o en el código versionado.

## 16. Simulación recomendada de una actualización

Antes de un despliegue institucional, ejecute el siguiente ensayo operativo:

1. Conserve una copia externa de `manifest.json` y anote su `run_id`.
2. Inicie la GUI, valide los insumos y seleccione un periodo, uno o más
   proyectos y los intervalos requeridos.
3. Inicie el procesamiento y confirme que los campos quedan bloqueados, el
   botón de detener está disponible y la publicación vigente continúa siendo
   legible por el dashboard.
4. Deje terminar el proceso y revise las cuatro pestañas de resultados.
5. Ejecute `python processing/validate_release.py --output dashboard/data`.
6. Abra el dashboard, aplique filtros de proyecto y corporación y confirme que
   los intervalos disponibles corresponden al manifiesto.
7. Compruebe que el nuevo `run_id` solo aparece después de alcanzar 100 % y que
   no quedan carpetas `.staging-*` o `.previous-*`.

Registre como evidencia el `run_id`, el resultado de la validación independiente
y las pruebas funcionales realizadas. Las pruebas automatizadas verifican que
una cancelación anterior a la activación conserva el manifiesto vigente sin
modificaciones.

## 17. Responsables y licencia

- Desarrollo: Cristian C. Acevedo, Ingeniero de Soluciones.
- Supervisión: Angélica Diaz Pulido, Investigador Adjunto, Centro Estudios Socioecológicos y Cambio Global, Dirección de Conocimiento, Instituto Humboldt.
- Versión: `v2026.1.0`.
- Licencia del código: MIT.

## 18. Manejo de información privada

El repositorio público no debe contener datos de operación. `.gitignore` excluye:

- Archivos RAW de Wildlife Insights.
- Datos procesados y reportes de calidad.
- Límites espaciales de corporaciones.
- Fotografías del dashboard.

Estos recursos deben conservarse en infraestructura institucional con acceso
restringido. Antes de ejecutar `git add`, confirme que ningún archivo privado
aparezca en `git status`. El acceso al servicio desplegado debe seguir la
política definida por el Instituto.
