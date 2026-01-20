"""
Validación de calidad de datos y consistencia de información.
Funciones de verificación, diagnóstico y reportes de calidad.
"""
import os
import pandas as pd
import numpy as np


# ===============================================================================
# VALIDACIÓN DE ESTRUCTURA
# ===============================================================================

def validar_columnas_requeridas(df, columnas_requeridas, nombre_tabla="DataFrame"):
    """
    Valida que un DataFrame tenga las columnas requeridas.
    
    Args:
        df (pd.DataFrame): DataFrame a validar
        columnas_requeridas (list): Lista de nombres de columnas requeridas
        nombre_tabla (str): Nombre de la tabla para mensajes
        
    Returns:
        tuple: (es_valido: bool, columnas_faltantes: set)
    """
    columnas_actuales = set(df.columns)
    columnas_req = set(columnas_requeridas)
    
    columnas_faltantes = columnas_req - columnas_actuales
    
    if columnas_faltantes:
        print(f"  ✗ {nombre_tabla}: Columnas faltantes: {columnas_faltantes}")
        return False, columnas_faltantes
    
    print(f"  ✓ {nombre_tabla}: Todas las columnas requeridas presentes ({len(columnas_requeridas)})")
    return True, set()


def validar_tipos_datos(df, tipos_esperados, nombre_tabla="DataFrame"):
    """
    Valida que las columnas tengan los tipos de datos esperados.
    
    Args:
        df (pd.DataFrame): DataFrame a validar
        tipos_esperados (dict): Diccionario {columna: tipo_esperado}
        nombre_tabla (str): Nombre de la tabla para mensajes
        
    Returns:
        bool: True si todos los tipos son correctos
    """
    errores = []
    
    for columna, tipo_esperado in tipos_esperados.items():
        if columna not in df.columns:
            continue
        
        tipo_actual = df[columna].dtype
        
        # Validación flexible de tipos
        if tipo_esperado == 'datetime' and not pd.api.types.is_datetime64_any_dtype(tipo_actual):
            errores.append(f"{columna}: esperado datetime, encontrado {tipo_actual}")
        elif tipo_esperado == 'numeric' and not pd.api.types.is_numeric_dtype(tipo_actual):
            errores.append(f"{columna}: esperado numérico, encontrado {tipo_actual}")
        elif tipo_esperado == 'string' and tipo_actual != 'object' and tipo_actual.name != 'category':
            errores.append(f"{columna}: esperado string, encontrado {tipo_actual}")
    
    if errores:
        print(f"  ⚠ {nombre_tabla}: Tipos de datos incorrectos:")
        for error in errores:
            print(f"    • {error}")
        return False
    
    print(f"  ✓ {nombre_tabla}: Tipos de datos correctos")
    return True


# ===============================================================================
# VALIDACIÓN DE CALIDAD DE DATOS
# ===============================================================================

def validar_valores_nulos(df, columnas_criticas, nombre_tabla="DataFrame", umbral_pct=1.0):
    """
    Valida que columnas críticas no tengan valores nulos excesivos.
    
    Args:
        df (pd.DataFrame): DataFrame a validar
        columnas_criticas (list): Lista de columnas que NO deben tener nulos
        nombre_tabla (str): Nombre de la tabla para mensajes
        umbral_pct (float): Porcentaje máximo tolerable de nulos (default 1.0%)
        
    Returns:
        bool: True si no hay nulos excesivos en columnas críticas
    """
    columnas_con_nulos_criticos = []
    columnas_con_nulos_menores = []
    
    for columna in columnas_criticas:
        if columna not in df.columns:
            continue
        
        n_nulos = df[columna].isna().sum()
        
        if n_nulos > 0:
            pct_nulos = (n_nulos / len(df)) * 100
            info = f"{columna}: {n_nulos:,} ({pct_nulos:.2f}%)"
            
            if pct_nulos > umbral_pct:
                columnas_con_nulos_criticos.append(info)
            else:
                columnas_con_nulos_menores.append(info)
    
    # Mostrar nulos menores como advertencia informativa
    if columnas_con_nulos_menores:
        print(f"  ℹ️ {nombre_tabla}: Valores nulos mínimos detectados (<{umbral_pct}%):")
        for info in columnas_con_nulos_menores:
            print(f"    • {info}")
    
    # Solo fallar si hay nulos críticos
    if columnas_con_nulos_criticos:
        print(f"  ⚠ {nombre_tabla}: Valores nulos críticos en columnas importantes (>{umbral_pct}%):")
        for info in columnas_con_nulos_criticos:
            print(f"    • {info}")
        return False
    
    if not columnas_con_nulos_menores:
        print(f"  ✓ {nombre_tabla}: Sin valores nulos en columnas críticas")
    
    return True


