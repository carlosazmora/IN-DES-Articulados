import sys
import os
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from DatosInternacionales import (
    mostrar_boton_actualizacion, get_analisis_completo, 
    tabla_existe, bd_existe,
    funcion_creacion, funcion_actualizacion, DB_PATH, TABLA
)
from AnalisisPorPrograma import analizar_por_programa
from VariacionesSalariales import mostrar_variaciones_salariales
from Tendencias import mostrar_tendencias_e_insights
from Habilidades import ( mostrar_habilidades, pipeline_datos, 
    bd_tiene_datos, pipeline_datos as habilidades_pipeline,
    bd_tiene_datos, DB_PATH as HAB_DB_PATH,
    TABLA_SK, TABLA_KN, TABLA_OCC
)
import duckdb as _ddb2
import duckdb as _ddb

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(page_title="Observatorio Laboral Unisabana", layout="wide", page_icon="📊")

# ==================== NUEVA FUNCIÓN DE PROGRESO ====================
def ejecutar_con_progreso(funcion_proceso, mensaje_inicial: str):
    """Ejecuta mostrando porcentaje real basado en logs tipo [x/total]"""
    
    status_text = st.empty()
    log_lines = []
    total = None

    def log_callback(mensaje: str):
        nonlocal total
        log_lines.append(mensaje)

        import re
        match = re.search(r"\[(\d+)/(\d+)\]", mensaje)

        if match:
            actual = int(match.group(1))
            total = int(match.group(2))
            porcentaje = int((actual / total) * 100)

            status_text.markdown(f"### ⏳ {porcentaje}% completado")
        else:
            status_text.markdown("### ⏳ Procesando...")

    try:
        with st.spinner(mensaje_inicial):
            funcion_proceso(log_fn=log_callback)

        status_text.markdown("### ✅ 100% completado")

        with st.expander("📋 Ver log completo"):
            st.text("\n".join(log_lines))

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

    st.rerun()

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
    "🏠 Panel de Actualización",
    "🔎 Análisis por Programa",
    "🌍 Datos Internacionales",
    "🎯 Habilidades",
    "📈 Tendencias e Insights",
    "🚨 Alertas",
    "💰 Variaciones Salariales",
    "🌍 Cobertura Geográfica",
    "📚 Fuentes",
    "🔧 Mantenimiento"
])

st.sidebar.caption(f"{datetime.now().strftime('%d %b %Y')}")

# ==================== PANEL DE ACTUALIZACIÓN ====================
if seccion == "🏠 Panel de Actualización":
    st.title("🏠 Panel de Actualización")
    st.markdown("**Actualización de Datos del Observatorio Laboral**")

    existe_bd    = bd_existe()
    existe_tabla = existe_bd and tabla_existe()

    with st.expander("🦆 Gestión de base de datos (DuckDB)", expanded=True):
        col_estado, col_boton = st.columns([3, 1])

        if existe_bd and existe_tabla:
            con = _ddb.connect(DB_PATH, read_only=True)
            n_filas = con.execute(f"SELECT COUNT(*) FROM {TABLA}").fetchone()[0]
            fecha_db = con.execute(f"SELECT MAX(fecha_extraccion) FROM {TABLA}").fetchone()[0]
            con.close()

            with col_estado:
                st.caption(f"✅ BD lista · **{n_filas:,} registros** · Última extracción: **{fecha_db}**")
            
            with col_boton:
                if st.button("🔄 Actualizar DB", use_container_width=True):
                    ejecutar_con_progreso(funcion_actualizacion, "Actualizando base de datos...")

        else:
            with col_estado:
                msg = "❌ Base de datos no encontrada." if not existe_bd else "❌ Tabla no encontrada."
                st.caption(f"{msg} Presiona **Crear DB** para inicializarla.")
            
            with col_boton:
                if st.button("🟢 Crear DB", use_container_width=True):
                    ejecutar_con_progreso(funcion_creacion, "Creando base de datos...")

    
    

    #### ====================================== HABILIDADES =============================================
    # --- DuckDB: Habilidades O*NET ---
    
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
                if st.button("🔄 Actualizar Datos", use_container_width=True, key="btn_hab_update"):
                    def proceso(log_fn):
                        habilidades_pipeline(log_fn=log_fn)
                        st.cache_data.clear()
                    ejecutar_con_progreso(proceso, "Actualizando habilidades O*NET...")
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

# ==================== ANÁLISIS POR PROGRAMA ====================
elif seccion == "🔎 Análisis por Programa":
    st.title("🔎 Análisis por Programa Académico")
    analizar_por_programa()

# ==================== HABILIDADES ====================
elif seccion == "🎯 Habilidades":
    st.title("🎯 Habilidades y Conocimientos")
    mostrar_habilidades()

# ==================== TENDENCIAS ====================
elif seccion == "📈 Tendencias e Insights":
    st.title("📈 Tendencias e Insights Estratégicos")
    mostrar_tendencias_e_insights()

# ==================== ALERTAS ====================
elif seccion == "🚨 Alertas":
    st.title("🚨 Alertas Estratégicas")
    st.error("**Alto Riesgo:** Derecho (-4% crecimiento)")
    st.warning("**Moderado:** Administración necesita más analítica y IA")
    st.success("**Oportunidad:** Marketing Digital (+22% crecimiento)")

# ==================== VARIACIONES ====================
elif seccion == "💰 Variaciones Salariales":
    st.title("💰 Variaciones Salariales")
    mostrar_variaciones_salariales()

# ==================== COBERTURA ====================
elif seccion == "🌍 Cobertura Geográfica":
    st.title("🌍 Cobertura Geográfica")
    st.info("**Local (Bogotá / Cundinamarca) | Nacional | Internacional**")

# ==================== FUENTES ====================
elif seccion == "📚 Fuentes":
    st.title("📚 Fuentes de Información")
    fuentes = ["Servicio Público de Empleo", "Ministerio del Trabajo", "Banco de la República",
               "Ocupacol", "LinkedIn", "World Economic Forum", "McKinsey"]
    for f in fuentes:
        st.success(f"✅ {f}")

# ==================== MANTENIMIENTO ====================
elif seccion == "🔧 Mantenimiento":
    st.title("🔧 Mantenimiento y Sostenibilidad")
    st.write("- Datos: Mensual / Trimestral según fuente")
    st.write("- Dashboard: Automático")
    st.write("- Auditoría: Mensual")

# ==================== HABILIDADES ====================
elif seccion == "🎯 Habilidades":
    st.title("🎯 Habilidades y Conocimientos")
    mostrar_habilidades()
# ==================== DATOS INTERNACIONALES ====================
elif seccion == "🌍 Datos Internacionales":
    st.title("🌍 Análisis Internacional - Adzuna")

    data = get_analisis_completo()

    if data is None:
        st.warning("⚠️ Sin datos cargados. Ve al **Panel de Actualización** y presiona '🔄 Actualizar DB' para habilitarlo.")
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

        st.dataframe(df_filtrado[["pais_nombre", "perfil", "vacantes"]],
                     use_container_width=True, hide_index=True)

st.caption("Observatorio Laboral - Alumni Sabana")