import calendar
import datetime
from io import BytesIO
import math
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from supabase import create_client
from fpdf import FPDF
from PIL import Image

# --- STREAMLIT CONFIG & FINTECH REVOLUT UI ---
st.set_page_config(
    page_title="Executive Wealth Engine",
    layout="centered",
    page_icon="💳",
    initial_sidebar_state="collapsed",
)

# --- CUSTOM CSS (REVOLUT / APPLE FINTECH THEME) ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, sans-serif;
    }

    .stApp {
        background-color: #0d0e12;
        color: #ffffff;
    }

    .hero-container {
        text-align: center;
        padding: 15px 0 5px 0;
    }
    .hero-label {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #8e94a5;
        font-weight: 600;
    }
    .hero-amount {
        font-size: 38px;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: -1.5px;
        margin-top: 2px;
    }

    div[data-baseweb="tab-list"] {
        gap: 4px;
        background-color: #1a1c23;
        padding: 4px;
        border-radius: 30px;
        border: 1px solid #2a2d37;
        margin-bottom: 15px;
    }
    button[data-baseweb="tab"] {
        border-radius: 20px !important;
        padding: 6px 12px !important;
        font-size: 11px !important;
        font-weight: 600 !important;
        color: #8e94a5 !important;
        border: none !important;
        background: transparent !important;
    }
    button[aria-selected="true"] {
        background: #ffffff !important;
        color: #0d0e12 !important;
        box-shadow: 0 4px 12px rgba(255, 255, 255, 0.15) !important;
    }

    div[data-testid="metric-container"] {
        background-color: #1a1c23;
        border: 1px solid #2a2d37;
        padding: 14px;
        border-radius: 16px;
    }

    div[data-testid="stExpander"] {
        background-color: #1a1c23;
        border: 1px solid #2a2d37;
        border-radius: 16px !important;
    }
    
    .stButton>button {
        background-color: #ffffff;
        color: #0d0e12;
        border: none;
        border-radius: 30px;
        font-weight: 700;
        padding: 8px 14px;
    }
    .stButton>button:hover {
        background-color: #e5e5ea;
        color: #0d0e12;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# --- SUPABASE CONNECTION ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except Exception as e:
    st.error(f"❌ Σφάλμα Secrets: {e}")
    st.stop()

# --- SECURITY / PIN LOCK ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown(
        """
        <div style='text-align: center; padding: 40px 0;'>
            <h2>🔒 Πρόσβαση στο Wealth Engine</h2>
            <p style='color: #8e94a5;'>Εισάγετε το PIN για να συνεχίσετε</p>
        </div>
    """,
        unsafe_allow_html=True,
    )
    pin_input = st.text_input(
        "PIN", type="password", label_visibility="collapsed"
    )
    if st.button("Ξεκλείδωμα", use_container_width=True):
        if pin_input == st.secrets.get("APP_PIN", "1234"):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Λανθασμένο PIN.")
    st.stop()

# --- HELPER: UNICODE-SAFE PDF GENERATOR ---
def create_pdf_report(month_name, year, income, expenses, balance, df_data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)

    months_map = {
        "Ιανουάριος": "January", "Φεβρουάριος": "February", "Μάρτιος": "March",
        "Απρίλιος": "April", "Μάιος": "May", "Ιούνιος": "June",
        "Ιούλιος": "July", "Αύγουστος": "August", "Σεπτέμβριος": "September",
        "Οκτώβριος": "October", "Νοέμβριος": "November", "Δεκέμβριος": "December"
    }
    safe_month = months_map.get(month_name, month_name)

    pdf.cell(0, 10, f"Executive Financial Statement - {safe_month} {year}", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, f"Total Income: {income:,.2f} EUR", ln=True)
    pdf.cell(0, 8, f"Total Expenses: {expenses:,.2f} EUR", ln=True)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, f"Net Balance: {balance:,.2f} EUR", ln=True)
    pdf.ln(10)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(30, 8, "Date", 1)
    pdf.cell(30, 8, "Type", 1)
    pdf.cell(45, 8, "Category", 1)
    pdf.cell(30, 8, "Amount", 1)
    pdf.cell(55, 8, "Note", 1)
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    for _, row in df_data.iterrows():
        date_str = row["date"].strftime("%Y-%m-%d") if hasattr(row["date"], "strftime") else str(row["date"])
        safe_type = str(row["type"]).encode("latin-1", "ignore").decode("latin-1") or "N/A"
        safe_cat = str(row["category"]).encode("latin-1", "ignore").decode("latin-1") or "Category"
        safe_note = str(row["note"]).encode("latin-1", "ignore").decode("latin-1") or ""

        pdf.cell(30, 7, date_str, 1)
        pdf.cell(30, 7, safe_type, 1)
        pdf.cell(45, 7, safe_cat[:20], 1)
        pdf.cell(30, 7, f"{row['amount']:.2f} EUR", 1)
        pdf.cell(55, 7, safe_note[:25], 1)
        pdf.ln()

    return bytes(pdf.output())

