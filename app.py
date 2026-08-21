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
    main_tab8,
) = st.tabs(
    [
        "💰 Dashboard",
        "🔮 Cash Flow",
        "🎯 Buckets",
        "📈 Ετήσια",
        "⚙️ Σταθερά",
        "📋 Checklist",
        "💳 Δάνεια",
        "📄 PDF",
    ]
)

# ==========================================
# TAB 1: DASHBOARD
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

    # QUICK ADD
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
    with st.expander("➕ Πλήρης Καταγραφή Συναλλαγής", expanded=False):
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

            if st.form_submit_button("Καταγραφή") and amount > 0:
                supabase.table("transactions").insert(
                    {
                        "date": str(date),
                        "category": category,
                        "amount": float(amount),
                        "type": t_type,
                        "note": note,
                    }
                ).execute()
                st.success("Καταχωρήθηκε!")
                st.rerun()

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
                    categories_list = ["Σούπερ Μάρκετ", "Λογαριασμοί/Σπίτι", "Καύσιμα/Μεταφορές", "Φαγητό/Καφές", "Ψυχαγωγία", "Μισθός", "Λοιπά"]
                    edit_cat_idx = categories_list.index(selected_row["category"]) if selected_row["category"] in categories_list else 0
                    edit_category = st.selectbox("Νέα Κατηγορία", categories_list, index=edit_cat_idx)
                    edit_note = st.text_input("Νέα Σημείωση", value=str(selected_row["note"]) if selected_row["note"] else "")

                btn_save, btn_delete = st.columns(2)
                with btn_save:
                    if st.form_submit_button("💾 Αποθήκευση"):
                        supabase.table("transactions").update({
                            "date": str(edit_date), "category": edit_category,
                            "amount": float(edit_amount), "type": edit_type, "note": edit_note
                        }).eq("id", selected_tx_id).execute()
                        st.success("Ενημερώθηκε!")
                        st.rerun()
                with btn_delete:
                    if st.form_submit_button("🗑️ Διαγραφή"):
                        supabase.table("transactions").delete().eq("id", selected_tx_id).execute()
                        st.warning("Διαγράφηκε!")
                        st.rerun()

    m1, m2 = st.columns(2)
    m1.metric("Έσοδα", f"+{income:,.2f} €")
    m2.metric("Έξοδα", f"-{expenses:,.2f} €")

    # CHARTS (INCOME vs EXPENSE BAR + DONUT)
    if not filtered_df.empty:
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            fig_compare = go.Figure(data=[
                go.Bar(name='Έσοδα', x=['Σύνολο'], y=[income], marker_color='#30d158'),
                go.Bar(name='Έξοδα', x=['Σύνολο'], y=[expenses], marker_color='#ff453a')
            ])
            fig_compare.update_layout(
                barmode='group', template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(t=10, b=10, l=10, r=10), height=220
            )
            st.plotly_chart(fig_compare, use_container_width=True)

        with chart_col2:
            df_exp = filtered_df[filtered_df["type"] == "Έξοδο"]
            if not df_exp.empty:
                cat_expenses = df_exp.groupby("category")["amount"].sum().reset_index()
                fig_pie = px.pie(
                    cat_expenses, values="amount", names="category", hole=0.6,
                    template="plotly_dark", color_discrete_sequence=["#30d158", "#0a84ff", "#ff453a", "#ffd60a", "#bf5af2", "#8e8e93"]
                )
                fig_pie.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    showlegend=False, margin=dict(t=10, b=10, l=10, r=10), height=220
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
    st.subheader("🔮 Cash Flow Projection")
    try:
        rec_data = supabase.table("recurring_expenses").select("*").execute().data
        upcoming_recurring = sum(float(r["amount"]) for r in rec_data) if rec_data else 0.0
    except Exception:
        upcoming_recurring = 0.0

    projected_remaining = balance - upcoming_recurring
    c_f1, c_f2 = st.columns(2)
    c_f1.metric("Τρέχον Υπόλοιπο", f"{balance:,.2f} €")
    c_f2.metric("Αναμενόμενα Σταθερά", f"-{upcoming_recurring:,.2f} €")
    st.markdown("---")
    st.metric("💡 Εκτιμώμενο Υπόλοιπο Τέλους Μήνα", f"{projected_remaining:,.2f} €")

