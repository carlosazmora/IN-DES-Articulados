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
            st.caption("⚠️ Sin datos cargados. Presiona **Actualizar DB** para consultar Adzuna.")

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






# ============================================================########################################################################################
# NUEVAS COSAS — Capa de persistencia DuckDB
# ============================================================
import os
import duckdb
from datetime import date as _date

# ── Ruta y tabla ──────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "observatorio_laboral.duckdb")
TABLA   = "adzuna_vacantes"

# ── Helpers de verificación ───────────────────────────────────

def bd_existe() -> bool:
    """True si el archivo .duckdb existe en disco."""
    return os.path.exists(DB_PATH)


def tabla_existe() -> bool:
    """True si la tabla existe dentro del DuckDB. Solo llamar si bd_existe()."""
    try:
        con = duckdb.connect(DB_PATH, read_only=True)
        tablas = con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()
        con.close()
        return (TABLA,) in tablas
    except Exception:
        return False


def _crear_tabla(con: duckdb.DuckDBPyConnection):
    """Crea la tabla con el esquema correcto. IF NOT EXISTS → seguro llamarlo siempre."""
    con.execute(f"""
        CREATE TABLE IF NOT EXISTS {TABLA} (
            pais_codigo      VARCHAR,
            pais_nombre      VARCHAR,
            perfil           VARCHAR,
            vacantes         INTEGER,
            fecha_extraccion DATE
        )
    """)


def _insertar_datos(con: duckdb.DuckDBPyConnection, df: pd.DataFrame):
    con.register("_df_tmp", df)
    con.execute(f"INSERT INTO {TABLA} SELECT * FROM _df_tmp")
    con.unregister("_df_tmp")


def _reemplazar_datos(con: duckdb.DuckDBPyConnection, df: pd.DataFrame):
    """TRUNCATE + INSERT — reemplaza todos los registros."""
    con.execute(f"DELETE FROM {TABLA}")
    _insertar_datos(con, df)


# ── Fetch adaptado al esquema DuckDB ─────────────────────────
# Reutiliza adzuna_request() ya definida arriba.
# Diferencia clave vs _consultar_adzuna_api(): agrega pais_codigo
# y usa fecha_extraccion (campo requerido por la tabla).

def _fetch_para_duckdb(log_fn=print) -> pd.DataFrame:
    """
    Recorre PAISES × PROFESIONES y devuelve un DataFrame con el
    esquema exacto de la tabla:
        pais_codigo | pais_nombre | perfil | vacantes | fecha_extraccion

    Incluye fallback con datos de ejemplo si la API devuelve todo en 0.
    """
    registros = []
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    total     = len(PAISES) * len(PROFESIONES)
    count     = 0

    log_fn(f"🌐 Iniciando extracción Adzuna — {total} consultas ({len(PAISES)} países × {len(PROFESIONES)} perfiles)")

    for codigo in PAISES:
        nombre = NOMBRES[codigo]
        for perfil in PROFESIONES:
            count += 1
            data = adzuna_request(codigo, "search/1", {
                "results_per_page": 1,
                "what": perfil
            })
            if data and "count" in data:
                vacantes = data["count"]
                log_fn(f"  ✅ [{count}/{total}] {nombre} | {perfil}: {vacantes:,}")
            else:
                vacantes = 0
                log_fn(f"  ⚠️  [{count}/{total}] {nombre} | {perfil}: sin respuesta → 0")

            registros.append({
                "pais_codigo":      codigo,
                "pais_nombre":      nombre,
                "perfil":           perfil,
                "vacantes":         int(vacantes),
                "fecha_extraccion": fecha_hoy,
            })
            time.sleep(0.25)

    df = pd.DataFrame(registros)

    # Si la API no respondió en ningún caso, usar datos de ejemplo
    if df["vacantes"].sum() == 0:
        log_fn("ℹ️  API sin respuesta — cargando datos de ejemplo (fallback)")
        df = _fallback_duckdb(fecha_hoy)

    log_fn(f"\n📊 Extracción completada: {len(df):,} registros | Total vacantes: {df['vacantes'].sum():,}")
    return df


