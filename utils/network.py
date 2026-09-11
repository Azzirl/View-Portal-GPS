import networkx as nx
import pandas as pd

def construir_grafo(df):
    """
    Genera el grafo dirigido de infraestructura relacionando los elementos del CAD.
    """
    G = nx.DiGraph()

    if df.empty or 'HANDLE' not in df.columns:
        return G

    # Agregar nodos con sus atributos técnicos
    for _, row in df.iterrows():
        handle = str(row.get('HANDLE', '')).strip()
        if handle and handle != 'nan':
            G.add_node(handle, **row.to_dict())

    # Construir relaciones topológicas (padre -> hijo)
    for _, row in df.iterrows():
        h_hijo = str(row.get('HANDLE', '')).strip()
        if not h_hijo or h_hijo == 'nan':
            continue

        h_trafo = str(row.get('HANDLE_TRAFO', '')).strip()
        if h_trafo and h_trafo != 'nan':
            G.add_edge(h_trafo, h_hijo, tipo="ALIMENTA")

        h_tablero = str(row.get('HANDLE_TABLERO', '')).strip()
        if h_tablero and h_tablero != 'nan':
            G.add_edge(h_tablero, h_hijo, tipo="ALIMENTA")

        h_alim = str(row.get('HANDLE_ALIMENTADOR', '')).strip()
        if h_alim and h_alim != 'nan':
            G.add_edge(h_alim, h_hijo, tipo="CONECTADO_A")

    return G

def obtener_ruta_upstream(grafo, handle_inicio):
    """
    Busca los elementos jerárquicamente superiores (Aireador -> Tablero -> Transformador).
    """
    if handle_inicio not in grafo:
        return []

    try:
        ancestros = list(nx.ancestors(grafo, handle_inicio))
        ruta = []
        for anc in ancestros:
            nodo_data = grafo.nodes[anc]
            tipo = nodo_data.get('TIPO_ELEMENTO', 'Desconocido')
            nombre = nodo_data.get('NOMBRE', nodo_data.get('ID_HANDLE', anc))
            ruta.append(f"{tipo}: {nombre}")
        return ruta
    except Exception:
        return []

def extraer_tramos_red(grafo):
    """
    Extrae los pares de coordenadas origen-destino para dibujar las líneas eléctricas de la red en el mapa.
    """
    tramos = []
    for u, v, data in grafo.edges(data=True):
        if u in grafo.nodes and v in grafo.nodes:
            n1 = grafo.nodes[u]
            n2 = grafo.nodes[v]
            if pd.notna(n1.get('LATITUD')) and pd.notna(n1.get('LONGITUD')) and \
               pd.notna(n2.get('LATITUD')) and pd.notna(n2.get('LONGITUD')):
                tramos.append({
                    'origen_coords': [n1['LATITUD'], n1['LONGITUD']],
                    'destino_coords': [n2['LATITUD'], n2['LONGITUD']],
                    'tipo_relacion': data.get('tipo', 'CONEXION'),
                    'origen_tipo': n1.get('TIPO_ELEMENTO', ''),
                    'destino_tipo': n2.get('TIPO_ELEMENTO', '')
                })
    return tramos
