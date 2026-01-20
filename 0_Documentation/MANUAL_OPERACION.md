# Manual de Operación del Dashboard
## Red OTUS Colombia - Sistema de Monitoreo de Biodiversidad con Cámaras Trampa

---

**Versión:** 2.0  
**Fecha:** Diciembre 2025  
**Institución:** Instituto Alexander von Humboldt  
**Proyecto:** Red OTUS Colombia

---

## 1. Introducción

### 1.1. ¿Qué es el Dashboard de la Red OTUS?

El Dashboard de la Red OTUS es una herramienta web interactiva que permite visualizar y analizar datos de biodiversidad capturados con cámaras trampa en Colombia. El sistema procesa información proveniente de **Wildlife Insights** y la presenta de manera clara y profesional para apoyar la toma de decisiones en conservación.

### 1.2. ¿Para qué sirve?

- **Monitorear biodiversidad**: Ver qué especies se registran en diferentes regiones
- **Analizar tendencias**: Identificar patrones de actividad y ocupación de especies
- **Generar reportes**: Exportar tablas y gráficos para informes técnicos
- **Compartir resultados**: Visualizar mapas y galerías de imágenes destacadas

### 1.3. Tipos de Dashboards Disponibles

El sistema cuenta con **dos vistas complementarias**:

**Dashboard por Corporaciones**
- Análisis por **Corporaciones Autónomas Regionales (CARs)**
- Vista regional con mapas de jurisdicción
- Ideal para administradores de CARs y análisis territoriales

**Dashboard por Proyectos**
- Análisis por **proyecto individual**
- Vista detallada de un solo proyecto de fototrampeo
- Ideal para investigadores y análisis técnicos específicos

---

## 2. Requisitos Previos

### 2.1. Software Necesario

Antes de usar el dashboard, asegúrese de tener instalado:

- **R** versión 4.0 o superior
- **RStudio** (recomendado para facilitar el uso)
- **Paquetes de R** necesarios:
  - shiny, shinydashboard, plotly, leaflet, DT, arrow, dplyr, sf

### 2.2. Datos Necesarios

El dashboard requiere tres archivos procesados:

1. **observations.parquet** - Registros de especies
2. **deployments.parquet** - Información de cámaras
3. **projects.parquet** - Catálogo de proyectos

Estos archivos deben estar en: `4_Dashboard/dashboard_input_data/`

> **Nota**: Si no tiene estos archivos, ejecute primero el pipeline de Python ubicado en `3_processing_pipeline/process_RAW_data_WI.py`

---

## 3. Cómo Iniciar el Dashboard

### 3.1. Pasos para Abrir el Dashboard

**Opción 1: Desde RStudio (Recomendada)**

1. Abra RStudio
2. Navegue a la carpeta del proyecto: `4_Dashboard/`
3. Abra el archivo que desee:
   - `Dashboard_Vista_Corporaciones.R` (vista por CARs)
   - `Dashboard_Vista_Proyectos.R` (vista por proyectos)
4. Haga clic en el botón **"Run App"** (esquina superior derecha)
5. El dashboard se abrirá automáticamente en su navegador

**Opción 2: Desde la Consola de R**

```r
# Cambiar al directorio del dashboard
setwd("ruta/al/proyecto/4_Dashboard/")

# Ejecutar el dashboard
shiny::runApp("Dashboard_Vista_Corporaciones.R")
```

### 3.2. Qué Esperar al Iniciar

Al abrir el dashboard, verá:

- ✅ **Mensaje de carga**: "Cargando datos..." (dura 2-5 segundos)
- ✅ **Interfaz completa**: Controles, selectores y visualizaciones vacías
- ✅ **Mensaje inicial**: "Seleccione filtros para visualizar datos"

> **Importante**: Los gráficos y tablas permanecerán vacíos hasta que seleccione y aplique filtros.

---

## 4. Uso del Dashboard por Corporaciones

### 4.1. Estructura de la Pantalla

