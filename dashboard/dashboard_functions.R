# Funciones del Dashboard Red OTUS 2026
# Lectura, validación y presentación del modelo de datos procesado.
# Desarrollo: Cristian C. Acevedo, Ingeniero de Soluciones.
# Supervisión: Angélica Diaz Pulido, Investigador Adjunto, Centro Estudios
# Socioecológicos y Cambio Global, Dirección de Conocimiento,
# Instituto de Investigación de Recursos Biológicos Alexander von Humboldt.
# Versión: v2026.1.0. Licencia: MIT; consulte LICENSE en la raíz del proyecto.

# ===============================================================================
# LIBRERÍAS REQUERIDAS
# ===============================================================================

.dashboard_function_packages <- c(
  "arrow", "dplyr", "ggplot2", "htmltools", "leaflet", "lubridate",
  "jsonlite", "openxlsx", "plotly", "scales", "tzdb", "zip"
)
.dashboard_missing_packages <- .dashboard_function_packages[
  !vapply(.dashboard_function_packages, requireNamespace, logical(1), quietly = TRUE)
]

if (length(.dashboard_missing_packages) > 0) {
  stop(
    "Faltan paquetes requeridos por dashboard_functions.R: ",
    paste(.dashboard_missing_packages, collapse = ", "),
    ". Instálelos antes de iniciar el dashboard.",
    call. = FALSE
  )
}

if (!("America/Bogota" %in% tzdb::tzdb_names())) {
  stop("La base de zonas horarias no contiene America/Bogota.", call. = FALSE)
}

suppressPackageStartupMessages({
  library(dplyr)
  library(ggplot2)
  library(leaflet)
  library(plotly)
})

rm(.dashboard_function_packages, .dashboard_missing_packages)

# Una ocasión de muestreo corresponde a una semana consecutiva. Esta constante
# también se replica en el procesamiento Python para mantener ambos cálculos
# alineados cuando el dashboard debe usar la ruta de cálculo de respaldo.
OCCASION_WINDOW_DAYS <- 7L

reparar_relaciones_excel <- function(file) {
  #' Elimina relaciones vacías creadas por algunas versiones de openxlsx.
  file <- normalizePath(file, winslash = "/", mustWork = TRUE)
  destino <- tempfile("red_otus_xlsx_")
  dir.create(destino)
  on.exit(unlink(destino, recursive = TRUE, force = TRUE), add = TRUE)
  utils::unzip(file, exdir = destino)

  dibujos <- file.path(destino, "xl", "drawings")
  tiene_dibujos <- dir.exists(dibujos) && length(list.files(dibujos, all.files = FALSE)) > 0
  if (tiene_dibujos) return(invisible(file))

  relaciones <- list.files(
    file.path(destino, "xl", "worksheets", "_rels"),
    pattern = "[.]rels$", full.names = TRUE
  )
  for (ruta in relaciones) {
    xml <- paste(readLines(ruta, warn = FALSE, encoding = "UTF-8"), collapse = "")
    xml <- gsub(
      '<Relationship Id="[^"]+" Type="[^"]+/(drawing|vmlDrawing)" Target="[^"]+"/>',
      "", xml, perl = TRUE
    )
    writeLines(xml, ruta, useBytes = TRUE)
  }

  hojas <- list.files(
    file.path(destino, "xl", "worksheets"),
    pattern = "^sheet[0-9]+[.]xml$", full.names = TRUE
  )
  for (ruta in hojas) {
    xml <- paste(readLines(ruta, warn = FALSE, encoding = "UTF-8"), collapse = "")
    xml <- gsub('<(drawing|legacyDrawing) r:id="[^"]+"/>', "", xml, perl = TRUE)
    writeLines(xml, ruta, useBytes = TRUE)
  }

  archivos <- list.files(destino, recursive = TRUE, all.files = TRUE, no.. = TRUE)
  unlink(file)
  zip::zipr(file, archivos, root = destino, mode = "mirror")
  invisible(file)
}

writeVisualizationWorkbook <- function(sheets, file) {
  #' Escribe el libro Excel consolidado de las visualizaciones.
  #'
  #' @param sheets Lista nombrada de data frames, uno por hoja.
  #' @param file Ruta de salida `.xlsx`.
  #' @return Ruta de salida, de forma invisible.
  if (!is.list(sheets) || length(sheets) == 0 || is.null(names(sheets)) ||
      any(!nzchar(names(sheets)))) {
    stop("`sheets` debe ser una lista nombrada de data frames.", call. = FALSE)
  }

  sheets <- lapply(sheets, function(data) {
    if (is.null(data) || !is.data.frame(data) || nrow(data) == 0) {
      data.frame(Mensaje = "No hay datos disponibles para el filtro aplicado")
    } else {
      data
    }
  })

  workbook <- openxlsx::createWorkbook(creator = "Red OTUS")
  percent_style <- openxlsx::createStyle(numFmt = "0.00%")
  datetime_style <- openxlsx::createStyle(numFmt = "yyyy-mm-dd hh:mm:ss")

  for (sheet_name in names(sheets)) {
    sheet_data <- sheets[[sheet_name]]
    openxlsx::addWorksheet(workbook, sheet_name, gridLines = FALSE)
    openxlsx::writeDataTable(
      workbook, sheet_name, sheet_data,
      tableStyle = "TableStyleMedium2", withFilter = TRUE
    )
    openxlsx::freezePane(workbook, sheet_name, firstRow = TRUE)
    openxlsx::setColWidths(workbook, sheet_name, cols = seq_along(sheet_data), widths = "auto")

    if ("Valor" %in% names(sheet_data)) {
      openxlsx::addStyle(
        workbook, sheet_name, percent_style,
        rows = 2:(nrow(sheet_data) + 1), cols = match("Valor", names(sheet_data)),
        gridExpand = TRUE, stack = TRUE
      )
    }
    if ("Fecha_hora" %in% names(sheet_data)) {
      openxlsx::addStyle(
        workbook, sheet_name, datetime_style,
        rows = 2:(nrow(sheet_data) + 1), cols = match("Fecha_hora", names(sheet_data)),
        gridExpand = TRUE, stack = TRUE
      )
    }
  }

  openxlsx::saveWorkbook(workbook, file, overwrite = TRUE)
  reparar_relaciones_excel(file)
  invisible(file)
}

# ===============================================================================
# FUNCIONES AUXILIARES
# ===============================================================================

texto_entidad_articulo <- function(modo) {
  if (identical(modo, "corporaciones")) "una corporación" else "un proyecto"
}

valor_todos_entidad <- function(modo) {
  if (identical(modo, "corporaciones")) "TODAS" else "TODOS"
}

etiqueta_todos_entidad <- function(modo) {
  if (identical(modo, "corporaciones")) "Todas las corporaciones" else "Todos los proyectos"
}

configurar_intervalo_independencia <- function(valor = "30min") {
  configuraciones <- list(
    "sin_filtro" = list(interval = 0, unit = "minutes", label = "Sin filtro temporal"),
    "30min" = list(interval = 30, unit = "minutes", label = "30 minutos"),
    "1h" = list(interval = 1, unit = "hours", label = "1 hora"),
    "24h" = list(interval = 24, unit = "hours", label = "24 horas")
  )

  if (is.null(valor) || length(valor) == 0 || is.na(valor[[1]])) {
    valor <- "30min"
  }
  valor <- as.character(valor[[1]])
  if (!valor %in% names(configuraciones)) {
    valor <- "30min"
  }
  configuraciones[[valor]]
}

memoria_r_mb <- function() {
  memoria <- gc(verbose = FALSE)
  round(sum(memoria[, "used"] * c(56, 8)) / 1024^2, 2)
}

fecha_corte_dashboard <- function() {
  valor <- getOption("red_otus.fecha_corte", Sys.Date())
  fecha <- suppressWarnings(as.Date(valor))
  if (length(fecha) != 1 || is.na(fecha)) Sys.Date() else fecha
}

depurar_fechas_dashboard <- function(observaciones, deployments, fecha_corte = fecha_corte_dashboard()) {
  #' Aplica controles temporales sin modificar los archivos Parquet.
  fecha_corte <- as.Date(fecha_corte)
  fechas_obs <- suppressWarnings(as.Date(observaciones$photo_datetime))
  anio_evento <- suppressWarnings(as.integer(sub("_.*$", "", observaciones$subproject_name)))
  anio_obs <- suppressWarnings(as.integer(format(fechas_obs, "%Y")))

  fecha_invalida <- is.na(fechas_obs)
  fecha_futura <- !fecha_invalida & fechas_obs > fecha_corte
  fuera_evento <- !fecha_invalida & !is.na(anio_evento) &
    (anio_obs < anio_evento - 1L | anio_obs > anio_evento + 1L)
  excluir_obs <- fecha_invalida | fecha_futura

  inicio <- suppressWarnings(as.Date(deployments$start_date))
  fin <- suppressWarnings(as.Date(deployments$end_date))
  orden_invalido <- !is.na(inicio) & !is.na(fin) & fin < inicio
  inicio_futuro <- !is.na(inicio) & inicio > fecha_corte
  fin_futuro <- !is.na(fin) & fin > fecha_corte
  excluir_dep <- orden_invalido | inicio_futuro

  resumen <- c(
    observaciones_entrada = nrow(observaciones),
    observaciones_fecha_invalida = sum(fecha_invalida),
    observaciones_futuras = sum(fecha_futura),
    observaciones_fuera_evento_advertidas = sum(fuera_evento & !fecha_futura),
    observaciones_excluidas = sum(excluir_obs),
    deployments_entrada = nrow(deployments),
    deployments_orden_invalido = sum(orden_invalido),
    deployments_inicio_futuro = sum(inicio_futuro),
    deployments_fin_futuro_acotado = sum(fin_futuro & !excluir_dep),
    deployments_excluidos = sum(excluir_dep)
  )

  if (isTRUE(getOption("red_otus.warn_quality", TRUE)) &&
      (resumen[["observaciones_excluidas"]] > 0 ||
      resumen[["observaciones_fuera_evento_advertidas"]] > 0 ||
      resumen[["deployments_excluidos"]] > 0 ||
      resumen[["deployments_fin_futuro_acotado"]] > 0)) {
    warning(
      sprintf(
        paste0(
          "Control temporal aplicado (corte %s): %d observaciones excluidas ",
          "(%d futuras y %d inválidas); %d observaciones adicionales fuera ",
          "del rango esperado del evento permanecen marcadas para revisión; ",
          "%d deployments excluidos y %d fechas finales acotadas."
        ),
        fecha_corte, resumen[["observaciones_excluidas"]],
        resumen[["observaciones_futuras"]], resumen[["observaciones_fecha_invalida"]],
        resumen[["observaciones_fuera_evento_advertidas"]], resumen[["deployments_excluidos"]],
        resumen[["deployments_fin_futuro_acotado"]]
      ),
      call. = FALSE
    )
  }

  deployments$start_date <- inicio
  deployments$end_date <- fin
  deployments$end_date[fin_futuro & !excluir_dep] <- fecha_corte

  list(
    observaciones = observaciones[!excluir_obs, , drop = FALSE],
    deployments = deployments[!excluir_dep, , drop = FALSE],
    resumen = resumen
  )
}

tamano_objeto_mb <- function(objeto) {
  round(as.numeric(utils::object.size(objeto)) / 1024^2, 2)
}

