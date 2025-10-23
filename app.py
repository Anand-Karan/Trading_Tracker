import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import gspread
from gspread_dataframe import set_with_dataframe, get_dataframe

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
        # This block was likely incomplete in your local file, causing the error.
        st.error(f"Error connecting to Google Sheets: {e}")
        return None

def get_data_from_sheet(sheet_name):
    """Retrieves data from a specific sheet as a pandas DataFrame."""
    gc = connect_gsheets()
    if not gc: return pd.DataFrame()
    try:
        # Open the spreadsheet by its ID
        spreadsheet = gc.open_by_key(SHEET_ID)
        worksheet = spreadsheet.worksheet(sheet_name)
        
        # Read all data into a DataFrame
        df = get_dataframe(worksheet, evaluate_formulas=True)
        
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
    """Writes a DataFrame to a specific sheet (append or overwrite/replace)."""
    gc = connect_gsheets()
    if not gc: return False
    try:
        spreadsheet = gc.open_by_key(SHEET_ID)
        worksheet = spreadsheet.worksheet(sheet_name)
        
        if mode == 'append':
            # Append the DataFrame to the existing data (ignoring header for append)
            set_with_dataframe(worksheet, df, row=len(worksheet.get_all_values()) + 1, include_column_header=False, resize=True)
        elif mode == 'replace':
            # Clear the sheet and write the new DataFrame (including header)
            worksheet.clear()
            set_with_dataframe(worksheet, df, include_index=False, include_column_header=True, resize=True)
            
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
        
        # Pull any existing deposit/bonus for this date from the old summary (if it exists)
        # For simplicity in this demo, we'll assume a dedicated 'deposits' sheet or a simple tracking mechanism 
        # For now, we'll just track the running balance
        
        start_balance = current_balance
        end_balance = start_balance + total_pl
        target_pl = start_balance * 0.065
        
        daily_summary_list.append({
            'Date': date.strftime("%Y-%m-%d"),
            'Week': week_counter, # Simplified week calculation
            'Trades': num_trades,
            'Start Bal.': round(start_balance, 2),
            'Target P&L': round(target_pl, 2),
            'Actual P&L': round(total_pl, 2),
            'Deposit/Bonus': 0.00, # Handled separately in the Add Deposit/Bonus form
            'End Bal.': round(end_balance, 2),
        })
        current_balance = end_balance # Update running balance for the next day's starting balance
        week_counter = (date - df_trades['entry_date'].min()).days // 7 + 1


    df_summary = pd.DataFrame(daily_summary_list)
    
    # 4. Handle Deposits/Bonuses separately from the 'trades' sheet
    # Since deposits/bonuses modify 'End Bal.' directly, we first read the existing summary
    df_old_summary = get_data_from_sheet('daily_summary')
    if not df_old_summary.empty:
        df_old_summary['Date'] = pd.to_datetime(df_old_summary['Date']).dt.date
        df_summary['Date'] = pd.to_datetime(df_summary['Date']).dt.date
        
        # Merge the new summary with the old one to preserve Deposit/Bonus amounts
        df_merged = pd.merge(df_summary, df_old_summary[['Date', 'Deposit/Bonus']], on='Date', how='left', suffixes=('_new', '_old'))
        df_merged['Deposit/Bonus'] = pd.to_numeric(df_merged['Deposit/Bonus_old'], errors='coerce').fillna(0.00)
        
        # Re-calculate End Bal. including the preserved deposit/bonus
        df_merged['End Bal.'] = df_merged['End Bal.'] + df_merged['Deposit/Bonus']
        
        # Final cleanup for the summary sheet columns
        df_summary = df_merged[['Date', 'Week', 'Trades', 'Start Bal.', 'Target P&L', 'Actual P&L', 'Deposit/Bonus', 'End Bal.']]
        df_summary['Date'] = df_summary['Date'].dt.strftime("%Y-%m-%d") # Convert back to string for sheets

    # 5. Write the final, recalculated summary back to the sheet
    if not df_summary.empty:
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
            df_summary['Date'] = pd.to_datetime(df_summary['Date'])
            df_summary['End Bal.'] = pd.to_numeric(df_summary['End Bal.'], errors='coerce').fillna(0)
            df_summary['Actual P&L'] = pd.to_numeric(df_summary['Actual P&L'], errors='coerce').fillna(0)
        except Exception as e:
            st.warning(f"Could not convert summary data types: {e}")
            df_summary = pd.DataFrame()

    if not df_trades.empty:
        try:
            df_trades['entry_date'] = pd.to_datetime(df_trades['entry_date'])
            df_trades['P&L'] = pd.to_numeric(df_trades['P&L'], errors='coerce').fillna(0)
        except Exception as e:
            st.warning(f"Could not convert trades data types: {e}")
            df_trades = pd.DataFrame()
            
    return df_summary, df_trades

