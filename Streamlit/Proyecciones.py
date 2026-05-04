import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
import streamlit as st

# ── Paleta ────────────────────────────────────────────────────────────────────
AZUL    = "#003366"
ROJO    = "#CC0000"
VERDE   = "#006633"
DORADO  = "#CC9900"
GRIS    = "#555555"

plt.rcParams.update({
    "figure.facecolor" : "white",
    "axes.facecolor"   : "#F8F9FA",
    "axes.spines.top"  : False,
    "axes.spines.right": False,
    "font.family"      : "sans-serif",
    "axes.titlesize"   : 13,
    "axes.titleweight" : "bold",
    "axes.labelsize"   : 10,
})

# ── Etiquetas cortas de sectores ──────────────────────────────────────────────
SECTOR_LABEL = {
    "management"              : "Gestión",
    "business and financial"  : "Negocios & Finanzas",
    "computer and mathematical": "TI & Matemáticas",
    "architecture and engineering": "Arquitectura & Ing.",
    "life, physical"          : "Ciencias",
    "community and social"    : "Serv. Sociales",
    "legal"                   : "Legal",
    "educational instruction" : "Educación",
    "arts, design"            : "Arte & Medios",
    "healthcare practitioners": "Salud Profesional",
    "healthcare support"      : "Salud Apoyo",
    "protective service"      : "Seguridad",
    "food preparation"        : "Gastronomía",
    "building and grounds"    : "Limpieza & Mant.",
    "personal care"           : "Cuidado Personal",
    "sales and related"       : "Ventas",
    "office and administrative": "Administración",
    "farming, fishing"        : "Agro & Pesca",
    "construction and extraction": "Construcción",
    "installation, maintenance": "Mantenimiento",
    "production occupations"  : "Producción",
    "transportation"          : "Transporte",
}

ETIQ_ED = {
    "No formal educational credential"  : "Sin credencial",
    "Some college, no degree"           : "Algo de universidad",
    "High school diploma or equivalent" : "Bachillerato",
    "Postsecondary nondegree award"     : "Certificado técnico",
    "Associate's degree"                : "Técnico 2 años",
    "Bachelor's degree"                 : "Pregrado",
    "Master's degree"                   : "Maestría",
    "Doctoral or professional degree"   : "Doctorado / Prof.",
}

ORDEN_ED = list(ETIQ_ED.keys())


def _short(s, n=45):
    s = str(s)
    for k, v in SECTOR_LABEL.items():
        if k in s.lower():
            return v
    return s[:n]


def _load_std(xls, sheet):
    df = xls.parse(sheet, skiprows=1, header=0)
    df.columns = ["occupation", "soc", "emp24", "emp34", "chg_num", "chg_pct", "wage"]
    for c in ["emp24", "emp34", "chg_num", "chg_pct", "wage"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[df["emp24"].notna() & df["occupation"].notna()]
    df["occupation"] = df["occupation"].astype(str)
    df = df[~df["occupation"].str.startswith("Total")]
    return df


# ── Carga principal ────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def cargar_datos(archivo_bytes):
    xls = pd.ExcelFile(archivo_bytes)

    df11 = _load_std(xls, "Table 1.1")
    df13 = _load_std(xls, "Table 1.3")
    df14 = _load_std(xls, "Table 1.4")
    df15 = _load_std(xls, "Table 1.5")
    df16 = _load_std(xls, "Table 1.6")

    df12 = xls.parse("Table 1.2", skiprows=1, header=0)
    df12.columns = [
        "occupation", "soc", "type", "emp24", "emp34", "dist24", "dist34",
        "chg_num", "chg_pct", "self_emp", "openings", "wage",
        "education", "work_exp", "ojt", "ooh",
    ]
    for c in ["emp24", "emp34", "chg_num", "chg_pct", "openings", "wage"]:
        df12[c] = pd.to_numeric(df12[c], errors="coerce")
    df12 = df12[df12["type"].astype(str).str.strip() == "Line item"]

    df11["label"] = df11["occupation"].apply(_short)

    return df11, df12, df13, df14, df15, df16


# ─────────────────────────────────────────────────────────────────────────────
# G1 · ¿Qué ocupaciones tienen mayor proyección?
# ─────────────────────────────────────────────────────────────────────────────
def grafico_mayor_proyeccion(df13):
    top = df13.nlargest(20, "chg_pct").copy()
    top["occ_s"] = top["occupation"].str[:48]
    top = top.sort_values("chg_pct")

    colors = [VERDE if v >= 20 else AZUL for v in top["chg_pct"]]

    fig, ax = plt.subplots(figsize=(10, 7))
    bars = ax.barh(top["occ_s"], top["chg_pct"], color=colors, edgecolor="white", height=0.72)

    for bar, val in zip(bars, top["chg_pct"]):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f"+{val:.1f}%", va="center", fontsize=8.5, fontweight="bold", color="#222")

    ax.axvline(3.1, color=GRIS, lw=1.4, linestyle="--")
    ax.text(3.4, ax.get_ylim()[1] * 0.98, "Promedio\nnacional\n3.1%",
            fontsize=7.5, color=GRIS, va="top")

    ax.set_xlabel("Crecimiento proyectado 2024–2034 (%)")
    ax.set_title("¿Qué ocupaciones tienen mayor proyección?", pad=10)
    ax.set_xlim(0, top["chg_pct"].max() * 1.22)
    ax.tick_params(axis="y", labelsize=8.5)

    verde_p = mpatches.Patch(color=VERDE, label="Muy alto (≥20%)")
    azul_p  = mpatches.Patch(color=AZUL,  label="Alto crecimiento")
    ax.legend(handles=[verde_p, azul_p], fontsize=9, loc="lower right")

    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# G2 · ¿Qué puestos son los más demandados?