imprimir_reporte_rendimiento <- function(
    contexto,
    inicio,
    cpu_inicio,
    memoria_inicio,
    hitos,
    datos) {
  fin <- Sys.time()
  cpu_fin <- proc.time()
  transcurrido <- max(as.numeric(difftime(fin, inicio, units = "secs")), .Machine$double.eps)
  cpu_usuario <- unname(cpu_fin[["user.self"]] - cpu_inicio[["user.self"]])
  cpu_sistema <- unname(cpu_fin[["sys.self"]] - cpu_inicio[["sys.self"]])
  cpu_promedio <- 100 * (cpu_usuario + cpu_sistema) / transcurrido
  memoria_fin <- memoria_r_mb()

  contar_unicos <- function(data, columna) {
    if (is.null(data) || nrow(data) == 0 || !columna %in% names(data)) return(0L)
    valores <- data[[columna]]
    length(unique(valores[!is.na(valores)]))
  }
  filas <- function(data) if (is.null(data)) 0L else nrow(data)

  cat("\n", strrep("=", 72), "\n", sep = "")
  cat("REPORTE DE RENDIMIENTO · DASHBOARD RED OTUS\n")
  cat(strrep("-", 72), "\n", sep = "")
  cat(sprintf("Ejecución:       %s\n", format(inicio, "%Y-%m-%d %H:%M:%S")))
  cat(sprintf("Vista:           %s\n", contexto$vista))
  cat(sprintf("Entidad:         %s\n", contexto$entidad))
  cat(sprintf("Evento:          %s\n", contexto$evento))
  cat(sprintf("Independencia:   %s\n", contexto$intervalo))
  cat(sprintf("Tiempo total:    %.2f s\n", transcurrido))
  cat(sprintf("CPU R:           %.2f s usuario · %.2f s sistema · %.1f%% promedio estimado\n",
              cpu_usuario, cpu_sistema, cpu_promedio))
  cat(sprintf("Memoria R:       %.2f MB inicial · %.2f MB final · %+.2f MB\n",
              memoria_inicio, memoria_fin, memoria_fin - memoria_inicio))
  entero <- function(valor) {
    format(valor, big.mark = ".", decimal.mark = ",", scientific = FALSE, trim = TRUE)
  }
  cat(sprintf("Datos filtrados: %s observaciones · %s instalaciones\n",
              entero(filas(datos$observaciones)),
              entero(filas(datos$sitios))))
  cat(sprintf("Cobertura:       %d proyectos · %d eventos · %d especies\n",
              contar_unicos(datos$observaciones, "project_id"),
              contar_unicos(datos$observaciones, "subproject_name"),
              contar_unicos(datos$observaciones, "sp_binomial")))
  cat(sprintf("Resultados:      %s filas en ranking · %s filas en indicadores\n",
              entero(filas(datos$ranking)), entero(filas(datos$indicadores))))
  cat(sprintf("Objetos medidos: %.2f MB\n", sum(vapply(datos, tamano_objeto_mb, numeric(1)))))
  if (length(hitos) > 0) {
    orden <- order(unlist(hitos))
    detalle <- paste(
      sprintf("%s %.2fs", names(hitos)[orden], unlist(hitos)[orden]),
      collapse = " · "
    )
    cat("Hitos:           ", detalle, "\n", sep = "")
  }
  cat(sprintf("Proceso R:       PID %d · R %s\n", Sys.getpid(), getRversion()))
  cat(strrep("=", 72), "\n\n", sep = "")

  invisible(list(
    elapsed_seconds = transcurrido,
    cpu_user_seconds = cpu_usuario,
    cpu_system_seconds = cpu_sistema,
    estimated_cpu_percent = cpu_promedio,
    memory_start_mb = memoria_inicio,
    memory_end_mb = memoria_fin
  ))
}

formatear_fecha_es <- function(fecha) {
  fecha <- suppressWarnings(as.Date(fecha))
  if (length(fecha) == 0 || is.na(fecha[[1]])) {
    return("–")
  }

  meses <- c(
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
  )
  paste0(
    format(fecha[[1]], "%Y"), ", ", as.integer(format(fecha[[1]], "%d")),
    " de ", meses[[as.integer(format(fecha[[1]], "%m"))]]
  )
}

es_seleccion_global_entidad <- function(valor, modo) {
  is.null(valor) || length(valor) == 0 || is.na(valor[[1]]) ||
    !nzchar(as.character(valor[[1]])) ||
    identical(as.character(valor[[1]]), valor_todos_entidad(modo))
}

# Localiza las fotografías destacadas según el alcance aplicado en la vista.
# Las vistas globales usan exclusivamente la carpeta General; una vista de
# proyecto usa su project_id y una vista de corporación reúne las carpetas de
# los proyectos que forman parte de la selección filtrada.
listar_imagenes_galeria <- function(
  favorites_root,
  modo,
  entidad,
  project_ids = character(0),
  pattern = "\\.(jpe?g|png)$"
) {
  listar_carpeta <- function(folder) {
    if (!dir.exists(folder)) return(character(0))
    sort(list.files(
      folder,
      pattern = pattern,
      ignore.case = TRUE,
      recursive = FALSE,
      full.names = TRUE
    ))
  }

  if (es_seleccion_global_entidad(entidad, modo)) {
    return(listar_carpeta(file.path(favorites_root, "General")))
  }

  if (identical(modo, "proyectos")) {
    return(listar_carpeta(file.path(favorites_root, as.character(entidad))))
  }

  project_ids <- sort(unique(as.character(project_ids)))
  project_ids <- project_ids[!is.na(project_ids) & nzchar(project_ids)]
  if (length(project_ids) == 0) return(character(0))

  unname(unlist(
    lapply(project_ids, function(project_id) {
      listar_carpeta(file.path(favorites_root, project_id))
    }),
    use.names = FALSE
  ))
}

# Resume la disponibilidad de fotografías destacadas para cada proyecto
# publicado. Se utiliza al iniciar la aplicación para advertir carpetas faltantes
# y mostrar cuántas imágenes reconoce la galería en cada project_id.
inventariar_imagenes_proyectos <- function(
  proyectos,
  favorites_root,
  pattern = "\\.(jpe?g|png)$"
) {
  columnas <- c("project_id", "project_short_name")
  if (is.null(proyectos) || nrow(proyectos) == 0 ||
      !all(columnas %in% names(proyectos))) {
    return(data.frame(
      project_id = character(0), project_short_name = character(0),
      image_count = integer(0), stringsAsFactors = FALSE
    ))
  }

  catalogo <- unique(data.frame(
    project_id = as.character(proyectos$project_id),
    project_short_name = as.character(proyectos$project_short_name),
    stringsAsFactors = FALSE
  ))
  catalogo <- catalogo[
    !is.na(catalogo$project_id) & nzchar(catalogo$project_id),
    , drop = FALSE
  ]
  catalogo$project_short_name[
    is.na(catalogo$project_short_name) | !nzchar(catalogo$project_short_name)
  ] <- "Proyecto sin nombre"
  catalogo <- catalogo[!duplicated(catalogo$project_id), , drop = FALSE]
  catalogo <- catalogo[order(catalogo$project_id), , drop = FALSE]

  catalogo$image_count <- vapply(catalogo$project_id, function(project_id) {
    carpeta <- file.path(favorites_root, project_id)
    if (!dir.exists(carpeta)) return(0L)
    as.integer(length(list.files(
      carpeta,
      pattern = pattern,
      ignore.case = TRUE,
      recursive = FALSE,
      full.names = FALSE
    )))
  }, integer(1))
  rownames(catalogo) <- NULL
  catalogo
}

es_seleccion_global_evento <- function(valor) {
  is.null(valor) || length(valor) == 0 || is.na(valor[[1]]) ||
    !nzchar(as.character(valor[[1]])) || identical(as.character(valor[[1]]), "TODOS")
}

filtrar_datos_dashboard <- function(
    datos,
    modo,
    entidad = "",
    evento = "",
    columna_corporacion = "Corporacion") {
  if (is.null(datos) || nrow(datos) == 0) {
    return(datos)
  }

  if (!modo %in% c("corporaciones", "proyectos")) {
    stop("Modo de visualización no reconocido: ", modo, call. = FALSE)
  }

  resultado <- datos

  if (!es_seleccion_global_entidad(entidad, modo)) {
    if (identical(modo, "corporaciones")) {
      if (!columna_corporacion %in% names(resultado)) {
        stop("Falta la columna requerida: ", columna_corporacion, call. = FALSE)
      }
      mantener <- !is.na(resultado[[columna_corporacion]]) &
        as.character(resultado[[columna_corporacion]]) == as.character(entidad)
      resultado <- resultado[mantener, , drop = FALSE]
    } else {
      if (!"project_id" %in% names(resultado)) {
        stop("Falta la columna requerida: project_id", call. = FALSE)
      }
      # Comparar como texto evita pérdida de precisión y admite IDs numéricos
      # o alfanuméricos sin duplicar lógica de conversión.
      mantener <- !is.na(resultado$project_id) &
        as.character(resultado$project_id) == as.character(entidad)
      resultado <- resultado[mantener, , drop = FALSE]
    }
  }

  if (!es_seleccion_global_evento(evento)) {
    if (!"subproject_name" %in% names(resultado)) {
      stop("Falta la columna requerida: subproject_name", call. = FALSE)
    }
    mantener <- !is.na(resultado$subproject_name) &
      as.character(resultado$subproject_name) == as.character(evento)
    resultado <- resultado[mantener, , drop = FALSE]
  }

  resultado
}

obtener_eventos_entidad <- function(datos, modo, entidad) {
  if (is.null(entidad) || length(entidad) != 1 || is.na(entidad) || !nzchar(entidad)) {
    return(character(0))
  }
  datos_entidad <- filtrar_datos_dashboard(
    datos,
    modo = modo,
    entidad = entidad,
    evento = "TODOS",
    columna_corporacion = "Corporacion"
  )
  if (is.null(datos_entidad) || nrow(datos_entidad) == 0 ||
      !"subproject_name" %in% names(datos_entidad)) {
    return(character(0))
  }
  eventos <- unique(as.character(datos_entidad$subproject_name))
  sort(eventos[!is.na(eventos) & nzchar(eventos)], decreasing = TRUE)
}

componente_nombre_archivo <- function(valor, valor_global) {
  if (is.null(valor) || length(valor) == 0 || is.na(valor[[1]]) ||
      !nzchar(as.character(valor[[1]]))) {
    return(valor_global)
  }

  limpio <- iconv(as.character(valor[[1]]), from = "", to = "ASCII//TRANSLIT")
  if (is.na(limpio)) {
    limpio <- as.character(valor[[1]])
  }
  # Conservar espacios y guiones legibles, pero retirar caracteres no válidos
  # en nombres de archivo de Windows y otros sistemas operativos.
  limpio <- gsub("[<>:\"/\\\\|?*]", "_", limpio)
  limpio <- gsub("[[:cntrl:]]", "", limpio)
  limpio <- gsub("[[:space:]]+", " ", limpio)
  limpio <- gsub("_+", "_", limpio)
  limpio <- trimws(limpio)
  limpio <- sub("[. ]+$", "", limpio)

  if (nzchar(limpio)) limpio else valor_global
}

normalizar_encabezados_csv <- function(datos) {
  #' Retira tildes de los encabezados sin modificar los valores de la tabla.
  #'
  #' Los datos se conservan en UTF-8; esta normalización evita que programas
  #' que ignoran la codificación muestren encabezados como "ImÃ¡genes".
  resultado <- datos
  encabezados <- iconv(names(resultado), from = "UTF-8", to = "ASCII//TRANSLIT")
  encabezados[is.na(encabezados)] <- names(resultado)[is.na(encabezados)]
  names(resultado) <- encabezados
  resultado
}

preparar_ranking_para_exportacion <- function(datos) {
  #' Sustituye los NA analíticos por mensajes que explican su causa.
  #'
  #' La diurnalidad ausente representa una especie sin detecciones en el
  #' evento. Una frecuencia ausente indica que las detecciones no pudieron
  #' ubicarse dentro del periodo válido de instalación de la cámara.
  resultado <- datos
  columnas_diurnalidad <- grep("^Diurnalidad ", names(resultado), value = TRUE)
  columnas_frecuencia <- grep("^Frecuencia ", names(resultado), value = TRUE)

  convertir_columna <- function(valores, mensaje) {
    faltantes <- is.na(valores) | !is.finite(as.numeric(valores))
    texto <- format(
      as.numeric(valores),
      trim = TRUE,
      scientific = FALSE,
      decimal.mark = ",",
      digits = 15
    )
    texto[faltantes] <- mensaje
    texto
  }

  for (columna in columnas_diurnalidad) {
    resultado[[columna]] <- convertir_columna(
      resultado[[columna]], "Sin detecciones en el evento"
    )
  }
  for (columna in columnas_frecuencia) {
    resultado[[columna]] <- convertir_columna(
      resultado[[columna]], "Revisar fechas de instalación"
    )
  }
  resultado
}

escribir_csv_excel <- function(datos, archivo, sep = ";", dec = ",", na = "") {
  #' Escribe un CSV UTF-8 con BOM para su apertura directa en Excel.
  datos <- normalizar_encabezados_csv(datos)
  temporal <- tempfile(fileext = ".csv")
  on.exit(unlink(temporal), add = TRUE)

  utils::write.table(
    datos,
    temporal,
    sep = sep,
    dec = dec,
    quote = FALSE,
    col.names = TRUE,
    row.names = FALSE,
    fileEncoding = "UTF-8",
    na = na
  )

  tamano <- file.info(temporal)$size
  contenido <- readBin(temporal, what = "raw", n = tamano)
  conexion <- file(archivo, open = "wb")
  on.exit(close(conexion), add = TRUE)
  writeBin(c(as.raw(c(0xEF, 0xBB, 0xBF)), contenido), conexion)
  invisible(archivo)
}

