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
        st.error(f"Could not connect to Google Sheets. Check your `secrets.toml` and credentials. Error: {e}")
        return None

def load_data(sheet_name):
    """Loads a specific sheet as a Pandas DataFrame."""
    client = connect_gsheets()
    if client is None:
        return pd.DataFrame() # Return empty if client connection failed
        
    try:
        sh = client.open_by_key(SHEET_ID)
        worksheet = sh.worksheet(sheet_name)
        # We use get_dataframe here, assuming gspread_dataframe is correctly installed
        # as verified in requirements.txt
        df = get_dataframe(worksheet, evaluate_formulas=True)
        # Standardize column names (make them lower case and replace spaces)
        df.columns = df.columns.str.lower().str.replace(' ', '_')
        return df
    except Exception as e:
        # Display this error if the gspread_dataframe methods are the problem
        st.error(f"Error reading data from sheet '{sheet_name}': {type(e).__name__}: {e}")
        return pd.DataFrame()

def update_sheet(df, sheet_name):
    """Writes a Pandas DataFrame to a specific sheet."""
    client = connect_gsheets()
    if client is None:
        return False

    try:
        sh = client.open_by_key(SHEET_ID)
        worksheet = sh.worksheet(sheet_name)
        
        # We use set_with_dataframe here
        set_with_dataframe(worksheet, df)
        return True
    except Exception as e:
        st.error(f"Error writing data to sheet '{sheet_name}': {type(e).__name__}: {e}")
        return False

# --- Data Loading ---
trades_df = load_data("trades")
daily_summary_df = load_data("daily_summary")


# --- Utility Functions for Calculations ---
def calculate_quick_stats(summary_df, trades_df):
    stats = {}
    
    # Current Balance (Last row of End Bal column)
    if 'end_bal' in summary_df.columns and not summary_df.empty:
        stats['current_balance'] = summary_df['end_bal'].iloc[-1]
    else:
        stats['current_balance'] = 0.00
    
    # Total Trades
    stats['total_trades'] = len(trades_df)
    
    # Week Number
    if 'week' in summary_df.columns and not summary_df.empty:
        stats['week'] = summary_df['week'].iloc[-1]
    else:
        stats['week'] = 1

    # Total Trading P&L
    if 'actual_p&l' in summary_df.columns and not summary_df.empty:
        # Sum of all P&L entries
        stats['total_pnl'] = summary_df['actual_p&l'].sum()
    else:
        stats['total_pnl'] = 0.00

    # P&L Percentage (requires calculation, simple example: total P&L / initial balance)
    initial_balance = summary_df.loc[summary_df['week'] == 1, 'start_bal'].iloc[0] if not summary_df.empty and 'start_bal' in summary_df.columns else 1000 # Use a default initial balance
    
    if initial_balance > 0 and stats['total_pnl'] != 0:
        stats['pnl_percent'] = (stats['total_pnl'] / initial_balance) * 100
    else:
        stats['pnl_percent'] = 0.00
        
    return stats

# --- Streamlit Layout ---
st.set_page_config(layout="wide", initial_sidebar_state="expanded", page_title="Trading Performance Tracker")

# Calculate stats once
quick_stats = calculate_quick_stats(daily_summary_df, trades_df)


