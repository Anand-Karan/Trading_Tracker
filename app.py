import sqlite3
from pathlib import Path
from datetime import date, datetime, timedelta
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURATION ---
DB_PATH = Path("trades.db")
INITIAL_BALANCE = 2272.22

# --- DATABASE FUNCTIONS ---

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.executescript(
        """
        -- Create daily_summary table
        CREATE TABLE IF NOT EXISTS daily_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date TEXT UNIQUE,
            week INTEGER,
            trades INTEGER DEFAULT 0,
            start_balance REAL DEFAULT 0,
            profit_needed REAL DEFAULT 0,
            actual_profit REAL DEFAULT 0,
            deposit_bonus REAL DEFAULT 0,
            end_balance REAL DEFAULT 0,
            weekly_profit REAL DEFAULT 0
        );

        -- Create trades table (Updated: Removed entry and exit columns)
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_date TEXT,
            ticker TEXT,
            leverage INTEGER,
            direction TEXT,
            investment REAL,
            pnl REAL,
            pnl_pct REAL
        );
        """
    )

    # --- Database Migration Step: Add missing deposit_bonus column if needed ---
    try:
        conn.execute("SELECT deposit_bonus FROM daily_summary LIMIT 1").fetchone()
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE daily_summary ADD COLUMN deposit_bonus REAL DEFAULT 0")
        conn.commit()
        st.info("Database updated: 'deposit_bonus' column added to daily_summary.")
        
    # --- Database Migration Step: Check for and drop old 'entry'/'exit' columns (Cleanup) ---
    # This block is purely for cleanup and can be safely ignored if starting with a new trades.db
    # try:
    #     conn.execute("SELECT entry, exit FROM trades LIMIT 1").fetchone()
    #     # If the above succeeds, the old columns exist. Dropping them requires complex SQL which we skip.
    #     # If you see errors related to old columns, delete trades.db
    # except sqlite3.OperationalError:
    #     pass

    return conn

def calculate_profit_needed(start_balance):
    """Profit needed is MIN(start_balance * 0.066, 1000)"""
    return min(start_balance * 0.066, 1000)

def get_daily_trades_sum(conn, trade_date):
    """Sum all P&L and count trades for a specific date"""
    row = conn.execute(
        "SELECT COALESCE(SUM(pnl), 0), COUNT(*) FROM trades WHERE trade_date = ?",
        (trade_date,)
    ).fetchone()
    return row[0], row[1]