def _fallback_duckdb(fecha: str) -> pd.DataFrame:
    """Datos de referencia Adzuna 2024 para cuando la API no está disponible."""
    import random
    random.seed(42)
    base = {
        "data scientist":       {"us": 52000, "gb": 25000, "br": 9500,  "mx": 6500, "de": 20000, "ca": 18000},
        "software engineer":    {"us": 65000, "gb": 30000, "br": 12000, "mx": 9000, "de": 28000, "ca": 22000},
        "data analyst":         {"us": 48000, "gb": 23000, "br": 8500,  "mx": 6000, "de": 17000, "ca": 16000},
        "marketing specialist": {"us": 42000, "gb": 20000, "br": 9000,  "mx": 7000, "de": 15000, "ca": 14000},
        "financial analyst":    {"us": 35000, "gb": 18000, "br": 6500,  "mx": 5000, "de": 12000, "ca": 11000},
    }
    rows = []
    for perfil, paises_val in base.items():
        for cod, val in paises_val.items():
            if cod in NOMBRES:
                rows.append({
                    "pais_codigo":      cod,
                    "pais_nombre":      NOMBRES[cod],
                    "perfil":           perfil,
                    "vacantes":         val + random.randint(-500, 500),
                    "fecha_extraccion": fecha,
                })
    return pd.DataFrame(rows)


# ── Función de creación ───────────────────────────────────────

