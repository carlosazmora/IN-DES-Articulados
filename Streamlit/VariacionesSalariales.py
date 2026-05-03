import streamlit as st
import plotly.express as px
from adzuna import get_analisis_completo

def mostrar_variaciones_salariales():
    data = get_analisis_completo()
    
    st.subheader("Demanda por Perfil (proxy de oportunidad salarial)")
    fig = px.bar(data['top_perfiles'], 
                 x='perfil', y='vacantes_total',
                 title="Demanda por Perfil (mayor vacantes = mayor presión salarial)")
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("Distribución de vacantes por país")
    fig_pie = px.pie(data['df_pais'], names='pais_nombre', values='vacantes_total')
    st.plotly_chart(fig_pie, use_container_width=True)