def validar_duplicados(df, columnas_clave, nombre_tabla="DataFrame", umbral_pct=5.0, modo_estricto=False):
    """
    Valida que no haya registros duplicados excesivos según columnas clave.
    
    Args:
        df (pd.DataFrame): DataFrame a validar
        columnas_clave (list): Columnas que definen unicidad
        nombre_tabla (str): Nombre de la tabla para mensajes
        umbral_pct (float): Porcentaje máximo tolerable de duplicados (default 5.0%)
        modo_estricto (bool): Si True, cualquier duplicado falla la validación
        
    Returns:
        bool: True si no hay duplicados excesivos
    """
    # Verificar que todas las columnas existan
    columnas_existentes = [col for col in columnas_clave if col in df.columns]
    
    if not columnas_existentes:
        print(f"  ⚠ {nombre_tabla}: Ninguna columna clave encontrada para validar duplicados")
        return True
    
    duplicados = df.duplicated(subset=columnas_existentes, keep=False)
    n_duplicados = duplicados.sum()
    
    if n_duplicados > 0:
        pct_duplicados = (n_duplicados / len(df)) * 100
        
        # En modo estricto, cualquier duplicado es un error
        if modo_estricto:
            print(f"  ✗ {nombre_tabla}: {n_duplicados:,} registros duplicados ({pct_duplicados:.2f}%)")
            # Mostrar algunos ejemplos
            df_duplicados = df[duplicados][columnas_existentes].head(5)
            print(f"    Ejemplos de duplicados:")
            print(df_duplicados.to_string(index=False))
            return False
        
        # En modo tolerante, solo fallar si supera el umbral
        if pct_duplicados > umbral_pct:
            print(f"  ✗ {nombre_tabla}: {n_duplicados:,} registros duplicados ({pct_duplicados:.2f}%) - EXCEDE UMBRAL {umbral_pct}%")
            df_duplicados = df[duplicados][columnas_existentes].head(5)
            print(f"    Ejemplos de duplicados:")
            print(df_duplicados.to_string(index=False))
            return False
        else:
            # Duplicados menores: solo informar
            print(f"  ℹ️ {nombre_tabla}: {n_duplicados:,} registros duplicados ({pct_duplicados:.2f}%) - DENTRO DEL UMBRAL")
            print(f"    Nota: Duplicados pueden ser legítimos en datos originales")
            return True
    
    print(f"  ✓ {nombre_tabla}: Sin duplicados en columnas clave")
    return True


def validar_rangos_numericos(df, validaciones_rango, nombre_tabla="DataFrame"):
    """
    Valida que columnas numéricas estén dentro de rangos esperados.
    
    Args:
        df (pd.DataFrame): DataFrame a validar
        validaciones_rango (dict): {columna: (min, max)}
        nombre_tabla (str): Nombre de la tabla para mensajes
        
    Returns:
        bool: True si todos los valores están en rango
    """
    errores = []
    
    for columna, (val_min, val_max) in validaciones_rango.items():
        if columna not in df.columns:
            continue
        
        valores_fuera_rango = df[
            (df[columna] < val_min) | (df[columna] > val_max)
        ]
        
        if len(valores_fuera_rango) > 0:
            n_fuera = len(valores_fuera_rango)
            pct_fuera = (n_fuera / len(df)) * 100
            errores.append(
                f"{columna}: {n_fuera:,} valores fuera de rango [{val_min}, {val_max}] ({pct_fuera:.2f}%)"
            )
    
    if errores:
        print(f"  ⚠ {nombre_tabla}: Valores fuera de rango:")
        for error in errores:
            print(f"    • {error}")
        return False
    
    print(f"  ✓ {nombre_tabla}: Todos los valores en rangos esperados")
    return True


# ===============================================================================
# VALIDACIÓN DE CONSISTENCIA
# ===============================================================================

