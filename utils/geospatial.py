import pandas as pd
from pyproj import Transformer

def dataframe_a_geodataframe(df, crs_origen="EPSG:32717"):
    """
    Transformación de coordenadas vectorizada y ultrarrápida sin bucles Python.
    """
    if df.empty or 'GEORREFERENCIA' not in df.columns:
        df['LATITUD'] = None
        df['LONGITUD'] = None
        return df

    coords_str = df['GEORREFERENCIA'].astype(str)
    extracted = coords_str.str.extract(r"([-+]?\d*\.?\d+)\s*,\s*([-+]?\d*\.?\d+)")

    df['X_TMP'] = pd.to_numeric(extracted[0], errors='coerce')
    df['Y_TMP'] = pd.to_numeric(extracted[1], errors='coerce')

    mask_validos = df['X_TMP'].notna() & df['Y_TMP'].notna()

    df['LONGITUD'] = None
    df['LATITUD'] = None

    if mask_validos.any():
        transformer = Transformer.from_crs(crs_origen, "EPSG:4326", always_xy=True)
        x_vals = df.loc[mask_validos, 'X_TMP'].values
        y_vals = df.loc[mask_validos, 'Y_TMP'].values

        lons, lats = transformer.transform(x_vals, y_vals)
        df.loc[mask_validos, 'LONGITUD'] = lons
        df.loc[mask_validos, 'LATITUD'] = lats

    df.drop(columns=['X_TMP', 'Y_TMP'], inplace=True, errors='ignore')
    return df.dropna(subset=['LATITUD', 'LONGITUD']).copy()
