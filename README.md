# Dashboard Red OTUS 2026

Solución para validar, transformar, analizar y visualizar datos de fototrampeo de la Red OTUS. La publicación 2026 integra un pipeline en Python y un dashboard unificado en R Shiny para consultas por proyecto, corporación y evento de muestreo.

## Alcance

La solución cubre tres procesos complementarios:

1. **Preparación de datos:** recibe archivos CSV exportados desde Wildlife Insights, controla su calidad y genera productos Parquet optimizados.
2. **Visualización:** presenta indicadores operativos y de biodiversidad mediante una única aplicación con vistas por proyecto y corporación.
3. **Actualización institucional:** valida la publicación aprobada y genera desde la GUI un ZIP de insumos con manifiestos y huellas SHA-256, listo para transferir al servidor.

Los cálculos de mayor costo se realizan previamente en Python. R consume productos aprobados y se concentra en filtros, visualizaciones, tablas y descargas.

## Estructura

```text
dashboard-red-otus/
├── docs/                  Documentación técnica y operativa
├── processing/            Pipeline, GUI, validaciones e insumos
│   ├── input/raw/         CSV descargados de Wildlife Insights
│   ├── input/spatial/     Límites geográficos para asignación espacial
│   ├── red_otus_pipeline/ Código fuente del procesamiento
│   │   ├── packaging.py   Validación y empaquetado de actualizaciones
│   │   └── deployment.py  Cliente de publicación controlada por SSH
│   ├── tests/             Pruebas automatizadas de reglas y publicación
│   ├── run_gui.py         Inicio portable de la interfaz gráfica
│   └── validate_release.py Validación independiente de la publicación
├── processing_reports/    Informes locales de calidad y operación
└── dashboard/             Aplicación R Shiny
    ├── app.R              Interfaz y lógica reactiva
    ├── dashboard_functions.R Lectura, validación y visualizaciones
    ├── data/              Publicación vigente del pipeline
    ├── spatial/           Límites usados en el mapa
    └── www/               Estilos, fuentes, imágenes y JavaScript
```

## Inicio rápido

1. Instale Python 3.11, 3.12 o 3.13. La versión validada para este release es Python 3.13.11. Luego restaure las dependencias congeladas:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r processing/requirements.lock.txt
   python -m pip install -e processing --no-deps
   ```

2. Elimine el contenido operativo anterior de `processing/input/raw/`, sin
   borrar el archivo `.gitkeep` cuando esté visible.
3. Solicite en Wildlife Insights la descarga completa de la iniciativa,
   descargue el archivo ZIP, descomprímalo y copie únicamente los CSV
   resultantes en `processing/input/raw/`. No procese directamente el ZIP.
4. Confirme que los componentes de `CAR_MPIO` sean idénticos en
   `processing/input/spatial/` y `dashboard/spatial/`.
5. Agregue las fotografías originales en `processing/input/favorites_originals/`
   y use la GUI para publicar copias optimizadas en
   `dashboard/www/images/favorites/`. La carpeta `General` alimenta las vistas
   globales y cada carpeta nombrada con un `project_id` alimenta ese proyecto y
   su corporación.
6. Ejecute `python processing/run_gui.py`.
7. Valide la entrada, configure el alcance y publique los datos.
8. Abra `dashboard/app.R` en RStudio, seleccione **Run App** y revise los datos, filtros, imágenes, mapas y descargas.
9. En la sección **Preparación de la actualización para el servidor**, valide el contenido, confirme la revisión local y genere el ZIP junto con su archivo `.sha256`. Los polígonos espaciales solo se incluyen cuando la opción correspondiente se selecciona expresamente.
10. Cuando exista una ventana institucional autorizada, use **Comprobar conexión** y luego **Transferir y activar actualización**. La GUI valida la identidad del servidor, publica el paquete y confirma la release activa y la respuesta HTTP. La reversión queda disponible como medida de recuperación.

Para preparar R por primera vez:

```powershell
Rscript -e "renv::restore(project='dashboard', prompt=FALSE)"
```

La publicación es transaccional: una ejecución incompleta no reemplaza los datos aprobados previamente.

La actualización de insumos es una operación manual y controlada, prevista
aproximadamente entre dos y cinco veces al año. El responsable inicia la GUI,
revisa el reporte de calidad y valida el dashboard antes de preparar o publicar
un paquete institucional. No existe una tarea calendarizada que procese o
despliegue datos sin intervención.

## Flujo de actualización segura

El procesador construye los once archivos Parquet y los informes en carpetas
temporales. Antes de activar una actualización, comprueba la estructura esperada
de los datos, las relaciones entre tablas, los intervalos solicitados y las
huellas de los archivos. La carpeta `dashboard/data/` solo se reemplaza cuando
todas las validaciones terminan correctamente. Si el usuario detiene la
ejecución o se presenta un error, la publicación anterior continúa disponible.

Cada publicación aprobada registra en `manifest.json` sus conteos, parámetros,
tiempos, versiones y huellas SHA-256. Estas cifras dependen de los insumos y no
se fijan en la documentación pública.

## Empaquetado para el servidor institucional

El empaquetado es una decisión manual posterior a la validación local, no una
consecuencia automática de terminar el procesamiento. La GUI comprueba el
manifiesto aprobado de datos, los hashes de los Parquet y el manifiesto de la
galería antes de habilitar la creación. El resultado contiene `data/`,
`favorites/`, `spatial/` cuando se solicita, `RELEASE.json` y `FILES.sha256`.
También se genera un archivo `.zip.sha256` para comprobar la transferencia.

Los paquetes se guardan por defecto en `internal_deployment/packages/`, dentro
de la copia institucional del proyecto pero excluidos de Git. La última carpeta
seleccionada queda recordada para las siguientes ejecuciones. No se incluyen
archivos RAW, informes de calidad, código fuente ni imágenes Docker.

La publicación semiautomática utiliza servidor, puerto, usuario y contraseña.
En la primera conexión registra localmente la identidad SSH observada y bloquea
cambios posteriores; la contraseña solo permanece en memoria durante la
operación. Los scripts de administración y los datos particulares de la
infraestructura institucional se distribuyen por canales internos autorizados y
no forman parte del repositorio público.

## Despliegue en Posit Connect

Para desplegar la aplicación con las dependencias congeladas, abra en RStudio el
archivo `dashboard/dashboard_red_otus_2026.Rproj`. Esta acción inicia R dentro de
la carpeta correcta y permite que `dashboard/.Rprofile` active automáticamente
el entorno `renv` antes de generar el paquete de publicación.

En una instalación nueva, ejecute una sola vez:

```r
renv::restore(prompt = FALSE)
stopifnot(renv::status()$synchronized)
```

Después reinicie la sesión de R y despliegue desde la carpeta `dashboard`:

```r
rsconnect::deployApp(
  appDir = ".",
  appName = "dashboard_red_otus_2026",
  account = "<cuenta_posit_connect>",
  server = "connect.posit.cloud",
  dependencyResolution = "renv"
)
```

Si RStudio se abrió desde la raíz del repositorio y no desde el archivo
`.Rproj`, cargue explícitamente el entorno antes de desplegar:

```r
deploy_dashboard <- rsconnect::deployApp
renv::load("dashboard")
stopifnot(renv::status(project = "dashboard")$synchronized)

