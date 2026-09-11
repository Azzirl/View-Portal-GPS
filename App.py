import streamlit as st
import folium
from streamlit_folium import st_folium
import json
import pandas as pd

# Importar módulos propios
from utils.data_loader import procesar_zip_en_memoria, unificar_dataframes
from utils.geospatial import dataframe_a_geodataframe
from utils.network import construir_grafo, obtener_ruta_upstream

# 1. Configuración de página
st.set_page_config(page_title="Geoportal GPS", layout="wide", page_icon="🌍")

# Funciones cacheadas para optimizar rendimiento en Streamlit
@st.cache_data
def load_data(file):
    return procesar_zip_en_memoria(file)

@st.cache_data
def process_geospatial(df):
    return dataframe_a_geodataframe(df)

@st.cache_data
def process_network(df):
    return construir_grafo(df)

# 2. Sidebar - Controles de Usuario
with st.sidebar:
    st.title("🌍 Geoportal de Ingeniería GPS")
    st.markdown("---")
    
    archivo_zip = st.file_uploader("Importar Zonas.zip", type="zip")
    
    if archivo_zip:
        # Procesar datos
        datos_proyectos = load_data(archivo_zip)
        lista_proyectos = list(datos_proyectos.keys())
        
        st.success(f"¡{len(lista_proyectos)} Proyectos detectados!")
        
        # Filtros
        proyecto_actual = st.selectbox("Seleccionar Proyecto", lista_proyectos)
        
        capas = st.multiselect(
            "Capas Visibles",
            ["AIREADORES", "TABLEROS", "TRAFO", "PISCINAS", "POSTES", "TENSOR"],
            default=["AIREADORES", "TABLEROS", "TRAFO"]
        )
    else:
        st.info("Sube el archivo ZIP para comenzar.")

# 3. Flujo Principal (si hay datos)
if archivo_zip and proyecto_actual:
    
    # Preparar DataFrames y Grafo
    df_raw = unificar_dataframes(datos_proyectos, proyecto_actual)
    gdf = process_geospatial(df_raw)
    grafo = process_network(df_raw)
    
    # 4. Dashboard de Estadísticas
    st.subheader(f"📊 Dashboard del Proyecto: {proyecto_actual}")
    col1, col2, col3, col4 = st.columns(4)
    
    total_aireadores = len(df_raw[df_raw['TIPO_ELEMENTO'] == 'AIREADORES'])
    total_tableros = len(df_raw[df_raw['TIPO_ELEMENTO'] == 'TABLEROS'])
    total_trafos = len(df_raw[df_raw['TIPO_ELEMENTO'] == 'TRAFO'])
    
    # Calcular potencia total si existe la columna KVA o POTENCIA
    potencia_total = 0
    if 'KVA' in df_raw.columns:
        potencia_total = pd.to_numeric(df_raw['KVA'], errors='coerce').sum()
        
    col1.metric("Aireadores", str(total_aireadores))
    col2.metric("Tableros", str(total_tableros))
    col3.metric("Transformadores", str(total_trafos))
    col4.metric("Potencia Total (kVA)", f"{potencia_total:,.2f}")
    
    st.markdown("---")
    
    # 5. Configuración del Mapa Folium
    # Obtener centro del mapa basado en las geometrías
    centro_lat, centro_lon = -2.15, -79.9 # Coordenadas por defecto (Guayas, Ecuador)
    if not gdf.empty:
        centro_lon = gdf.geometry.x.mean()
        centro_lat = gdf.geometry.y.mean()
        
    m = folium.Map(location=[centro_lat, centro_lon], zoom_start=15, tiles="cartodbpositron")
    
    # Paleta de colores para las capas
    colores = {
        'AIREADORES': 'green',
        'TABLEROS': 'orange',
        'TRAFO': 'red',
        'PISCINAS': 'blue'
    }

    # Dibujar Elementos en el Mapa
    for capa in capas:
        gdf_capa = gdf[gdf['TIPO_ELEMENTO'] == capa]
        
        for _, row in gdf_capa.iterrows():
            geom = row['geometry']
            if geom:
                # Extraemos info para el popup interactivo
                handle = row.get('HANDLE', 'N/A')
                nombre = row.get('NOMBRE', handle)
                
                # Crear diccionario limpio de atributos (ignorando nulos para no saturar)
                attrs = {k: v for k, v in row.to_dict().items() if pd.notna(v) and k != 'geometry'}
                
                # Renderizar marcador
                folium.CircleMarker(
                    location=[geom.y, geom.x],
                    radius=6,
                    color=colores.get(capa, 'gray'),
                    fill=True,
                    fill_opacity=0.7,
                    tooltip=f"{capa}: {nombre}",
                    # Pasamos los atributos como JSON al popup para que Streamlit los lea al hacer clic
                    popup=folium.Popup(json.dumps(attrs), show=False)
                ).add_to(m)

    # Mostrar mapa en Streamlit y capturar interacción
    mapa_info = st_folium(m, height=500, use_container_width=True, returned_objects=["last_object_clicked_popup"])
    
    # 6. Panel Lateral / Inferior de Información al hacer clic
    if mapa_info and mapa_info.get("last_object_clicked_popup"):
        try:
            # Recuperar datos del popup que empaquetamos en JSON
            datos_elemento = json.loads(mapa_info["last_object_clicked_popup"])
            
            st.subheader("Detalles del Elemento Seleccionado")
            info_col, network_col = st.columns(2)
            
            with info_col:
                st.markdown(f"**Tipo:** {datos_elemento.get('TIPO_ELEMENTO', 'N/A')}")
                st.markdown(f"**Nombre/Código:** {datos_elemento.get('NOMBRE', 'N/A')}")
                
                # Mostrar tabla con el resto de atributos técnicos
                df_atributos = pd.DataFrame(list(datos_elemento.items()), columns=['Atributo', 'Valor'])
                st.dataframe(df_atributos, use_container_width=True, hide_index=True)
                
            with network_col:
                st.markdown("**Navegación de Red (Upstream)**")
                handle_actual = datos_elemento.get('HANDLE')
                if handle_actual:
                    ruta = obtener_ruta_upstream(grafo, handle_actual)
                    if ruta:
                        st.write("Conectado desde:")
                        for nodo in reversed(ruta):
                            st.info(f"⬇️ {nodo}")
                        st.success(f"📍 {datos_elemento.get('TIPO_ELEMENTO')}: {datos_elemento.get('NOMBRE', handle_actual)}")
                    else:
                        st.write("No se encontraron elementos superiores conectados (Posible inicio de red o huérfano).")
                else:
                    st.warning("Elemento sin identificador (HANDLE) para calcular red.")
        except Exception as e:
            st.error(f"Error procesando la selección: {e}")
