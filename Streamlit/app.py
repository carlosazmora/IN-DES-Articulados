import streamlit as st
import pandas as pd
import plotly.express as px 
from datetime import datetime
from adzuna import cargar_datos_adzuna
from VariacionesSalariales import mostrar_variaciones_salariales
from Tendencias import mostrar_tendencias_e_insights


# Forzar caché limpio si es necesario
st.cache_data.clear()

st.set_page_config(page_title="Observatorio Laboral Unisabana", layout="wide", page_icon="📊")

# ==================== DATOS DE EJEMPLO ====================
@st.cache_data
def cargar_datos():
    df_programas = pd.DataFrame({
        'Programa': ['Ingeniería de Sistemas', 'Administración', 'Economía', 'Derecho', 'Marketing', 'Diseño Industrial'],
        'Empleabilidad_%': [94, 87, 85, 76, 89, 82],
        'Salario_inicial': [5200, 3900, 4300, 3100, 3700, 3600],
        'Crecimiento_%': [18, 9, 12, -4, 22, 11],
        'Sector': ['Tecnología', 'Finanzas', 'Finanzas', 'Legal', 'Marketing', 'Manufactura'],
        'Region': ['Nacional', 'Nacional', 'Nacional', 'Nacional', 'Nacional', 'Nacional']
    })
    
    df_competencias = pd.DataFrame({
        'Competencia': ['Python', 'Power BI / Tableau', 'Inglés Avanzado', 'IA Generativa', 'Liderazgo', 'Comunicación', 'Machine Learning'],
        'Demanda_%': [96, 89, 91, 94, 82, 87, 78],
        'Tipo': ['Técnica', 'Técnica', 'Transversal', 'Técnica', 'Transversal', 'Transversal', 'Técnica'],
        'Tendencia': ['Fuerte Crecimiento', 'Crecimiento', 'Estable', 'Fuerte Crecimiento', 'Estable', 'Estable', 'Crecimiento']
    })
    return df_programas, df_competencias

df_programas, df_competencias = cargar_datos()

# ==================== SIDEBAR ====================
st.sidebar.title("📊 Observatorio Laboral")


seccion = st.sidebar.radio("Navegación", [
    "🏠 Panel Ejecutivo",
    "🔎 Análisis por Programa",
    "🌍 Datos Internacionales",
    "📈 Tendencias e Insights",
    "🚨 Alertas",
    "💰 Variaciones Salariales",
    "🌍 Cobertura Geográfica",
    "📚 Fuentes",
    "🔧 Mantenimiento"
])

st.sidebar.caption(f"Actualizado: {datetime.now().strftime('%d %b %Y')}")

# ==================== PANEL EJECUTIVO ====================
if seccion == "🏠 Panel Ejecutivo":
    st.title("🏠 Panel Ejecutivo")
    st.markdown("**Monitoreo del Mercado Laboral - Universidad de La Sabana**")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Empleabilidad Promedio", "87.2%", "↑ 3.1")
    c2.metric("Programas en Riesgo", "3", "↓ 1")
    c3.metric("Competencias Emergentes", "7", "↑ 2")
    c4.metric("Salario Inicial Promedio", "$4.3M COP", "↑ 7.8%")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("¿Qué perfiles profesionales demanda el mercado?")
        fig_pie = px.pie(df_programas, names='Sector', values='Crecimiento_%', title="Demanda por Sector")
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        st.subheader("¿Qué competencias necesitan los graduados?")
        fig_bar = px.bar(df_competencias.head(7), x='Demanda_%', y='Competencia', color='Tipo', orientation='h')
        st.plotly_chart(fig_bar, use_container_width=True)
    
    st.subheader("¿Qué ocupaciones tienen mayor proyección?")
    st.dataframe(df_programas.sort_values('Crecimiento_%', ascending=False), use_container_width=True)

