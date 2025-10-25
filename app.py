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

# --- PASSWORD PROTECTION ---
def check_password():
    """Returns `True` if the user had the correct password."""
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        # Get password from secrets, handle both quoted and unquoted formats
        correct_password = str(st.secrets.get("app_password", "trading123")).strip().strip('"').strip("'")
        entered_password = st.session_state["password"].strip()
        
        if entered_password == correct_password:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show password input
        st.markdown("""
            <style>
            .main {
                background: linear-gradient(135deg, #0a0e0f 0%, #0f1419 100%);
                background-attachment: fixed;
            }
            </style>
        """, unsafe_allow_html=True)
        
        st.markdown("<h1 style='text-align: center; color: #00ff88;'>🔒 Trading Performance Tracker</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center; color: #e8f5e9;'>Enter Password to Access</h3>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.text_input(
                "Password", 
                type="password", 
                on_change=password_entered, 
                key="password",
                label_visibility="collapsed",
                placeholder="Enter password..."
            )
            st.markdown("<p style='text-align: center; color: #b8c5b8; font-size: 0.9rem;'>Contact admin for access</p>", unsafe_allow_html=True)
        return False
    elif not st.session_state["password_correct"]:
        # Password incorrect, show input + error
        st.markdown("""
            <style>
            .main {
                background: linear-gradient(135deg, #0a0e0f 0%, #0f1419 100%);
                background-attachment: fixed;
            }
            </style>
        """, unsafe_allow_html=True)
        
        st.markdown("<h1 style='text-align: center; color: #00ff88;'>🔒 Trading Performance Tracker</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center; color: #e8f5e9;'>Enter Password to Access</h3>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.text_input(
                "Password", 
                type="password", 
                on_change=password_entered, 
                key="password",
                label_visibility="collapsed",
                placeholder="Enter password..."
            )
            st.error("😕 Password incorrect")
            st.markdown("<p style='text-align: center; color: #b8c5b8; font-size: 0.9rem;'>Contact admin for access</p>", unsafe_allow_html=True)
        return False
    else:
        # Password correct
        return True

# Check password before showing the rest of the app
if not check_password():
    st.stop()  # Do not continue if check fails