# ─────────────────────────────────────────────────────────────────────────────
def grafico_puestos_demandados(df14):
    top = df14.nlargest(20, "chg_num").copy()
    top["occ_s"] = top["occupation"].str[:48]
    top = top.sort_values("chg_num")

    palette = plt.cm.Blues(np.linspace(0.40, 0.88, len(top)))

    fig, ax = plt.subplots(figsize=(10, 7))
    bars = ax.barh(top["occ_s"], top["chg_num"], color=palette, edgecolor="white", height=0.72)

    for bar, val in zip(bars, top["chg_num"]):
        ax.text(bar.get_width() + 1.5, bar.get_y() + bar.get_height() / 2,
                f"+{val:.0f}K", va="center", fontsize=8.5, fontweight="bold", color="#222")

    ax.set_xlabel("Nuevos empleos proyectados 2024–2034 (miles)")
    ax.set_title("¿Qué puestos son los más demandados?", pad=10)
    ax.tick_params(axis="y", labelsize=8.5)

    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# G3 · Tendencias por sector — Aumento vs. Disminución
# ─────────────────────────────────────────────────────────────────────────────
def grafico_tendencias_sector(df11):
    df = df11[["label", "chg_pct"]].dropna().sort_values("chg_pct")
    colors = [ROJO if v < 0 else (VERDE if v >= 7 else AZUL) for v in df["chg_pct"]]

    fig, ax = plt.subplots(figsize=(10, 7))
    bars = ax.barh(df["label"], df["chg_pct"], color=colors, edgecolor="white", height=0.68)

    for bar, val in zip(bars, df["chg_pct"]):
        xpos = bar.get_width() + 0.15 if val >= 0 else bar.get_width() - 0.15
        ha   = "left" if val >= 0 else "right"
        ax.text(xpos, bar.get_y() + bar.get_height() / 2,
                f"{val:+.1f}%", va="center", ha=ha, fontsize=9,
                fontweight="bold", color=ROJO if val < 0 else "#222")

    ax.axvline(0,   color="black", lw=0.9)
    ax.axvline(3.1, color=GRIS,   lw=1.2, linestyle=":", label="Promedio nacional: 3.1%")
    ax.set_xlabel("Variación de empleo proyectada 2024–2034 (%)")
    ax.set_title("¿Cómo está cambiando la empleabilidad? — Tendencias por sector", pad=10)
    ax.tick_params(axis="y", labelsize=9)

    rojo_p  = mpatches.Patch(color=ROJO,  label="Sector en declive")
    azul_p  = mpatches.Patch(color=AZUL,  label="Crecimiento moderado")
    verde_p = mpatches.Patch(color=VERDE, label="Alto crecimiento (≥7%)")
    ax.legend(handles=[verde_p, azul_p, rojo_p], fontsize=9, loc="lower right")

    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# G4 · Programas en riesgo
