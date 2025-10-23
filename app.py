import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import gspread

# --- Configuration and Setup ---
# The secrets are loaded automatically by Streamlit from the cloud configuration
# and your local .streamlit/secrets.toml file.
SHEET_ID = st.secrets["gsheets"]["sheet_id"]

# --- Utility Functions for Google Sheets Interaction ---

@st.cache_resource(ttl=3600)
def connect_gsheets():
    """Authenticates and returns a gspread client object."""
    try:
        # Load credentials from st.secrets and authenticate gspread client
        # The entire dict is passed to gspread.service_account_from_dict
        client = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
        return client
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return None

def get_data_from_sheet(sheet_name):
    """Retrieves data from a specific sheet as a pandas DataFrame using core gspread."""
    gc = connect_gsheets()
    if not gc: return pd.DataFrame()
    try:
        spreadsheet = gc.open_by_key(SHEET_ID)
        worksheet = spreadsheet.worksheet(sheet_name)
        
        # --- MANUAL DATA RETRIEVAL using gspread's built-in method ---
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        
        # Ensure only non-empty rows are returned
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
        
        # Prepare data: Convert DataFrame to a list of lists (including header for 'replace')
        data_to_write = df.values.tolist()
        
        if mode == 'append':
            # Append only the data rows (excluding header)
            worksheet.append_rows(data_to_write, value_input_option='USER_ENTERED')
            
        elif mode == 'replace':
            # Clear the sheet and write the new DataFrame (including header)
            header = [str(col) for col in df.columns.tolist()]
            full_data = [header] + data_to_write
            
            # --- OVERWRITE DATA using gspread's built-in method ---
            worksheet.clear()
            # Update the sheet starting from cell A1
            worksheet.update('A1', full_data, value_input_option='USER_ENTERED')
            
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
    # 1. Get raw trades and ensure correct data types
    df_trades = get_data_from_sheet('trades')
    
    if df_trades.empty or df_trades.shape[0] == 0:
        # If no trades, create a starting summary row
        start_date = datetime.now().strftime("%Y-%m-%d")
        summary_data = {
            'Date': [start_date],
            'Week': [1],
            'Trades': [0],
            'Start Bal.': [initial_balance],
            'Target P&L': [initial_balance * 0.065],
            'Actual P&L': [0.0],
            'Deposit/Bonus': [0.0],
            'End Bal.': [initial_balance],
        }
        df_summary = pd.DataFrame(summary_data)
        write_data_to_sheet('daily_summary', df_summary, mode='replace')
        return

    try:
        # Convert necessary columns to correct types
        # Note: We must ensure column names are correctly matched to those in the sheet (P&L, entry_date)
        df_trades['entry_date'] = pd.to_datetime(df_trades['entry_date']).dt.date
        df_trades['P&L'] = pd.to_numeric(df_trades['P&L'], errors='coerce').fillna(0)
    except Exception as e:
        st.error(f"Error processing trade data types: {e}")
        return

    # 2. Sort by date and group by day
    df_trades = df_trades.sort_values(by='entry_date')
    daily_groups = df_trades.groupby('entry_date')

    # 3. Calculate Daily Metrics
    daily_summary_list = []
    current_balance = initial_balance
    week_counter = 1

    for date, group in daily_groups:
        total_pl = group['P&L'].sum()
        num_trades = group.shape[0]
        
        start_balance = current_balance
        end_balance = start_balance + total_pl
        target_pl = start_balance * 0.065
        
        # Check if the start balance is greater than 0 before calculating target P&L
        if start_balance <= 0:
             target_pl = 0
             
        daily_summary_list.append({
            'Date': date.strftime("%Y-%m-%d"),
            'Week': week_counter, # Simplified week calculation
            'Trades': num_trades,
            'Start Bal.': round(start_balance, 2),
            'Target P&L': round(target_pl, 2),
            'Actual P&L': round(total_pl, 2),
            'Deposit/Bonus': 0.00, # Will be merged from old summary later
            'End Bal.': round(end_balance, 2),
        })
        current_balance = end_balance # Update running balance for the next day's starting balance
        week_counter = (date - df_trades['entry_date'].min()).days // 7 + 1


    df_summary = pd.DataFrame(daily_summary_list)
    
    # 4. Handle Deposits/Bonuses separately from the 'trades' sheet
    # Since deposits/bonuses modify 'End Bal.' directly, we first read the existing summary
    df_old_summary = get_data_from_sheet('daily_summary')
    if not df_old_summary.empty:
        df_old_summary['Date'] = pd.to_datetime(df_old_summary['Date'], errors='coerce').dt.date.astype(str)
        df_summary['Date'] = pd.to_datetime(df_summary['Date'], errors='coerce').dt.date.astype(str)
        
        # Merge the new summary with the old one to preserve Deposit/Bonus amounts
        df_merged = pd.merge(df_summary, df_old_summary[['Date', 'Deposit/Bonus']], on='Date', how='left', suffixes=('_new', '_old'))
        
        # Ensure Deposit/Bonus is treated as numeric
        df_merged['Deposit/Bonus'] = pd.to_numeric(df_merged['Deposit/Bonus_old'], errors='coerce').fillna(0.00)
        
        # Re-calculate End Bal. including the preserved deposit/bonus
        df_merged['End Bal.'] = df_merged['End Bal.'] + df_merged['Deposit/Bonus']
        
        # Final cleanup for the summary sheet columns
        df_summary = df_merged[['Date', 'Week', 'Trades', 'Start Bal.', 'Target P&L', 'Actual P&L', 'Deposit/Bonus', 'End Bal.']]
    else:
        # Ensure 'Date' is a string if no old summary exists for merging
        df_summary['Date'] = df_summary['Date'].astype(str)


    # 5. Write the final, recalculated summary back to the sheet
    if not df_summary.empty:
        # IMPORTANT: Convert the Date column back to YYYY-MM-DD string format for writing to Google Sheets
        # Since we converted it to string for merging, this might be redundant but is safer.
        df_summary['Date'] = df_summary['Date'].astype(str)
        write_data_to_sheet('daily_summary', df_summary, mode='replace')
        st.toast("Daily summaries recalculated successfully.")
        
    return df_summary

