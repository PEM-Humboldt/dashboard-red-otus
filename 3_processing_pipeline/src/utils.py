"""
Utilidades genéricas para el pipeline de procesamiento.
Funciones de lectura, filtrado, limpieza y operaciones comunes.
"""
import os
import pandas as pd
import geopandas as gpd
from pathlib import Path
from datetime import datetime
import numpy as np


# ===============================================================================
# LECTURA DE ARCHIVOS
# ===============================================================================

def obtener_archivos_csv_imagenes(folder_path):
    """
    Obtiene lista de archivos CSV de imágenes en una carpeta.
    
    Args:
        folder_path (str): Ruta a la carpeta con archivos CSV
        
    Returns:
        list: Lista de nombres de archivos CSV que contienen 'images'
    """
    if not os.path.exists(folder_path):
        print(f"  ✗ Carpeta no encontrada: {folder_path}")
        return []
    
    all_files = os.listdir(folder_path)
    images_files = [f for f in all_files if 'images' in f]
    csv_files = [f for f in images_files if f.endswith('.csv')]
    
    return sorted(csv_files)


def cargar_csv_robusto(file_path, descripcion="archivo"):
    """
    Carga un archivo CSV con manejo robusto de encodings.
    
    Args:
        file_path (str): Ruta al archivo CSV
        descripcion (str): Descripción del archivo para mensajes
        
    Returns:
        pd.DataFrame: DataFrame cargado o None si hay error
    """
    if not os.path.exists(file_path):
        print(f"  ✗ Archivo no encontrado: {file_path}")
        return None
    
    try:
        # Intento 1: UTF-8 (más común)
        # low_memory=False para evitar DtypeWarning en columnas con tipos mixtos
        df = pd.read_csv(file_path, low_memory=False)
        print(f"  ✓ {descripcion} cargado: {len(df):,} registros")
        return df
        
    except UnicodeDecodeError:
        try:
            # Intento 2: UTF-16 con tabulación
            df = pd.read_csv(file_path, sep='\t', encoding='utf-16')
            print(f"  ✓ {descripcion} cargado (UTF-16): {len(df):,} registros")
            return df
            
        except Exception as e:
            print(f"  ✗ Error al leer {descripcion}: {e}")
            return None
            
    except Exception as e:
        print(f"  ✗ Error al leer {descripcion}: {e}")
        return None


def concatenar_archivos_csv(folder_path, patron='images'):
    """
    Concatena múltiples archivos CSV en un solo DataFrame.
    
    Args:
        folder_path (str): Ruta a la carpeta con archivos CSV
        patron (str): Patrón para filtrar archivos
        
    Returns:
        pd.DataFrame: DataFrame consolidado o None si hay error
    """
    csv_files = obtener_archivos_csv_imagenes(folder_path)
    
    if not csv_files:
        print(f"  ✗ No se encontraron archivos CSV con patrón '{patron}'")
        return None
    
    print(f"  Archivos encontrados: {len(csv_files)}")
    
    df_list = []
    
    for idx, csv in enumerate(csv_files, 1):
        file_path = os.path.join(folder_path, csv)
        df = cargar_csv_robusto(file_path, f"Archivo {idx}/{len(csv_files)}")
        
        if df is not None:
            df_list.append(df)
    
    if not df_list:
        print("  ✗ No se pudo cargar ningún archivo")
        return None
    
    # Concatenar todos los DataFrames
    df_consolidado = pd.concat(df_list, ignore_index=True)
    print(f"  ✓ Dataset consolidado: {len(df_consolidado):,} registros totales")
    
    return df_consolidado


# ===============================================================================
# PROCESAMIENTO DE FECHAS
# ===============================================================================

