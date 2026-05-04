"""
Habilidades.py
==============
Módulo del Observatorio Laboral — Habilidades y Conocimientos O*NET.
(Solo visualización - la actualización se gestiona desde app.py)
"""

import requests
import zipfile
import io
import re
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.figure as mfig
import duckdb
import streamlit as st
from bs4 import BeautifulSoup


# ============================================================
# CONFIGURACIÓN
# ============================================================

DB_PATH   = "observatorio_laboral.duckdb"
TABLA_SK  = "skills"
TABLA_KN  = "knowledge"
TABLA_OCC = "ocupaciones"

PALETTE = {
    "bg":      "white",
    "panel":   "#f6f8fa",
    "accent1": "#1f77b4",
    "accent2": "#2ca02c",
    "accent3": "#d62728",
    "text":    "#1a1a2e",
    "muted":   "#444444",
}


# ============================================================
# PIPELINE DE DATOS (solo para uso interno desde app.py)
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
# FUNCIONES DE GRÁFICOS (retornan fig, no plt.show)
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


def _base_fig(title: str, figsize=(14, 7)) -> tuple:
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(PALETTE["bg"])
    ax.set_facecolor(PALETTE["panel"])
    ax.set_title(title, color=PALETTE["text"], fontsize=14, fontweight="bold", pad=14)
    ax.tick_params(colors=PALETTE["text"], labelsize=9)
    for spine in ax.spines.values():
        spine.set_edgecolor("#cccccc")
    ax.grid(axis="x", color="#dddddd", linewidth=0.6, linestyle="--")
    ax.set_axisbelow(True)
    return fig, ax


def fig_skills_top(df_skills: pd.DataFrame) -> mfig.Figure:
    agg     = _agregar(df_skills).head(20)
    fig, ax = _base_fig("Top 20 Skills más demandadas en O*NET", figsize=(14, 8))
    bars    = ax.barh(
        agg["Element Name"][::-1], agg["Promedio"][::-1],
        color=PALETTE["accent1"], edgecolor="none", height=0.65,
    )
    for bar in bars:
        ax.text(
            bar.get_width() + 0.05, bar.get_y() + bar.get_height() / 2,
            f"{bar.get_width():.2f}", va="center", ha="left",
            color=PALETTE["muted"], fontsize=8,
        )
    ax.set_xlabel("Promedio del Data Value", color=PALETTE["muted"], fontsize=10)
    ax.tick_params(axis="y", labelcolor=PALETTE["text"])
    plt.tight_layout()
    return fig


def fig_knowledge_top(df_knowledge: pd.DataFrame) -> mfig.Figure:
    agg     = _agregar(df_knowledge).head(20)
    fig, ax = _base_fig("Top 20 Áreas de Conocimiento más demandadas en O*NET", figsize=(14, 8))
    bars    = ax.barh(
        agg["Element Name"][::-1], agg["Promedio"][::-1],
        color=PALETTE["accent2"], edgecolor="none", height=0.65,
    )
    for bar in bars:
        ax.text(
            bar.get_width() + 0.05, bar.get_y() + bar.get_height() / 2,
            f"{bar.get_width():.2f}", va="center", ha="left",
            color=PALETTE["muted"], fontsize=8,
        )
    ax.set_xlabel("Promedio del Data Value", color=PALETTE["muted"], fontsize=10)
    ax.tick_params(axis="y", labelcolor=PALETTE["text"])
    plt.tight_layout()
    return fig


def fig_skills_dist(df_skills: pd.DataFrame) -> mfig.Figure:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor(PALETTE["bg"])
    fig.suptitle("Distribución de Skills por Escala O*NET", 
                 color=PALETTE["text"], fontsize=14, fontweight="bold")

    escalas = {
        "IM": ("Importancia (1–5)\n¿Qué tan importante es esta skill?", PALETTE["accent1"]),
        "LV": ("Nivel requerido (0–7)\n¿Qué nivel se necesita?",         PALETTE["accent1"]),
    }

    for ax, (scale_id, (descripcion, color)) in zip(axes, escalas.items()):
        vals = df_skills[df_skills["Scale ID"] == scale_id]["Data Value"].dropna()
        ax.set_facecolor(PALETTE["panel"])
        ax.hist(vals, bins=30, color=color, edgecolor=PALETTE["bg"], linewidth=0.4)
        ax.set_title(f"Scale ID = {scale_id}", color=PALETTE["text"], fontsize=11, fontweight="bold")
        ax.set_xlabel(descripcion, color=PALETTE["muted"], fontsize=9)
        ax.set_ylabel("Frecuencia",  color=PALETTE["muted"], fontsize=9)
        ax.tick_params(axis="both", labelcolor=PALETTE["muted"])
        ax.grid(axis="y", color="#dddddd", linewidth=0.5, linestyle="--")
        for spine in ax.spines.values():
            spine.set_edgecolor("#cccccc")

    plt.tight_layout()
    return fig


