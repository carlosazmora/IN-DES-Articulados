"""
Colombia.py
===========
Módulo del Observatorio Laboral — Vacantes LinkedIn Colombia.

Flujo de datos:
  jobspy.scrape_jobs()  →  DataFrame en memoria  →  DuckDB (tabla 'colombia_vacantes')

La tabla se guarda directamente desde el DataFrame, sin parquet.
La actualización se gestiona desde app.py (Panel de Actualización).
"""

import re
import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.figure as mfig
import matplotlib.patches as mpatches
import duckdb
import streamlit as st
from collections import Counter
from datetime import datetime

# ============================================================
# CONFIGURACIÓN
# ============================================================

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "observatorio_laboral.duckdb")
TABLA_CO  = "colombia_vacantes"

PERFILES = [
    # TI & Datos
    "data",
    "developer",
    # Ingeniería
    "ingeniero",
    "industrial",
    "ingeniero mecanico",
    # Derecho
    "derecho",
    # Salud
    "medicina",
    "enfermeria",
    "psicologia",
    # Negocio & Gestión
    "business analyst",
    "project manager",
    # Marketing
    "marketing",
    # Finanzas
    "finantial",
]

PERFILES_ES = {
    "data":             "Datos / BI",
    "developer":        "Developer",
    "ingeniero":        "Ingeniero",
    "industrial":       "Ing. Industrial",
    "ingeniero mecanico": "Ing. Mecánico",
    "derecho":          "Derecho",
    "medicina":         "Medicina",
    "enfermeria":       "Enfermería",
    "psicologia":       "Psicología",
    "business analyst": "Analista de Negocio",
    "project manager":  "Gerente de Proyectos",
    "marketing":        "Marketing",
    "finantial":        "Finanzas",
}

CATEGORIA_PERFIL = {
    "data":             "TI & Datos",
    "developer":        "TI & Datos",
    "ingeniero":        "Ingeniería",
    "industrial":       "Ingeniería",
    "ingeniero mecanico": "Ingeniería",
    "derecho":          "Derecho",
    "medicina":         "Salud",
    "enfermeria":       "Salud",
    "psicologia":       "Salud",
    "business analyst": "Negocio & Gestión",
    "project manager":  "Negocio & Gestión",
    "marketing":        "Marketing",
    "finantial":        "Finanzas",
}

PALETTE = {
    "bg":      "white",
    "panel":   "#f6f8fa",
    "azul":    "#003F87",
    "naranja": "#D35400",
    "verde":   "#1E8449",
    "rojo":    "#C0392B",
    "morado":  "#5B2C6F",
    "dorado":  "#B7950B",
    "gris":    "#7F8C8D",
    "text":    "#1a1a2e",
    "muted":   "#444444",
}

CAT_COLOR = {
    "TI & Datos":        PALETTE["azul"],
    "Ingeniería":        PALETTE["verde"],
    "Derecho":           PALETTE["morado"],
    "Salud":             PALETTE["rojo"],
    "Negocio & Gestión": PALETTE["naranja"],
    "Marketing":         "#8E44AD",
    "Finanzas":          PALETTE["dorado"],
}

SENIORITY_PATTERNS = {
    "Junior / Trainee":    r"junior|trainee|auxiliar|asistente|pasante|intern|aprendiz",
    "Semi-Senior":         r"semi|mid[- ]level",
    "Senior":              r"senior|sr\.?\s|especialista senior",
    "Coordinador / Jefe":  r"coordinador|jefe|supervisor",
    "Gerente / Director":  r"gerente|director|head of|chief",
    "C-Level / VP":        r"ceo|cto|cfo|vp |vice president",
}

COMP_TECNICAS = {
    "python", "sql", "excel", "power bi", "powerbi", "tableau", "looker",
    "machine learning", "aws", "azure", "gcp", "cloud", "docker", "kubernetes",
    "devops", "java", "javascript", "react", "angular", "sap", "salesforce",
    "scrum", "agile", "data", "bi", "nlp", "tensorflow", "pytorch", "spark",
}
COMP_BLANDAS = {
    "liderazgo", "comunicación", "comunicacion", "gestion", "gestión",
    "analítica", "analitica", "estrategia", "innovación", "innovacion",
    "servicio", "consultoría", "consultoria",
}