def procesar_timestamps(df, columna='timestamp'):
    """
    Procesa timestamps con manejo robusto de múltiples formatos.
    
    Args:
        df (pd.DataFrame): DataFrame con columna de timestamp
        columna (str): Nombre de la columna con timestamps
        
    Returns:
        pd.DataFrame: DataFrame con columnas de fecha procesadas
    """
    if columna not in df.columns:
        print(f"  ✗ Columna '{columna}' no encontrada")
        return df
    
    print(f"  Procesando {len(df):,} timestamps...")
    
    df_work = df.copy()
    
    # Formatos de fecha conocidos en Wildlife Insights
    formatos_fecha = [
        '%Y-%m-%d %H:%M:%S',           # 2025-01-15 14:30:00
        '%Y-%m-%d %H:%M:%S.%f',        # 2025-01-15 14:30:00.123
        '%m/%d/%Y %H:%M',              # 01/15/2025 14:30
        '%d/%m/%Y %H:%M:%S',           # 15/01/2025 14:30:00
        '%d/%m/%Y %H:%M',              # 15/01/2025 14:30
        '%Y/%m/%d %H:%M:%S',           # 2025/01/15 14:30:00
        '%Y-%m-%dT%H:%M:%S',           # ISO 8601: 2025-01-15T14:30:00
        '%Y-%m-%dT%H:%M:%S.%f',        # ISO 8601 con microsegundos
        '%Y-%m-%dT%H:%M:%SZ',          # ISO 8601 UTC
    ]
    
    # Intentar conversión con cada formato
    timestamp_parsed = None
    formato_exitoso = None
    
    for formato in formatos_fecha:
        try:
            timestamp_parsed = pd.to_datetime(df_work[columna], format=formato, errors='coerce')
            registros_validos = timestamp_parsed.notna().sum()
            
            if registros_validos > 0:
                formato_exitoso = formato
                break
                
        except Exception:
            continue
    
    # Si ningún formato funcionó, usar conversión automática
    if timestamp_parsed is None or timestamp_parsed.notna().sum() == 0:
        print("    ⚠ Usando conversión automática de fechas...")
        timestamp_parsed = pd.to_datetime(df_work[columna], errors='coerce')
    else:
        print(f"    ✓ Formato detectado: {formato_exitoso}")
    
    # Agregar columnas procesadas
    df_work['timestamp_parsed'] = timestamp_parsed
    df_work['photo_datetime'] = timestamp_parsed
    df_work['photo_date'] = timestamp_parsed.dt.date
    df_work['year'] = timestamp_parsed.dt.year
    df_work['month'] = timestamp_parsed.dt.month
    df_work['day'] = timestamp_parsed.dt.day
    df_work['hour'] = timestamp_parsed.dt.hour
    df_work['minute'] = timestamp_parsed.dt.minute
    
    # Reportar estadísticas
    registros_validos = timestamp_parsed.notna().sum()
    registros_invalidos = timestamp_parsed.isna().sum()
    
    print(f"    Registros con fecha válida: {registros_validos:,}")
    if registros_invalidos > 0:
        print(f"    ⚠ Registros con fecha inválida: {registros_invalidos:,}")
    
    return df_work


def validar_subproject_name(subproject_name):
    """
    Valida que un subproject_name cumpla los criterios de formato.
    
    Criterios:
        - Exactamente 6 caracteres
        - No vacío, no 'nan', no None
        - Formato YYYY_N donde:
            * YYYY es un año de 4 dígitos >= 2020
            * _ es guión bajo
            * N es un dígito único (1-9)
    
    Args:
        subproject_name (str): Nombre del subproyecto a validar
    
    Returns:
        bool: True si es válido, False si no cumple criterios
    """
    if pd.isna(subproject_name):
        return False
    
    subproject_str = str(subproject_name).strip()
    
    # Verificar longitud exacta de 6 caracteres
    if len(subproject_str) != 6:
        return False
    
    # Verificar que no sea 'nan' o vacío
    if subproject_str == 'nan' or subproject_str == '':
        return False
    
    # Verificar formato YYYY_N exacto
    try:
        # Debe tener exactamente un guión bajo en posición 4
        if subproject_str[4] != '_':
            return False
        
        # Dividir por guión bajo
        partes = subproject_str.split('_')
        
        # Debe tener exactamente 2 partes
        if len(partes) != 2:
            return False
        
        year_str, num_str = partes
        
        # Validar que año sea 4 dígitos
        if len(year_str) != 4 or not year_str.isdigit():
            return False
        
        # Validar que número sea 1 dígito
        if len(num_str) != 1 or not num_str.isdigit():
            return False
        
        # Validar año >= 2020
        year = int(year_str)
        if year < 2020:
            return False
        
    except (ValueError, IndexError):
        return False
    
    return True


# ===============================================================================
# FILTRADO DE DATOS
# ===============================================================================

