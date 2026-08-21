import os
import calendar
import datetime
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


try:
    data = fetch_transactions()
    df = pd.DataFrame(data) if data else pd.DataFrame()
except Exception as err:
    st.error(f"🔍 Σφάλμα Supabase: {err}")
    df = pd.DataFrame()

if not df.empty:
    df["date"] = pd.to_datetime(df["date"])


def refresh_and_rerun():
    """Clears the transactions cache so writes show up immediately, then reruns."""
    fetch_transactions.clear()
    st.rerun()


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

if st.sidebar.button("🔒 Αποσύνδεση"):
    st.session_state["authenticated"] = False
    st.rerun()

# --- NAVIGATION TABS ---
(
    main_tab1, main_tab2, main_tab3, main_tab4,
    main_tab5, main_tab6, main_tab7, main_tab8,
) = st.tabs(
    [
        "👛 Dashboard", "🧭 Cash Flow", "🎯 Buckets", "📊 Ετήσια",
        "⚙️ Σταθερά", "📋 Checklist", "🏦 Δάνεια", "📄 PDF",
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
                            supabase.table("transactions").delete().eq("id", selected_tx_id).execute()
                            st.warning("Διαγράφηκε!")
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
        display_df = filtered_df.copy()
        display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
        st.dataframe(
            display_df[["id", "date", "type", "category", "amount", "note"]],
            use_container_width=True, hide_index=True,
        )

# ==========================================
# TAB 2: CASH FLOW FORECASTING
# ==========================================
with main_tab2:
    clay_header("🧭", "Cash Flow Projection", "Πρόβλεψη υπολοίπου βάσει σταθερών εξόδων", accent="purple")

    upcoming_recurring = (
        sum(float(r["amount"]) for r in st.session_state["recurring"])
        if "recurring" in st.session_state and st.session_state["recurring"]
        else 0.0
    )

    projected_remaining = balance - upcoming_recurring
    c_f1, c_f2 = st.columns(2)
    c_f1.metric("Τρέχον Υπόλοιπο (Dashboard)", f"{balance:,.2f} €")
    c_f2.metric("Σύνολο Σταθερών Εξόδων (Tab 5)", f"-{upcoming_recurring:,.2f} €")
    st.markdown("---")
    st.metric("💡 Εκτιμώμενο Υπόλοιπο Τέλους Μήνα", f"{projected_remaining:,.2f} €")

# ==========================================
# TAB 3: DYNAMIC SAVINGS BUCKETS
# ==========================================
with main_tab3:
    clay_header("🎯", "Multi-Goal Savings Buckets", "Διαχειριστείτε δυναμικά τους αποταμιευτικούς σας στόχους", accent="green")

    if "buckets" not in st.session_state:
        st.session_state["buckets"] = [
            {"name": "🚗 Συντήρηση Ι.Χ.", "current": 400.0, "target": 800.0},
            {"name": "🏖️ Διακοπές", "current": 1200.0, "target": 1500.0},
            {"name": "💻 Εξοπλισμός", "current": 300.0, "target": 1000.0},
        ]

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
# TAB 5: FIXED RECURRING EXPENSES
# ==========================================
with main_tab5:
    clay_header("⚙️", "Σταθερά Έξοδα (Recurring)", "Πλήρως παραμετροποιήσιμη διαχείριση πάγιων υποχρεώσεων", accent="blue")

    if "recurring" not in st.session_state:
        st.session_state["recurring"] = [
            {"title": "Ενοίκιο", "amount": 450.0, "due_day": 1, "paid": False, "tx_id": None},
            {"title": "Internet / Κοινόχρηστα", "amount": 35.0, "due_day": 10, "paid": False, "tx_id": None},
            {"title": "Συνδρομές (Streaming)", "amount": 15.99, "due_day": 15, "paid": False, "tx_id": None},
        ]
    else:
        # Backfill fields for anyone who added recurring items before these existed
        for item in st.session_state["recurring"]:
            item.setdefault("paid", False)
            item.setdefault("tx_id", None)

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
                st.session_state["recurring"].pop(idx)
                st.toast(f"Διαγράφηκε: {item['title']}", icon="🗑️")
                st.rerun()
        st.markdown("---")

# ==========================================
# TAB 6: WEEKLY CHECKLIST
# ==========================================
with main_tab6:
    clay_header("📋", "Εβδομαδιαίο Checklist", "Προσθέστε, τσεκάρετε ή διαγράψτε εργασίες", accent="purple")

    if "checklist" not in st.session_state:
        st.session_state["checklist"] = [
            {"task": "Έλεγχος υπολοίπου τραπέζης", "done": False},
            {"task": "Καταχώρηση αποδείξεων εβδομάδας", "done": True},
            {"task": "Πληρωμή λογαριασμών", "done": False},
        ]

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
                st.session_state["checklist"].pop(idx)
                st.rerun()

# ==========================================
# TAB 7: DEBT SIMULATOR
# ==========================================
with main_tab7:
    clay_header("🏦", "Δάνεια & Πιστωτικές", accent="red")
    card_balance = st.number_input("Υπόλοιπο Πιστωτικών (€)", min_value=0.0, value=1500.0)
    loan_balance = st.number_input("Υπόλοιπο Δανείων (€)", min_value=0.0, value=8000.0)
    st.metric("Συνολικό Χρέος", f"{card_balance + loan_balance:,.2f} €")

# ==========================================
# TAB 8: PDF STATEMENT
# ==========================================
with main_tab8:
    clay_header("📄", "Εξαγωγή PDF Statement", accent="gold")
    if not filtered_df.empty:
        try:
            pdf_bytes = create_pdf_report(selected_month_name, selected_year, income, expenses, balance, filtered_df)
            st.download_button(
                label=f"📥 Λήψη PDF Αναφοράς ({selected_month_name} {selected_year})",
                data=pdf_bytes, file_name=f"statement_{selected_year}_{selected_month:02d}.pdf",
                mime="application/pdf", use_container_width=True,
            )
        except Exception as e:
            st.error(f"Σφάλμα δημιουργίας PDF: {e}")
    else:
        st.info("Δεν υπάρχουν συναλλαγές για την παραγωγή PDF.")