# --- Custom CSS for Ultra Dark Green/Black Aesthetic ---
st.markdown("""
    <style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    
    /* === REFINED COLOR PALETTE === */
    /* Pure Black BG: #0a0e0f */
    /* Dark Charcoal: #0f1419 */
    /* Neon Green (Primary): #00ff88 */
    /* Soft Green (Secondary): #00d97e */
    /* Dark Green Accent: #1a4d3e */
    /* Red (Loss): #ff4757 */
    /* Text: #e8f5e9 */
    
    /* Main background - Pure black with subtle gradient */
    .main {
        background: linear-gradient(135deg, #0a0e0f 0%, #0f1419 100%);
        background-attachment: fixed;
        font-family: 'Inter', sans-serif;
    }
    
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        background: rgba(15, 20, 25, 0.95);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        box-shadow: 0 8px 32px rgba(0, 255, 136, 0.1);
        border: 1px solid rgba(0, 255, 136, 0.1);
        margin: 1rem auto;
    }
    
    /* Header styling - Neon green gradient */
    h1 {
        color: #f8fafc;
        font-weight: 800;
        font-size: 3rem !important;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(135deg, #00ff88, #00d97e);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-shadow: 0 0 30px rgba(0, 255, 136, 0.5);
        filter: drop-shadow(0 0 20px rgba(0, 255, 136, 0.3));
    }
    
    h2, h3 {
        color: #e8f5e9;
        font-weight: 700;
        border-bottom: 2px solid rgba(0, 255, 136, 0.3);
        padding-bottom: 8px;
        margin-bottom: 20px;
    }
    
    /* Sidebar - Deep black with green accent */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0e0f 0%, #0f1419 100%);
        border-right: 2px solid rgba(0, 255, 136, 0.2);
    }
    
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: #e8f5e9;
    }

    [data-testid="stSidebar"] h3 {
        color: #00ff88 !important; 
        text-shadow: 0 0 15px rgba(0, 255, 136, 0.6);
        border-bottom: none;
        font-weight: 800;
    }
    
    /* Metric cards - Enhanced styling */
    [data-testid="stMetricValue"] {
        font-size: 2.2rem;
        font-weight: 800;
        color: #00ff88;
        text-shadow: 0 0 15px rgba(0, 255, 136, 0.4);
    }
    
    [data-testid="stMetricLabel"] {
        color: #b8c5b8;
        font-weight: 600;
        font-size: 0.95rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    [data-testid="stMetricDelta"] {
        color: #00ff88;
        font-weight: 700;
    }
    
    /* Tabs - Sleek dark with neon green active state */
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
        background-color: rgba(15, 20, 25, 0.9);
        border-radius: 12px;
        padding: 0.75rem;
        border: 1px solid rgba(0, 255, 136, 0.15);
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: rgba(26, 77, 62, 0.2);
        border-radius: 10px;
        color: #b8c5b8;
        font-weight: 600;
        font-size: 1rem;
        padding: 0 2rem;
        transition: all 0.3s ease;
        border: 1px solid transparent;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: rgba(26, 77, 62, 0.4);
        border-color: rgba(0, 255, 136, 0.3);
        transform: translateY(-2px);
        color: #00ff88;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(0, 255, 136, 0.2), rgba(0, 217, 126, 0.2));
        color: #00ff88 !important;
        font-weight: 800;
        box-shadow: 0 4px 20px rgba(0, 255, 136, 0.4);
        border: 1px solid rgba(0, 255, 136, 0.5);
    }
    
    /* Form styling - Dark with green accents */
    .stForm {
        background: linear-gradient(135deg, rgba(15, 20, 25, 0.95) 0%, rgba(26, 77, 62, 0.1) 100%);
        border-radius: 15px;
        padding: 2rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.6), 0 0 40px rgba(0, 255, 136, 0.05);
        border: 2px solid rgba(0, 255, 136, 0.2);
        backdrop-filter: blur(10px);
    }
    
    /* Input fields - Dark with green focus */
    .stTextInput input, .stNumberInput input, .stSelectbox select, .stDateInput input {
        background-color: rgba(10, 14, 15, 0.95) !important;
        color: #e8f5e9 !important;
        border-radius: 10px;
        border: 2px solid rgba(0, 255, 136, 0.2) !important;
        padding: 0.75rem;
        font-size: 1rem;
        transition: all 0.3s ease;
    }
    
    .stTextInput input:focus, .stNumberInput input:focus, .stSelectbox select:focus, .stDateInput input:focus {
        border-color: #00ff88 !important;
        box-shadow: 0 0 0 3px rgba(0, 255, 136, 0.15) !important;
        background-color: rgba(10, 14, 15, 1) !important;
    }
    
    .stTextInput label, .stNumberInput label, .stSelectbox label, .stDateInput label {
        color: #e8f5e9 !important;
        font-weight: 600;
        font-size: 0.95rem;
    }
    
    /* Button styling - Neon green gradient */
    .stButton button {
        background: linear-gradient(135deg, #00ff88 0%, #00d97e 100%);
        color: #0a0e0f;
        font-weight: 800;
        font-size: 1.1rem;
        padding: 0.85rem 2rem;
        border-radius: 12px;
        border: none;
        box-shadow: 0 4px 20px rgba(0, 255, 136, 0.4);
        transition: all 0.3s ease;
        width: 100%;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .stButton button:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 30px rgba(0, 255, 136, 0.6);
        background: linear-gradient(135deg, #00d97e 0%, #00ff88 100%);
    }
    
    /* Secondary button (Reset) */
    .stButton button[kind="secondary"] {
        background: linear-gradient(135deg, rgba(255, 71, 87, 0.2), rgba(255, 71, 87, 0.3));
        color: #ff4757;
        border: 2px solid rgba(255, 71, 87, 0.5);
        box-shadow: 0 4px 15px rgba(255, 71, 87, 0.2);
    }
    
    .stButton button[kind="secondary"]:hover {
        background: linear-gradient(135deg, rgba(255, 71, 87, 0.3), rgba(255, 71, 87, 0.4));
        box-shadow: 0 6px 25px rgba(255, 71, 87, 0.4);
    }
    
    /* Success/Error messages */
    .stSuccess {
        background-color: rgba(0, 255, 136, 0.15);
        color: #00ff88;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #00ff88;
        backdrop-filter: blur(10px);
    }
    
    .stError {
        background-color: rgba(255, 71, 87, 0.15);
        color: #ff4757;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #ff4757;
        backdrop-filter: blur(10px);
    }
    
    /* Info box - Dark green theme instead of blue */
    .stInfo {
        background: linear-gradient(135deg, rgba(26, 77, 62, 0.3), rgba(0, 255, 136, 0.05));
        border-left: 4px solid #00ff88;
        color: #e8f5e9;
        padding: 1rem;
        border-radius: 10px;
        backdrop-filter: blur(10px);
        box-shadow: 0 2px 10px rgba(0, 255, 136, 0.1);
    }
    
    .stInfo a {
        color: #00ff88 !important;
        font-weight: 600;
    }
    
    /* Dataframe styling */
    .dataframe {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.6);
        background-color: rgba(15, 20, 25, 0.95) !important;
    }
    
    /* Chart containers */
    .js-plotly-plot {
        border-radius: 15px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.6);
        background: rgba(15, 20, 25, 0.95);
        padding: 1.5rem;
        border: 1px solid rgba(0, 255, 136, 0.1);
    }
    
    /* Divider */
    hr {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, rgba(0, 255, 136, 0.5), transparent);
        margin: 2rem 0;
    }
    
    /* Progress bar - Green for wins, Red for losses */
    .stProgress > div > div > div:first-child {
        background-color: rgba(26, 77, 62, 0.3) !important; 
    }
    .stProgress > div > div > div > div {
        background-color: #00ff88 !important;
        box-shadow: 0 0 10px rgba(0, 255, 136, 0.5);
    }
    .stProgress.loss > div > div > div > div {
        background-color: #ff4757 !important;
        box-shadow: 0 0 10px rgba(255, 71, 87, 0.5);
    }
    
    /* Scrollbar styling */
    ::-webkit-scrollbar {
        width: 12px;
        height: 12px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(15, 20, 25, 0.8);
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #00ff88, #00d97e);
        border-radius: 6px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #00d97e, #00ff88);
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background-color: rgba(26, 77, 62, 0.2);
        border-radius: 8px;
        color: #e8f5e9;
        font-weight: 600;
    }
    
    .streamlit-expanderHeader:hover {
        background-color: rgba(26, 77, 62, 0.3);
        border-color: rgba(0, 255, 136, 0.3);
    }
    </style>
""", unsafe_allow_html=True)