# ============================================================
# PIPELINE DE DATOS  (llamado desde app.py)
# ============================================================

def pipeline_datos(db_path: str = DB_PATH, log_fn=None) -> None:
    """
    Scraping de LinkedIn Colombia con jobspy → DataFrame → DuckDB.

    Responde la lógica:
      • BD no existe → la crea y crea la tabla
      • BD existe, tabla no existe → solo crea la tabla
      • BD existe, tabla existe → reemplaza la tabla (CREATE OR REPLACE)
    """
    def log(msg: str):
        if log_fn:
            log_fn(msg)

    try:
        from jobspy import scrape_jobs
    except ImportError:
        raise ImportError(
            "jobspy no está instalado. Ejecuta: pip install python-jobspy"
        )

    log(f"[1/4] Iniciando scraping LinkedIn Colombia — {len(PERFILES)} queries definidas")

    frames = []
    total = len(PERFILES)
    for i, perfil in enumerate(PERFILES, 1):
        log(f"[{i}/{total}] Buscando: {perfil}")
        try:
            jobs = scrape_jobs(
                site_name=["linkedin"],
                search_term=perfil,
                location="Colombia",
                results_wanted=50,
                hours_old=720,  # últimos 30 días
            )
            if len(jobs) > 0:
                jobs["perfil_busqueda"] = perfil
                frames.append(jobs)
                log(f"         → {len(jobs)} vacantes encontradas")
            else:
                log(f"         → Sin resultados")
        except Exception as e:
            log(f"         → Error en '{perfil}': {e}")

    if not frames:
        raise RuntimeError(
            "No se obtuvieron vacantes. "
            "Verifica tu conexión a LinkedIn o ejecuta create_session.py primero."
        )

    log(f"[2/4] Combinando y limpiando {sum(len(f) for f in frames)} registros...")
    df = pd.concat(frames, ignore_index=True)

    # Deduplicar por URL si existe la columna
    if "job_url" in df.columns:
        df = df.drop_duplicates(subset="job_url", keep="first")

    # ── Enriquecimiento ───────────────────────────────────────────────────────
    df["fecha_extraccion"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    df["title_lower"] = df["title"].astype(str).str.lower().str.strip()

    df["ciudad"] = (
        df["location"].astype(str)
        .str.extract(r"^([^,]+)", expand=False)
        .str.strip()
        .fillna("No especificado")
    )
    df["departamento"] = (
        df["location"].astype(str)
        .str.extract(r",\s*([^,]+),\s*Colombia", expand=False)
        .str.strip()
        .replace("Capital District", "Bogotá D.C.")
        .fillna("No especificado")
    )

    def _match_perfil(row):
        # Primero usa la query con la que se obtuvo el resultado
        pb = str(row.get("perfil_busqueda", "")).strip().lower()
        if pb and pb in [p.lower() for p in PERFILES]:
            return pb
        # Fallback: búsqueda por substring en el título
        tl = str(row.get("title_lower", ""))
        for p in PERFILES:
            if p.lower() in tl:
                return p
        return None

    def _clasif_seniority(t):
        for nivel, pat in SENIORITY_PATTERNS.items():
            if re.search(pat, str(t)):
                return nivel
        return "Sin nivel especificado"

    df["perfil_ref"]       = df.apply(_match_perfil, axis=1)
    df["categoria_macro"]  = df["perfil_ref"].map(CATEGORIA_PERFIL).fillna("Otros")
    df["nombre_es"]        = df["perfil_ref"].map(PERFILES_ES).fillna(df["title"].str[:40])
    df["seniority"]        = df["title_lower"].apply(_clasif_seniority)

    # Asegurar que todas las columnas sean tipos serializables por DuckDB
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].astype(str).replace("nan", None)

    log(f"[3/4] {len(df):,} vacantes únicas procesadas")

    # ── Guardar en DuckDB ─────────────────────────────────────────────────────
    log(f"[4/4] Guardando en DuckDB: tabla '{TABLA_CO}'...")
    con = duckdb.connect(db_path)
    # CREATE OR REPLACE funciona tanto si la tabla existe como si no
    con.execute(f"CREATE OR REPLACE TABLE {TABLA_CO} AS SELECT * FROM df")
    n = con.execute(f"SELECT COUNT(*) FROM {TABLA_CO}").fetchone()[0]
    con.close()

    log(f"✅ Pipeline completado — {n:,} vacantes en '{TABLA_CO}'")


