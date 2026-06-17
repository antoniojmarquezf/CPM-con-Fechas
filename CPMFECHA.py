import streamlit as st
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
from datetime import date

st.set_page_config(layout="wide")

st.title("🎯 Juego CPM - Ruta Crítica")

# =====================================================
# FASE 1: Construcción del grafo
# =====================================================

st.header("1️⃣ Construye el grafo del proyecto")

edges_input = st.text_area(
    "Escribe las relaciones (Actividad,Sucesora), una por línea",
    """A,B
A,C
B,D
C,D
D,E
D,F
E,G
F,G"""
)

edges = []

if edges_input:

    for line in edges_input.splitlines():

        if line.strip():

            parts = line.split(",")

            origen = parts[0].strip()

            sucesores = [p.strip() for p in parts[1:]]

            for suc in sucesores:

                if suc not in ["", "-"]:

                    edges.append((origen, suc))

# Crear grafo
G = nx.DiGraph()
G.add_edges_from(edges)

# Dibujar grafo
st.subheader("Red del proyecto")

fig, ax = plt.subplots(figsize=(8,6))

pos = nx.spring_layout(G, seed=42)

nx.draw(
    G,
    pos,
    with_labels=True,
    node_color="lightblue",
    node_size=2500,
    arrowsize=20,
    font_size=12,
    ax=ax
)

st.pyplot(fig)

# =====================================================
# FASE 2: Fechas y duraciones
# =====================================================

st.header("2️⃣ Ingresa las fechas")

nodes = sorted(list(G.nodes()))

if "fechas_df" not in st.session_state:

    hoy = date.today()

    st.session_state.fechas_df = pd.DataFrame({
        "Actividad": nodes,
        "Fecha Inicio": [hoy for _ in nodes],
        "Fecha Fin": [hoy for _ in nodes]
    })

fechas = st.data_editor(
    st.session_state.fechas_df,
    num_rows="dynamic",
    use_container_width=True
)

# =====================================================
# Calcular duraciones
# =====================================================

dur_cal = {}
dur_hab = {}

for _, row in fechas.iterrows():

    actividad = row["Actividad"]

    if pd.notnull(actividad):

        inicio = pd.to_datetime(row["Fecha Inicio"])
        fin = pd.to_datetime(row["Fecha Fin"])

        # Días calendario
        dias_cal = (fin - inicio).days + 1
        dias_cal = max(dias_cal, 0)

        # Días hábiles
        dias_hab = np.busday_count(
            inicio.date(),
            fin.date()
        ) + 1

        dias_hab = max(dias_hab, 0)

        dur_cal[actividad] = dias_cal
        dur_hab[actividad] = dias_hab

# Mostrar duraciones calculadas
tabla_dur = pd.DataFrame({
    "Actividad": list(dur_cal.keys()),
    "Duración Calendario": list(dur_cal.values()),
    "Duración Hábil": [dur_hab[a] for a in dur_cal.keys()]
})

st.subheader("📅 Duraciones calculadas")
st.dataframe(tabla_dur, use_container_width=True)

# =====================================================
# Selección del tipo de duración
# =====================================================

tipo_duracion = st.radio(
    "Selecciona el tipo de duración para el CPM:",
    [
        "Días calendario",
        "Días hábiles"
    ]
)

if tipo_duracion == "Días calendario":
    dur_dict = dur_cal
else:
    dur_dict = dur_hab

# =====================================================
# Cálculo CPM
# =====================================================

if st.button("🚀 Calcular CPM"):

    # Verificar duraciones faltantes
    faltantes = [n for n in G.nodes() if n not in dur_dict]

    if faltantes:
        st.error(
            f"Faltan fechas para: {', '.join(faltantes)}"
        )
        st.stop()

    # ---------------------------------
    # Forward Pass
    # ---------------------------------

    ES = {}
    EF = {}

    for node in nx.topological_sort(G):

        preds = list(G.predecessors(node))

        if len(preds) == 0:
            ES[node] = 0
        else:
            ES[node] = max(EF[p] for p in preds)

        EF[node] = ES[node] + dur_dict[node]

    # ---------------------------------
    # Backward Pass
    # ---------------------------------

    LS = {}
    LF = {}

    duracion_total = max(EF.values())

    for node in reversed(
        list(nx.topological_sort(G))
    ):

        succs = list(G.successors(node))

        if len(succs) == 0:
            LF[node] = duracion_total
        else:
            LF[node] = min(
                LS[s] for s in succs
            )

        LS[node] = LF[node] - dur_dict[node]

    # ---------------------------------
    # Holgura
    # ---------------------------------

    Slack = {
        n: LS[n] - ES[n]
        for n in G.nodes()
    }

    ruta_critica = [
        n for n in G.nodes()
        if Slack[n] == 0
    ]

    # ---------------------------------
    # Resultados
    # ---------------------------------

    result = pd.DataFrame({

        "Actividad": list(G.nodes()),

        "Duración": [
            dur_dict[n]
            for n in G.nodes()
        ],

        "ES": [
            ES[n]
            for n in G.nodes()
        ],

        "EF": [
            EF[n]
            for n in G.nodes()
        ],

        "LS": [
            LS[n]
            for n in G.nodes()
        ],

        "LF": [
            LF[n]
            for n in G.nodes()
        ],

        "Holgura": [
            Slack[n]
            for n in G.nodes()
        ]
    })

    st.subheader("📊 Resultados CPM")

    st.dataframe(
        result,
        use_container_width=True
    )

    st.success(
        f"🚩 Ruta crítica: {' → '.join(ruta_critica)}"
    )

    st.info(
        f"Duración total del proyecto: "
        f"{duracion_total} "
        f"{'días calendario' if tipo_duracion=='Días calendario' else 'días hábiles'}"
    )

    # =================================================
    # Grafo con ruta crítica
    # =================================================

    st.subheader("🔴 Ruta crítica en el grafo")

    fig2, ax2 = plt.subplots(
        figsize=(8,6)
    )

    colores = [
        "red"
        if n in ruta_critica
        else "lightblue"
        for n in G.nodes()
    ]

    nx.draw(
        G,
        pos,
        with_labels=True,
        node_color=colores,
        node_size=2500,
        arrowsize=20,
        font_size=12,
        ax=ax2
    )

    st.pyplot(fig2)
