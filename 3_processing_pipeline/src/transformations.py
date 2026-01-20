"""
Transformaciones de datos para el pipeline de procesamiento.
Funciones de enriquecimiento, merge, agregación y análisis espacial.
"""
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point


# ===============================================================================
# MAPEO DE COLUMNAS
# ===============================================================================

# Mapeo de columnas del formato Wildlife Insights al formato interno
COLUMN_MAPPING = {
    "deployment_id": "deployment_name",
    "timestamp": "photo_datetime",
    "start_date": "sensor_start_date_and_time",
    "end_date": "sensor_end_date_and_time",
    "scientific_name": "sp_binomial"
}


# ===============================================================================
# ENRIQUECIMIENTO DE DATOS
# ===============================================================================

def crear_nombre_cientifico(df):
    """
    Crea columna sp_binomial combinando genus y species.
    
    Args:
        df (pd.DataFrame): DataFrame con columnas genus y species
        
    Returns:
        pd.DataFrame: DataFrame con columna sp_binomial agregada
    """
    if 'genus' in df.columns and 'species' in df.columns:
        df['sp_binomial'] = df['genus'] + " " + df['species']
        print("  ✓ Columna 'sp_binomial' creada")
    else:
        print("  ⚠ Columnas 'genus' o 'species' no encontradas")
    
    return df


def agregar_metadata_administrativa(df, admin_name="", organization="Instituto Humboldt"):
    """
    Agrega información administrativa estándar al DataFrame.
    
    Args:
        df (pd.DataFrame): DataFrame a enriquecer
        admin_name (str): Nombre del administrador del proyecto
        organization (str): Nombre de la organización
        
    Returns:
        pd.DataFrame: DataFrame con columnas administrativas
    """
    df['project_admin'] = admin_name
    df['project_admin_organization'] = organization
    
    print(f"  ✓ Metadata administrativa agregada: {organization}")
    
    return df


def renombrar_columnas_wi(df):
    """
    Renombra columnas según el mapeo de Wildlife Insights.
    
    Args:
        df (pd.DataFrame): DataFrame con columnas originales
        
    Returns:
        pd.DataFrame: DataFrame con columnas renombradas
    """
    columnas_renombradas = []
    
    for old_name, new_name in COLUMN_MAPPING.items():
        if old_name in df.columns:
            df = df.rename(columns={old_name: new_name})
            columnas_renombradas.append(f"{old_name} → {new_name}")
    
    if columnas_renombradas:
        print(f"  ✓ Columnas renombradas: {len(columnas_renombradas)}")
    
    return df


# ===============================================================================
# MERGE DE DATOS
# ===============================================================================

def merge_images_deployments(images_df, deployments_df):
    """
    Combina datos de imágenes con información de despliegues.
    
    Args:
        images_df (pd.DataFrame): DataFrame con imágenes
        deployments_df (pd.DataFrame): DataFrame con deployments
        
    Returns:
        pd.DataFrame: DataFrame combinado
    """
    print("  Realizando merge entre imágenes y deployments...")
    
    registros_inicial = len(images_df)
    
    # Merge por project_id y deployment_id (antes de renombrar)
    df_merged = pd.merge(
        images_df, 
        deployments_df, 
        on=["project_id", "deployment_id"], 
        how="left"
    )
    
    # Ahora aplicar el mapeo de columnas al resultado del merge
    df_merged = renombrar_columnas_wi(df_merged)
    
    registros_final = len(df_merged)
    
    print(f"    Registros antes del merge: {registros_inicial:,}")
    print(f"    Registros después del merge: {registros_final:,}")
    
    # Verificar registros sin match (usar deployment_name después del mapeo)
    if 'deployment_name' in df_merged.columns:
        registros_sin_deployment = df_merged['deployment_name'].isna().sum()
        if registros_sin_deployment > 0:
            print(f"    ⚠ Registros sin deployment asociado: {registros_sin_deployment:,}")
    
    return df_merged


def merge_with_projects(df, projects_df):
    """
    Agrega información de proyectos al DataFrame principal.
    
    Args:
        df (pd.DataFrame): DataFrame principal
        projects_df (pd.DataFrame): DataFrame con información de proyectos
        
    Returns:
        pd.DataFrame: DataFrame enriquecido con project_name
    """
    if 'project_id' not in df.columns:
        print("  ⚠ Columna 'project_id' no encontrada, sin merge con projects")
        return df
    
    if 'project_id' not in projects_df.columns:
        print("  ⚠ projects_df sin columna 'project_id', sin merge")
        return df
    
    # Seleccionar columnas relevantes de projects
    projects_subset = projects_df[['project_id', 'project_name']].copy()
    
    df_merged = df.merge(projects_subset, on='project_id', how='left')
    
    print("  ✓ Información de proyectos agregada (project_name)")
    
    return df_merged