# --- Data Loading and Caching ---

def load_data():
    """Load data for the UI."""
    df_summary = get_data_from_sheet('daily_summary')
    df_trades = get_data_from_sheet('trades')
    
    # Data Cleaning and Type Conversion for Charting/Display
    if not df_summary.empty:
        try:
            # Ensure proper columns exist before accessing
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
            if 'entry_date' in df_trades.columns:
                df_trades['entry_date'] = pd.to_datetime(df_trades['entry_date'], errors='coerce')
            if 'P&L' in df_trades.columns:
                df_trades['P&L'] = pd.to_numeric(df_trades['P&L'], errors='coerce').fillna(0)
            # Convert the new 'P&L %' column
            if 'P&L %' in df_trades.columns:
                df_trades['P&L %'] = pd.to_numeric(df_trades['P&L %'], errors='coerce').fillna(0)
        except Exception as e:
            st.warning(f"Could not convert trades data types: {e}")
            df_trades = pd.DataFrame()
            
    return df_summary, df_trades

# --- Initialize App and State ---

# Run initial calculation if data is empty or missing (especially on first run)
if 'initial_balance' not in st.session_state:
    # Set a default starting balance if not derived from data
    st.session_state.initial_balance = 2272.22 

# Load data on page load
df_summary, df_trades = load_data()

# Recalculate if the summary is critically empty but trades exist (to catch first-time use)
if df_summary.empty and not df_trades.empty:
    recalculate_all_summaries(st.session_state.initial_balance)
    df_summary, df_trades = load_data() # Reload data after recalculation
elif df_summary.empty and df_trades.empty:
    # If both are empty, initialize a single summary row for display
    recalculate_all_summaries(st.session_state.initial_balance)
    df_summary, df_trades = load_data() # Reload data after initialization


# --- Sidebar: Quick Stats ---