# Sidebar layout for quick stats
with st.sidebar:
    st.markdown("### 📊 Quick Stats")
    
    # Current Balance
    st.metric(
        label="Current Balance",
        value=f"${quick_stats['current_balance']:,.2f}",
        delta=f"${quick_stats['current_balance'] - quick_stats['current_balance'] if len(daily_summary_df) < 2 else daily_summary_df['end_bal'].iloc[-1] - daily_summary_df['end_bal'].iloc[-2]:,.2f}", # Simple delta, could be improved
        delta_color="normal"
    )
    
    # Total Trades
    st.metric(label="Total Trades", value=quick_stats['total_trades'])
    
    # Week Number
    st.metric(label="Week", value=quick_stats['week'])
    
    # Total Trading P&L
    st.metric(
        label="Total Trading P&L",
        value=f"${quick_stats['total_pnl']:,.2f}",
        delta=f"{quick_stats['pnl_percent']:,.2f}%",
        delta_color="normal" if quick_stats['pnl_percent'] >= 0 else "inverse"
    )
    
    st.markdown("---")
    
    st.markdown("### Add Deposit/Bonus")
    
    # Deposit/Bonus Form
    with st.form(key='deposit_form'):
        deposit_date = st.date_input("Date", datetime.now().date())
        deposit_amount = st.number_input("Amount ($)", min_value=0.00, value=0.00, step=0.01)
        
        deposit_submitted = st.form_submit_button("Record Deposit")
        
        if deposit_submitted and deposit_amount > 0:
            
            # 1. Update daily_summary sheet
            new_end_bal = quick_stats['current_balance'] + deposit_amount
            
            if not daily_summary_df.empty and str(daily_summary_df['date'].iloc[-1]) == str(deposit_date):
                # If a row for today already exists, update the existing row
                daily_summary_df.loc[daily_summary_df.index[-1], 'deposit/bonus'] += deposit_amount
                daily_summary_df.loc[daily_summary_df.index[-1], 'end_bal'] = new_end_bal
            else:
                # Add a new row for the deposit (this simple logic may need review for multi-day gaps)
                new_row = {
                    'date': str(deposit_date),
                    'week': quick_stats['week'], # Assumes same week
                    'trades_start_bal': quick_stats['current_balance'],
                    'target_p&l': daily_summary_df['target_p&l'].iloc[-1] if not daily_summary_df.empty else 0,
                    'actual_p&l': 0.00,
                    'deposit/bonus': deposit_amount,
                    'end_bal': new_end_bal
                }
                daily_summary_df = pd.concat([daily_summary_df, pd.DataFrame([new_row])], ignore_index=True)
            
            if update_sheet(daily_summary_df, "daily_summary"):
                st.success("Deposit successfully recorded! Refreshing app...")
                st.rerun()
            else:
                st.error("Failed to update daily summary sheet.")
                
            
# --- Main Content ---
st.title("📈 Trading Performance Tracker")

# Tabs
tab1, tab2, tab3 = st.tabs(["📊 Trade Entry", "🗒️ Daily Summary", "📈 Analytics"])

with tab1:
    st.markdown("### Log a New Trade")
    
    # Trade Entry Form
    with st.form(key='trade_form', clear_on_submit=True):
        
        col1, col2 = st.columns(2)
        
        with col1:
            trade_type = st.selectbox("Type", ["Long", "Short"], index=0)
            entry_price = st.number_input("Entry Price", min_value=0.01, value=0.01, step=0.01)
            stop_loss = st.number_input("Stop Loss", min_value=0.01, value=0.01, step=0.01)
            pnl_dollars = st.number_input("P&L ($)", min_value=-1000000.00, value=0.00, step=0.01, help="Enter the actual P&L from the trade.")
            investment = st.number_input("Investment ($)", min_value=0.01, value=100.00, step=0.01)
            
        with col2:
            market = st.selectbox("Market", ["Stock", "Crypto", "Forex", "Futures"], index=0)
            exit_price = st.number_input("Exit Price", min_value=0.01, value=0.01, step=0.01)
            target_price = st.number_input("Target Price", min_value=0.01, value=0.01, step=0.01)
            trade_date = st.date_input("Entry Date", datetime.now().date())
            pnl_percent = st.number_input("P&L %", min_value=-100.00, value=0.00, step=0.01, help="P&L as a percentage of investment.")

        notes = st.text_area("Notes", placeholder="Enter any trade analysis or emotional notes here...")
        
        trade_submitted = st.form_submit_button("Submit Trade")
        
        if trade_submitted:
            
            # Data validation (minimal check)
            if pnl_dollars == 0.00 and pnl_percent == 0.00:
                st.warning("Please enter the P&L ($) or P&L (%).")
            else:
                # --- 1. Prepare new trade record ---
                new_trade = {
                    # Assuming these columns exist in the 'trades' sheet
                    'trade_date': str(trade_date),
                    'type': trade_type,
                    'market': market,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'stop_loss': stop_loss,
                    'target_price': target_price,
                    'investment': investment,
                    'pnl': pnl_dollars,
                    'pnl_pct': pnl_percent,
                    'notes': notes
                }
                
                # --- 2. Append new trade to DataFrame and sheet ---
                # Ensure column consistency
                new_trade_df = pd.DataFrame([new_trade])
                
                # Ensure the trades_df has all expected columns from the new trade (in case it was empty)
                for col in new_trade_df.columns:
                    if col not in trades_df.columns:
                        trades_df[col] = pd.NA

                trades_df = pd.concat([trades_df, new_trade_df], ignore_index=True)
                
                if update_sheet(trades_df, "trades"):
                    st.success("Trade successfully logged!")
                    
                    # --- 3. Update Daily Summary ---
                    if not daily_summary_df.empty:
                        last_row_index = daily_summary_df.index[-1]
                        
                        # Get today's date in string format for comparison
                        today_date_str = str(trade_date)
                        last_summary_date_str = str(daily_summary_df.loc[last_row_index, 'date'])
                        
                        # If the last entry is NOT for today, we must create a new summary row for today
                        if last_summary_date_str != today_date_str:
                            new_end_bal = daily_summary_df.loc[last_row_index, 'end_bal']
                            
                            new_summary_row = {
                                'date': today_date_str,
                                'week': quick_stats['week'], # Assumes same week
                                'trades_start_bal': new_end_bal, # Yesterday's end is today's start
                                'target_p&l': daily_summary_df.loc[last_row_index, 'target_p&l'], # Carry over target P&L
                                'actual_p&l': pnl_dollars,
                                'deposit/bonus': 0.00,
                                'end_bal': new_end_bal + pnl_dollars
                            }
                            daily_summary_df = pd.concat([daily_summary_df, pd.DataFrame([new_summary_row])], ignore_index=True)
                            
                        # If the last entry IS for today, update the existing row
                        else:
                            daily_summary_df.loc[last_row_index, 'actual_p&l'] += pnl_dollars
                            daily_summary_df.loc[last_row_index, 'end_bal'] += pnl_dollars
                            
                        # Final update to the daily summary sheet
                        if update_sheet(daily_summary_df, "daily_summary"):
                            st.info("Daily summary updated.")
                            
                        # --- THIS IS THE FIX ---
                        st.rerun() # Line 405 (now uses the correct function)
                    else:
                        st.error("Cannot update daily summary because daily_summary sheet is empty.")
                        
                else:
                    st.error("Failed to update trades sheet.")