etiqueta_intervalo_archivo <- function(valor) {
  switch(
    as.character(valor),
    sin_filtro = "sin_filtro",
    `30min` = "30min",
    `1h` = "1h",
    `24h` = "24h",
    "intervalo"
  )
}

construir_nombre_descarga <- function(
  seccion,
  entidad,
  evento,
  intervalo,
  extension,
  fecha = Sys.time()
) {
  #' Construye nombres de descarga descriptivos y seguros.
  partes <- c(
    componente_nombre_archivo(seccion, "Archivo"),
    componente_nombre_archivo(entidad, "Entidad"),
    componente_nombre_archivo(evento, "Evento"),
    etiqueta_intervalo_archivo(intervalo),
    format(fecha, "%d_%m_%Y"),
    format(fecha, "%H_%M")
  )
  paste0(paste(partes, collapse = "-"), ".", sub("^\\.", "", extension))
}

validar_columnas <- function(datos, columnas, nombre_datos) {
  faltantes <- setdiff(columnas, names(datos))
  if (length(faltantes) > 0) {
    stop(
      "El archivo ", nombre_datos, " no cumple el esquema requerido. Faltan: ",
      paste(faltantes, collapse = ", "),
      call. = FALSE
    )
  }
  invisible(TRUE)
}

extract_date_ymd <- function(df) {
  #' Extrae fechas de timestamps de Wildlife Insights
  #'
  #' Convierte timestamps en formato ISO 8601 a objetos Date de R,
  #' eliminando información de hora y zona horaria.
  #'
  #' @param df DataFrame con columnas 'photo_datetime' o 'date'
  #'
  #' @return Vector de objetos Date en formato YYYY-MM-DD
  #'
  #' @examples
  #' extract_date_ymd(df_images)
  #'
  
  col <- if ("photo_datetime" %in% names(df)) df$photo_datetime
  else if ("date" %in% names(df)) df$date
  else return(as.Date(character()))
  
  x <- as.character(col)
  # Conserva solo 'YYYY-MM-DD' (elimina hora, 'T', etc.)
  x <- sub("[ T].*$", "", x)
  suppressWarnings(as.Date(x))
}

consolidar_estadisticas_sitios <- function(tableSites, nombre_proyecto) {
  #' Agrega estadísticas de múltiples sitios
  #'
  #' Consolida métricas operacionales y de biodiversidad de todos los sitios
  #' de una vista (corporación/evento o proyecto/evento), generando totales
  #' agregados para ambas vistas.
  #'
  #' @param tableSites DataFrame con columnas: n, ndepl, effort, ospTot, etc.
  #' @param nombre_proyecto String identificador de la vista (corporación o
  #'        proyecto, combinado con el evento de muestreo)
  #'
  #' @return DataFrame con fila única de totales consolidados
  #'
  #' @details
  #' Filtra registros válidos (n > 0) y suma:
  #'   - Imágenes totales
  #'   - Número de deployments
  #'   - Días-cámara acumulados
  #'   - Especies totales (Mammalia, Aves, Total)
  #'
  # Incluir cámaras válidas sin detecciones: aportan al esfuerzo y al
  # denominador de ocupación aunque su conteo de imágenes sea cero.
  datos_validos <- tableSites[!is.na(tableSites$n) & tableSites$n >= 0, ]

  if (nrow(datos_validos) == 0) {
    # Retornar estructura vacía con valores por defecto
    return(data.frame(
      project_short_name = nombre_proyecto,
      site_name = "Consolidado",
      n = 0,
      ndepl = 0,
      effort = 0,
      ospTot = 0,
      ospMamiferos = 0,
      ospAves = 0,
      # Rankings (valores por defecto)
      rank_images = 1,
      rank_ndepl = 1,
      rank_effort = 1,
      rank_onsp = 1,
      rank_onMamiferos = 1,
      rank_onAves = 1,
      collector = "Múltiples",
      departamento = "Colombia",
      stringsAsFactors = FALSE
    ))
  }

  consolidado <- data.frame(
    project_short_name = nombre_proyecto,
    site_name = "Consolidado",
    n = sum(datos_validos$n, na.rm = TRUE),
    ndepl = sum(datos_validos$ndepl, na.rm = TRUE),
    effort = sum(datos_validos$effort, na.rm = TRUE),
    ospTot = sum(datos_validos$ospTot, na.rm = TRUE),
    ospMamiferos = sum(datos_validos$ospMamiferos, na.rm = TRUE),
    ospAves = sum(datos_validos$ospAves, na.rm = TRUE),
    rank_images = 1,
    rank_ndepl = 1,
    rank_effort = 1,
    rank_onsp = 1,
    rank_onMamiferos = 1,
    rank_onAves = 1,
    collector = nombre_proyecto,
    departamento = paste(unique(datos_validos$departamento[!is.na(datos_validos$departamento)]), collapse = ", "),
    stringsAsFactors = FALSE
  )

  return(consolidado)
}

# ===============================================================================
# FUNCIONES DE VISUALIZACIÓN Y ANÁLISIS
# ===============================================================================

makeSpeciesTable <- function(subset, deployments, interval = 30, unit = "minutes") {
  #' Genera el ranking taxonómico y las métricas por evento de cada especie.
  #'
  #' @param subset Observaciones ya filtradas por entidad y evento.
  #' @param deployments Instalaciones ya filtradas por la misma entidad/evento.
  #' @param interval Intervalo usado para definir registros independientes.
  #' @param unit Unidad del intervalo (`minutes` u `hours`).
  #'
  #' @return Data frame con taxonomía, abundancia y, por evento, ocupación,
  #'   frecuencia de detección por ocasiones de 7 días y diurnalidad media.

  columnas_base <- data.frame(
    Ranking = integer(), Especie = character(), Clase = character(),
    Orden = character(), Familia = character(), Genero = character(),
    "Numero imagenes" = integer(), "Registros independientes" = integer(),
    stringsAsFactors = FALSE, check.names = FALSE
  )
  if (is.null(subset) || nrow(subset) == 0) return(columnas_base)

  validar_columnas(
    subset,
    c(
      "project_id", "subproject_name", "deployment_name", "photo_datetime",
      "sp_binomial", "class", "order", "family", "genus"
    ),
    "fact_observation.parquet (datos filtrados)"
  )
  validar_columnas(
    deployments,
    c("project_id", "subproject_name", "deployment_name", "start_date", "end_date"),
    "dim_deployment.parquet (datos filtrados)"
  )

  primer_valor_valido <- function(x) {
    x <- as.character(x)
    x <- x[!is.na(x) & nzchar(x)]
    if (length(x) == 0) "Sin informacion" else x[[1]]
  }
  clave_deployment <- function(project_id, evento, deployment_name) {
    paste(as.character(project_id), as.character(evento), as.character(deployment_name), sep = "||")
  }

  datos <- subset %>%
    dplyr::filter(!is.na(sp_binomial), nzchar(as.character(sp_binomial))) %>%
    dplyr::mutate(
      sp_binomial = as.character(sp_binomial),
      subproject_name = as.character(subproject_name),
      deployment_name = as.character(deployment_name),
      .deployment_key = clave_deployment(project_id, subproject_name, deployment_name)
    )
  if (nrow(datos) == 0) return(columnas_base)

  datos_independientes <- suppressMessages(
    remove_duplicates(datos, interval = interval, unit = unit)
  )

  taxonomia <- datos %>%
    dplyr::group_by(sp_binomial) %>%
    dplyr::summarise(
      Clase = primer_valor_valido(class),
      Orden = primer_valor_valido(order),
      Familia = primer_valor_valido(family),
      Genero = primer_valor_valido(genus),
      .groups = "drop"
    )
  imagenes <- datos %>%
    dplyr::count(sp_binomial, name = "Numero imagenes")
  independientes <- datos_independientes %>%
    dplyr::count(sp_binomial, name = "Registros independientes")

  resultado <- independientes %>%
    dplyr::left_join(imagenes, by = "sp_binomial") %>%
    dplyr::left_join(taxonomia, by = "sp_binomial") %>%
    dplyr::arrange(dplyr::desc(.data[["Registros independientes"]]), sp_binomial) %>%
    dplyr::transmute(
      Ranking = dplyr::row_number(), Especie = sp_binomial,
      Clase, Orden, Familia, Genero,
      "Numero imagenes" = .data[["Numero imagenes"]],
      "Registros independientes" = .data[["Registros independientes"]]
    )

  deployments_normalizados <- deployments %>%
    dplyr::mutate(
      subproject_name = as.character(subproject_name),
      deployment_name = as.character(deployment_name),
      start_date = suppressWarnings(as.Date(start_date)),
      end_date = suppressWarnings(as.Date(end_date)),
      .deployment_key = clave_deployment(project_id, subproject_name, deployment_name)
    ) %>%
    dplyr::group_by(.deployment_key, subproject_name) %>%
    dplyr::summarise(
      start_date = if (all(is.na(start_date))) as.Date(NA) else min(start_date, na.rm = TRUE),
      end_date = if (all(is.na(end_date))) as.Date(NA) else max(end_date, na.rm = TRUE),
      .groups = "drop"
    )

  eventos <- sort(unique(datos$subproject_name[!is.na(datos$subproject_name) & nzchar(datos$subproject_name)]), decreasing = TRUE)
  for (evento in eventos) {
    datos_evento <- datos %>% dplyr::filter(subproject_name == evento)
    independientes_evento <- datos_independientes %>%
      dplyr::filter(as.character(subproject_name) == evento)

    deployments_evento <- deployments_normalizados %>%
      dplyr::filter(
        subproject_name == evento,
        !is.na(start_date),
        !is.na(end_date),
        end_date >= start_date
      )
    total_sitios <- dplyr::n_distinct(deployments_evento$.deployment_key)
    ocupacion <- independientes_evento %>%
      dplyr::group_by(sp_binomial) %>%
      dplyr::summarise(
        valor = if (total_sitios > 0) {
          dplyr::n_distinct(.deployment_key) / total_sitios
        } else {
          NA_real_
        },
        .groups = "drop"
      )

    registros_deployment <- independientes_evento %>%
      dplyr::mutate(
        photo_datetime = as.POSIXct(photo_datetime),
        photo_date = as.Date(photo_datetime)
      ) %>%
      dplyr::left_join(
        deployments_normalizados %>% dplyr::filter(subproject_name == evento),
        by = c(".deployment_key", "subproject_name")
      ) %>%
      dplyr::filter(
        !is.na(start_date), !is.na(end_date), end_date >= start_date,
        !is.na(photo_date), photo_date >= start_date, photo_date <= end_date
      ) %>%
      dplyr::mutate(
        total_ocasiones = pmax(
          1L,
          ceiling((as.numeric(end_date - start_date) + 1) / OCCASION_WINDOW_DAYS)
        ),
        ocasion = floor(
          as.numeric(photo_date - start_date) / OCCASION_WINDOW_DAYS
        ) + 1L
      )

    denominadores <- registros_deployment %>%
      dplyr::distinct(sp_binomial, .deployment_key, total_ocasiones) %>%
      dplyr::group_by(sp_binomial) %>%
      dplyr::summarise(total_ocasiones = sum(total_ocasiones), .groups = "drop")
    numeradores <- registros_deployment %>%
      dplyr::filter(ocasion >= 1, ocasion <= total_ocasiones) %>%
      dplyr::distinct(sp_binomial, .deployment_key, ocasion) %>%
      dplyr::count(sp_binomial, name = "ocasiones_deteccion")
    frecuencia <- denominadores %>%
      dplyr::left_join(numeradores, by = "sp_binomial") %>%
      dplyr::mutate(
        ocasiones_deteccion = dplyr::coalesce(ocasiones_deteccion, 0L),
        valor = ocasiones_deteccion / total_ocasiones
      ) %>%
      dplyr::select(sp_binomial, valor)

    diurnalidad <- independientes_evento %>%
      dplyr::mutate(
        photo_datetime = as.POSIXct(photo_datetime),
        fecha = as.Date(photo_datetime),
        es_diurno = lubridate::hour(photo_datetime) >= 6 & lubridate::hour(photo_datetime) < 18
      ) %>%
      dplyr::filter(!is.na(fecha)) %>%
      dplyr::group_by(sp_binomial, fecha) %>%
      dplyr::summarise(proporcion_diaria = mean(es_diurno), .groups = "drop") %>%
      dplyr::group_by(sp_binomial) %>%
      dplyr::summarise(valor = mean(proporcion_diaria), .groups = "drop")

    metricas_evento <- stats::setNames(
      list(ocupacion, frecuencia, diurnalidad),
      c(
        paste0("Ocupaci\u00f3n ", evento),
        paste0("Frecuencia ", evento),
        paste0("Diurnalidad ", evento)
      )
    )
    for (nombre_columna in names(metricas_evento)) {
      metrica <- metricas_evento[[nombre_columna]]
      names(metrica)[names(metrica) == "valor"] <- nombre_columna
      resultado <- resultado %>% dplyr::left_join(metrica, by = c("Especie" = "sp_binomial"))
    }
  }

  names(resultado)[names(resultado) == "Genero"] <- "G\u00e9nero"
  resultado
}