with st.sidebar:
    st.markdown("### 📊 Quick Stats")
    
    # Current Balance
    current_balance = df_summary['End Bal.'].iloc[-1] if not df_summary.empty else st.session_state.initial_balance
    
    # Initial balance must be calculated from the first 'Start Bal.' entry if summary exists
    if not df_summary.empty and 'Start Bal.' in df_summary.columns:
        # Find the very first recorded starting balance (the true initial capital)
        first_start_bal = pd.to_numeric(df_summary['Start Bal.'], errors='coerce').iloc[0]
        st.session_state.initial_balance = first_start_bal # Update session state with the true initial value
    
    st.metric(
        label="Current Balance",
        value=f"${current_balance:,.2f}",
        delta=f"${current_balance - st.session_state.initial_balance:,.2f}",
        delta_color="normal"
    )

    # Total Trades
    total_trades = df_trades.shape[0] if not df_trades.empty else 0
    st.metric(label="Total Trades", value=total_trades)
    
    # Current Week
    latest_week = df_summary['Week'].iloc[-1] if not df_summary.empty else 1
    st.metric(label="Week", value=latest_week)

    # Total Trading P&L
    total_pl = df_summary['Actual P&L'].sum() if not df_summary.empty else 0.0
    total_pl_percent = (total_pl / st.session_state.initial_balance) * 100 if st.session_state.initial_balance > 0 else 0
    st.metric(
        label="Total Trading P&L",
        value=f"${total_pl:,.2f}",
        delta=f"{total_pl_percent:.2f}%",
        delta_color="normal"
    )
    
    st.divider()
    
    # Form for adding deposits/bonuses
    with st.form("Deposit/Bonus Form"):
        st.subheader("Add Deposit/Bonus")
        deposit_date = st.date_input("Date", datetime.now().date())
        deposit_amount = st.number_input("Amount ($)", min_value=0.01, step=10.00)
        deposit_submitted = st.form_submit_button("Add Funds")

        if deposit_submitted:
            # We must reload the summary data here to ensure we have the very latest version before modification
            df_summary_temp, _ = load_data()
            
            if df_summary_temp.empty:
                 st.error("Cannot add deposit as the daily summary sheet is empty.")
                 deposit_submitted = False # Prevent further execution
            
            if deposit_submitted:
                # Find the row for the deposit date
                deposit_date_str = deposit_date.strftime("%Y-%m-%d")
                
                # Convert the 'Date' column to string for consistent comparison
                df_summary_temp['Date_str'] = df_summary_temp['Date'].astype(str).str[:10] # ensure YYYY-MM-DD format
                
                # Check if an entry for this date already exists
                target_index = df_summary_temp[df_summary_temp['Date_str'] == deposit_date_str].index
                
                if not target_index.empty:
                    # Update existing row
                    idx = target_index[0]
                    
                    # Check current deposit value (needs to be numeric)
                    current_deposit = pd.to_numeric(df_summary_temp.loc[idx, 'Deposit/Bonus'], errors='coerce').fillna(0)
                    
                    # Add new amount to existing deposit
                    new_deposit = current_deposit + deposit_amount
                    df_summary_temp.loc[idx, 'Deposit/Bonus'] = round(new_deposit, 2)
                    
                    # Update End Bal.: End Bal = Start Bal + P&L + New Deposit
                    start_bal = pd.to_numeric(df_summary_temp.loc[idx, 'Start Bal.'], errors='coerce').fillna(0)
                    actual_pl = pd.to_numeric(df_summary_temp.loc[idx, 'Actual P&L'], errors='coerce').fillna(0)
                    df_summary_temp.loc[idx, 'End Bal.'] = round(start_bal + actual_pl + new_deposit, 2)
                    
                    # Drop the temporary date column
                    df_summary_temp = df_summary_temp.drop(columns=['Date_str'])
                    
                    # Write back the updated summary sheet
                    # Note: Dropping the original 'Date' column which is a Timestamp for writing, 
                    # relying on the string version from merge being preserved and used.
                    write_data_to_sheet('daily_summary', df_summary_temp.drop(columns=['Date'], errors='ignore'), mode='replace')
                    
                    # Rerun summary calculation to update subsequent rows
                    recalculate_all_summaries(st.session_state.initial_balance)
                    
                    # Clear cache and trigger reload
                    st.cache_resource.clear()
                    st.experimental_rerun()
                else:
                    st.error("Cannot add deposit to a date without a corresponding trade entry.")
            

# --- Main Page: Title and Tabs ---
st.title("📈 Trading Performance Tracker")

tab1, tab2, tab3 = st.tabs(["💵 Trade Entry", "🗓️ Daily Summary", "📊 Analytics"])

