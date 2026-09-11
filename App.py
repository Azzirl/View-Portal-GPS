import json
import pandas as pd
import folium
from folium import plugins
from streamlit_folium import st_folium
import streamlit as st

# Módulos internos
from utils.data_loader import procesar_zip_en_memoria, unificar_dataframes
from utils.geospatial import dataframe_a_geodataframe
from utils.network import construir_grafo, obtener_ruta_upstream, extraer_tramos_red

# 1. Configuración de página
st.set_page_config(
    page_title="Geoportal de Ingeniería GPS",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo personalizado estilo WebGIS Profesional
st.markdown("""
    <style>
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    .stMetric { background-color: #f8f9fa; border: 1px solid #e9ecef; padding: 10px; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

# 2. Funciones cacheadas
@st.cache_data(show_spinner="Cargando archivo ZIP en memoria...")
def load_data(file_bytes):
    return procesar_zip_en_memoria(file_bytes)

@st.cache_data(show_spinner="Vectorizando coordenadas espaciales...")
def process_geospatial(df):
    return dataframe_a_geodataframe(df)

@st.cache_data(show_spinner="Construyendo la red topológica...")
def process_network(df):
    return construir_grafo(df)

# 3. Sidebar
with st.sidebar:
    st.title("⚡ Geoportal GPS")
    st.caption("Sistema de Información Geográfica de Ingeniería")
    st.markdown("---")
    
    archivo_zip = st.file_uploader("Cargar Proyectos (Zonas.zip)", type="zip")
    
    if archivo_zip:
        datos_proyectos = load_data(archivo_zip.getvalue())
        lista_proyectos = sorted(list(datos_proyectos.keys()))
        
        st.success(f"✓ {len(lista_proyectos)} Proyectos detectados")
        proyecto_actual = st.selectbox("Proyecto Activo", lista_proyectos)
        
        st.markdown("### Configuración del Mapa")
        mostrar_red_lineas = st.checkbox("Trazar Redes de Alimentación (Líneas)", value=True)
        mostrar_etiquetas = st.checkbox("Mostrar Etiquetas de Texto", value=True)
        
        capas_disponibles = ["AIREADORES", "TABLEROS", "TRAFO", "PISCINAS", "POSTES", "TENSOR", "CBL", "ESTRUCTURA"]
        capas_seleccionadas = st.multiselect("Capas Visibles", capas_disponibles, default=["AIREADORES", "TABLEROS", "TRAFO", "POSTES"])
    else:
        st.info("Sube `Zonas.zip` para activar la plataforma.")

# 4. Área Principal
if archivo_zip and 'proyecto_actual' in locals() and proyecto_actual:
    
    df_raw = unificar_dataframes(datos_proyectos, proyecto_actual)
    
    if df_raw.empty:
        st.warning(f"El proyecto **{proyecto_actual}** no contiene información técnica procesable.")
        st.stop()
        
    df_geo = process_geospatial(df_raw)
    grafo = process_network(df_raw)
    
    # Header & KPIs
    st.markdown(f"## 🌐 Geoportal — Proyecto: **{proyecto_actual}**")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    total_aireadores = len(df_raw[df_raw['TIPO_ELEMENTO'] == 'AIREADORES'])
    total_tableros = len(df_raw[df_raw['TIPO_ELEMENTO'] == 'TABLEROS'])
    total_trafos = len(df_raw[df_raw['TIPO_ELEMENTO'] == 'TRAFO'])
    total_postes = len(df_raw[df_raw['TIPO_ELEMENTO'] == 'POSTES'])
    
    potencia_total = 0.0
    if 'KVA' in df_raw.columns:
        potencia_total = pd.to_numeric(df_raw['KVA'], errors='coerce').fillna(0).sum()
    elif 'POTENCIA' in df_raw.columns:
        potencia_total = pd.to_numeric(df_raw['POTENCIA'], errors='coerce').fillna(0).sum()
        
    col1.metric("Transformadores", f"{total_trafos:,}")
    col2.metric("Tableros", f"{total_tableros:,}")
    col3.metric("Aireadores", f"{total_aireadores:,}")
    col4.metric("Postes", f"{total_postes:,}")
    col5.metric("Potencia Total", f"{potencia_total:,.1f} kVA")
    
    st.markdown("---")
    
    # Centro del mapa
    centro_lat, centro_lon = -2.15, -79.9
    if not df_geo.empty and 'LATITUD' in df_geo.columns and df_geo['LATITUD'].notna().any():
        centro_lon = float(df_geo['LONGITUD'].mean())
        centro_lat = float(df_geo['LATITUD'].mean())
        
    m = folium.Map(
        location=[centro_lat, centro_lon], 
        zoom_start=16, 
        tiles="cartodbpositron",
        control_scale=True
    )

    # 5. Trazar Redes de Alimentación (Líneas Eléctricas)
    if mostrar_red_lineas and not df_geo.empty:
        grupo_red = folium.FeatureGroup(name="Red Eléctrica / Conexiones", show=True)
        tramos = extraer_tramos_red(grafo)
        
        for tramo in tramos:
            color_linea = "#27ae60" if tramo['origen_tipo'] == 'TRAFO' else "#8e44ad"
            folium.PolyLine(
                locations=[tramo['origen_coords'], tramo['destino_coords']],
                weight=2,
                color=color_linea,
                opacity=0.7,
                dash_array='4, 4' if color_linea == "#8e44ad" else None,
                tooltip=f"Línea: {tramo['origen_tipo']} ➔ {tramo['destino_tipo']}"
            ).add_to(grupo_red)
        grupo_red.add_to(m)

    # 6. Iconografía Técnica CAD / GIS
    simbolos = {
        'TRAFO': {'icono': '▲', 'bg': '#e74c3c', 'color': '#ffffff', 'size': 22},
        'TABLEROS': {'icono': '█', 'bg': '#e67e22', 'color': '#ffffff', 'size': 18},
        'AIREADORES': {'icono': '⚙', 'bg': '#2ecc71', 'color': '#ffffff', 'size': 18},
        'POSTES': {'icono': '●', 'bg': '#34495e', 'color': '#ffffff', 'size': 14},
        'PISCINAS': {'icono': '▧', 'bg': '#3498db', 'color': '#ffffff', 'size': 16},
        'TENSOR': {'icono': '♦', 'bg': '#9b59b6', 'color': '#ffffff', 'size': 14}
    }

    MAX_MARCADORES = 800

    for capa in capas_seleccionadas:
        grupo_capa = folium.FeatureGroup(name=capa, show=True)
        df_capa = df_geo[df_geo['TIPO_ELEMENTO'] == capa].head(MAX_MARCADORES)
        style = simbolos.get(capa, {'icono': '●', 'bg': '#7f8c8d', 'color': '#ffffff', 'size': 14})
        
        for _, row in df_capa.iterrows():
            if pd.notna(row.get('LATITUD')) and pd.notna(row.get('LONGITUD')):
                handle = str(row.get('HANDLE', 'N/A'))
                nombre = str(row.get('NOMBRE', row.get('ID_HANDLE', handle)))
                kva = str(row.get('KVA', row.get('POTENCIA', '')))
                
                texto_label = f"{nombre}"
                if kva and kva != 'nan' and kva != 'N/A':
                    texto_label += f" ({kva}kVA)"
                    
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

                # Marcador CAD con etiqueta visual (CORREGIDO: html=html_icon)
                html_icon = f"""
                <div style="font-size: {style['size']}px; color: {style['bg']}; text-shadow: 1px 1px 2px black; text-align: center; line-height: 1;">
                    {style['icono']}
                    {f'<span style="font-size: 10px; font-weight: bold; color: #111; background: rgba(255,255,255,0.85); padding: 1px 3px; border-radius: 3px; white-space: nowrap; display: block;">{texto_label}</span>' if mostrar_etiquetas else ''}
                </div>
                """

                folium.Marker(
                    location=[row['LATITUD'], row['LONGITUD']],
                    icon=folium.DivIcon(html=html_icon, icon_size=(100, 30), icon_anchor=(15, 15)),
                    tooltip=f"<b>{capa}</b>: {nombre}",
                    popup=folium.Popup(json.dumps(attrs), show=False)
                ).add_to(grupo_capa)
                
        grupo_capa.add_to(m)

    folium.LayerControl(position='topright').add_to(m)

    # Renderizar mapa
    mapa_interactivo = st_folium(
        m, 
        height=520, 
        use_container_width=True, 
        returned_objects=["last_object_clicked_popup"]
    )
    
    # 7. Inspección del Elemento Seleccionado
    if mapa_interactivo and mapa_interactivo.get("last_object_clicked_popup"):
        try:
            datos_elemento = json.loads(mapa_interactivo["last_object_clicked_popup"])
            st.markdown(f"### 🔍 Inspección Técnica: **{datos_elemento.get('TIPO_ELEMENTO')} {datos_elemento.get('NOMBRE')}**")
            
            col_info, col_topologia = st.columns(2)
            
            with col_info:
                df_atributos = pd.DataFrame(list(datos_elemento.items()), columns=['Parámetro', 'Valor'])
                st.dataframe(df_atributos, use_container_width=True, hide_index=True)
                
            with col_topologia:
                st.markdown("**Árbol de Conexiones Topológicas (Upstream)**")
                handle_actual = datos_elemento.get('HANDLE')
                if handle_actual and handle_actual in grafo:
                    ruta_red = obtener_ruta_upstream(grafo, handle_actual)
                    if ruta_red:
                        for nodo in reversed(ruta_red):
                            st.info(f"⚡ {nodo}")
                        st.success(f"📍 {datos_elemento.get('TIPO_ELEMENTO')}: {datos_elemento.get('NOMBRE')}")
                    else:
                        st.warning("El elemento no reporta tableros o alimentadores superiores asociados.")
                else:
                    st.warning("Elemento aislado o sin relaciones topológicas en la red.")
        except Exception as err:
            st.error(f"Error procesando la entidad: {err}")

    # 8. TABLA DE ATRIBUTOS INFERIOR (Estilo ArcGIS / Geoportal CNEL)
    st.markdown("---")
    st.markdown("### 📋 Tabla de Atributos del Proyecto")
    
    capas_existentes = sorted(df_geo['TIPO_ELEMENTO'].unique().tolist())
    tab_list = st.tabs([f"📄 {c}" for c in capas_existentes])
    
    for i, capa_nombre in enumerate(capas_existentes):
        with tab_list[i]:
            df_tabla = df_geo[df_geo['TIPO_ELEMENTO'] == capa_nombre].copy()
            cols_visibles = [c for c in df_tabla.columns if c not in ['PROYECTO', 'geometry'] and df_tabla[c].notna().any()]
            st.dataframe(df_tabla[cols_visibles], use_container_width=True, hide_index=True)
else:
    if not archivo_zip:
        st.warning("Esperando archivo de proyectos. Sube `Zonas.zip` desde la barra lateral.")