def fig_knowledge_dist(df_knowledge: pd.DataFrame) -> mfig.Figure:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor(PALETTE["bg"])
    fig.suptitle("Distribución de Knowledge por Escala O*NET",
                 color=PALETTE["text"], fontsize=14, fontweight="bold")

    escalas = {
        "IM": ("Importancia (1–5)\n¿Qué tan importante es esta área?", PALETTE["accent2"]),
        "LV": ("Nivel requerido (0–7)\n¿Qué nivel se necesita?",        PALETTE["accent2"]),
    }

    for ax, (scale_id, (descripcion, color)) in zip(axes, escalas.items()):
        vals = df_knowledge[df_knowledge["Scale ID"] == scale_id]["Data Value"].dropna()
        ax.set_facecolor(PALETTE["panel"])
        ax.hist(vals, bins=30, color=color, edgecolor=PALETTE["bg"], linewidth=0.4)
        ax.set_title(f"Scale ID = {scale_id}", color=PALETTE["text"], fontsize=11, fontweight="bold")
        ax.set_xlabel(descripcion, color=PALETTE["muted"], fontsize=9)
        ax.set_ylabel("Frecuencia",  color=PALETTE["muted"], fontsize=9)
        ax.tick_params(axis="both", labelcolor=PALETTE["muted"])
        ax.grid(axis="y", color="#dddddd", linewidth=0.5, linestyle="--")
        for spine in ax.spines.values():
            spine.set_edgecolor("#cccccc")

    plt.tight_layout()
    return fig


def fig_ocupaciones(df_occ: pd.DataFrame) -> mfig.Figure | None:
    if "O*NET-SOC Code" not in df_occ.columns:
        return None
    df             = df_occ.copy()
    df["Grupo"]    = df["O*NET-SOC Code"].astype(str).str[:2]
    conteo         = df["Grupo"].value_counts().head(20).reset_index()
    conteo.columns = ["Grupo SOC", "Cantidad"]
    fig, ax        = _base_fig("Top 20 Grupos Ocupacionales (por código SOC)", figsize=(12, 6))
    bars           = ax.bar(
        conteo["Grupo SOC"], conteo["Cantidad"],
        color=PALETTE["accent3"], edgecolor="none", width=0.6,
    )
    for bar in bars:
        ax.text(
            bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
            str(int(bar.get_height())), ha="center", va="bottom",
            color=PALETTE["muted"], fontsize=8,
        )
    ax.set_xlabel("Código de grupo SOC (2 dígitos)", color=PALETTE["muted"], fontsize=10)
    ax.set_ylabel("Nº de ocupaciones",               color=PALETTE["muted"], fontsize=10)
    ax.tick_params(axis="both", labelcolor=PALETTE["muted"])
    plt.tight_layout()
    return fig


def _tabla_soc_referencia() -> pd.DataFrame:
    """Tabla de referencia de los grupos ocupacionales SOC (2 dígitos)."""
    return pd.DataFrame([
        ("11", "Gerencia y Dirección",                         "CEOs, gerentes, administradores de empresas"),
        ("13", "Negocios y Finanzas",                          "Analistas financieros, contadores, auditores"),
        ("15", "Computación y Matemáticas",                    "Programadores, científicos de datos, ingenieros de software"),
        ("17", "Arquitectura e Ingeniería",                    "Ingenieros civiles, mecánicos, eléctricos, arquitectos"),
        ("19", "Ciencias Naturales y Sociales",                "Biólogos, químicos, economistas, psicólogos"),
        ("21", "Servicios Sociales y Comunitarios",            "Trabajadores sociales, consejeros, orientadores"),
        ("23", "Derecho y Jurídica",                           "Abogados, jueces, paralegales"),
        ("25", "Educación y Bibliotecología",                  "Docentes, profesores universitarios, bibliotecarios"),
        ("27", "Arte, Diseño y Medios",                        "Diseñadores gráficos, músicos, periodistas, actores"),
        ("29", "Salud — Profesionales",                        "Médicos, enfermeras, farmacéuticos, dentistas"),
        ("31", "Salud — Técnicos y Asistentes",                "Auxiliares de enfermería, técnicos de laboratorio"),
        ("33", "Seguridad y Protección",                       "Policías, bomberos, guardas de seguridad"),
        ("35", "Preparación y Servicio de Alimentos",          "Chefs, cocineros, meseros, bartenders"),
        ("37", "Mantenimiento de Edificios y Espacios",        "Conserjes, jardineros, personal de limpieza"),
        ("39", "Cuidado Personal y Servicios",                 "Estilistas, cuidadores, entrenadores personales"),
        ("41", "Ventas",                                       "Vendedores, representantes comerciales, agentes"),
        ("43", "Soporte Administrativo y de Oficina",          "Secretarias, recepcionistas, operadores de datos"),
        ("45", "Agricultura, Pesca y Forestal",                "Agricultores, pescadores, trabajadores forestales"),
        ("47", "Construcción y Extracción",                    "Albañiles, electricistas, mineros, soldadores"),
        ("49", "Instalación y Reparación",                     "Técnicos de mantenimiento, mecánicos, electricistas"),
        ("51", "Producción e Industria",                       "Operadores de maquinaria, ensambladores, inspectores de calidad"),
        ("53", "Transporte y Logística",                       "Conductores, pilotos, operadores de grúas, despachadores"),
        ("55", "Fuerzas Militares",                            "Personal militar de todas las ramas"),
    ], columns=["Código SOC", "Grupo Ocupacional", "Ejemplos de ocupaciones"])