# ===============================================================================
# GRÁFICOS COMPARATIVOS DE OCUPACIÓN Y DIURNALIDAD
# ===============================================================================

ordenar_eventos_cronologicamente <- function(eventos) {
  #' Ordena identificadores de evento desde el periodo más antiguo al más reciente.
  #'
  #' Reconoce el formato operativo AAAA_N y conserva un orden estable para otros
  #' nombres que incluyan un año de cuatro dígitos.
  eventos <- unique(as.character(eventos))
  if (length(eventos) <= 1) return(eventos)

  coincidencias <- regexec(
    "((?:19|20)[0-9]{2})(?:[^0-9]+([0-9]+))?",
    eventos,
    perl = TRUE
  )
  partes <- regmatches(eventos, coincidencias)
  anio <- vapply(partes, function(valor) {
    if (length(valor) >= 2) suppressWarnings(as.integer(valor[[2]])) else NA_integer_
  }, integer(1))
  periodo <- vapply(partes, function(valor) {
    if (length(valor) >= 3 && nzchar(valor[[3]])) {
      suppressWarnings(as.integer(valor[[3]]))
    } else {
      0L
    }
  }, integer(1))

  eventos[order(is.na(anio), anio, periodo, eventos, na.last = TRUE)]
}

prepareSpeciesMetricData <- function(
  species_table,
  metric = c("ocupacion", "diurnalidad"),
  selected_event = NULL,
  all_events = FALSE,
  top_n = 15,
  max_events = 5
) {
  #' Prepara los datos que alimentan las gráficas de ocupación y diurnalidad.
  #'
  #' Devuelve la misma selección de especies y eventos empleada por
  #' makeSpeciesMetricGraph(), en formato largo y con valores entre 0 y 1.

  metric <- match.arg(metric)
  metric_prefix <- if (identical(metric, "ocupacion")) "Ocupación" else "Diurnalidad"

  if (is.null(species_table) || nrow(species_table) == 0 ||
      !all(c("Ranking", "Especie") %in% names(species_table))) {
    return(data.frame())
  }

  column_prefix <- paste0(metric_prefix, " ")
  metric_columns <- names(species_table)[startsWith(names(species_table), column_prefix)]
  if (length(metric_columns) == 0) return(data.frame())

  available_events <- substring(metric_columns, nchar(column_prefix) + 1L)
  shown_events <- if (isTRUE(all_events)) {
    eventos_ordenados <- ordenar_eventos_cronologicamente(available_events)
    utils::tail(eventos_ordenados, max_events)
  } else {
    intersect(as.character(selected_event), available_events)
  }
  if (length(shown_events) == 0) return(data.frame())

  shown_columns <- paste0(column_prefix, shown_events)
  top_species <- species_table %>%
    dplyr::arrange(Ranking) %>%
    dplyr::slice_head(n = top_n)

  plot_data <- dplyr::bind_rows(lapply(seq_along(shown_columns), function(index) {
    data.frame(
      Especie = as.character(top_species$Especie),
      Evento = shown_events[[index]],
      Valor = suppressWarnings(as.numeric(top_species[[shown_columns[[index]]]])),
      Ranking = top_species$Ranking,
      stringsAsFactors = FALSE
    )
  })) %>%
    dplyr::mutate(
      Sin_detecciones = is.na(Valor) | !is.finite(Valor),
      Valor = dplyr::if_else(
        Sin_detecciones,
        NA_real_,
        pmin(pmax(Valor, 0), 1)
      ),
      Valor_grafico = dplyr::coalesce(Valor, 0),
      Estado = dplyr::if_else(Sin_detecciones, "Sin detecciones", "Valor calculado")
    )

  # La selección sigue correspondiendo a las especies con más registros
  # independientes. Dentro de esa muestra, el eje se ordena por la métrica:
  # valor del evento seleccionado o promedio de los eventos comparados.
  species_order <- plot_data %>%
    dplyr::group_by(Especie) %>%
    dplyr::summarise(
      Orden_metrica = if (all(is.na(Valor))) NA_real_ else mean(Valor, na.rm = TRUE),
      Ranking = min(Ranking, na.rm = TRUE),
      .groups = "drop"
    ) %>%
    dplyr::arrange(dplyr::desc(Orden_metrica), Ranking, Especie) %>%
    dplyr::pull(Especie) %>%
    as.character()
  plot_data$Especie <- factor(plot_data$Especie, levels = rev(species_order))
  plot_data$Evento <- factor(plot_data$Evento, levels = shown_events)
  plot_data
}

makeSpeciesMetricGraph <- function(
  species_table,
  metric = c("ocupacion", "diurnalidad"),
  selected_event = NULL,
  all_events = FALSE,
  top_n = 15,
  max_events = 5,
  interval_label = NULL
) {
  #' Grafica ocupación o diurnalidad por especie.
  #'
  #' Usa un gráfico de segmentos para un evento y una matriz de calor para la
  #' comparación de eventos recientes.
  #'
  #' @param species_table Tabla generada por makeSpeciesTable().
  #' @param metric Métrica: "ocupacion" o "diurnalidad".
  #' @param selected_event Identificador del evento seleccionado.
  #' @param all_events TRUE cuando el filtro corresponde a todos los eventos.
  #' @param top_n Número máximo de especies a mostrar.
  #' @param max_events Número máximo de eventos recientes en la comparación.
  #' @param interval_label Nombre del intervalo aplicado para el subtítulo.
  #'
  #' @return Objeto ggplot.

  metric <- match.arg(metric)
  metric_config <- switch(
    metric,
    ocupacion = list(
      prefix = "Ocupaci\u00f3n",
      title = "Ocupación por especie",
      axis = "Ocupación (%)",
      color = "#3498DB",
      track_color = "#D6EAF5",
      heatmap_colors = c("#EFF8FC", "#B9E1F2", "#65B7DC", "#238CC4", "#1A5490")
    ),
    diurnalidad = list(
      prefix = "Diurnalidad",
      title = "Diurnalidad por especie",
      axis = "Diurnalidad (%)",
      color = "#D9B64C",
      track_color = "#F5EAC4",
      heatmap_colors = c("#163E5C", "#236B8E", "#4FAFC0", "#B8DEC0", "#FFF1A3")
    )
  )

  empty_plot <- function(message) {
    ggplot2::ggplot() +
      ggplot2::theme_void() +
      ggplot2::annotate(
        "text", x = 0.5, y = 0.5, label = message,
        size = 5, color = "#7f8c8d"
      )
  }

  if (is.null(species_table) || nrow(species_table) == 0) {
    return(empty_plot("Sin datos para generar la gráfica"))
  }

  plot_data <- prepareSpeciesMetricData(
    species_table = species_table,
    metric = metric,
    selected_event = selected_event,
    all_events = all_events,
    top_n = top_n,
    max_events = max_events
  )

  if (nrow(plot_data) == 0) {
    return(empty_plot("Sin valores disponibles para esta métrica"))
  }

  shown_events <- levels(plot_data$Evento)
  shown_species <- dplyr::n_distinct(plot_data$Especie)
  interval_subtitle <- if (!is.null(interval_label) && nzchar(as.character(interval_label))) {
    paste0(" · Intervalo: ", as.character(interval_label))
  } else {
    ""
  }

  percentage_label <- function(values) {
    vapply(values, function(value) {
      formatted <- format(
        round(value * 100, 2),
        trim = TRUE,
        scientific = FALSE,
        decimal.mark = ","
      )
      paste0(formatted, "%")
    }, character(1))
  }

  if (isTRUE(all_events)) {
    plot_data <- plot_data %>%
      dplyr::mutate(
        Etiqueta = dplyr::if_else(
          Sin_detecciones,
          "—",
          percentage_label(Valor)
        ),
        Color_etiqueta = dplyr::case_when(
          Sin_detecciones ~ "#17324D",
          identical(metric, "diurnalidad") & Valor <= 0.40 ~ "#FFFFFF",
          identical(metric, "diurnalidad") ~ "#17324D",
          Valor >= 0.55 ~ "#FFFFFF",
          TRUE ~ "#17324D"
        )
      )

    ggplot2::ggplot(
      plot_data,
      ggplot2::aes(x = Evento, y = Especie, fill = Valor)
    ) +
      ggplot2::geom_tile(
        width = 0.94,
        height = 0.88,
        color = "#FFFFFF",
        linewidth = 1
      ) +
      ggplot2::geom_text(
        ggplot2::aes(label = Etiqueta, color = Color_etiqueta),
        size = 3,
        fontface = "bold",
        show.legend = FALSE
      ) +
      ggplot2::scale_color_identity() +
      ggplot2::scale_fill_gradientn(
        colors = metric_config$heatmap_colors,
        limits = c(0, 1),
        breaks = seq(0, 1, by = 0.25),
        labels = percentage_label,
        na.value = "#E8EDF2"
      ) +
      ggplot2::labs(
        title = metric_config$title,
        subtitle = paste0(
          "Matriz comparativa · Últimos ", length(shown_events),
          " eventos · Top ", shown_species, " especies", interval_subtitle
        ),
        x = "Evento",
        y = NULL,
        fill = metric_config$prefix
      ) +
      ggplot2::guides(
        fill = ggplot2::guide_colorbar(
          title.position = "top",
          barwidth = grid::unit(10, "lines"),
          barheight = grid::unit(0.6, "lines")
        )
      ) +
      ggplot2::theme_minimal(base_size = 12) +
      ggplot2::theme(
        plot.title = ggplot2::element_text(face = "bold", size = 14, color = "#1A5490"),
        plot.subtitle = ggplot2::element_text(size = 9.5, color = "#667085", margin = ggplot2::margin(b = 10)),
        axis.text.y = ggplot2::element_text(face = "italic", size = 9, color = "#243B53"),
        axis.text.x = ggplot2::element_text(face = "bold", size = 9, color = "#34495E"),
        axis.title.x = ggplot2::element_text(face = "bold", size = 10, margin = ggplot2::margin(t = 8)),
        panel.grid = ggplot2::element_blank(),
        legend.position = "top",
        legend.justification = "left",
        legend.title = ggplot2::element_text(face = "bold", size = 9),
        legend.text = ggplot2::element_text(size = 8),
        plot.background = ggplot2::element_rect(fill = "#FFFFFF", color = NA),
        plot.margin = ggplot2::margin(10, 18, 10, 10)
      )
  } else {
    valores_validos <- plot_data$Valor[is.finite(plot_data$Valor)]
    promedio <- if (length(valores_validos) > 0) mean(valores_validos) else 0
    ggplot2::ggplot(
      plot_data,
      ggplot2::aes(x = Valor_grafico, y = Especie)
    ) +
      ggplot2::geom_hline(
        yintercept = seq_len(shown_species),
        color = "#EDF2F7",
        linewidth = 0.7
      ) +
      ggplot2::geom_segment(
        ggplot2::aes(x = 0, xend = Valor_grafico, yend = Especie),
        color = metric_config$track_color,
        linewidth = 5,
        lineend = "round"
      ) +
      ggplot2::geom_segment(
        ggplot2::aes(x = 0, xend = Valor_grafico, yend = Especie),
        color = metric_config$color,
        linewidth = 2.8,
        lineend = "round"
      ) +
      ggplot2::geom_vline(
        xintercept = promedio,
        color = "#7A8FA6",
        linewidth = 0.6,
        linetype = "22"
      ) +
      ggplot2::geom_point(
        shape = 21,
        size = 4.4,
        stroke = 1.2,
        color = "#FFFFFF",
        fill = metric_config$color
      ) +
      ggplot2::geom_text(
        ggplot2::aes(label = percentage_label(Valor)),
        hjust = -0.18,
        size = 3,
        fontface = "bold",
        color = "#243B53"
      ) +
      ggplot2::scale_x_continuous(
        limits = c(0, 1.10),
        breaks = seq(0, 1, by = 0.25),
        labels = percentage_label,
        expand = ggplot2::expansion(mult = c(0.01, 0))
      ) +
      ggplot2::labs(
        title = metric_config$title,
        subtitle = paste0(
          "Evento ", shown_events[[1]], " · Top ", shown_species,
          " especies", interval_subtitle, " · Línea punteada: promedio"
        ),
        x = metric_config$axis,
        y = NULL
      ) +
      ggplot2::coord_cartesian(clip = "off") +
      ggplot2::theme_minimal(base_size = 12) +
      ggplot2::theme(
        plot.title = ggplot2::element_text(face = "bold", size = 14, color = "#1A5490"),
        plot.subtitle = ggplot2::element_text(size = 9.5, color = "#667085", margin = ggplot2::margin(b = 10)),
        axis.text.y = ggplot2::element_text(face = "italic", size = 9, color = "#243B53"),
        axis.text.x = ggplot2::element_text(size = 9, color = "#34495E"),
        axis.title.x = ggplot2::element_text(face = "bold", size = 10, margin = ggplot2::margin(t = 8)),
        panel.grid.major.y = ggplot2::element_blank(),
        panel.grid.minor = ggplot2::element_blank(),
        panel.grid.major.x = ggplot2::element_line(color = "#E5EDF3", linewidth = 0.5),
        legend.position = "none",
        plot.background = ggplot2::element_rect(fill = "#FFFFFF", color = NA),
        plot.margin = ggplot2::margin(10, 28, 10, 10)
      )
  }
}