# --- Initialize App and State ---

# Run initial calculation if data is empty or missing (especially on first run)
if 'initial_balance' not in st.session_state:
    st.session_state.initial_balance = 2272.22 # Using the starting balance from your screenshot

# Load data on page load
df_summary, df_trades = load_data()

# Recalculate if the summary is critically empty but trades exist (to catch first-time use)
if df_summary.empty and not df_trades.empty:
    recalculate_all_summaries(st.session_state.initial_balance)
    df_summary, df_trades = load_data() # Reload data after recalculation

# --- Sidebar: Quick Stats ---

with st.sidebar:
    st.markdown("### 📊 Quick Stats")
    
    # Current Balance
    current_balance = df_summary['End Bal.'].iloc[-1] if not df_summary.empty else st.session_state.initial_balance
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
            if df_summary.empty:
                 # This should rarely happen but handles edge case if no summary exists
                recalculate_all_summaries(st.session_state.initial_balance)
                df_summary, _ = load_data() 
                
            # Find the row for the deposit date
            deposit_date_str = deposit_date.strftime("%Y-%m-%d")
            
            # Find the row index to update
            df_summary_temp = df_summary.copy()
            df_summary_temp['Date'] = df_summary_temp['Date'].astype(str) # Match string format
            
            # Check if an entry for this date already exists
            target_index = df_summary_temp[df_summary_temp['Date'] == deposit_date_str].index
            
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
                
                # Write back the updated summary sheet
                write_data_to_sheet('daily_summary', df_summary_temp, mode='replace')
                
                # Rerun summary calculation to update subsequent rows if any
                recalculate_all_summaries(st.session_state.initial_balance)
                
                # Clear cache and trigger reload
                st.cache_resource.clear()
                st.experimental_rerun()
            else:
                st.error("Cannot add deposit to a date without a corresponding trade entry.")
                
            

# --- Main Page: Title and Tabs ---
st.title("📈 Trading Performance Tracker")

tab1, tab2, tab3 = st.tabs(["💵 Trade Entry", "🗓️ Daily Summary", "📊 Analytics"])

# --- Tab 1: Trade Entry Form ---
with tab1:
    st.header("Log a New Trade")
    
    with st.form("Trade Entry Form"):
        # Trade Details
        col_1, col_2 = st.columns(2)
        with col_1:
            trade_type = st.selectbox("Type", ["Long", "Short"])
            entry_price = st.number_input("Entry Price", min_value=0.01, format="%.2f")
            stop_loss = st.number_input("Stop Loss", min_value=0.01, format="%.2f")
            pnl = st.number_input("P&L ($)", help="Enter profit as positive, loss as negative.")
        with col_2:
            market = st.selectbox("Market", ["Stock", "Forex", "Crypto", "Futures"])
            exit_price = st.number_input("Exit Price", min_value=0.01, format="%.2f")
            target_price = st.number_input("Target Price", min_value=0.01, format="%.2f")
            trade_date = st.date_input("Entry Date", datetime.now().date())
        
        notes = st.text_area("Notes")
        
        submitted = st.form_submit_button("Submit Trade")

        if submitted:
            # Create a new row of data
            new_trade_data = pd.DataFrame([{
                'entry_date': trade_date.strftime("%Y-%m-%d"),
                'trade_type': trade_type,
                'market': market,
                'entry_price': entry_price,
                'exit_price': exit_price,
                'stop_loss': stop_loss,
                'target_price': target_price,
                'P&L': pnl,
                'notes': notes,
            }])
            
            # Write new trade to the 'trades' sheet
            if write_data_to_sheet('trades', new_trade_data, mode='append'):
                st.success("Trade successfully logged!")
                
                # Recalculate all summaries and running balances
                recalculate_all_summaries(st.session_state.initial_balance)
                
                # Clear cache and trigger reload to update stats
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
            df_display[col] = df_display[col].apply(lambda x: f"${x:,.2f}")
            
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