import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import gspread
import pytz 
import numpy as np

# Define the timezone for Central Time (CDT/CST)
CENTRAL_TZ = pytz.timezone('America/Chicago')

# --- Page Configuration ---
st.set_page_config(
    page_title="Trading Performance Tracker",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Robinhood Dark Green Styling ---
st.markdown("""
    <style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    
    /* --- COLOR PALETTE (Robinhood Inspired) --- */
    /* BG Primary: #17191e */
    /* BG Secondary: #212328 */
    /* Accent Green: #00C800 (Vibrant Green) */
    /* Accent Red: #FF5353 (Vibrant Red) */
    /* Text Light: #E0E7FF */

    /* Main background and theme */
    .main {
        background: linear-gradient(135deg, #17191e 0%, #212328 100%);
        background-attachment: fixed;
        font-family: 'Inter', sans-serif;
    }
    
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        background: rgba(33, 35, 40, 0.8); /* Slightly lighter background for content blocks */
        backdrop-filter: blur(5px);
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4);
        border: 1px solid rgba(0, 200, 0, 0.1); /* Subtle green border */
        margin: 1rem auto;
    }
    
    /* Header styling */
    h1 {
        color: #f8fafc;
        font-weight: 800;
        font-size: 3rem !important;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(135deg, #00C800, #3AD866); /* Vibrant green gradient */
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-shadow: 0 0 10px rgba(0, 200, 0, 0.3);
    }
    
    h2, h3 {
        color: #E0E7FF;
        font-weight: 700;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #17191e 0%, #292c31 100%);
        border-right: 1px solid rgba(0, 200, 0, 0.2);
    }
    
    [data-testid="stSidebar"] h3 {
        color: #f8fafc !important;
        text-shadow: 0 0 5px rgba(0, 200, 0, 0.5);
    }
    
    /* Metric cards styling */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 800;
        color: #f8fafc;
    }
    
    /* Positive delta (Profit) */
    [data-testid="stMetricDelta"] {
        color: #00C800; /* Vibrant Green */
    }
    
    /* Negative delta (Loss) */
    [data-testid="stMetricDelta"][data-baseweb="badge"]::before {
        content: "▼";
        color: #FF5353 !important; /* Vibrant Red */
    }
    [data-testid="stMetricDelta"][data-baseweb="badge"] {
        color: #FF5353 !important;
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #212328; 
        border-radius: 8px;
        padding: 0.3rem;
        border: 1px solid rgba(0, 200, 0, 0.1);
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #292c31; 
        color: #E0E7FF;
        border-radius: 6px;
        transition: all 0.2s ease;
    }
    
    .stTabs [aria-selected="true"] {
        background: #00C800 !important; /* Solid vibrant green for active tab */
        color: #17191e !important; /* Dark text on green tab */
        font-weight: 700;
        box-shadow: 0 2px 10px rgba(0, 200, 0, 0.5);
    }
    
    /* Form styling */
    .stForm {
        background: #212328;
        border-radius: 10px;
        padding: 1.5rem;
        border: 1px solid rgba(0, 200, 0, 0.1);
    }
    
    /* Input fields */
    .stTextInput input, .stNumberInput input, .stSelectbox div, .stDateInput input {
        background-color: #292c31 !important;
        color: #E0E7FF !important;
        border: 1px solid rgba(0, 200, 0, 0.3) !important;
        border-radius: 6px;
        transition: all 0.2s ease;
    }
    
    .stTextInput input:focus, .stNumberInput input:focus, .stSelectbox div:focus, .stDateInput input:focus {
        border-color: #00C800 !important;
        box-shadow: 0 0 0 3px rgba(0, 200, 0, 0.2) !important;
    }
    
    .stTextInput label, .stNumberInput label, .stSelectbox label, .stDateInput label {
        color: #E0E7FF !important;
    }
    
    /* Button styling (Primary: Green, Secondary: Red) */
    .stButton button[kind="primary"] {
        background-color: #00C800; /* Vibrant Green */
        color: #17191e;
        font-weight: 700;
        border: none;
        box-shadow: 0 4px 15px rgba(0, 200, 0, 0.4);
    }
    .stButton button[kind="primary"]:hover {
        background-color: #3AD866;
        transform: translateY(-1px);
    }
    
    .stButton button[kind="secondary"] {
        background-color: #FF5353; /* Vibrant Red for reset/danger */
        color: white;
        border: none;
        box-shadow: 0 4px 15px rgba(255, 83, 83, 0.4);
    }
    .stButton button[kind="secondary"]:hover {
        background-color: #E64B4B;
        transform: translateY(-1px);
    }

    /* Success/Error messages */
    .stSuccess {
        background-color: rgba(0, 200, 0, 0.2);
        color: #00C800;
        border-left: 4px solid #00C800;
    }
    
    .stError {
        background-color: rgba(255, 83, 83, 0.2);
        color: #FF5353;
        border-left: 4px solid #FF5353;
    }
    
    /* Info box */
    .stInfo {
        background: rgba(0, 200, 0, 0.1);
        border-left: 4px solid #00C800;
        color: #E0E7FF;
    }
    
    /* Chart containers */
    .js-plotly-plot {
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
        background: #212328;
        padding: 1rem;
    }
    
    /* Divider */
    hr {
        background: rgba(0, 200, 0, 0.1);
    }

    /* Custom style for the progress bar */
    /* Progress bar track (background) */
    .stProgress > div > div > div:first-child {
        background-color: #292c31 !important; 
        border-radius: 5px;
    }
    
    /* Custom color logic for the progress fill */
    .stProgress > div > div > div > div {
        /* Default to success color (Green) */
        background-color: #00C800 !important;
    }

    /* Style for loss state in the progress bar (Red) */
    .stProgress.loss > div > div > div > div {
        background-color: #FF5353 !important; 
    }
    
    /* Style for progress state in the progress bar (Subtle Green) */
    .stProgress.progress > div > div > div > div {
        background-color: #00C800 !important; /* Keep it vibrant green for progress */
    }

    </style>
""", unsafe_allow_html=True)


# --- Configuration and Setup ---
if "gsheets" not in st.secrets or "sheet_id" not in st.secrets["gsheets"]:
    st.error("Google Sheets configuration is missing. Please ensure 'gsheets.sheet_id' is set in your secrets.")
    SHEET_ID = None
else:
    SHEET_ID = st.secrets["gsheets"]["sheet_id"]


# --- Utility Functions for Google Sheets Interaction (REMAINS THE SAME) ---

@st.cache_resource(ttl=3600)
def connect_gsheets():
    """Authenticates and returns a gspread client object."""
    if not SHEET_ID: return None
    try:
        client = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
        return client
    except Exception as e:
        st.error(f"Error connecting to Google Sheets. Check 'gcp_service_account' in secrets: {e}")
        return None

@st.cache_data(ttl=60)
def get_data_from_sheet(sheet_name):
    """Retrieves data from a specific sheet as a pandas DataFrame using core gspread."""
    gc = connect_gsheets()
    if not gc: return pd.DataFrame()
    try:
        spreadsheet = gc.open_by_key(SHEET_ID)
        worksheet = spreadsheet.worksheet(sheet_name)
        
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        
        df = df.dropna(how='all')
        
        return df
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Worksheet '{sheet_name}' not found. Please ensure your Google Sheet has tabs named 'trades' and 'daily_summary'.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error reading data from sheet '{sheet_name}': {e}")
        return pd.DataFrame()


def write_data_to_sheet(sheet_name, df, mode='append'):
    """Writes a DataFrame to a specific sheet using core gspread."""
    gc = connect_gsheets()
    if not gc: return False
    try:
        spreadsheet = gc.open_by_key(SHEET_ID)
        worksheet = spreadsheet.worksheet(sheet_name)
        
        data_to_write = df.values.tolist()
        
        if mode == 'append':
            worksheet.append_rows(data_to_write, value_input_option='USER_ENTERED')
            
        elif mode == 'replace':
            header = [str(col) for col in df.columns.tolist()]
            full_data = [header] + data_to_write
            
            worksheet.clear()
            worksheet.update('A1', full_data, value_input_option='USER_ENTERED')
        
        get_data_from_sheet.clear()
        
        return True
    except Exception as e:
        st.error(f"Error writing data to sheet '{sheet_name}': {e}")
        return False

# --- Core Business Logic: Recalculate Summaries (CRITICAL - CST FIX INCLUDED) ---

def recalculate_all_summaries(initial_balance=2283.22):
    """
    Reads the full trade history, recalculates daily summaries, and updates the sheet.
    This function is run after every trade or deposit entry.
    """
    if not SHEET_ID: return pd.DataFrame()
    
    # Get the current date in the target timezone (CST/CDT)
    today_date = datetime.now(CENTRAL_TZ).date()
    today_date_str = today_date.strftime("%Y-%m-%d")

    df_trades = get_data_from_sheet('trades')
    
    # --- 1. Initial State if No Trades ---
    if df_trades.empty or df_trades.shape[0] == 0:
        summary_data = {
            'Date': [today_date_str],
            'Week': [f'Wk {today_date.isocalendar()[1]}'],
            'Trades': [0],
            'Start Bal.': [initial_balance],
            'Target P&L': [initial_balance * 0.065],
            'Actual P&L': [0.0],
            'Deposit/Bonus': [0.0],
            'End Bal.': [initial_balance],
        }
        df_summary = pd.DataFrame(summary_data)
        write_data_to_sheet('daily_summary', df_summary, mode='replace')
        return df_summary

    # --- 2. Processing Trades & Recalculating History ---
    try:
        df_trades['trade_date'] = pd.to_datetime(df_trades['trade_date'], errors='coerce').dt.date.fillna(pd.NaT).ffill()
        df_trades['pnl'] = pd.to_numeric(df_trades['pnl'], errors='coerce').fillna(0)
    except Exception as e:
        st.error(f"Error processing trade data types: {e}.")
        return pd.DataFrame()

    df_trades = df_trades.sort_values(by='trade_date')
    daily_groups = df_trades.groupby('trade_date')

    daily_summary_list = []
    current_balance = initial_balance
    
    for date, group in daily_groups:
        total_pl = group['pnl'].sum()
        num_trades = group.shape[0]
        
        start_balance = current_balance
        end_balance = start_balance + total_pl
        target_pl = start_balance * 0.065
        if start_balance <= 0: target_pl = 0
        
        week_num = datetime.combine(date, datetime.min.time()).isocalendar()[1]
             
        daily_summary_list.append({
            'Date': date.strftime("%Y-%m-%d"),
            'Week': f'Wk {week_num}',
            'Trades': num_trades,
            'Start Bal.': round(start_balance, 2),
            'Target P&L': round(target_pl, 2),
            'Actual P&L': round(total_pl, 2),
            'Deposit/Bonus': 0.00,
            'End Bal.': round(end_balance, 2),
        })
        current_balance = end_balance 

    df_summary = pd.DataFrame(daily_summary_list)
    df_summary['Date'] = df_summary['Date'].astype(str)
    
    # --- 3. Re-integrate deposits/bonuses and Recalculate Balances ---
    df_old_summary = get_data_from_sheet('daily_summary')
    if not df_old_summary.empty:
        df_old_summary['Date'] = pd.to_datetime(df_old_summary['Date'], errors='coerce').dt.date.astype(str)
        df_summary['Date'] = pd.to_datetime(df_summary['Date'], errors='coerce').dt.date.astype(str)
        
        df_merged = pd.merge(df_summary, df_old_summary[['Date', 'Deposit/Bonus']], on='Date', how='left', suffixes=('_new', '_old'))
        
        df_merged['Deposit/Bonus'] = pd.to_numeric(df_merged['Deposit/Bonus_old'], errors='coerce').fillna(0.00)
        
        df_summary = df_merged[['Date', 'Week', 'Trades', 'Start Bal.', 'Target P&L', 'Actual P&L', 'Deposit/Bonus', 'End Bal.']]
        
        # Recalculate balances with Deposit/Bonus applied
        current_balance_recalc = initial_balance
        new_summary_list = []
        for index, row in df_summary.iterrows():
            deposit = row['Deposit/Bonus']
            actual_pl = row['Actual P&L'] 
            start_balance = current_balance_recalc
            end_balance = start_balance + actual_pl + deposit 
            target_pl = start_balance * 0.065
            if start_balance <= 0:
                 target_pl = 0
            
            new_summary_list.append({
                'Date': row['Date'],
                'Week': row['Week'],
                'Trades': row['Trades'],
                'Start Bal.': round(start_balance, 2),
                'Target P&L': round(target_pl, 2),
                'Actual P&L': round(actual_pl, 2),
                'Deposit/Bonus': round(deposit, 2),
                'End Bal.': round(end_balance, 2),
            })
            current_balance_recalc = end_balance 
        
        df_summary = pd.DataFrame(new_summary_list)
        df_summary['Date'] = df_summary['Date'].astype(str)
        
    # --- 4. FIX: Add today's entry ONLY if the last recorded day is NOT today ---
    if not df_summary.empty:
        last_recorded_date_str = df_summary['Date'].iloc[-1]
        
        if last_recorded_date_str != today_date_str:
            
            last_end_bal = df_summary['End Bal.'].iloc[-1]
            today_start_bal = last_end_bal
            today_target_pl = today_start_bal * 0.065
            
            new_row = pd.DataFrame([{
                'Date': today_date_str,
                'Week': f'Wk {today_date.isocalendar()[1]}',
                'Trades': 0,
                'Start Bal.': round(today_start_bal, 2),
                'Target P&L': round(today_target_pl, 2),
                'Actual P&L': 0.0,
                'Deposit/Bonus': 0.0,
                'End Bal.': round(today_start_bal, 2),
            }])
            
            df_summary = pd.concat([df_summary, new_row], ignore_index=True)


    if not df_summary.empty:
        write_data_to_sheet('daily_summary', df_summary, mode='replace')
        st.toast("✅ Daily summaries recalculated successfully!", icon="✅")
        
    return df_summary

# --- Data Loading and Caching (REMAINS THE SAME) ---

def load_data():
    """Load data for the UI."""
    df_summary = get_data_from_sheet('daily_summary')
    df_trades = get_data_from_sheet('trades')
    
    if not df_summary.empty:
        try:
            if 'Date' in df_summary.columns:
                df_summary['Date'] = pd.to_datetime(df_summary['Date'], errors='coerce').dt.date
            
            numeric_cols = ['Start Bal.', 'Target P&L', 'Actual P&L', 'Deposit/Bonus', 'End Bal.', 'Trades']
            for col in numeric_cols:
                if col in df_summary.columns:
                     df_summary[col] = pd.to_numeric(df_summary[col], errors='coerce').fillna(0)
            
            df_summary = df_summary.sort_values(by='Date')

        except Exception as e:
            st.warning(f"Could not convert summary data types: {e}")
            df_summary = pd.DataFrame()

    if not df_trades.empty:
        try:
            if 'trade_date' in df_trades.columns:
                df_trades['trade_date'] = pd.to_datetime(df_trades['trade_date'], errors='coerce').dt.date
            if 'pnl' in df_trades.columns:
                df_trades['pnl'] = pd.to_numeric(df_trades['pnl'], errors='coerce').fillna(0)
            if 'pnl_pct' in df_trades.columns:
                df_trades['pnl_pct'] = pd.to_numeric(df_trades['pnl_pct'], errors='coerce').fillna(0)
            if 'leverage' in df_trades.columns:
                df_trades['leverage'] = pd.to_numeric(df_trades['leverage'], errors='coerce').fillna(1.0)
            if 'investment' in df_trades.columns:
                df_trades['investment'] = pd.to_numeric(df_trades['investment'], errors='coerce').fillna(0)

        except Exception as e:
            st.warning(f"Could not convert trades data types: {e}")
            df_trades = pd.DataFrame()
            
    return df_summary, df_trades

# --- Initialize App and State ---

if 'initial_balance' not in st.session_state:
    st.session_state.initial_balance = 2272.22 

# Load data initially to set the starting balance correctly
df_summary_temp, df_trades_temp = load_data() 
if not df_summary_temp.empty and 'Start Bal.' in df_summary_temp.columns:
    st.session_state.initial_balance = df_summary_temp['Start Bal.'].iloc[0]
    
# Immediate recalculation with the timezone-aware date logic
recalculate_all_summaries(st.session_state.initial_balance)
df_summary, df_trades = load_data()


# --- Sidebar: Quick Stats (RESTORED) ---

with st.sidebar:
    st.markdown("### 📊 Quick Stats")
    
    current_balance = df_summary['End Bal.'].iloc[-1] if not df_summary.empty else st.session_state.initial_balance
    
    
    st.metric(
        label="💰 Current Balance",
        value=f"${current_balance:,.2f}",
        delta=f"${current_balance - st.session_state.initial_balance:,.2f}",
        delta_color="normal"
    )

    total_trades = df_trades.shape[0] if not df_trades.empty else 0
    st.metric(label="🔄 Total Trades", value=total_trades)
    
    latest_week = df_summary['Week'].iloc[-1] if not df_summary.empty else 'Wk 1'
    st.metric(label="📅 Current Week", value=latest_week)

    total_pl = df_summary['Actual P&L'].sum() if not df_summary.empty else 0.0
    total_pl_percent = (total_pl / st.session_state.initial_balance) * 100 if st.session_state.initial_balance > 0 else 0
    st.metric(
        label="📈 Total Trading P&L",
        value=f"${total_pl:,.2f}",
        delta=f"{total_pl_percent:.2f}%",
        delta_color="normal"
    )
    
    st.divider()
    
    # Reset App Section
    st.markdown("### ⚠️ Danger Zone")
    with st.expander("🗑️ Reset All Data", expanded=False):
        st.warning("⚠️ This will permanently delete ALL trades and summaries. This action cannot be undone!")
        
        reset_confirmation = st.text_input(
            "Type 'DELETE' to confirm:",
            key="reset_confirm",
            help="Type DELETE in capital letters to enable the reset button"
        )
        
        reset_button = st.button(
            "🗑️ Reset App & Delete All Data",
            type="secondary",
            disabled=(reset_confirmation != "DELETE"),
            use_container_width=True
        )
        
        if reset_button and reset_confirmation == "DELETE":
            try:
                gc = connect_gsheets()
                if gc:
                    spreadsheet = gc.open_by_key(SHEET_ID)
                    
                    # Clear trades sheet
                    trades_sheet = spreadsheet.worksheet('trades')
                    trades_sheet.clear()
                    # Add headers back
                    trades_sheet.update('A1', [['trade_date', 'ticker', 'leverage', 'direction', 'investment', 'pnl', 'pnl_pct']])
                    
                    # Clear daily summary sheet
                    summary_sheet = spreadsheet.worksheet('daily_summary')
                    summary_sheet.clear()
                    # Add headers back
                    summary_sheet.update('A1', [['Date', 'Week', 'Trades', 'Start Bal.', 'Target P&L', 'Actual P&L', 'Deposit/Bonus', 'End Bal.']])
                    
                    # Clear all caches
                    st.cache_data.clear()
                    st.cache_resource.clear()
                    
                    st.success("✅ All data has been deleted successfully!")
                    st.balloons()
                    
                    # Wait a moment then rerun
                    import time
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Failed to connect to Google Sheets")
            except Exception as e:
                st.error(f"❌ Error resetting app: {e}")
            

# --- Main Page: Title and Tabs ---
st.markdown("# 📈 Trading Performance Tracker")

tab1, tab2, tab3 = st.tabs(["💵 Trade Entry", "🗓️ Daily Summary", "📊 Analytics"])

# --- Tab 1: Trade Entry Form (with Progress Bar) ---
with tab1:
    
    # === Today's Performance Snapshot ===
    st.subheader("🎯 Today's Performance Snapshot (CST/CDT)")
    
    # Get Today's Date Object using the defined timezone
    today_date_obj = datetime.now(CENTRAL_TZ).date()

    # Find Today's Summary Row (Guaranteed to exist now)
    df_today = df_summary[df_summary['Date'] == today_date_obj]
    
    if not df_today.empty:
        today_target_pl = df_today['Target P&L'].iloc[0]
        today_actual_pl = df_today['Actual P&L'].iloc[0]
        
        # --- PROGRESS BAR LOGIC (CST/Data-Aware) ---
        
        if today_target_pl > 0:
            
            st.info(f"**Target P&L for Today ({today_date_obj.strftime('%b %d')}):** `${today_target_pl:,.2f}`")
            
            # --- Determine State and Style ---
            progress_css_class = ""
            if today_actual_pl >= today_target_pl:
                # Target HIT!
                fill_ratio = 1.0
                fill_value = 100
                label_text = f"**Target HIT!** (P&L: ${today_actual_pl:,.2f})"
                progress_css_class = "" # Uses default green from CSS
                
            elif today_actual_pl > 0:
                # Making Progress
                fill_ratio = today_actual_pl / today_target_pl 
                fill_value = int(fill_ratio * 100)
                label_text = f"**Making Progress:** {fill_value:.1f}% of Target (P&L: ${today_actual_pl:,.2f})"
                progress_css_class = "progress" # Uses green class
                
            else: # Loss or Breakeven (Actual P&L <= 0)
                # Loss/Behind Target
                fill_value = 0 
                label_text = f"**LOSS/Behind Target:** (P&L: ${today_actual_pl:,.2f})"
                progress_css_class = "loss" # Uses red class
                
            # Embed custom CSS for coloring the bar based on loss/progress/hit
            st.markdown(
                f"""
                <style>
                /* Inject custom CSS class to control the bar color */
                .stProgress > div > div > div > div {{
                    background-color: {'#FF5353' if progress_css_class == 'loss' else ('#00C800')} !important;
                }}
                </style>
                """,
                unsafe_allow_html=True
            )
            
            # Display Progress Bar.
            st.progress(
                value=min(100, fill_value), 
                text=label_text 
            )
            
        else:
            st.info(f"Today's P&L: **${today_actual_pl:,.2f}** (Target P&L is $0.00 or balance is negative).")

    else:
        st.warning(f"Could not retrieve summary data for {today_date_obj.strftime('%Y-%m-%d')}. Please refresh or ensure a trade/deposit has been entered.")

    st.markdown("---") 
    
    st.header("Log a New Trade")
    
    with st.form("Trade Entry Form"):
        
        col_1a, col_1b, col_1c, col_1d = st.columns(4)
        with col_1a:
            trade_date = st.date_input("📅 Trade Date", datetime.now(CENTRAL_TZ).date()) # Use CST/CDT
        with col_1b:
            ticker = st.text_input("🏷️ Ticker", help="e.g., GOOG, EURUSD")
        with col_1c:
            direction = st.selectbox("📊 Direction", ["Long", "Short", "Other"])
        with col_1d:
            leverage = st.number_input("⚡ Leverage (x)", min_value=1.0, value=1.0, step=0.5)

        col_2a, col_2b, col_2c = st.columns(3)
        with col_2a:
            investment = st.number_input("💰 Investment ($)", min_value=0.01, value=1000.00, step=100.0, format="%.2f")
        with col_2b:
            pnl = st.number_input("💵 P&L ($)", help="Profit (+), Loss (-)", format="%.2f")
        with col_2c:
            pnl_pct = st.number_input("📊 P&L %", help="e.g., 5.5 for 5.5%", format="%.2f")
        
        st.markdown("---")
        submitted = st.form_submit_button("✅ Submit Trade", type="primary", use_container_width=True)

        if submitted:
            if not ticker.strip():
                st.error("❌ Ticker cannot be empty.")
            elif investment <= 0:
                st.error("❌ Investment must be greater than zero.")
            else:
                new_trade_data = pd.DataFrame([{
                    'trade_date': trade_date.strftime("%Y-%m-%d"),
                    'ticker': ticker.upper(),
                    'leverage': leverage,
                    'direction': direction,
                    'investment': investment,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct,
                }])
                
                if write_data_to_sheet('trades', new_trade_data, mode='append'):
                    st.success("✅ Trade successfully logged!")
                    st.rerun()
                else:
                    st.error("❌ Failed to log trade to Google Sheet.")


# --- Tab 2: Daily Summary ---
with tab2:
    st.header("Daily Summary")
    
    if df_summary.empty:
        st.info("ℹ️ No summary data available. Enter trades or refresh the page after configuration.")
    else:
        df_display = df_summary.copy()
        
        # Sort by Date and convert back to string for clean table display
        if 'Date' in df_display.columns:
            df_display = df_display.sort_values(by='Date', ascending=False)
            df_display['Date'] = df_display['Date'].astype(str)
        
        # Format currency columns
        currency_cols = ['Start Bal.', 'Target P&L', 'Actual P&L', 'Deposit/Bonus', 'End Bal.']
        for col in currency_cols:
             if col in df_display.columns:
                df_display[col] = pd.to_numeric(df_display[col], errors='coerce').fillna(0).apply(lambda x: f"${x:,.2f}")

        cols_to_keep = ['Date', 'Week', 'Trades', 'Start Bal.', 'Target P&L', 'Actual P&L', 'Deposit/Bonus', 'End Bal.']
        df_display = df_display[[col for col in cols_to_keep if col in df_display.columns]]
            
        st.dataframe(
            df_display, 
            use_container_width=True,
            hide_index=True
        )
        
        st.subheader("📈 Balance Progression")
        
        df_chart = df_summary.sort_values(by='Date', ascending=True)

        fig = go.Figure()
        
        # 1. End Balance (The main purple/accent line, now a lighter green/white)
        fig.add_trace(go.Scatter(
            x=df_chart['Date'].astype(str),
            y=df_chart['End Bal.'],
            mode='lines+markers',
            name='End Balance',
            line=dict(color='white', width=3, shape='spline'), # Use white for high contrast
            marker=dict(size=8, color='#00C800', line=dict(color='#17191e', width=2)),
            fill='tozeroy',
            fillcolor='rgba(0, 200, 0, 0.1)' # Subtle green fill
        ))
        
        # 2. Start Balance (Dotted Line - maybe a light gray/yellow)
        fig.add_trace(go.Scatter(
            x=df_chart['Date'].astype(str),
            y=df_chart['Start Bal.'],
            mode='lines+markers',
            name='Start Balance',
            line=dict(color='#AAAAAA', width=2, dash='dot'), 
            marker=dict(size=6, color='#CCCCCC')
        ))

        # 3. Target End Balance (Dashed Line - vibrant green)
        fig.add_trace(go.Scatter(
            x=df_chart['Date'].astype(str),
            y=df_chart['Start Bal.'] + df_chart['Target P&L'],
            mode='lines',
            name='Target End Bal',
            line=dict(color='#00C800', width=2, dash='dash')
        ))
        
        # Determine y-axis range dynamically with padding
        if not df_chart.empty:
            min_bal = df_chart[['End Bal.', 'Start Bal.']].min().min()
            max_bal = df_chart[['End Bal.', 'Start Bal.']].max().max()
            padding = (max_bal - min_bal) * 0.1 
            y_range = [max(0, min_bal - padding), max_bal + padding]
        else:
            y_range = [0, 100]


        fig.update_layout(
            title='Balance Progression Over Time',
            xaxis_title="Date", 
            yaxis_title="Balance ($)",
            hovermode='x unified',
            height=450,
            plot_bgcolor='#212328', # Content background
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Inter, sans-serif", size=12, color="#E0E7FF"),
            title_font=dict(size=20, color='#f8fafc', family="Inter"),
            legend=dict(
                orientation="h", 
                yanchor="bottom", y=1.02, xanchor="right", x=1, 
                bgcolor='rgba(0,0,0,0)',
                font=dict(color="#E0E7FF")
            ),
            xaxis=dict(
                showgrid=True, 
                gridcolor='rgba(0, 200, 0, 0.1)', # Subtle grid lines
                tickfont=dict(color='#E0E7FF'),
                tickformat="%b %d<br>%Y",
                dtick='d' # Fix: Ensure one tick per date
            ),
            yaxis=dict(
                showgrid=True, 
                gridcolor='rgba(0, 200, 0, 0.1)', # Subtle grid lines
                tickfont=dict(color='#E0E7FF'),
                autorange=False, 
                range=y_range 
            ),
            margin=dict(t=50) 
        )
        st.plotly_chart(fig, use_container_width=True)

# --- Tab 3: Performance Analytics ---
with tab3:
    st.header("Performance Analytics")
    
    if df_trades.empty:
        st.info("ℹ️ No trade data yet. Start logging trades to see analytics!")
    else:
        
        # === Date Filter ===
        all_dates_summary = df_summary['Date'].unique()
        all_dates_trades = df_trades['trade_date'].unique()
        
        all_available_dates = pd.to_datetime(list(all_dates_summary) + list(all_dates_trades)).unique()
        
        min_date_overall = min(all_available_dates) if len(all_available_dates) > 0 else datetime.now(CENTRAL_TZ).date()
        max_date_overall = max(all_available_dates) if len(all_available_dates) > 0 else datetime.now(CENTRAL_TZ).date()
        
        col_start_date, col_end_date = st.columns(2)
        
        with col_start_date:
            start_date = st.date_input("Start Date", value=min_date_overall, min_value=min_date_overall, max_value=max_date_overall)
        
        with col_end_date:
            end_date = st.date_input("End Date", value=max_date_overall, min_value=min_date_overall, max_value=max_date_overall)

        if start_date > end_date:
            st.error("❌ Error: Start Date must be before or the same as End Date.")
            df_summary_filtered = pd.DataFrame()
            df_trades_filtered = pd.DataFrame()
        else:
            df_summary_filtered = df_summary[
                (df_summary['Date'] >= start_date) & 
                (df_summary['Date'] <= end_date)
            ]
            
            df_trades_filtered = df_trades[
                (df_trades['trade_date'] >= start_date) & 
                (df_trades['trade_date'] <= end_date)
            ]

        st.markdown("---")
        
        if df_summary_filtered.empty or df_trades_filtered.empty:
            st.info("ℹ️ No trading data found for the selected date range.")
            
        else:
            col_pnl, col_winrate = st.columns(2)
            
            # --- Daily P&L Chart ---
            with col_pnl:
                st.subheader("💵 Daily P&L Chart")
                
                df_chart_pnl = df_summary_filtered.sort_values(by='Date', ascending=True)
                
                # Use Robinhood green/red
                colors = ['#00C800' if x > 0 else '#FF5353' for x in df_chart_pnl['Actual P&L']]
                
                fig_pnl = go.Figure()
                
                fig_pnl.add_trace(go.Bar(
                    x=df_chart_pnl['Date'].astype(str),
                    y=df_chart_pnl['Actual P&L'],
                    marker_color=colors,
                    name='Daily P&L',
                    text=df_chart_pnl['Actual P&L'].apply(lambda x: f'${x:,.2f}'),
                    textposition='auto', 
                    textfont=dict(color='#17191e', size=11), # Dark text on bright bars
                    marker=dict(line=dict(color='rgba(0, 0, 0, 0.3)', width=1))
                ))
                
                fig_pnl.update_layout(
                    title=f'Daily Trading P&L ({start_date.strftime("%b %d")} - {end_date.strftime("%b %d")})',
                    xaxis_title="Date", 
                    yaxis_title="P&L ($)",
                    height=450,
                    plot_bgcolor='#212328',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(family="Inter, sans-serif", size=12, color="#E0E7FF"),
                    title_font=dict(size=18, color='#f8fafc', family="Inter"),
                    xaxis=dict(
                        showgrid=True, 
                        gridcolor='rgba(0, 200, 0, 0.1)',
                        tickfont=dict(color='#E0E7FF'),
                        tickformat="%b %d<br>%Y" ,
                        dtick='d' # Fix: Ensure one tick per date
                    ),
                    yaxis=dict(
                        showgrid=True, 
                        gridcolor='rgba(0, 200, 0, 0.1)', 
                        zeroline=True, 
                        zerolinecolor='rgba(0, 200, 0, 0.3)',
                        tickfont=dict(color='#E0E7FF')
                    ),
                    margin=dict(t=50)
                )
                st.plotly_chart(fig_pnl, use_container_width=True)
                
            # --- Trade Win/Loss Breakdown ---
            with col_winrate:
                st.subheader("🎯 Trade Win/Loss Breakdown")
                
                df_trades_temp = df_trades_filtered.copy()
                df_trades_temp['Result'] = df_trades_temp['pnl'].apply(lambda x: 'Win' if x > 0 else ('Loss' if x < 0 else 'Breakeven'))
                
                result_counts = df_trades_temp['Result'].value_counts().reset_index()
                result_counts.columns = ['Result', 'Count']

                # Ensure all categories (Win, Loss, Breakeven) are present for consistent coloring
                all_results = pd.DataFrame({'Result': ['Win', 'Loss', 'Breakeven'], 'Count': [0, 0, 0]})
                result_counts = pd.merge(all_results, result_counts, on='Result', how='left', suffixes=('_all', '')).fillna(0)
                result_counts['Count'] = result_counts['Count_all'] + result_counts['Count'] 
                result_counts = result_counts[['Result', 'Count']]
                result_counts = result_counts[result_counts['Count'] > 0] 
                
                # Define colors for Pie chart
                pie_colors = {
                    'Win': '#00C800',
                    'Loss': '#FF5353',
                    'Breakeven': '#AAAAAA'
                }
                
                sorted_results = result_counts['Result'].map(pie_colors).dropna().tolist()
                
                fig_pie = go.Figure(data=[go.Pie(
                    labels=result_counts['Result'],
                    values=result_counts['Count'],
                    hole=0.4,
                    marker=dict(colors=sorted_results), 
                    textfont=dict(size=16, color='white', family='Inter'),
                    textinfo='label+percent'
                )])
                
                fig_pie.update_layout(
                    title=f'Trade Outcomes ({df_trades_filtered.shape[0]} trades total)',
                    height=450,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(family="Inter, sans-serif", size=12, color="#E0E7FF"),
                    title_font=dict(size=18, color='#f8fafc', family="Inter"),
                    showlegend=True,
                    legend=dict(font=dict(color='#E0E7FF')),
                    margin=dict(t=50)
                )
                st.plotly_chart(fig_pie, use_container_width=True)