makeMapLeaflet <- function(data, selected_sites, bounds, input_site, mode = "proyectos") {
  #' Crea el mapa de cámaras y sus fichas informativas.
  #'
  #' @param data Sitios filtrados con coordenadas, proyecto, contacto y métricas.
  #' @param selected_sites Sitios que deben resaltarse.
  #' @param bounds Límites geográficos de respaldo.
  #' @param input_site Descripción de la selección aplicada.
  #' @param mode Vista activa: `corporaciones` o `proyectos`.
  #' @return Mapa Leaflet.
  mode <- match.arg(mode, c("corporaciones", "proyectos"))
    
    # Excluir coordenadas ausentes o nulas.
    data_valid <- data[!is.na(data$lat) & !is.na(data$lon) & 
                       data$lat != 0 & data$lon != 0, ]
    
    if (nrow(data_valid) == 0) {
        return(leaflet() %>% 
               addTiles(options = tileOptions(crossOrigin = TRUE)) %>% 
               fitBounds(lng1 = bounds$lon[1], lat1 = bounds$lat[2], 
                        lng2 = bounds$lon[3], lat2 = bounds$lat[4]) %>%
               addScaleBar("bottomleft") %>%
               addControl(html = "<div style='background-color: white; padding: 10px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.2);'>
                              <strong>⚠️ No hay ubicaciones con coordenadas válidas</strong></div>",
                         position = "topright"))
    }
    
    color <- rep("#7fa3c4", nrow(data_valid))
    size <- rep(6, nrow(data_valid))
    
    selected_rows <- which(data_valid$site_name %in% selected_sites$site_name)

    if (grepl("^Red OTUS - ", input_site)) {
        color[selected_rows] <- "#1a5490"
        size[selected_rows] <- 10
    } else {
        color[selected_rows] <- "#0397d6"
        size[selected_rows] <- 10
    }
    
    escapar_html <- function(valor) {
        valor <- as.character(valor)
        valor <- gsub("&", "&amp;", valor, fixed = TRUE)
        valor <- gsub("<", "&lt;", valor, fixed = TRUE)
        valor <- gsub(">", "&gt;", valor, fixed = TRUE)
        valor <- gsub('"', "&quot;", valor, fixed = TRUE)
        valor
    }

    valor_texto <- function(columna, indice, respaldo = "No especificado") {
        if (!columna %in% names(data_valid)) return(respaldo)
        valor <- as.character(data_valid[[columna]][indice])
        if (is.na(valor) || !nzchar(trimws(valor))) respaldo else escapar_html(trimws(valor))
    }
    formato_entero <- function(valor) {
        format(valor, big.mark = ".", decimal.mark = ",", scientific = FALSE, trim = TRUE)
    }
    formato_decimal <- function(valor) {
        format(valor, decimal.mark = ",", nsmall = 2, scientific = FALSE, trim = TRUE)
    }

    popups <- character(nrow(data_valid))
    labels <- character(nrow(data_valid))
    
    for (i in 1:nrow(data_valid)) {
        site_name <- escapar_html(ifelse(is.na(data_valid$site_name[i]), "Sin nombre", data_valid$site_name[i]))
        departamento <- escapar_html(ifelse(is.na(data_valid$departamento[i]), "No especificado", data_valid$departamento[i]))
        project_id <- valor_texto("project_id", i)
        project_name <- valor_texto("project_short_name", i, project_id)
        project_admin <- valor_texto("project_admin", i)
        project_email <- valor_texto("project_admin_email", i)
        n_images <- ifelse(is.na(data_valid$n[i]), 0, as.numeric(data_valid$n[i]))
        effort <- ifelse(is.na(data_valid$effort[i]), 0, as.numeric(data_valid$effort[i]))
        osp_total <- ifelse(is.na(data_valid$ospTot[i]), 0, as.numeric(data_valid$ospTot[i]))
        osp_mamiferos <- ifelse(is.na(data_valid$ospMamiferos[i]), 0, as.numeric(data_valid$ospMamiferos[i]))
        osp_aves <- ifelse(is.na(data_valid$ospAves[i]), 0, as.numeric(data_valid$ospAves[i]))
        lat_value <- as.numeric(data_valid$lat[i])
        lon_value <- as.numeric(data_valid$lon[i])
        
        capture_rate <- ifelse(effort > 0, round(n_images / effort, 2), 0)
        labels[i] <- paste0(
            "<strong>", site_name, "</strong><br>",
            "Proyecto: ", project_name
        )

        contexto_popup <- if (identical(mode, "corporaciones")) {
            paste0(
                "<div class='map-popup-metadata'>",
                "<div><strong>Corporación:</strong> ", departamento, "</div>",
                "<div><strong>Proyecto:</strong> ", project_name, "</div>",
                "<div><strong>Administrador:</strong> ", project_admin, "</div>",
                "<div><strong>Correo:</strong> ", project_email, "</div>",
                "</div>"
            )
        } else {
            paste0(
                "<div class='map-popup-metadata'>",
                "<div><strong>Administrador:</strong> ", project_admin, "</div>",
                "<div><strong>Correo:</strong> ", project_email, "</div>",
                "</div>"
            )
        }
        
        popups[i] <- paste0(
            "<div style='font-family: Arial, sans-serif; min-width: 250px;'>",
            "<div style='background: linear-gradient(135deg, #1A5490 0%, #0397D6 100%); ",
            "color: white; padding: 10px 12px; margin: -10px -10px 10px -10px; ",
            "border-radius: 4px 4px 0 0; font-weight: bold; font-size: 14px;'>",
            "📍 ", site_name,
            "</div>",
            "<div style='margin-bottom: 8px; color: #555; font-size: 12px;'>",
            contexto_popup,
            "</div>",
            "<hr style='margin: 10px 0; border: none; border-top: 1px solid #e0e0e0;'>",
            "<div style='margin-bottom: 10px;'>",
            "<div style='color: #0397d6; font-weight: bold; margin-bottom: 5px; font-size: 11px;'>",
            "🎥 ESFUERZO DE MUESTREO",
            "</div>",
            "<div style='display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px;'>",
            "<span style='color: #666;'>Total de imágenes:</span>",
            "<span style='font-weight: bold; color: #2c3e50;'>", formato_entero(n_images), "</span>",
            "</div>",
            "<div style='display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px;'>",
            "<span style='color: #666;'>Días-cámara:</span>",
            "<span style='font-weight: bold; color: #2c3e50;'>", formato_entero(effort), "</span>",
            "</div>",
            "<div style='display: flex; justify-content: space-between; font-size: 12px;'>",
            "<span style='color: #666;'>Tasa de captura:</span>",
            "<span style='font-weight: bold; color: #27ae60;'>", formato_decimal(capture_rate), " img/día</span>",
            "</div>",
            "</div>",
            
            "<hr style='margin: 10px 0; border: none; border-top: 1px solid #e0e0e0;'>",
            "<div style='margin-bottom: 5px;'>",
            "<div style='color: #27ae60; font-weight: bold; margin-bottom: 5px; font-size: 11px;'>",
            "🦎 BIODIVERSIDAD REGISTRADA",
            "</div>",
            "<div style='display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px;'>",
            "<span style='color: #666;'>🔢 Total de especies:</span>",
            "<span style='font-weight: bold; color: #2c3e50;'>", osp_total, "</span>",
            "</div>",
            "<div style='display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px;'>",
            "<span style='color: #666;'>🐾 Mamíferos:</span>",
            "<span style='font-weight: bold; color: #e74c3c;'>", osp_mamiferos, "</span>",
            "</div>",
            "<div style='display: flex; justify-content: space-between; font-size: 12px;'>",
            "<span style='color: #666;'>🦜 Aves:</span>",
            "<span style='font-weight: bold; color: #3498db;'>", osp_aves, "</span>",
            "</div>",
            "</div>",
            
            "<div style='margin-top: 10px; padding-top: 8px; border-top: 1px solid #e0e0e0; ",
            "font-size: 10px; color: #999; text-align: center;'>",
            "Lat: ", round(lat_value, 5), " | Lon: ", round(lon_value, 5),
            "</div>",
            
            "</div>"
        )
    }
    
    map <- leaflet(data_valid) %>% 
        addMapPane("car-polygons", zIndex = 410) %>%
        addMapPane("camera-markers", zIndex = 430) %>%
        fitBounds(lng1 = bounds$lon[1], lat1 = bounds$lat[2], 
                  lng2 = bounds$lon[3], lat2 = bounds$lat[4]) %>% 
        addTiles(options = tileOptions(crossOrigin = TRUE)) %>% 
        addCircleMarkers(
            ~lon, ~lat, 
            color = color, 
            radius = size,
            fillOpacity = 0.7,
            weight = 2,
            popup = popups,
            label = lapply(labels, htmltools::HTML),
            labelOptions = labelOptions(
                style = list(
                    "font-weight" = "bold",
                    "font-size" = "12px",
                    "padding" = "3px 8px",
                    "background-color" = "rgba(255, 255, 255, 0.9)",
                    "border" = "1px solid #ccc",
                    "border-radius" = "4px"
                ),
                direction = "top"
            ),
            options = pathOptions(pane = "camera-markers")
        ) %>% 
        addScaleBar("bottomleft")
    
    return(map)
}


# ===============================================================================
# FUNCIÓN DE PATRÓN DE ACTIVIDAD TEMPORAL
# ===============================================================================

prepareActivityPatternData <- function(data, top_n = 10, interval = 30, unit = "minutes") {
  #' Prepara los registros independientes empleados en el patrón de actividad.
  #'
  #' @return Registros de las especies principales con timestamp y hora del día.
  if (is.null(data) || nrow(data) == 0 ||
      !all(c("photo_datetime", "sp_binomial", "deployment_name") %in% names(data))) {
    return(data.frame())
  }

  prepared <- data %>%
    dplyr::mutate(
      timestamp = as.POSIXct(photo_datetime, format = "%Y-%m-%d %H:%M:%S"),
      hour = lubridate::hour(timestamp)
    ) %>%
    dplyr::filter(
      !is.na(timestamp), !is.na(sp_binomial), sp_binomial != "", !is.na(hour)
    )

  if (nrow(prepared) == 0) return(data.frame())

  independent <- suppressMessages(
    remove_duplicates(prepared, interval = interval, unit = unit)
  ) %>%
    dplyr::mutate(
      timestamp = as.POSIXct(photo_datetime, format = "%Y-%m-%d %H:%M:%S"),
      hour = lubridate::hour(timestamp)
    )
  top_species <- independent %>%
    dplyr::count(sp_binomial, sort = TRUE) %>%
    dplyr::slice_head(n = top_n) %>%
    dplyr::pull(sp_binomial)

  independent %>%
    dplyr::filter(sp_binomial %in% top_species)
}