# --- Configuration and Setup ---
if "gsheets" not in st.secrets or "sheet_id" not in st.secrets["gsheets"]:
    st.error("Google Sheets configuration is missing. Please ensure 'gsheets.sheet_id' is set in your secrets.")
    SHEET_ID = None
else:
    SHEET_ID = st.secrets["gsheets"]["sheet_id"]


# --- Utility Functions for Google Sheets Interaction ---

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

# --- Core Business Logic: Recalculate Summaries ---

def recalculate_all_summaries(initial_balance=2283.22):
    """
    Reads the full trade history, recalculates daily summaries, and updates the sheet.
    This function is run after every trade or deposit entry.
    """
    if not SHEET_ID: return pd.DataFrame()
    
    today_date = datetime.now(CENTRAL_TZ).date()
    today_date_str = today_date.strftime("%Y-%m-%d")

    df_trades = get_data_from_sheet('trades')
    
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
    
    df_old_summary = get_data_from_sheet('daily_summary')
    if not df_old_summary.empty:
        df_old_summary['Date'] = pd.to_datetime(df_old_summary['Date'], errors='coerce').dt.date.astype(str)
        df_summary['Date'] = pd.to_datetime(df_summary['Date'], errors='coerce').dt.date.astype(str)
        
        df_merged = pd.merge(df_summary, df_old_summary[['Date', 'Deposit/Bonus']], on='Date', how='left', suffixes=('_new', '_old'))
        
        df_merged['Deposit/Bonus'] = pd.to_numeric(df_merged['Deposit/Bonus_old'], errors='coerce').fillna(0.00)
        
        df_summary = df_merged[['Date', 'Week', 'Trades', 'Start Bal.', 'Target P&L', 'Actual P&L', 'Deposit/Bonus', 'End Bal.']]
        
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

