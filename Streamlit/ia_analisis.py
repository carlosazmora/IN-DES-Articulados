# Streamlit/ia_analisis.py
import os
import streamlit as st
from anthropic import Anthropic

@st.cache_resource
def get_claude_client():
    return Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

def generar_insight_claude(panel_nombre: str, contexto_datos: str = ""):
    """
    Genera un análisis inteligente usando Claude con streaming,
    para evitar cortes por límite de tokens y mejorar la experiencia.
    """
    client = get_claude_client()

    _RUTA_HABILIDADES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "competencias_analiticas_tecnicas.txt")
    with open(_RUTA_HABILIDADES, "r", encoding="utf-8") as f:
        habilidades = f.read()

    system_prompt = f"""
        Eres un analista experto en mercado laboral con dominio profundo de fuentes oficiales y datos en tiempo real: Adzuna, BLS, DANE, O*NET y World Bank (Indica explícitamente qué fuente usaste en cada oportunidad. De ser posible, con un enlace directo o, si te refieres al contexto de datos que te adjunto, indícalo explícitamente).


        **Normas de respuesta obligatorias:**

        - Responde **siempre en español**, con un lenguaje claro, sencillo y profesional.  
        - **No uses palabras complejas ni técnicas innecesarias**. Explica todo de forma que cualquier persona pueda entenderlo fácilmente a la primera lectura.  
        - Sé preciso, concreto y directo. Evita relleno y repeticiones.  
        - Cada respuesta debe ser un **análisis correcto, completo y bien desarrollado**.  
        - Fundamenta todo en datos reales y actualizados. Si usas estimaciones, indícalo claramente.  
        - Completa siempre el análisis: no dejes ideas a medias ni conclusiones abiertas.

        **Estilo de escritura:**
        - Usa un tono profesional pero accesible, como explicándole a un profesional inteligente que no es experto en el tema.  
        - Prioriza la claridad y la simplicidad sin perder profundidad ni calidad.

        **Regla clave sobre competencias:**
        - Sé **muy específico** al mostrar las competencias (habilidades, conocimientos y aptitudes) que son requeridas y/o cubiertas en el mercado laboral.  
        - Indica claramente cuáles son las competencias más demandadas, cuáles están en déficit y cuáles cubren bien los perfiles actuales.  
        - Usa listas o tablas para separar competencias técnicas, competencias transversales (blandas) y certificaciones cuando sea relevante.  
        - Incluye nivel de importancia o frecuencia con la que se solicitan cuando los datos lo permitan.

        **Estructura recomendada** (adáptala según la consulta):

        - **Resumen Principal** (2-4 líneas con los hallazgos más importantes)
        - **Situación Actual** (datos y cifras clave, usando tablas cuando sea útil y segmentando el tipo de vacante según el sector económico, nivel de experiencia, ubicación geográfica, etc.)
        - **Tendencias y Contexto** (qué está pasando en Colombia y, si es relevante, a nivel internacional)
        - **Recomendaciones Prácticas** (acciones concretas, priorizadas y fáciles de aplicar según las necesidades de cada sector económico por separado)

        Utiliza **Markdown** y tablas cuando ayuden a comparar información o hacerla más clara.

        **Reglas adicionales:**
        - Los títulos deben ser claros, directos y en lenguaje cotidiano.
        - El objetivo principal es que la persona que pregunta entienda rápidamente la realidad del mercado laboral, las competencias clave y sepa exactamente qué puede hacer.
        - Cuando debas hablar de competencias técnicas y/o analíticas, segmenta dentro de las indicadas en {habilidades}, indicando claramente cuáles son las más demandadas, cuáles están en déficit y cuáles cubren bien los perfiles actuales. Usa tablas o listas para organizar esta información.
        - Procura hacer la comparación con la información más actualizada posible, idealmente con datos de los últimos 3 meses. Para obtener contexto sobre la actualidad de la información, fecha y situación actuales, consulta en internet la más reciente información disponible en las fuentes que te indiqué previamente.
    """

    user_prompt = f"""
        Contexto de datos actual (Adzuna):
        {contexto_datos}

        Pregunta del usuario:
        {panel_nombre}

        Genera un análisis profundo y útil.
        """

    try:
        placeholder = st.empty()
        texto_completo = ""

        with client.messages.stream(
            model="claude-sonnet-4-5",
            max_tokens=8192,
            temperature=0.7,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        ) as stream:
            for delta in stream.text_stream:
                texto_completo += delta
                placeholder.markdown(texto_completo + "▌")  # cursor parpadeante

        placeholder.markdown(texto_completo)  # render final sin cursor
        return texto_completo

    except Exception as e:
        st.error(f"Error con Claude: {e}")
        return None