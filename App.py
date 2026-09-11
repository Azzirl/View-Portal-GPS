import json
import pandas as pd
import folium
from streamlit_folium import st_folium
import streamlit as st

# Importar módulos de la carpeta utils
from utils.data_loader import procesar_zip_en_memoria, unificar_dataframes
from utils.geospatial import dataframe_a_geodataframe
from utils.network import construir_grafo, obtener_ruta_upstream

# 1. Configuración de la página
st.set_page_config(
    page_title="Geoportal de Ingeniería GPS",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Funciones cacheadas para rendimiento extremo
@st.cache_data(show_spinner="Procesando archivo ZIP en memoria...")
def load_data(file_bytes):
    return procesar_zip_en_memoria(file_bytes)

@st.cache_data(show_spinner="Calculando geometrías espaciales...")
def process_geospatial(df):
    return dataframe_a_geodataframe(df)

@st.cache_data(show_spinner="Generando topología de red...")
def process_network(df):
    return construir_grafo(df)

# 3. Sidebar (Panel Izquierdo)
with st.sidebar:
    st.title("🌍 Geoportal GPS")
    st.markdown("---")
    
    archivo_zip = st.file_uploader("Cargar Proyectos (Zonas.zip)", type="zip")
    
    if archivo_zip:
        datos_proyectos = load_data(archivo_zip.getvalue())
        lista_proyectos = sorted(list(datos_proyectos.keys()))
        
        st.success(f"✓ {len(lista_proyectos)} Proyectos cargados")
        
        proyecto_actual = st.selectbox("Seleccionar Proyecto", lista_proyectos)
        
        st.markdown("### Capas del Geoportal")
        capas = st.multiselect(
            "Seleccionar Capas Visibles",
            ["AIREADORES", "TABLEROS", "TRAFO", "PISCINAS", "POSTES", "TENSOR", "CBL", "ESTRUCTURA"],
            default=["AIREADORES", "TABLEROS", "TRAFO"]
        )
    else:
        st.info("Sube el archivo `Zonas.zip` para activar la plataforma.")

# 4. Vista Principal
if archivo_zip and 'proyecto_actual' in locals() and proyecto_actual:
    
    # Extraer y preparar datos del proyecto seleccionado
    df_raw = unificar_dataframes(datos_proyectos, proyecto_actual)
    
    if df_raw.empty:
        st.warning(f"El proyecto **{proyecto_actual}** no contiene información técnica procesable.")
        st.stop()
        
    df_geo = process_geospatial(df_raw)
    grafo = process_network(df_raw)
    
    # --- Dashboard de Métricas y KPIs ---
    st.title(f"📍 Proyecto: {proyecto_actual}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_aireadores = len(df_raw[df_raw['TIPO_ELEMENTO'] == 'AIREADORES'])
    total_tableros = len(df_raw[df_raw['TIPO_ELEMENTO'] == 'TABLEROS'])
    total_trafos = len(df_raw[df_raw['TIPO_ELEMENTO'] == 'TRAFO'])
    
    # Sumatoria de Potencia / kVA
    potencia_total = 0.0
    if 'KVA' in df_raw.columns:
        potencia_total = pd.to_numeric(df_raw['KVA'], errors='coerce').fillna(0).sum()
    elif 'POTENCIA' in df_raw.columns:
        potencia_total = pd.to_numeric(df_raw['POTENCIA'], errors='coerce').fillna(0).sum()
        
    col1.metric("Aireadores", f"{total_aireadores:,}")
    col2.metric("Tableros", f"{total_tableros:,}")
    col3.metric("Transformadores", f"{total_trafos:,}")
    col4.metric("Potencia Total", f"{potencia_total:,.1f} kVA/kW")
    
    st.markdown("---")
    
    # --- Mapa Interactivo GIS ---
    # Determinar centro óptimo del mapa
    centro_lat, centro_lon = -2.15, -79.9
    if not df_geo.empty and 'LATITUD' in df_geo.columns and df_geo['LATITUD'].notna().any():
        centro_lon = float(df_geo['LONGITUD'].mean())
        centro_lat = float(df_geo['LATITUD'].mean())
        
    m = folium.Map(
        location=[centro_lat, centro_lon], 
        zoom_start=15, 
        tiles="cartodbpositron"
    )
    
    # Simbología vectorizada por tipo de elemento
    estilos_capa = {
        'AIREADORES': {'color': '#2ecc71', 'radius': 5},
        'TABLEROS': {'color': '#e67e22', 'radius': 6},
        'TRAFO': {'color': '#e74c3c', 'radius': 8},
        'PISCINAS': {'color': '#3498db', 'radius': 4},
        'POSTES': {'color': '#95a5a6', 'radius': 4},
        'TENSOR': {'color': '#9b59b6', 'radius': 3},
        'CBL': {'color': '#f1c40f', 'radius': 4},
        'ESTRUCTURA': {'color': '#34495e', 'radius': 4}
    }

    # Cargar elementos en el mapa
    for capa in capas:
        df_capa = df_geo[df_geo['TIPO_ELEMENTO'] == capa]
        
        for _, row in df_capa.iterrows():
            if pd.notna(row.get('LATITUD')) and pd.notna(row.get('LONGITUD')):
                handle = str(row.get('HANDLE', 'N/A'))
                nombre = str(row.get('NOMBRE', row.get('ID_HANDLE', handle)))
                
                # Diccionario limpio para transferir al panel de información
                attrs = {
                    'TIPO_ELEMENTO': str(row.get('TIPO_ELEMENTO', '')),
                    'HANDLE': handle,
                    'NOMBRE': nombre,
                    'POTENCIA': str(row.get('POTENCIA', 'N/A')),
                    'VOLTAJE': str(row.get('VOLTAJE', 'N/A')),
                    'FASE': str(row.get('FASE', 'N/A')),
                    'TABLERO': str(row.get('TABLERO', 'N/A')),
                    'KVA': str(row.get('KVA', 'N/A'))
                }
                
                config_estilo = estilos_capa.get(capa, {'color': '#7f8c8d', 'radius': 5})
                
                folium.CircleMarker(
                    location=[row['LATITUD'], row['LONGITUD']],
                    radius=config_estilo['radius'],
                    color=config_estilo['color'],
                    fill=True,
                    fill_color=config_estilo['color'],
                    fill_opacity=0.8,
                    tooltip=f"<b>{capa}</b>: {nombre}",
                    popup=folium.Popup(json.dumps(attrs), show=False)
                ).add_to(m)

    # Renderizado estricto del mapa (Evita recargas al mover o hacer zoom)
    mapa_interactivo = st_folium(
        m, 
        height=550, 
        use_container_width=True, 
        returned_objects=["last_object_clicked_popup"]
    )
    
    # --- Panel Lateral / Inferior de Detalles e Inspección de Red ---
    st.markdown("### 🔍 Inspección Técnica y Topología de Red")
    
    if mapa_interactivo and mapa_interactivo.get("last_object_clicked_popup"):
        try:
            datos_elemento = json.loads(mapa_interactivo["last_object_clicked_popup"])
            
            col_info, col_topologia = st.columns(2)
            
            with col_info:
                st.subheader(f"📌 {datos_elemento.get('TIPO_ELEMENTO')}: {datos_elemento.get('NOMBRE')}")
                
                # Generar tabla resumen de atributos
                df_atributos = pd.DataFrame(
                    list(datos_elemento.items()), 
                    columns=['Parámetro', 'Valor']
                )
                st.dataframe(df_atributos, use_container_width=True, hide_index=True)
                
            with col_topologia:
                st.subheader("🌐 Árbol de Conexiones (Upstream)")
                handle_actual = datos_elemento.get('HANDLE')
                
                if handle_actual and handle_actual in grafo:
                    ruta_red = obtener_ruta_upstream(grafo, handle_actual)
                    if ruta_red:
                        st.write("Jerarquía de Alimentación Detectada:")
                        for nodo in reversed(ruta_red):
                            st.info(f"⚡ {nodo}")
                        st.success(f"📍 {datos_elemento.get('TIPO_ELEMENTO')}: {datos_elemento.get('NOMBRE')}")
                    else:
                        st.warning("El elemento no reporta alimentadores o tableros superiores asociados.")
                else:
                    st.warning("El elemento seleccionado no posee relaciones topológicas activas.")
        except Exception as err:
            st.error(f"Error parseando los datos de la entidad: {err}")
    else:
        st.info("Haz clic sobre cualquier elemento (Punto) dentro del mapa para desplegar sus especificaciones de ingeniería y árbol de conexión.")
else:
    if not archivo_zip:
        st.warning("Esperando archivo de proyectos. Por favor sube `Zonas.zip` desde la barra lateral.")
