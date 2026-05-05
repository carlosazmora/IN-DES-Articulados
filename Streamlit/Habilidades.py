"""
Habilidades.py
==============
Módulo del Observatorio Laboral — Habilidades y Conocimientos O*NET.
"""

import requests
import zipfile
import io
import re
import os
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import duckdb
import streamlit as st
from bs4 import BeautifulSoup
import numpy as np


# ============================================================
# CONFIGURACIÓN
# ============================================================

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "habilidades_onet.duckdb")
TABLA_SK  = "skills"
TABLA_KN  = "knowledge"
TABLA_OCC = "ocupaciones"


# ============================================================
# PIPELINE DE DATOS
# ============================================================

def pipeline_datos(db_path: str = DB_PATH, log_fn=None) -> None:
    def log(msg: str):
        if log_fn:
            log_fn(msg)

    log("🔍 Buscando versión más reciente de O*NET...")
    url = _get_latest_url(log)

    log("⬇️  Descargando ZIP en memoria...")
    archivos = _descargar_en_memoria(url, log)

    log("🔧 Procesando DataFrames...")
    df_occ, df_sk, df_kn = _cargar_dataframes(archivos, log)

    log(f"💾 Guardando en DuckDB: '{db_path}'")
    _guardar_en_duckdb(df_occ, df_sk, df_kn, db_path, log)

    log("✅ Pipeline completado.")


def bd_tiene_datos(db_path: str = DB_PATH) -> bool:
    if not os.path.exists(db_path):
        return False
    try:
        con = duckdb.connect(db_path, read_only=True)
        tablas = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
        con.close()
        return {TABLA_SK, TABLA_KN, TABLA_OCC}.issubset(tablas)
    except Exception:
        return False


# Helpers internos
def _get_latest_url(log=None) -> str:
    BASE = "https://www.onetcenter.org"
    headers = {"User-Agent": "Mozilla/5.0"}
    page = requests.get(f"{BASE}/database.html", headers=headers, timeout=30)
    page.raise_for_status()
    soup = BeautifulSoup(page.content, "html.parser")
    candidates = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        match = re.search(r"db_(\d+)_(\d+)_text\.zip", href)
        if match:
            major = int(match.group(1))
            minor = int(match.group(2))
            full_url = href if href.startswith("http") else f"{BASE}{href}"
            candidates.append(((major, minor), full_url))
    candidates.sort(key=lambda x: x[0], reverse=True)
    _, url = candidates[0]
    if log:
        log(f"   Versión encontrada: {candidates[0][0][0]}.{candidates[0][0][1]}")
    return url


def _descargar_en_memoria(url: str, log=None) -> dict:
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=120)
    r.raise_for_status()
    archivos = {}
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        for nombre in z.namelist():
            archivos[nombre.lower()] = z.read(nombre)
    if log:
        log(f"   {len(archivos)} archivos cargados en memoria.")
    return archivos


def _buscar_archivo(archivos: dict, nombre_exacto: str):
    clave = nombre_exacto.lower()
    for ruta, contenido in archivos.items():
        if os.path.basename(ruta) == clave:
            return contenido
    return None


def _leer_tsv(archivos: dict, nombre_exacto: str) -> pd.DataFrame:
    contenido = _buscar_archivo(archivos, nombre_exacto)
    if contenido is None:
        raise FileNotFoundError(f"No se encontró '{nombre_exacto}'")
    return pd.read_csv(io.BytesIO(contenido), sep="\t", encoding="latin1")


def _detectar_col_valor(df: pd.DataFrame) -> str:
    for candidato in ["Data Value", "Value", "data value", "Score"]:
        if candidato in df.columns:
            return candidato
    for col in df.columns:
        if "value" in col.lower() or "score" in col.lower():
            return col
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            return col
    raise ValueError("Sin columna numérica")


def _cargar_dataframes(archivos: dict, log=None):
    df_occ = _leer_tsv(archivos, "occupation data.txt")
    df_sk  = _leer_tsv(archivos, "skills.txt")
    df_kn  = _leer_tsv(archivos, "knowledge.txt")

    for df, nombre in [(df_sk, "Skills"), (df_kn, "Knowledge")]:
        col = _detectar_col_valor(df)
        if col != "Data Value":
            df.rename(columns={col: "Data Value"}, inplace=True)
        df["Data Value"] = pd.to_numeric(df["Data Value"], errors="coerce").round(2)

    if log:
        log(f"   Ocupaciones : {df_occ.shape[0]:,} filas")
        log(f"   Skills      : {df_sk.shape[0]:,} filas")
        log(f"   Knowledge   : {df_kn.shape[0]:,} filas")
    return df_occ, df_sk, df_kn