# ==========================================
# TAB 3: DYNAMIC SAVINGS BUCKETS
# ==========================================
with main_tab3:
    st.subheader("🎯 Multi-Goal Savings Buckets")
    st.caption("Διαχειριστείτε δυναμικά τους αποταμιευτικούς σας στόχους.")

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
                st.session_state["buckets"].append({
                    "name": b_name, "current": float(b_curr), "target": float(b_targ)
                })
                st.success(f"Προστέθηκε: {b_name}")
                st.rerun()

    st.markdown("---")

    if st.session_state["buckets"]:
        for idx, bucket in enumerate(st.session_state["buckets"]):
            col_b1, col_b2, col_b3 = st.columns([3, 2, 1])
            with col_b1:
                st.markdown(f"##### {bucket['name']}")
                b_ratio = max(0.0, min(bucket["current"] / bucket["target"], 1.0))
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
    st.subheader(f"📈 Ετήσια Ανασκόπηση {selected_year}")
    if not df.empty:
        df_year = df[df["date"].dt.year == selected_year]
        if not df_year.empty:
            y_income = df_year[df_year["type"] == "Έσοδο"]["amount"].sum()
            y_expenses = df_year[df_year["type"] == "Έξοδο"]["amount"].sum()
            
            col_y1, col_y2, col_y3 = st.columns(3)
            col_y1.metric("Ετήσια Έσοδα", f"+{y_income:,.2f} €")
            col_y2.metric("Ετήσια Έξοδα", f"-{y_expenses:,.2f} €")
            col_y3.metric("Ετήσιο Καθαρό", f"{y_income - y_expenses:,.2f} €")

            df_year["month"] = df_year["date"].dt.month
            monthly_summary = df_year.groupby(["month", "type"])["amount"].sum().unstack(fill_value=0).reset_index()
            
            fig_annual = px.bar(
                monthly_summary, x="month", y=["Έσοδο", "Έξοδο"] if "Έσοδο" in monthly_summary.columns and "Έξοδο" in monthly_summary.columns else monthly_summary.columns[1:],
                barmode="group", template="plotly_dark",
                color_discrete_map={"Έσοδο": "#30d158", "Έξοδο": "#ff453a"}
            )
            fig_annual.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_annual, use_container_width=True)