def filtrar_fechas_inconsistentes(df, columna_fecha='photo_datetime', columna_subproject='subproject_name'):
    """
    Filtra registros con fechas inconsistentes con el año del evento.
    
    Problema común: Eventos 2025_1 que contienen datos de 2019 con timestamps
    por defecto (2019-01-01 00:00:00) cuando la fecha real no está disponible.
    
    Criterio de filtrado:
        - Si subproject_name = YYYY_N, entonces año de photo_datetime debe ser >= YYYY - 1
        - Permite 1 año de tolerancia hacia atrás (ej: evento 2025_1 acepta desde 2024)
        - Rechaza datos con años muy anteriores (2019, 2020 en evento 2025_1)
    
    Args:
        df (pd.DataFrame): DataFrame con columnas photo_datetime y subproject_name
        columna_fecha (str): Nombre de la columna con timestamp
        columna_subproject (str): Nombre de la columna con evento (YYYY_N)
    
    Returns:
        pd.DataFrame: DataFrame filtrado sin fechas inconsistentes
    """
    if columna_fecha not in df.columns or columna_subproject not in df.columns:
        print(f"  ⚠ Columnas {columna_fecha} o {columna_subproject} no encontradas")
        return df
    
    # CRÍTICO: Verificar y eliminar columnas duplicadas ANTES del filtrado
    if df.columns.duplicated().any():
        duplicadas = df.columns[df.columns.duplicated()].tolist()
        print(f"  ⚠ Columnas duplicadas detectadas: {set(duplicadas)}")
        print(f"    Eliminando duplicados...")
        df = df.loc[:, ~df.columns.duplicated()]
    
    registros_iniciales = len(df)
    
    # Verificar que la columna es datetime
    if not pd.api.types.is_datetime64_any_dtype(df[columna_fecha]):
        print(f"  ⚠ Columna {columna_fecha} no es datetime, convirtiendo...")
        df[columna_fecha] = pd.to_datetime(df[columna_fecha], errors='coerce')
    
    # Extraer año de la fecha (acceder como Serie)
    year_photo = df[columna_fecha].dt.year
    
    # Extraer año del subproject_name (primeros 4 caracteres)
    year_subproject = df[columna_subproject].astype(str).str[:4]
    year_subproject = pd.to_numeric(year_subproject, errors='coerce')
    
    # Calcular diferencia de años (debe ser <= 1 año hacia atrás)
    year_diff = year_subproject - year_photo
    
    # Filtrar: mantener solo registros donde la diferencia es razonable
    # Criterio: año_subproject - año_photo <= 1 (permite 1 año de tolerancia)
    # Y año_photo no debe ser NaT
    mask_valido = (
        (year_diff <= 1) & 
        (year_photo.notna()) &
        (year_subproject.notna())
    )
    
    df_filtrado = df[mask_valido].copy()
    
    registros_finales = len(df_filtrado)
    registros_eliminados = registros_iniciales - registros_finales
    
    if registros_eliminados > 0:
        pct_eliminado = (registros_eliminados / registros_iniciales) * 100
        print(f"  ✓ Fechas inconsistentes filtradas: {registros_eliminados:,} ({pct_eliminado:.1f}%)")
    else:
        print(f"  ✓ No se encontraron fechas inconsistentes")
    
    return df_filtrado


def filtrar_por_subproject_valido(df, columna='subproject_name'):
    """
    Filtra el DataFrame para mantener solo registros con subproject_name válido.
    
    Excluye:
        - subproject_name = nan, None, vacío
        - subproject_name != 6 caracteres (ej: 2025_1.2, 2025_1.3)
        - subproject_name con año < 2020
    
    Args:
        df (pd.DataFrame): DataFrame con columna subproject_name
        columna (str): Nombre de la columna a validar
    
    Returns:
        pd.DataFrame: DataFrame filtrado solo con subproject_name válidos
    """
    if columna not in df.columns:
        print(f"  ⚠ Columna '{columna}' no encontrada, sin filtrado")
        return df
    
    registros_inicial = len(df)
    
    # Aplicar validación a cada registro
    mask_valido = df[columna].apply(validar_subproject_name)
    
    df_filtrado = df[mask_valido].copy()
    
    n_excluidos = registros_inicial - len(df_filtrado)
    
    if n_excluidos > 0:
        valores_excluidos = df[~mask_valido][columna].unique()
        print(f"    ⚠ Excluidos {n_excluidos:,} registros con {columna} inválido")
        print(f"      Valores excluidos: {sorted(set(map(str, valores_excluidos[:5])))}")
    
    return df_filtrado


