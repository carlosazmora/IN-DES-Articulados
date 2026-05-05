import streamlit as st
from DatosInternacionales import get_contexto_para_ia
from ia_analisis import generar_insight_claude

# Lista de pregrados (puedes expandirla)
PROGRAMAS = [
    "Ingeniería de Sistemas",
    "Administración de Empresas",
    "Economía",
    "Derecho",
    "Marketing",
    "Diseño Industrial",
    "Ingeniería Industrial",
    "Psicología",
    "Medicina",
    "Enfermería",
    "Contaduría Pública",
    "Ingeniería Mecánica",
    "Arquitectura",
    "Comunicación Social"
]

# Preguntas frecuentes por programa
PREGUNTAS_FRECUENTES = [
    # --- BLOQUE: DASHBOARD Y PANEL EJECUTIVO ---
    "1. ¿Qué perfiles profesionales demanda el mercado actualmente para este programa?",
    "2. ¿Qué competencias específicas necesitan los graduados para integrarse con éxito?",
    "3. ¿Qué tan pertinente es el programa académico frente a las necesidades del sector productivo?",
    "4. ¿Qué puestos de trabajo son los más demandados para este perfil profesional?",
    "5. ¿Qué ocupaciones dentro de esta área tienen la mayor proyección de crecimiento?",
    "6. ¿Cómo está cambiando la empleabilidad para este programa (Tendencias de aumento/disminución)?",
    
    # --- BLOQUE: VARIACIONES Y SECTORES ---
    "7. ¿Cuáles son las variaciones totales de empleo detectadas en este sector?",
    "8. ¿Qué variaciones por sectores económicos afectan más a este programa?",
    "9. ¿Qué programas o áreas específicas de esta carrera se encuentran en riesgo por la IA?",
    "10. ¿Cuáles son las nuevas oportunidades laborales identificadas para este perfil?",
    "11. ¿En qué sectores se observa una disminución significativa de la demanda?",
    
    # --- BLOQUE: ANÁLISIS SALARIAL ---
    "12. ¿Cómo se comportan las variaciones salariales por sector para este programa?",
    "13. ¿Cuál es la variación salarial según la experiencia requerida por las empresas?",
    "14. ¿Cómo influye la experiencia obtenida en el incremento del salario para este profesional?",
    "15. ¿Cuál es la comparación salarial para este cargo a nivel local, nacional e internacional?",
    
    # --- BLOQUE: TENDENCIAS E INSIGHTS ---
    "16. ¿Qué brechas críticas se han identificado entre la oferta y la demanda de este talento?",
    "17. ¿Cuáles son las habilidades técnicas emergentes que el mercado está solicitando?",
    "18. ¿Qué habilidades blandas son ahora indispensables para este programa académico?",
    "19. ¿Cuáles son los sectores con mayor crecimiento en términos de trabajos y vacantes?",
    "20. ¿Qué habilidades tradicionales de este programa han sido ya reemplazadas por la IA?",
    "21. ¿Cuáles sectores relacionados tendrán menos cabida en el mercado a razón de la IA?",
    
    # --- BLOQUE: CONSOLIDACIÓN Y FUENTES ---
    "22. ¿Se clasifica la tendencia de este programa como una consolidación fuerte o mantenimiento?",
    "23. ¿Cómo es el crecimiento relativo de las tendencias de estudio frente a las laborales?",
    "24. ¿Qué alertas de variabilidad existen para los salarios más altos de este sector?",
    "25. ¿Cuál es el nivel de confianza y frecuencia de actualización de las fuentes para estos datos?"
]

def analizar_por_programa():
    st.markdown("Selecciona un programa y una pregunta para obtener un análisis inteligente con Claude.")

    col1, col2 = st.columns(2)

    with col1:
        programa_sel = st.selectbox(
            "🎓 Programa Académico",
            options=PROGRAMAS,
            index=0
        )

    with col2:
        # Preguntas dinámicas según el programa
        preguntas = PREGUNTAS_FRECUENTES.get(programa_sel, PREGUNTAS_FRECUENTES["default"])
        pregunta_sel = st.selectbox(
            "❓ Pregunta",
            options=preguntas,
            index=0
        )

    # Contexto para Claude
    contexto = get_contexto_para_ia()

    if "Sin datos" in contexto:
        st.info("⚠️ Sin datos cargados. Ve al **Panel Ejecutivo** → Gestión de DuckDB y actualiza la base de datos.")
        return

    # Botón para generar análisis
    if st.button("Generar Análisis con Claude", use_container_width=True):
        prompt_completo = f"""
Programa seleccionado: {programa_sel}

Pregunta: {pregunta_sel}

Contexto de datos disponibles:
{contexto}
"""

        with st.spinner("Claude está analizando..."):
            respuesta = generar_insight_claude(
                panel_nombre=f"Análisis de {programa_sel}",
                contexto_datos=prompt_completo
            )

            if respuesta:
                st.success(f"**Análisis de {programa_sel}**")
                st.markdown(respuesta)
            else:
                st.error("No se pudo obtener respuesta de Claude.")


    st.caption("💡 El análisis se genera en tiempo real combinando datos de Adzuna + O*NET + conocimiento general de Claude.")