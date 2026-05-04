import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from DatosInternacionales import mostrar_boton_actualizacion, get_analisis_completo
from VariacionesSalariales import mostrar_variaciones_salariales
from Tendencias import mostrar_tendencias_e_insights

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
    "🎯 Habilidades",        ##########
    "📈 Tendencias e Insights",
    "🚨 Alertas",
    "💰 Variaciones Salariales",
    "🌍 Cobertura Geográfica",
    "📚 Fuentes",
    "🔧 Mantenimiento"
])

st.sidebar.caption(f"{datetime.now().strftime('%d %b %Y')}")

# ==================== PANEL EJECUTIVO ====================
if seccion == "🏠 Panel Ejecutivo":
    st.title("🏠 Panel Ejecutivo")
    st.markdown("**Observatorio del Mercado Laboral - Alumni Sabana**")

    # --- Orquestación de datos Adzuna ---
    with st.expander("🔄 Gestión de datos internacionales (Adzuna)", expanded=True):
        mostrar_boton_actualizacion()

    st.divider()



    ####=========================================================================================== código nuevo de prueba
    # --- DuckDB: persistencia entre sesiones ---
    from DatosInternacionales import (
        bd_existe, tabla_existe,
        funcion_creacion, funcion_actualizacion,
        DB_PATH, TABLA
    )
    import duckdb as _ddb

    existe_bd    = bd_existe()
    existe_tabla = existe_bd and tabla_existe()

    with st.expander("🦆 Gestión de base de datos persistente (DuckDB)", expanded=True):
        col_estado, col_boton = st.columns([3, 1])

        if existe_bd and existe_tabla:
            con      = _ddb.connect(DB_PATH, read_only=True)
            n_filas  = con.execute(f"SELECT COUNT(*) FROM {TABLA}").fetchone()[0]
            fecha_db = con.execute(f"SELECT MAX(fecha_extraccion) FROM {TABLA}").fetchone()[0]
            con.close()
            with col_estado:
                st.caption(f"✅ BD lista · **{n_filas:,} registros** · Última extracción: **{fecha_db}**")
            with col_boton:
                if st.button("🔄 Actualizar BD", use_container_width=True):
                    log_lines = []
                    with st.spinner("Actualizando DuckDB..."):
                        funcion_actualizacion(log_fn=log_lines.append)
                    st.success("✅ BD actualizada.")
                    with st.expander("Ver log"):
                        st.text("\n".join(log_lines))
                    st.rerun()
        else:
            with col_estado:
                msg = "❌ Base de datos no encontrada." if not existe_bd else "❌ Tabla no encontrada."
                st.caption(f"{msg} Presiona **Crear BD** para inicializarla.")
            with col_boton:
                if st.button("🟢 Crear BD", use_container_width=True):
                    log_lines = []
                    with st.spinner("Creando base de datos..."):
                        funcion_creacion(log_fn=log_lines.append)
                    st.success("✅ BD creada.")
                    with st.expander("Ver log"):
                        st.text("\n".join(log_lines))
                    st.rerun()
    from DatosInternacionales import DB_PATH ## borrable
    st.info(f"Ruta del .duckdb: `{DB_PATH}`")  ## borrable
    st.divider()
    #### Finalización Código de porueba ======================
    #### Prueba de Habilidades ======================================================
    # --- DuckDB: Habilidades O*NET ---
    from Habilidades import (
        pipeline_datos as habilidades_pipeline,
        bd_tiene_datos, DB_PATH as HAB_DB_PATH,
        TABLA_SK, TABLA_KN, TABLA_OCC
        )
    import duckdb as _ddb2

    _hab_lista = bd_tiene_datos()

    with st.expander("🎯 Gestión de datos de Habilidades O*NET (DuckDB)", expanded=True):
        col_estado, col_boton = st.columns([3, 1])

        if _hab_lista:
            _con = _ddb2.connect(HAB_DB_PATH, read_only=True)
            _n_sk  = _con.execute(f"SELECT COUNT(*) FROM {TABLA_SK}").fetchone()[0]
            _n_kn  = _con.execute(f"SELECT COUNT(*) FROM {TABLA_KN}").fetchone()[0]
            _n_occ = _con.execute(f"SELECT COUNT(*) FROM {TABLA_OCC}").fetchone()[0]
            _con.close()
            with col_estado:
                st.caption(
                    f"✅ Habilidades listas · "
                    f"Skills: **{_n_sk:,}** · "
                    f"Knowledge: **{_n_kn:,}** · "
                    f"Ocupaciones: **{_n_occ:,}**"
                )
            with col_boton:
                if st.button("🔄 Actualizar Habilidades", use_container_width=True, key="btn_hab_update"):
                    _log = []
                    with st.spinner("Descargando O*NET y actualizando tablas..."):
                        try:
                            habilidades_pipeline(log_fn=_log.append)
                            st.cache_data.clear()
                            st.success("✅ Habilidades actualizadas.")
                        except Exception as _e:
                            st.error(f"❌ Error: {_e}")
                    with st.expander("Ver log"):
                        st.text("\n".join(_log))
                    st.rerun()
        else:
            with col_estado:
                st.caption("❌ Tablas de habilidades no encontradas. Presiona **Crear Habilidades** para inicializarlas.")
            with col_boton:
                if st.button("🟢 Crear Habilidades", use_container_width=True, key="btn_hab_create"):
                    _log = []
                    with st.spinner("Descargando O*NET... (puede tardar ~1 min)"):
                        try:
                            habilidades_pipeline(log_fn=_log.append)
                            st.cache_data.clear()
                            st.success("✅ Tablas de habilidades creadas.")
                        except Exception as _e:
                            st.error(f"❌ Error: {_e}")
                    with st.expander("Ver log"):
                        st.text("\n".join(_log))
                    st.rerun()
#### finalización prueba Habilidades

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

# ===================== HABILIDADES==================================================================================
# ==================== HABILIDADES ====================
elif seccion == "🎯 Habilidades":
    from Habilidades import mostrar_habilidades
    mostrar_habilidades()
# ==================== DATOS INTERNACIONALES ====================
elif seccion == "🌍 Datos Internacionales":
    st.title("🌍 Análisis Internacional - Adzuna")

    data = get_analisis_completo()

    if data is None:
        st.warning("⚠️ Sin datos cargados. Ve al **Panel Ejecutivo** y presiona 🔄 Actualizar datos.")
    else:
        df_adzuna = data['df']
        st.success(f"✅ Datos cargados: **{len(df_adzuna):,} registros**")

        col1, col2 = st.columns(2)
        with col1:
            pais_sel = st.selectbox("País", sorted(df_adzuna["pais_nombre"].unique()))
        with col2:
            todas = sorted(df_adzuna["perfil"].unique())
            perfil_sel = st.multiselect("Profesiones", options=todas, default=todas)

        df_filtrado = df_adzuna[
            (df_adzuna["pais_nombre"] == pais_sel) &
            (df_adzuna["perfil"].isin(perfil_sel))
        ].sort_values("vacantes", ascending=False)

        fig = px.bar(df_filtrado, x="perfil", y="vacantes",
                     title=f"Vacantes en {pais_sel}", color="perfil")
        st.plotly_chart(fig, use_container_width=True)

        columnas_mostrar = ["pais_nombre", "perfil", "vacantes"]
        st.dataframe(df_filtrado[columnas_mostrar], use_container_width=True, hide_index=True)

st.caption("Observatorio del Mercado Laboral - Alumni Sabana")




