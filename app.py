import os
import calendar
import datetime
from io import BytesIO
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from supabase import create_client
from fpdf import FPDF

# --- STREAMLIT CONFIG & FINTECH REVOLUT UI ---
st.set_page_config(
    page_title="Executive Wealth Engine",
    layout="centered",
    page_icon="💳",
    initial_sidebar_state="collapsed",
)

# --- CONSTANTS (single source of truth, was duplicated 3x before) ---
CATEGORIES = [
    "Σούπερ Μάρκετ", "Λογαριασμοί/Σπίτι", "Καύσιμα/Μεταφορές",
    "Φαγητό/Καφές", "Ψυχαγωγία", "Μισθός", "Σταθερά Έξοδα", "Λοιπά",
]
MONTH_NAMES = [
    "Ιανουάριος", "Φεβρουάριος", "Μάρτιος", "Απρίλιος", "Μάιος", "Ιούνιος",
    "Ιούλιος", "Αύγουστος", "Σεπτέμβριος", "Οκτώβριος", "Νοέμβριος", "Δεκέμβριος",
]
MONTHS_EN = {
    "Ιανουάριος": "January", "Φεβρουάριος": "February", "Μάρτιος": "March",
    "Απρίλιος": "April", "Μάιος": "May", "Ιούνιος": "June",
    "Ιούλιος": "July", "Αύγουστος": "August", "Σεπτέμβριος": "September",
    "Οκτώβριος": "October", "Νοέμβριος": "November", "Δεκέμβριος": "December",
}