El dashboard está organizado en **7 secciones**:

```
┌─────────────────────────────────────────────┐
│ 1. ENCABEZADO                               │
│    Título y logo institucional              │
├─────────────────────────────────────────────┤
│ 2. CONTROLES                                │
│    Selectores y botones de filtrado         │
├─────────────────────────────────────────────┤
│ 3. INDICADORES CLAVE                        │
│    Números de biodiversidad y esfuerzo      │
├─────────────────────────────────────────────┤
│ 4. TABLA DE ESPECIES                        │
│    Ranking detallado con búsqueda           │
├─────────────────────────────────────────────┤
│ 5. GRÁFICOS DE ANÁLISIS                     │
│    Ocupación, acumulación, actividad, mapa  │
├─────────────────────────────────────────────┤
│ 6. GALERÍA MULTIMEDIA                       │
│    Carrusel de imágenes destacadas          │
├─────────────────────────────────────────────┤
│ 7. EXPORTACIÓN                              │
│    Botones para descargar resultados        │
└─────────────────────────────────────────────┘
```

### 4.2. Paso a Paso: Cómo Filtrar Datos

#### Paso 1: Seleccionar Corporación

1. Ubique el selector **"Corporación"** en la sección de controles
2. Haga clic y elija una opción:
   - **Todas las corporaciones**: Vista consolidada de toda la red
   - **CORPOCALDAS, CAM, AMVA, etc.**: Vista de una CAR específica

#### Paso 2: Seleccionar Evento de Muestreo

1. Ubique el selector **"Evento de muestreo"**
2. Elija un período (ejemplo: `2024_2`, `2025_1`) o `Todos los eventos`

> **¿Qué es un evento?** Un evento es un período de muestreo específico, por ejemplo: "2024_2" significa el segundo evento del año 2024.

#### Paso 3: Seleccionar Intervalo de Independencia

1. Ubique el selector **"Intervalo de independencia"**
2. Deje el valor por defecto (**30 minutos**) o elija otro:
   - 1 minuto (análisis muy detallado)
   - 1 hora (análisis general)
   - 6 horas o 12 horas (análisis conservador)

> **¿Qué significa esto?** El intervalo define cuánto tiempo debe pasar entre dos fotografías de la misma especie para considerarlas eventos independientes. Por ejemplo, con 30 minutos: si un jaguar aparece 5 veces en 20 minutos, se cuenta como 1 solo evento.

#### Paso 4: Aplicar la Selección

1. Haga clic en el botón **"Aplicar selección"**
2. Espere 1-3 segundos mientras se procesan los datos
3. Las visualizaciones se actualizarán automáticamente

#### Paso 5: Limpiar Filtros (Opcional)

Si desea empezar de nuevo:
1. Haga clic en **"Limpiar selección"**
2. Todos los selectores volverán a su estado inicial

### 4.3. Interpretando los Indicadores

#### Indicadores Operacionales (Cajas Azules)

- **🗂️ Imágenes**: Total de fotografías capturadas
  - *Ejemplo: 12,345 imágenes*
  
- **📸 Cámaras**: Número de sitios de muestreo activos
  - *Ejemplo: 45 cámaras*
  
- **📅 Trampas/noche**: Esfuerzo de muestreo total
  - *Ejemplo: 1,890 días-cámara*
  - *Cómo se calcula: Número de cámaras × días de funcionamiento*

#### Indicadores de Biodiversidad (Cajas Verdes)

- **🏞️ Especies**: Total de especies registradas
  - *Ejemplo: 87 especies*
  
- **🐆 Mamíferos**: Especies de mamíferos
  - *Ejemplo: 42 mamíferos*
  
- **🦅 Aves**: Especies de aves
  - *Ejemplo: 35 aves*

#### Índices de Diversidad de Hill (Cajas Naranjas)

- **🌿 Hill 1 (q=0)**: Riqueza total de especies
  - *Igual al indicador "Especies"*
  
