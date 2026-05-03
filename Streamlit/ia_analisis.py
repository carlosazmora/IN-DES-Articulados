# Streamlit/ia_analisis.py
import streamlit as st
from anthropic import Anthropic
import time

@st.cache_resource
def get_claude_client():
    return Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

def generar_insight_claude(panel_nombre: str, contexto_datos: str = ""):
    """
    Genera un análisis inteligente usando Claude.
    """
    client = get_claude_client()
    
    # Prompt base (puedes tener uno por panel)
    system_prompt = """Eres un analista experto en mercado laboral con acceso a datos de Adzuna, BLS, DANE, O*NET y World Bank.
Responde siempre en español, de forma estructurada, analítica y basada en evidencia.
Usa Markdown con tablas cuando sea útil. Sé preciso y evita generalidades."""

    user_prompt = f"""
Contexto de datos actual (Adzuna):
{contexto_datos}

Pregunta del usuario:
{panel_nombre}

Genera un análisis profundo y útil.
"""

    with st.spinner("Claude está analizando..."):
        try:
            with st.status("Consultando Claude...", expanded=True) as status:
                response = client.messages.create(
                    model="claude-sonnet-4-5",   # o claude-3-opus-20240229
                    max_tokens=1200,
                    temperature=0.7,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}]
                )
                status.update(label="✅ Análisis completado", state="complete")
            
            return response.content[0].text

        except Exception as e:
            st.error(f"Error con Claude: {e}")
            return None