def bd_tiene_datos(db_path: str = DB_PATH) -> bool:
    """Devuelve True si la BD existe y la tabla tiene al menos una fila."""
    if not os.path.exists(db_path):
        return False
    try:
        con = duckdb.connect(db_path, read_only=True)
        tablas = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
        if TABLA_CO not in tablas:
            con.close()
            return False
        n = con.execute(f"SELECT COUNT(*) FROM {TABLA_CO}").fetchone()[0]
        con.close()
        return n > 0
    except Exception:
        return False


# ============================================================
# CARGA DESDE DUCKDB
# ============================================================

@st.cache_data(show_spinner=False)
def _cargar_desde_db(db_path: str = DB_PATH) -> pd.DataFrame:
    con = duckdb.connect(db_path, read_only=True)
    df  = con.execute(f"SELECT * FROM {TABLA_CO}").df()
    con.close()
    df["date_posted"] = pd.to_datetime(df.get("date_posted", pd.Series(dtype="object")),
                                        errors="coerce")
    return df


# ============================================================
# HELPERS INTERNOS DE GRÁFICOS
# ============================================================

def _base_fig(title: str, figsize=(14, 7)) -> tuple:
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(PALETTE["bg"])
    ax.set_facecolor(PALETTE["panel"])
    ax.set_title(title, color=PALETTE["text"], fontsize=13, fontweight="bold", pad=12)
    ax.tick_params(colors=PALETTE["text"], labelsize=9)
    for spine in ax.spines.values():
        spine.set_edgecolor("#cccccc")
    ax.grid(axis="x", color="#dddddd", linewidth=0.6, linestyle="--")
    ax.set_axisbelow(True)
    return fig, ax


# ============================================================
# GRÁFICOS  (retornan fig, nunca plt.show)
# ============================================================

def fig_perfiles_top(df: pd.DataFrame) -> mfig.Figure:
    """G1 — Perfiles más demandados (bar horizontal coloreado por categoría)."""
    data = (
        df[df["perfil_ref"].notna()]
        .groupby("perfil_ref").size()
        .reset_index(name="vacantes")
        .sort_values("vacantes", ascending=False)
        .head(30)
    )
    data["nombre_es"] = data["perfil_ref"].map(PERFILES_ES)
    data["categoria"] = data["perfil_ref"].map(CATEGORIA_PERFIL)
    data = data.sort_values("vacantes")

    colors = [CAT_COLOR.get(c, PALETTE["gris"]) for c in data["categoria"]]
    fig, ax = _base_fig("Perfiles Profesionales más Demandados — LinkedIn Colombia",
                        figsize=(13, 10))
    bars = ax.barh(data["nombre_es"], data["vacantes"],
                   color=colors, edgecolor="white", height=0.72)
    for bar, val in zip(bars, data["vacantes"]):
        ax.text(bar.get_width() + 0.4, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=8.5, fontweight="bold",
                color=PALETTE["muted"])
    ax.set_xlabel("Vacantes activas", color=PALETTE["muted"], fontsize=10)
    patches = [mpatches.Patch(color=v, label=k)
               for k, v in CAT_COLOR.items() if k in data["categoria"].values]
    ax.legend(handles=patches, fontsize=8, loc="lower right")
    plt.tight_layout()
    return fig


def fig_categorias(df: pd.DataFrame) -> mfig.Figure:
    """G1b — Distribución por categoría profesional (pie)."""
    cat = (
        df[df["perfil_ref"].notna()]
        .groupby("categoria_macro").size()
        .sort_values(ascending=False)
    )
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor(PALETTE["bg"])
    ax.pie(cat.values, labels=cat.index, autopct="%1.1f%%", startangle=140,
           pctdistance=0.82, colors=[CAT_COLOR.get(c, PALETTE["gris"]) for c in cat.index])
    ax.set_title("Distribución por Categoría Profesional",
                 color=PALETTE["text"], fontsize=13, fontweight="bold")
    plt.tight_layout()
    return fig


