# Streamlit/AnalisisInternacional/DatosInternacionales.py
import streamlit as st
import requests
import pandas as pd
import time
from datetime import datetime

# ==================== CONFIG ====================
APP_ID = st.secrets["ADZUNA_APP_ID"]
APP_KEY = st.secrets["ADZUNA_APP_KEY"]
BASE_URL = "https://api.adzuna.com/v1/api/jobs"

PAISES = [
    "gb",  # Reino Unido
    "us",  # EE.UU.
    "au",  # Australia
    "ca",  # Canadá
    "nz",  # Nueva Zelanda
    "de",  # Alemania
    "fr",  # Francia
    "nl",  # Países Bajos
    "be",  # Bélgica
    "at",  # Austria
    "ch",  # Suiza
    "it",  # Italia
    "es",  # España
    "pl",  # Polonia
    "br",  # Brasil
    "in",  # India
    "mx",  # México
    "sg",  # Singapur
    "za",  # Sudáfrica
]

NOMBRES = {
    "gb": "Reino Unido",
    "us": "EE.UU.",
    "au": "Australia",
    "ca": "Canadá",
    "nz": "Nueva Zelanda",
    "de": "Alemania",
    "fr": "Francia",
    "nl": "Países Bajos",
    "be": "Bélgica",
    "at": "Austria",
    "ch": "Suiza",
    "it": "Italia",
    "es": "España",
    "pl": "Polonia",
    "br": "Brasil",
    "in": "India",
    "mx": "México",
    "sg": "Singapur",
    "za": "Sudáfrica",
}

PROFESIONES = [
    "data scientist", "software engineer", "data analyst",
    "machine learning engineer", "devops engineer",
    "cybersecurity analyst", "cloud engineer",
    "business analyst", "project manager", "product manager",
    "financial analyst", "marketing specialist", "ux designer",
    "industrial engineer", "supply chain analyst", "nurse", "teacher", "consultant"
]


# ==================== INICIALIZACIÓN DE CACHE EN SESSION STATE ====================

def _inicializar_session_state():
    if "datos_adzuna_df" not in st.session_state:
        st.session_state.datos_adzuna_df = None
    if "datos_adzuna_analisis" not in st.session_state:
        st.session_state.datos_adzuna_analisis = None
    if "datos_adzuna_fecha" not in st.session_state:
        st.session_state.datos_adzuna_fecha = None


# ==================== CONSULTA REAL A ADZUNA ====================

def _consultar_adzuna_api() -> pd.DataFrame:
    """Consulta vacantes usando solo Adzuna (internacional). Uso interno."""
    registros = []
    progress_bar = st.progress(0)
    total = len(PAISES) * len(PROFESIONES)
    count = 0

    for pais in PAISES:
        for perfil in PROFESIONES:
            data = adzuna_request(pais, "search/1", {
                "results_per_page": 1,
                "what": perfil
            })
            if data:
                registros.append({
                    "pais": pais,
                    "pais_nombre": NOMBRES[pais],
                    "perfil": perfil.title(),
                    "vacantes": data.get("count", 0),
                    "fecha": datetime.now().date()
                })
            count += 1
            progress_bar.progress(count / total)
            time.sleep(0.25)

    progress_bar.empty()
    return pd.DataFrame(registros)


def _calcular_analisis(df: pd.DataFrame) -> dict:
    """Calcula las agregaciones a partir del DataFrame crudo."""
    df_perfil = df.groupby('perfil').agg(
        vacantes_total=('vacantes', 'sum'),
        paises_presentes=('pais_nombre', 'nunique')
    ).reset_index()

    df_pais = df.groupby('pais_nombre').agg(
        vacantes_total=('vacantes', 'sum')
    ).reset_index()

    top_perfiles = df_perfil.nlargest(10, 'vacantes_total')
    bottom_perfiles = df_perfil.nsmallest(5, 'vacantes_total')

    vacantes_us = df[df['pais_nombre'] == 'EE.UU.']['vacantes'].sum()
    vacantes_br = df[df['pais_nombre'] == 'Brasil']['vacantes'].sum()

    return {
        'df': df,
        'df_perfil': df_perfil,
        'df_pais': df_pais,
        'top_perfiles': top_perfiles,
        'bottom_perfiles': bottom_perfiles,
        'vacantes_us': vacantes_us,
        'vacantes_br': vacantes_br,
        'total_registros': len(df)
    }


# ==================== INTERFAZ PÚBLICA ====================

def mostrar_boton_actualizacion():
    """
    Renderiza el botón de refresco y el timestamp.
    Llama a esto en la página antes de usar get_analisis_completo().
    """
    _inicializar_session_state()

    col1, col2 = st.columns([3, 1])

    with col1:
        if st.session_state.datos_adzuna_fecha:
            st.caption(
                f"📅 Datos actualizados el "
                f"{st.session_state.datos_adzuna_fecha.strftime('%d/%m/%Y a las %H:%M')}"
            )
        else:
            st.caption("⚠️ Sin datos cargados. Presiona **Actualizar** para consultar Adzuna.")

    with col2:
        if st.button("🔄 Actualizar datos", use_container_width=True):
            with st.spinner("Consultando Adzuna... esto puede tomar unos minutos."):
                df = _consultar_adzuna_api()
                st.session_state.datos_adzuna_df = df
                st.session_state.datos_adzuna_analisis = _calcular_analisis(df)
                st.session_state.datos_adzuna_fecha = datetime.now()
            st.success("✅ Datos actualizados correctamente.")
            st.rerun()


def get_analisis_completo() -> dict | None:
    """
    Retorna el análisis desde session_state.
    Devuelve None si aún no se ha hecho la primera consulta.
    """
    _inicializar_session_state()
    return st.session_state.datos_adzuna_analisis


def get_contexto_para_ia() -> str:
    """
    Retorna un resumen en texto plano de los datos actuales,
    listo para enviarse como contexto a Claude.
    """
    analisis = get_analisis_completo()

    if analisis is None:
        return "Sin datos de Adzuna disponibles. El usuario no ha realizado una consulta aún."

    top = analisis['top_perfiles'][['perfil', 'vacantes_total']].to_string(index=False)
    bottom = analisis['bottom_perfiles'][['perfil', 'vacantes_total']].to_string(index=False)
    paises = analisis['df_pais'].nlargest(5, 'vacantes_total')[['pais_nombre', 'vacantes_total']].to_string(index=False)
    fecha = st.session_state.datos_adzuna_fecha.strftime('%d/%m/%Y %H:%M')

    return f"""
        Fuente: Adzuna (datos al {fecha})
        Total de registros analizados: {analisis['total_registros']}

        TOP 10 perfiles con más vacantes:
        {top}

        Perfiles con menos demanda:
        {bottom}

        Top 5 países con más vacantes:
        {paises}

        Vacantes en EE.UU.: {analisis['vacantes_us']:,}
        Vacantes en Brasil: {analisis['vacantes_br']:,}
        """.strip()


# ==================== REQUEST HELPER ====================

def adzuna_request(pais: str, endpoint: str, params: dict = None):
    url = f"{BASE_URL}/{pais}/{endpoint}"
    p = {"app_id": APP_ID, "app_key": APP_KEY, **(params or {})}
    try:
        r = requests.get(url, params=p, timeout=12)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None





#============================================================
# NUEVAS COSAS