# --- Data Loading and Caching ---

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

df_summary_temp, df_trades_temp = load_data() 
if not df_summary_temp.empty and 'Start Bal.' in df_summary_temp.columns:
    st.session_state.initial_balance = df_summary_temp['Start Bal.'].iloc[0]
    
recalculate_all_summaries(st.session_state.initial_balance)
df_summary, df_trades = load_data()


# --- Sidebar: Quick Stats ---

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
                    
                    trades_sheet = spreadsheet.worksheet('trades')
                    trades_sheet.clear()
                    trades_sheet.update('A1', [['trade_date', 'ticker', 'leverage', 'direction', 'investment', 'pnl', 'pnl_pct']])
                    
                    summary_sheet = spreadsheet.worksheet('daily_summary')
                    summary_sheet.clear()
                    summary_sheet.update('A1', [['Date', 'Week', 'Trades', 'Start Bal.', 'Target P&L', 'Actual P&L', 'Deposit/Bonus', 'End Bal.']])
                    
                    st.cache_data.clear()
                    st.cache_resource.clear()
                    
                    st.success("✅ All data has been deleted successfully!")
                    st.balloons()
                    
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

# --- Tab 1: Trade Entry Form ---
with tab1:
    
    st.subheader("🎯 Today's Performance Snapshot (CST/CDT)")
    
    today_date_obj = datetime.now(CENTRAL_TZ).date()

    df_today = df_summary[df_summary['Date'] == today_date_obj]
    
    if not df_today.empty:
        today_target_pl = df_today['Target P&L'].iloc[0]
        today_actual_pl = df_today['Actual P&L'].iloc[0]
        
        if today_target_pl > 0:
            
            st.info(f"**Target P&L for Today ({today_date_obj.strftime('%b %d')}):** `${today_target_pl:,.2f}`")
            
            progress_css_class = ""
            if today_actual_pl >= today_target_pl:
                fill_ratio = 1.0
                fill_value = 100
                label_text = f"**Target HIT!** (P&L: ${today_actual_pl:,.2f})"
                progress_css_class = "" 
                
            elif today_actual_pl > 0:
                fill_ratio = today_actual_pl / today_target_pl 
                fill_value = int(fill_ratio * 100)
                label_text = f"**Making Progress:** {fill_value:.1f}% of Target (P&L: ${today_actual_pl:,.2f})"
                progress_css_class = "progress" 
                
            else:
                fill_value = 0 
                label_text = f"**LOSS/Behind Target:** (P&L: ${today_actual_pl:,.2f})"
                progress_css_class = "loss" 
                
            st.markdown(
                f"""
                <style>
                .stProgress > div > div > div > div {{
                    background-color: {'#ff4757' if progress_css_class == 'loss' else '#00ff88'} !important;
                }}
                </style>
                """,
                unsafe_allow_html=True
            )
            
            st.progress(
                value=min(100, fill_value), 
                text=label_text 
            )
            
        else:
            st.info(f"Today's P&L: **${today_actual_pl:,.2f}** (Target P&L is $0.00 or balance is negative).")

    else:
        st.info("No summary data for today yet. Your first trade will establish today's entry and target.")
        
    st.markdown("---") 
    
    st.header("Log a New Trade")
    
    with st.form("Trade Entry Form"):
        
        col_1a, col_1b, col_1c, col_1d = st.columns(4)
        with col_1a:
            trade_date = st.date_input("📅 Trade Date", datetime.now(CENTRAL_TZ).date()) 
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

