import sys
import os
import streamlit as st
import plotly.express as px
from datetime import datetime
from DatosInternacionales import (
    get_analisis_completo, 
    tabla_existe, bd_existe,
    funcion_creacion, funcion_actualizacion, DB_PATH, TABLA
)
from AnalisisPorPrograma import analizar_por_programa
from VariacionesSalariales import mostrar_variaciones_salariales
from Tendencias import mostrar_tendencias_e_insights
from Habilidades import (
    mostrar_habilidades,
    pipeline_datos as habilidades_pipeline,
    bd_tiene_datos,
    DB_PATH as HAB_DB_PATH,
    TABLA_SK, TABLA_KN, TABLA_OCC
)
from Proyecciones import (
    cargar_datos as cargar_proyecciones,
    grafico_mayor_proyeccion, grafico_puestos_demandados,
    grafico_tendencias_sector, grafico_programas_riesgo,
    grafico_salarios_sector, grafico_salarios_educacion,
    grafico_scatter_crecimiento,
)
from Colombia import (
    mostrar_colombia,
    pipeline_datos as colombia_pipeline,
    bd_tiene_datos as colombia_tiene_datos,
    DB_PATH as CO_DB_PATH,
    TABLA_CO,
)

import duckdb as _ddb2
import duckdb as _ddb

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

st.set_page_config(page_title="ObserLABOR - Alumni Sabana", layout="wide", page_icon="📊")

# ==================== FUNCIÓN DE PROGRESO ====================
def ejecutar_con_progreso(funcion_proceso, mensaje_inicial: str):
    """Ejecuta mostrando porcentaje real basado en logs tipo [x/total]"""
    import re
    status_text = st.empty()
    log_lines = []
    total = None

    def log_callback(mensaje: str):
        nonlocal total
        log_lines.append(mensaje)
        match = re.search(r"\[(\d+)/(\d+)\]", mensaje)
        if match:
            actual = int(match.group(1))
            total  = int(match.group(2))
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

# ==================== SIDEBAR ====================
st.sidebar.title("📊 ObserLABOR - Alumni Sabana")

seccion = st.sidebar.radio("Navegación", [
    "🏠 Panel de Actualización",
    "🔎 Análisis por Programa",
    "🌺 Datos Nacionales",
    "🌍 Datos Internacionales",
    "🎯 Habilidades",
    "📈 Tendencias e Insights",
    "💰 Variaciones Salariales",
    "📊 Predicciones"
])

st.sidebar.caption(f"{datetime.now().strftime('%d %b %Y')}")

# ==================== PANEL DE ACTUALIZACIÓN ====================
if seccion == "🏠 Panel de Actualización":
    st.title("🏠 Panel de Actualización")
    st.markdown("**Actualización de Datos del Observatorio Laboral**")

    # --- DuckDB: Adzuna Internacional ---
    existe_bd    = bd_existe()
    existe_tabla = existe_bd and tabla_existe()

    with st.expander("🔎 Gestión de base de datos Adzuna", expanded=True):
        col_estado, col_boton = st.columns([3, 1])

        if existe_bd and existe_tabla:
            con = _ddb.connect(DB_PATH, read_only=True)
            n_filas  = con.execute(f"SELECT COUNT(*) FROM {TABLA}").fetchone()[0]
            fecha_db = con.execute(f"SELECT MAX(fecha_extraccion) FROM {TABLA}").fetchone()[0]
            con.close()
            with col_estado:
                st.caption(f"✅ DB lista · **{n_filas:,} registros** · Última extracción: **{fecha_db}**")
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

    # --- DuckDB: Habilidades O*NET ---
    _hab_lista = bd_tiene_datos()

    with st.expander("🎯 Gestión de datos de Habilidades O*NET", expanded=True):
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
                st.caption("❌ Tablas de habilidades no encontradas. Presiona **Consultar Habilidades** para inicializarlas.")
            with col_boton:
                if st.button("🟢 Consultar Habilidades", use_container_width=True, key="btn_hab_create"):
                    def proceso(log_fn):
                        habilidades_pipeline(log_fn=log_fn)
                        st.cache_data.clear()
                    ejecutar_con_progreso(proceso, "Obteniendo habilidades O*NET...")

    # --- DuckDB: Colombia LinkedIn ---
    _co_lista = colombia_tiene_datos()

    with st.expander("🌺 Gestión de datos Colombia — LinkedIn", expanded=True):
        col_estado, col_boton = st.columns([3, 1])

        if _co_lista:
            _con_co   = _ddb2.connect(CO_DB_PATH, read_only=True)
            _n_co     = _con_co.execute(f"SELECT COUNT(*) FROM {TABLA_CO}").fetchone()[0]
            _fecha_co = _con_co.execute(f"SELECT MAX(fecha_extraccion) FROM {TABLA_CO}").fetchone()[0]
            _con_co.close()
            with col_estado:
                st.caption(f"✅ Colombia lista · **{_n_co:,} vacantes** · Última extracción: **{_fecha_co}**")
            with col_boton:
                if st.button("🔄 Actualizar LinkedIn", use_container_width=True, key="btn_co_update"):
                    def proceso(log_fn):
                        colombia_pipeline(log_fn=log_fn)
                        st.cache_data.clear()
                    ejecutar_con_progreso(proceso, "Scrapeando LinkedIn Colombia...")
        else:
            with col_estado:
                st.caption("❌ Sin datos de Colombia. Presiona **Consultar LinkedIn** para inicializarlos.")
            with col_boton:
                if st.button("🟢 Consultar LinkedIn", use_container_width=True, key="btn_co_create"):
                    def proceso(log_fn):
                        colombia_pipeline(log_fn=log_fn)
                        st.cache_data.clear()
                    ejecutar_con_progreso(proceso, "Obteniendo vacantes LinkedIn Colombia...")

