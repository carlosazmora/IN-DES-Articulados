import streamlit as st
from DatosInternacionales import get_contexto_para_ia
from ia_analisis import generar_insight_claude
 
def mostrar_tendencias_e_insights():
    contexto = get_contexto_para_ia()
 
    # Avisar al usuario si no hay datos aún
    if "Sin datos" in contexto:
        st.info("⚠️ Sin datos cargados. Ve al **Panel de Actualización** y presiona '🔄 Actualizar DB' para habilitarlo.")
 
    # if st.button("Generar Análisis con Claude", disabled=("Sin datos" in contexto)):
    if st.button("Generar Análisis con Claude", disabled = True):
        generar_insight_claude(
            panel_nombre="Tendencias e Insights Estratégicos",
            contexto_datos=contexto
        )
    st.caption("🔍 *Nota: La función de análisis con Claude está temporalmente deshabilitada. Si te interesa explorarla, contáctanos en www.linkedin.com/in/carlosazmora, https://www.linkedin.com/in/celyjorge/, https://www.linkedin.com/in/alejandro-morantes-castellanos, https://www.linkedin.com/in/dianapaolaquintero?utm_source=share_via&utm_content=profile&utm_medium=member_android*")