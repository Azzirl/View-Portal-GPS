import io
import zipfile
import pandas as pd

def procesar_zip_en_memoria(archivo_zip_input):
    """
    Lee la estructura de carpetas y archivos TXT dentro del ZIP subido desde Streamlit.
    """
    proyectos = {}

    # Convertir bytes a un flujo IO operable si es necesario
    if isinstance(archivo_zip_input, bytes):
        archivo_zip_input = io.BytesIO(archivo_zip_input)

    with zipfile.ZipFile(archivo_zip_input, 'r') as z:
        for filepath in z.namelist():
            if filepath.endswith('.txt') and not filepath.startswith('__MACOSX'):
                partes = filepath.split('/')
                if len(partes) >= 2:
                    proyecto_nombre = partes[0]
                    nombre_archivo = partes[-1].replace('.txt', '')

                    if proyecto_nombre not in proyectos:
                        proyectos[proyecto_nombre] = {}

                    with z.open(filepath) as f:
                        try:
                            contenido = f.read()
                            try:
                                texto = contenido.decode('utf-8')
                            except UnicodeDecodeError:
                                texto = contenido.decode('latin-1')

                            df = pd.read_csv(io.StringIO(texto), sep=None, engine='python')
                            df.columns = [str(c).strip().upper() for c in df.columns]
                            df['TIPO_ELEMENTO'] = nombre_archivo.upper()
                            df['PROYECTO'] = proyecto_nombre
                            proyectos[proyecto_nombre][nombre_archivo.upper()] = df
                        except Exception as e:
                            print(f"Error procesando {filepath}: {e}")

    return proyectos

def unificar_dataframes(proyectos_dict, proyecto_seleccionado):
    """
    Une las categorías de un proyecto específico en un solo DataFrame.
    """
    if proyecto_seleccionado not in proyectos_dict:
        return pd.DataFrame()

    dfs = list(proyectos_dict[proyecto_seleccionado].values())
    if not dfs:
        return pd.DataFrame()

    return pd.concat(dfs, ignore_index=True)
