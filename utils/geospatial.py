import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from pyproj import Transformer
import re

def parsear_coordenadas(coord_str, transformer):
    """Convierte un string de coordenadas (X,Y) en un objeto Point (Long, Lat)"""
    if pd.isna(coord_str):
        return None
    try:
        # Extraer números usando expresiones regulares por si vienen con texto basura
        numeros = re.findall(r"[-+]?(?:\d*\.\d+|\d+)", str(coord_str))
        if len(numeros) >= 2:
            x, y = float(numeros[0]), float(numeros[1])
            # Transformar UTM a WGS84
            lon, lat = transformer.transform(x, y)
            return Point(lon, lat)
    except:
        return None
    return None

def dataframe_a_geodataframe(df, crs_origen="EPSG:32717"):
    """
    Convierte un DataFrame normal a GeoDataFrame.
    EPSG:32717 corresponde a UTM Zona 17S (común en Ecuador/Perú).
    """
    if df.empty or 'GEORREFERENCIA' not in df.columns:
        # Si no hay columna de coordenadas, devolver GeoDataFrame vacío
        return gpd.GeoDataFrame(df, geometry=[None]*len(df))
        
    # Inicializar el transformador de PyProj (UTM 17S a WGS84 EPSG:4326)
    transformer = Transformer.from_crs(crs_origen, "EPSG:4326", always_xy=True)
    
    # Aplicar transformación
    geometrias = df['GEORREFERENCIA'].apply(lambda c: parsear_coordenadas(c, transformer))
    
    # Crear GeoDataFrame
    gdf = gpd.GeoDataFrame(df, geometry=geometrias, crs="EPSG:4326")
    
    # Filtrar elementos sin coordenadas válidas para el mapa
    gdf_valido = gdf.dropna(subset=['geometry'])
    return gdf_valido