makeActivityPattern <- function(data, top_n = 10, interval = 30, unit = "minutes", interactive = FALSE, activity_pattern = NULL) {
  # Genera el patrón horario de las especies con más detecciones independientes.
  if (is.null(data) || nrow(data) == 0) {
    return(ggplot() + theme_void() + 
           annotate("text", x = 0.5, y = 0.5, label = "Sin datos para generar patrón", size = 5))
  }
  
  # Admitir un resumen horario precalculado.
  if (!is.null(activity_pattern) && nrow(activity_pattern) > 0) {
    project_names <- unique(data$project_short_name[!is.na(data$project_short_name)])
    eventos <- unique(data$subproject_name[!is.na(data$subproject_name)])
    
    pattern_data <- activity_pattern
    
    if (length(project_names) > 0 && !all(is.na(project_names))) {
      if (length(project_names) == 1 && project_names[1] != "TODOS") {
        if ("project_name" %in% names(pattern_data)) {
          pattern_data <- pattern_data %>% dplyr::filter(project_name %in% project_names)
        }
      }
    }
    
    if (length(eventos) > 0 && !all(is.na(eventos))) {
      if (length(eventos) == 1 && eventos[1] != "TODOS") {
        if ("subproject_name" %in% names(pattern_data)) {
          pattern_data <- pattern_data %>% dplyr::filter(subproject_name == eventos[1])
        }
      }
    }
    
    # Usar el resumen global cuando el filtro no tenga coincidencias.
    if (nrow(pattern_data) == 0) {
      if ("project_id" %in% names(activity_pattern) && "subproject_name" %in% names(activity_pattern)) {
        pattern_data <- activity_pattern %>% 
          dplyr::filter(project_id == "TODOS" & subproject_name == "TODOS")
      } else {
        pattern_data <- activity_pattern
      }
    }
    
    top_species_data <- pattern_data %>%
      dplyr::group_by(sp_binomial) %>%
      dplyr::summarise(total = sum(count, na.rm = TRUE), .groups = 'drop') %>%
      dplyr::arrange(desc(total)) %>%
      dplyr::slice_head(n = top_n)
    
    pattern_filtered <- pattern_data %>%
      dplyr::filter(sp_binomial %in% top_species_data$sp_binomial)
    
    if (nrow(pattern_filtered) == 0) {
      return(ggplot() + theme_void() + 
             annotate("text", x = 0.5, y = 0.5, label = "No hay datos de actividad", size = 5))
    }
    
    colors_pal <- c("#E74C3C", "#3498DB", "#2ECC71", "#F39C12", "#9B59B6",
                    "#1ABC9C", "#E67E22", "#34495E", "#16A085", "#D35400")
    
    if (interactive) {
      species_list <- unique(pattern_filtered$sp_binomial)
      color_map <- setNames(colors_pal[seq_along(species_list)], species_list)
      
      p_interactive <- plot_ly()
      
      for (sp in species_list) {
        sp_data <- pattern_filtered %>%
          dplyr::filter(sp_binomial == sp) %>%
          dplyr::arrange(hour) %>%
          dplyr::mutate(
            hover_text = paste0(
              "<b>", sp, "</b><br>",
              "Hora: ", hour, ":00<br>",
              "Registros independientes: ", scales::label_number(
                big.mark = ".", decimal.mark = ",", accuracy = 1
              )(count)
            )
          )
        
        p_interactive <- p_interactive %>%
          add_trace(
            data = sp_data,
            x = ~hour,
            y = ~count,
            type = "scatter",
            mode = "lines+markers",
            fill = "tozeroy",
            fillcolor = paste0(color_map[sp], "33"),
            line = list(
              color = color_map[sp], width = 2.5,
              shape = "spline", smoothing = 0.8
            ),
            marker = list(
              size = 6, color = color_map[sp],
              line = list(color = "white", width = 0.7)
            ),
            name = sp,
            text = ~hover_text,
            hoveron = "points",
            hovertemplate = "%{text}<extra></extra>"
          )
      }
      
      p_interactive <- p_interactive %>%
        layout(
          title = list(
            text = paste0("<b>Patrón de actividad por hora del día</b><br>",
                         "<sub>Top ", length(species_list), " especies más detectadas</sub>"),
            font = list(size = 14, color = "#2c3e50")
          ),
          xaxis = list(
            title = "Hora del día (0-24)",
            range = c(0, 24),
            dtick = 3,
            gridcolor = "#ecf0f1",
            titlefont = list(size = 11, color = "#2c3e50")
          ),
          yaxis = list(
            title = "Eventos independientes",
            gridcolor = "#ecf0f1",
            titlefont = list(size = 11, color = "#2c3e50"),
            rangemode = "tozero"
          ),
          plot_bgcolor = "white",
          paper_bgcolor = "white",
          margin = list(l = 65, r = 30, t = 65, b = 145),
          hovermode = "x unified",
          legend = list(
            orientation = "h",
            x = 0.5,
            y = -0.28,
            xanchor = "center",
            yanchor = "top",
            font = list(size = 9),
            bgcolor = "rgba(255,255,255,0)"
          ),
          autosize = TRUE
        ) %>%
        config(
          displayModeBar = TRUE, 
          displaylogo = FALSE,
          modeBarButtonsToRemove = c("pan2d", "lasso2d", "select2d", "autoScale2d"),
          responsive = TRUE
        )

      p_interactive <- htmlwidgets::onRender(
        p_interactive,
        "function(el, x) {
          el.on('plotly_click', function(eventData) {
            if (!eventData || !eventData.points || !eventData.points.length) return;
            var point = eventData.points[0];
            Plotly.Fx.hover(el, [{
              curveNumber: point.curveNumber,
              pointNumber: point.pointNumber
            }]);
          });
          el.on('plotly_doubleclick', function() {
            Plotly.Fx.unhover(el);
          });
        }"
      )
      
      return(p_interactive)
    } else {
      p <- ggplot(pattern_filtered, aes(x = hour, y = count, color = sp_binomial, fill = sp_binomial)) +
        geom_area(alpha = 0.2, position = "identity") +
        geom_line(linewidth = 1.5) +
        scale_color_manual(values = colors_pal) +
        scale_fill_manual(values = colors_pal) +
        scale_x_continuous(
          breaks = seq(0, 24, 3),
          limits = c(0, 24),
          expand = c(0.01, 0)
        ) +
        scale_y_continuous(expand = expansion(mult = c(0, 0.1))) +
        labs(
          title = "Patrón de actividad circadiana por especie",
          subtitle = paste("Top", length(species_list), "especies más detectadas"),
          x = "Hora del día (0-24)",
          y = "Eventos independientes",
          color = "Especie",
          fill = "Especie"
        ) +
        theme_minimal(base_size = 12) +
        theme(
          plot.title = element_text(size = 14, face = "bold", hjust = 0, color = "#2c3e50"),
          plot.subtitle = element_text(size = 11, hjust = 0, color = "#7f8c8d", margin = margin(b = 10)),
          axis.title = element_text(size = 11, face = "bold", color = "#2c3e50"),
          axis.text = element_text(size = 10, color = "#34495e"),
          legend.position = "right",
          legend.title = element_text(face = "bold", size = 10),
          legend.text = element_text(face = "italic", size = 9),
          panel.grid.major = element_line(color = "#ecf0f1", linewidth = 0.5),
          panel.grid.minor = element_blank(),
          panel.background = element_rect(fill = "white", color = NA),
          plot.background = element_rect(fill = "white", color = NA),
          plot.margin = margin(15, 10, 15, 15)
        )
      
      return(p)
    }
  }
  
  # Calcular el patrón desde las observaciones filtradas.
  data_filtered <- tryCatch(
    prepareActivityPatternData(data, top_n = top_n, interval = interval, unit = unit),
    error = function(e) {
      warning(paste("Error preparando datos de actividad:", e$message))
      data.frame()
    }
  )

  if (nrow(data_filtered) == 0) {
    return(ggplot() + theme_void() + 
           annotate("text", x = 0.5, y = 0.5, label = "No hay datos válidos de hora", size = 5))
  }

  top_species <- unique(data_filtered$sp_binomial)
  
  if (length(top_species) == 0) {
    return(ggplot() + theme_void() + 
           annotate("text", x = 0.5, y = 0.5, label = "No hay especies suficientes", size = 5))
  }
  
  p <- ggplot(data_filtered, aes(x = hour, color = sp_binomial, fill = sp_binomial))
  
  tryCatch({
    colors_pal <- c("#E74C3C", "#3498DB", "#2ECC71", "#F39C12", "#9B59B6",
                    "#1ABC9C", "#E67E22", "#34495E", "#16A085", "#D35400")
    
    p <- p + 
      geom_density(alpha = 0.2, linewidth = 1.5, adjust = 1.5) +
      scale_color_manual(values = colors_pal) +
      scale_fill_manual(values = colors_pal) +
      scale_x_continuous(
        breaks = seq(0, 24, 3),
        limits = c(0, 24),
        expand = c(0.01, 0)
      ) +
      scale_y_continuous(expand = expansion(mult = c(0, 0.1))) +
      labs(
        title = "Patrón de actividad circadiana por especie",
        subtitle = paste("Top", length(top_species), "especies más fotografiadas"),
        x = "Hora del día (0-24)",
        y = "Densidad de actividad",
        color = "Especie",
        fill = "Especie"
      ) +
      theme_minimal(base_size = 12) +
      theme(
        plot.title = element_text(size = 14, face = "bold", hjust = 0, color = "#2c3e50"),
        plot.subtitle = element_text(size = 11, hjust = 0, color = "#7f8c8d", margin = margin(b = 10)),
        axis.title = element_text(size = 11, face = "bold", color = "#2c3e50"),
        axis.text = element_text(size = 10, color = "#34495e"),
        legend.position = "right",
        legend.title = element_text(face = "bold", size = 10),
        legend.text = element_text(face = "italic", size = 9),
        panel.grid.major = element_line(color = "#ecf0f1", linewidth = 0.5),
        panel.grid.minor = element_blank(),
        panel.background = element_rect(fill = "white", color = NA),
        plot.background = element_rect(fill = "white", color = NA),
        plot.margin = margin(15, 10, 15, 15)
      )
    
    if (interactive) {
      # La densidad requiere al menos tres observaciones por especie.
      especies_validas <- data_filtered %>%
        group_by(sp_binomial) %>%
        summarise(n_obs = n(), .groups = 'drop') %>%
        filter(n_obs >= 3) %>%
        pull(sp_binomial)
      
      data_filtered <- data_filtered %>%
        filter(sp_binomial %in% especies_validas)
      
      density_data <- data_filtered %>%
        group_by(sp_binomial) %>%
        group_modify(~ {
          dens <- density(.x$hour, adjust = 1.5, from = 0, to = 24, n = 200)
          data.frame(hour = dens$x, density = dens$y)
        }) %>%
        ungroup()
      
      if (nrow(density_data) > 0) {
        species_list <- unique(density_data$sp_binomial)
        color_map <- setNames(colors_pal[seq_along(species_list)], species_list)
        
        p_interactive <- plot_ly(type = 'scatter', mode = 'lines')
        
        for (sp in species_list) {
          sp_data <- density_data %>% filter(sp_binomial == sp)
          
          p_interactive <- p_interactive %>%
            add_trace(
              data = sp_data,
              x = ~hour,
              y = ~density,
              type = 'scatter',
              mode = 'lines',
              fill = 'tozeroy',
              fillcolor = paste0(color_map[sp], "33"),
              line = list(color = color_map[sp], width = 2.5),
              name = sp,
              hovertemplate = paste0(
                "<b>", sp, "</b><br>",
                "Hora: %{x:.1f}h<br>",
                "Densidad: %{y:.3f}<extra></extra>"
              )
            )
        }
        
        p_interactive <- p_interactive %>%
          layout(
            title = list(
              text = paste0("<b>Patrón de actividad por hora del día</b><br>",
                           "<sub>Top ", length(top_species), " especies más fotografiadas</sub>"),
              font = list(size = 14, color = "#2c3e50")
            ),
            xaxis = list(
              title = "Hora del día (0-24)",
              range = c(0, 24),
              dtick = 3,
              gridcolor = "#ecf0f1",
              titlefont = list(size = 11, color = "#2c3e50")
            ),
            yaxis = list(
              title = "Densidad de actividad",
              gridcolor = "#ecf0f1",
              titlefont = list(size = 11, color = "#2c3e50"),
              rangemode = "tozero"
            ),
            plot_bgcolor = "white",
            paper_bgcolor = "white",
            margin = list(l = 60, r = 140, t = 60, b = 70),
            hovermode = "closest",
            legend = list(
              orientation = "v",
              x = 1.01,
              y = 1,
              xanchor = "left",
              yanchor = "top",
              font = list(size = 9),
              bgcolor = "rgba(255,255,255,0.8)",
              bordercolor = "#ecf0f1",
              borderwidth = 1
            ),
            autosize = TRUE
          ) %>%
          config(
            displayModeBar = TRUE, 
            displaylogo = FALSE,
            modeBarButtonsToRemove = c("pan2d", "lasso2d", "select2d", "autoScale2d"),
            responsive = TRUE
          )
        
        return(p_interactive)
      }
    }
    
    # Compactar la leyenda cuando se muestran varias especies.
    if (length(top_species) > 6) {
      p <- p + guides(
        color = guide_legend(ncol = 1, override.aes = list(linewidth = 2, alpha = 1)),
        fill = guide_legend(ncol = 1)
      )
    }
    
  }, error = function(e) {
    # Conservar una salida útil si la densidad no converge.
    p <<- ggplot(data_filtered, aes(x = hour, fill = sp_binomial)) +
      geom_histogram(alpha = 0.6, position = "identity", bins = 24) +
      scale_x_continuous(breaks = seq(0, 24, 2), limits = c(0, 24)) +
      labs(
        title = "Patrón de actividad por especie",
        x = "Hora del día",
        y = "Frecuencia",
        fill = "Especie"
      ) +
      theme_minimal()
  })
  
  return(p)
}