# ─────────────────────────────────────────────────────────────────────────────
def grafico_programas_riesgo(df15, df16):
    fig, axes = plt.subplots(1, 2, figsize=(14, 7))

    d5 = df15.nsmallest(15, "chg_pct").copy()
    d5["occ_s"] = d5["occupation"].str[:40]
    d5 = d5.sort_values("chg_pct", ascending=False)
    p5 = plt.cm.Reds(np.linspace(0.45, 0.88, len(d5)))
    axes[0].barh(d5["occ_s"], d5["chg_pct"], color=p5, edgecolor="white", height=0.68)
    for i, (_, row) in enumerate(d5.iterrows()):
        axes[0].text(row["chg_pct"] - 0.3, i, f"{row['chg_pct']:.1f}%",
                     va="center", ha="right", fontsize=8, fontweight="bold", color="white")
    axes[0].axvline(0, color="black", lw=0.8)
    axes[0].set_xlabel("Cambio % 2024–2034")
    axes[0].set_title("Declive más rápido (%)", pad=8)
    axes[0].tick_params(axis="y", labelsize=8)

    d6 = df16.nsmallest(15, "chg_num").copy()
    d6["occ_s"] = d6["occupation"].str[:40]
    d6 = d6.sort_values("chg_num", ascending=False)
    p6 = plt.cm.Oranges(np.linspace(0.45, 0.88, len(d6)))
    axes[1].barh(d6["occ_s"], d6["chg_num"], color=p6, edgecolor="white", height=0.68)
    for i, (_, row) in enumerate(d6.iterrows()):
        axes[1].text(row["chg_num"] - 1.5, i, f"{row['chg_num']:.0f}K",
                     va="center", ha="right", fontsize=8, fontweight="bold", color="white")
    axes[1].axvline(0, color="black", lw=0.8)
    axes[1].set_xlabel("Empleos perdidos (miles) 2024–2034")
    axes[1].set_title("Mayor pérdida neta de empleos", pad=8)
    axes[1].tick_params(axis="y", labelsize=8)

    fig.suptitle("Programas en riesgo — Ocupaciones en declive 2024–2034",
                 fontsize=13, fontweight="bold", y=1.01)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# G5 · Variaciones salariales por sector
# ─────────────────────────────────────────────────────────────────────────────
def grafico_salarios_sector(df11):
    df = df11[["label", "wage"]].dropna().sort_values("wage")
    mediana_usa = 49500

    norm = (df["wage"] - df["wage"].min()) / (df["wage"].max() - df["wage"].min())
    bar_colors = [plt.cm.RdYlGn(v) for v in norm]

    fig, ax = plt.subplots(figsize=(10, 7))
    bars = ax.barh(df["label"], df["wage"] / 1000, color=bar_colors, edgecolor="white", height=0.70)

    for bar, val in zip(bars, df["wage"]):
        ax.text(bar.get_width() + 0.8, bar.get_y() + bar.get_height() / 2,
                f"${val/1000:.0f}K", va="center", fontsize=9, fontweight="bold", color="#333")

    ax.axvline(mediana_usa / 1000, color=ROJO, lw=1.8, linestyle="--",
               label=f"Mediana USA: ${mediana_usa/1000:.0f}K")
    ax.set_xlabel("Salario mediano anual 2024 (miles USD)")
    ax.set_title("Variaciones salariales por sector ocupacional", pad=10)
    ax.set_xlim(0, df["wage"].max() / 1000 * 1.18)
    ax.tick_params(axis="y", labelsize=9)
    ax.legend(fontsize=9)

    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# G6 · Variaciones salariales por nivel educativo requerido