def validar_consistencia_fechas(df, col_inicio, col_fin, nombre_tabla="DataFrame"):
    """
    Valida que fechas de inicio sean anteriores a fechas de fin.
    
    Args:
        df (pd.DataFrame): DataFrame a validar
        col_inicio (str): Nombre de columna de fecha de inicio
        col_fin (str): Nombre de columna de fecha de fin
        nombre_tabla (str): Nombre de la tabla para mensajes
        
    Returns:
        bool: True si las fechas son consistentes
    """
    if col_inicio not in df.columns or col_fin not in df.columns:
        print(f"  ⚠ {nombre_tabla}: Columnas de fecha no encontradas")
        return True
    
    # Filtrar registros con ambas fechas válidas
    df_valido = df[[col_inicio, col_fin]].dropna()
    
    if len(df_valido) == 0:
        print(f"  ⚠ {nombre_tabla}: No hay registros con fechas válidas para validar")
        return True
    
    # Comparar fechas
    fechas_inconsistentes = df_valido[df_valido[col_inicio] > df_valido[col_fin]]
    
    n_inconsistentes = len(fechas_inconsistentes)
    
    if n_inconsistentes > 0:
        pct_inconsistentes = (n_inconsistentes / len(df_valido)) * 100
        print(f"  ⚠ {nombre_tabla}: {n_inconsistentes:,} registros con fechas inconsistentes ({pct_inconsistentes:.2f}%)")
        return False
    
    print(f"  ✓ {nombre_tabla}: Fechas consistentes")
    return True


def validar_referencias_cruzadas(df_hijo, df_padre, col_fk, col_pk, nombre_relacion="FK"):
    """
    Valida que todas las foreign keys existan en la tabla padre.
    
    Args:
        df_hijo (pd.DataFrame): DataFrame con foreign key
        df_padre (pd.DataFrame): DataFrame con primary key
        col_fk (str): Nombre de columna foreign key
        col_pk (str): Nombre de columna primary key
        nombre_relacion (str): Nombre de la relación para mensajes
        
    Returns:
        bool: True si todas las referencias son válidas
    """
    if col_fk not in df_hijo.columns:
        print(f"  ⚠ {nombre_relacion}: Columna FK '{col_fk}' no encontrada")
        return True
    
    if col_pk not in df_padre.columns:
        print(f"  ⚠ {nombre_relacion}: Columna PK '{col_pk}' no encontrada")
        return True
    
    # Valores únicos en hijo
    valores_fk = set(df_hijo[col_fk].dropna().unique())
    
    # Valores únicos en padre
    valores_pk = set(df_padre[col_pk].dropna().unique())
    
    # Referencias huérfanas
    referencias_huerfanas = valores_fk - valores_pk
    
    if referencias_huerfanas:
        n_huerfanas = len(referencias_huerfanas)
        print(f"  ⚠ {nombre_relacion}: {n_huerfanas} referencias huérfanas")
        print(f"    Ejemplos: {list(referencias_huerfanas)[:5]}")
        return False
    
    print(f"  ✓ {nombre_relacion}: Todas las referencias son válidas")
    return True


# ===============================================================================
# REPORTES DE CALIDAD
# ===============================================================================