def _guardar_en_duckdb(df_occ, df_sk, df_kn, db_path: str, log=None):
    con = duckdb.connect(db_path)
    for nombre_tabla, df in [(TABLA_OCC, df_occ), (TABLA_SK, df_sk), (TABLA_KN, df_kn)]:
        con.execute(f"CREATE OR REPLACE TABLE {nombre_tabla} AS SELECT * FROM df")
        n = con.execute(f"SELECT COUNT(*) FROM {nombre_tabla}").fetchone()[0]
        if log:
            log(f"   '{nombre_tabla}' → {n:,} filas guardadas")
    con.close()


# ============================================================
# CARGA DESDE DUCKDB
# ============================================================

@st.cache_data(show_spinner=False)
def _cargar_desde_db(db_path: str = DB_PATH):
    con = duckdb.connect(db_path, read_only=True)
    df_sk  = con.execute(f"SELECT * FROM {TABLA_SK}").df()
    df_kn  = con.execute(f"SELECT * FROM {TABLA_KN}").df()
    df_occ = con.execute(f"SELECT * FROM {TABLA_OCC}").df()
    con.close()
    return df_sk, df_kn, df_occ


# ============================================================
# ESTILO VISUAL
# ============================================================

def _agregar(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("Element Name")["Data Value"]
        .mean()
        .round(2)
        .sort_values(ascending=False)
        .reset_index()
        .rename(columns={"Data Value": "Promedio"})
    )


_C_SKILL  = "#1e40af"
_C_KNOW   = "#166534"
_FONT     = "Inter, Segoe UI, sans-serif"

def _base_layout(title: str = None, height: int = 520, **kwargs) -> dict:
    base = dict(
        paper_bgcolor="#f8fafc",
        plot_bgcolor="#f8fafc",
        font=dict(family=_FONT, color="#111827", size=13),
        title=dict(
            text=title,
            font=dict(size=20, color="#111827", family=_FONT),
            x=0.5,
            xanchor="center",
            y=0.96
        ),
        margin=dict(l=25, r=25, t=70, b=60),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=13, color="#111827")
        )
    )
    base.update(kwargs)
    return base


# ============================================================
# GRÁFICOS
# ============================================================

def fig_skills_top(df_skills: pd.DataFrame) -> go.Figure:
    agg = _agregar(df_skills).head(20)
    fig = go.Figure(go.Bar(
        x=agg["Promedio"], y=agg["Element Name"], orientation="h",
        marker=dict(color="#3b82f6", line=dict(color="white", width=1), cornerradius=6),
        text=[f"{v:.2f}" for v in agg["Promedio"]],
        textposition="inside", insidetextanchor="end", textfont=dict(size=13, color="white"),
        hovertemplate="<b>%{y}</b><br>Promedio: <b>%{x:.2f}</b><extra></extra>",
    ))
    fig.update_layout(**_base_layout("Top 20 Skills más demandadas según O*NET", height=650))
    fig.update_xaxes(title="Promedio O*NET (0-5)", title_font=dict(size=14, color="#1f2937"), showgrid=True, gridcolor="#e2e8f0")
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=13.5, color="#1f2937"))
    return fig


def fig_knowledge_top(df_knowledge: pd.DataFrame) -> go.Figure:
    agg = _agregar(df_knowledge).head(20)
    fig = go.Figure(go.Bar(
        x=agg["Promedio"], y=agg["Element Name"], orientation="h",
        marker=dict(color="#10b981", line=dict(color="white", width=1), cornerradius=6),
        text=[f"{v:.2f}" for v in agg["Promedio"]],
        textposition="inside", insidetextanchor="end", textfont=dict(size=13, color="white"),
        hovertemplate="<b>%{y}</b><br>Promedio: <b>%{x:.2f}</b><extra></extra>",
    ))
    fig.update_layout(**_base_layout("Top 20 Áreas de Conocimiento más demandadas", height=650))
    fig.update_xaxes(title="Promedio O*NET (0-5)", title_font=dict(size=14, color="#1f2937"), showgrid=True, gridcolor="#e2e8f0")
    fig.update_yaxes(autorange="reversed", tickfont=dict(size=13.5, color="#1f2937"))
    return fig