# ─────────────────────────────────────────────────────────────────────────────
def grafico_salarios_educacion(df12):
    df_ed = (
        df12.groupby("education")
        .agg(
            wage_median=("wage", "median"),
            wage_q25=("wage", lambda x: x.quantile(0.25)),
            wage_q75=("wage", lambda x: x.quantile(0.75)),
            chg_pct_med=("chg_pct", "median"),
        )
        .reset_index()
    )
    df_ed = df_ed[df_ed["education"].isin(ORDEN_ED)]
    df_ed["education"] = pd.Categorical(df_ed["education"], categories=ORDEN_ED, ordered=True)
    df_ed = df_ed.sort_values("education")
    df_ed["ed_s"] = df_ed["education"].map(ETIQ_ED)

    norm = (df_ed["wage_median"] - df_ed["wage_median"].min()) / (
        df_ed["wage_median"].max() - df_ed["wage_median"].min()
    )
    bar_colors = [plt.cm.YlGn(0.35 + v * 0.55) for v in norm]

    fig, ax1 = plt.subplots(figsize=(12, 6))
    bars = ax1.bar(df_ed["ed_s"], df_ed["wage_median"] / 1000,
                   color=bar_colors, edgecolor="white", width=0.60)

    yerr_low  = (df_ed["wage_median"] - df_ed["wage_q25"])  / 1000
    yerr_high = (df_ed["wage_q75"]    - df_ed["wage_median"]) / 1000
    ax1.errorbar(df_ed["ed_s"], df_ed["wage_median"] / 1000,
                 yerr=[yerr_low, yerr_high],
                 fmt="none", ecolor=GRIS, elinewidth=1.5, capsize=5, zorder=5)

    for bar, val in zip(bars, df_ed["wage_median"]):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.8,
                 f"${val/1000:.0f}K", ha="center", va="bottom", fontsize=8.5, fontweight="bold")

    ax2 = ax1.twinx()
    ax2.plot(df_ed["ed_s"], df_ed["chg_pct_med"], "s--", color=AZUL,
             lw=2, markersize=8, label="Crecimiento mediano (%)", zorder=6)
    ax2.set_ylabel("Crecimiento de empleo mediano (%)", color=AZUL, fontsize=10)
    ax2.tick_params(axis="y", labelcolor=AZUL)

    ax1.axhline(49.5, color=ROJO, lw=1.5, linestyle=":", label="Mediana USA: $49.5K")
    ax1.set_ylabel("Salario mediano anual 2024 (miles USD)", fontsize=10)
    ax1.set_title("Variaciones salariales por nivel educativo requerido\n(barras de error = rango IQR)", pad=10)
    ax1.set_xticklabels(df_ed["ed_s"], rotation=28, ha="right", fontsize=9)

    lines1, lbl1 = ax1.get_legend_handles_labels()
    lines2, lbl2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, lbl1 + lbl2, fontsize=9, loc="upper left")

    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


# ─────────────────────────────────────────────────────────────────────────────
# G7 · Sectores con mayor crecimiento — scatter vacantes vs %
# ─────────────────────────────────────────────────────────────────────────────
def grafico_scatter_crecimiento(df11, df12):
    df12_agg = df12.copy()
    df12_agg["soc2"] = df12_agg["soc"].astype(str).str[:2]
    sector_op = (
        df12_agg.groupby("soc2")
        .agg(openings_total=("openings", "sum"))
        .reset_index()
    )

    df11["soc2"] = df11["soc"].astype(str).str[:2]
    df_sc = df11[["soc2", "label", "chg_pct", "emp24"]].merge(sector_op, on="soc2", how="left")
    df_sc = df_sc.dropna(subset=["chg_pct", "openings_total"])

    sizes  = (df_sc["emp24"] / df_sc["emp24"].max()) * 1400 + 60
    colors_sc = [ROJO if p < 0 else (VERDE if p >= 7 else AZUL) for p in df_sc["chg_pct"]]

    fig, ax = plt.subplots(figsize=(11, 7))
    ax.scatter(df_sc["openings_total"] / 1000, df_sc["chg_pct"],
               s=sizes, c=colors_sc, alpha=0.82, edgecolors="white", linewidths=1.5, zorder=3)

    for _, row in df_sc.iterrows():
        ax.annotate(row["label"],
                    (row["openings_total"] / 1000, row["chg_pct"]),
                    textcoords="offset points", xytext=(7, 3), fontsize=8, color="#222")

    ax.axhline(0,   color="black", lw=0.8)
    ax.axhline(3.1, color=GRIS,   lw=1.2, linestyle="--", label="Promedio: 3.1%")
    ax.set_xlabel("Vacantes anuales proyectadas 2024–2034 (miles)", fontsize=10)
    ax.set_ylabel("Crecimiento de empleo proyectado (%)", fontsize=10)
    ax.set_title("Sectores con mayor crecimiento\n(tamaño = empleo total 2024)", pad=10)

    rojo_p  = mpatches.Patch(color=ROJO,  label="Sector en declive")
    azul_p  = mpatches.Patch(color=AZUL,  label="Crecimiento moderado")
    verde_p = mpatches.Patch(color=VERDE, label="Alto crecimiento (≥7%)")
    prom_l  = plt.Line2D([0], [0], color=GRIS, lw=1.2, linestyle="--", label="Promedio: 3.1%")
    ax.legend(handles=[verde_p, azul_p, rojo_p, prom_l], fontsize=9, loc="upper left")

    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