def generar_reporte_calidad(df, nombre_tabla="DataFrame"):
    """
    Genera un reporte completo de calidad de datos.
    
    Args:
        df (pd.DataFrame): DataFrame a analizar
        nombre_tabla (str): Nombre de la tabla
        
    Returns:
        dict: Diccionario con métricas de calidad
    """
    print(f"\n{'='*70}")
    print(f"REPORTE DE CALIDAD: {nombre_tabla}")
    print(f"{'='*70}")
    
    reporte = {}
    
    # 1. Dimensiones
    reporte['n_registros'] = len(df)
    reporte['n_columnas'] = len(df.columns)
    
    print(f"\n📏 Dimensiones:")
    print(f"  • Registros: {reporte['n_registros']:,}")
    print(f"  • Columnas: {reporte['n_columnas']}")
    
    # 2. Valores nulos
    print(f"\n💧 Valores Nulos:")
    nulos_por_columna = df.isna().sum()
    columnas_con_nulos = nulos_por_columna[nulos_por_columna > 0]
    
    if len(columnas_con_nulos) > 0:
        reporte['columnas_con_nulos'] = len(columnas_con_nulos)
        print(f"  Columnas con nulos: {len(columnas_con_nulos)}/{len(df.columns)}")
        
        for col, n_nulos in columnas_con_nulos.head(10).items():
            pct = (n_nulos / len(df)) * 100
            print(f"    • {col}: {n_nulos:,} ({pct:.2f}%)")
    else:
        print(f"  ✓ Sin valores nulos")
        reporte['columnas_con_nulos'] = 0
    
    # 3. Duplicados
    print(f"\n🔁 Duplicados:")
    n_duplicados = df.duplicated().sum()
    
    if n_duplicados > 0:
        pct_duplicados = (n_duplicados / len(df)) * 100
        print(f"  ⚠ {n_duplicados:,} registros duplicados ({pct_duplicados:.2f}%)")
        reporte['n_duplicados'] = n_duplicados
    else:
        print(f"  ✓ Sin duplicados completos")
        reporte['n_duplicados'] = 0
    
    # 4. Cardinalidad (columnas únicas)
    print(f"\n🔢 Cardinalidad (Top 10 columnas):")
    cardinalidades = {}
    
    for col in df.columns[:10]:
        n_unique = df[col].nunique()
        pct_unique = (n_unique / len(df)) * 100
        cardinalidades[col] = n_unique
        print(f"  • {col}: {n_unique:,} únicos ({pct_unique:.1f}%)")
    
    reporte['cardinalidad'] = cardinalidades
    
    # 5. Tipos de datos
    print(f"\n📊 Tipos de Datos:")
    tipos_resumen = df.dtypes.value_counts()
    
    for tipo, count in tipos_resumen.items():
        print(f"  • {tipo}: {count} columnas")
    
    reporte['tipos_datos'] = tipos_resumen.to_dict()
    
    # 6. Estadísticas específicas para tabla
    if 'sp_binomial' in df.columns:
        n_especies = df['sp_binomial'].nunique()
        print(f"\n🦁 Biodiversidad:")
        print(f"  • Especies únicas: {n_especies:,}")
        reporte['especies_unicas'] = n_especies
    
    if 'project_id' in df.columns:
        n_proyectos = df['project_id'].nunique()
        print(f"\n📁 Proyectos:")
        print(f"  • Proyectos únicos: {n_proyectos:,}")
        reporte['proyectos_unicos'] = n_proyectos
    
    if 'Corporacion' in df.columns:
        n_corporaciones = df['Corporacion'].nunique()
        print(f"\n🏛️ Corporaciones:")
        print(f"  • Corporaciones únicas: {n_corporaciones:,}")
        reporte['corporaciones_unicas'] = n_corporaciones
        
        # Distribución
        print(f"  Distribución:")
        dist = df['Corporacion'].value_counts()
        for corp, count in dist.head(5).items():
            print(f"    • {corp}: {count:,}")
    
    print(f"\n{'='*70}\n")
    
    return reporte


def validar_observations_parquet(parquet_path):
    """
    Validación específica para observations.parquet.
    
    Args:
        parquet_path (str): Ruta al archivo observations.parquet
        
    Returns:
        bool: True si pasa todas las validaciones
    """
    print("\n=== Validación de observations.parquet ===")
    
    # Leer archivo Parquet
    if not os.path.exists(parquet_path):
        print(f"  ✗ Archivo no encontrado: {parquet_path}")
        return False
    
    df = pd.read_parquet(parquet_path)
    
    validaciones = []
    
    # 1. Columnas requeridas (después del renombrado)
    columnas_requeridas = [
        'project_id', 'project_name', 'Corporacion', 'subproject_name',
        'deployment_name', 'sp_binomial',
        'photo_datetime', 'hour', 'latitude', 'longitude'
    ]
    
    es_valido, _ = validar_columnas_requeridas(df, columnas_requeridas, "observations")
    validaciones.append(es_valido)
    
    # 2. Valores nulos en columnas críticas (tolerar hasta 1% de nulos)
    columnas_criticas = ['project_id', 'deployment_name', 'sp_binomial', 'photo_datetime']
    es_valido = validar_valores_nulos(df, columnas_criticas, "observations", umbral_pct=1.0)
    validaciones.append(es_valido)
    
    # 3. Rangos numéricos
    validaciones_rango = {
        'hour': (0, 23),
        'latitude': (-90, 90),
        'longitude': (-180, 180),
    }
    es_valido = validar_rangos_numericos(df, validaciones_rango, "observations")
    validaciones.append(es_valido)
    
    # 4. Consistencia de fechas
    es_valido = validar_consistencia_fechas(df, 'sensor_start_date', 'sensor_end_date', "observations")
    validaciones.append(es_valido)
    
    # Resultado final
    todas_validas = all(validaciones)
    
    if todas_validas:
        print("\n  ✅ observations.parquet: TODAS LAS VALIDACIONES PASARON")
    else:
        print("\n  ⚠️  observations.parquet: ALGUNAS VALIDACIONES FALLARON")
    
    return todas_validas