# ===============================================================================
# ANÁLISIS GEOGRÁFICO
# ===============================================================================

def asignar_corporacion_geografica(deployments_df, shapefile_path):
    """
    Asigna Corporación a cada proyecto basado en análisis geográfico.
    
    Proceso:
    1. Lee shapefile con polígonos de CARs
    2. Realiza análisis espacial punto-en-polígono
    3. Agrega a nivel de proyecto usando moda (valor más frecuente)
    
    Args:
        deployments_df (pd.DataFrame): DataFrame con deployment_id, project_id, longitude, latitude
        shapefile_path (str): Ruta al archivo shapefile con polígonos de CARs
    
    Returns:
        pd.DataFrame: DataFrame con project_id y Corporacion asignada
    """
    print("\n  Realizando análisis geográfico para asignar Corporaciones...")
    
    try:
        # 1. Verificar que existe el shapefile
        import os
        if not os.path.exists(shapefile_path):
            print(f"    ✗ Shapefile no encontrado: {shapefile_path}")
            print("    ⚠ Se asignará NULL a todos los proyectos")
            return crear_corporaciones_null(deployments_df)
        
        # 2. Leer shapefile
        gdf_cars = gpd.read_file(shapefile_path)
        
        if 'NOMBRE_CAR' not in gdf_cars.columns:
            print("    ✗ Columna 'NOMBRE_CAR' no encontrada en shapefile")
            print(f"    Columnas disponibles: {list(gdf_cars.columns)}")
            return crear_corporaciones_null(deployments_df)
        
        print(f"    ✓ Shapefile cargado: {gdf_cars['NOMBRE_CAR'].nunique()} Corporaciones")
        
        # 3. Preparar deployments con coordenadas válidas
        deps = deployments_df[['deployment_id', 'project_id', 'longitude', 'latitude']].copy()
        deps_validos = deps.dropna(subset=['longitude', 'latitude'])
        
        if len(deps_validos) == 0:
            print("    ✗ No hay deployments con coordenadas válidas")
            return crear_corporaciones_null(deployments_df)
        
        print(f"    Deployments con coordenadas válidas: {len(deps_validos):,}")
        
        # 4. Crear GeoDataFrame de puntos
        geometry = [Point(xy) for xy in zip(deps_validos['longitude'], deps_validos['latitude'])]
        gdf_deployments = gpd.GeoDataFrame(deps_validos, geometry=geometry, crs="EPSG:4326")
        
        # 5. Spatial join (point-in-polygon)
        print("    Ejecutando análisis espacial punto-en-polígono...")
        joined = gpd.sjoin(gdf_deployments, gdf_cars[['NOMBRE_CAR', 'geometry']], 
                          how='left', predicate='within')
        
        # 6. Extraer resultado
        deployment_corps = joined[['deployment_id', 'project_id', 'NOMBRE_CAR']].copy()
        deployment_corps.rename(columns={'NOMBRE_CAR': 'Corporacion'}, inplace=True)
        
        # 7. Agregar a nivel de proyecto (moda)
        project_corps = deployment_corps.groupby('project_id')['Corporacion'].agg(
            lambda x: x.mode()[0] if len(x.mode()) > 0 and pd.notna(x.mode()[0]) else None
        ).reset_index()
        
        # 8. Reportar estadísticas
        n_asignados = project_corps['Corporacion'].notna().sum()
        n_total = len(project_corps)
        
        print(f"    ✓ Proyectos con Corporación asignada: {n_asignados}/{n_total} ({n_asignados/n_total*100:.1f}%)")
        
        # Mostrar distribución de Corporaciones
        if n_asignados > 0:
            dist_corps = project_corps['Corporacion'].value_counts()
            print(f"    Distribución de Corporaciones:")
            for corp, count in dist_corps.items():
                if pd.notna(corp):
                    print(f"      • {corp}: {count} proyectos")
        
        return project_corps
        
    except Exception as e:
        print(f"    ✗ Error en análisis geográfico: {e}")
        print(f"    ⚠ Se asignará NULL a todos los proyectos")
        return crear_corporaciones_null(deployments_df)


def crear_corporaciones_null(deployments_df):
    """
    Crea DataFrame de corporaciones con valores NULL.
    
    Args:
        deployments_df (pd.DataFrame): DataFrame con project_id
        
    Returns:
        pd.DataFrame: DataFrame con project_id y Corporacion=None
    """
    project_ids = deployments_df['project_id'].unique()
    
    return pd.DataFrame({
        'project_id': project_ids,
        'Corporacion': None
    })