def fig_top_titulos(df: pd.DataFrame) -> mfig.Figure:
    """G2 — Top 25 títulos exactos."""
    top = df["title"].value_counts().head(25)
    fig, ax = _base_fig("Top 25 Puestos más Demandados — Títulos exactos", figsize=(13, 8))
    palette = plt.cm.Blues(
        __import__("numpy").linspace(0.40, 0.88, len(top))
    )
    bars = ax.barh(top.index[::-1], top.values[::-1],
                   color=palette, edgecolor="white", height=0.72)
    for bar, val in zip(bars, top.values[::-1]):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=9, color=PALETTE["muted"])
    ax.set_xlabel("Número de vacantes", color=PALETTE["muted"], fontsize=10)
    plt.tight_layout()
    return fig


def fig_seniority(df: pd.DataFrame) -> mfig.Figure:
    """G3 — Nivel de seniority demandado."""
    counts = df["seniority"].value_counts()
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.patch.set_facecolor(PALETTE["bg"])
    colors = list(CAT_COLOR.values())[:len(counts)]

    axes[0].set_facecolor(PALETTE["panel"])
    bars = axes[0].barh(counts.index[::-1], counts.values[::-1],
                         color=colors[::-1], edgecolor="white")
    for bar, val in zip(bars, counts.values[::-1]):
        axes[0].text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                     str(val), va="center", fontsize=9, color=PALETTE["muted"])
    axes[0].set_xlabel("Vacantes", color=PALETTE["muted"], fontsize=10)
    axes[0].set_title("Seniority demandado", color=PALETTE["text"],
                      fontsize=12, fontweight="bold")
    for sp in axes[0].spines.values(): sp.set_edgecolor("#cccccc")

    axes[1].set_facecolor(PALETTE["bg"])
    axes[1].pie(counts.values, labels=counts.index, autopct="%1.1f%%",
                colors=colors, startangle=90)
    axes[1].set_title("Distribución (%)", color=PALETTE["text"],
                      fontsize=12, fontweight="bold")

    fig.suptitle("Nivel de Experiencia Demandado — LinkedIn Colombia",
                 color=PALETTE["text"], fontsize=13, fontweight="bold")
    plt.tight_layout()
    return fig


def fig_temporal(df: pd.DataFrame) -> mfig.Figure | None:
    """G4 — Vacantes publicadas por semana."""
    if df["date_posted"].isna().all():
        return None
    df2 = df.copy()
    df2["semana"] = df2["date_posted"].dt.to_period("W")
    por_semana = (df2.groupby("semana").size()
                  .reset_index(name="vacantes")
                  .sort_values("semana"))
    por_semana["semana_str"] = por_semana["semana"].astype(str)
    por_semana["mm"] = por_semana["vacantes"].rolling(3, min_periods=1).mean()

    import numpy as np
    coefs = np.polyfit(range(len(por_semana)), por_semana["vacantes"], 1)
    tend  = "Creciente 📈" if coefs[0] > 0 else "Decreciente 📉"

    fig, ax = plt.subplots(figsize=(13, 4))
    fig.patch.set_facecolor(PALETTE["bg"])
    ax.set_facecolor(PALETTE["panel"])
    ax.bar(por_semana["semana_str"], por_semana["vacantes"],
           color=PALETTE["azul"], alpha=0.6, label="Vacantes / semana")
    ax.plot(por_semana["semana_str"], por_semana["mm"],
            color=PALETTE["naranja"], lw=2.5, label="Media móvil 3 semanas")
    ax.set_title(f"Publicaciones por Semana — LinkedIn Colombia | Tendencia: {tend}",
                 color=PALETTE["text"], fontsize=13, fontweight="bold", pad=10)
    ax.set_xlabel("Semana", color=PALETTE["muted"])
    ax.set_ylabel("Vacantes", color=PALETTE["muted"])
    ax.tick_params(axis="x", rotation=35, labelcolor=PALETTE["muted"])
    ax.tick_params(axis="y", labelcolor=PALETTE["muted"])
    ax.legend(fontsize=9)
    for sp in ax.spines.values(): sp.set_edgecolor("#cccccc")
    plt.tight_layout()
    return fig