def get_week_number(input_date):
    """Calculate week number from start of tracking"""
    start_date = date(2025, 10, 20)  # Adjust to your actual start date
    days_diff = (input_date - start_date).days
    return max(1, (days_diff // 7) + 1)


# --- NEW: CORE BALANCE RECALCULATION FUNCTION ---
def recalculate_all_summaries(conn):
    """
    Recalculates the entire daily_summary table chronologically to ensure
    cascading balance integrity (especially after deletions).
    """
    # 1. Fetch all unique dates that have entries in either table
    trade_dates = pd.read_sql("SELECT DISTINCT trade_date FROM trades ORDER BY trade_date ASC", conn)['trade_date'].tolist()
    summary_dates = pd.read_sql("SELECT DISTINCT entry_date FROM daily_summary ORDER BY entry_date ASC", conn)['entry_date'].tolist()
    
    all_dates = sorted(list(set(trade_dates) | set(summary_dates)))

    current_balance = INITIAL_BALANCE
    
    # Iterate through all dates in chronological order
    for entry_date in all_dates:
        
        # Get trade summary for this specific date
        daily_pnl, trade_count = get_daily_trades_sum(conn, entry_date)
        
        # Get existing record for deposit_bonus (must be preserved)
        existing_row = conn.execute(
            "SELECT deposit_bonus FROM daily_summary WHERE entry_date = ?", (entry_date,)
        ).fetchone()
        deposit_bonus = existing_row[0] if existing_row else 0.0
        
        # Calculate derived metrics
        start_balance = current_balance
        profit_needed = calculate_profit_needed(start_balance)
        end_balance = start_balance + daily_pnl + deposit_bonus
        
        # Calculate week number
        try:
            d = datetime.strptime(entry_date, "%Y-%m-%d").date()
            week = get_week_number(d)
        except ValueError:
            week = 1 # Default for invalid date
        
        # Update or insert the record
        conn.execute(
            """
            INSERT INTO daily_summary
            (entry_date, week, trades, start_balance, profit_needed,
             actual_profit, deposit_bonus, end_balance, weekly_profit)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0) 
            ON CONFLICT(entry_date) DO UPDATE SET
                week=excluded.week,
                trades=excluded.trades,
                start_balance=excluded.start_balance,
                profit_needed=excluded.profit_needed,
                actual_profit=excluded.actual_profit,
                deposit_bonus=excluded.deposit_bonus,
                end_balance=excluded.end_balance
            """,
            (entry_date, week, trade_count, start_balance, profit_needed,
             daily_pnl, deposit_bonus, end_balance)
        )
        
        # Set the current balance for the next iteration (next day's start balance)
        current_balance = end_balance
        
    conn.commit()
    
    # 2. Delete summary records for dates that no longer have trades/bonuses
    # This prevents orphaned summary records if the only activity for a day was a deleted trade.
    dates_to_delete = [
        s_date for s_date in summary_dates
        if s_date not in trade_dates and conn.execute("SELECT deposit_bonus FROM daily_summary WHERE entry_date = ?", (s_date,)).fetchone()[0] == 0.0
    ]
    for d_date in dates_to_delete:
         conn.execute("DELETE FROM daily_summary WHERE entry_date = ?", (d_date,))
    conn.commit()

# --- MODIFIED: update_daily_summary simplified as it just focuses on one day's deposit/bonus ---
def update_daily_summary(conn, trade_date, new_deposit_bonus=0.0):
    """
    Updates the deposit/bonus for a single day and then triggers full recalculation.
    """
    # 1. Update the deposit_bonus first
    if new_deposit_bonus != 0.0:
        # Ensure a record exists for deposit update if it's the first activity of the day
        conn.execute(
            """
            INSERT INTO daily_summary (entry_date, deposit_bonus)
            VALUES (?, ?)
            ON CONFLICT(entry_date) DO UPDATE SET
            deposit_bonus = deposit_bonus + excluded.deposit_bonus
            """,
            (trade_date, new_deposit_bonus)
        )
        conn.commit()

    # 2. Trigger the full chronological recalculation to fix all balances
    recalculate_all_summaries(conn)


# ===================== STREAMLIT APP =====================

st.set_page_config(page_title="Trading Tracker", layout="wide", page_icon="📈")

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
    }
    .stTabs [data-baseweb="tab-list"] button {
        font-size: 18px;
    }
</style>
""", unsafe_allow_html=True)

st.title("📈 Trading Performance Tracker")

conn = get_conn()
recalculate_all_summaries(conn) # Ensure sidebar stats are correct on initial load

# ===================== SIDEBAR STATS =====================
st.sidebar.header("📊 Quick Stats")

# Get latest data
df_summary = pd.read_sql("SELECT * FROM daily_summary ORDER BY entry_date DESC", conn)
if not df_summary.empty:
    latest = df_summary.iloc[0]
    total_trades = conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    
    st.sidebar.metric("Current Balance", f"${latest['end_balance']:,.2f}", 
                     f"${latest['actual_profit']:,.2f}")
    st.sidebar.metric("Total Trades", total_trades)
    st.sidebar.metric("Week", int(latest['week']))
    
    # Calculate total P&L from start (excluding deposits)
    total_deposits = df_summary['deposit_bonus'].sum()
    total_pnl = latest['end_balance'] - INITIAL_BALANCE - total_deposits
    pnl_pct = (total_pnl / INITIAL_BALANCE) * 100 if INITIAL_BALANCE > 0 else 0
    st.sidebar.metric("Total Trading P&L", f"${total_pnl:,.2f}", f"{pnl_pct:.2f}%")
else:
    # Show initial state
    st.sidebar.metric("Current Balance", f"${INITIAL_BALANCE:,.2f}")
    st.sidebar.metric("Total Trades", 0)
    st.sidebar.metric("Week", 1)
    st.sidebar.metric("Total Trading P&L", "$0.00", "0.00%")
    st.sidebar.info("💡 Add your first trade to get started!")

# ===================== TABS =====================
tab1, tab2, tab3 = st.tabs(["💹 Trade Entry", "📅 Daily Summary", "📈 Analytics"])

# ===================== TAB 1: TRADE ENTRY =====================
with tab1:
    st.header("💹 Log New Trade / Deposit")
    
    col_main, col_summary = st.columns([2, 1])
    
    with col_main:
        with st.form("trade_form", clear_on_submit=True):
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                trade_date = st.date_input("Date", date.today())
                ticker = st.text_input("Ticker (Optional for Deposit)", placeholder="e.g., BTC").upper()
                leverage = st.number_input("Leverage", min_value=1, max_value=125, value=50, step=1)
            
            with col_b:
                direction = st.selectbox("Direction", ["LONG", "SHORT"])
                investment = st.number_input("Investment ($)", min_value=0.0, value=20.0, step=1.0)
                pnl = st.number_input("P&L ($)", value=0.0, step=0.01, format="%.2f")
            
            with col_c:
                # P&L % is now directly entered by the user
                pnl_pct = st.number_input("P&L % (User Input)", value=0.0, step=0.1, format="%.2f")
                deposit_bonus = st.number_input("Deposit/Bonus ($) (Optional)", value=0.0, step=10.0)
                
            st.markdown("---")
            submitted = st.form_submit_button("💾 Save Entry", use_container_width=True, type="primary")
            
            if submitted:
                # Handle Trade Entry
                if ticker and (pnl != 0 or pnl_pct != 0):
                    if investment == 0 and pnl != 0:
                        st.warning("Investment is $0. P&L % may not be meaningful.")
                    
                    # Insert trade
                    conn.execute(
                        """
                        INSERT INTO trades 
                        (trade_date, ticker, leverage, direction, investment, pnl, pnl_pct)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (trade_date.isoformat(), ticker, leverage, direction, 
                         investment, pnl, pnl_pct)
                    )
                    conn.commit()
                    
                    # Update daily summary with the potential deposit/bonus and trigger full recalculation
                    update_daily_summary(conn, trade_date.isoformat(), new_deposit_bonus=deposit_bonus)
                    
                    st.success(f"✅ Trade added: {direction} {ticker} · P&L: ${pnl:.2f}")
                    st.rerun()
                
                # Handle Deposit/Bonus Only
                elif deposit_bonus != 0:
                    # Update daily summary just for the deposit/bonus and trigger full recalculation
                    update_daily_summary(conn, trade_date.isoformat(), new_deposit_bonus=deposit_bonus)
                    st.success(f"✅ Deposit/Bonus of ${deposit_bonus:.2f} added to {trade_date}")
                    st.rerun()
                
                # Handle Error
                else:
                    st.error("Please enter valid trade details (Ticker and P&L) OR a Deposit/Bonus amount.")
    
    with col_summary:
        # Show today's trades summary - Need to re-read df_summary after potential updates
        df_summary_today = pd.read_sql("SELECT * FROM daily_summary WHERE entry_date = ?", conn, params=(date.today().isoformat(),))
        
        today = date.today().isoformat()
        today_pnl, today_count = get_daily_trades_sum(conn, today)
        
        # Get start balance (previous day's end balance) for today's target
        start_bal_row = pd.read_sql("SELECT end_balance FROM daily_summary WHERE entry_date < ? ORDER BY entry_date DESC LIMIT 1", conn, params=(today,))
        start_bal = start_bal_row.iloc[0]['end_balance'] if not start_bal_row.empty else INITIAL_BALANCE
        
        target = calculate_profit_needed(start_bal)
        
        st.subheader("📊 Today's Summary")
        
        today_deposit_bonus = df_summary_today.iloc[0]['deposit_bonus'] if not df_summary_today.empty else 0.0

        st.metric("Trades Today", today_count)
        st.metric("Today's Trading P&L", f"${today_pnl:.2f}", 
                 delta_color="normal" if today_pnl >= 0 else "inverse")
        st.metric("Total Deposits/Bonus Today", f"${today_deposit_bonus:.2f}")

        st.markdown("---")
        
        st.metric("Today's Target P&L", f"${target:.2f}")
        
        if target > 0:
            progress = (today_pnl / target) * 100
            # Clamp progress between 0 and 100 for the progress bar display
            progress_bar_value = min(max(progress / 100, 0), 1)
            st.progress(progress_bar_value)
            st.caption(f"{progress:.1f}% of target")

    st.markdown("---")
    
    # Recent trades table
    st.subheader("📋 Recent Trades")
    trades_df = pd.read_sql(
        "SELECT * FROM trades ORDER BY trade_date DESC, id DESC LIMIT 20", 
        conn
    )
    
    if not trades_df.empty:
        # Format for display
        display_df = trades_df[['id', 'trade_date', 'ticker', 'leverage', 'direction', 
                                'investment', 'pnl', 'pnl_pct']].copy()
        display_df['pnl'] = display_df['pnl'].apply(lambda x: f"${x:.2f}")
        display_df['pnl_pct'] = display_df['pnl_pct'].apply(lambda x: f"{x:.2f}%")
        display_df['investment'] = display_df['investment'].apply(lambda x: f"${x:.2f}")
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Delete trade option
        st.subheader("🗑️ Delete Trade")
        col_del1, col_del2 = st.columns([3, 1])
        with col_del1:
            trade_to_delete = st.selectbox(
                "Select trade ID to delete",
                options=trades_df['id'].tolist(),
                format_func=lambda x: f"ID {x}: {trades_df[trades_df['id']==x]['ticker'].values[0]} - {trades_df[trades_df['id']==x]['trade_date'].values[0]} - P&L: ${trades_df[trades_df['id']==x]['pnl'].values[0]:.2f}"
            )
        with col_del2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True) # Spacer
            if st.button("🗑️ Delete Selected Trade", type="secondary", use_container_width=True):
                # Get the trade date before deleting
                trade_date_to_update = conn.execute(
                    "SELECT trade_date FROM trades WHERE id = ?", (trade_to_delete,)
                ).fetchone()[0]
                
                # Delete the trade
                conn.execute("DELETE FROM trades WHERE id = ?", (trade_to_delete,))
                conn.commit()
                
                # Trigger full recalculation
                recalculate_all_summaries(conn)
                
                st.success(f"✅ Trade ID {trade_to_delete} deleted and all balances updated.")
                st.rerun()
    else:
        st.info("No trades yet. Add your first trade above!")