- **🌱 Hill 2 (q=1)**: Especies "efectivas" (ponderadas por abundancia)
  - *Ejemplo: Si Hill 2 = 45, hay 45 especies igualmente comunes en términos de diversidad*
  
- **🌳 Hill 3 (q=2)**: Especies muy abundantes (dominantes)
  - *Ejemplo: Si Hill 3 = 12, significa que 12 especies concentran la mayoría de registros*

> **Interpretación**: Si Hill 1 = 87, Hill 2 = 45 y Hill 3 = 12, indica que hay 87 especies, pero solo 45 son relativamente comunes y 12 son muy abundantes. Esto sugiere que hay especies raras.

### 4.4. Usando la Tabla de Especies

#### ¿Qué muestra la tabla?

La tabla presenta un ranking de especies con las siguientes columnas:

- **Ranking**: Posición según número de registros independientes
- **Nombre común**: Ejemplo: "Jaguar", "Puma", "Venado cola blanca"
- **Nombre científico**: Ejemplo: *Panthera onca*, *Puma concolor*
- **Clase**: Mammalia, Aves, Reptilia, etc.
- **Imágenes**: Total de fotografías de esa especie
- **Registros independientes**: Eventos únicos según el intervalo configurado
- **Ocupación (%)**: Porcentaje de cámaras donde se detectó la especie

#### Funciones Interactivas

**Búsqueda:**
1. Use el campo de búsqueda (esquina superior derecha de la tabla)
2. Escriba un nombre (ejemplo: "jaguar")
3. La tabla se filtrará automáticamente

**Ordenamiento:**
1. Haga clic en el encabezado de cualquier columna
2. La tabla se ordenará de forma ascendente/descendente

**Paginación:**
- Use los botones **"Anterior"** y **"Siguiente"** para navegar
- Por defecto muestra 15 especies por página

#### Descargar la Tabla en CSV

1. Haga clic en **"Descargar Tabla de Especies"**
2. Se descargará un archivo CSV con formato:
   - Nombre: `Ranking_Especies_CORPOCALDAS_2024_2_20251209.csv`
3. Puede abrir el archivo en Excel o cualquier hoja de cálculo

### 4.5. Interpretando los Gráficos

#### Gráfico 1: Ocupación de Especies

**¿Qué muestra?**
- Barras horizontales con las 15 especies más frecuentes
- El porcentaje indica en cuántos sitios se detectó cada especie

**Ejemplo de interpretación:**
- Jaguar: 78% → Se detectó en 78% de las cámaras (especie ampliamente distribuida)
- Oso hormiguero: 23% → Solo apareció en 23% de las cámaras (especie rara o localizada)

**Colores:**
- Verde: Mamíferos
- Azul: Aves
- Gris: Otras clases

#### Gráfico 2: Curva de Acumulación de Especies

**¿Qué muestra?**
- Cómo aumenta el número de especies a medida que pasa el tiempo
- El eje X es el tiempo (días de muestreo)
- El eje Y es el número acumulado de especies

**Ejemplo de interpretación:**
- Curva con pendiente pronunciada al inicio: Se están descubriendo muchas especies nuevas
- Curva que se aplana al final: El muestreo está capturando casi todas las especies presentes

**¿Cuándo es suficiente el muestreo?**
Si la curva se aplana (forma de "S"), significa que el esfuerzo es adecuado.

#### Gráfico 3: Patrón de Actividad Circadiano

**¿Qué muestra?**
- Distribución de actividad de las especies por hora del día (0-24h)
- Líneas de colores representan las 5 especies más frecuentes

**Funciones interactivas:**
- **Zoom**: Haga doble clic para acercar
- **Pan**: Arrastre el mouse para desplazar
- **Tooltip**: Pase el mouse sobre la línea para ver valores exactos
- **Leyenda**: Haga clic en una especie para mostrar/ocultar su línea

