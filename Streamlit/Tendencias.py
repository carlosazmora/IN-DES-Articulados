import streamlit as st
import plotly.express as px
from DatosInternacionales import get_analisis_completo
from ia_analisis import generar_insight_claude

def mostrar_tendencias_e_insights():
    if st.button("🤖 Generar Análisis con Claude"):
        data = get_analisis_completo()  # tu función actual
        contexto = data['df'].to_string(max_rows=20)  # o un resumen
        respuesta = generar_insight_claude(
            panel_nombre="Tendencias e Insights Estratégicos",
            contexto_datos=contexto
        )
        if respuesta:
            st.markdown(respuesta)