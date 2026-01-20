"""
Generación de archivos Parquet para el dashboard.
Funciones de exportación de las 3 tablas esenciales.
"""
import pandas as pd
import os


# ===============================================================================
# GENERACIÓN DE OBSERVATIONS.PARQUET
# ===============================================================================

def generar_observations_parquet(df, output_path):
    """
    Genera el archivo observations.parquet con todas las observaciones.
    
    Args:
        df (pd.DataFrame): DataFrame con observaciones procesadas
        output_path (str): Ruta completa del archivo de salida
        
    Returns:
        bool: True si la exportación fue exitosa
    """
    print("\n=== Generando observations.parquet ===")
    
    try:
        # Validar que el DataFrame no esté vacío
        if df.empty:
            print("  ✗ DataFrame vacío, no se puede generar observations.parquet")
            return False
        
        # Ordenar por columnas de filtro para optimizar queries
        print("  Ordenando datos para optimizar consultas...")
        df_sorted = df.sort_values([
            'project_id', 
            'Corporacion', 
            'subproject_name',
            'deployment_name',
            'photo_datetime'
        ], na_position='last')
        
        # Optimizar tipos de datos
        print("  Optimizando tipos de datos...")
        df_optimized = optimizar_tipos_datos(df_sorted)
        
        # Exportar a Parquet
        print(f"  Exportando a: {output_path}")
        df_optimized.to_parquet(
            output_path,
            engine='pyarrow',
            compression='snappy',
            index=False
        )
        
        # Verificar tamaño del archivo
        tamaño_mb = os.path.getsize(output_path) / (1024 * 1024)
        
        print(f"  ✓ observations.parquet generado exitosamente")
        print(f"    Registros: {len(df_optimized):,}")
        print(f"    Columnas: {len(df_optimized.columns)}")
        print(f"    Tamaño: {tamaño_mb:.2f} MB")
        
        # Reportar estadísticas clave
        if 'sp_binomial' in df_optimized.columns:
            print(f"    Especies únicas: {df_optimized['sp_binomial'].nunique()}")
        if 'project_id' in df_optimized.columns:
            print(f"    Proyectos únicos: {df_optimized['project_id'].nunique()}")
        if 'subproject_name' in df_optimized.columns:
            print(f"    Eventos únicos: {df_optimized['subproject_name'].nunique()}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error al generar observations.parquet: {e}")
        return False


# ===============================================================================
# GENERACIÓN DE DEPLOYMENTS.PARQUET
# ===============================================================================

def generar_deployments_parquet(df_observations, df_deployments, output_path):
    """
    Genera el archivo deployments.parquet con metadata de despliegues.
    
    Args:
        df_observations (pd.DataFrame): DataFrame de observaciones (para enriquecer)
        df_deployments (pd.DataFrame): DataFrame de deployments procesados
        output_path (str): Ruta completa del archivo de salida
        
    Returns:
        bool: True si la exportación fue exitosa
    """
    print("\n=== Generando deployments.parquet ===")
    
    try:
        # Validar que el DataFrame no esté vacío
        if df_deployments.empty:
            print("  ✗ DataFrame de deployments vacío")
            return False
        
        # Calcular estadísticas por deployment desde observations
        print("  Calculando estadísticas por deployment...")
        deployment_stats = calcular_estadisticas_deployment(df_observations)
        
        # Determinar columna de deployment en cada DataFrame
        # df_deployments tiene deployment_id (del CSV original)
        # deployment_stats tiene deployment_name (después del renombrado)
        # Necesitamos hacer el merge correctamente
        
        # Si deployments tiene deployment_id, debemos renombrarlo temporalmente para el merge
        if 'deployment_id' in df_deployments.columns and 'deployment_name' in deployment_stats.columns:
            # Crear columna deployment_name en df_deployments para el merge
            df_deployments_merge = df_deployments.copy()
            df_deployments_merge['deployment_name'] = df_deployments_merge['deployment_id']
            merge_col = 'deployment_name'
        elif 'deployment_name' in df_deployments.columns:
            df_deployments_merge = df_deployments
            merge_col = 'deployment_name'
        else:
            df_deployments_merge = df_deployments
            merge_col = 'deployment_id'
        
        # Merge con deployments base
        df_final = df_deployments_merge.merge(
            deployment_stats, 
            on=merge_col, 
            how='left'
        )
        
        # Ordenar por project_id y la columna de deployment
        order_cols = ['project_id']
        if 'deployment_id' in df_final.columns:
            order_cols.append('deployment_id')
        elif 'deployment_name' in df_final.columns:
            order_cols.append('deployment_name')
        
        df_final = df_final.sort_values(order_cols)
        
        # Optimizar tipos de datos
        df_final = optimizar_tipos_datos(df_final)
        
        # Exportar a Parquet
        print(f"  Exportando a: {output_path}")
        df_final.to_parquet(
            output_path,
            engine='pyarrow',
            compression='snappy',
            index=False
        )
        
        # Verificar tamaño del archivo
        tamaño_mb = os.path.getsize(output_path) / (1024 * 1024)
        
        print(f"  ✓ deployments.parquet generado exitosamente")
        print(f"    Deployments: {len(df_final):,}")
        print(f"    Columnas: {len(df_final.columns)}")
        print(f"    Tamaño: {tamaño_mb:.2f} MB")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error al generar deployments.parquet: {e}")
        return False