# --- Tab 1: Trade Entry Form (Simplified) ---
with tab1:
    st.header("Log a New Trade")
    
    with st.form("Trade Entry Form"):
        # Trade Details - Simplified to just the required core data
        col_1, col_2, col_3 = st.columns(3) # Use three columns for better layout
        with col_1:
            trade_type = st.selectbox("Type", ["Long", "Short"])
            market = st.selectbox("Market", ["Stock", "Forex", "Crypto", "Futures"])
        with col_2:
            trade_date = st.date_input("Entry Date", datetime.now().date())
            pnl = st.number_input("P&L ($)", help="Enter profit as positive, loss as negative.", format="%.2f")
        with col_3:
            # New field for P&L %
            st.markdown(" ") # Spacer for alignment
            pnl_percent = st.number_input("P&L %", help="Enter percentage (e.g., 2.5 for 2.5%)", format="%.2f")
        
        submitted = st.form_submit_button("Submit Trade")

        if submitted:
            # Create a new row of data
            new_trade_data = pd.DataFrame([{
                'entry_date': trade_date.strftime("%Y-%m-%d"),
                'trade_type': trade_type,
                'market': market,
                'P&L': pnl,
                'P&L %': pnl_percent, # Log the new P&L %
            }])
            
            # Write new trade to the 'trades' sheet
            if write_data_to_sheet('trades', new_trade_data, mode='append'):
                st.success("Trade successfully logged!")
                
                # Recalculate all summaries and running balances
                recalculate_all_summaries(st.session_state.initial_balance)
                
                # Clear cache and trigger reload
                st.cache_resource.clear()
                st.experimental_rerun()
            else:
                st.error("Failed to log trade to Google Sheet.")


# --- Tab 2: Daily Summary ---
with tab2:
    st.header("Daily Summary")
    
    if df_summary.empty:
        st.info("No summary data available. Enter trades or refresh the page after configuration.")
    else:
        # Prepare data for display: ensure 'Date' is displayed nicely but use original for charts
        df_display = df_summary.copy()
        
        # Format currency columns for display
        currency_cols = ['Start Bal.', 'Target P&L', 'Actual P&L', 'Deposit/Bonus', 'End Bal.']
        for col in currency_cols:
             if col in df_display.columns:
                df_display[col] = pd.to_numeric(df_display[col], errors='coerce').apply(lambda x: f"${x:,.2f}" if pd.notna(x) else '$0.00')

        # Drop columns that are not in the sheet if they accidentally crept in (like a temporary 'Date_str')
        cols_to_keep = ['Date', 'Week', 'Trades', 'Start Bal.', 'Target P&L', 'Actual P&L', 'Deposit/Bonus', 'End Bal.']
        df_display = df_display[[col for col in cols_to_keep if col in df_display.columns]]
            
        st.dataframe(
            df_display.sort_values(by='Date', ascending=False), 
            use_container_width=True,
            hide_index=True
        )
        
        st.subheader("📉 Balance Progression")
        
        # Ensure chronological order for the chart
        df_chart = df_summary.sort_values(by='Date', ascending=True)

        fig = px.line(
            df_chart, 
            x='Date',
            y='End Bal.',
            title='Balance Progression',
            markers=True,
            height=400
        )
        fig.update_layout(
            xaxis_title="Date", 
            yaxis_title="Balance ($)",
            hovermode='x unified'
        )
        st.plotly_chart(fig, use_container_width=True)

# --- Tab 3: Performance Analytics ---
with tab3:
    st.header("Performance Analytics")
    
    if df_summary.empty:
        st.info("No summary data yet. Start trading to see your progress!")
    else:
        # Use summary data for P&L chart
        df_chart = df_summary.sort_values(by='Date', ascending=True)
        
        col_pnl, col_winrate = st.columns(2)
        
        with col_pnl:
            st.subheader("Daily P&L Chart")
            fig_pnl = px.bar(
                df_chart, 
                x='Date',
                y='Actual P&L',
                title='Daily Trading Profit/Loss',
                color='Actual P&L',
                color_continuous_scale=px.colors.diverging.RdYlGn,
                height=400
            )
            fig_pnl.update_layout(xaxis_title="Date", yaxis_title="P&L ($)")
            st.plotly_chart(fig_pnl, use_container_width=True)
            
        with col_winrate:
            st.subheader("Trade Win/Loss Breakdown")
            
            if not df_trades.empty:
                # Use raw trades for win/loss calculation
                df_trades_temp = df_trades.copy()
                df_trades_temp['Result'] = df_trades_temp['P&L'].apply(lambda x: 'Win' if x > 0 else ('Loss' if x < 0 else 'Breakeven'))
                
                result_counts = df_trades_temp['Result'].value_counts().reset_index()
                result_counts.columns = ['Result', 'Count']
                
                fig_pie = px.pie(
                    result_counts, 
                    names='Result', 
                    values='Count',
                    title='Total Trade Outcomes',
                    color_discrete_map={'Win': 'green', 'Loss': 'red', 'Breakeven': 'blue'},
                    height=400
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                 st.info("No trades logged yet to calculate win/loss.")