**Ejemplo de interpretación:**
- Pico entre 6-8 AM → Especie con actividad crepuscular matutina
- Pico entre 20-22h → Especie nocturna
- Actividad constante 24h → Especie con actividad irregular (cathemeral)

#### Gráfico 4: Mapa Geográfico

**¿Qué muestra?**
- **Puntos azules**: Ubicación de cada cámara trampa
- **Polígono azul claro**: Jurisdicción de la CAR seleccionada (solo si eligió una corporación específica)

**Funciones interactivas:**
- **Zoom**: Use los botones + y - o la rueda del mouse
- **Pan**: Arrastre el mapa para desplazarse
- **Popup**: Haga clic en un punto para ver información del sitio
  - Nombre del sitio
  - Coordenadas
  - Número de especies detectadas

**Capas disponibles:**
- Puede cambiar entre vista satelital y vista de calles (botón esquina superior derecha)

### 4.6. Galería de Imágenes

#### ¿Qué muestra?

Un carrusel con fotografías destacadas de fauna capturadas en las cámaras trampa.

#### Funciones:

- **Autoplay**: Las imágenes cambian automáticamente cada 4 segundos
- **Navegación manual**: Use las flechas laterales para avanzar/retroceder
- **Puntos indicadores**: Muestran cuántas imágenes hay en total

#### Organización de imágenes:

- Si seleccionó **"Todas las corporaciones"**: Muestra imágenes de `www/images/favorites/General/`
- Si seleccionó una CAR específica: Muestra imágenes de `www/images/favorites/{NOMBRE_CAR}/`

> **Nota**: Máximo 40 imágenes aleatorias por sesión. Si desea ver otras imágenes, cierre y vuelva a abrir el dashboard.

### 4.7. Exportar Resultados

#### Opción 1: Descargar Tabla de Especies (CSV)

**Pasos:**
1. Asegúrese de haber aplicado filtros
2. Haga clic en **"Descargar Tabla de Especies"**
3. Guarde el archivo `.csv` en su computadora

**Formato del archivo:**
```
Ranking,Especie,Nombre científico,Clase,Imágenes,Registros independientes,Ocupación (%)
1,Jaguar,Panthera onca,Mammalia,456,145,78
2,Puma,Puma concolor,Mammalia,389,132,67
...
```

**Usos:**
- Copiar la tabla a informes en Word
- Hacer análisis estadísticos en Excel
- Crear gráficos personalizados

#### Opción 2: Capturar Dashboard Completo (PNG)

**Pasos:**
1. Asegúrese de que todas las visualizaciones estén cargadas
2. Ajuste el zoom de su navegador al 100% (para mejor calidad)
3. Haga clic en **"Capturar Dashboard"**
4. Espere 3-5 segundos mientras se genera la imagen
5. Se descargará automáticamente un archivo `.png`

**Formato del archivo:**
- Nombre: `Dashboard_CORPOCALDAS_2024_2_20251209.png`
- Resolución: Alta (2x)
- Incluye: Indicadores, tablas, gráficos (parcialmente el mapa)

**Limitación conocida:**
- El mapa base de Leaflet puede no capturarse perfectamente
- Recomendación: Tome una captura de pantalla manual del mapa si necesita incluirlo en un informe

**Usos:**
- Anexar a presentaciones de PowerPoint
- Incluir en informes técnicos
- Compartir resultados por correo electrónico

---

## 5. Uso del Dashboard por Proyectos

### 5.1. Diferencias con el Dashboard por Corporaciones

| Característica | Dashboard Corporaciones | Dashboard Proyectos |
|---------------|------------------------|---------------------|
| **Filtro principal** | Corporación (CAR) | Proyecto individual |
| **Mapa** | Con polígonos de jurisdicción | Solo puntos de cámaras |
| **Público objetivo** | Administradores de CARs | Investigadores de campo |
| **Nivel de análisis** | Regional/territorial | Proyecto específico |

### 5.2. Paso a Paso: Filtrar por Proyecto

