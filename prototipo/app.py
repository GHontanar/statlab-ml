"""StatLab ML – ejecución independiente de la página de k-means."""
import streamlit as st

from statlab_ml.ui_kmeans import render

st.set_page_config(page_title="StatLab ML · k-means", page_icon="🧩", layout="wide")
render()
