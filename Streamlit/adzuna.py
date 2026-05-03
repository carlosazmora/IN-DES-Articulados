# Streamlit/adzuna.py
import requests
import pandas as pd
import time
from datetime import datetime
import os

# ==================== CONFIG ====================
APP_ID = "aa4dc3a4"
APP_KEY = "ec8882a52bf119f4e787ef6d92256f86"
BASE_URL = "https://api.adzuna.com/v1/api/jobs"

PAISES = ["us", "ca", "br", "mx", "gb"]
NOMBRES = {"us": "EE.UU.", "ca": "Canadá", "br": "Brasil", "mx": "México", "gb": "Reino Unido"}

# ==================== FUNCIONES ====================
def adzuna_request(pais: str, endpoint: str, params: dict = None):
    url = f"{BASE_URL}/{pais}/{endpoint}"
    p = {"app_id": APP_ID, "app_key": APP_KEY, **(params or {})}
    try:
        r = requests.get(url, params=p, timeout=15)
        if r.status_code == 200:
            return r.json()
        else:
            print(f"Error {r.status_code} en {pais}")
            return None
    except Exception as e:
        print(f"Error conexión {pais}: {e}")
        return None


@st.cache_data(ttl=3600)  # Cache por 1 hora
def cargar_datos_adzuna():
    """Carga los datos principales (puedes expandir)"""
    registros = []
    
    for pais in PAISES:
        # Ejemplo: demanda por perfil
        perfiles = ["data scientist", "software engineer", "data analyst", 
                   "machine learning engineer", "project manager"]
        
        for perfil in perfiles:
            data = adzuna_request(pais, "search/1", {
                "results_per_page": 1,
                "what": perfil
            })
            if data:
                registros.append({
                    "pais": pais,
                    "pais_nombre": NOMBRES[pais],
                    "perfil": perfil,
                    "vacantes": data.get("count", 0),
                    "fecha": datetime.now().date()
                })
            time.sleep(0.3)
    
    df = pd.DataFrame(registros)
    return df