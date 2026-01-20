"""
Pipeline de procesamiento de datos de cámaras trampa desde Wildlife Insights.

Este módulo orquesta el procesamiento de datos crudos de Wildlife Insights y genera
archivos Parquet optimizados para visualización en un dashboard de R/Shiny.

Arquitectura Modular:
    - src.utils: Utilidades de carga y filtrado de datos
    - src.transformations: Transformaciones y enriquecimiento de datos
    - src.generate_parquets: Generación de archivos Parquet
    - src.validation: Validación de calidad de datos

Flujo de procesamiento:
    1. Carga de datos crudos (proyectos, despliegues, imágenes)
    2. Filtrado y validación (subproject_name, registros CV)
    3. Enriquecimiento (nombres científicos, metadata administrativa)
    4. Análisis geográfico (asignación de CARs)
    5. Generación de 3 tablas Parquet:
       - observations.parquet: Datos granulares de observaciones
       - deployments.parquet: Metadata de despliegues
       - projects.parquet: Catálogo de proyectos con estadísticas
    6. Validación de calidad de datos

Entrada:
    - 1_Data_RAW_WI/projects.csv: Información maestra de proyectos
    - 1_Data_RAW_WI/deployments.csv: Despliegues de cámaras
    - 1_Data_RAW_WI/images_*.csv: Imágenes por proyecto (múltiples archivos)
    - 2_Data_Shapefiles_CARs/CAR_MPIO.shp: Shapefile de CARs

Salida:
    - observations.parquet: 20 columnas, datos de observaciones con filtros
    - deployments.parquet: 15 columnas, metadata de despliegues
    - projects.parquet: 10 columnas, catálogo de proyectos

Validación de proyectos:
    - subproject_name debe tener exactamente 6 caracteres (formato: YYYY_N)
    - Año >= 2020
    - Se excluyen: eventos vacíos, formato incorrecto, años antiguos

Author: Proyecto OTUS - Instituto Humboldt
Version: 3.0 (Arquitectura Modular)
Date: Enero 2025
"""

import os
import sys
import pandas as pd
from pathlib import Path

# Configurar encoding UTF-8 para Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Importar módulos del pipeline
from src.utils import (
    concatenar_archivos_csv,
    procesar_timestamps,
    filtrar_por_subproject_valido,
    filtrar_fechas_inconsistentes,
    limpiar_registros_cv
)
from src.transformations import (
    crear_nombre_cientifico,
    agregar_metadata_administrativa,
    merge_images_deployments,
    merge_with_projects,
    asignar_corporacion_geografica
)
from src.generate_parquets import generar_todas_las_tablas
from src.validation import (
    validar_observations_parquet,
    validar_deployments_parquet,
    validar_projects_parquet,
    generar_reporte_calidad
)

# ===============================================================================
# CONFIGURACIÓN GLOBAL
# ===============================================================================

# Rutas base (relativas a la ubicación de este script)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)  # Directorio raíz del proyecto (un nivel arriba)
BASE_RAW_PATH = os.path.join(PROJECT_ROOT, '1_Data_RAW_WI')
BASE_OUTPUT_PATH = os.path.join(PROJECT_ROOT, '4_Dashboard', 'dashboard_input_data')
SHAPEFILE_PATH = os.path.join(PROJECT_ROOT, '2_Data_Shapefiles_CARs', 'CAR_MPIO.shp')

# ===============================================================================
# FUNCIÓN PRINCIPAL DE PROCESAMIENTO
# ===============================================================================