def limpiar_registros_cv(df):
    """
    Elimina registros con identificaciones no válidas del sistema de visión computacional.
    
    Args:
        df (pd.DataFrame): DataFrame con columnas genus y species
        
    Returns:
        pd.DataFrame: DataFrame limpio sin registros CV inválidos
    """
    if 'genus' not in df.columns or 'species' not in df.columns:
        print("  ⚠ Columnas 'genus' o 'species' no encontradas, sin limpieza CV")
        return df
    
    registros_inicial = len(df)
    
    # Eliminar registros sin identificación
    df_clean = df.dropna(subset=["genus", "species"], how="any")
    
    # Filtrar valores no válidos del CV
    mask1 = df_clean["genus"].isin(["No CV Result", "Unknown"])
    mask2 = df_clean["species"].isin(["No CV Result", "Unknown"])
    df_clean = df_clean[~mask1 & ~mask2]
    
    n_eliminados = registros_inicial - len(df_clean)
    
    if n_eliminados > 0:
        print(f"    Registros eliminados (nulos/CV inválidos): {n_eliminados:,}")
    
    return df_clean


# ===============================================================================
# CREACIÓN DE DIRECTORIOS
# ===============================================================================

def crear_directorio_salida(output_path):
    """
    Crea el directorio de salida si no existe.
    
    Args:
        output_path (str): Ruta del directorio a crear
    """
    os.makedirs(output_path, exist_ok=True)
    print(f"  ✓ Directorio de salida: {output_path}")


def limpiar_directorio_salida(output_path):
    """
    Limpia el directorio de salida eliminando archivos existentes.
    
    Args:
        output_path (str): Ruta del directorio a limpiar
    """
    import shutil
    
    if os.path.exists(output_path):
        archivos_existentes = os.listdir(output_path)
        
        if archivos_existentes:
            print(f"  ⚠ Eliminando {len(archivos_existentes)} archivos existentes...")
            shutil.rmtree(output_path)
    
    os.makedirs(output_path, exist_ok=True)
    print("  ✓ Carpeta de salida limpia y lista")


# ===============================================================================
# OPERACIONES CON GEOPANDAS
# ===============================================================================

def cargar_shapefile(shapefile_path):
    """
    Carga un shapefile de manera robusta.
    
    Args:
        shapefile_path (str): Ruta al archivo .shp
        
    Returns:
        gpd.GeoDataFrame: GeoDataFrame o None si hay error
    """
    if not os.path.exists(shapefile_path):
        print(f"  ✗ Shapefile no encontrado: {shapefile_path}")
        return None
    
    try:
        gdf = gpd.read_file(shapefile_path)
        print(f"  ✓ Shapefile cargado: {len(gdf)} polígonos")
        return gdf
    except Exception as e:
        print(f"  ✗ Error al cargar shapefile: {e}")
        return None


# ===============================================================================
# UTILIDADES DE REPORTE
# ===============================================================================

def reportar_estadisticas_dataframe(df, nombre="DataFrame"):
    """
    Imprime estadísticas básicas de un DataFrame.
    
    Args:
        df (pd.DataFrame): DataFrame a analizar
        nombre (str): Nombre del DataFrame para el reporte
    """
    print(f"\n  📊 Estadísticas de {nombre}:")
    print(f"    Registros: {len(df):,}")
    print(f"    Columnas: {len(df.columns)}")
    
    # Especies únicas (si existe la columna)
    if 'sp_binomial' in df.columns:
        print(f"    Especies únicas: {df['sp_binomial'].nunique()}")
    
    # Proyectos únicos (si existe la columna)
    if 'project_id' in df.columns:
        print(f"    Proyectos únicos: {df['project_id'].nunique()}")
    
    # Eventos únicos (si existe la columna)
    if 'subproject_name' in df.columns:
        print(f"    Eventos únicos: {df['subproject_name'].nunique()}")
    
    # Despliegues únicos (si existe la columna)
    if 'deployment_name' in df.columns:
        print(f"    Despliegues únicos: {df['deployment_name'].nunique()}")


def validar_columnas_requeridas(df, columnas_requeridas, nombre="DataFrame"):
    """
    Valida que un DataFrame tenga las columnas requeridas.
    
    Args:
        df (pd.DataFrame): DataFrame a validar
        columnas_requeridas (list): Lista de nombres de columnas requeridas
        nombre (str): Nombre del DataFrame para mensajes
        
    Returns:
        bool: True si todas las columnas están presentes
    """
    columnas_faltantes = set(columnas_requeridas) - set(df.columns)
    
    if columnas_faltantes:
        print(f"  ✗ {nombre}: Columnas faltantes: {columnas_faltantes}")
        return False
    
    print(f"  ✓ {nombre}: Todas las columnas requeridas presentes")
    return True