# ===================== TAB 2: DAILY SUMMARY =====================
with tab2:
    st.header("📅 Daily Summary")
    
    # Get the final, correct data for display (DESC order is usually preferred for tables)
    # df_display is read from the DB and contains columns like 'entry_date', 'end_balance', etc.
    df_display = pd.read_sql("SELECT * FROM daily_summary ORDER BY entry_date DESC", conn)
    
    if not df_display.empty:
        
        # Create a separate DataFrame for the table display where names are changed
        display_summary = df_display[['entry_date', 'week', 'trades', 'start_balance', 
                                     'profit_needed', 'actual_profit', 'deposit_bonus', 
                                     'end_balance']].copy()
        
        # Rename columns for clarity in the table (display_summary only)
        display_summary.columns = ['Date', 'Week', 'Trades', 'Start Bal.', 
                                   'Target P&L', 'Actual P&L', 'Deposit/Bonus', 
                                   'End Bal.']
        
        # Format currency columns
        for col in ['Start Bal.', 'Target P&L', 'Actual P&L', 'Deposit/Bonus', 'End Bal.']:
            display_summary[col] = display_summary[col].apply(lambda x: f"${x:,.2f}")
        
        st.dataframe(display_summary, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        
        # Summary chart 
        
        # FIX: Sort the DataFrame by the ORIGINAL column name 'entry_date'
        # to ensure chronological order for the chart.
        df_chart = df_display.sort_values(by='entry_date', ascending=True) 

        st.subheader("📈 Balance Progression")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            # Use the original column name for the x-axis data
            x=df_chart['entry_date'], 
            y=df_chart['end_balance'], # Use the original column name for the y-axis data
            mode='lines+markers',
            name='End Balance',
            line=dict(color='#667eea', width=3)
        ))
        fig.update_layout(
            height=400,
            xaxis_title="Date",
            yaxis_title="Balance ($)",
            hovermode='x unified'
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No summary data yet. Start trading to see your progress!")

# ===================== TAB 3: ANALYTICS =====================
with tab3:
    st.header("📈 Performance Analytics")
    
    df_analytics = pd.read_sql("SELECT * FROM daily_summary ORDER BY entry_date ASC", conn)
    
    if not df_analytics.empty:
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Daily P&L chart
            st.subheader("Daily Trading Profit/Loss")
            fig_pnl = px.bar(
                df_analytics, 
                x='entry_date', 
                y='actual_profit',
                color='actual_profit',
                color_continuous_scale=['red', 'yellow', 'green'],
                labels={'actual_profit': 'P&L ($)', 'entry_date': 'Date'}
            )
            fig_pnl.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig_pnl, use_container_width=True)
        
        with col2:
            # Target vs Actual
            st.subheader("Target vs Actual Profit")
            fig_target = go.Figure()
            fig_target.add_trace(go.Scatter(
                x=df_analytics['entry_date'],
                y=df_analytics['profit_needed'],
                name='Target P&L',
                line=dict(color='orange', dash='dash')
            ))
            fig_target.add_trace(go.Scatter(
                x=df_analytics['entry_date'],
                y=df_analytics['actual_profit'],
                name='Actual P&L',
                line=dict(color='green')
            ))
            fig_target.update_layout(height=350)
            st.plotly_chart(fig_target, use_container_width=True)
        
        st.markdown("---")
        
        # Trade statistics
        st.subheader("📊 Trade Statistics")
        trades_df = pd.read_sql("SELECT * FROM trades", conn)
        
        if not trades_df.empty:
            col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
            
            winning_trades = len(trades_df[trades_df['pnl'] > 0])
            total_trades_all = len(trades_df)
            win_rate = (winning_trades / total_trades_all * 100) if total_trades_all > 0 else 0
            
            avg_win = trades_df[trades_df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
            avg_loss = trades_df[trades_df['pnl'] < 0]['pnl'].mean() if (total_trades_all - winning_trades) > 0 else 0
            
            col_stat1.metric("Total Trades", total_trades_all)
            col_stat2.metric("Win Rate", f"{win_rate:.1f}%")
            col_stat3.metric("Avg Win", f"${avg_win:.2f}")
            col_stat4.metric("Avg Loss", f"${avg_loss:.2f}")
            
            # Ticker performance
            st.subheader("🎯 Performance by Ticker")
            ticker_stats = trades_df.groupby('ticker').agg({
                'pnl': ['sum', 'count', 'mean']
            }).round(2)
            ticker_stats.columns = ['Total P&L', 'Trades', 'Avg P&L']
            ticker_stats = ticker_stats.sort_values('Total P&L', ascending=False)
            st.dataframe(ticker_stats, use_container_width=True)
        else:
             st.info("No trades to generate detailed statistics.")
    else:
        st.info("Start trading to see analytics!")

# Footer
st.markdown("---")
st.caption("💡 Trading Tracker · Track your daily trading performance")