# ==========================================
# TAB 5: FIXED RECURRING EXPENSES (WITH DELETE)
# ==========================================
with main_tab5:
    st.subheader("⚙️ Σταθερά Έξοδα (Recurring)")
    st.caption("Πλήρως παραμετροποιήσιμη διαχείριση πάγιων υποχρεώσεων.")

    # Αρχικοποίηση Σταθερών Εξόδων στο Session State
    if "recurring" not in st.session_state:
        st.session_state["recurring"] = [
            {"title": "Ενοίκιο", "amount": 450.0, "due_day": 1},
            {"title": "Internet / Κοινόχρηστα", "amount": 35.0, "due_day": 10},
            {"title": "Συνδρομές (Streaming)", "amount": 15.99, "due_day": 15},
        ]

    # Φόρμα Προσθήκης Νέου Σταθερού Εξόδου
    with st.expander("➕ Προσθήκη Νέου Σταθερού Εξόδου", expanded=False):
        with st.form("add_rec_form", clear_on_submit=True):
            r_title = st.text_input("Τίτλος Εξόδου (π.χ. ΔΕΗ / Ρεύμα)")
            r_amount = st.number_input(
                "Ποσό (€)", min_value=0.0, value=50.0, step=5.0
            )
            r_day = st.number_input(
                "Ημέρα Πληρωμής (1-31)", min_value=1, max_value=31, value=1
            )
            if st.form_submit_button("Προσθήκη Σταθερού") and r_title:
                st.session_state["recurring"].append(
                    {
                        "title": r_title,
                        "amount": float(r_amount),
                        "due_day": int(r_day),
                    }
                )
                st.success(f"Προστέθηκε: {r_title}")
                st.rerun()

    st.markdown("---")

    # Προβολή, Επεξεργασία & Αφαίρεση Σταθερών Εξόδων
    if st.session_state["recurring"]:
        total_rec = sum(item["amount"] for item in st.session_state["recurring"])
        st.markdown(f"##### 📌 Συνολικά Σταθερά Έξοδα: **{total_rec:,.2f} €/μήνα**")
        st.markdown("<br>", unsafe_allow_html=True)

        for idx, item in enumerate(st.session_state["recurring"]):
            col_r1, col_r2, col_r3, col_r4 = st.columns([3, 2, 2, 1])

            with col_r1:
                st.markdown(f"**{item['title']}**")
                st.caption(f"Πληρωμή στις {item['due_day']} του μηνός")

            with col_r2:
                # Δυνατότητα αλλαγής ποσού επί τόπου
                new_amt = st.number_input(
                    "Ποσό (€)",
                    min_value=0.0,
                    value=float(item["amount"]),
                    step=5.0,
                    key=f"rec_amt_{idx}",
                )
                if new_amt != item["amount"]:
                    st.session_state["recurring"][idx]["amount"] = new_amt
                    st.rerun()

            with col_r3:
                # Δυνατότητα αλλαγής ημέρας πληρωμής
                new_day = st.number_input(
                    "Ημέρα",
                    min_value=1,
                    max_value=31,
                    value=int(item["due_day"]),
                    key=f"rec_day_{idx}",
                )
                if new_day != item["due_day"]:
                    st.session_state["recurring"][idx]["due_day"] = new_day
                    st.rerun()

            with col_r4:
                st.markdown("<br>", unsafe_allow_html=True)
                # ΚΟΥΜΠΙ ΔΙΑΓΡΑΦΗΣ
                if st.button("🗑️", key=f"del_rec_{idx}"):
                    st.session_state["recurring"].pop(idx)
                    st.toast(f"Διαγράφηκε: {item['title']}", icon="🗑️")
                    st.rerun()

            st.markdown("---")
    else:
        st.info("Δεν έχετε καταχωρημένα σταθερά έξοδα. Προσθέστε ένα παραπάνω!")

# ==========================================
# TAB 6: WEEKLY CHECKLIST
# ==========================================
with main_tab6:
    st.subheader("📋 Εβδομαδιαίο Checklist")
    st.caption("Προσθέστε, τσεκάρετε ή διαγράψτε εργασίες.")

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
    st.subheader("💳 Δάνεια & Πιστωτικές")
    card_balance = st.number_input("Υπόλοιπο Πιστωτικών (€)", min_value=0.0, value=1500.0)
    loan_balance = st.number_input("Υπόλοιπο Δανείων (€)", min_value=0.0, value=8000.0)
    st.metric("Συνολικό Χρέος", f"{card_balance + loan_balance:,.2f} €")

# ==========================================
# TAB 8: PDF STATEMENT
# ==========================================
with main_tab8:
    st.subheader("📄 Εξαγωγή PDF Statement")
    if not filtered_df.empty:
        pdf_bytes = create_pdf_report(selected_month_name, selected_year, income, expenses, balance, filtered_df)
        st.download_button(
            label=f"📥 Λήψη PDF Αναφοράς ({selected_month_name} {selected_year})",
            data=pdf_bytes, file_name=f"statement_{selected_year}_{selected_month:02d}.pdf",
            mime="application/pdf", use_container_width=True
        )
    else:
        st.info("Δεν υπάρχουν συναλλαγές για την παραγωγή PDF.")