def fig_geografico(df: pd.DataFrame) -> mfig.Figure | None:
    """G5 — Vacantes por departamento."""
    depto = (
        df[df["departamento"] != "No especificado"]["departamento"]
        .value_counts().reset_index()
    )
    depto.columns = ["departamento", "vacantes"]
    if depto.empty:
        return None

    pct_sin = (df["departamento"] == "No especificado").sum() / len(df) * 100
    colors  = list(CAT_COLOR.values())[:len(depto)]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor(PALETTE["bg"])

    ax1.set_facecolor(PALETTE["panel"])
    bars = ax1.barh(depto["departamento"][::-1], depto["vacantes"][::-1],
                    color=colors, edgecolor="white")
    for bar, val in zip(bars, depto["vacantes"][::-1]):
        ax1.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                 str(val), va="center", fontsize=9, color=PALETTE["muted"])
    ax1.set_xlabel("Vacantes", color=PALETTE["muted"], fontsize=10)
    ax1.set_title("Vacantes por Departamento", color=PALETTE["text"],
                  fontsize=12, fontweight="bold")
    for sp in ax1.spines.values(): sp.set_edgecolor("#cccccc")

    ax2.set_facecolor(PALETTE["bg"])
    ax2.pie(depto["vacantes"], labels=depto["departamento"],
            autopct="%1.1f%%", colors=colors, startangle=140)
    ax2.set_title("Distribución (%)", color=PALETTE["text"],
                  fontsize=12, fontweight="bold")

    fig.suptitle(f"Distribución Geográfica — LinkedIn Colombia "
                 f"({pct_sin:.1f}% sin localización)",
                 color=PALETTE["text"], fontsize=13, fontweight="bold")
    plt.tight_layout()
    return fig


def fig_habilidades(df: pd.DataFrame) -> mfig.Figure:
    """G6 — Competencias técnicas y blandas detectadas en títulos (y descripciones si existen)."""
    texto_fuente = df["title_lower"].fillna("")
    if "description" in df.columns and df["description"].notna().sum() > 0:
        texto_fuente = texto_fuente + " " + df["description"].fillna("").str.lower()

    contador_tec, contador_bla = Counter(), Counter()
    for texto in texto_fuente:
        for kw in COMP_TECNICAS:
            if kw in texto:
                contador_tec[kw] += 1
        for kw in COMP_BLANDAS:
            if kw in texto:
                contador_bla[kw] += 1

    top_tec = pd.Series(dict(contador_tec.most_common(15))).sort_values()
    top_bla = pd.Series(dict(contador_bla.most_common(10))).sort_values()

    import numpy as np
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.patch.set_facecolor(PALETTE["bg"])

    if len(top_tec) > 0:
        norm = top_tec / top_tec.max()
        axes[0].set_facecolor(PALETTE["panel"])
        axes[0].barh(top_tec.index, top_tec.values,
                     color=[plt.cm.Blues(0.35 + v * 0.55) for v in norm],
                     edgecolor="white")
        for i, val in enumerate(top_tec.values):
            axes[0].text(val + 0.3, i, str(val), va="center", fontsize=9,
                         color=PALETTE["muted"])
        axes[0].set_title("Competencias Técnicas", color=PALETTE["text"],
                          fontsize=12, fontweight="bold")
        axes[0].set_xlabel("Menciones", color=PALETTE["muted"])
        for sp in axes[0].spines.values(): sp.set_edgecolor("#cccccc")
    else:
        axes[0].text(0.5, 0.5, "Sin datos suficientes", ha="center", va="center",
                     transform=axes[0].transAxes, fontsize=11, color="gray")

    if len(top_bla) > 0:
        norm2 = top_bla / top_bla.max()
        axes[1].set_facecolor(PALETTE["panel"])
        axes[1].barh(top_bla.index, top_bla.values,
                     color=[plt.cm.Oranges(0.35 + v * 0.55) for v in norm2],
                     edgecolor="white")
        for i, val in enumerate(top_bla.values):
            axes[1].text(val + 0.3, i, str(val), va="center", fontsize=9,
                         color=PALETTE["muted"])
        axes[1].set_title("Competencias Blandas", color=PALETTE["text"],
                          fontsize=12, fontweight="bold")
        axes[1].set_xlabel("Menciones", color=PALETTE["muted"])
        for sp in axes[1].spines.values(): sp.set_edgecolor("#cccccc")
    else:
        axes[1].text(0.5, 0.5, "Muy pocas menciones.\nRe-ejecuta con description=True.",
                     ha="center", va="center", transform=axes[1].transAxes,
                     fontsize=9, color="gray")

    fig.suptitle("Habilidades Detectadas en Vacantes — LinkedIn Colombia",
                 color=PALETTE["text"], fontsize=13, fontweight="bold")
    plt.tight_layout()
    return fig