# ===============================================================================
# CÁLCULO DE ESTADÍSTICAS
# ===============================================================================

def calcular_deployment_days(df):
    """
    Calcula deployment_days a partir de sensor_start_date y sensor_end_date.
    
    Args:
        df (pd.DataFrame): DataFrame con columnas de fechas de sensor
        
    Returns:
        pd.DataFrame: DataFrame con columna deployment_days
    """
    # Mapeo de nombres alternativos de columnas
    start_col = None
    end_col = None
    
    # Buscar columnas de inicio
    for col in ['sensor_start_date', 'sensor_start_date_and_time', 'start_date']:
        if col in df.columns:
            start_col = col
            break
    
    # Buscar columnas de fin
    for col in ['sensor_end_date', 'sensor_end_date_and_time', 'end_date']:
        if col in df.columns:
            end_col = col
            break
    
    if start_col is None or end_col is None:
        print("  ⚠ Columnas de fechas de sensor no encontradas, deployment_days = 0")
        df['deployment_days'] = 0
        return df
    
    try:
        # Convertir a datetime
        df['sensor_start_date'] = pd.to_datetime(df[start_col], errors='coerce')
        df['sensor_end_date'] = pd.to_datetime(df[end_col], errors='coerce')
        
        # Calcular diferencia en días
        df['deployment_days'] = (df['sensor_end_date'] - df['sensor_start_date']).dt.days
        
        # Reemplazar negativos o NaN por 0
        df['deployment_days'] = df['deployment_days'].fillna(0)
        df['deployment_days'] = df['deployment_days'].apply(lambda x: max(0, int(x)))
        
        print(f"  ✓ deployment_days calculado (promedio: {df['deployment_days'].mean():.1f} días)")
        
    except Exception as e:
        print(f"  ⚠ Error al calcular deployment_days: {e}")
        df['deployment_days'] = 0
    
    return df


# ===============================================================================
# SELECCIÓN DE COLUMNAS
# ===============================================================================

def seleccionar_columnas_observations(df):
    """
    Selecciona y ordena columnas para la tabla observations.parquet.
    
    Args:
        df (pd.DataFrame): DataFrame consolidado
        
    Returns:
        pd.DataFrame: DataFrame con columnas seleccionadas
    """
    columnas_requeridas = [
        # Filtros del Dashboard
        'project_id',
        'project_name',
        'Corporacion',
        'subproject_name',
        
        # Identificación Espacial
        'deployment_id',
        'deployment_name',
        'placename',
        'latitude',
        'longitude',
        
        # Taxonomía
        'sp_binomial',
        'genus',
        'species',
        'class',
        
        # Temporalidad
        'photo_datetime',
        'photo_date',
        'hour',
        
        # Metadata del Sensor
        'sensor_start_date',
        'sensor_end_date',
        'deployment_days',
        
        # Administración
        'project_admin',
    ]
    
    # Seleccionar solo columnas que existen
    columnas_existentes = [col for col in columnas_requeridas if col in df.columns]
    columnas_faltantes = set(columnas_requeridas) - set(columnas_existentes)
    
    if columnas_faltantes:
        print(f"  ⚠ Columnas faltantes (se omitirán): {columnas_faltantes}")
    
    df_final = df[columnas_existentes].copy()
    
    print(f"  ✓ Columnas seleccionadas: {len(columnas_existentes)}/{len(columnas_requeridas)}")
    
    return df_final


def seleccionar_columnas_deployments(df):
    """
    Selecciona columnas para la tabla deployments.parquet.
    
    Args:
        df (pd.DataFrame): DataFrame de deployments
        
    Returns:
        pd.DataFrame: DataFrame con columnas seleccionadas
    """
    columnas_requeridas = [
        'deployment_id',
        'deployment_name',
        'project_id',
        'project_name',
        'Corporacion',
        'subproject_name',
        'placename',
        'latitude',
        'longitude',
        'sensor_start_date',
        'sensor_end_date',
        'deployment_days',
    ]
    
    # Seleccionar solo columnas que existen
    columnas_existentes = [col for col in columnas_requeridas if col in df.columns]
    columnas_faltantes = set(columnas_requeridas) - set(columnas_existentes)
    
    if columnas_faltantes:
        print(f"  ⚠ Columnas faltantes en deployments (se omitirán): {columnas_faltantes}")
    
    # Eliminar duplicados por deployment_id
    df_final = df[columnas_existentes].drop_duplicates(subset=['deployment_id']).copy()
    
    print(f"  ✓ Columnas seleccionadas: {len(columnas_existentes)}/{len(columnas_requeridas)}")
    print(f"  ✓ Deployments únicos: {len(df_final):,}")
    
    return df_final
