import zipfile
import pandas as pd
import io

def procesar_zip_en_memoria(archivo_zip):
    """
    Lee el archivo Zonas.zip subido en Streamlit y extrae la información 
    de los archivos TXT en DataFrames de Pandas.
    """
    proyectos = {}
    
    with zipfile.ZipFile(archivo_zip, 'r') as z:
        for filepath in z.namelist():
            # Filtrar solo archivos .txt y omitir carpetas vacías o archivos ocultos
            if filepath.endswith('.txt') and not filepath.startswith('__MACOSX'):
                # filepath ej: "KANSAS/AIREADORES.txt"
                partes = filepath.split('/')
                if len(partes) >= 2:
                    proyecto_nombre = partes[0]
                    nombre_archivo = partes[-1].replace('.txt', '')
                    
                    if proyecto_nombre not in proyectos:
                        proyectos[proyecto_nombre] = {}
                        
                    # Leer el contenido del TXT
                    with z.open(filepath) as f:
                        try:
                            # Intentamos leer asumiendo separadores por tabulador o coma
                            df = pd.read_csv(io.TextIOWrapper(f, 'utf-8'), sep=None, engine='python')
                            # Limpiar nombres de columnas
                            df.columns = [str(c).strip().upper() for c in df.columns]
                            df['TIPO_ELEMENTO'] = nombre_archivo.upper()
                            df['PROYECTO'] = proyecto_nombre
                            proyectos[proyecto_nombre][nombre_archivo.upper()] = df
                        except Exception as e:
                            print(f"Error leyendo {filepath}: {e}")
                            
    return proyectos

def unificar_dataframes(proyectos_dict, proyecto_seleccionado):
    """
    Une todos los DataFrames de un proyecto en uno solo para facilitar el análisis.
    """
    if proyecto_seleccionado not in proyectos_dict:
        return pd.DataFrame()
    
    dfs = list(proyectos_dict[proyecto_seleccionado].values())
    if not dfs:
        return pd.DataFrame()
        
    df_unificado = pd.concat(dfs, ignore_index=True)
    return df_unificado