#### Paso 1: Seleccionar Proyecto

1. Ubique el selector **"Proyecto"**
2. Elija un proyecto de la lista (ejemplo: "Fototrampeo CORPOCALDAS")

#### Paso 2: Seleccionar Evento (Opcional)

1. Elija un evento específico o **"Todos los eventos"**

#### Paso 3: Aplicar Selección

1. Haga clic en **"Aplicar selección"**
2. Las visualizaciones se actualizarán

### 5.3. Visualizaciones Disponibles

El Dashboard por Proyectos tiene **las mismas visualizaciones** que el Dashboard por Corporaciones:

- ✅ Indicadores clave
- ✅ Tabla de especies
- ✅ Gráfico de ocupación
- ✅ Curva de acumulación
- ✅ Patrón de actividad
- ✅ Mapa (sin polígonos de jurisdicción)
- ✅ Galería de imágenes

> La interpretación de cada visualización es **exactamente igual** a la descrita en la sección 4.

---

## 6. Solución de Problemas Comunes

### 6.1. El dashboard no abre

**Síntomas:**
- Error al hacer clic en "Run App"
- Mensaje: "Cannot find function 'runApp'"

**Soluciones:**
1. Verifique que instaló el paquete `shiny`:
   ```r
   install.packages("shiny")
   ```
2. Reinicie RStudio
3. Intente abrir el dashboard nuevamente

### 6.2. Error: "No se encontraron archivos Parquet"

**Síntomas:**
- Dashboard abre pero no muestra selectores
- Mensaje en consola: "Archivos parquet no encontrados"

**Soluciones:**
1. Verifique que existen los archivos en `4_Dashboard/dashboard_input_data/`:
   - observations.parquet
   - deployments.parquet
   - projects.parquet
   
2. Si no existen, ejecute primero el pipeline de Python:
   ```bash
   cd 3_processing_pipeline
   python process_RAW_data_WI.py
   ```

### 6.3. Las visualizaciones están vacías

**Síntomas:**
- Dashboard abre correctamente
- Selectores funcionan
- Pero gráficos y tablas están vacíos

**Soluciones:**
1. Verifique que seleccionó **y aplicó** los filtros (botón "Aplicar selección")
2. Verifique que los datos filtrados no están vacíos:
   - Intente seleccionar "Todas las corporaciones" o "Todos los eventos"
3. Revise la consola de R por errores

### 6.4. Error al descargar CSV

**Síntomas:**
- Botón "Descargar Tabla" no responde
- Se descarga archivo vacío

**Soluciones:**
1. Asegúrese de haber aplicado filtros primero
2. Verifique que la tabla tiene datos (debe mostrar especies)
3. Intente cambiar la carpeta de descargas predeterminada del navegador

### 6.5. El mapa no carga

**Síntomas:**
- Mapa aparece gris o en blanco
- No se ven puntos de cámaras

**Soluciones:**
1. Verifique su conexión a internet (Leaflet requiere conexión para tiles)
2. Espere 5-10 segundos para que carguen los tiles del mapa base
3. Si persiste, revise que las coordenadas en `deployments.parquet` son válidas

### 6.6. Error: "object 'CAR_MPIO' not found"

**Síntomas:**
- Dashboard abre pero muestra error en el mapa
- Solo en Dashboard por Corporaciones

**Soluciones:**
1. Verifique que existe el shapefile:
   - Carpeta: `2_Data_Shapefiles_CARs/`
   - Archivo: `CAR_MPIO.shp` (y archivos asociados .shx, .dbf, .prj)
   
2. Si no existe, contacte al administrador del proyecto para obtener el shapefile

### 6.7. Rendimiento lento

**Síntomas:**
- Dashboard tarda mucho en cargar (>30 segundos)
- Visualizaciones tardan en actualizarse

**Soluciones:**
1. Verifique el tamaño de sus archivos Parquet:
   - Si `observations.parquet` > 50 MB, considere filtrar datos en el pipeline Python
   