# ==================== ANÁLISIS POR PROGRAMA ====================
elif seccion == "🔎 Análisis por Programa":
    st.title("🔎 Análisis por Programa Académico")
    programa = st.selectbox("Selecciona un programa", df_programas['Programa'])
    info = df_programas[df_programas['Programa'] == programa].iloc[0]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Empleabilidad", f"{info['Empleabilidad_%']}%")
    col2.metric("Salario Inicial", f"${info['Salario_inicial']:,} COP")
    col3.metric("Crecimiento", f"{info['Crecimiento_%']}%", delta=f"{info['Crecimiento_%']}%")
    
    st.info(f"**Pertinencia frente al sector productivo:** Alta en el sector **{info['Sector']}**")

# ==================== TENDENCIAS E INSIGHTS ====================
elif seccion == "📈 Tendencias e Insights":
    st.title("📈 Tendencias e Insights Estratégicos")
    mostrar_tendencias_e_insights()

# ==================== ALERTAS ====================
elif seccion == "🚨 Alertas":
    st.title("🚨 Alertas Estratégicas")
    st.error("**Alto Riesgo:** Derecho (-4% crecimiento)")
    st.warning("**Moderado:** Administración necesita más analítica y IA")
    st.success("**Oportunidad:** Marketing Digital (+22% crecimiento)")

# ==================== VARIACIONES SALARIALES ====================
elif seccion == "💰 Variaciones Salariales":
    st.title("💰 Variaciones Salariales")
    mostrar_variaciones_salariales()

# ==================== COBERTURA GEOGRÁFICA ====================
elif seccion == "🌍 Cobertura Geográfica":
    st.title("🌍 Cobertura Geográfica")
    st.info("**Local (Bogotá / Cundinamarca) | Nacional | Internacional**")
    # Aquí puedes agregar filtros por región más adelante

# ==================== FUENTES ====================
elif seccion == "📚 Fuentes":
    st.title("📚 Fuentes de Información")
    st.write("**Principales fuentes:**")
    fuentes = ["Servicio Público de Empleo", "Ministerio del Trabajo", "Banco de la República", 
               "Ocupacol", "LinkedIn", "World Economic Forum", "McKinsey"]
    for f in fuentes:
        st.success(f"✅ {f}")

# ==================== MANTENIMIENTO ====================
elif seccion == "🔧 Mantenimiento":
    st.title("🔧 Mantenimiento y Sostenibilidad")
    st.subheader("Frecuencia de Actualización")
    st.write("- Datos: Mensual / Trimestral según fuente")
    st.write("- Dashboard: Automático cada vez que se actualicen los datos")
    st.write("- Auditoría: Mensual por responsable de Alumni")

# ==================== DATOS INTERNACIONALES ====================
elif seccion == "🌍 Datos Internacionales":
    st.title("🌍 Análisis Internacional - Adzuna")
    
    with st.spinner("Cargando datos de Adzuna..."):
        df_adzuna = cargar_datos_adzuna()
    
    if df_adzuna.empty:
        st.error("No se pudieron obtener datos de Adzuna")
    else:
        st.success(f"✅ Datos cargados: **{len(df_adzuna):,} registros**")
        
        col1, col2 = st.columns(2)
        with col1:
            pais_sel = st.selectbox("País", sorted(df_adzuna["pais_nombre"].unique()))
        with col2:
            todas = sorted(df_adzuna["perfil"].unique())
            perfil_sel = st.multiselect(
                "Profesiones", 
                options=todas,
                default=todas,
            )
        
        df_filtrado = df_adzuna[
            (df_adzuna["pais_nombre"] == pais_sel) & 
            (df_adzuna["perfil"].isin(perfil_sel))
        ].sort_values("vacantes", ascending=False)
        
        fig = px.bar(df_filtrado, x="perfil", y="vacantes", 
                     title=f"Vacantes en {pais_sel}",
                     color="perfil")
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabla limpia: solo las columnas que quieres
        columnas_mostrar = ["pais_nombre", "perfil", "vacantes"]
        st.dataframe(
            df_filtrado[columnas_mostrar], 
            use_container_width=True,
            hide_index=True
        )

st.caption("MVP - Observatorio del Mercado Laboral Unisabana • Hecho con Streamlit")