# ============================================================
# SECCIÓN STREAMLIT PRINCIPAL  (solo visualización)
# ============================================================

def mostrar_colombia() -> None:
    """Renderiza la página Colombia en Streamlit. Solo visualización."""

    st.markdown(
        "Análisis de vacantes activas en **LinkedIn Colombia** por perfil profesional, "
        "geografía, seniority y habilidades."
    )

    if not bd_tiene_datos():
        st.warning(
            "⚠️ No hay datos de Colombia cargados. "
            "Ve al **Panel de Actualización** y presiona **'Consultar LinkedIn Colombia'** "
            "para inicializarlos."
        )
        return

    con     = duckdb.connect(DB_PATH, read_only=True)
    n_vac   = con.execute(f"SELECT COUNT(*) FROM {TABLA_CO}").fetchone()[0]
    fecha   = con.execute(f"SELECT MAX(fecha_extraccion) FROM {TABLA_CO}").fetchone()[0]
    con.close()

    st.info(
        f"📊 Datos LinkedIn Colombia cargados · "
        f"**{n_vac:,} vacantes** · Última extracción: **{fecha}**"
    )
    st.caption("💡 Para actualizar, ve al **Panel de Actualización** en el menú principal.")

    df = _cargar_desde_db()

    # ── Filtros rápidos ───────────────────────────────────────────────────────
    with st.expander("🔎 Filtros", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            cats = ["Todas"] + sorted(df["categoria_macro"].dropna().unique().tolist())
            cat_sel = st.selectbox("Categoría", cats)
        with col2:
            deptos = ["Todos"] + sorted(
                df[df["departamento"] != "No especificado"]["departamento"]
                .dropna().unique().tolist()
            )
            depto_sel = st.selectbox("Departamento", deptos)

    df_f = df.copy()
    if cat_sel != "Todas":
        df_f = df_f[df_f["categoria_macro"] == cat_sel]
    if depto_sel != "Todos":
        df_f = df_f[df_f["departamento"] == depto_sel]

    st.caption(f"Mostrando **{len(df_f):,}** vacantes con los filtros aplicados.")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🏆 Perfiles",
        "💼 Puestos",
        "📶 Seniority",
        "📅 Temporal",
        "🗺️ Geografía",
        "💡 Habilidades"
    ])

    with tab1:
        st.subheader("Perfiles más demandados")
        fig = fig_perfiles_top(df_f)
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

        st.divider()
        st.subheader("Distribución por categoría")
        fig2 = fig_categorias(df_f)
        st.pyplot(fig2, use_container_width=True)
        plt.close(fig2)

    with tab2:
        st.subheader("Top 25 títulos exactos en LinkedIn Colombia")
        fig = fig_top_titulos(df_f)
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

    with tab3:
        st.subheader("Nivel de experiencia demandado")
        fig = fig_seniority(df_f)
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

    with tab4:
        st.subheader("Evolución temporal de publicaciones")
        fig = fig_temporal(df_f)
        if fig:
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)
        else:
            st.info("Sin datos de fecha de publicación en este dataset.")

    with tab5:
        st.subheader("Distribución geográfica de vacantes")
        fig = fig_geografico(df_f)
        if fig:
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)
        else:
            st.info("Sin datos geográficos suficientes.")

    with tab6:
        st.subheader("Habilidades detectadas en vacantes")
        fig = fig_habilidades(df_f)
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)
        if "description" not in df_f.columns or df_f["description"].isna().all():
            st.caption(
                "ℹ️ Solo se analizaron títulos. "
                "Para análisis completo de competencias, re-ejecuta el pipeline "
                "con `linkedin_fetch_description=True` en jobspy."
            )