# --- Deposit / Bonus Entry ---
with st.expander("💵 Add Deposit or Bonus", expanded=False):
    st.info("Use this to add any deposit or bonus amount to a specific day. This will update your balance and daily summaries automatically.")

    with st.form("deposit_form"):
        col1, col2 = st.columns(2)
        with col1:
            deposit_date = st.date_input("Select Date", datetime.now(CENTRAL_TZ).date())
        with col2:
            deposit_amount = st.number_input("Deposit / Bonus Amount ($)", min_value=0.0, value=0.0, step=50.0, format="%.2f")

        submit_deposit = st.form_submit_button("✅ Add Deposit / Bonus", use_container_width=True)

        if submit_deposit:
            df_summary_latest = get_data_from_sheet("daily_summary")

            if df_summary_latest.empty:
                st.error("⚠️ No summary found. Please record at least one trade before adding deposits.")
            else:
                # Convert date formats for comparison
                df_summary_latest["Date"] = pd.to_datetime(df_summary_latest["Date"], errors="coerce").dt.date

                if deposit_date in df_summary_latest["Date"].values:
                    # Update existing deposit value for the day
                    idx = df_summary_latest[df_summary_latest["Date"] == deposit_date].index[0]
                    prev_value = df_summary_latest.at[idx, "Deposit/Bonus"]
                    df_summary_latest.at[idx, "Deposit/Bonus"] = float(prev_value) + deposit_amount
                    st.success(f"💰 Added ${deposit_amount:,.2f} to {deposit_date}.")
                else:
                    # If date missing (e.g., future day) — add new row
                    new_row = {
                        "Date": deposit_date.strftime("%Y-%m-%d"),
                        "Week": f"Wk {deposit_date.isocalendar()[1]}",
                        "Trades": 0,
                        "Start Bal.": 0.0,
                        "Target P&L": 0.0,
                        "Actual P&L": 0.0,
                        "Deposit/Bonus": deposit_amount,
                        "End Bal.": 0.0,
                    }
                    df_summary_latest = pd.concat([df_summary_latest, pd.DataFrame([new_row])], ignore_index=True)
                    st.info(f"🆕 Created new entry for {deposit_date} with ${deposit_amount:,.2f} deposit.")

                # Write back to sheet
                success = write_data_to_sheet("daily_summary", df_summary_latest, mode="replace")
                if success:
                    recalculate_all_summaries(st.session_state.initial_balance)
                    st.success("✅ Deposit recorded and balances updated!")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ Failed to update deposit in Google Sheet.")