def main():
    """
    Función principal que ejecuta el flujo completo de procesamiento modular.
    
    Flujo:
        1. Carga de datos crudos (proyectos, despliegues, imágenes)
        2. Filtrado y limpieza (subproject_name, CV)
        3. Enriquecimiento y transformaciones
        4. Análisis geográfico
        5. Generación de Parquets
        6. Validación de calidad
    """
    print("="*80)
    print("PIPELINE DE PROCESAMIENTO DE DATOS - WILDLIFE INSIGHTS")
    print("Arquitectura Modular - Generación de 3 tablas Parquet")
    print("="*80)
    
    # ===========================================================================
    # FASE 0: LIMPIEZA DE CARPETA DE SALIDA
    # ===========================================================================
    print("\n" + "="*80)
    print("FASE 0: PREPARACIÓN DEL ENTORNO")
    print("="*80)
    
    print("\n0.1 Limpiando carpeta de salida...")
    # Crear directorio si no existe
    if not os.path.exists(BASE_OUTPUT_PATH):
        os.makedirs(BASE_OUTPUT_PATH)
        print(f"  ✓ Directorio creado: {BASE_OUTPUT_PATH}")
    else:
        # Limpiar archivos .parquet existentes
        archivos_eliminados = 0
        for archivo in os.listdir(BASE_OUTPUT_PATH):
            if archivo.endswith('.parquet'):
                archivo_path = os.path.join(BASE_OUTPUT_PATH, archivo)
                try:
                    os.remove(archivo_path)
                    archivos_eliminados += 1
                except Exception as e:
                    print(f"  ⚠ No se pudo eliminar {archivo}: {e}")
        
        if archivos_eliminados > 0:
            print(f"  ✓ {archivos_eliminados} archivo(s) Parquet eliminado(s)")
        else:
            print(f"  ✓ Carpeta de salida vacía")
    
    # ===========================================================================
    # FASE 1: CARGA DE DATOS CRUDOS
    # ===========================================================================
    print("\n" + "="*80)
    print("FASE 1: CARGA DE DATOS CRUDOS")
    print("="*80)
    
    # 1.1 Cargar archivos de referencia
    print("\n1.1 Cargando archivos de referencia...")
    projects_path = os.path.join(BASE_RAW_PATH, 'projects.csv')
    deployments_path = os.path.join(BASE_RAW_PATH, 'deployments.csv')
    
    try:
        projects = pd.read_csv(projects_path)
        deployments = pd.read_csv(deployments_path)
        print(f"  ✓ projects.csv: {len(projects):,} proyectos")
        print(f"  ✓ deployments.csv: {len(deployments):,} despliegues")
    except Exception as e:
        print(f"  ✗ Error al cargar archivos de referencia: {e}")
        return False
    
    # 1.2 Cargar y concatenar imágenes
    print("\n1.2 Cargando archivos de imágenes...")
    images = concatenar_archivos_csv(
        folder_path=BASE_RAW_PATH,
        patron='images'
    )
    
    if images is None or images.empty:
        print("  ✗ No se pudieron cargar imágenes")
        return False
    
    print(f"  ✓ Imágenes cargadas: {len(images):,} registros")
    
    # ===========================================================================
    # FASE 2: FILTRADO Y LIMPIEZA
    # ===========================================================================
    print("\n" + "="*80)
    print("FASE 2: FILTRADO Y LIMPIEZA")
    print("="*80)
    
    # 2.1 Procesar timestamps
    print("\n2.1 Procesando timestamps...")
    images = procesar_timestamps(images)
    
    # 2.2 Limpiar registros CV
    print("\n2.2 Limpiando registros de Computer Vision...")
    registros_antes = len(images)
    images = limpiar_registros_cv(images)
    registros_despues = len(images)
    print(f"  ✓ Registros después de limpieza CV: {registros_despues:,} de {registros_antes:,}")
    
    # ===========================================================================
    # FASE 3: ENRIQUECIMIENTO Y TRANSFORMACIONES
    # ===========================================================================
    print("\n" + "="*80)
    print("FASE 3: ENRIQUECIMIENTO Y TRANSFORMACIONES")
    print("="*80)
    
    # 3.1 Crear nombre científico
    print("\n3.1 Creando nombres científicos...")
    images = crear_nombre_cientifico(images)
    
    # 3.2 Agregar metadata administrativa
    print("\n3.2 Agregando metadata administrativa...")
    images = agregar_metadata_administrativa(
        images,
        admin_name="",
        organization="Instituto Humboldt"
    )
    
    # 3.3 Merge con deployments
    print("\n3.3 Fusionando imágenes con deployments...")
    data = merge_images_deployments(images, deployments)
    print(f"  ✓ Registros después del merge: {len(data):,}")
    
    # 3.4 Filtrar por subproject_name válido (DESPUÉS del merge)
    print("\n3.4 Filtrando por subproject_name válido (YYYY_N, año >= 2020)...")
    registros_antes = len(data)
    data = filtrar_por_subproject_valido(data)
    registros_despues = len(data)
    print(f"  ✓ Registros filtrados: {registros_despues:,} de {registros_antes:,}")
    
    if data.empty:
        print("  ✗ No hay registros válidos después del filtrado")
        return False
    
    # 3.5 Filtrar fechas inconsistentes con evento (ej: 2025_1 con datos de 2019)
    print("\n3.5 Filtrando fechas inconsistentes con evento...")
    registros_antes = len(data)
    data = filtrar_fechas_inconsistentes(data, columna_fecha='photo_datetime', columna_subproject='subproject_name')
    registros_despues = len(data)
    print(f"  ✓ Registros filtrados: {registros_despues:,} de {registros_antes:,}")
    
    if data.empty:
        print("  ✗ No hay registros válidos después del filtrado de fechas")
        return False
    
    # 3.6 Merge con projects
    print("\n3.6 Fusionando con información de proyectos...")
    data = merge_with_projects(data, projects)
    print(f"  ✓ Registros finales: {len(data):,}")
    
    # ===========================================================================
    # FASE 4: ANÁLISIS GEOGRÁFICO
    # ===========================================================================
    print("\n" + "="*80)
    print("FASE 4: ANÁLISIS GEOGRÁFICO")
    print("="*80)
    
    # 4.1 Asignar Corporaciones geográficamente
    print("\n4.1 Asignando Corporaciones por análisis geográfico...")
    # La función retorna corporaciones a nivel de proyecto (project_id, Corporacion)
    project_corporaciones = asignar_corporacion_geografica(
        deployments_df=deployments,
        shapefile_path=SHAPEFILE_PATH
    )
    
    # Hacer merge por project_id para agregar la columna Corporacion
    data = data.merge(
        project_corporaciones[['project_id', 'Corporacion']],
        on='project_id',
        how='left'
    )
    
    corporaciones_asignadas = data['Corporacion'].notna().sum()
    print(f"  ✓ Corporaciones asignadas: {corporaciones_asignadas:,} observaciones")
    
    # ===========================================================================
    # FASE 4.5: PREPARACIÓN FINAL DE DATOS
    # ===========================================================================
    print("\n" + "="*80)
    print("FASE 4.5: PREPARACIÓN FINAL DE DATOS")
    print("="*80)
    
    # 4.5.1 Calcular deployment_days
    print("\n4.5.1 Calculando deployment_days...")
    from src.transformations import calcular_deployment_days
    data = calcular_deployment_days(data)
    
    # 4.5.2 Diagnosticar columnas duplicadas
    print("\n4.5.2 Diagnosticando columnas duplicadas...")
    duplicated_cols = data.columns[data.columns.duplicated()].tolist()
    if duplicated_cols:
        print(f"  ⚠ COLUMNAS DUPLICADAS DETECTADAS: {duplicated_cols}")
        print(f"  Total de columnas: {len(data.columns)}")
        print(f"  Columnas únicas: {data.columns.nunique()}")
        # Eliminar columnas duplicadas quedándonos con la primera ocurrencia
        data = data.loc[:, ~data.columns.duplicated()]
        print(f"  ✓ Duplicados eliminados. Columnas restantes: {len(data.columns)}")
    else:
        print(f"  ✓ No hay columnas duplicadas ({len(data.columns)} columnas)")
    
    # 4.5.3 Crear columnas de fecha adicionales
    print("\n4.5.3 Creando columnas de fecha adicionales...")
    if 'photo_datetime' in data.columns:
        data['photo_date'] = pd.to_datetime(data['photo_datetime']).dt.date
        if 'hour' not in data.columns:
            data['hour'] = pd.to_datetime(data['photo_datetime']).dt.hour
        print(f"  ✓ Columnas de fecha creadas")
    
    # 4.5.4 Asegurar que subproject_name existe
    if 'subproject_name' not in data.columns:
        print("\n4.5.4 Agregando columna subproject_name...")
        # Intentar obtenerla de deployments si no existe
        if 'subproject_name' in deployments.columns:
            # Ya debería estar del merge, pero por si acaso
            print("  ⚠ subproject_name faltante, revisar merge anterior")
        data['subproject_name'] = ''
        print(f"  ⚠ Columna subproject_name creada vacía")
    
    # 4.5.5 Verificar columnas esenciales
    print("\n4.5.5 Verificando columnas esenciales...")
    columnas_esenciales = [
        'project_id', 'project_name', 'Corporacion', 'deployment_name',
        'placename', 'latitude', 'longitude', 'sp_binomial', 'genus',
        'species', 'class', 'photo_datetime'
    ]
    
    columnas_presentes = [col for col in columnas_esenciales if col in data.columns]
    columnas_faltantes = [col for col in columnas_esenciales if col not in data.columns]
    
    print(f"  ✓ Columnas presentes: {len(columnas_presentes)}/{len(columnas_esenciales)}")
    if columnas_faltantes:
        print(f"  ⚠ Columnas faltantes: {columnas_faltantes}")
    
    # ===========================================================================
    # FASE 5: GENERACIÓN DE ARCHIVOS PARQUET
    # ===========================================================================
    print("\n" + "="*80)
    print("FASE 5: GENERACIÓN DE ARCHIVOS PARQUET")
    print("="*80)
    
    # 5.1 Generar las 3 tablas esenciales
    print("\n5.1 Generando archivos Parquet...")
    resultado = generar_todas_las_tablas(
        observations_df=data,
        deployments_df=deployments,
        projects_df=projects,
        output_dir=BASE_OUTPUT_PATH
    )
    
    if not resultado:
        print("  ✗ Error al generar archivos Parquet")
        return False
    
    # ===========================================================================
    # FASE 6: VALIDACIÓN DE CALIDAD
    # ===========================================================================
    print("\n" + "="*80)
    print("FASE 6: VALIDACIÓN DE CALIDAD")
    print("="*80)
    
    # 6.1 Validar observations.parquet
    print("\n6.1 Validando observations.parquet...")
    obs_path = os.path.join(BASE_OUTPUT_PATH, 'observations.parquet')
    validar_observations_parquet(obs_path)
    
    # 6.2 Validar deployments.parquet
    print("\n6.2 Validando deployments.parquet...")
    deps_path = os.path.join(BASE_OUTPUT_PATH, 'deployments.parquet')
    validar_deployments_parquet(deps_path)
    
    # 6.3 Validar projects.parquet
    print("\n6.3 Validando projects.parquet...")
    projs_path = os.path.join(BASE_OUTPUT_PATH, 'projects.parquet')
    validar_projects_parquet(projs_path)
    
    # 6.4 Resumen de validación
    print("\n6.4 Resumen de validación completado")
    print("  ✓ Validaciones ejecutadas para las 3 tablas Parquet")
    print("  ⚠ Revise los detalles arriba para identificar columnas faltantes")
    
    # ===========================================================================
    # RESUMEN FINAL
    # ===========================================================================
    print("\n" + "="*80)
    print("PROCESAMIENTO COMPLETADO EXITOSAMENTE")
    print("="*80)
    
    print(f"\n📊 RESUMEN:")
    print(f"  • Total observaciones: {len(data):,}")
    print(f"  • Especies únicas: {data['sp_binomial'].nunique()}")
    print(f"  • Proyectos: {data['project_id'].nunique()}")
    print(f"  • Eventos (subproject_name): {data['subproject_name'].nunique()}")
    print(f"  • Despliegues: {data['deployment_name'].nunique()}")
    
    print(f"\n📁 ARCHIVOS GENERADOS:")
    print(f"  • observations.parquet: Datos granulares de observaciones")
    print(f"  • deployments.parquet: Metadata de despliegues")
    print(f"  • projects.parquet: Catálogo de proyectos")
    
    print(f"\n✨ Pipeline ejecutado correctamente con arquitectura modular")
    
    return True


# ===============================================================================
# SCRIPT PRINCIPAL
# ===============================================================================

if __name__ == "__main__":
    main()