deploy_dashboard(
  appDir = "dashboard",
  appName = "dashboard_red_otus_2026",
  account = "<cuenta_posit_connect>",
  server = "connect.posit.cloud",
  dependencyResolution = "renv"
)
```

No se recomienda agregar `renv.lock` a `.rscignore` ni utilizar
`dependencyResolution = "library"` para una publicación estable, ya que ambas
alternativas omiten el entorno congelado y pueden producir diferencias entre el
equipo local y Posit Connect.

En el diálogo de publicación de RStudio deben incluirse `.Rprofile`, `app.R`,
`dashboard_functions.R`, `renv.lock`, `data/`, `spatial/` y `www/`. No se deben
incorporar `processing/`, `processing_reports/`, `.Rproj.user/`, `.Rhistory` ni
la biblioteca local `renv/library/`.

## Despliegue institucional

La aplicación también puede ejecutarse mediante Shiny Server en Linux. La
configuración concreta del servidor -contenedores, proxy inverso, HTTPS, DNS,
credenciales, rutas y scripts de actualización- depende de la infraestructura
autorizada por el Instituto y se administra fuera de este repositorio. El código
público no incluye secretos ni datos operativos.

Antes de declarar estable un despliegue institucional se debe comprobar, en el
servidor de destino, el arranque de la aplicación, WebSocket, filtros, mapas,
galería, descargas, actualización de datos y reversión. Los cambios derivados de
esa validación deben incorporarse mediante una nueva revisión del código y sus
pruebas.

## Validación

Desde la raíz del proyecto:

```powershell
python -m unittest discover -s processing/tests -v
python processing/validate_release.py --output dashboard/data
```

## Documentación

- [Arquitectura de la solución](docs/ARCHITECTURE.md)
- [Flujo de procesamiento](docs/PROCESSING_WORKFLOW.md)
- [Diccionario de datos](docs/DATA_DICTIONARY.md)
- [Manual de operación](docs/OPERATION_MANUAL.md)

## Versionamiento

- Aplicación: **v2026.1.0**
- Estructura de datos: **2.2.0**
- Entorno Python validado: **3.13.11**
- Entorno R bloqueado: **4.5.2**

Durante esta iteración, los ajustes finos y correcciones menores permanecen identificados como `v2026.1.0`. Un cambio de versión se realizará únicamente cuando se defina una nueva iteración funcional.

La rama `legacy/2025` conserva la versión anterior únicamente como referencia
histórica. Esa implementación está deprecada y no debe usarse para nuevas
actualizaciones, despliegues ni desarrollos.

## Responsables

- **Desarrollo:** Cristian C. Acevedo, Ingeniero de Soluciones.
- **Supervisión:** Angélica Diaz Pulido, Investigador Adjunto, Centro Estudios Socioecológicos y Cambio Global, Dirección de Conocimiento, Instituto de Investigación de Recursos Biológicos Alexander von Humboldt.

## Licencia

El código desarrollado para esta solución se distribuye bajo la [Licencia MIT](LICENSE). Los datos, imágenes, marcas, fuentes y recursos de terceros mantienen sus condiciones de uso y atribución originales.

## Información privada

El repositorio público contiene código y documentación. Los CSV, datos procesados, límites geográficos y fotografías están excluidos de Git y deben administrarse únicamente en espacios institucionales autorizados.

La exclusión mediante `.gitignore` evita nuevas incorporaciones, pero no elimina archivos que hayan quedado registrados en commits anteriores. Antes de publicar una actualización del repositorio, se debe revisar su historial y, si la clasificación institucional lo exige, retirar de forma controlada cualquier dato o límite espacial histórico.
