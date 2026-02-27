import streamlit as st
import pandas as pd
import datetime
import gspread
from google.oauth2.service_account import Credentials

# ---------------------------------------------------------
# ZÁKLADNÍ NASTAVENÍ STRÁNKY
# ---------------------------------------------------------
st.set_page_config(
    page_title="Směny",
    layout="wide"
)

st.title("📅 Směny – Hlavní stránka")

# ---------------------------------------------------------
# PŘIPOJENÍ KE GOOGLE SHEETS (přes Secrets)
# ---------------------------------------------------------
SHEET_NAME_MAIN = "Data 2026"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_gspread_client():
    service_account_info = st.secrets["service_account"]
    creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
    return gspread.authorize(creds)

@st.cache_data(show_spinner=False)
def load_raw_data():
    gc = get_gspread_client()
    sh = gc.open_by_key("1jeKeW4pXde8ECc8PGwrfOU2GfujNXEozlzurlThxvpU")
    ws = sh.worksheet(SHEET_NAME_MAIN)
    rows = ws.get_all_values()
    return rows

def parse_date(value: str):
    value = value.strip()
    if not value:
        return None
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None

# ---------------------------------------------------------
# NAČTENÍ DAT PRO KONKRÉTNÍ DEN
# ---------------------------------------------------------
def load_data_for_date(selected_date: datetime.date) -> pd.DataFrame:
    rows = load_raw_data()
    if not rows:
        return pd.DataFrame()

    data_rows = rows[1:]
    records = []

    for r in data_rows:
        r = r + [""] * (17 - len(r))

        name = r[10]
        persons = r[11]
        date_from = parse_date(r[4])
        date_to = parse_date(r[6])
        arrival = r[5]
        flight_arrival = r[7]
        flight_no_from = r[3]
        flight_no_to = r[8]
        spz = r[13]
        note_o = r[14]
        note_q = r[16]

        if date_from == selected_date:
            records.append({
                "Jméno": name,
                "Počet osob": persons,
                "Datum": selected_date.strftime("%d.%m.%Y"),
                "Příjezd": arrival,
                "Přílet": "",
                "Číslo letu": flight_no_from,
                "SPZ": spz,
                "Klíče": "",
                "Poznámka": " | ".join([x for x in [note_o, note_q] if x.strip()]),
                "Vyřízeno": False,
                "Směna": ""
            })

        if date_to == selected_date:
            records.append({
                "Jméno": name,
                "Počet osob": persons,
                "Datum": selected_date.strftime("%d.%m.%Y"),
                "Příjezd": "",
                "Přílet": flight_arrival,
                "Číslo letu": flight_no_to,
                "SPZ": spz,
                "Klíče": "",
                "Poznámka": " | ".join([x for x in [note_o, note_q] if x.strip()]),
                "Vyřízeno": False,
                "Směna": ""
            })

    if not records:
        return pd.DataFrame(columns=[
            "Jméno", "Počet osob", "Datum", "Příjezd", "Přílet",
            "Číslo letu", "SPZ", "Klíče", "Poznámka", "Vyřízeno", "Směna"
        ])

    return pd.DataFrame(records)

# ---------------------------------------------------------
# TISKOVÁ VERZE
# ---------------------------------------------------------
def build_printable_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    cols = list(df.columns)
    out_rows = []
    first_shift = True

    for _, row in df.iterrows():
        shift_name = str(row.get("Směna", "") or "").strip()

        if shift_name:
            if not first_shift:
                out_rows.append({c: c for c in cols})
            first_shift = False

        out_rows.append(row.to_dict())

    return pd.DataFrame(out_rows, columns=cols)

# ---------------------------------------------------------
# ULOŽENÍ DO LISTU S DATEM
# ---------------------------------------------------------
def save_snapshot_sheet(selected_date: datetime.date, df: pd.DataFrame):
    gc = get_gspread_client()
    sh = gc.open_by_key("1svPbIAItWRAw8XdKFhbC50Qns8CN56Wc")

    title = selected_date.strftime("%d.%m.%Y")

    try:
        ws = sh.worksheet(title)
        ws.clear()
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=title, rows=str(len(df) + 10), cols="20")

    printable_df = build_printable_df(df)
    values = [list(printable_df.columns)] + printable_df.astype(str).values.tolist()
    ws.update(values)

# ---------------------------------------------------------
# UI – FILTR PODLE DATA
# ---------------------------------------------------------
col_date, col_buttons = st.columns([1, 2])

with col_date:
    selected_date = st.date_input("Vyber datum směny", datetime.date.today())

if selected_date is None:
    st.stop()

df = load_data_for_date(selected_date)

if df.empty:
    st.info("Pro zvolené datum nejsou v listu 'Data 2026' žádné záznamy.")
    st.stop()

st.subheader("Přehled směny")

edited_df = st.data_editor(
    df,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Vyřízeno": st.column_config.CheckboxColumn(label="Vyřízeno"),
        "Klíče": st.column_config.SelectboxColumn(label="Klíče", options=["", "X"]),
        "Směna": st.column_config.TextColumn(label="Směna")
    }
)

with col_buttons:
    save_clicked = st.button("💾 Uložit směnu do listu s datem", type="primary")
    print_clicked = st.button("🖨️ Tisk")

if save_clicked:
    save_snapshot_sheet(selected_date, edited_df)
    st.success(f"Směna byla uložena do listu '{selected_date.strftime('%d.%m.%Y')}'.")

if print_clicked:
    st.markdown("<script>window.print();</script>", unsafe_allow_html=True)