def fig_importancia_skills(df_skills: pd.DataFrame) -> go.Figure:
    """Gráfico específico para distribución de importancia de Skills"""
    vals_sk = df_skills[df_skills["Scale ID"] == "IM"]["Data Value"].dropna()
    
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=vals_sk, nbinsx=25, name="Skills", 
        marker_color=_C_SKILL, opacity=0.85, 
        hovertemplate="Importancia: %{x}<br>Frecuencia: %{y}<extra></extra>"
    ))
    
    media = vals_sk.mean()
    fig.add_vline(x=media, line_width=2.5, line_dash="dash", line_color=_C_SKILL,
                  annotation_text=f"Media: {media:.2f}", annotation_position="top")
    
    fig.update_layout(**_base_layout("Distribución de Importancia — Skills", height=480))
    fig.update_xaxes(title="Nivel de Importancia (1-5)", title_font=dict(size=14, color="#1f2937"), 
                     showgrid=True, gridcolor="#e2e8f0", range=[0.5, 5.5])
    fig.update_yaxes(title="Frecuencia", title_font=dict(size=14, color="#1f2937"), 
                     showgrid=True, gridcolor="#e2e8f0")
    return fig


def fig_importancia_knowledge(df_knowledge: pd.DataFrame) -> go.Figure:
    """Gráfico específico para distribución de importancia de Knowledge"""
    vals_kn = df_knowledge[df_knowledge["Scale ID"] == "IM"]["Data Value"].dropna()
    
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=vals_kn, nbinsx=25, name="Knowledge", 
        marker_color=_C_KNOW, opacity=0.85,
        hovertemplate="Importancia: %{x}<br>Frecuencia: %{y}<extra></extra>"
    ))
    
    media = vals_kn.mean()
    fig.add_vline(x=media, line_width=2.5, line_dash="dash", line_color=_C_KNOW,
                  annotation_text=f"Media: {media:.2f}", annotation_position="top")
    
    fig.update_layout(**_base_layout("Distribución de Importancia — Knowledge", height=480))
    fig.update_xaxes(title="Nivel de Importancia (1-5)", title_font=dict(size=14, color="#1f2937"),
                     showgrid=True, gridcolor="#e2e8f0", range=[0.5, 5.5])
    fig.update_yaxes(title="Frecuencia", title_font=dict(size=14, color="#1f2937"), 
                     showgrid=True, gridcolor="#e2e8f0")
    return fig


def fig_ocupaciones(df_occ: pd.DataFrame) -> go.Figure | None:
    if "O*NET-SOC Code" not in df_occ.columns:
        return None
    df = df_occ.copy()
    df["Grupo"] = df["O*NET-SOC Code"].astype(str).str[:2]
    conteo = df["Grupo"].value_counts().head(20).reset_index()
    conteo.columns = ["Grupo SOC", "Cantidad"]
    conteo = conteo.sort_values("Cantidad", ascending=True)

    fig = go.Figure(go.Bar(
        x=conteo["Cantidad"], y=conteo["Grupo SOC"], orientation="h",
        marker=dict(color="#8b5cf6", line=dict(color="white", width=1), cornerradius=6),
        text=conteo["Cantidad"].astype(str),
        textposition="inside", insidetextanchor="end",
    ))
    fig.update_layout(**_base_layout("Distribución de Ocupaciones por Grupo SOC", height=580))
    fig.update_xaxes(title="Cantidad de Ocupaciones", title_font=dict(size=14, color="#1f2937"), showgrid=True, gridcolor="#e2e8f0")
    fig.update_yaxes(tickfont=dict(size=13.5, color="#1f2937"), showgrid=False)
    return fig


def fig_scatter_skills_vs_knowledge(df_skills: pd.DataFrame, df_knowledge: pd.DataFrame) -> go.Figure | None:
    sk_agg = _agregar(df_skills).head(30).reset_index(drop=True)
    kn_agg = _agregar(df_knowledge).head(30).reset_index(drop=True)
    if sk_agg.empty and kn_agg.empty:
        return None

    fig = go.Figure()
    for df_agg, name, color, symbol in [(sk_agg, "Skills", _C_SKILL, "circle"), (kn_agg, "Knowledge", _C_KNOW, "diamond")]:
        rankings = list(range(1, len(df_agg) + 1))
        fig.add_trace(go.Scatter(
            x=rankings, y=df_agg["Promedio"], mode="markers",
            name=name, marker=dict(color=color, size=12, symbol=symbol, line=dict(color="white", width=1.5)),
            text=df_agg["Element Name"],
            hovertemplate="<b>%{text}</b><br>Ranking: %{x}°<br>Promedio: <b>%{y:.2f}</b><extra></extra>",
        ))

    fig.update_layout(**_base_layout("Comparación Skills vs Knowledge (Top 30)", height=520))
    fig.update_xaxes(title="Ranking (1 = más importante)", title_font=dict(size=14, color="#1f2937"), tickfont=dict(size=13, color="#1f2937"), showgrid=True, gridcolor="#e2e8f0", dtick=5)
    fig.update_yaxes(title="Promedio O*NET", title_font=dict(size=14, color="#1f2937"), tickfont=dict(size=13, color="#1f2937"), showgrid=True, gridcolor="#e2e8f0")
    return fig


