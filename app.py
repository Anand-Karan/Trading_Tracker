import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import gspread

# --- Page Configuration ---
st.set_page_config(
    page_title="Trading Performance Tracker",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for Beautiful Dark Styling ---
st.markdown("""
    <style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    
    /* Main background and theme */
    .main {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #312e81 100%);
        background-attachment: fixed;
        font-family: 'Inter', sans-serif;
    }
    
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        background: rgba(15, 23, 42, 0.6);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
        border: 1px solid rgba(99, 102, 241, 0.2);
        margin: 1rem auto;
    }
    
    /* Header styling */
    h1 {
        color: #f8fafc;
        font-weight: 800;
        font-size: 3rem !important;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 0 0 20px rgba(99, 102, 241, 0.5);
        background: linear-gradient(135deg, #818cf8, #c084fc, #f472b6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    h2, h3 {
        color: #e0e7ff;
        font-weight: 700;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e1b4b 0%, #312e81 100%);
        border-right: 1px solid rgba(99, 102, 241, 0.3);
    }
    
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: #e0e7ff;
    }
    
    [data-testid="stSidebar"] h3 {
        color: #f8fafc !important;
        font-weight: 700;
        font-size: 1.5rem;
        text-shadow: 0 0 10px rgba(139, 92, 246, 0.5);
    }
    
    /* Metric cards styling */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 800;
        color: #f8fafc;
        text-shadow: 0 0 10px rgba(139, 92, 246, 0.3);
    }
    
    [data-testid="stMetricLabel"] {
        color: rgba(226, 232, 240, 0.9);
        font-weight: 600;
        font-size: 1rem;
    }
    
    [data-testid="stMetricDelta"] {
        color: #34d399;
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: rgba(30, 27, 75, 0.8);
        border-radius: 10px;
        padding: 0.5rem;
        border: 1px solid rgba(99, 102, 241, 0.2);
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: rgba(51, 65, 85, 0.6);
        border-radius: 8px;
        color: #cbd5e1;
        font-weight: 600;
        font-size: 1rem;
        padding: 0 2rem;
        transition: all 0.3s ease;
        border: 1px solid transparent;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: rgba(79, 70, 229, 0.3);
        border-color: rgba(139, 92, 246, 0.5);
        transform: translateY(-2px);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        color: white !important;
        box-shadow: 0 4px 20px rgba(139, 92, 246, 0.6);
        border-color: rgba(139, 92, 246, 0.8);
    }
    
    /* Form styling */
    .stForm {
        background: linear-gradient(135deg, rgba(30, 27, 75, 0.8) 0%, rgba(49, 46, 129, 0.8) 100%);
        border-radius: 15px;
        padding: 2rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
        border: 2px solid rgba(139, 92, 246, 0.3);
        backdrop-filter: blur(10px);
    }
    
    /* Input fields */
    .stTextInput input, .stNumberInput input, .stSelectbox select, .stDateInput input {
        background-color: rgba(30, 41, 59, 0.9) !important;
        color: #e0e7ff !important;
        border-radius: 8px;
        border: 2px solid rgba(99, 102, 241, 0.3) !important;
        padding: 0.5rem;
        font-size: 1rem;
        transition: all 0.3s ease;
    }
    
    .stTextInput input:focus, .stNumberInput input:focus, .stSelectbox select:focus {
        border-color: #8b5cf6 !important;
        box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.2) !important;
        background-color: rgba(30, 41, 59, 1) !important;
    }
    
    .stTextInput label, .stNumberInput label, .stSelectbox label, .stDateInput label {
        color: #cbd5e1 !important;
        font-weight: 600;
    }
    
    /* Button styling */
    .stButton button {
        background: linear-gradient(135deg, #f43f5e 0%, #dc2626 100%);
        color: white;
        font-weight: 700;
        font-size: 1.1rem;
        padding: 0.75rem 2rem;
        border-radius: 10px;
        border: none;
        box-shadow: 0 4px 20px rgba(244, 63, 94, 0.5);
        transition: all 0.3s ease;
        width: 100%;
    }
    
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 30px rgba(244, 63, 94, 0.7);
    }
    
    /* Success/Error messages */
    .stSuccess {
        background-color: rgba(16, 185, 129, 0.2);
        color: #6ee7b7;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #10b981;
        backdrop-filter: blur(10px);
    }
    
    .stError {
        background-color: rgba(239, 68, 68, 0.2);
        color: #fca5a5;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #ef4444;
        backdrop-filter: blur(10px);
    }
    
    /* Dataframe styling */
    .dataframe {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
        background-color: rgba(30, 41, 59, 0.8) !important;
    }
    
    /* Chart containers */
    .js-plotly-plot {
        border-radius: 15px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
        background: rgba(30, 41, 59, 0.8);
        padding: 1rem;
        border: 1px solid rgba(99, 102, 241, 0.2);
    }
    
    /* Divider */
    hr {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, rgba(139, 92, 246, 0.6), transparent);
        margin: 2rem 0;
    }
    
    /* Info/Warning boxes */
    .stInfo {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(139, 92, 246, 0.2) 100%);
        border-left: 4px solid #6366f1;
        border-radius: 10px;
        padding: 1rem;
        color: #cbd5e1;
        backdrop-filter: blur(10px);
    }
    
    /* Toast notification style */
    .stToast {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        color: white;
        border-radius: 10px;
        font-weight: 600;
    }
    
    /* Scrollbar styling */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(30, 41, 59, 0.5);
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        border-radius: 5px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #8b5cf6, #a78bfa);
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
        
        # Clear the cache after writing to force fresh data on next read
        get_data_from_sheet.clear()
        
        return True
    except Exception as e:
        st.error(f"Error writing data to sheet '{sheet_name}': {e}")
        return False

# --- Core Business Logic: Recalculate Summaries (CRITICAL) ---

def recalculate_all_summaries(initial_balance=2283.22):
    """
    Reads the full trade history, recalculates daily summaries, and updates the sheet.
    This function is run after every trade or deposit entry.
    """
    if not SHEET_ID: return pd.DataFrame()

    df_trades = get_data_from_sheet('trades')
    
    if df_trades.empty or df_trades.shape[0] == 0:
        start_date = datetime.now().strftime("%Y-%m-%d")
        summary_data = {
            'Date': [start_date],
            'Week': ['Wk 1'],
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
        st.error(f"Error processing trade data types: {e}. Check that your 'trades' sheet has columns 'trade_date' and 'pnl'.")
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
        
        if start_balance <= 0:
             target_pl = 0
        
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
    
    df_old_summary = get_data_from_sheet('daily_summary')
    if not df_old_summary.empty:
        df_old_summary['Date'] = pd.to_datetime(df_old_summary['Date'], errors='coerce').dt.date.astype(str)
        df_summary['Date'] = pd.to_datetime(df_summary['Date'], errors='coerce').dt.date.astype(str)
        
        df_merged = pd.merge(df_summary, df_old_summary[['Date', 'Deposit/Bonus']], on='Date', how='left', suffixes=('_new', '_old'))
        
        df_merged['Deposit/Bonus'] = pd.to_numeric(df_merged['Deposit/Bonus_old'], errors='coerce').fillna(0.00)
        
        df_merged['End Bal.'] = pd.to_numeric(df_merged['End Bal.'], errors='coerce').fillna(0) + df_merged['Deposit/Bonus']
        
        df_summary = df_merged[['Date', 'Week', 'Trades', 'Start Bal.', 'Target P&L', 'Actual P&L', 'Deposit/Bonus', 'End Bal.']]
    else:
        df_summary['Date'] = df_summary['Date'].astype(str)


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
                df_summary['Date'] = pd.to_datetime(df_summary['Date'], errors='coerce')
            if 'End Bal.' in df_summary.columns:
                df_summary['End Bal.'] = pd.to_numeric(df_summary['End Bal.'], errors='coerce').fillna(0)
            if 'Actual P&L' in df_summary.columns:
                df_summary['Actual P&L'] = pd.to_numeric(df_summary['Actual P&L'], errors='coerce').fillna(0)
        except Exception as e:
            st.warning(f"Could not convert summary data types: {e}")
            df_summary = pd.DataFrame()

    if not df_trades.empty:
        try:
            if 'trade_date' in df_trades.columns:
                df_trades['trade_date'] = pd.to_datetime(df_trades['trade_date'], errors='coerce')
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

df_summary, df_trades = load_data()

if df_summary.empty and not df_trades.empty:
    recalculate_all_summaries(st.session_state.initial_balance)
    df_summary, df_trades = load_data()
elif df_summary.empty and df_trades.empty:
    recalculate_all_summaries(st.session_state.initial_balance)
    df_summary, df_trades = load_data()


# --- Sidebar: Quick Stats ---

with st.sidebar:
    st.markdown("### 📊 Quick Stats")
    
    current_balance = df_summary['End Bal.'].iloc[-1] if not df_summary.empty else st.session_state.initial_balance
    
    if not df_summary.empty and 'Start Bal.' in df_summary.columns:
        first_start_bal = pd.to_numeric(df_summary['Start Bal.'], errors='coerce').iloc[0]
        st.session_state.initial_balance = first_start_bal
    
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
    
    with st.form("Deposit/Bonus Form"):
        st.subheader("💵 Add Deposit/Bonus")
        deposit_date = st.date_input("Date", datetime.now().date())
        deposit_amount = st.number_input("Amount ($)", min_value=0.01, step=10.00)
        deposit_submitted = st.form_submit_button("Add Funds", use_container_width=True)

        if deposit_submitted:
            df_summary_temp, _ = load_data()
            
            if df_summary_temp.empty:
                 st.error("Cannot add deposit as the daily summary sheet is empty.")
            else:
                deposit_date_str = deposit_date.strftime("%Y-%m-%d")
                
                # Convert Date column to string for comparison
                df_summary_temp['Date_str'] = pd.to_datetime(df_summary_temp['Date'], errors='coerce').dt.strftime('%Y-%m-%d')
                
                target_index = df_summary_temp[df_summary_temp['Date_str'] == deposit_date_str].index
                
                if not target_index.empty:
                    idx = target_index[0]
                    
                    # Get current deposit value, handle both string and numeric types
                    current_deposit_val = df_summary_temp.loc[idx, 'Deposit/Bonus']
                    if pd.isna(current_deposit_val) or current_deposit_val == '':
                        current_deposit = 0.0
                    else:
                        # Remove dollar sign and commas if present
                        if isinstance(current_deposit_val, str):
                            current_deposit_val = current_deposit_val.replace('$', '').replace(',', '')
                        current_deposit = pd.to_numeric(current_deposit_val, errors='coerce')
                        if pd.isna(current_deposit):
                            current_deposit = 0.0
                    
                    new_deposit = current_deposit + deposit_amount
                    df_summary_temp.loc[idx, 'Deposit/Bonus'] = round(new_deposit, 2)
                    
                    # Drop temporary column
                    df_summary_temp = df_summary_temp.drop(columns=['Date_str'], errors='ignore')
                    
                    # Write back to sheet
                    write_data_to_sheet('daily_summary', df_summary_temp.drop(columns=['Date'], errors='ignore'), mode='replace')
                    
                    # Recalculate summaries
                    recalculate_all_summaries(st.session_state.initial_balance)
                    
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error("❌ Deposit date does not match any existing trade dates. Deposits can only be added on days where trading occurred.")
            

# --- Main Page: Title and Tabs ---
st.markdown("# 📈 Trading Performance Tracker")

tab1, tab2, tab3 = st.tabs(["💵 Trade Entry", "🗓️ Daily Summary", "📊 Analytics"])

# --- Tab 1: Trade Entry Form ---
with tab1:
    st.header("Log a New Trade")
    
    with st.form("Trade Entry Form"):
        
        col_1a, col_1b, col_1c, col_1d = st.columns(4)
        with col_1a:
            trade_date = st.date_input("📅 Trade Date", datetime.now().date())
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
                    
                    recalculate_all_summaries(st.session_state.initial_balance)
                    
                    # Only clear cache, don't use rerun - let the cache refresh handle it
                    st.cache_data.clear()
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
        
        # Sort FIRST before formatting
        df_display = df_display.sort_values(by='Date', ascending=False)
        
        # Then format currency columns
        currency_cols = ['Start Bal.', 'Target P&L', 'Actual P&L', 'Deposit/Bonus', 'End Bal.']
        for col in currency_cols:
             if col in df_display.columns:
                df_display[col] = pd.to_numeric(df_display[col], errors='coerce').apply(lambda x: f"${x:,.2f}" if pd.notna(x) else '$0.00')

        # Format date column for display
        if 'Date' in df_display.columns:
            df_display['Date'] = df_display['Date'].dt.strftime('%Y-%m-%d')

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
        
        fig.add_trace(go.Scatter(
            x=df_chart['Date'],
            y=df_chart['End Bal.'],
            mode='lines+markers',
            name='Balance',
            line=dict(color='#818cf8', width=3, shape='spline'),
            marker=dict(size=8, color='#a78bfa', line=dict(color='#312e81', width=2)),
            fill='tozeroy',
            fillcolor='rgba(129, 140, 248, 0.2)'
        ))
        
        fig.update_layout(
            title='Balance Progression Over Time',
            xaxis_title="Date", 
            yaxis_title="Balance ($)",
            hovermode='x unified',
            height=450,
            plot_bgcolor='rgba(30, 41, 59, 0.5)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Inter, sans-serif", size=12, color="#e0e7ff"),
            title_font=dict(size=20, color='#f8fafc', family="Inter"),
            xaxis=dict(
                showgrid=True, 
                gridcolor='rgba(99, 102, 241, 0.1)',
                tickfont=dict(color='#cbd5e1')
            ),
            yaxis=dict(
                showgrid=True, 
                gridcolor='rgba(99, 102, 241, 0.1)',
                tickfont=dict(color='#cbd5e1')
            )
        )
        st.plotly_chart(fig, use_container_width=True)

# --- Tab 3: Performance Analytics ---
with tab3:
    st.header("Performance Analytics")
    
    if df_trades.empty:
        st.info("ℹ️ No trade data yet. Start logging trades to see analytics!")
    else:
        
        col_pnl, col_winrate = st.columns(2)
        
        with col_pnl:
            st.subheader("💵 Daily P&L Chart")
            
            df_chart_pnl = df_summary.sort_values(by='Date', ascending=True)
            
            colors = ['#34d399' if x > 0 else '#f87171' for x in df_chart_pnl['Actual P&L']]
            
            fig_pnl = go.Figure()
            
            fig_pnl.add_trace(go.Bar(
                x=df_chart_pnl['Date'],
                y=df_chart_pnl['Actual P&L'],
                marker_color=colors,
                name='Daily P&L',
                text=df_chart_pnl['Actual P&L'].apply(lambda x: f'${x:,.2f}'),
                textposition='outside',
                textfont=dict(color='#f8fafc', size=11),
                marker=dict(line=dict(color='rgba(99, 102, 241, 0.3)', width=1))
            ))
            
            fig_pnl.update_layout(
                title='Daily Trading Profit/Loss',
                xaxis_title="Date", 
                yaxis_title="P&L ($)",
                height=450,
                plot_bgcolor='rgba(30, 41, 59, 0.5)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Inter, sans-serif", size=12, color="#e0e7ff"),
                title_font=dict(size=18, color='#f8fafc', family="Inter"),
                xaxis=dict(
                    showgrid=True, 
                    gridcolor='rgba(99, 102, 241, 0.1)',
                    tickfont=dict(color='#cbd5e1')
                ),
                yaxis=dict(
                    showgrid=True, 
                    gridcolor='rgba(99, 102, 241, 0.1)', 
                    zeroline=True, 
                    zerolinecolor='rgba(139, 92, 246, 0.3)',
                    tickfont=dict(color='#cbd5e1')
                )
            )
            st.plotly_chart(fig_pnl, use_container_width=True)
            
        with col_winrate:
            st.subheader("🎯 Trade Win/Loss Breakdown")
            
            df_trades_temp = df_trades.copy()
            df_trades_temp['Result'] = df_trades_temp['pnl'].apply(lambda x: 'Win' if x > 0 else ('Loss' if x < 0 else 'Breakeven'))
            
            result_counts = df_trades_temp['Result'].value_counts().reset_index()
            result_counts.columns = ['Result', 'Count']
            
            fig_pie = go.Figure(data=[go.Pie(
                labels=result_counts['Result'],
                values=result_counts['Count'],
                hole=0.4,
                marker=dict(colors=['#34d399', '#f87171', '#818cf8']),
                textfont=dict(size=16, color='white', family='Inter'),
                textinfo='label+percent'
            )])
            
            fig_pie.update_layout(
                title='Total Trade Outcomes',
                height=450,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Inter, sans-serif", size=12, color="#e0e7ff"),
                title_font=dict(size=18, color='#f8fafc', family="Inter"),
                showlegend=True,
                legend=dict(font=dict(color='#e0e7ff'))
            )
            st.plotly_chart(fig_pie, use_container_width=True)