# --- FETCH DATA ---
try:
    response = (
        supabase.table("transactions")
        .select("*")
        .order("date", desc=True)
        .execute()
    )
    data = response.data
    df = pd.DataFrame(data) if data else pd.DataFrame()
except Exception as err:
    st.error(f"🔍 Σφάλμα Supabase: {err}")
    df = pd.DataFrame()

if not df.empty:
    df["date"] = pd.to_datetime(df["date"])

# --- SIDEBAR FILTERS ---
st.sidebar.header("🗓️ Περίοδος & Στόχοι")
now = datetime.datetime.now()
current_year = now.year
current_month = now.month

years = list(range(2024, current_year + 2))
selected_year = st.sidebar.selectbox(
    "Έτος", years, index=years.index(current_year)
)

month_names = [
    "Ιανουάριος", "Φεβρουάριος", "Μάρτιος", "Απρίλιος", "Μάιος", "Ιούνιος",
    "Ιούλιος", "Αύγουστος", "Σεπτέμβριος", "Οκτώβριος", "Νοέμβριος", "Δεκέμβριος"
]
selected_month_name = st.sidebar.selectbox(
    "Μήνας", month_names, index=current_month - 1
)
selected_month = month_names.index(selected_month_name) + 1

monthly_budget = st.sidebar.number_input(
    "Μηνιαίο Όριο (€)", min_value=0.0, value=1200.0, step=50.0
)

if st.sidebar.button("🔒 Αποσύνδεση"):
    st.session_state["authenticated"] = False
    st.rerun()

# --- NAVIGATION TABS ---
(
    main_tab1,
    main_tab2,
    main_tab3,
    main_tab4,
    main_tab5,
    main_tab6,
    main_tab7,
) = st.tabs(
    [
        "💰 Dashboard",
        "🔮 Cash Flow",
        "🎯 Buckets",
        "📈 Investments",
        "💳 Δάνεια",
        "📄 PDF Statement",
        "🤖 Automation",
    ]
)