2. Cierre otras aplicaciones que consuman memoria RAM

3. Use filtros más específicos:
   - En lugar de "Todos los eventos", seleccione un evento particular
   - En lugar de "Todas las corporaciones", seleccione una CAR específica

### 6.8. Las imágenes de la galería no cargan

**Síntomas:**
- Galería vacía o muestra iconos rotos

**Soluciones:**
1. Verifique que existen imágenes en:
   - `4_Dashboard/www/images/favorites/General/` (para vista consolidada)
   - `4_Dashboard/www/images/favorites/{NOMBRE_CAR}/` (para vista por CAR)
   
2. Verifique que las imágenes tienen formato válido:
   - Extensiones permitidas: `.jpg`, `.jpeg`, `.png`
   
3. Si la carpeta está vacía, agregue imágenes manualmente

---

## 7. Buenas Prácticas de Uso

### 7.1. Antes de Generar Reportes

✅ **Verifique los filtros aplicados**
- Asegúrese de seleccionar la corporación/proyecto correcto
- Confirme que el evento corresponde al período de análisis

✅ **Revise los indicadores**
- Número de cámaras debe ser razonable (>5 cámaras)
- Número de especies debe ser coherente con la región

✅ **Explore los datos**
- Use la búsqueda en la tabla de especies
- Revise el patrón de actividad de especies clave

### 7.2. Al Exportar Datos

✅ **Nombre descriptivo de archivos**
- Los archivos descargados incluyen fecha automáticamente
- Agregue información adicional si es necesario (ejemplo: renombre el CSV a `Ranking_Especies_CORPOCALDAS_2024_2_FINAL.csv`)

✅ **Verifique la descarga**
- Abra el archivo CSV en Excel para confirmar que se descargó correctamente
- Revise que la imagen PNG muestra todas las secciones del dashboard

### 7.3. Para Presentaciones

✅ **Ajuste el zoom del navegador**
- Use 100% de zoom para mejor calidad de captura
- Si el dashboard no cabe en pantalla, use zoom de 90% o 80%

✅ **Capture secciones individualmente si es necesario**
- Use la herramienta de captura de Windows (Win + Shift + S)
- Capture el mapa separadamente para mejor calidad

### 7.4. Mantenimiento de Datos

✅ **Actualice los datos periódicamente**
- Descargue nuevos datos de Wildlife Insights cada mes/trimestre
- Ejecute el pipeline de Python para actualizar los Parquet
- Reabra el dashboard para cargar los nuevos datos

✅ **Respalde los archivos Parquet**
- Haga copias de seguridad de `dashboard_input_data/`
- Mantenga versiones anteriores por si necesita comparar

---

## 8. Preguntas Frecuentes (FAQ)

### 8.1. Sobre los Datos

**P: ¿Con qué frecuencia debo actualizar los datos?**  
R: Depende de su proyecto. Lo recomendado es mensual o trimestral, después de cada descarga de Wildlife Insights.

**P: ¿Puedo combinar datos de diferentes fuentes además de Wildlife Insights?**  
R: Sí, pero debe procesarlos primero con el pipeline Python para generar archivos Parquet compatibles.

**P: ¿Qué formato tienen los archivos Parquet?**  
R: Parquet es un formato columnar optimizado para lectura rápida. Se lee con R usando el paquete `arrow`.

### 8.2. Sobre los Filtros

**P: ¿Qué intervalo de independencia debo usar?**  
R: 30 minutos es el estándar en estudios ecológicos. Use 1 hora si desea ser más conservador.

**P: ¿Puedo aplicar múltiples filtros a la vez?**  
R: Sí, puede seleccionar Corporación + Evento + Intervalo y aplicarlos simultáneamente.

**P: ¿Qué pasa si selecciono "Todos los eventos"?**  
R: Se mostrarán datos consolidados de todos los períodos de muestreo, útil para análisis históricos.

### 8.3. Sobre las Visualizaciones

