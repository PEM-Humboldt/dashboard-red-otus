"""
Script de análisis de archivos Parquet generados por el pipeline.

Propósito:
    - Inspeccionar la estructura de los archivos Parquet
    - Simular las agrupaciones que usará el dashboard de R
    - Validar la disponibilidad de datos para cada combinación de filtros

Author: Proyecto OTUS - Instituto Humboldt
Date: Enero 2025
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
import warnings
import random

# Configurar encoding UTF-8 para Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Suprimir FutureWarnings de pandas
warnings.filterwarnings('ignore', category=FutureWarning)

# ===============================================================================
# CONFIGURACIÓN
# ===============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
PARQUET_DIR = os.path.join(PROJECT_ROOT, '4_Dashboard', 'dashboard_input_data')

# ===============================================================================
# FUNCIONES DE ANÁLISIS
# ===============================================================================

def analizar_estructura_archivo(parquet_path):
    """
    Analiza la estructura básica de un archivo Parquet.
    
    Args:
        parquet_path (str): Ruta al archivo Parquet
        
    Returns:
        dict: Diccionario con información del archivo
    """
    if not os.path.exists(parquet_path):
        print(f"  ✗ Archivo no encontrado: {parquet_path}")
        return None
    
    # Cargar archivo
    df = pd.read_parquet(parquet_path)
    
    # Información básica
    info = {
        'nombre_archivo': os.path.basename(parquet_path),
        'ruta_completa': parquet_path,
        'num_filas': len(df),
        'num_columnas': len(df.columns),
        'columnas': list(df.columns),
        'tipos_datos': df.dtypes.to_dict(),
        'tamaño_mb': os.path.getsize(parquet_path) / (1024 * 1024),
        'dataframe': df
    }
    
    return info


def mostrar_resumen_archivo(info):
    """
    Muestra un resumen detallado de un archivo Parquet.
    
    Args:
        info (dict): Información del archivo
    """
    if info is None:
        return
    
    print(f"\n{'='*80}")
    print(f"ARCHIVO: {info['nombre_archivo']}")
    print(f"{'='*80}")
    
    print(f"\n📊 INFORMACIÓN BÁSICA:")
    print(f"  • Nombre: {info['nombre_archivo']}")
    print(f"  • Filas: {info['num_filas']:,}")
    print(f"  • Columnas: {info['num_columnas']}")
    print(f"  • Tamaño: {info['tamaño_mb']:.2f} MB")
    
    print(f"\n📋 COLUMNAS DISPONIBLES:")
    print(f"\n{'  Nº':<5} {'Nombre':<35} {'Tipo':<20} {'Ejemplo':<40}")
    print(f"  {'-'*4} {'-'*34} {'-'*19} {'-'*39}")
    
    df = info['dataframe']
    
    for i, col in enumerate(info['columnas'], 1):
        tipo = str(info['tipos_datos'][col])
        
        # Obtener ejemplo (valor aleatorio no nulo)
        valores_validos = df[col].dropna()
        if len(valores_validos) > 0:
            ejemplo = valores_validos.iloc[random.randint(0, len(valores_validos) - 1)]
        else:
            ejemplo = 'NaN'
        
        # Formatear ejemplo según tipo
        if pd.api.types.is_numeric_dtype(df[col]):
            if pd.isna(ejemplo):
                ejemplo_str = 'NaN'
            elif isinstance(ejemplo, (int, np.integer)):
                ejemplo_str = f"{int(ejemplo):,}"
            else:
                ejemplo_str = str(ejemplo)
        else:
            ejemplo_str = str(ejemplo)
        
        # Truncar si es muy largo
        if len(ejemplo_str) > 37:
            ejemplo_str = ejemplo_str[:34] + "..."
        
        print(f"  {i:<4} {col:<35} {tipo:<20} {ejemplo_str:<40}")


def mostrar_lista_proyectos(observations_df):
    """
    Muestra resúmenes por corporación y por proyecto.
    
    Args:
        observations_df (pd.DataFrame): DataFrame de observaciones
    """
    # ============================================================================
    # RESUMEN POR CORPORACIÓN
    # ============================================================================
    print(f"\n{'='*80}")
    print("RESUMEN POR CORPORACIÓN")
    print(f"{'='*80}")
    
    # Agrupar por corporación y obtener estadísticas
    resumen_corp = observations_df.groupby('Corporacion', observed=True).agg({
        'project_id': lambda x: sorted(x.unique()),
        'subproject_name': lambda x: sorted(x.dropna().unique()),
        'Corporacion': 'count'
    }).rename(columns={
        'project_id': 'project_ids',
        'subproject_name': 'eventos',
        'Corporacion': 'n_observaciones'
    })
    
    # Calcular conteos
    resumen_corp['n_proyectos'] = resumen_corp['project_ids'].apply(len)
    resumen_corp['n_eventos'] = resumen_corp['eventos'].apply(len)
    
    # Ordenar por número de observaciones
    resumen_corp = resumen_corp.sort_values('n_observaciones', ascending=False)
    
    print(f"\n{'Corporación':<20} {'#Proy':<7} {'Project_IDs':<35} {'#Evts':<7} {'Eventos':<25} {'Observaciones':<15}")
    print(f"{'-'*19} {'-'*6} {'-'*34} {'-'*6} {'-'*24} {'-'*14}")
    
    for corporacion, row in resumen_corp.iterrows():
        # Formatear IDs de proyectos
        project_ids_str = ', '.join(map(str, row['project_ids']))
        if len(project_ids_str) > 32:
            project_ids_str = project_ids_str[:29] + "..."
        
        # Formatear eventos
        eventos_str = ', '.join(map(str, row['eventos']))
        if len(eventos_str) > 22:
            eventos_str = eventos_str[:19] + "..."
        
        print(f"{corporacion:<20} {row['n_proyectos']:<7} {project_ids_str:<35} {row['n_eventos']:<7} {eventos_str:<25} {row['n_observaciones']:<15,}")
    
    # ============================================================================
    # RESUMEN POR PROYECTO
    # ============================================================================
    print(f"\n{'='*80}")
    print("RESUMEN POR PROYECTO")
    print(f"{'='*80}")
    
    # Agrupar por proyecto y obtener estadísticas
    resumen_proy = observations_df.groupby('project_id', observed=True).agg({
        'Corporacion': 'first',
        'subproject_name': lambda x: sorted(x.dropna().unique()),
        'project_id': 'count'
    }).rename(columns={
        'Corporacion': 'corporacion',
        'subproject_name': 'eventos',
        'project_id': 'n_observaciones'
    })
    
    # Calcular conteo de eventos
    resumen_proy['n_eventos'] = resumen_proy['eventos'].apply(len)
    
    # Ordenar por corporación y luego por observaciones
    resumen_proy = resumen_proy.sort_values(['corporacion', 'n_observaciones'], ascending=[True, False])
    
    print(f"\n{'Project_ID':<12} {'Corporación':<20} {'#Evts':<7} {'Eventos':<30} {'Observaciones':<15}")
    print(f"{'-'*11} {'-'*19} {'-'*6} {'-'*29} {'-'*14}")
    
    for project_id, row in resumen_proy.iterrows():
        # Formatear eventos
        eventos_str = ', '.join(map(str, row['eventos']))
        if len(eventos_str) > 27:
            eventos_str = eventos_str[:24] + "..."
        
        print(f"{project_id:<12} {row['corporacion']:<20} {row['n_eventos']:<7} {eventos_str:<30} {row['n_observaciones']:<15,}")


def simular_agrupaciones_dashboard(observations_df):
    """
    Simula todas las posibles agrupaciones que usará el dashboard.
    
    Args:
        observations_df (pd.DataFrame): DataFrame de observaciones
    """
    print(f"\n{'='*80}")
    print("SIMULACIÓN DE AGRUPACIONES DEL DASHBOARD")
    print(f"{'='*80}")
    
    # Verificar columnas necesarias
    columnas_requeridas = ['project_id', 'subproject_name', 'Corporacion']
    columnas_faltantes = [col for col in columnas_requeridas if col not in observations_df.columns]
    
    if columnas_faltantes:
        print(f"\n⚠ ADVERTENCIA: Columnas faltantes para análisis: {columnas_faltantes}")
        return
    
    # Obtener valores únicos
    proyectos = observations_df['project_id'].dropna().unique()
    eventos = observations_df['subproject_name'].dropna().unique()
    corporaciones = observations_df['Corporacion'].dropna().unique()
    
    print(f"\n📊 VALORES ÚNICOS DISPONIBLES:")
    print(f"  • Proyectos: {len(proyectos)}")
    print(f"  • Eventos (subproject_name): {len(eventos)}")
    print(f"  • Corporaciones: {len(corporaciones)}")
    
    # ============================================================================
    # AGRUPACIÓN 1: PROYECTO - EVENTO
    # ============================================================================
    print(f"\n{'─'*80}")
    print("1️⃣  AGRUPACIÓN: PROYECTO × EVENTO")
    print(f"{'─'*80}")
    
    # 1.1 Uno a Uno (Proyecto específico × Evento específico)
    print(f"\n📌 1.1. UNO A UNO (Proyecto específico × Evento específico)")
    print(f"     Combinaciones posibles: {len(proyectos)} × {len(eventos)} = {len(proyectos) * len(eventos):,}")
    
    # Calcular matriz de datos disponibles
    matriz_proyecto_evento = observations_df.groupby(
        ['project_id', 'subproject_name'], observed=True
    ).size().reset_index(name='n_observaciones')
    
    print(f"     Combinaciones con datos: {len(matriz_proyecto_evento):,}")
    print(f"\n     Top 10 combinaciones con más observaciones:")
    
    top_10 = matriz_proyecto_evento.nlargest(10, 'n_observaciones')
    for idx, row in top_10.iterrows():
        print(f"       • Proyecto {row['project_id']} × Evento {row['subproject_name']}: {row['n_observaciones']:,} obs")
    
    # 1.2 Uno a Todos (Proyecto específico × Todos los eventos)
    print(f"\n📌 1.2. UNO A TODOS (Proyecto específico × Todos los eventos)")
    print(f"     Opciones disponibles: {len(proyectos)} proyectos")
    
    agrup_proyecto_todos_eventos = observations_df.groupby('project_id', observed=True).agg({
        'subproject_name': 'nunique',
        'project_id': 'count'
    }).rename(columns={'project_id': 'n_observaciones', 'subproject_name': 'n_eventos'})
    
    print(f"\n     Top 10 proyectos con más observaciones:")
    top_10_proyectos = agrup_proyecto_todos_eventos.nlargest(10, 'n_observaciones')
    for proyecto, row in top_10_proyectos.iterrows():
        print(f"       • Proyecto {proyecto}: {row['n_observaciones']:,} obs ({row['n_eventos']} eventos)")
    
    # 1.3 Todos a Uno (Todos los proyectos × Evento específico)
    print(f"\n📌 1.3. TODOS A UNO (Todos los proyectos × Evento específico)")
    print(f"     Opciones disponibles: {len(eventos)} eventos")
    
    agrup_todos_proyectos_evento = observations_df.groupby('subproject_name', observed=True).agg({
        'project_id': 'nunique',
        'subproject_name': 'count'
    }).rename(columns={'subproject_name': 'n_observaciones', 'project_id': 'n_proyectos'})
    
    print(f"\n     Eventos ordenados por número de observaciones:")
    for evento, row in agrup_todos_proyectos_evento.sort_values('n_observaciones', ascending=False).iterrows():
        print(f"       • Evento '{evento}': {row['n_observaciones']:,} obs ({row['n_proyectos']} proyectos)")
    
    # 1.4 Todos a Todos
    print(f"\n📌 1.4. TODOS A TODOS (Todos los proyectos × Todos los eventos)")
    print(f"     Total de observaciones: {len(observations_df):,}")
    print(f"     Proyectos únicos: {observations_df['project_id'].nunique()}")
    print(f"     Eventos únicos: {observations_df['subproject_name'].nunique()}")
    
    # ============================================================================
    # AGRUPACIÓN 2: CORPORACIÓN - EVENTO
    # ============================================================================
    print(f"\n{'─'*80}")
    print("2️⃣  AGRUPACIÓN: CORPORACIÓN × EVENTO")
    print(f"{'─'*80}")
    
    # 2.1 Uno a Uno (Corporación específica × Evento específico)
    print(f"\n📌 2.1. UNO A UNO (Corporación específica × Evento específico)")
    print(f"     Combinaciones posibles: {len(corporaciones)} × {len(eventos)} = {len(corporaciones) * len(eventos):,}")
    
    matriz_corporacion_evento = observations_df.groupby(
        ['Corporacion', 'subproject_name'], observed=True
    ).size().reset_index(name='n_observaciones')
    
    print(f"     Combinaciones con datos: {len(matriz_corporacion_evento):,}")
    print(f"\n     Top 10 combinaciones con más observaciones:")
    
    top_10_corp_evento = matriz_corporacion_evento.nlargest(10, 'n_observaciones')
    for idx, row in top_10_corp_evento.iterrows():
        print(f"       • {row['Corporacion']} × Evento {row['subproject_name']}: {row['n_observaciones']:,} obs")
    
    # 2.2 Uno a Todos (Corporación específica × Todos los eventos)
    print(f"\n📌 2.2. UNO A TODOS (Corporación específica × Todos los eventos)")
    print(f"     Opciones disponibles: {len(corporaciones)} corporaciones")
    
    agrup_corporacion_todos_eventos = observations_df.groupby('Corporacion', observed=True).agg({
        'subproject_name': 'nunique',
        'Corporacion': 'count'
    }).rename(columns={'Corporacion': 'n_observaciones', 'subproject_name': 'n_eventos'})
    
    print(f"\n     Corporaciones ordenadas por número de observaciones:")
    top_corporaciones = agrup_corporacion_todos_eventos.nlargest(15, 'n_observaciones')
    for corporacion, row in top_corporaciones.iterrows():
        print(f"       • {corporacion}: {row['n_observaciones']:,} obs ({row['n_eventos']} eventos)")
    
    # 2.3 Todos a Uno (Todas las corporaciones × Evento específico)
    print(f"\n📌 2.3. TODOS A UNO (Todas las corporaciones × Evento específico)")
    print(f"     Opciones disponibles: {len(eventos)} eventos")
    
    agrup_todas_corporaciones_evento = observations_df.groupby('subproject_name', observed=True).agg({
        'Corporacion': 'nunique',
        'subproject_name': 'count'
    }).rename(columns={'subproject_name': 'n_observaciones', 'Corporacion': 'n_corporaciones'})
    
    print(f"\n     Eventos con distribución de corporaciones:")
    for evento, row in agrup_todas_corporaciones_evento.sort_values('n_observaciones', ascending=False).iterrows():
        print(f"       • Evento '{evento}': {row['n_observaciones']:,} obs ({row['n_corporaciones']} corporaciones)")
    
    # 2.4 Todos a Todos
    print(f"\n📌 2.4. TODOS A TODOS (Todas las corporaciones × Todos los eventos)")
    print(f"     Total de observaciones: {len(observations_df):,}")
    print(f"     Corporaciones únicas: {observations_df['Corporacion'].nunique()}")
    print(f"     Eventos únicos: {observations_df['subproject_name'].nunique()}")
    
    # ============================================================================
    # MATRIZ DE DISTRIBUCIÓN
    # ============================================================================
    print(f"\n{'─'*80}")
    print("📊 MATRIZ DE DISTRIBUCIÓN CORPORACIÓN × EVENTO")
    print(f"{'─'*80}")
    
    # Crear tabla pivote
    pivot_corp_evento = observations_df.pivot_table(
        index='Corporacion',
        columns='subproject_name',
        values='project_id',
        aggfunc='count',
        fill_value=0,
        observed=True
    )
    
    print(f"\nDimensiones: {pivot_corp_evento.shape[0]} corporaciones × {pivot_corp_evento.shape[1]} eventos")
    print(f"\nVista previa de la matriz (primeras 10 corporaciones × todos los eventos):")
    print(pivot_corp_evento.head(10).to_string())
    
    # Estadísticas de cobertura
    print(f"\n📈 ESTADÍSTICAS DE COBERTURA:")
    
    # Por corporación
    obs_por_corp = pivot_corp_evento.sum(axis=1).sort_values(ascending=False)
    print(f"\n  Observaciones por Corporación:")
    print(f"    • Máximo: {obs_por_corp.max():,} ({obs_por_corp.idxmax()})")
    print(f"    • Mínimo: {obs_por_corp.min():,} ({obs_por_corp.idxmin()})")
    print(f"    • Promedio: {obs_por_corp.mean():,.0f}")
    print(f"    • Mediana: {obs_por_corp.median():,.0f}")
    
    # Por evento
    obs_por_evento = pivot_corp_evento.sum(axis=0).sort_values(ascending=False)
    print(f"\n  Observaciones por Evento:")
    print(f"    • Máximo: {obs_por_evento.max():,} ({obs_por_evento.idxmax()})")
    print(f"    • Mínimo: {obs_por_evento.min():,} ({obs_por_evento.idxmin()})")
    print(f"    • Promedio: {obs_por_evento.mean():,.0f}")
    print(f"    • Mediana: {obs_por_evento.median():,.0f}")
    
    # Celdas vacías (sin datos)
    total_celdas = pivot_corp_evento.shape[0] * pivot_corp_evento.shape[1]
    celdas_vacias = (pivot_corp_evento == 0).sum().sum()
    pct_vacias = (celdas_vacias / total_celdas) * 100
    
    print(f"\n  Cobertura de la matriz:")
    print(f"    • Total de combinaciones posibles: {total_celdas:,}")
    print(f"    • Combinaciones sin datos: {celdas_vacias:,} ({pct_vacias:.1f}%)")
    print(f"    • Combinaciones con datos: {total_celdas - celdas_vacias:,} ({100-pct_vacias:.1f}%)")


def generar_reporte_completo():
    """
    Genera el reporte completo de análisis de los archivos Parquet.
    """
    print("="*80)
    print("ANÁLISIS DE ARCHIVOS PARQUET GENERADOS")
    print("Dashboard de Monitoreo - Red OTUS Colombia")
    print("="*80)
    
    # Lista de archivos a analizar
    archivos = [
        'observations.parquet',
        'deployments.parquet',
        'projects.parquet'
    ]
    
    # Diccionario para almacenar DataFrames
    dataframes = {}
    
    # ============================================================================
    # PARTE 1: ANÁLISIS DE ESTRUCTURA DE ARCHIVOS
    # ============================================================================
    print(f"\n{'█'*80}")
    print("PARTE 1: ESTRUCTURA DE ARCHIVOS")
    print(f"{'█'*80}")
    
    for archivo in archivos:
        ruta = os.path.join(PARQUET_DIR, archivo)
        info = analizar_estructura_archivo(ruta)
        
        if info is not None:
            mostrar_resumen_archivo(info)
            dataframes[archivo.replace('.parquet', '')] = info['dataframe']
    
    # ============================================================================
    # PARTE 2: RESUMEN POR CORPORACIÓN
    # ============================================================================
    print(f"\n{'█'*80}")
    print("PARTE 2: RESUMEN POR PROYECTO Y CORPORACIÓN")
    print(f"{'█'*80}")
    
    if 'observations' in dataframes:
        mostrar_lista_proyectos(dataframes['observations'])
    else:
        print("\n⚠ No se pudo cargar observations.parquet")
    
    # ============================================================================
    # PARTE 3: SIMULACIÓN DE AGRUPACIONES DEL DASHBOARD
    # ============================================================================
    print(f"\n{'█'*80}")
    print("PARTE 3: SIMULACIÓN DE AGRUPACIONES DEL DASHBOARD")
    print(f"{'█'*80}")
    
    if 'observations' in dataframes:
        simular_agrupaciones_dashboard(dataframes['observations'])
    else:
        print("\n⚠ No se pudo cargar observations.parquet para simulación")
    
    # ============================================================================
    # RESUMEN FINAL
    # ============================================================================
    print(f"\n{'='*80}")
    print("✅ ANÁLISIS COMPLETADO")
    print(f"{'='*80}")
    
    print(f"\n📁 Archivos analizados: {len(dataframes)}/{len(archivos)}")
    
    if 'observations' in dataframes:
        obs_df = dataframes['observations']
        print(f"\n📊 Resumen de observations.parquet:")
        print(f"  • Total registros: {len(obs_df):,}")
        print(f"  • Especies únicas: {obs_df['sp_binomial'].nunique() if 'sp_binomial' in obs_df.columns else 'N/A'}")
        print(f"  • Proyectos únicos: {obs_df['project_id'].nunique() if 'project_id' in obs_df.columns else 'N/A'}")
        print(f"  • Eventos únicos: {obs_df['subproject_name'].nunique() if 'subproject_name' in obs_df.columns else 'N/A'}")
        print(f"  • Corporaciones únicas: {obs_df['Corporacion'].nunique() if 'Corporacion' in obs_df.columns else 'N/A'}")
    
    print(f"\n🎯 El dashboard en R podrá gestionar todas estas agrupaciones de datos.")
    print(f"{'='*80}\n")


# ===============================================================================
# SCRIPT PRINCIPAL
# ===============================================================================

if __name__ == "__main__":
    generar_reporte_completo()