with tab2:
    st.markdown("### Daily Performance Summary")
    if not daily_summary_df.empty:
        # Display the summary table
        st.dataframe(daily_summary_df, use_container_width=True)
        
        # Simple Chart of End Balance over time
        if 'date' in daily_summary_df.columns and 'end_bal' in daily_summary_df.columns:
            fig_bal = px.line(
                daily_summary_df, 
                x='date', 
                y='end_bal', 
                title='Account Balance Over Time',
                labels={'date': 'Date', 'end_bal': 'Ending Balance ($)'},
                line_shape="linear"
            )
            fig_bal.update_layout(xaxis_title="", yaxis_title="Balance ($)", hovermode="x unified")
            st.plotly_chart(fig_bal, use_container_width=True)
        else:
            st.warning("Daily Summary data is missing required columns ('date', 'end_bal') for charting.")
    else:
        st.info("No daily summary data available. Please check the sheet name and data format.")
        

with tab3:
    st.markdown("### Analytics and Trade Breakdown")
    if not trades_df.empty:
        # P&L Distribution (Simple Histogram)
        if 'pnl_pct' in trades_df.columns:
            st.markdown("#### P&L Percentage Distribution")
            fig_pnl_dist = px.histogram(
                trades_df, 
                x='pnl_pct', 
                nbins=20, 
                title='P&L % Distribution Across Trades',
                labels={'pnl_pct': 'P&L Percentage'},
                color_discrete_sequence=['#FF4B4B']
            )
            fig_pnl_dist.update_layout(xaxis_title="P&L %", yaxis_title="Trade Count")
            st.plotly_chart(fig_pnl_dist, use_container_width=True)
        
        # Performance by Market
        if 'market' in trades_df.columns and 'pnl' in trades_df.columns:
            st.markdown("#### Performance by Market")
            market_pnl = trades_df.groupby('market')['pnl'].sum().reset_index()
            fig_market = px.bar(
                market_pnl, 
                x='market', 
                y='pnl', 
                title='Total P&L by Market',
                labels={'market': 'Market', 'pnl': 'Total P&L ($)'},
                color='market'
            )
            fig_market.update_layout(xaxis_title="", yaxis_title="Total P&L ($)")
            st.plotly_chart(fig_market, use_container_width=True)
            
        st.markdown("---")
        st.markdown("#### Raw Trades Data")
        st.dataframe(trades_df, use_container_width=True)
        
    else:
        st.info("No trade data available to run analytics. Submit a trade first!")