# ==================== DATOS NACIONALES ====================
elif seccion == "🌺 Datos Nacionales":
    st.title("🌺 Vacantes en Colombia — LinkedIn")
    mostrar_colombia()

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

# ==================== VARIACIONES ====================
elif seccion == "💰 Variaciones Salariales":
    st.title("💰 Variaciones Salariales")
    mostrar_variaciones_salariales()

# ==================== PROYECCIONES ====================
elif seccion == "📊 Predicciones":
    st.title("📊 Predicciones Ocupacionales — BLS 2024–2034")

    archivo = st.file_uploader(
        "Sube el archivo de predicciones (.xlsx)",
        type=["xlsx"],
        accept_multiple_files=False,  # ← EXPLÍCITAMENTE: solo un archivo
        help="Usa el archivo occupation.xlsx del BLS Employment Projections Program.",
    )

    if archivo is None:
        st.info("⬆️ Sube el archivo Excel para comenzar el análisis.")

        st.caption(
    """
        Guía de Navegación: Proyecciones Ocupacionales BLS

        1.	Acceso inicial: Abra en su navegador el siguiente link: https://www.bls.gov/emp/tables.htm 
        2.	Categoría de Ocupaciones: En la nueva pantalla, verás una lista organizada por categorías. Ubícate en el primer ítem titulado "Occupations" (Ocupaciones).
        3.	Descarga Final: Dentro de esa sección, busca el enlace directo que dice: "All occupational tables in a single file (XLSX)" y suba el excel “occupations” a la página.
        
        En caso de que no le sirva el link anterior, haga lo siguiente: 
        
        1.	Acceso Inicial: Abre tu navegador y dirígete a la página principal del Bureau of Labor Statistics (bls.gov) https://www.bls.gov/ .
        2.	Menú Principal: En la barra de navegación superior, haz clic en la pestaña "Subjects" (Temas).
        3.	Selección de Área: Dentro del menú desplegable, busca “Subjects”, en el menú desplegable busque "Employment" (Empleo) y selecciona la opción "Employment Projections".
        4.	Sección de Datos: Una vez en la página de predicciones, busca en el menú "EP Data" (Datos de Predicciones de Empleo) y posteriormente seleccione “Tables” (tablas).
        5.	Categoría de Ocupaciones: En la nueva pantalla, verás una lista organizada por categorías. Ubícate en el primer ítem titulado "Occupations" (Ocupaciones).
        6.	Descarga Final: Dentro de esa sección, busca el enlace directo que dice: "All occupational tables in a single file (XLSX)" y suba el excel “occupations” a la página.
    """
               )
    else:
        with st.spinner("Cargando datos..."):
            df11, df12, df13, df14, df15, df16 = cargar_proyecciones(archivo)
        st.success(f"✅ {len(df11)} sectores · {len(df12):,} ocupaciones cargadas")
        st.divider()

        st.subheader("¿Qué ocupaciones tienen mayor proyección?")
        st.caption("Top 20 con mayor crecimiento porcentual proyectado al 2034.")
        grafico_mayor_proyeccion(df13)
        st.divider()

        st.subheader("¿Qué puestos son los más demandados?")
        st.caption("Top 20 con mayor número absoluto de empleos nuevos al 2034.")
        grafico_puestos_demandados(df14)
        st.divider()

        st.subheader("¿Cómo está cambiando la empleabilidad? — Tendencias por sector")
        st.caption("Variación porcentual del empleo 2024–2034 por grupo ocupacional.")
        grafico_tendencias_sector(df11)
        st.divider()

        st.subheader("Programas en riesgo — Ocupaciones en declive")
        st.caption("Izquierda: declive más rápido (%). Derecha: mayor pérdida absoluta de empleos.")
        grafico_programas_riesgo(df15, df16)
        st.divider()

        st.subheader("Variaciones salariales por sector")
        st.caption("Salario mediano anual 2024 (USD) por grupo ocupacional.")
        grafico_salarios_sector(df11)
        st.divider()

        st.subheader("Variaciones salariales por nivel educativo requerido")
        st.caption("Salario mediano por nivel mínimo de educación requerida.")
        grafico_salarios_educacion(df12)
        st.divider()

        st.subheader("Sectores con mayor crecimiento — Vacantes vs. Crecimiento %")
        st.caption("Cada punto es un sector. Tamaño = empleo total 2024.")
        grafico_scatter_crecimiento(df11, df12)

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

st.caption("ObserLABOR - Alumni Sabana")