# ===============================================================================
# FUNCIONES PARA CÁLCULO DE ÍNDICES DE DIVERSIDAD
# ===============================================================================

calcular_numeros_hill <- function(data, q = 1) {
  #' Calcula la diversidad efectiva de orden 0, 1 o 2.
  #' @param data Observaciones con la columna `sp_binomial`.
  #' @param q Orden de Hill solicitado.
  #' @return Número de especies efectivas o `NA` cuando no hay datos.
  
  if (!("sp_binomial" %in% names(data)) || nrow(data) == 0) {
    return(NA)
  }
  
  # Contar individuos por especie
  conteos <- data %>%
    filter(!is.na(sp_binomial)) %>%
    count(sp_binomial, name = "n_individuos")
  
  if (nrow(conteos) == 0) {
    return(NA)
  }
  
  total <- sum(conteos$n_individuos)
  
  proporciones <- conteos$n_individuos / total
  
  # Eliminar proporciones cero
  proporciones <- proporciones[proporciones > 0]
  
  if (q == 0) {
    # q = 0: Riqueza de especies (simplemente el número de especies)
    hill <- length(proporciones)
    
  } else if (q == 1) {
    # q = 1: Exponencial de Shannon
    # ^1D = exp(-Σ p_i * ln(p_i))
    shannon <- -sum(proporciones * log(proporciones))
    hill <- exp(shannon)
    
  } else {
    # q > 0 y q ≠ 1: Fórmula general
    # ^qD = (Σ p_i^q)^(1/(1-q))
    suma_potencias <- sum(proporciones^q)
    hill <- suma_potencias^(1/(1-q))
  }
  
  return(round(hill, 2))
}

# ===============================================================================
# FUNCIÓN PARA FILTRADO DE EVENTOS INDEPENDIENTES
# ===============================================================================

remove_duplicates <- function(data, interval = 30, unit = "minutes") {
  #' Conserva detecciones independientes por cámara, evento y especie.
  #' @param data Observaciones con cámara, fecha y nombre científico.
  #' @param interval Separación mínima entre detecciones conservadas.
  #' @param unit Unidad del intervalo.
  #' @return Observaciones filtradas; los registros sin taxón se preservan.
  
  # Validar datos de entrada
  if (is.null(data) || nrow(data) == 0) {
    warning("DataFrame vacío proporcionado a remove_duplicates")
    return(data)
  }
  
  # Verificar columnas requeridas
  required_cols <- c("deployment_name", "photo_datetime", "sp_binomial")
  missing_cols <- setdiff(required_cols, names(data))
  
  if (length(missing_cols) > 0) {
    stop(paste("Columnas faltantes en el DataFrame:", paste(missing_cols, collapse = ", ")))
  }
  
  # Convertir intervalo a segundos según la unidad especificada
  interval_seconds <- switch(
    tolower(unit),
    "seconds" = interval,
    "minutes" = interval * 60,
    "hours" = interval * 3600,
    "days" = interval * 86400,
    "weeks" = interval * 604800,
    stop(paste("Unidad no reconocida:", unit, 
               ". Use: 'seconds', 'minutes', 'hours', 'days', 'weeks'"))
  )
  
  # Separar registros con y sin identificación taxonómica
  data_with_taxon <- data %>% filter(!is.na(sp_binomial) & sp_binomial != "")
  data_without_taxon <- data %>% filter(is.na(sp_binomial) | sp_binomial == "")
  
  # Sin taxón no es posible agrupar detecciones.
  if (nrow(data_with_taxon) == 0) {
    message("No hay registros con identificación taxonómica para filtrar")
    return(data)
  }
  
  # Convertir photo_datetime a POSIXct si no lo está
  data_with_taxon <- data_with_taxon %>%
    mutate(
      timestamp = as.POSIXct(photo_datetime, format = "%Y-%m-%d %H:%M:%S")
    )
  
  # Descartar fechas no interpretables.
  if (all(is.na(data_with_taxon$timestamp))) {
    warning("No se pudo convertir photo_datetime a timestamp válido")
    return(data)
  }
  
  # Incluir proyecto y evento evita mezclar cámaras con nombres repetidos entre
  # proyectos o periodos de muestreo.
  group_cols <- intersect(
    c("project_id", "subproject_name", "deployment_name", "sp_binomial"),
    names(data_with_taxon)
  )

  # La selección debe ser acumulativa: comparar con lag() sobre todas las filas
  # subcuenta cadenas como 00:00, 00:20 y 00:40 para un umbral de 30 minutos.
  marcar_independientes <- function(timestamp, umbral_segundos) {
    segundos <- as.numeric(timestamp)
    conservar <- logical(length(segundos))
    ultimo_conservado <- NA_real_

    for (i in seq_along(segundos)) {
      actual <- segundos[[i]]
      if (is.na(actual)) {
        # Un timestamp inválido no debe provocar pérdida silenciosa de datos.
        conservar[[i]] <- TRUE
      } else if (is.na(ultimo_conservado) ||
                 actual - ultimo_conservado >= umbral_segundos) {
        conservar[[i]] <- TRUE
        ultimo_conservado <- actual
      }
    }
    conservar
  }

  # Agrupar por contexto de deployment y taxón, ordenar por tiempo.
  data_grouped <- data_with_taxon %>%
    dplyr::group_by(dplyr::across(dplyr::all_of(group_cols))) %>%
    dplyr::arrange(timestamp, .by_group = TRUE) %>%
    mutate(
      keep_record = marcar_independientes(timestamp, interval_seconds)
    ) %>%
    ungroup()
  
  # Filtrar solo registros a mantener
  data_filtered <- data_grouped %>%
    filter(keep_record) %>%
    select(-timestamp, -keep_record)  # Eliminar columnas auxiliares
  
  # Combinar con registros sin taxón (que se preservan todos)
  data_final <- bind_rows(data_filtered, data_without_taxon)
  
  # Restaurar el orden analítico.
  data_final <- data_final %>%
    arrange(deployment_name, photo_datetime)
  
  # Mensaje informativo
  n_original <- nrow(data)
  n_final <- nrow(data_final)
  n_removed <- n_original - n_final
  pct_removed <- round((n_removed / n_original) * 100, 2)
  
  message(sprintf(
    "Eliminados %d registros duplicados (%.2f%%) - Intervalo: %d %s",
    n_removed, pct_removed, interval, unit
  ))
  message(sprintf(
    "Registros originales: %d | Registros finales: %d",
    n_original, n_final
  ))
  
  return(data_final)
  
}

# ===============================================================================
# FUNCIÓN PARA CALCULAR INDICADORES POR PERÍODO (VISTA CONSOLIDADA)
# ===============================================================================

calcular_indicadores_por_periodo <- function(tableSites_consolidado, iavhdata_consolidado, mostrar_consolidado = TRUE) {
  # Resume operación y diversidad por evento y, cuando aplica, en conjunto.
  if (is.null(tableSites_consolidado) || nrow(tableSites_consolidado) == 0) {
    return(data.frame(
      Periodo = character(),
      Imagenes = numeric(),
      Camaras = numeric(),
      Dias_camara = numeric(),
      Especies = numeric(),
      Mamiferos = numeric(),
      Aves = numeric(),
      Hill1 = numeric(),
      Hill2 = numeric(),
      Hill3 = numeric(),
      stringsAsFactors = FALSE
    ))
  }
  
  periodos <- unique(tableSites_consolidado$evento_muestreo)
  periodos <- periodos[!is.na(periodos)]
  periodos <- sort(periodos, decreasing = TRUE)
  
  if (length(periodos) == 0) {
    return(data.frame(
      Periodo = character(),
      Imagenes = numeric(),
      Camaras = numeric(),
      Dias_camara = numeric(),
      Especies = numeric(),
      Mamiferos = numeric(),
      Aves = numeric(),
      Hill1 = numeric(),
      Hill2 = numeric(),
      Hill3 = numeric(),
      stringsAsFactors = FALSE
    ))
  }
  
  resultados <- list()
  
  for (periodo in periodos) {
    sites_periodo <- tableSites_consolidado %>% filter(evento_muestreo == periodo)
    data_periodo <- iavhdata_consolidado %>% filter(evento_muestreo == periodo)
    
    total_imagenes <- sum(sites_periodo$n, na.rm = TRUE)
    
    if (total_imagenes > 0) {
      hill1 <- tryCatch(calcular_numeros_hill(data_periodo, q = 0), error = function(e) NA)
      hill2 <- tryCatch(calcular_numeros_hill(data_periodo, q = 1), error = function(e) NA)
      hill3 <- tryCatch(calcular_numeros_hill(data_periodo, q = 2), error = function(e) NA)
      
      # La riqueza se calcula desde las observaciones únicas del periodo.
      especies_periodo <- data_periodo %>%
        dplyr::filter(!is.na(sp_binomial) & sp_binomial != "") %>%
        dplyr::pull(sp_binomial) %>%
        unique() %>%
        length()
      
      mamiferos_periodo <- data_periodo %>%
        dplyr::filter(!is.na(sp_binomial) & sp_binomial != "" & 
                      !is.na(class) & class == "Mammalia") %>%
        dplyr::pull(sp_binomial) %>%
        unique() %>%
        length()
      
      aves_periodo <- data_periodo %>%
        dplyr::filter(!is.na(sp_binomial) & sp_binomial != "" & 
                      !is.na(class) & class == "Aves") %>%
        dplyr::pull(sp_binomial) %>%
        unique() %>%
        length()
      
      # Incluir cámaras válidas aunque no tengan detecciones.
      camaras_periodo <- if ("ndepl" %in% names(sites_periodo)) {
        sum(sites_periodo$ndepl, na.rm = TRUE)
      } else if ("site_name" %in% names(sites_periodo)) {
        dplyr::n_distinct(sites_periodo$site_name)
      } else {
        nrow(sites_periodo)
      }
      
      resultados[[periodo]] <- data.frame(
        Periodo = periodo,
        Imagenes = total_imagenes,
        Camaras = camaras_periodo,
        Dias_camara = sum(sites_periodo$effort, na.rm = TRUE),
        Especies = especies_periodo,
        Mamiferos = mamiferos_periodo,
        Aves = aves_periodo,
        Hill1 = ifelse(is.na(hill1), 0, hill1),
        Hill2 = ifelse(is.na(hill2), 0, round(hill2, 2)),
        Hill3 = ifelse(is.na(hill3), 0, round(hill3, 2)),
        stringsAsFactors = FALSE
      )
    }
  }
  
  if (length(resultados) == 0) {
    return(data.frame(
      Periodo = character(),
      Imagenes = numeric(),
      Camaras = numeric(),
      Dias_camara = numeric(),
      Especies = numeric(),
      Mamiferos = numeric(),
      Aves = numeric(),
      Hill1 = numeric(),
      Hill2 = numeric(),
      Hill3 = numeric(),
      stringsAsFactors = FALSE
    ))
  }
  
  tabla_periodos <- do.call(rbind, resultados)
  
  # El consolidado solo se agrega cuando existen varios periodos.
  num_periodos <- nrow(tabla_periodos)
  
  if (mostrar_consolidado && num_periodos > 1) {
    # Recalcular sobre toda la selección evita sumar especies repetidas.
    especies_total <- iavhdata_consolidado %>%
      dplyr::filter(!is.na(sp_binomial) & sp_binomial != "") %>%
      dplyr::pull(sp_binomial) %>%
      unique() %>%
      length()
    
    mamiferos_total <- iavhdata_consolidado %>%
      dplyr::filter(!is.na(sp_binomial) & sp_binomial != "" & 
                    !is.na(class) & class == "Mammalia") %>%
      dplyr::pull(sp_binomial) %>%
      unique() %>%
      length()
    
    aves_total <- iavhdata_consolidado %>%
      dplyr::filter(!is.na(sp_binomial) & sp_binomial != "" & 
                    !is.na(class) & class == "Aves") %>%
      dplyr::pull(sp_binomial) %>%
      unique() %>%
      length()
    
    # Cada instalación cámara-evento aporta una unidad al consolidado.
    camaras_total <- if ("ndepl" %in% names(tableSites_consolidado)) {
      sum(tableSites_consolidado$ndepl, na.rm = TRUE)
    } else if ("site_name" %in% names(tableSites_consolidado)) {
      dplyr::n_distinct(tableSites_consolidado$site_name)
    } else {
      nrow(tableSites_consolidado)
    }
    
    hill1_total <- tryCatch(calcular_numeros_hill(iavhdata_consolidado, q = 0), error = function(e) NA)
    hill2_total <- tryCatch(calcular_numeros_hill(iavhdata_consolidado, q = 1), error = function(e) NA)
    hill3_total <- tryCatch(calcular_numeros_hill(iavhdata_consolidado, q = 2), error = function(e) NA)
    
    fila_total <- data.frame(
      Periodo = "CONSOLIDADO",
      Imagenes = sum(tabla_periodos$Imagenes, na.rm = TRUE),
      Camaras = camaras_total,
      Dias_camara = sum(tabla_periodos$Dias_camara, na.rm = TRUE),
      Especies = especies_total,
      Mamiferos = mamiferos_total,
      Aves = aves_total,
      Hill1 = ifelse(is.na(hill1_total), 0, hill1_total),
      Hill2 = ifelse(is.na(hill2_total), 0, round(hill2_total, 2)),
      Hill3 = ifelse(is.na(hill3_total), 0, round(hill3_total, 2)),
      stringsAsFactors = FALSE
    )
    
    tabla_final <- rbind(tabla_periodos, fila_total)
  } else {
    tabla_final <- tabla_periodos
  }
  
  return(tabla_final)
  
}

