import pandas as pd
from pyproj import Transformer
import re

def dataframe_a_geodataframe(df, crs_origen="EPSG:32717"):
    """
    Transformación vectorial rápida de coordenadas sin bucles pesados.
    """
    if df.empty or 'GEORREFERENCIA' not in df.columns:
        df['LATITUD'] = None
        df['LONGITUD'] = None
        return df

    # Limpieza rápida mediante expresiones regulares
    def extraer_xy(val):
        if pd.isna(val):
            return None, None
        nums = re.findall(r"[-+]?(?:\d*\.\d+|\d+)", str(val))
        if len(nums) >= 2:
            return float(nums[0]), float(nums[1])
        return None, None

    # Extraer X e Y
    coords = df['GEORREFERENCIA'].apply(extraer_xy)
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]

    # Filtrar válidos para transformar en lote
    df['X_TMP'] = xs
    df['Y_TMP'] = ys
    
    validos = df['X_TMP'].notna() & df['Y_TMP'].notna()
    
    if not validos.any():
        df['LATITUD'] = None
        df['LONGITUD'] = None
        return df

    # Transformación masiva (Vectorizada)
    transformer = Transformer.from_crs(crs_origen, "EPSG:4326", always_xy=True)
    lons, lats = transformer.transform(
        df.loc[validos, 'X_TMP'].values, 
        df.loc[validos, 'Y_TMP'].values
    )

    df['LONGITUD'] = None
    df['LATITUD'] = None
    
    df.loc[validos, 'LONGITUD'] = lons
    df.loc[validos, 'LATITUD'] = lats
    
    df.drop(columns=['X_TMP', 'Y_TMP'], inplace=True)
    
    return df.dropna(subset=['LATITUD', 'LONGITUD']).copy()