def _tabla_soc_referencia() -> pd.DataFrame:
    return pd.DataFrame([
        ("11", "Gerencia y Dirección", "CEOs, gerentes, administradores"),
        ("13", "Negocios y Finanzas", "Analistas, contadores, auditores"),
        ("15", "Computación y Matemáticas", "Programadores, científicos de datos"),
        ("17", "Arquitectura e Ingeniería", "Ingenieros de todo tipo"),
        ("19", "Ciencias Naturales y Sociales", "Biólogos, economistas, psicólogos"),
        ("29", "Salud — Profesionales", "Médicos, enfermeras, farmacéuticos"),
        ("41", "Ventas", "Vendedores y representantes comerciales"),
        ("47", "Construcción", "Albañiles, electricistas, soldadores"),
    ], columns=["Código SOC", "Grupo Ocupacional", "Ejemplos"])


# ============================================================
# SECCIÓN STREAMLIT CON KEYS ÚNICOS
# ============================================================

def mostrar_habilidades() -> None:
    st.markdown("### Análisis de Habilidades y Conocimientos O*NET")
    st.markdown("Datos actualizados de la base de datos **O\*NET** de EE.UU.")
    
    if bd_tiene_datos():
        con = duckdb.connect(DB_PATH, read_only=True)
        n_sk = con.execute(f"SELECT COUNT(*) FROM {TABLA_SK}").fetchone()[0]
        n_kn = con.execute(f"SELECT COUNT(*) FROM {TABLA_KN}").fetchone()[0]
        n_occ = con.execute(f"SELECT COUNT(*) FROM {TABLA_OCC}").fetchone()[0]
        con.close()
        st.success(f"✅ Datos cargados: **{n_sk:,}** skills • **{n_kn:,}** knowledge • **{n_occ:,}** ocupaciones")
    else:
        st.error("❌ No hay datos cargados. Ve al Panel de Actualización.")
        return

    df_sk, df_kn, df_occ = _cargar_desde_db()

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🔵 Top Skills", 
        "🟢 Top Knowledge", 
        "📊 Importancia Skills", 
        "📊 Importancia Knowledge",
        "🏢 Ocupaciones", 
        "🔀 Skills vs Knowledge"
    ])

    with tab1:
        st.plotly_chart(fig_skills_top(df_sk), use_container_width=True, key="fig_skills_top")
        st.caption("**Top 20 Habilidades más demandadas.** Muestra las habilidades que tienen mayor puntaje promedio de importancia en miles de ocupaciones analizadas por O*NET.")

    with tab2:
        st.plotly_chart(fig_knowledge_top(df_kn), use_container_width=True, key="fig_knowledge_top")
        st.caption("**Top 20 Áreas de Conocimiento más demandadas.** Muestra los conocimientos teóricos más valorados en el mercado laboral estadounidense.")

    with tab3:
        st.plotly_chart(fig_importancia_skills(df_sk), use_container_width=True, key="fig_importancia_skills")
        st.caption("**Distribución de la importancia de las Skills.** Muestra qué tan importantes se consideran las habilidades en general (escala 1 a 5). La línea punteada muestra el valor promedio.")

    with tab4:
        st.plotly_chart(fig_importancia_knowledge(df_kn), use_container_width=True, key="fig_importancia_knowledge")
        st.caption("**Distribución de la importancia de los Knowledge.** Muestra qué tan importantes se consideran los conocimientos teóricos (escala 1 a 5). La línea punteada muestra el valor promedio.")

    with tab5:
        fig_occ = fig_ocupaciones(df_occ)
        if fig_occ:
            st.plotly_chart(fig_occ, use_container_width=True, key="fig_ocupaciones")
        st.caption("**Distribución de ocupaciones por gran grupo.** Muestra cuántas ocupaciones diferentes existen en cada categoría principal según el sistema SOC.")
        st.divider()
        st.subheader("📋 Referencia de Grupos Ocupacionales (SOC)")
        st.dataframe(_tabla_soc_referencia(), use_container_width=True, hide_index=True)

    with tab6:
        fig_scatter = fig_scatter_skills_vs_knowledge(df_sk, df_kn)
        if fig_scatter:
            st.plotly_chart(fig_scatter, use_container_width=True, key="fig_scatter_skills_knowledge")
            st.caption("**Comparación entre Skills y Knowledge.** Cada punto representa una habilidad o conocimiento. El ranking 1 es el más importante.")
        else:
            st.warning("No hay suficientes datos para esta gráfica.")