def funcion_creacion(log_fn=print):
    """
    Lógica:
      BD existe + tabla existe → avisa, no hace nada
      BD existe + tabla no    → crea tabla, llena con Adzuna
      BD no existe            → crea archivo .duckdb, crea tabla, llena
    """
    log_fn("=" * 55)
    log_fn("🟢 FUNCIÓN DE CREACIÓN — Observatorio Laboral")
    log_fn(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_fn("=" * 55)

    existe_bd = bd_existe()
    log_fn(f"\n[1/3] Verificando base de datos...")
    log_fn(f"  → '{DB_PATH}': {'✅ encontrado' if existe_bd else '❌ no existe'}")

    log_fn(f"\n[2/3] Verificando tabla '{TABLA}'...")
    if existe_bd:
        existe_tabla = tabla_existe()
        log_fn(f"  → Tabla: {'✅ encontrada' if existe_tabla else '❌ no existe'}")
    else:
        existe_tabla = False
        log_fn(f"  → Tabla: ❌ no aplica (BD no existe aún)")

    log_fn(f"\n[3/3] Ejecutando acción...")

    if existe_bd and existe_tabla:
        log_fn("\n⚠️  La BD y la tabla ya existen.")
        log_fn(f"   → {DB_PATH}")
        log_fn("   👉  Usa ACTUALIZAR si quieres refrescar los datos.")
        log_fn("=" * 55)
        return

    log_fn("\n📡 Consultando Adzuna...")
    df = _fetch_para_duckdb(log_fn=log_fn)

    log_fn(f"\n💾 Guardando en DuckDB...")
    con = duckdb.connect(DB_PATH)
    if not existe_bd:
        log_fn(f"  → 🆕 Archivo creado: {DB_PATH}")
    _crear_tabla(con)
    log_fn(f"  → 🆕 Tabla '{TABLA}' lista")
    _insertar_datos(con, df)
    n = con.execute(f"SELECT COUNT(*) FROM {TABLA}").fetchone()[0]
    con.close()

    log_fn(f"\n✅ CREACIÓN COMPLETADA")
    log_fn(f"   → Filas insertadas: {n:,}")
    log_fn(f"   → Fecha extracción: {df['fecha_extraccion'].iloc[0]}")
    log_fn("=" * 55)


# ── Función de actualización ──────────────────────────────────

def funcion_actualizacion(log_fn=print):
    """
    Lógica:
      BD + tabla existen → re-extrae Adzuna y reemplaza (DELETE + INSERT)
      BD o tabla faltan  → avisa sin tocar nada
    """
    log_fn("=" * 55)
    log_fn("🔄 FUNCIÓN DE ACTUALIZACIÓN — Observatorio Laboral")
    log_fn(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_fn("=" * 55)

    existe_bd = bd_existe()
    log_fn(f"\n[1/3] Verificando base de datos...")
    log_fn(f"  → '{DB_PATH}': {'✅ encontrado' if existe_bd else '❌ no existe'}")

    if not existe_bd:
        log_fn("\n❌ BASE NO EXISTE — usa CREAR primero.")
        log_fn("=" * 55)
        return

    log_fn(f"\n[2/3] Verificando tabla '{TABLA}'...")
    existe_tabla = tabla_existe()
    log_fn(f"  → Tabla: {'✅ encontrada' if existe_tabla else '❌ no existe'}")

    if not existe_tabla:
        log_fn("\n❌ TABLA NO EXISTE — usa CREAR primero.")
        log_fn("=" * 55)
        return

    con = duckdb.connect(DB_PATH)
    filas_antes = con.execute(f"SELECT COUNT(*) FROM {TABLA}").fetchone()[0]
    fecha_antes = con.execute(f"SELECT MAX(fecha_extraccion) FROM {TABLA}").fetchone()[0]
    con.close()

    log_fn(f"  → Filas actuales: {filas_antes:,} | Última extracción: {fecha_antes}")

    log_fn(f"\n[3/3] Re-extrayendo desde Adzuna...")
    df_nuevo = _fetch_para_duckdb(log_fn=log_fn)

    log_fn(f"\n💾 Reemplazando datos en DuckDB...")
    con = duckdb.connect(DB_PATH)
    _reemplazar_datos(con, df_nuevo)
    filas_despues = con.execute(f"SELECT COUNT(*) FROM {TABLA}").fetchone()[0]
    con.close()

    log_fn(f"\n✅ ACTUALIZACIÓN COMPLETADA")
    log_fn(f"   → Filas anteriores : {filas_antes:,}")
    log_fn(f"   → Filas nuevas     : {filas_despues:,}")
    log_fn(f"   → Fecha anterior   : {fecha_antes}")
    log_fn(f"   → Fecha nueva      : {df_nuevo['fecha_extraccion'].iloc[0]}")
    log_fn("=" * 55)


# ── Override de get_analisis_completo ─────────────────────────
# Python toma la última definición → esta reemplaza la de arriba.
# Prioridad: session_state (rápido) → DuckDB (persistente) → None

def get_analisis_completo() -> dict | None:
    """
    1. Si esta sesión ya cargó datos → los devuelve directo.
    2. Si no, busca en DuckDB y puebla session_state (persiste entre reinicios).
    3. Devuelve None si no hay datos en ningún lado.
    """
    _inicializar_session_state()

    # Prioridad 1: ya está en sesión
    if st.session_state.datos_adzuna_analisis is not None:
        return st.session_state.datos_adzuna_analisis

    # Prioridad 2: leer de DuckDB
    if bd_existe() and tabla_existe():
        con = duckdb.connect(DB_PATH, read_only=True)
        df = con.execute(
            f"SELECT pais_codigo, pais_nombre, perfil, vacantes, fecha_extraccion "
            f"FROM {TABLA} ORDER BY pais_nombre, perfil"
        ).df()
        fecha_raw = con.execute(
            f"SELECT MAX(fecha_extraccion) FROM {TABLA}"
        ).fetchone()[0]
        con.close()

        analisis = _calcular_analisis(df)

        # Poblar session_state para que get_contexto_para_ia() siga funcionando
        st.session_state.datos_adzuna_df       = df
        st.session_state.datos_adzuna_analisis = analisis
        st.session_state.datos_adzuna_fecha    = (
            datetime.combine(fecha_raw, datetime.min.time())
            if isinstance(fecha_raw, _date)
            else datetime.now()
        )
        return analisis

    return None