def fig_scatter_skills_vs_knowledge(
    df_skills: pd.DataFrame, df_knowledge: pd.DataFrame
) -> mfig.Figure | None:
    sk_agg = _agregar(df_skills).rename(columns={"Promedio": "Skill"})
    kn_agg = _agregar(df_knowledge).rename(columns={"Promedio": "Knowledge"})
    merged = sk_agg.merge(kn_agg, on="Element Name", how="inner")
    if merged.empty:
        return None
    fig, ax = _base_fig("Skills vs Knowledge — Elementos en común", figsize=(10, 7))
    sc = ax.scatter(
        merged["Skill"], merged["Knowledge"],
        c=merged["Skill"] + merged["Knowledge"],
        cmap="cool", s=60, alpha=0.8, edgecolors="none",
    )
    cbar = fig.colorbar(sc, ax=ax)
    cbar.ax.yaxis.set_tick_params(color=PALETTE["muted"])
    cbar.outline.set_edgecolor(PALETTE["panel"])
    plt.setp(plt.getp(cbar.ax.axes, "yticklabels"), color=PALETTE["muted"])
    for _, row in merged.nlargest(5, "Skill").iterrows():
        ax.annotate(
            row["Element Name"], (row["Skill"], row["Knowledge"]),
            textcoords="offset points", xytext=(6, 4),
            color=PALETTE["text"], fontsize=7,
        )
    ax.set_xlabel("Promedio Skill",     color=PALETTE["muted"], fontsize=10)
    ax.set_ylabel("Promedio Knowledge", color=PALETTE["muted"], fontsize=10)
    ax.tick_params(axis="both", labelcolor=PALETTE["muted"])
    plt.tight_layout()
    return fig


# ============================================================
# SECCIÓN STREAMLIT PRINCIPAL (SOLO VISUALIZACIÓN)
# ============================================================

def mostrar_habilidades() -> None:
    """Muestra solo la visualización de habilidades sin controles de actualización"""
    
    st.markdown("Análisis de habilidades y áreas de conocimiento más demandadas según la base de datos **O*NET** (EE.UU.).")
    
    # Mostrar estado de los datos (solo informativo, sin botones)
    if bd_tiene_datos():
        con = duckdb.connect(DB_PATH, read_only=True)
        n_sk = con.execute(f"SELECT COUNT(*) FROM {TABLA_SK}").fetchone()[0]
        n_kn = con.execute(f"SELECT COUNT(*) FROM {TABLA_KN}").fetchone()[0]
        n_occ = con.execute(f"SELECT COUNT(*) FROM {TABLA_OCC}").fetchone()[0]
        con.close()
        
        st.info(f"📊 Datos O*NET cargados · Skills: **{n_sk:,}** · Knowledge: **{n_kn:,}** · Ocupaciones: **{n_occ:,}**")
        st.caption("💡 Para actualizar estos datos, ve al **Panel de Actualización** en el menú principal.")
    else:
        st.warning("⚠️ No hay datos de O*NET cargados. Ve al **Panel de Actualización** y presiona 'Crear Habilidades' para inicializarlos.")
        return

    df_sk, df_kn, df_occ = _cargar_desde_db()

    # ── Tabs de visualización ─────────────────────────────────
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🔵 Top Skills",
        "🟢 Top Knowledge",
        "📊 Dist. Skills",
        "📊 Dist. Knowledge",
        "🏢 Ocupaciones",
        "🔀 Skills vs Knowledge",
    ])

    with tab1:
        st.subheader("Top 20 Skills más demandadas")
        fig = fig_skills_top(df_sk)
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

    with tab2:
        st.subheader("Top 20 Áreas de Conocimiento más demandadas")
        fig = fig_knowledge_top(df_kn)
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

    with tab3:
        st.subheader("Distribución de valores — Skills")
        fig = fig_skills_dist(df_sk)
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

    with tab4:
        st.subheader("Distribución de valores — Knowledge")
        fig = fig_knowledge_dist(df_kn)
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

    with tab5:
        st.subheader("Grupos Ocupacionales (código SOC)")
        fig = fig_ocupaciones(df_occ)
        if fig:
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)
        else:
            st.warning("No se encontró la columna 'O*NET-SOC Code' en los datos.")

        st.divider()
        st.markdown("#### 📋 Referencia de Códigos SOC")
        st.dataframe(
            _tabla_soc_referencia(),
            use_container_width=True,
            hide_index=True,
        )

    with tab6:
        st.subheader("Skills vs Knowledge — correlación de promedios")
        fig = fig_scatter_skills_vs_knowledge(df_sk, df_kn)
        if fig:
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)
        else:
            st.warning("Sin elementos comunes entre Skills y Knowledge.")