# --- CUSTOM CSS (APPLE PRO DARK METALLIC LIQUID TEXTURE + 3D CLAYMORPHISM ICONS) ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Inter', sans-serif;
    }

    .stApp {
        background-color: #08090c;
        background-image:
            radial-gradient(at 0% 0%, rgba(30, 36, 50, 0.4) 0px, transparent 50%),
            radial-gradient(at 100% 100%, rgba(15, 18, 26, 0.8) 0px, transparent 50%),
            linear-gradient(135deg, #060709 0%, #0d1017 40%, #151a24 70%, #08090c 100%);
        background-attachment: fixed;
        background-size: cover;
        color: #ffffff;
    }

    .hero-container { text-align: center; padding: 15px 0 5px 0; }
    .hero-label {
        font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px;
        color: #8e94a5; font-weight: 600;
    }
    .hero-amount {
        font-size: 40px; font-weight: 800; color: #ffffff;
        letter-spacing: -1.5px; margin-top: 2px;
        text-shadow: 0 4px 20px rgba(0,0,0,0.6);
    }

    div[data-baseweb="tab-list"] {
        gap: 6px; background: rgba(22, 26, 36, 0.65);
        backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
        padding: 6px; border-radius: 30px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        margin-bottom: 20px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }
    button[data-baseweb="tab"] {
        border-radius: 20px !important; padding: 8px 16px !important;
        font-size: 13px !important; font-weight: 600 !important;
        color: #9aa0b4 !important; border: none !important;
        background: transparent !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    button[aria-selected="true"] {
        background: rgba(255, 255, 255, 0.95) !important;
        color: #08090c !important;
        box-shadow: 0 4px 16px rgba(255, 255, 255, 0.2) !important;
    }

    div[data-testid="metric-container"], div[data-testid="stExpander"] {
        background: rgba(22, 26, 36, 0.55) !important;
        backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        padding: 16px; border-radius: 20px !important;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }

    .stButton>button {
        background: #ffffff; color: #08090c; border: none;
        border-radius: 30px; font-weight: 700; padding: 8px 16px;
        box-shadow: 0 4px 12px rgba(255, 255, 255, 0.15);
        transition: transform 0.2s ease;
    }
    .stButton>button:hover {
        background: #e5e5ea; color: #08090c; transform: scale(1.02);
    }

    /* --- 3D CLAYMORPHISM SECTION ICONS (matches dark metallic theme) --- */
    .clay-header { display: flex; align-items: center; gap: 14px; margin: 4px 0 18px 0; }
    .clay-icon {
        width: 52px; height: 52px; min-width: 52px; border-radius: 18px;
        display: flex; align-items: center; justify-content: center;
        font-size: 24px;
        background: linear-gradient(145deg, #262c3a, #14161d);
        box-shadow:
            6px 6px 14px rgba(0,0,0,0.55),
            -4px -4px 10px rgba(255,255,255,0.04),
            inset 1px 1px 2px rgba(255,255,255,0.08),
            inset -2px -2px 6px rgba(0,0,0,0.5);
        border: 1px solid rgba(255,255,255,0.06);
    }
    .clay-icon.accent-green   { background: linear-gradient(145deg, #2a5b3f, #163021); }
    .clay-icon.accent-red     { background: linear-gradient(145deg, #5b2a2e, #301619); }
    .clay-icon.accent-blue    { background: linear-gradient(145deg, #204a68, #10253a); }
    .clay-icon.accent-purple  { background: linear-gradient(145deg, #4a2a5e, #221230); }
    .clay-icon.accent-gold    { background: linear-gradient(145deg, #5e4f1f, #2e2610); }

    .clay-title { font-size: 19px; font-weight: 800; letter-spacing: -0.3px; color: #fff; }
    .clay-subtitle { font-size: 12.5px; color: #8e94a5; margin-top: 2px; }

    /* --- FORCE DARK, READABLE INPUT WIDGETS ON EVERY DEVICE ---
       Without this, Streamlit's BaseWeb widgets fall back to the device's own
       light/dark preference. Desktop browsers were often in dark mode (so it
       looked fine "by accident"), but mobile browsers default to light mode,
       producing gray/white text on a white or near-white input background. */

    /* Text / number inputs */
    .stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea {
        background-color: #161a24 !important;
        color: #ffffff !important;
        border: 1px solid rgba(255,255,255,0.14) !important;
        border-radius: 12px !important;
        -webkit-text-fill-color: #ffffff !important;
    }
    .stTextInput input::placeholder, .stNumberInput input::placeholder, .stTextArea textarea::placeholder {
        color: #8e94a5 !important;
        opacity: 1 !important;
    }
    /* Number input +/- step buttons */
    button[data-testid="stNumberInputStepUp"], button[data-testid="stNumberInputStepDown"] {
        background-color: #161a24 !important;
        border-color: rgba(255,255,255,0.14) !important;
    }
    button[data-testid="stNumberInputStepUp"] svg, button[data-testid="stNumberInputStepDown"] svg {
        fill: #ffffff !important;
    }

    /* Selectbox (closed state) */
    div[data-baseweb="select"] > div {
        background-color: #161a24 !important;
        border-color: rgba(255,255,255,0.14) !important;
        color: #ffffff !important;
    }
    div[data-baseweb="select"] span, div[data-baseweb="select"] div {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }
    div[data-baseweb="select"] svg { fill: #ffffff !important; }

    /* Selectbox / dropdown menu popover (renders in a portal, needs its own rule) */
    ul[data-baseweb="menu"], div[data-baseweb="popover"] {
        background-color: #161a24 !important;
    }
    li[role="option"] { color: #ffffff !important; background-color: transparent !important; }
    li[role="option"]:hover, li[aria-selected="true"] { background-color: rgba(255,255,255,0.10) !important; }

    /* Date picker calendar popover */
    div[data-baseweb="calendar"], div[data-baseweb="calendar"] * {
        background-color: #161a24 !important;
        color: #ffffff !important;
    }

    /* Labels above every widget */
    .stTextInput label, .stNumberInput label, .stSelectbox label,
    .stDateInput label, .stTextArea label, .stCheckbox label p {
        color: #c7cad1 !important;
    }

    /* Checkbox text + box */
    .stCheckbox p { color: #ffffff !important; }
    </style>
""",
    unsafe_allow_html=True,
)


def clay_header(icon: str, title: str, subtitle: str = "", accent: str = "") -> None:
    """Renders a 3D claymorphism icon badge + title, matching the app's dark metallic look.
    NOTE: built as a single-line string on purpose - an indented multiline f-string here
    gets parsed by Streamlit's Markdown engine as a code block (4+ leading spaces = code
    block in CommonMark), which is what caused stray "</div>" text to render on screen."""
    accent_class = f"accent-{accent}" if accent else ""
    subtitle_html = f'<div class="clay-subtitle">{subtitle}</div>' if subtitle else ""
    html = (
        f'<div class="clay-header">'
        f'<div class="clay-icon {accent_class}">{icon}</div>'
        f'<div><div class="clay-title">{title}</div>{subtitle_html}</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


# --- GREEK → LATIN TRANSLITERATION (fallback for PDF export without a unicode font) ---
_GREEK_MAP = {
    "Α": "A", "Β": "V", "Γ": "G", "Δ": "D", "Ε": "E", "Ζ": "Z", "Η": "I", "Θ": "Th",
    "Ι": "I", "Κ": "K", "Λ": "L", "Μ": "M", "Ν": "N", "Ξ": "X", "Ο": "O", "Π": "P",
    "Ρ": "R", "Σ": "S", "Τ": "T", "Υ": "Y", "Φ": "F", "Χ": "Ch", "Ψ": "Ps", "Ω": "O",
    "α": "a", "β": "v", "γ": "g", "δ": "d", "ε": "e", "ζ": "z", "η": "i", "θ": "th",
    "ι": "i", "κ": "k", "λ": "l", "μ": "m", "ν": "n", "ξ": "x", "ο": "o", "π": "p",
    "ρ": "r", "σ": "s", "ς": "s", "τ": "t", "υ": "y", "φ": "f", "χ": "ch", "ψ": "ps",
    "ω": "o",
    # Accented/tonos variants (both cases) - these were missing before and were the
    # direct cause of the "Character outside range of helvetica" crash, since words
    # like "Έξοδο" / "Έσοδο" start with an accented capital that fell through untouched.
    "ά": "a", "έ": "e", "ή": "i", "ί": "i", "ό": "o", "ύ": "y", "ώ": "o",
    "Ά": "A", "Έ": "E", "Ή": "I", "Ί": "I", "Ό": "O", "Ύ": "Y", "Ώ": "O",
    "ϊ": "i", "ϋ": "y", "ΐ": "i", "ΰ": "y",
    "€": "EUR",
}


def transliterate_greek(text: str) -> str:
    """Transliterates Greek to Latin for the Helvetica PDF fallback. Any character that's
    neither ASCII nor in the map is swapped for '?' instead of passed through untouched -
    that guarantee is what prevents a repeat of the fpdf 'outside font range' crash for any
    character we didn't think to map."""
    out = []
    for ch in str(text):
        if ch in _GREEK_MAP:
            out.append(_GREEK_MAP[ch])
        elif ord(ch) < 128:
            out.append(ch)
        else:
            out.append("?")
    return "".join(out)


def _find_unicode_font() -> str | None:
    """Looks for a common DejaVu Sans install so the PDF can render real Greek text."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        os.path.join(os.path.dirname(__file__), "DejaVuSans.ttf") if "__file__" in globals() else None,
        "DejaVuSans.ttf",
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


# --- HELPER: UNICODE-AWARE PDF GENERATOR (fixes Greek text being silently dropped) ---
def create_pdf_report(month_name, year, income, expenses, balance, df_data):
    pdf = FPDF()
    pdf.add_page()

    font_path = _find_unicode_font()
    if font_path:
        pdf.add_font("DejaVu", "", font_path)
        pdf.add_font("DejaVu", "B", font_path)
        base_font = "DejaVu"
        display_month = month_name
        txt = lambda s: str(s) if s is not None else ""
    else:
        base_font = "Helvetica"
        display_month = MONTHS_EN.get(month_name, month_name)
        txt = lambda s: transliterate_greek(s) if s is not None else ""

    pdf.set_font(base_font, "B", 16)
    pdf.cell(0, 10, f"Executive Financial Statement - {display_month} {year}", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font(base_font, "", 12)
    pdf.cell(0, 8, f"Total Income: {income:,.2f} EUR", ln=True)
    pdf.cell(0, 8, f"Total Expenses: {expenses:,.2f} EUR", ln=True)
    pdf.set_font(base_font, "B", 12)
    pdf.cell(0, 8, f"Net Balance: {balance:,.2f} EUR", ln=True)
    pdf.ln(10)

    pdf.set_font(base_font, "B", 10)
    pdf.cell(30, 8, "Date", 1)
    pdf.cell(30, 8, "Type", 1)
    pdf.cell(45, 8, "Category", 1)
    pdf.cell(30, 8, "Amount", 1)
    pdf.cell(55, 8, "Note", 1)
    pdf.ln()

    pdf.set_font(base_font, "", 9)
    for _, row in df_data.iterrows():
        date_str = row["date"].strftime("%Y-%m-%d") if hasattr(row["date"], "strftime") else str(row["date"])
        safe_type = txt(row["type"]) or "N/A"
        safe_cat = txt(row["category"]) or "Category"
        note_val = row["note"] if pd.notna(row.get("note")) else ""
        safe_note = txt(note_val)

        pdf.cell(30, 7, date_str, 1)
        pdf.cell(30, 7, safe_type[:15], 1)
        pdf.cell(45, 7, safe_cat[:25], 1)
        pdf.cell(30, 7, f"{row['amount']:.2f} EUR", 1)
        pdf.cell(55, 7, safe_note[:30], 1)
        pdf.ln()

    return bytes(pdf.output())


# --- HELPER: EXCEL EXPORT ---
def create_excel_report(df_data: pd.DataFrame) -> bytes:
    """Requires 'openpyxl' in requirements.txt - pandas uses it as the .xlsx writer engine."""
    buffer = BytesIO()
    export_df = df_data.copy()
    export_df["date"] = pd.to_datetime(export_df["date"]).dt.strftime("%Y-%m-%d")
    export_df = export_df[["id", "date", "type", "category", "amount", "note"]]
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        export_df.to_excel(writer, index=False, sheet_name="Συναλλαγές")
    buffer.seek(0)
    return buffer.getvalue()


# --- SUPABASE CONNECTION ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except Exception as e:
    st.error(f"❌ Σφάλμα Secrets: {e}")
    st.stop()

# --- SECURITY / PIN LOCK WITH FINTECH IMAGE ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown(
        '<div style="text-align: center; padding-top: 25px;">'
        '<div style="width:120px; height:120px; margin:0 auto 18px auto; border-radius:28px; '
        'display:flex; align-items:center; justify-content:center; font-size:52px; '
        'background: linear-gradient(145deg, #262c3a, #14161d); '
        'box-shadow: 8px 8px 18px rgba(0,0,0,0.6), -4px -4px 10px rgba(255,255,255,0.04), '
        'inset 1px 1px 2px rgba(255,255,255,0.08), inset -2px -2px 6px rgba(0,0,0,0.5); '
        'border: 1px solid rgba(255,255,255,0.08);">💳</div>'
        '<h2 style="font-weight: 800; letter-spacing: -0.5px; margin-bottom: 4px;">Executive Wealth Engine</h2>'
        '<p style="color: #8e94a5; font-size: 14px;">Εισάγετε το PIN για ασφαλή πρόσβαση</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    col_login1, col_login2, col_login3 = st.columns([1, 2, 1])
    with col_login2:
        pin_input = st.text_input("PIN", type="password", label_visibility="collapsed")
        if st.button("🔓 Ξεκλείδωμα", use_container_width=True):
            if pin_input == st.secrets.get("APP_PIN", "1234"):
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("❌ Λανθασμένο PIN.")
    st.stop()


# --- CACHED DATA FETCH (was refetching on every rerun before; now cached + explicitly
#     invalidated after every write so the dashboard never shows stale numbers) ---
@st.cache_data(ttl=60, show_spinner=False)
def fetch_transactions():
    response = (
        supabase.table("transactions")
        .select("*")
        .order("date", desc=True)
        .execute()
    )
    return response.data


@st.cache_data(ttl=60, show_spinner=False)
def fetch_savings():
    """Reads from a separate 'savings' table - this is a genuinely different account,
    so it is never mixed into the main transactions/income-expense numbers."""
    response = (
        supabase.table("savings")
        .select("*")
        .order("date", desc=True)
        .execute()
    )
    return response.data


try:
    data = fetch_transactions()
    df = pd.DataFrame(data) if data else pd.DataFrame()
except Exception as err:
    st.error(f"🔍 Σφάλμα Supabase: {err}")
    df = pd.DataFrame()

if not df.empty:
    df["date"] = pd.to_datetime(df["date"])

try:
    savings_data = fetch_savings()
    savings_df = pd.DataFrame(savings_data) if savings_data else pd.DataFrame()
except Exception as err:
    st.error(f"🔍 Σφάλμα Supabase (Αποταμίευση): {err}")
    savings_df = pd.DataFrame()

if not savings_df.empty:
    savings_df["date"] = pd.to_datetime(savings_df["date"])


def refresh_and_rerun():
    """Clears the transactions cache so writes show up immediately, then reruns."""
    fetch_transactions.clear()
    st.rerun()


def refresh_savings_and_rerun():
    fetch_savings.clear()
    st.rerun()


# --- CENTRALIZED SESSION STATE DEFAULTS ---
# Streamlit re-runs every "with tab:" block on every rerun, top to bottom in the script,
# regardless of which tab is visually active. Previously "recurring"/"buckets"/etc. were
# only initialized inside their own tab, so a tab appearing earlier in the script (e.g.
# Cash Flow, which reads "recurring") would see missing state on the very first-ever load.
# Initializing everything here, before any tab runs, removes that class of bug.
if "recurring" not in st.session_state:
    st.session_state["recurring"] = [
        {"title": "Ενοίκιο", "amount": 450.0, "due_day": 1, "paid": False, "tx_id": None},
        {"title": "Internet / Κοινόχρηστα", "amount": 35.0, "due_day": 10, "paid": False, "tx_id": None},
        {"title": "Συνδρομές (Streaming)", "amount": 15.99, "due_day": 15, "paid": False, "tx_id": None},
    ]
else:
    for _item in st.session_state["recurring"]:
        _item.setdefault("paid", False)
        _item.setdefault("tx_id", None)

if "buckets" not in st.session_state:
    st.session_state["buckets"] = [
        {"name": "🚗 Συντήρηση Ι.Χ.", "current": 400.0, "target": 800.0},
        {"name": "🏖️ Διακοπές", "current": 1200.0, "target": 1500.0},
        {"name": "💻 Εξοπλισμός", "current": 300.0, "target": 1000.0},
    ]

if "checklist" not in st.session_state:
    st.session_state["checklist"] = [
        {"task": "Έλεγχος υπολοίπου τραπέζης", "done": False},
        {"task": "Καταχώρηση αποδείξεων εβδομάδας", "done": True},
        {"task": "Πληρωμή λογαριασμών", "done": False},
    ]

if "debts" not in st.session_state:
    st.session_state["debts"] = {"card_balance": 1500.0, "loan_balance": 8000.0}

if "category_budgets" not in st.session_state:
    st.session_state["category_budgets"] = {}  # {category: monthly_limit}

if "last_deleted" not in st.session_state:
    st.session_state["last_deleted"] = None


def stash_for_undo(kind: str, payload: dict) -> None:
    """Remembers the most recently deleted record so it can be restored with one click
    from the sidebar. Single-level undo (only the latest deletion) - simple and covers
    the common "oops" case without the complexity of a full undo stack."""
    st.session_state["last_deleted"] = {"kind": kind, "payload": payload}


def undo_last_delete() -> None:
    ld = st.session_state.get("last_deleted")
    if not ld:
        return
    kind, payload = ld["kind"], ld["payload"]
    try:
        if kind == "transaction":
            supabase.table("transactions").insert(payload).execute()
            fetch_transactions.clear()
        elif kind == "saving":
            supabase.table("savings").insert(payload).execute()
            fetch_savings.clear()
        elif kind == "bucket":
            st.session_state["buckets"].insert(payload["idx"], payload["item"])
        elif kind == "recurring":
            st.session_state["recurring"].insert(payload["idx"], payload["item"])
        elif kind == "checklist":
            st.session_state["checklist"].insert(payload["idx"], payload["item"])
        st.session_state["last_deleted"] = None
        st.toast("Η διαγραφή αναιρέθηκε.", icon="↩️")
        st.rerun()
    except Exception as e:
        st.error(f"Σφάλμα αναίρεσης: {e}")


def detect_recurring_candidates(tx_df: pd.DataFrame, existing_recurring: list) -> list:
    """Heuristic: an expense category+amount combo that shows up in 2+ distinct months
    is very likely a recurring bill, so it's surfaced as a one-click suggestion instead
    of asking the user to notice and re-type it into the Σταθερά tab themselves."""
    if tx_df.empty:
        return []
    exp = tx_df[tx_df["type"] == "Έξοδο"].copy()
    if exp.empty:
        return []
    exp["year_month"] = exp["date"].dt.to_period("M")
    exp["amount_r"] = exp["amount"].round(2)
    existing_titles = {r["title"].strip().lower() for r in existing_recurring}
    candidates = []
    for (cat, amt), g in exp.groupby(["category", "amount_r"]):
        months = g["year_month"].nunique()
        if months >= 2 and len(g) >= 2 and cat.strip().lower() not in existing_titles:
            avg_day = int(round(g["date"].dt.day.mean()))
            candidates.append({
                "title": cat, "amount": float(amt),
                "due_day": max(1, min(avg_day, 28)), "occurrences": int(months),
            })
    candidates.sort(key=lambda c: -c["occurrences"])
    return candidates


# --- SIDEBAR FILTERS ---
st.sidebar.header("🗓️ Περίοδος & Στόχοι")
now = datetime.datetime.now()
current_year = now.year
current_month = now.month

years = list(range(2024, current_year + 2))
selected_year = st.sidebar.selectbox("Έτος", years, index=years.index(current_year))
selected_month_name = st.sidebar.selectbox("Μήνας", MONTH_NAMES, index=current_month - 1)
selected_month = MONTH_NAMES.index(selected_month_name) + 1

monthly_budget = st.sidebar.number_input("Μηνιαίο Όριο (€)", min_value=0.0, value=1200.0, step=50.0)

with st.sidebar.expander("🎯 Προϋπολογισμοί ανά Κατηγορία"):
    st.caption("Βάλε 0 για να απενεργοποιήσεις το όριο μιας κατηγορίας.")
    for _cat in CATEGORIES:
        _current = st.session_state["category_budgets"].get(_cat, 0.0)
        _new = st.number_input(_cat, min_value=0.0, value=_current, step=10.0, key=f"catbudget_{_cat}")
        if _new != _current:
            if _new > 0:
                st.session_state["category_budgets"][_cat] = _new
            else:
                st.session_state["category_budgets"].pop(_cat, None)

if st.session_state.get("last_deleted"):
    _kind_labels = {
        "transaction": "συναλλαγή", "saving": "κίνηση αποταμίευσης",
        "bucket": "στόχο αποταμίευσης", "recurring": "σταθερό έξοδο", "checklist": "εργασία",
    }
    _kind = st.session_state["last_deleted"]["kind"]
    if st.sidebar.button(f"↩️ Αναίρεση διαγραφής ({_kind_labels.get(_kind, _kind)})", use_container_width=True):
        undo_last_delete()

if st.sidebar.button("🔒 Αποσύνδεση"):
    st.session_state["authenticated"] = False
    st.rerun()

# --- NAVIGATION TABS ---
(
    main_tab1, main_tab2, main_tab3, main_tab4, main_tab_savings,
    main_tab5, main_tab6, main_tab7, main_tab8,
) = st.tabs(
    [
        "👛 Dashboard", "🧭 Cash Flow", "🎯 Buckets", "📊 Ετήσια", "💰 Αποταμίευση",
        "⚙️ Σταθερά", "📋 Checklist", "🏦 Δάνεια", "📄 Εξαγωγή",
    ]
)

# ==========================================
# TAB 1: DASHBOARD
# ==========================================
with main_tab1:
    clay_header("👛", "Dashboard", f"Επισκόπηση για {selected_month_name} {selected_year}", accent="blue")

    if not df.empty:
        filtered_df = df[
            (df["date"].dt.year == selected_year) & (df["date"].dt.month == selected_month)
        ].copy()
        income = filtered_df.loc[filtered_df["type"] == "Έσοδο", "amount"].sum() if not filtered_df.empty else 0.0
        expenses = filtered_df.loc[filtered_df["type"] == "Έξοδο", "amount"].sum() if not filtered_df.empty else 0.0
        balance = income - expenses
    else:
        filtered_df = pd.DataFrame()
        income, expenses, balance = 0.0, 0.0, 0.0

    st.markdown(
        f'<div class="hero-container">'
        f'<div class="hero-label">Συνολικό Υπόλοιπο ({selected_month_name})</div>'
        f'<div class="hero-amount">{balance:,.2f} €</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if monthly_budget > 0:
        pct_used = (expenses / monthly_budget) * 100
        if pct_used >= 100:
            st.error(f"🚨 **Υπέρβαση Budget!** Έχεις καταναλώσει το {pct_used:.1f}% του ορίου ({expenses:.2f} / {monthly_budget:.2f}€).")
        elif pct_used >= 80:
            st.warning(f"⚠️ **Προσοχή:** Έχεις φτάσει το {pct_used:.1f}% του μηνιαίου ορίου.")

    # QUICK ADD
    q_col1, q_col2, q_col3 = st.columns(3)
    today_str = str(datetime.date.today())
    quick_adds = [
        (q_col1, "+ Καφές 2.50€", "Φαγητό/Καφές", 2.50, "Καφές", "☕"),
        (q_col2, "+ Βενζίνη 20€", "Καύσιμα/Μεταφορές", 20.00, "Βενζίνη", "⛽"),
        (q_col3, "+ Super 50€", "Σούπερ Μάρκετ", 50.00, "Supermarket", "🛒"),
    ]
    for col, label, category, amount, note, icon in quick_adds:
        with col:
            if st.button(label, use_container_width=True):
                try:
                    supabase.table("transactions").insert(
                        {"date": today_str, "category": category, "amount": amount,
                         "type": "Έξοδο", "note": f"Quick Add - {note}"}
                    ).execute()
                    st.toast(f"Προστέθηκε: {note} {amount:.2f}€", icon=icon)
                    refresh_and_rerun()
                except Exception as e:
                    st.error(f"Σφάλμα καταχώρησης: {e}")

    # MANUAL INPUT FORM
    with st.expander("➕ Πλήρης Καταγραφή Συναλλαγής", expanded=False):
        with st.form("entry_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                date = st.date_input("Ημερομηνία", datetime.date.today())
                t_type = st.selectbox("Τύπος", ["Έξοδο", "Έσοδο"])
                amount = st.number_input("Ποσό (€)", min_value=0.0, format="%.2f")
            with col2:
                category = st.selectbox("Κατηγορία", CATEGORIES)
                note = st.text_input("Σημείωση")

            if st.form_submit_button("Καταγραφή") and amount > 0:
                try:
                    supabase.table("transactions").insert(
                        {"date": str(date), "category": category, "amount": float(amount), "type": t_type, "note": note}
                    ).execute()
                    st.success("Καταχωρήθηκε!")
                    refresh_and_rerun()
                except Exception as e:
                    st.error(f"Σφάλμα καταχώρησης: {e}")

    # EDIT / DELETE SECTION
    with st.expander("✏️ Διορθώσεις & Διαγραφή Συναλλαγών", expanded=False):
        if not filtered_df.empty:
            tx_options = {
                row["id"]: f"ID {row['id']} | {row['date'].strftime('%Y-%m-%d')} | {row['category']} | {row['amount']:.2f}€ ({row['type']})"
                for _, row in filtered_df.iterrows()
            }
            selected_tx_id = st.selectbox("Επιλέξτε Συναλλαγή", list(tx_options.keys()), format_func=lambda x: tx_options[x])
            selected_row = filtered_df[filtered_df["id"] == selected_tx_id].iloc[0]

            with st.form("edit_form"):
                e_col1, e_col2 = st.columns(2)
                with e_col1:
                    edit_date = st.date_input("Νέα Ημερομηνία", pd.to_datetime(selected_row["date"]))
                    edit_type = st.selectbox("Νέος Τύπος", ["Έξοδο", "Έσοδο"], index=0 if selected_row["type"] == "Έξοδο" else 1)
                    edit_amount = st.number_input("Νέο Ποσό (€)", min_value=0.0, value=float(selected_row["amount"]), format="%.2f")
                with e_col2:
                    edit_cat_idx = CATEGORIES.index(selected_row["category"]) if selected_row["category"] in CATEGORIES else 0
                    edit_category = st.selectbox("Νέα Κατηγορία", CATEGORIES, index=edit_cat_idx)
                    edit_note = st.text_input("Νέα Σημείωση", value=str(selected_row["note"]) if pd.notna(selected_row["note"]) else "")

                btn_save, btn_delete = st.columns(2)
                with btn_save:
                    if st.form_submit_button("💾 Αποθήκευση"):
                        try:
                            supabase.table("transactions").update({
                                "date": str(edit_date), "category": edit_category,
                                "amount": float(edit_amount), "type": edit_type, "note": edit_note,
                            }).eq("id", selected_tx_id).execute()
                            st.success("Ενημερώθηκε!")
                            refresh_and_rerun()
                        except Exception as e:
                            st.error(f"Σφάλμα ενημέρωσης: {e}")
                with btn_delete:
                    if st.form_submit_button("🗑️ Διαγραφή"):
                        try:
                            undo_payload = {
                                "date": str(pd.to_datetime(selected_row["date"]).date()),
                                "category": selected_row["category"],
                                "amount": float(selected_row["amount"]),
                                "type": selected_row["type"],
                                "note": selected_row["note"] if pd.notna(selected_row["note"]) else "",
                            }
                            supabase.table("transactions").delete().eq("id", selected_tx_id).execute()
                            stash_for_undo("transaction", undo_payload)
                            st.warning("Διαγράφηκε! (Αναίρεση διαθέσιμη από το sidebar)")
                            refresh_and_rerun()
                        except Exception as e:
                            st.error(f"Σφάλμα διαγραφής: {e}")
        else:
            st.caption("Δεν υπάρχουν συναλλαγές για επεξεργασία αυτόν τον μήνα.")

    m1, m2 = st.columns(2)
    m1.metric("Έσοδα", f"+{income:,.2f} €")
    m2.metric("Έξοδα", f"-{expenses:,.2f} €")

    if not filtered_df.empty:
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            fig_compare = go.Figure(data=[
                go.Bar(name='Έσοδα', x=['Σύνολο'], y=[income], marker_color='#30d158'),
                go.Bar(name='Έξοδα', x=['Σύνολο'], y=[expenses], marker_color='#ff453a'),
            ])
            fig_compare.update_layout(
                barmode='group', template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=10, b=10, l=10, r=10), height=220,
            )
            st.plotly_chart(fig_compare, use_container_width=True)

        with chart_col2:
            df_exp = filtered_df[filtered_df["type"] == "Έξοδο"]
            if not df_exp.empty:
                cat_expenses = df_exp.groupby("category")["amount"].sum().reset_index()
                fig_pie = px.pie(
                    cat_expenses, values="amount", names="category", hole=0.6,
                    template="plotly_dark",
                    color_discrete_sequence=["#30d158", "#0a84ff", "#ff453a", "#ffd60a", "#bf5af2", "#8e8e93"],
                )
                fig_pie.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    showlegend=False, margin=dict(t=10, b=10, l=10, r=10), height=220,
                )
                st.plotly_chart(fig_pie, use_container_width=True)

        st.subheader("📜 Συναλλαγές")
        dash_search = st.text_input("🔎 Αναζήτηση (κατηγορία ή σημείωση)", key="dash_search")
        display_df = filtered_df.copy()
        if dash_search:
            _mask = (
                display_df["category"].str.contains(dash_search, case=False, na=False)
                | display_df["note"].astype(str).str.contains(dash_search, case=False, na=False)
            )
            display_df = display_df[_mask]
        display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
        st.dataframe(
            display_df[["id", "date", "type", "category", "amount", "note"]],
            use_container_width=True, hide_index=True,
        )

    # --- PER-CATEGORY BUDGETS ---
    active_budgets = {c: v for c, v in st.session_state.get("category_budgets", {}).items() if v > 0}
    if active_budgets:
        st.markdown("---")
        st.subheader("🎯 Προϋπολογισμοί ανά Κατηγορία")
        exp_by_cat = (
            filtered_df[filtered_df["type"] == "Έξοδο"].groupby("category")["amount"].sum()
            if not filtered_df.empty else pd.Series(dtype=float)
        )
        for cat, limit in active_budgets.items():
            spent = float(exp_by_cat.get(cat, 0.0))
            ratio = min(spent / limit, 1.0) if limit else 0.0
            st.caption(f"{cat}: {spent:,.2f} € / {limit:,.2f} €")
            st.progress(ratio)
            if spent > limit:
                st.warning(f"🚨 Υπέρβαση ορίου στην κατηγορία «{cat}» ({spent:,.2f} € / {limit:,.2f} €)")

    # --- ANOMALY DETECTION: flag categories spending well above their historical average ---
    if not df.empty:
        exp_all = df[df["type"] == "Έξοδο"].copy()
        if not exp_all.empty:
            exp_all["year_month"] = exp_all["date"].dt.to_period("M")
            current_period = pd.Period(year=selected_year, month=selected_month, freq="M")
            hist = exp_all[exp_all["year_month"] != current_period]
            if not hist.empty:
                months_seen = hist["year_month"].nunique()
                hist_avg = hist.groupby("category")["amount"].sum() / months_seen
                cur_spend = exp_all.loc[exp_all["year_month"] == current_period].groupby("category")["amount"].sum()
                anomalies = []
                for cat, cur_amt in cur_spend.items():
                    avg_amt = float(hist_avg.get(cat, 0.0))
                    # Ignore tiny amounts so a €3 vs €1 comparison doesn't get flagged as "3x"
                    if avg_amt > 0 and cur_amt >= avg_amt * 1.5 and (cur_amt - avg_amt) >= 10:
                        anomalies.append((cat, cur_amt / avg_amt, float(cur_amt), avg_amt))
                if anomalies:
                    st.markdown("---")
                    st.subheader("🔍 Ασυνήθιστα Έξοδα")
                    for cat, ratio, cur_amt, avg_amt in sorted(anomalies, key=lambda x: -x[1]):
                        st.warning(
                            f"Ξόδεψες **{ratio:.1f}x** πάνω από τον μέσο όρο σε «{cat}» αυτόν τον μήνα "
                            f"({cur_amt:,.2f} € έναντι μέσου όρου {avg_amt:,.2f} €/μήνα)."
                        )

# ==========================================
# TAB 2: CASH FLOW FORECASTING (+ NET WORTH)
# ==========================================
with main_tab2:
    clay_header("🧭", "Cash Flow Projection", "Πρόβλεψη βάσει ιστορικού μοτίβου + ανεξόφλητων σταθερών", accent="purple")

    upcoming_recurring_unpaid = sum(
        float(r["amount"]) for r in st.session_state["recurring"] if not r.get("paid", False)
    )

    # Historical-pattern forecast: extrapolate the rest of the month from how much you've
    # actually been spending per day so far, instead of just subtracting fixed bills.
    today = datetime.date.today()
    days_in_month = calendar.monthrange(selected_year, selected_month)[1]
    if selected_year == today.year and selected_month == today.month:
        days_elapsed = today.day
    else:
        days_elapsed = days_in_month  # a past/future month: nothing left to "extrapolate"
    days_remaining = max(days_in_month - days_elapsed, 0)

    daily_avg_expense = (expenses / days_elapsed) if days_elapsed > 0 else 0.0
    projected_additional_expenses = daily_avg_expense * days_remaining
    projected_balance = balance - upcoming_recurring_unpaid - projected_additional_expenses

    c_f1, c_f2, c_f3 = st.columns(3)
    c_f1.metric("Τρέχον Υπόλοιπο (μήνα)", f"{balance:,.2f} €")
    c_f2.metric("Ανεξόφλητα Σταθερά", f"-{upcoming_recurring_unpaid:,.2f} €")
    c_f3.metric("Αναμενόμενα Έξοδα (υπόλοιπες μέρες)", f"-{projected_additional_expenses:,.2f} €")
    st.markdown("---")
    st.metric("💡 Εκτιμώμενο Υπόλοιπο Τέλους Μήνα", f"{projected_balance:,.2f} €")
    st.caption(
        f"Βάσει μέσου ημερήσιου εξόδου {daily_avg_expense:,.2f} €/ημέρα · {days_remaining} ημέρες απομένουν στον μήνα."
    )

    st.markdown("---")
    clay_header("💎", "Καθαρή Θέση (Net Worth)", "Ό,τι έχεις μείον ό,τι χρωστάς, σε μία ματιά", accent="gold")

    checking_balance_all_time = (
        df.loc[df["type"] == "Έσοδο", "amount"].sum() - df.loc[df["type"] == "Έξοδο", "amount"].sum()
        if not df.empty else 0.0
    )
    savings_total = (
        savings_df.loc[savings_df["type"] == "Κατάθεση", "amount"].sum()
        - savings_df.loc[savings_df["type"] == "Ανάληψη", "amount"].sum()
        if not savings_df.empty else 0.0
    )
    buckets_total = sum(b["current"] for b in st.session_state.get("buckets", []))
    total_debt = st.session_state["debts"]["card_balance"] + st.session_state["debts"]["loan_balance"]
    net_worth = checking_balance_all_time + savings_total + buckets_total - total_debt

    nw1, nw2, nw3, nw4 = st.columns(4)
    nw1.metric("Λογαριασμός", f"{checking_balance_all_time:,.2f} €")
    nw2.metric("Αποταμίευση", f"{savings_total:,.2f} €")
    nw3.metric("Buckets", f"{buckets_total:,.2f} €")
    nw4.metric("Χρέη", f"-{total_debt:,.2f} €")
    st.markdown("---")
    st.markdown(
        f'<div class="hero-container">'
        f'<div class="hero-label">Καθαρή Θέση (Net Worth)</div>'
        f'<div class="hero-amount">{net_worth:,.2f} €</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ==========================================
# TAB 3: DYNAMIC SAVINGS BUCKETS
# ==========================================
with main_tab3:
    clay_header("🎯", "Multi-Goal Savings Buckets", "Διαχειριστείτε δυναμικά τους αποταμιευτικούς σας στόχους", accent="green")

    with st.expander("➕ Προσθήκη Νέου Στόχου / Bucket", expanded=False):
        with st.form("add_bucket_form", clear_on_submit=True):
            b_name = st.text_input("Όνομα Στόχου")
            b_curr = st.number_input("Τρέχον Υπόλοιπο (€)", min_value=0.0, value=0.0, step=50.0)
            b_targ = st.number_input("Στόχος (€)", min_value=1.0, value=500.0, step=50.0)
            if st.form_submit_button("Δημιουργία Στόχου") and b_name:
                st.session_state["buckets"].append({"name": b_name, "current": float(b_curr), "target": float(b_targ)})
                st.success(f"Προστέθηκε: {b_name}")
                st.rerun()

    st.markdown("---")

    for idx, bucket in enumerate(st.session_state["buckets"]):
        col_b1, col_b2, col_b3 = st.columns([3, 2, 1])
        with col_b1:
            st.markdown(f"##### {bucket['name']}")
            b_ratio = max(0.0, min(bucket["current"] / bucket["target"], 1.0)) if bucket["target"] else 0.0
            st.progress(b_ratio)
            st.caption(f"{bucket['current']:,.2f} € / {bucket['target']:,.2f} € ({b_ratio*100:.1f}%)")
        with col_b2:
            new_val = st.number_input("Νέο Υπόλοιπο (€)", min_value=0.0, value=float(bucket["current"]), key=f"b_val_{idx}")
            if new_val != bucket["current"]:
                st.session_state["buckets"][idx]["current"] = new_val
                st.rerun()
        with col_b3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️", key=f"del_b_{idx}"):
                stash_for_undo("bucket", {"idx": idx, "item": dict(st.session_state["buckets"][idx])})
                st.session_state["buckets"].pop(idx)
                st.rerun()
        st.markdown("---")

# ==========================================
# TAB 4: ANNUAL REVIEW
# ==========================================
with main_tab4:
    clay_header("📊", f"Ετήσια Ανασκόπηση {selected_year}", accent="gold")

    if not df.empty:
        df_year = df[df["date"].dt.year == selected_year].copy()
        if not df_year.empty:
            y_income = df_year.loc[df_year["type"] == "Έσοδο", "amount"].sum()
            y_expenses = df_year.loc[df_year["type"] == "Έξοδο", "amount"].sum()

            col_y1, col_y2, col_y3 = st.columns(3)
            col_y1.metric("Ετήσια Έσοδα", f"+{y_income:,.2f} €")
            col_y2.metric("Ετήσια Έξοδα", f"-{y_expenses:,.2f} €")
            col_y3.metric("Ετήσιο Καθαρό", f"{y_income - y_expenses:,.2f} €")

            df_year["month"] = df_year["date"].dt.month
            monthly_summary = df_year.groupby(["month", "type"])["amount"].sum().unstack(fill_value=0).reset_index()

            y_cols = [c for c in ["Έσοδο", "Έξοδο"] if c in monthly_summary.columns]
            fig_annual = px.bar(
                monthly_summary, x="month", y=y_cols or monthly_summary.columns[1:],
                barmode="group", template="plotly_dark",
                color_discrete_map={"Έσοδο": "#30d158", "Έξοδο": "#ff453a"},
            )
            fig_annual.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_annual, use_container_width=True)
        else:
            st.info(f"Δεν υπάρχουν συναλλαγές για το {selected_year}.")
    else:
        st.info("Δεν υπάρχουν δεδομένα ακόμα.")

# ==========================================
# TAB: ΑΠΟΤΑΜΙΕΥΣΗ (separate savings account - never mixed with the checking
# account's income/expenses above)
# ==========================================
with main_tab_savings:
    clay_header("💰", "Αποταμίευση", "Ξεχωριστός λογαριασμός - μόνο καταθέσεις/αναλήψεις αποταμίευσης", accent="gold")

    if not savings_df.empty:
        s_deposits = savings_df.loc[savings_df["type"] == "Κατάθεση", "amount"].sum()
        s_withdrawals = savings_df.loc[savings_df["type"] == "Ανάληψη", "amount"].sum()
        savings_balance = s_deposits - s_withdrawals
    else:
        s_deposits, s_withdrawals, savings_balance = 0.0, 0.0, 0.0

    st.markdown(
        f'<div class="hero-container">'
        f'<div class="hero-label">Υπόλοιπο Αποταμίευσης</div>'
        f'<div class="hero-amount">{savings_balance:,.2f} €</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    s_m1, s_m2 = st.columns(2)
    s_m1.metric("Σύνολο Καταθέσεων", f"+{s_deposits:,.2f} €")
    s_m2.metric("Σύνολο Αναλήψεων", f"-{s_withdrawals:,.2f} €")

    with st.expander("➕ Νέα Κίνηση Αποταμίευσης", expanded=False):
        with st.form("savings_entry_form", clear_on_submit=True):
            sv_col1, sv_col2 = st.columns(2)
            with sv_col1:
                sv_date = st.date_input("Ημερομηνία", datetime.date.today(), key="sv_date")
                sv_type = st.selectbox("Τύπος", ["Κατάθεση", "Ανάληψη"], key="sv_type")
            with sv_col2:
                sv_amount = st.number_input("Ποσό (€)", min_value=0.0, format="%.2f", key="sv_amount")
                sv_note = st.text_input("Σημείωση", key="sv_note")

            if st.form_submit_button("Καταγραφή") and sv_amount > 0:
                try:
                    supabase.table("savings").insert(
                        {"date": str(sv_date), "type": sv_type, "amount": float(sv_amount), "note": sv_note}
                    ).execute()
                    st.success("Καταχωρήθηκε!")
                    refresh_savings_and_rerun()
                except Exception as e:
                    st.error(f"Σφάλμα καταχώρησης: {e}")

    with st.expander("✏️ Διορθώσεις & Διαγραφή Κινήσεων", expanded=False):
        if not savings_df.empty:
            sv_tx_options = {
                row["id"]: f"ID {row['id']} | {row['date'].strftime('%Y-%m-%d')} | {row['type']} | {row['amount']:.2f}€"
                for _, row in savings_df.iterrows()
            }
            sv_selected_id = st.selectbox("Επιλέξτε Κίνηση", list(sv_tx_options.keys()), format_func=lambda x: sv_tx_options[x])
            sv_selected_row = savings_df[savings_df["id"] == sv_selected_id].iloc[0]

            with st.form("savings_edit_form"):
                sve_col1, sve_col2 = st.columns(2)
                with sve_col1:
                    sv_edit_date = st.date_input("Νέα Ημερομηνία", pd.to_datetime(sv_selected_row["date"]))
                    sv_edit_type = st.selectbox(
                        "Νέος Τύπος", ["Κατάθεση", "Ανάληψη"],
                        index=0 if sv_selected_row["type"] == "Κατάθεση" else 1,
                    )
                with sve_col2:
                    sv_edit_amount = st.number_input("Νέο Ποσό (€)", min_value=0.0, value=float(sv_selected_row["amount"]), format="%.2f")
                    sv_edit_note = st.text_input("Νέα Σημείωση", value=str(sv_selected_row["note"]) if pd.notna(sv_selected_row["note"]) else "")

                sv_btn_save, sv_btn_delete = st.columns(2)
                with sv_btn_save:
                    if st.form_submit_button("💾 Αποθήκευση"):
                        try:
                            supabase.table("savings").update({
                                "date": str(sv_edit_date), "type": sv_edit_type,
                                "amount": float(sv_edit_amount), "note": sv_edit_note,
                            }).eq("id", sv_selected_id).execute()
                            st.success("Ενημερώθηκε!")
                            refresh_savings_and_rerun()
                        except Exception as e:
                            st.error(f"Σφάλμα ενημέρωσης: {e}")
                with sv_btn_delete:
                    if st.form_submit_button("🗑️ Διαγραφή"):
                        try:
                            undo_payload = {
                                "date": str(pd.to_datetime(sv_selected_row["date"]).date()),
                                "type": sv_selected_row["type"],
                                "amount": float(sv_selected_row["amount"]),
                                "note": sv_selected_row["note"] if pd.notna(sv_selected_row["note"]) else "",
                            }
                            supabase.table("savings").delete().eq("id", sv_selected_id).execute()
                            stash_for_undo("saving", undo_payload)
                            st.warning("Διαγράφηκε! (Αναίρεση διαθέσιμη από το sidebar)")
                            refresh_savings_and_rerun()
                        except Exception as e:
                            st.error(f"Σφάλμα διαγραφής: {e}")
        else:
            st.caption("Δεν υπάρχουν κινήσεις αποταμίευσης ακόμα.")

    if not savings_df.empty:
        st.markdown("---")
        st.subheader("📈 Πορεία Αποταμίευσης")
        sv_chart_df = savings_df.sort_values("date").copy()
        sv_chart_df["signed_amount"] = sv_chart_df.apply(
            lambda r: r["amount"] if r["type"] == "Κατάθεση" else -r["amount"], axis=1
        )
        sv_chart_df["cumulative"] = sv_chart_df["signed_amount"].cumsum()
        fig_savings = px.area(
            sv_chart_df, x="date", y="cumulative", template="plotly_dark",
        )
        fig_savings.update_traces(line_color="#ffd60a", fillcolor="rgba(255, 214, 10, 0.15)")
        fig_savings.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=10, b=10, l=10, r=10), height=240,
            xaxis_title=None, yaxis_title=None,
        )
        st.plotly_chart(fig_savings, use_container_width=True)

        st.subheader("📜 Ιστορικό Κινήσεων")
        sv_display_df = savings_df.copy()
        sv_display_df["date"] = sv_display_df["date"].dt.strftime("%Y-%m-%d")
        st.dataframe(
            sv_display_df[["id", "date", "type", "amount", "note"]],
            use_container_width=True, hide_index=True,
        )


# ==========================================
# TAB 5: FIXED RECURRING EXPENSES
# ==========================================
with main_tab5:
    clay_header("⚙️", "Σταθερά Έξοδα (Recurring)", "Πλήρως παραμετροποιήσιμη διαχείριση πάγιων υποχρεώσεων", accent="blue")

    with st.expander("➕ Προσθήκη Νέου Σταθερού Εξόδου", expanded=False):
        with st.form("add_rec_form", clear_on_submit=True):
            r_title = st.text_input("Τίτλος Εξόδου")
            r_amount = st.number_input("Ποσό (€)", min_value=0.0, value=50.0, step=5.0)
            r_day = st.number_input("Ημέρα Πληρωμής (1-31)", min_value=1, max_value=31, value=1)
            if st.form_submit_button("Προσθήκη Σταθερού") and r_title:
                st.session_state["recurring"].append(
                    {"title": r_title, "amount": float(r_amount), "due_day": int(r_day), "paid": False, "tx_id": None}
                )
                st.success(f"Προστέθηκε: {r_title}")
                st.rerun()

    recurring_suggestions = detect_recurring_candidates(df, st.session_state["recurring"])
    if recurring_suggestions:
        st.markdown("---")
        st.subheader("🤖 Προτάσεις Αυτόματης Ανίχνευσης")
        st.caption("Βρέθηκαν έξοδα που επαναλαμβάνονται σταθερά μήνα με μήνα στο ιστορικό σου.")
        for s_idx, cand in enumerate(recurring_suggestions):
            sug_col1, sug_col2 = st.columns([4, 1])
            with sug_col1:
                st.markdown(
                    f"**{cand['title']}** — {cand['amount']:,.2f} €, ~{cand['occurrences']} μήνες, "
                    f"συνήθως γύρω στις {cand['due_day']} του μηνός"
                )
            with sug_col2:
                if st.button("➕ Προσθήκη", key=f"add_suggestion_{s_idx}", use_container_width=True):
                    st.session_state["recurring"].append({
                        "title": cand["title"], "amount": cand["amount"], "due_day": cand["due_day"],
                        "paid": False, "tx_id": None,
                    })
                    st.success(f"Προστέθηκε ως σταθερό: {cand['title']}")
                    st.rerun()

    st.markdown("---")

    total_rec = sum(item["amount"] for item in st.session_state["recurring"])
    st.markdown(f"##### 📌 Συνολικά Σταθερά Έξοδα: **{total_rec:,.2f} €/μήνα**")
    st.markdown("<br>", unsafe_allow_html=True)

    today_day = datetime.date.today().day
    for idx, item in enumerate(st.session_state["recurring"]):
        col_r1, col_r2, col_r3, col_r4 = st.columns([3, 2, 2, 1])
        with col_r1:
            st.markdown(f"**{item['title']}**")
            st.caption(f"Πληρωμή στις {item['due_day']} του μηνός")
            new_paid = st.checkbox("Πληρώθηκε", value=item["paid"], key=f"rec_paid_{idx}")
            if new_paid != item["paid"]:
                if new_paid:
                    # Checking the box = a real transaction, exactly like the manual
                    # entry form: it lands in Supabase, shows up on the Dashboard,
                    # in the pie/bar charts, and in the PDF export.
                    now_local = datetime.date.today()
                    safe_day = min(item["due_day"], calendar.monthrange(now_local.year, now_local.month)[1])
                    tx_date = datetime.date(now_local.year, now_local.month, safe_day)
                    try:
                        result = (
                            supabase.table("transactions")
                            .insert({
                                "date": str(tx_date),
                                "category": "Σταθερά Έξοδα",
                                "amount": float(item["amount"]),
                                "type": "Έξοδο",
                                "note": f"Σταθερό - {item['title']}",
                            })
                            .execute()
                        )
                        new_tx_id = result.data[0]["id"] if result.data else None
                        st.session_state["recurring"][idx]["paid"] = True
                        st.session_state["recurring"][idx]["tx_id"] = new_tx_id
                        st.toast(f"Καταχωρήθηκε πληρωμή: {item['title']}", icon="✅")
                        refresh_and_rerun()
                    except Exception as e:
                        st.error(f"Σφάλμα καταχώρησης πληρωμής: {e}")
                else:
                    # Unchecking = removes the transaction it created, so the
                    # Dashboard/PDF stay in sync with what's actually ticked here.
                    tx_id = item.get("tx_id")
                    try:
                        if tx_id is not None:
                            supabase.table("transactions").delete().eq("id", tx_id).execute()
                        st.session_state["recurring"][idx]["paid"] = False
                        st.session_state["recurring"][idx]["tx_id"] = None
                        st.toast(f"Ακυρώθηκε πληρωμή: {item['title']}", icon="↩️")
                        refresh_and_rerun()
                    except Exception as e:
                        st.error(f"Σφάλμα ακύρωσης πληρωμής: {e}")
        with col_r2:
            new_amt = st.number_input("Ποσό (€)", min_value=0.0, value=float(item["amount"]), step=5.0, key=f"rec_amt_{idx}")
            if new_amt != item["amount"]:
                st.session_state["recurring"][idx]["amount"] = new_amt
                st.rerun()
        with col_r3:
            new_day = st.number_input("Ημέρα", min_value=1, max_value=31, value=int(item["due_day"]), key=f"rec_day_{idx}")
            if new_day != item["due_day"]:
                st.session_state["recurring"][idx]["due_day"] = new_day
                st.rerun()
        with col_r4:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🗑️", key=f"del_rec_{idx}"):
                tx_id = item.get("tx_id")
                try:
                    if tx_id is not None:
                        supabase.table("transactions").delete().eq("id", tx_id).execute()
                        fetch_transactions.clear()
                except Exception as e:
                    st.error(f"Σφάλμα διαγραφής συνδεδεμένης συναλλαγής: {e}")
                stash_for_undo("recurring", {"idx": idx, "item": dict(item)})
                st.session_state["recurring"].pop(idx)
                st.toast(f"Διαγράφηκε: {item['title']}", icon="🗑️")
                st.rerun()
        st.markdown("---")

# ==========================================
# TAB 6: WEEKLY CHECKLIST
# ==========================================
with main_tab6:
    clay_header("📋", "Εβδομαδιαίο Checklist", "Προσθέστε, τσεκάρετε ή διαγράψτε εργασίες", accent="purple")

    new_task = st.text_input("➕ Νέα Εργασία Checklist")
    if st.button("Προσθήκη Εργασίας") and new_task:
        st.session_state["checklist"].append({"task": new_task, "done": False})
        st.rerun()

    st.markdown("---")
    for idx, item in enumerate(st.session_state["checklist"]):
        c_col1, c_col2 = st.columns([4, 1])
        with c_col1:
            st.session_state["checklist"][idx]["done"] = st.checkbox(item["task"], value=item["done"], key=f"chk_{idx}")
        with c_col2:
            if st.button("🗑️", key=f"del_chk_{idx}"):
                stash_for_undo("checklist", {"idx": idx, "item": dict(st.session_state["checklist"][idx])})
                st.session_state["checklist"].pop(idx)
                st.rerun()

# ==========================================
# TAB 7: DEBT SIMULATOR
# ==========================================
with main_tab7:
    clay_header("🏦", "Δάνεια & Πιστωτικές", accent="red")
    card_balance = st.number_input(
        "Υπόλοιπο Πιστωτικών (€)", min_value=0.0, value=st.session_state["debts"]["card_balance"], key="debt_card"
    )
    loan_balance = st.number_input(
        "Υπόλοιπο Δανείων (€)", min_value=0.0, value=st.session_state["debts"]["loan_balance"], key="debt_loan"
    )
    if (
        card_balance != st.session_state["debts"]["card_balance"]
        or loan_balance != st.session_state["debts"]["loan_balance"]
    ):
        st.session_state["debts"]["card_balance"] = card_balance
        st.session_state["debts"]["loan_balance"] = loan_balance
    st.metric("Συνολικό Χρέος", f"{card_balance + loan_balance:,.2f} €")

# ==========================================
# TAB 8: EXPORT (PDF + EXCEL, MONTHLY OR CUSTOM RANGE)
# ==========================================
with main_tab8:
    clay_header("📄", "Εξαγωγή Αναφορών", "PDF & Excel, για τον επιλεγμένο μήνα ή προσαρμοσμένο εύρος", accent="gold")

    range_mode = st.radio(
        "Περίοδος Αναφοράς",
        ["Επιλεγμένος μήνας (sidebar)", "Προσαρμοσμένο εύρος ημερομηνιών"],
        horizontal=True,
    )

    if range_mode == "Επιλεγμένος μήνας (sidebar)":
        export_df = filtered_df.copy() if not filtered_df.empty else pd.DataFrame()
        export_label = f"{selected_year}_{selected_month:02d}"
        export_income, export_expenses, export_balance = income, expenses, balance
        report_month_title, report_year_title = selected_month_name, selected_year
    else:
        rc1, rc2 = st.columns(2)
        with rc1:
            range_start = st.date_input("Από", datetime.date.today().replace(day=1), key="export_range_start")
        with rc2:
            range_end = st.date_input("Έως", datetime.date.today(), key="export_range_end")

        if range_start > range_end:
            st.error("Η ημερομηνία 'Από' δεν μπορεί να είναι μετά την 'Έως'.")
            export_df = pd.DataFrame()
        elif not df.empty:
            _mask = (df["date"].dt.date >= range_start) & (df["date"].dt.date <= range_end)
            export_df = df[_mask].copy()
        else:
            export_df = pd.DataFrame()

        export_income = export_df.loc[export_df["type"] == "Έσοδο", "amount"].sum() if not export_df.empty else 0.0
        export_expenses = export_df.loc[export_df["type"] == "Έξοδο", "amount"].sum() if not export_df.empty else 0.0
        export_balance = export_income - export_expenses
        export_label = f"{range_start}_{range_end}"
        report_month_title, report_year_title = f"{range_start} έως {range_end}", ""

    export_search = st.text_input("🔎 Αναζήτηση (κατηγορία ή σημείωση)", key="export_search")
    if export_search and not export_df.empty:
        _mask = (
            export_df["category"].str.contains(export_search, case=False, na=False)
            | export_df["note"].astype(str).str.contains(export_search, case=False, na=False)
        )
        export_df = export_df[_mask]

    if not export_df.empty:
        e_m1, e_m2, e_m3 = st.columns(3)
        e_m1.metric("Έσοδα", f"+{export_income:,.2f} €")
        e_m2.metric("Έξοδα", f"-{export_expenses:,.2f} €")
        e_m3.metric("Καθαρό", f"{export_balance:,.2f} €")

        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
            try:
                pdf_bytes = create_pdf_report(
                    report_month_title, report_year_title, export_income, export_expenses, export_balance, export_df
                )
                st.download_button(
                    "📥 Λήψη PDF", data=pdf_bytes,
                    file_name=f"statement_{export_label}.pdf", mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"Σφάλμα δημιουργίας PDF: {e}")
        with dl_col2:
            try:
                excel_bytes = create_excel_report(export_df)
                st.download_button(
                    "📊 Λήψη Excel", data=excel_bytes,
                    file_name=f"statement_{export_label}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"Σφάλμα δημιουργίας Excel: {e}")

        st.markdown("---")
        st.subheader("📜 Προεπισκόπηση")
        preview_df = export_df.copy()
        preview_df["date"] = pd.to_datetime(preview_df["date"]).dt.strftime("%Y-%m-%d")
        st.dataframe(
            preview_df[["id", "date", "type", "category", "amount", "note"]],
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("Δεν υπάρχουν συναλλαγές για την επιλεγμένη περίοδο/αναζήτηση.")