# ==============================================================================
# ADAPTADOR DEL MODELO SILVER/GOLD 2026
# ==============================================================================

resolver_release <- function(data_path = getOption("red_otus.data_path", "data")) {
  release_path <- normalizePath(data_path, winslash = "/", mustWork = FALSE)
  if (!dir.exists(release_path)) {
    stop("No existe la carpeta de datos procesados: ", release_path, call. = FALSE)
  }
  manifest_path <- file.path(release_path, "manifest.json")
  if (!file.exists(manifest_path)) stop("La publicación no contiene manifest.json.", call. = FALSE)
  manifest <- jsonlite::fromJSON(manifest_path)
  if (!identical(as.character(manifest$status), "approved")) {
    stop("La publicación activa no está aprobada.", call. = FALSE)
  }

  archivos_requeridos <- c(
    "validated_data/dim_project.parquet",
    "validated_data/dim_event.parquet",
    "validated_data/dim_deployment.parquet",
    "validated_data/dim_taxon.parquet",
    "validated_data/fact_observation.parquet",
    "validated_data/bridge_deployment_corporation.parquet",
    "dashboard_outputs/filter_catalog.parquet",
    "dashboard_outputs/indicator_summary.parquet",
    "dashboard_outputs/species_metrics.parquet",
    "dashboard_outputs/activity_hour.parquet",
    "dashboard_outputs/map_deployment.parquet"
  )
  faltantes <- archivos_requeridos[!file.exists(file.path(release_path, archivos_requeridos))]
  if (length(faltantes) > 0) {
    stop(
      "La publicación está incompleta. Faltan: ",
      paste(faltantes, collapse = ", "),
      call. = FALSE
    )
  }
  list(path = release_path, manifest = manifest)
}

obtener_eventos_disponibles <- function() {
  release <- tryCatch(resolver_release(), error = function(e) NULL)
  if (is.null(release)) return(character(0))
  catalog_path <- file.path(release$path, "dashboard_outputs", "filter_catalog.parquet")
  if (!file.exists(catalog_path)) return(character(0))
  catalog <- as.data.frame(arrow::read_parquet(catalog_path))
  sort(unique(as.character(catalog$event_id[catalog$event_id != "ALL"])), decreasing = TRUE)
}

cargar_datos <- function() {
  release <- resolver_release()
  read_tier <- function(tier, name, columns = NULL) {
    directory <- switch(tier, silver = "validated_data", gold = "dashboard_outputs", tier)
    path <- file.path(release$path, directory, paste0(name, ".parquet"))
    if (!file.exists(path)) stop("Falta el dataset: ", directory, "/", name, ".parquet", call. = FALSE)
    table <- if (is.null(columns)) {
      arrow::read_parquet(path)
    } else {
      arrow::read_parquet(path, col_select = dplyr::all_of(columns))
    }
    as.data.frame(table)
  }

  # La vista usa la tabla de hechos únicamente para filtrar, contar y resolver
  # el rango temporal. Los cálculos analíticos provienen de los productos Gold.
  observations <- read_tier(
    "silver", "fact_observation",
    c(
      "project_id", "subproject_name", "photo_datetime", "Corporacion",
      "project_short_name", "sp_binomial"
    )
  )
  deployments <- read_tier(
    "silver", "dim_deployment",
    c(
      "project_id", "deployment_id", "subproject_name", "Corporacion",
      "effective_start_date", "effective_end_date", "deployment_days", "deployment_key"
    )
  )
  projects <- read_tier(
    "silver", "dim_project",
    c(
      "project_id", "project_short_name", "project_name", "project_admin",
      "project_admin_email", "project_admin_organization", "initiative_id", "initiative_name"
    )
  )
  map_data <- read_tier("gold", "map_deployment")

  observations <- observations %>%
    dplyr::mutate(
      project_id = as.character(project_id),
      subproject_name = as.character(subproject_name),
      photo_datetime = as.POSIXct(photo_datetime, tz = "UTC"),
      evento_muestreo = subproject_name
    )

  deployments <- deployments %>%
    dplyr::mutate(
      project_id = as.character(project_id),
      deployment_name = as.character(deployment_id),
      subproject_name = as.character(subproject_name),
      start_date = as.Date(effective_start_date),
      end_date = as.Date(effective_end_date)
    )

  table_sites <- map_data %>%
    dplyr::transmute(
      project_id = as.character(project_id),
      project_short_name = as.character(project_short_name),
      subproject_name = as.character(subproject_name),
      evento_muestreo = as.character(subproject_name),
      site_name = as.character(deployment_id),
      Corporacion = as.character(Corporacion),
      departamento = as.character(Corporacion),
      project_admin = as.character(project_admin),
      project_admin_email = as.character(project_admin_email),
      lat = as.numeric(latitude), lon = as.numeric(longitude),
      n = as.integer(images), ndepl = 1L, effort = as.numeric(deployment_days),
      ospTot = as.integer(species), ospMamiferos = as.integer(mammals), ospAves = as.integer(birds),
      rank_onsp = 1L, rank_onMamiferos = 1L, rank_onAves = 1L,
      collector = as.character(project_short_name)
    )

  list(
    iavhdata = observations,
    deployments = deployments,
    tableSites = table_sites,
    projects = projects,
    gold = list(
      filters = read_tier("gold", "filter_catalog"),
      indicators = read_tier("gold", "indicator_summary"),
      species = read_tier("gold", "species_metrics"),
      activity = read_tier("gold", "activity_hour")
    ),
    manifest = release$manifest
  )
}

scope_gold <- function(modo, entidad) {
  if (es_seleccion_global_entidad(entidad, modo)) return(c(type = "global", id = "ALL"))
  c(type = if (identical(modo, "corporaciones")) "corporation" else "project", id = as.character(entidad))
}

filtrar_gold <- function(data, modo, entidad, evento = NULL, intervalo = NULL) {
  scope <- scope_gold(modo, entidad)
  result <- data[data$scope_type == scope[["type"]] & data$scope_id == scope[["id"]], , drop = FALSE]
  if (!is.null(evento) && "selection_event" %in% names(result)) {
    event_id <- if (es_seleccion_global_evento(evento)) "ALL" else as.character(evento)
    result <- result[result$selection_event == event_id, , drop = FALSE]
  }
  if (!is.null(intervalo) && "interval_minutes" %in% names(result)) {
    result <- result[result$interval_minutes == as.integer(intervalo), , drop = FALSE]
  }
  result
}

tabla_indicadores_gold <- function(data, modo, entidad, evento, intervalo_minutos) {
  scope <- scope_gold(modo, entidad)
  rows <- data[data$scope_type == scope[["type"]] & data$scope_id == scope[["id"]], , drop = FALSE]
  rows <- rows[rows$interval_minutes == as.integer(intervalo_minutos), , drop = FALSE]
  if (!es_seleccion_global_evento(evento)) rows <- rows[rows$event_id == as.character(evento), , drop = FALSE]
  if (es_seleccion_global_evento(evento)) {
    event_rows <- rows[rows$event_id != "ALL", , drop = FALSE]
    event_rows <- event_rows[order(event_rows$event_id, decreasing = TRUE), , drop = FALSE]
    rows <- rbind(event_rows, rows[rows$event_id == "ALL", , drop = FALSE])
  }
  data.frame(
    Periodo = ifelse(rows$event_id == "ALL", "CONSOLIDADO", rows$event_id),
    `Imágenes` = as.integer(rows$images),
    `Registros independientes` = as.integer(rows$independent_records),
    `Cámaras` = as.integer(rows$cameras),
    `Trampas/noche` = as.numeric(rows$camera_days), Especies = as.integer(rows$species),
    `Mamíferos` = as.integer(rows$mammals), Aves = as.integer(rows$birds),
    `Hill 1` = as.numeric(rows$hill1), `Hill 2` = as.numeric(rows$hill2),
    `Hill 3` = as.numeric(rows$hill3), check.names = FALSE
  )
}

tabla_especies_gold <- function(data, modo, entidad, evento, intervalo_minutos) {
  rows <- filtrar_gold(data, modo, entidad, evento, intervalo_minutos)
  if (nrow(rows) == 0) return(data.frame())
  base_columns <- c("ranking", "sp_binomial", "class", "order", "family", "genus", "image_count", "independent_count")
  result <- unique(rows[, base_columns, drop = FALSE])
  result <- result[order(result$ranking, result$sp_binomial), , drop = FALSE]
  names(result) <- c("Ranking", "Especie", "Clase", "Orden", "Familia", "Genero", "Numero imagenes", "Registros independientes")
  taxonomy_columns <- c("Clase", "Orden", "Familia", "Genero")
  for (column in taxonomy_columns) {
    value <- trimws(as.character(result[[column]]))
    value[is.na(value) | !nzchar(value)] <- "Sin información"
    result[[column]] <- value
  }
  events <- sort(unique(as.character(rows$metric_event)), decreasing = TRUE)
  for (event_id in events) {
    metric <- rows[rows$metric_event == event_id, c("sp_binomial", "occupancy", "frequency", "diurnality"), drop = FALSE]
    no_detection <- is.na(metric$occupancy)
    metric$occupancy[no_detection] <- 0
    metric$frequency[no_detection & is.na(metric$frequency)] <- 0
    names(metric) <- c("Especie", paste0("Ocupación ", event_id), paste0("Frecuencia ", event_id), paste0("Diurnalidad ", event_id))
    result <- merge(result, metric, by = "Especie", all.x = TRUE, sort = FALSE)
    result <- result[order(result$Ranking, result$Especie), , drop = FALSE]
  }
  result[, c("Ranking", "Especie", setdiff(names(result), c("Ranking", "Especie"))), drop = FALSE]
}

actividad_gold <- function(data, modo, entidad, evento, intervalo_minutos) {
  rows <- filtrar_gold(data, modo, entidad, evento, intervalo_minutos)
  rows <- rows[order(rows$ranking, rows$sp_binomial, rows$subproject_name, rows$hour), , drop = FALSE]
  rows
}

intervalo_minutos <- function(value) {
  result <- switch(as.character(value), "sin_filtro" = 0L, "30min" = 30L, "1h" = 60L, "24h" = 1440L, NA_integer_)
  if (is.na(result)) stop("Intervalo de independencia no válido.", call. = FALSE)
  result
}

# Fin de las funciones consumidas por app.R.