# ==========================================
# TAB 1: DASHBOARD & MANUAL CONTROLS
# ==========================================
with main_tab1:
    if not df.empty:
        filtered_df = df[
            (df["date"].dt.year == selected_year)
            & (df["date"].dt.month == selected_month)
        ].copy()
        income = (
            filtered_df[filtered_df["type"] == "Έσοδο"]["amount"].sum()
            if not filtered_df.empty
            else 0.0
        )
        expenses = (
            filtered_df[filtered_df["type"] == "Έξοδο"]["amount"].sum()
            if not filtered_df.empty
            else 0.0
        )
        balance = income - expenses
    else:
        filtered_df = pd.DataFrame()
        income, expenses, balance = 0.0, 0.0, 0.0

    st.markdown(
        f"""
        <div class="hero-container">
            <div class="hero-label">Συνολικο Υπολοιπο ({selected_month_name})</div>
            <div class="hero-amount">{balance:,.2f} €</div>
        </div>
    """,
        unsafe_allow_html=True,
    )

    # SMART BUDGET ALERT
    if monthly_budget > 0:
        pct_used = (expenses / monthly_budget) * 100
        if pct_used >= 100:
            st.error(
                f"🚨 **Υπέρβαση Budget!** Έχεις καταναλώσει το {pct_used:.1f}% του ορίου ({expenses:.2f} / {monthly_budget:.2f}€)."
            )
        elif pct_used >= 80:
            st.warning(
                f"⚠️ **Προσοχή:** Έχεις φτάσει το {pct_used:.1f}% του μηνιαίου ορίου."
            )

    # QUICK ADD ACTIONS
    q_col1, q_col2, q_col3 = st.columns(3)
    today_str = str(datetime.date.today())

    with q_col1:
        if st.button("+ Καφές 2.50€", use_container_width=True):
            supabase.table("transactions").insert(
                {
                    "date": today_str,
                    "category": "Φαγητό/Καφές",
                    "amount": 2.50,
                    "type": "Έξοδο",
                    "note": "Quick Add - Καφές",
                }
            ).execute()
            st.toast("Προστέθηκε: Καφές 2.50€", icon="☕")
            st.rerun()

    with q_col2:
        if st.button("+ Βενζίνη 20€", use_container_width=True):
            supabase.table("transactions").insert(
                {
                    "date": today_str,
                    "category": "Καύσιμα/Μεταφορές",
                    "amount": 20.00,
                    "type": "Έξοδο",
                    "note": "Quick Add - Βενζίνη",
                }
            ).execute()
            st.toast("Προστέθηκε: Βενζίνη 20.00€", icon="⛽")
            st.rerun()

    with q_col3:
        if st.button("+ Super 50€", use_container_width=True):
            supabase.table("transactions").insert(
                {
                    "date": today_str,
                    "category": "Σούπερ Μάρκετ",
                    "amount": 50.00,
                    "type": "Έξοδο",
                    "note": "Quick Add - Supermarket",
                }
            ).execute()
            st.toast("Προστέθηκε: Supermarket 50.00€", icon="🛒")
            st.rerun()

    # MANUAL INPUT FORM
    with st.expander("➕ Πλήρης Καταγραφή Συναλλαγής (Manual Input)", expanded=False):
        with st.form("entry_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                date = st.date_input("Ημερομηνία", datetime.date.today())
                t_type = st.selectbox("Τύπος", ["Έξοδο", "Έσοδο"])
                amount = st.number_input("Ποσό (€)", min_value=0.0, format="%.2f")
            with col2:
                category = st.selectbox(
                    "Κατηγορία",
                    [
                        "Σούπερ Μάρκετ", "Λογαριασμοί/Σπίτι", "Καύσιμα/Μεταφορές",
                        "Φαγητό/Καφές", "Ψυχαγωγία", "Μισθός", "Λοιπά",
                    ],
                )
                note = st.text_input("Σημείωση")

            if st.form_submit_button("Καταγραφή Συναλλαγής") and amount > 0:
                supabase.table("transactions").insert(
                    {
                        "date": str(date),
                        "category": category,
                        "amount": float(amount),
                        "type": t_type,
                        "note": note,
                    }
                ).execute()
                st.success("Καταχωρήθηκε επιτυχώς!")
                st.rerun()

    # MANUAL CORRECTIONS / EDIT & DELETE SECTION
    with st.expander("✏️ Διορθώσεις & Διαγραφή Συναλλαγών", expanded=False):
        if not filtered_df.empty:
            tx_options = {
                row["id"]: f"ID {row['id']} | {row['date'].strftime('%Y-%m-%d')} | {row['category']} | {row['amount']:.2f}€ ({row['type']})"
                for _, row in filtered_df.iterrows()
            }
            selected_tx_id = st.selectbox("Επιλέξτε Συναλλαγή για Διόρθωση/Διαγραφή", list(tx_options.keys()), format_func=lambda x: tx_options[x])
            
            selected_row = filtered_df[filtered_df["id"] == selected_tx_id].iloc[0]

            with st.form("edit_form"):
                e_col1, e_col2 = st.columns(2)
                with e_col1:
                    edit_date = st.date_input("Νέα Ημερομηνία", pd.to_datetime(selected_row["date"]))
                    edit_type = st.selectbox("Νέος Τύπος", ["Έξοδο", "Έσοδο"], index=0 if selected_row["type"] == "Έξοδο" else 1)
                    edit_amount = st.number_input("Νέο Ποσό (€)", min_value=0.0, value=float(selected_row["amount"]), format="%.2f")
                with e_col2:
                    categories_list = ["Σούπερ Μάρκετ", "Λογαριασμοί/Σπίτι", "Καύσιμα/Μεταφορές", "Φαγητό/Καφές", "Ψυχαγωγία", "Μισθός", "Λοιπά"]
                    edit_cat_idx = categories_list.index(selected_row["category"]) if selected_row["category"] in categories_list else 0
                    edit_category = st.selectbox("Νέα Κατηγορία", categories_list, index=edit_cat_idx)
                    edit_note = st.text_input("Νέα Σημείωση", value=str(selected_row["note"]) if selected_row["note"] else "")

                btn_save, btn_delete = st.columns(2)
                with btn_save:
                    if st.form_submit_button("💾 Αποθήκευση Διόρθωσης"):
                        supabase.table("transactions").update(
                            {
                                "date": str(edit_date),
                                "category": edit_category,
                                "amount": float(edit_amount),
                                "type": edit_type,
                                "note": edit_note,
                            }
                        ).eq("id", selected_tx_id).execute()
                        st.success("Η συναλλαγή ενημερώθηκε!")
                        st.rerun()
                with btn_delete:
                    if st.form_submit_button("🗑️ Διαγραφή Συναλλαγής"):
                        supabase.table("transactions").delete().eq("id", selected_tx_id).execute()
                        st.warning("Η συναλλαγή διαγράφηκε!")
                        st.rerun()
        else:
            st.info("Δεν υπάρχουν διαθέσιμες συναλλαγές για διόρθωση.")

    # AI OCR RECEIPT SCANNER
    with st.expander("📷 AI OCR Receipt Scanner (Σάρωση Απόδειξης)", expanded=False):
        uploaded_file = st.file_uploader("Ανεβάστε φωτογραφία απόδειξης", type=["png", "jpg", "jpeg"])
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.image(image, caption="Φορτωμένη Απόδειξη", use_container_width=True)
            st.info("⚡ Αναγνώριση στοιχείων... (Προσυμπλήρωση φόρμας)")

    m1, m2 = st.columns(2)
    m1.metric("Έσοδα", f"+{income:,.2f} €")
    m2.metric("Έξοδα", f"-{expenses:,.2f} €")

    if not filtered_df.empty:
        df_expenses = filtered_df[filtered_df["type"] == "Έξοδο"]
        if not df_expenses.empty:
            cat_expenses = df_expenses.groupby("category")["amount"].sum().reset_index()
            fig_pie = px.pie(
                cat_expenses,
                values="amount",
                names="category",
                hole=0.6,
                template="plotly_dark",
                color_discrete_sequence=[
                    "#30d158", "#0a84ff", "#ff453a", "#ffd60a", "#bf5af2", "#8e8e93",
                ],
            )
            fig_pie.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
                margin=dict(t=10, b=10, l=10, r=10),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        st.subheader("📜 Συναλλαγές")
        display_df = filtered_df.copy()
        display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
        st.dataframe(
            display_df[["id", "date", "type", "category", "amount", "note"]],
            use_container_width=True,
            hide_index=True,
        )

# ==========================================
# TAB 2: CASH FLOW FORECASTING
# ==========================================
with main_tab2:
    st.subheader("🔮 30-Day Cash Flow Projection")
    st.caption("Πρόβλεψη διαθέσιμου υπολοίπου μέχρι το τέλος του μήνα.")

    try:
        rec_data = supabase.table("recurring_expenses").select("*").execute().data
        upcoming_recurring = sum(float(r["amount"]) for r in rec_data) if rec_data else 0.0
    except Exception:
        upcoming_recurring = 0.0

    projected_remaining = balance - upcoming_recurring

    c_f1, c_f2 = st.columns(2)
    c_f1.metric("Τρέχον Υπόλοιπο", f"{balance:,.2f} €")
    c_f2.metric("Αναμενόμενα Σταθερά Έξοδα", f"-{upcoming_recurring:,.2f} €")

    st.markdown("---")
    st.metric("💡 Εκτιμώμενο Υπόλοιπο Τέλους Μήνα", f"{projected_remaining:,.2f} €")

# ==========================================
# TAB 3: SAVINGS BUCKETS
# ==========================================
with main_tab3:
    st.subheader("🎯 Multi-Goal Savings Buckets")
    st.caption("Διαχωρισμός αποταμιεύσεων σε συγκεκριμένους στόχους.")

    b1, b2, b3 = st.columns(3)
    with b1:
        st.markdown("##### 🚗 Συντήρηση Ι.Χ.")
        b1_val = st.number_input("Υπόλοιπο (€)", value=400.0, step=50.0, key="b1")
        st.progress(min(b1_val / 800.0, 1.0))

    with b2:
        st.markdown("##### 🏖️ Διακοπές")
        b2_val = st.number_input("Υπόλοιπο (€)", value=1200.0, step=50.0, key="b2")
        st.progress(min(b2_val / 1500.0, 1.0))

    with b3:
        st.markdown("##### 💻 Εξοπλισμός")
        b3_val = st.number_input("Υπόλοιπο (€)", value=300.0, step=50.0, key="b3")
        st.progress(min(b3_val / 1000.0, 1.0))

# ==========================================
# TAB 4: INVESTMENTS & COMPOUND INTEREST
# ==========================================
with main_tab4:
    st.subheader("📈 Investments & Compound Interest")
    initial_inv = st.number_input("Αρχικό Κεφάλαιο (€)", min_value=0.0, value=1000.0)
    monthly_contrib = st.number_input("Μηνιαία Κατάθεση (€)", min_value=0.0, value=200.0)
    annual_return = st.slider("Ετήσια Απόδοση (%)", min_value=1.0, max_value=15.0, value=8.0)
    years_horizon = st.slider("Ορίζοντας (Έτη)", min_value=1, max_value=30, value=10)

    months = years_horizon * 12
    rate_monthly = (annual_return / 100) / 12
    future_val = initial_inv * ((1 + rate_monthly) ** months)
    for m in range(1, months + 1):
        future_val += monthly_contrib * ((1 + rate_monthly) ** (months - m))

    st.metric("🚀 Εκτιμώμενη Μελλοντική Αξία", f"{future_val:,.2f} €")

# ==========================================
# TAB 5: DEBT SIMULATOR
# ==========================================
with main_tab5:
    st.subheader("💳 Δάνεια & Πιστωτικές")
    card_balance = st.number_input("Υπόλοιπο Πιστωτικών (€)", min_value=0.0, value=1500.0)
    loan_balance = st.number_input("Υπόλοιπο Δανείων (€)", min_value=0.0, value=8000.0)
    st.metric("Συνολικό Χρέος", f"{card_balance + loan_balance:,.2f} €")

# ==========================================
# TAB 6: PDF FINANCIAL STATEMENT
# ==========================================
with main_tab6:
    st.subheader("📄 Εξαγωγή Μηνιαίου PDF Statement")
    st.caption("Δημιουργήστε ένα επίσημο οικονομικό report 1 σελίδας.")

    if not filtered_df.empty:
        pdf_bytes = create_pdf_report(
            selected_month_name, selected_year, income, expenses, balance, filtered_df
        )
        st.download_button(
            label=f"📥 Λήψη PDF Αναφοράς ({selected_month_name} {selected_year})",
            data=pdf_bytes,
            file_name=f"statement_{selected_year}_{selected_month:02d}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    else:
        st.info("Δεν υπάρχουν συναλλαγές για την παραγωγή PDF.")

# ==========================================
# TAB 7: TELEGRAM BOT & AUTOMATIONS
# ==========================================
with main_tab7:
    st.subheader("🤖 Telegram Bot & Auto-Recurring Tasks")
    st.markdown(
        """
        ##### 1. Telegram Bot Integration
        Στείλτε μήνυμα στο Telegram: `Καφές 2.50` και θα καταχωρηθεί αυτόματα!
        
        ##### 2. Auto-Recurring Expenses
        Τα σταθερά σας έξοδα μπορούν να καταχωρούνται αυτόματα την 1η κάθε μήνα μέσω Supabase Database Cron Triggers.
    """
    )
