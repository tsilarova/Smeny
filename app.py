import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ---------------------------------------------------------------
# ZÁKLADNÍ NASTAVENÍ STRÁNKY
# ---------------------------------------------------------------
st.set_page_config(
    page_title="Směny",
    layout="wide"
)

st.title("📅 Směny — Hlavní stránka")

# ---------------------------------------------------------------
# KONSTANTY
# ---------------------------------------------------------------
GOOGLE_SHEET_ID = "1jeKeW4pXde8ECc8PGwrfOU2GfujNXEozlzurlThxvpU"
SHEET_NAME_MAIN = "Data 2026"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ---------------------------------------------------------------
# FUNKCE PRO PŘIPOJENÍ KE GOOGLE SHEETS
# ---------------------------------------------------------------
def get_gspread_client():
    service_account_info = st.secrets["service_account"]
    creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    return gspread.authorize(creds)

# ---------------------------------------------------------------
# NAČTENÍ DAT Z GOOGLE SHEETS
# ---------------------------------------------------------------
@st.cache_data
def load_raw_data():
    # změna kvůli resetu cache v2
    gc = get_gspread_client()
    sh = gc.open_by_key(GOOGLE_SHEET_ID)
    worksheet = sh.worksheet(SHEET_NAME_MAIN)
    rows = worksheet.get_all_records()
    return rows

def load_data_for_date(selected_date):
    rows = load_raw_data()
    df = pd.DataFrame(rows)

    # převod datumu na datetime
    df["datumodletu"] = pd.to_datetime(df["datumodletu"], errors="coerce")

    # filtrování podle vybraného data
    df_filtered = df[df["datumodletu"] == pd.to_datetime(selected_date)]
    return df_filtered

# ---------------------------------------------------------------
# UI — VÝBĚR DATUMU
# ---------------------------------------------------------------
selected_date = st.date_input("Vyber datum směny")

# ---------------------------------------------------------------
# ZOBRAZENÍ DAT (bez try/except, aby se ukázala skutečná chyba)
# ---------------------------------------------------------------
df = load_data_for_date(selected_date)
st.dataframe(df, use_container_width=True)