# ===============================================================================
# GENERACIÓN DE PROJECTS.PARQUET
# ===============================================================================

def generar_projects_parquet(df_observations, df_projects_base, output_path):
    """
    Genera el archivo projects.parquet con catálogo de proyectos.
    
    Args:
        df_observations (pd.DataFrame): DataFrame de observaciones (para calcular estadísticas)
        df_projects_base (pd.DataFrame): DataFrame base de proyectos
        output_path (str): Ruta completa del archivo de salida
        
    Returns:
        bool: True si la exportación fue exitosa
    """
    print("\n=== Generando projects.parquet ===")
    
    try:
        # Calcular estadísticas por proyecto
        print("  Calculando estadísticas por proyecto...")
        project_stats = calcular_estadisticas_proyecto(df_observations)
        
        # Crear catálogo de proyectos
        if df_projects_base is not None and not df_projects_base.empty:
            # Merge con información base de proyectos
            df_final = df_projects_base.merge(
                project_stats,
                on='project_id',
                how='right'  # Mantener solo proyectos con datos
            )
        else:
            # Usar solo estadísticas calculadas
            df_final = project_stats
        
        # Ordenar por project_id
        df_final = df_final.sort_values('project_id')
        
        # Optimizar tipos de datos
        df_final = optimizar_tipos_datos(df_final)
        
        # Exportar a Parquet
        print(f"  Exportando a: {output_path}")
        df_final.to_parquet(
            output_path,
            engine='pyarrow',
            compression='snappy',
            index=False
        )
        
        # Verificar tamaño del archivo
        tamaño_mb = os.path.getsize(output_path) / (1024 * 1024)
        
        print(f"  ✓ projects.parquet generado exitosamente")
        print(f"    Proyectos: {len(df_final):,}")
        print(f"    Columnas: {len(df_final.columns)}")
        print(f"    Tamaño: {tamaño_mb:.2f} MB")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error al generar projects.parquet: {e}")
        return False


# ===============================================================================
# FUNCIONES AUXILIARES
# ===============================================================================

def calcular_estadisticas_deployment(df_observations):
    """
    Calcula estadísticas por deployment desde observations.
    
    Args:
        df_observations (pd.DataFrame): DataFrame de observaciones
        
    Returns:
        pd.DataFrame: DataFrame con deployment_name y estadísticas
    """
    # Usar deployment_name que es el resultado del renombrado de deployment_id
    deployment_col = 'deployment_name' if 'deployment_name' in df_observations.columns else 'deployment_id'
    
    if deployment_col not in df_observations.columns:
        print(f"  ⚠ Columna '{deployment_col}' no encontrada")
        return pd.DataFrame(columns=[deployment_col])
    
    stats = df_observations.groupby(deployment_col).agg(
        total_photos=(deployment_col, 'count'),
        species_count=('sp_binomial', 'nunique') if 'sp_binomial' in df_observations.columns else (deployment_col, lambda x: 0)
    ).reset_index()
    
    print(f"    Estadísticas calculadas para {len(stats):,} deployments")
    
    return stats