**P: ¿Por qué el mapa no muestra el polígono de jurisdicción?**  
R: El polígono solo aparece si selecciona una CAR específica (no en "Todas las corporaciones").

**P: ¿Puedo personalizar los gráficos?**  
R: No desde la interfaz, pero puede modificar el código R si tiene conocimientos técnicos.

**P: ¿Los gráficos se actualizan en tiempo real?**  
R: Sí, cualquier cambio en los filtros actualiza todas las visualizaciones automáticamente después de hacer clic en "Aplicar selección".

### 8.4. Sobre Exportación

**P: ¿En qué formato se descargan los archivos?**  
R: Tabla de especies en CSV (compatible con Excel) y captura de dashboard en PNG.

**P: ¿Puedo descargar los gráficos individualmente?**  
R: No directamente, pero puede tomar capturas de pantalla de cada gráfico.

**P: ¿El archivo PNG incluye el mapa completo?**  
R: Parcialmente. Debido a limitaciones técnicas, se recomienda capturar el mapa por separado.

### 8.5. Sobre Rendimiento

**P: ¿Cuánto tiempo tarda en cargar el dashboard?**  
R: Entre 2-10 segundos, dependiendo del tamaño de sus datos y la velocidad de su computadora.

**P: ¿Qué hago si el dashboard se congela?**  
R: Cierre el dashboard, reinicie RStudio y vuelva a abrir. Considere filtrar datos si el problema persiste.

**P: ¿Cuántos registros puede manejar el dashboard?**  
R: Hasta 500,000 observaciones funcionan bien. Para datasets más grandes, filtre en el pipeline Python primero.

---

## 9. Recursos Adicionales

### 9.1. Documentación Técnica Completa

Para información más detallada, consulte:

- **README.md**: Vista general del proyecto
- **INSTALL.md**: Guía de instalación completa
- **PIPELINE.md**: Documentación del procesamiento de datos en Python
- **ARCHITECTURE.md**: Arquitectura técnica del sistema
- **Dashboard_Vista_Corporaciones.md**: Documentación técnica del dashboard por CARs
- **DOC_Dashboard_Vista_Proyectos.md**: Documentación técnica del dashboard por proyectos

### 9.2. Contacto y Soporte

Para preguntas técnicas o reportar problemas:

**Instituto Alexander von Humboldt**  
Proyecto: Red OTUS Colombia  
Email: [contacto del proyecto]

### 9.3. Licencia

Este dashboard es software de dominio público bajo licencia **CC0 1.0 Universal**.

Puede usar, modificar y distribuir libremente este sistema para fines de conservación y educación ambiental.

---

## 10. Glosario de Términos

**CAR (Corporación Autónoma Regional)**: Entidad territorial responsable de la gestión ambiental en Colombia.

**Deployment**: Instalación individual de una cámara trampa en un sitio específico.

**Evento de muestreo**: Período temporal definido para el monitoreo (ejemplo: 2024_2 = segundo semestre de 2024).

**Intervalo de independencia**: Tiempo mínimo entre fotografías de la misma especie para considerarlas eventos separados.

**Números de Hill**: Índices de diversidad que ponderan la abundancia de especies de diferentes formas (q=0, q=1, q=2).

**Ocupación naive**: Porcentaje simple de sitios donde se detectó una especie (sin modelado estadístico complejo).

**Parquet**: Formato de archivo columnar optimizado para análisis de datos.

**Registros independientes**: Eventos únicos de detección de una especie, filtrados por el intervalo de independencia.

**Trampa/noche (días-cámara)**: Unidad de esfuerzo de muestreo equivalente a una cámara funcionando durante 24 horas.

**Wildlife Insights**: Plataforma global para almacenar y procesar datos de cámaras trampa.

---

**Fin del Manual de Operación**

---

*Documento generado para la Red OTUS Colombia - Instituto Alexander von Humboldt*  
*Versión 2.0 - Diciembre 2025*
