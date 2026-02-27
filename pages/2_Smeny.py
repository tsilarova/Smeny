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

st.title("📅 Směny")

# ---------------------------------------------------------
# PŘIPOJENÍ KE GOOGLE SHEETS
# ---------------------------------------------------------
# Očekává se soubor service_account.json v rootu projektu
SHEET_NAME_MAIN = "Data 2026"   # hlavní zdroj dat
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def get_gspread_client():
    creds = Credentials.from_service_account_file(
        "service_account.json",
        scopes=SCOPES
    )
    return gspread.authorize(creds)

@st.cache_data(show_spinner=False)
def load_raw_data():
    gc = get_gspread_client()
    sh = gc.open_by_key("1svPbIAItWRAw8XdKFhbC50Qns8CN56Wc")  # tvůj sheet
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
    """
    Čte list 'Data 2026' a podle mapování:
    - Jméno       -> K
    - Počet osob  -> L
    - Datum       -> E nebo G (podle toho, co odpovídá filtru)
    - Příjezd     -> F (pokud E = vybrané datum)
    - Přílet      -> H (pokud G = vybrané datum)
    - Číslo letu  -> D (při E) nebo I (při G)
    - SPZ         -> N
    - Klíče       -> zatím prázdné (X se zadává z webu)
    - Poznámka    -> O + Q (čtení)
    - Vyřízeno    -> False (checkbox)
    - Směna       -> prázdné (zadává se z webu)
    """
    rows = load_raw_data()
    if not rows:
        return pd.DataFrame()

    data_rows = rows[1:]  # bez hlavičky

    records = []

    for r in data_rows:
        # Ošetření délky řádku
        r = r + [""] * (17 - len(r))

        # Mapování indexů (0-based)
        # D=3, E=4, F=5, G=6, H=7, I=8, K=10, L=11, N=13, O=14, P=15, Q=16
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

        # Příjezd (E/F/D)
        if date_from == selected_date:
            rec = {
                "Jméno": name,
                "Počet osob": persons,
                "Datum": selected_date.strftime("%d.%m.%Y"),
                "Příjezd": arrival,
                "Přílet": "",
                "Číslo letu": flight_no_from,
                "SPZ": spz,
                "Klíče": "",
                "Poznámka": " | ".join(
                    [x for x in [note_o, note_q] if x.strip()]
                ),
                "Vyřízeno": False,
                "Směna": ""
            }
            records.append(rec)

        # Přílet (G/H/I)
        if date_to == selected_date:
            rec = {
                "Jméno": name,
                "Počet osob": persons,
                "Datum": selected_date.strftime("%d.%m.%Y"),
                "Příjezd": "",
                "Přílet": flight_arrival,
                "Číslo letu": flight_no_to,
                "SPZ": spz,
                "Klíče": "",
                "Poznámka": " | ".join(
                    [x for x in [note_o, note_q] if x.strip()]
                ),
                "Vyřízeno": False,
                "Směna": ""
            }
            records.append(rec)

    if not records:
        return pd.DataFrame(
            columns=[
                "Jméno", "Počet osob", "Datum", "Příjezd", "Přílet",
                "Číslo letu", "SPZ", "Klíče", "Poznámka", "Vyřízeno", "Směna"
            ]
        )

    df = pd.DataFrame(records)
    return df


# ---------------------------------------------------------
# VYTVOŘENÍ "TISKOVÉHO" DATAFRAME S HLAVIČKAMI SMĚN
# ---------------------------------------------------------
def build_printable_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Vloží řádek s hlavičkou vždy nad každou další směnu (kromě první),
    pokud je ve sloupci 'Směna' vyplněno jméno.
    """
    if df.empty:
        return df

    cols = list(df.columns)
    out_rows = []

    first_shift = True

    for _, row in df.iterrows():
        shift_name = str(row.get("Směna", "") or "").strip()

        if shift_name:
            if not first_shift:
                # vložíme hlavičku
                header_row = {c: c for c in cols}
                out_rows.append(header_row)
            first_shift = False

        out_rows.append(row.to_dict())

    printable_df = pd.DataFrame(out_rows, columns=cols)
    return printable_df


# ---------------------------------------------------------
# ULOŽENÍ DO LISTU S NÁZVEM DD.MM.RRRR
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

    # Připravíme tiskovou verzi s hlavičkami směn
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
        "Vyřízeno": st.column_config.CheckboxColumn(
            label="Vyřízeno",
            help="Zaškrtnuté = hotovo"
        ),
        "Klíče": st.column_config.SelectboxColumn(
            label="Klíče",
            options=["", "X"],
            help="X = klíče jsou v kanceláři"
        ),
        "Směna": st.column_config.TextColumn(
            label="Směna",
            help="Jméno směny (např. Pavel, Blaženka...)"
        )
    }
)

with col_buttons:
    save_clicked = st.button("💾 Uložit směnu do listu s datem", type="primary")
    print_clicked = st.button("🖨️ Tisk", help="Otevře dialog pro tisk stránky")

if save_clicked:
    save_snapshot_sheet(selected_date, edited_df)
    st.success(f"Směna byla uložena do listu '{selected_date.strftime('%d.%m.%Y')}'.")

# Jednoduché tlačítko pro tisk – prohlížečové window.print()
if print_clicked:
    st.markdown(
        """
        <script>
        window.print();
        </script>
        """,
        unsafe_allow_html=True
    )