# --- Tab 2: Daily Summary ---
with tab2:
    st.header("Daily Summary")
    
    if df_summary.empty:
        st.info("ℹ️ No summary data available. Enter trades or refresh the page after configuration.")
    else:
        df_display = df_summary.copy()
        
        if 'Date' in df_display.columns:
            df_display = df_display.sort_values(by='Date', ascending=False)
            df_display['Date'] = df_display['Date'].astype(str)
        
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

        #######
        

    ###
        # --- Trade Breakdown Section (Date Filter) ---
        st.subheader("🗓️ Trade Breakdown (CST/CDT)")

        # --- Date selection ---
        all_trade_dates = sorted(df_trades['trade_date'].dropna().unique())
        default_date = datetime.now(CENTRAL_TZ).date()

        selected_date = st.date_input(
            "Select Trade Date",
            value=default_date if default_date in all_trade_dates else all_trade_dates[-1] if len(all_trade_dates) > 0 else default_date,
            min_value=min(all_trade_dates) if len(all_trade_dates) > 0 else default_date,
            max_value=max(all_trade_dates) if len(all_trade_dates) > 0 else default_date,
        )

        # --- Filter trades for selected date ---
        df_trades_today = df_trades[df_trades['trade_date'] == pd.to_datetime(selected_date).date()].sort_index()

        if df_trades_today.empty:
            st.info(f"ℹ️ No trades logged for {selected_date.strftime('%Y-%m-%d')}.")
        else:
            df_trades_today = df_trades_today.copy()
            df_trades_today['Trade #'] = range(1, len(df_trades_today) + 1)
            colors_today = ['#00ff88' if x > 0 else '#ff4757' for x in df_trades_today['pnl']]

            # --- Create Plotly Figure ---
            fig_daily = go.Figure()

            # Bar: Individual trade P&L
            fig_daily.add_trace(go.Bar(
                x=df_trades_today['Trade #'],
                y=df_trades_today['pnl'],
                marker_color=colors_today,
                name='Trade P&L',
                hovertemplate=(
                    "<b>Trade #%{x}</b><br>"
                    "P&L: $%{y:,.2f}<br>"
                    "Ticker: %{customdata[0]}<br>"
                    "Direction: %{customdata[1]}<br>"
                    "Investment: $%{customdata[2]:,.2f}<extra></extra>"
                ),
                customdata=df_trades_today[['ticker', 'direction', 'investment']]
            ))

            # Line: Running cumulative P&L
            df_trades_today['Running P&L'] = df_trades_today['pnl'].cumsum()
            fig_daily.add_trace(go.Scatter(
                x=df_trades_today['Trade #'],
                y=df_trades_today['Running P&L'],
                mode='lines+markers',
                name='Running P&L',
                yaxis='y2',
                line=dict(color='#fbbf24', width=2),
                marker=dict(size=6, color='#fbbf24')
            ))

            # --- Safe y-axis range ---
            max_pnl = df_trades_today['pnl'].abs().max()
            max_running = df_trades_today['Running P&L'].abs().max()
            y_max = max(max_pnl, max_running) * 1.1
            if pd.isna(y_max) or y_max <= 0:
                y_max = 1.0

            # --- Layout ---
            fig_daily.update_layout(
                title=f"Trade P&L Breakdown ({selected_date.strftime('%Y-%m-%d')})",
                xaxis_title="Trade #",
                hovermode='x unified',
                yaxis=dict(
                    title=dict(text="Individual P&L ($)", font=dict(color='#00ff88')),
                    tickfont=dict(color='#e8f5e9'),
                    showgrid=True,
                    gridcolor='rgba(0, 255, 136, 0.1)',
                    zeroline=True,
                    zerolinecolor='rgba(0, 255, 136, 0.3)',
                    range=[-y_max, y_max]
                ),
                yaxis2=dict(
                    title=dict(text="Running P&L ($)", font=dict(color='#fbbf24')),
                    tickfont=dict(color='#e8f5e9'),
                    overlaying='y',
                    side='right',
                    showgrid=False,
                    zeroline=True,
                    zerolinecolor='rgba(0, 255, 136, 0.3)',
                    range=[-y_max, y_max]
                ),
                xaxis=dict(
                    showgrid=False,
                    tickfont=dict(color='#e8f5e9'),
                    dtick=1
                ),
                plot_bgcolor='#0f1419',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Inter, sans-serif", size=12, color="#e8f5e9"),
                title_font=dict(size=18, color='#00ff88'),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    bgcolor='rgba(0,0,0,0)',
                    font=dict(color="#e8f5e9")
                ),
                margin=dict(t=50, b=50, l=50, r=50),
                height=420,
            )

            # --- Display chart ---
            st.plotly_chart(fig_daily, width="stretch")

            #############
        
        st.subheader("📈 Balance Progression")
        
        df_chart = df_summary.sort_values(by='Date', ascending=True)

        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df_chart['Date'].astype(str),
            y=df_chart['End Bal.'],
            mode='lines+markers',
            name='End Balance',
            line=dict(color='#00ff88', width=3, shape='spline'),
            marker=dict(size=8, color='#00d97e', line=dict(color='#0a0e0f', width=2)),
            fill='tozeroy',
            fillcolor='rgba(0, 255, 136, 0.1)'
        ))
        
        fig.add_trace(go.Scatter(
            x=df_chart['Date'].astype(str),
            y=df_chart['Start Bal.'],
            mode='lines+markers',
            name='Start Balance',
            line=dict(color='#fbbf24', width=2, dash='dot'), 
            marker=dict(size=6, color='#fbbf24')
        ))

        fig.add_trace(go.Scatter(
            x=df_chart['Date'].astype(str),
            y=df_chart['Start Bal.'] + df_chart['Target P&L'],
            mode='lines',
            name='Target End Bal',
            line=dict(color='#34d399', width=2, dash='dash')
        ))
        
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
            plot_bgcolor='#0f1419', 
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Inter, sans-serif", size=12, color="#e8f5e9"),
            title_font=dict(size=20, color='#00ff88', family="Inter"),
            legend=dict(
                orientation="h", 
                yanchor="bottom", y=1.02, xanchor="right", x=1, 
                bgcolor='rgba(0,0,0,0)',
                font=dict(color="#e8f5e9")
            ),
            xaxis=dict(
                showgrid=True, 
                gridcolor='rgba(0, 255, 136, 0.1)',
                tickfont=dict(color='#e8f5e9'),
                tickformat="%b %d<br>%Y",
                dtick='d' 
            ),
            yaxis=dict(
                showgrid=True, 
                gridcolor='rgba(0, 255, 136, 0.1)',
                tickfont=dict(color='#e8f5e9'),
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
            
            with col_pnl:
                st.subheader("💵 Daily P&L Chart")
                
                df_chart_pnl = df_summary_filtered.sort_values(by='Date', ascending=True)
                
                colors = ['#00ff88' if x > 0 else '#ff4757' for x in df_chart_pnl['Actual P&L']]
                
                fig_pnl = go.Figure()
                
                fig_pnl.add_trace(go.Bar(
                    x=df_chart_pnl['Date'].astype(str),
                    y=df_chart_pnl['Actual P&L'],
                    marker_color=colors,
                    name='Daily P&L',
                    text=df_chart_pnl['Actual P&L'].apply(lambda x: f'${x:,.2f}'),
                    textposition='auto', 
                    textfont=dict(color='#0a0e0f', size=11, weight='bold'), 
                    marker=dict(line=dict(color='rgba(0, 0, 0, 0.3)', width=1))
                ))
                
                fig_pnl.update_layout(
                    title=f'Daily Trading P&L ({start_date.strftime("%b %d")} - {end_date.strftime("%b %d")})',
                    xaxis_title="Date", 
                    yaxis_title="P&L ($)",
                    height=450,
                    plot_bgcolor='#0f1419',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(family="Inter, sans-serif", size=12, color="#e8f5e9"),
                    title_font=dict(size=18, color='#00ff88', family="Inter"),
                    xaxis=dict(
                        showgrid=True, 
                        gridcolor='rgba(0, 255, 136, 0.1)',
                        tickfont=dict(color='#e8f5e9'),
                        tickformat="%b %d<br>%Y" ,
                        dtick='d' 
                    ),
                    yaxis=dict(
                        showgrid=True, 
                        gridcolor='rgba(0, 255, 136, 0.1)', 
                        zeroline=True, 
                        zerolinecolor='rgba(0, 255, 136, 0.3)',
                        tickfont=dict(color='#e8f5e9')
                    ),
                    margin=dict(t=50)
                )
                st.plotly_chart(fig_pnl, use_container_width=True)
                
            with col_winrate:
                st.subheader("🎯 Trade Win/Loss Breakdown")
                
                df_trades_temp = df_trades_filtered.copy()
                df_trades_temp['Result'] = df_trades_temp['pnl'].apply(lambda x: 'Win' if x > 0 else ('Loss' if x < 0 else 'Breakeven'))
                
                result_counts = df_trades_temp['Result'].value_counts().reset_index()
                result_counts.columns = ['Result', 'Count']

                all_results = pd.DataFrame({'Result': ['Win', 'Loss', 'Breakeven'], 'Count': [0, 0, 0]})
                result_counts = pd.merge(all_results, result_counts, on='Result', how='left', suffixes=('_all', '')).fillna(0)
                result_counts['Count'] = result_counts['Count_all'] + result_counts['Count'] 
                result_counts = result_counts[['Result', 'Count']]
                result_counts = result_counts[result_counts['Count'] > 0] 
                
                pie_colors = {
                    'Win': '#00ff88',
                    'Loss': '#ff4757',
                    'Breakeven': '#94a3b8'
                }
                
                sorted_results = [pie_colors.get(r, '#94a3b8') for r in result_counts['Result']]
                
                fig_pie = go.Figure(data=[go.Pie(
                    labels=result_counts['Result'],
                    values=result_counts['Count'],
                    hole=0.4,
                    marker=dict(colors=sorted_results), 
                    textfont=dict(size=16, color='#0a0e0f', family='Inter', weight='bold'),
                    textinfo='label+percent'
                )])
                
                fig_pie.update_layout(
                    title=f'Trade Outcomes ({df_trades_filtered.shape[0]} trades total)',
                    height=450,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(family="Inter, sans-serif", size=12, color="#e8f5e9"),
                    title_font=dict(size=18, color='#00ff88', family="Inter"),
                    showlegend=True,
                    legend=dict(font=dict(color='#e8f5e9')),
                    margin=dict(t=50)
                )
                st.plotly_chart(fig_pie, use_container_width=True)