def calcular_estadisticas_proyecto(df_observations):
    """
    Calcula estadísticas por proyecto desde observations.
    
    Args:
        df_observations (pd.DataFrame): DataFrame de observaciones
        
    Returns:
        pd.DataFrame: DataFrame con project_id, subproject_names y estadísticas
    """
    if 'project_id' not in df_observations.columns:
        print("  ⚠ Columna 'project_id' no encontrada")
        return pd.DataFrame(columns=['project_id'])
    
    # Agregar estadísticas por proyecto
    # Preparar fecha como datetime si existe
    date_col = None
    if 'photo_datetime' in df_observations.columns:
        df_observations_copy = df_observations.copy()
        df_observations_copy['photo_datetime_dt'] = pd.to_datetime(df_observations_copy['photo_datetime'], errors='coerce')
        date_col = 'photo_datetime_dt'
    else:
        df_observations_copy = df_observations
    
    agg_dict = {
        'total_photos': ('project_id', 'count')
    }
    
    if 'sp_binomial' in df_observations_copy.columns:
        agg_dict['total_species'] = ('sp_binomial', 'nunique')
    
    if date_col:
        agg_dict['project_start_date'] = (date_col, 'min')
        agg_dict['project_end_date'] = (date_col, 'max')
    
    stats = df_observations_copy.groupby('project_id').agg(**agg_dict).reset_index()
    
    # Agregar lista de subproject_names
    if 'subproject_name' in df_observations.columns:
        subproject_names = df_observations.groupby('project_id')['subproject_name'].apply(
            lambda x: ', '.join(sorted(x.unique().astype(str)))
        ).reset_index()
        
        stats = stats.merge(subproject_names, on='project_id', how='left')
    
    # Agregar project_name si existe
    if 'project_name' in df_observations.columns:
        project_names = df_observations[['project_id', 'project_name']].drop_duplicates()
        stats = stats.merge(project_names, on='project_id', how='left')
    
    # Agregar Corporacion si existe
    if 'Corporacion' in df_observations.columns:
        corporaciones = df_observations[['project_id', 'Corporacion']].drop_duplicates()
        stats = stats.merge(corporaciones, on='project_id', how='left')
    
    print(f"    Estadísticas calculadas para {len(stats):,} proyectos")
    
    return stats


def optimizar_tipos_datos(df):
    """
    Optimiza tipos de datos del DataFrame para reducir tamaño.
    
    Args:
        df (pd.DataFrame): DataFrame a optimizar
        
    Returns:
        pd.DataFrame: DataFrame optimizado
    """
    df_optimized = df.copy()
    
    # Optimizar columnas categóricas (pocas categorías únicas)
    for col in df_optimized.columns:
        if df_optimized[col].dtype == 'object':
            num_unique = df_optimized[col].nunique()
            num_total = len(df_optimized)
            
            # Si tiene menos del 50% de valores únicos, convertir a category
            if num_unique / num_total < 0.5:
                df_optimized[col] = df_optimized[col].astype('category')
    
    # Optimizar columnas numéricas enteras
    for col in df_optimized.select_dtypes(include=['int64']).columns:
        col_min = df_optimized[col].min()
        col_max = df_optimized[col].max()
        
        # Usar int32 si el rango lo permite
        if col_min >= -2147483648 and col_max <= 2147483647:
            df_optimized[col] = df_optimized[col].astype('int32')
    
    return df_optimized


# ===============================================================================
# GENERACIÓN DE TODAS LAS TABLAS
# ===============================================================================

def generar_todas_las_tablas(observations_df, deployments_df, projects_df, output_dir):
    """
    Genera las 3 tablas Parquet esenciales para el dashboard.
    
    Args:
        observations_df (pd.DataFrame): DataFrame de observaciones procesadas
        deployments_df (pd.DataFrame): DataFrame de deployments procesados
        projects_df (pd.DataFrame): DataFrame de proyectos base
        output_dir (str): Directorio de salida
        
    Returns:
        dict: Diccionario con éxito/falla de cada tabla
    """
    print("\n" + "="*70)
    print("GENERACIÓN DE ARCHIVOS PARQUET PARA EL DASHBOARD")
    print("="*70)
    
    resultados = {}
    
    # 1. observations.parquet
    observations_path = os.path.join(output_dir, 'observations.parquet')
    resultados['observations'] = generar_observations_parquet(observations_df, observations_path)
    
    # 2. deployments.parquet
    deployments_path = os.path.join(output_dir, 'deployments.parquet')
    resultados['deployments'] = generar_deployments_parquet(
        observations_df, 
        deployments_df, 
        deployments_path
    )
    
    # 3. projects.parquet
    projects_path = os.path.join(output_dir, 'projects.parquet')
    resultados['projects'] = generar_projects_parquet(
        observations_df,
        projects_df,
        projects_path
    )
    
    # Resumen final
    print("\n" + "="*70)
    print("RESUMEN DE GENERACIÓN")
    print("="*70)
    
    tablas_exitosas = sum(resultados.values())
    tablas_totales = len(resultados)
    
    for tabla, exito in resultados.items():
        estado = "✓ EXITOSO" if exito else "✗ FALLIDO"
        print(f"  {estado}: {tabla}.parquet")
    
    print(f"\n  Total: {tablas_exitosas}/{tablas_totales} tablas generadas")
    
    if tablas_exitosas == tablas_totales:
        print("\n  🎉 ¡Todas las tablas generadas exitosamente!")
    else:
        print("\n  ⚠ Algunas tablas no se generaron correctamente")
    
    return resultados
