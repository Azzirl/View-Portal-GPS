import networkx as nx
import pandas as pd

def construir_grafo(df):
    """
    Construye un grafo dirigido a partir de los campos HANDLE, HANDLE_TABLERO, HANDLE_ALIMENTADOR.
    """
    G = nx.DiGraph()
    
    if df.empty or 'HANDLE' not in df.columns:
        return G
        
    # Añadir todos los nodos (elementos)
    for _, row in df.iterrows():
        handle = str(row.get('HANDLE', '')).strip()
        if handle and handle != 'nan':
            # Guardamos los atributos del nodo para mostrarlos en la UI
            G.add_node(handle, **row.to_dict())
            
    # Añadir las aristas (relaciones)
    for _, row in df.iterrows():
        h_hijo = str(row.get('HANDLE', '')).strip()
        
        if not h_hijo or h_hijo == 'nan':
            continue
            
        # Relación 1: Tablero hacia Transformador (El trafo alimenta al tablero)
        h_trafo = str(row.get('HANDLE_TRAFO', '')).strip()
        if h_trafo and h_trafo != 'nan':
            G.add_edge(h_trafo, h_hijo, tipo="ALIMENTA")
            
        # Relación 2: Elemento hacia Tablero (El tablero alimenta al elemento)
        h_tablero = str(row.get('HANDLE_TABLERO', '')).strip()
        if h_tablero and h_tablero != 'nan':
            G.add_edge(h_tablero, h_hijo, tipo="ALIMENTA")
            
        # Relación 3: Elemento hacia Alimentador
        h_alim = str(row.get('HANDLE_ALIMENTADOR', '')).strip()
        if h_alim and h_alim != 'nan':
            G.add_edge(h_alim, h_hijo, tipo="CONECTADO_A")
            
    return G

def obtener_ruta_upstream(grafo, handle_inicio):
    """Rastrea la red hacia arriba (ej: Aireador -> Tablero -> Trafo)"""
    if handle_inicio not in grafo:
        return []
    
    try:
        # Devuelve los ancestros (elementos que alimentan a este nodo)
        ancestros = list(nx.ancestors(grafo, handle_inicio))
        ruta = []
        # Ordenamos los ancestros buscando el camino más corto en el grafo
        # Para simplificar en esta versión, devolvemos la lista de nodos padre
        for anc in ancestros:
            nodo_data = grafo.nodes[anc]
            tipo = nodo_data.get('TIPO_ELEMENTO', 'Desconocido')
            nombre = nodo_data.get('NOMBRE', nodo_data.get('ID_HANDLE', anc))
            ruta.append(f"{tipo}: {nombre}")
        return ruta
    except:
        return []
