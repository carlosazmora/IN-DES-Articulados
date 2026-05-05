import streamlit as st
import plotly.express as px
from DatosInternacionales import get_analisis_completo

def mostrar_variaciones_salariales():
    data = get_analisis_completo()

    if data is None:
        st.info("⚠️ Sin datos cargados. Ve al **Panel de Actualización** y presiona '🔄 Actualizar DB' para habilitarlo.")
        return

    # ====================== TÍTULO (sin duplicar) ======================
    st.subheader("💰 Análisis de Variaciones Salariales Internacionales")
    st.caption("**Demanda de vacantes (Adzuna) como proxy de presión salarial** • Mayor demanda = Mayor presión alcista en salarios")

    st.divider()

    # ====================== 1. TOP PRESIÓN SALARIAL ======================
    st.subheader("1️⃣ Perfiles con Mayor Presión Salarial")

    top_perfiles = data['top_perfiles'].head(12).copy()

    col1, col2 = st.columns([3, 2])

    with col1:
        fig_bar = px.bar(
            top_perfiles,
            x='perfil',
            y='vacantes_total',
            title="Demanda por Perfil (Mayor vacantes = Mayor presión salarial)",
            color='vacantes_total',
            color_continuous_scale='Blues',
            text='vacantes_total'
        )
        fig_bar.update_traces(texttemplate='%{text:,}', textposition='outside')
        fig_bar.update_layout(xaxis_title="Perfil", yaxis_title="Vacantes Totales", height=500)
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        st.dataframe(
            top_perfiles[['perfil', 'vacantes_total']].style.format({"vacantes_total": "{:,}"}),
            use_container_width=True,
            hide_index=True
        )

    # ====================== 2. PRESIÓN SALARIAL POR PAÍS ======================
    st.subheader("2️⃣ Presión Salarial por Región")

    df_pais = data['df_pais'].sort_values('vacantes_total', ascending=False).copy()

    # Filtro geográfico
    regiones = {
        "🌍 Todos los Países": df_pais,
        "🌍 Anglosajón (Alta Oportunidad)": df_pais[df_pais['pais_nombre'].isin(['EE.UU.', 'Reino Unido', 'Canadá', 'Australia', 'Nueva Zelanda'])],
        "🌍 Europa Continental": df_pais[df_pais['pais_nombre'].isin(['Alemania', 'Francia', 'Países Bajos', 'Bélgica', 'Austria', 'Suiza', 'Italia', 'España', 'Polonia'])],
        "🌎 Latinoamérica": df_pais[df_pais['pais_nombre'].isin(['Brasil', 'México'])],
        "🌏 Asia y Otros": df_pais[df_pais['pais_nombre'].isin(['India', 'Singapur', 'Sudáfrica'])]
    }

    region_seleccionada = st.selectbox(
        "Filtrar por región geográfica:",
        options=list(regiones.keys()),
        index=0
    )

    df_filtrado = regiones[region_seleccionada]

    col1, col2 = st.columns([3, 2])

    with col1:
        fig_pie = px.pie(
            df_filtrado,
            names='pais_nombre',
            values='vacantes_total',
            title=f"Distribución de Oportunidades - {region_seleccionada}",
            hole=0.4
        )
        fig_pie.update_traces(textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        st.markdown("**Ranking de Presión Salarial**")
        st.dataframe(
            df_filtrado[['pais_nombre', 'vacantes_total']].style.format({"vacantes_total": "{:,}"}),
            use_container_width=True,
            hide_index=True
        )

    # ====================== 3. INSIGHTS CLAVE ======================
    st.subheader("3️⃣ Insights Clave")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**🔥 Perfiles con mayor presión alcista:**")
        for i, row in top_perfiles.head(6).iterrows():
            st.success(f"{i+1}. **{row['perfil']}** — {row['vacantes_total']:,} vacantes")

    with col2:
        st.markdown("**🌍 Países con mayor presión salarial:**")
        top_paises = df_pais.head(6)
        for i, row in top_paises.iterrows():
            st.success(f"{i+1}. **{row['pais_nombre']}** — {row['vacantes_total']:,} vacantes")

    st.info("""
    **Regla clave:**  
    A mayor volumen de vacantes → mayor competencia entre empresas → **mayor presión alcista en los salarios**.  
    Los roles de **IA, Data Science y Ciberseguridad** lideran las variaciones salariales positivas actualmente.
    """)

    # ====================== 4. RECOMENDACIONES ======================
    st.subheader("4️⃣ Recomendaciones Estratégicas")

    st.markdown("""
    | Estrategia                                      | Potencial de Crecimiento Salarial | Recomendación      |
    |------------------------------------------------|-----------------------------------|--------------------|
    | Especializarte en **IA / Machine Learning**     | Muy Alto                          | ★★★★★ Prioridad #1 |
    | Enfocarte en **Ciberseguridad**                 | Alto                              | ★★★★ Muy recomendable |
    | Buscar oportunidades en **EE.UU., Alemania, UK**| Muy Alto                          | ★★★★★ Ideal        |
    | Aplicar remotamente a empresas extranjeras      | Alto                              | ★★★★ Excelente     |
    | Quedarte solo en roles generales                | Medio-Bajo                        | ★★ Menos favorable |
    """)

    st.caption("📊 Fuente: Adzuna • Datos actualizados • Proxy de presión salarial")