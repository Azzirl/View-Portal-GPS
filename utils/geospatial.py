import pandas as pd
from shapely.geometry import Point
from pyproj import Transformer
import re

def parsear_coordenadas(coord_str, transformer):
    """Convierte un string de coordenadas (X,Y) en un objeto Point (Long, Lat)"""
    if pd.isna(coord_str):
        return None
    try:
        # Extraer números flotantes o enteros del texto
        numeros = re.findall(r"[-+]?(?:\d*\.\d+|\d+)", str(coord_str))
        if len(numeros) >= 2:
            x, y = float(numeros[0]), float(numeros[1])
            # Transformación de coordenadas UTM 17S (EPSG:32717) a WGS84 (EPSG:4326)
            lon, lat = transformer.transform(x, y)
            return Point(lon, lat)
    except Exception:
        return None
    return None

def dataframe_a_geodataframe(df, crs_origen="EPSG:32717"):
    """
    Agrega columnas LATITUD y LONGITUD al DataFrame de Pandas usando Shapely y PyProj,
    omitiendo el uso de la librería GeoPandas.
    """
    if df.empty or 'GEORREFERENCIA' not in df.columns:
        df['geometry'] = None
        df['LATITUD'] = None
        df['LONGITUD'] = None
        return df

    # Transformador geoespacial
    transformer = Transformer.from_crs(crs_origen, "EPSG:4326", always_xy=True)

    # Crear geometrías
    geometrias = df['GEORREFERENCIA'].apply(lambda c: parsear_coordenadas(c, transformer))

    df['geometry'] = geometrias
    df['LONGITUD'] = geometrias.apply(lambda p: p.x if p else None)
    df['LATITUD'] = geometrias.apply(lambda p: p.y if p else None)

    # Filtrar solo registros con coordenadas válidas
    df_valido = df.dropna(subset=['LATITUD', 'LONGITUD']).copy()
    return df_valido