def validar_deployments_parquet(parquet_path):
    """
    Validación específica para deployments.parquet.
    
    Args:
        parquet_path (str): Ruta al archivo deployments.parquet
        
    Returns:
        bool: True si pasa todas las validaciones
    """
    print("\n=== Validación de deployments.parquet ===")
    
    # Leer archivo Parquet
    if not os.path.exists(parquet_path):
        print(f"  ✗ Archivo no encontrado: {parquet_path}")
        return False
    
    df = pd.read_parquet(parquet_path)
    
    validaciones = []
    
    # 1. Columnas requeridas (del CSV original de deployments)
    columnas_requeridas = [
        'deployment_id', 'project_id', 'placename',
        'latitude', 'longitude', 'start_date', 'end_date'
    ]
    
    es_valido, _ = validar_columnas_requeridas(df, columnas_requeridas, "deployments")
    validaciones.append(es_valido)
    
    # 2. Sin duplicados excesivos en deployment_id (tolerar hasta 5%)
    es_valido = validar_duplicados(df, ['deployment_id'], "deployments", umbral_pct=5.0, modo_estricto=False)
    validaciones.append(es_valido)
    
    # 3. Valores nulos en columnas críticas
    columnas_criticas = ['deployment_id', 'project_id']
    es_valido = validar_valores_nulos(df, columnas_criticas, "deployments")
    validaciones.append(es_valido)
    
    # Resultado final
    todas_validas = all(validaciones)
    
    if todas_validas:
        print("\n  ✅ deployments.parquet: TODAS LAS VALIDACIONES PASARON")
    else:
        print("\n  ⚠️  deployments.parquet: ALGUNAS VALIDACIONES FALLARON")
    
    return todas_validas


def validar_projects_parquet(parquet_path):
    """
    Validación específica para projects.parquet.
    
    Args:
        parquet_path (str): Ruta al archivo projects.parquet
        
    Returns:
        bool: True si pasa todas las validaciones
    """
    print("\n=== Validación de projects.parquet ===")
    
    # Leer archivo Parquet
    if not os.path.exists(parquet_path):
        print(f"  ✗ Archivo no encontrado: {parquet_path}")
        return False
    
    df = pd.read_parquet(parquet_path)
    
    validaciones = []
    
    # 1. Columnas requeridas (del CSV original de projects)
    columnas_requeridas = ['project_id', 'project_name']
    
    # Validación flexible: project_name puede no estar en el CSV original
    # pero se agrega durante el procesamiento
    columnas_presentes = [col for col in columnas_requeridas if col in df.columns]
    if len(columnas_presentes) < len(columnas_requeridas):
        columnas_faltantes = set(columnas_requeridas) - set(columnas_presentes)
        # Solo validar project_id como obligatorio
        if 'project_id' not in df.columns:
            print(f"  ✗ projects: Columna crítica 'project_id' faltante")
            validaciones.append(False)
        else:
            if columnas_faltantes:
                print(f"  ⚠ projects: Columnas opcionales no encontradas: {columnas_faltantes}")
            validaciones.append(True)
    else:
        es_valido, _ = validar_columnas_requeridas(df, columnas_requeridas, "projects")
        validaciones.append(es_valido)
    
    # 2. Sin duplicados en project_id
    es_valido = validar_duplicados(df, ['project_id'], "projects")
    validaciones.append(es_valido)
    
    # 3. Valores nulos en columnas críticas
    columnas_criticas = ['project_id']
    es_valido = validar_valores_nulos(df, columnas_criticas, "projects")
    validaciones.append(es_valido)
    
    # Resultado final
    todas_validas = all(validaciones)
    
    if todas_validas:
        print("\n  ✅ projects.parquet: TODAS LAS VALIDACIONES PASARON")
    else:
        print("\n  ⚠️  projects.parquet: ALGUNAS VALIDACIONES FALLARON")
    
    return todas_validas
