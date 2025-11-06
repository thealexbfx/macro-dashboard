import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ---------------------- Helper functions ----------------------

def download_prices(tickers, start, end):
    data = yf.download(tickers, start=start, end=end, progress=False, threads=True)['Close']
    if isinstance(data, pd.Series):
        data = data.to_frame()
    data.columns = [c.replace('.', '-') for c in data.columns]
    return data


def resample_monthly(price_df):
    return price_df.resample('M').last()


def compute_returns(price_df):
    return price_df.pct_change().fillna(0)


def annualize_return(cum_return, periods_per_year):
    return (1 + cum_return) ** (periods_per_year) - 1


def cagr(returns, periods_per_year=252):
    cumulative = (1 + returns).prod() - 1
    days = len(returns)
    return (1 + cumulative) ** (periods_per_year / days) - 1


def sharpe_ratio(returns, rf=0.0, periods_per_year=252):
    excess = returns - rf / periods_per_year
    if returns.std() == 0:
        return 0.0
    return np.sqrt(periods_per_year) * excess.mean() / (returns.std())


def max_drawdown(cum_returns):
    cum = (1 + cum_returns).cumprod()
    peak = cum.cummax()
    dd = (cum - peak) / peak
    return dd.min()


def portfolio_return_from_weights(returns, weights):
    # returns: DataFrame (dates x assets), weights: dict asset->weight (sums to 1)
    w = pd.Series(weights)
    matched = returns[w.index]
    return (matched * w).sum(axis=1)

# ---------------------- Model Definitions ----------------------

def classify_regime(gdp, cpi, unemployment, y10):
    """Simple rule-based regime classifier. Returns one of: Expansion, Overheating, Recession, Stagflation"""
    # normalize indicators via simple thresholds
    if gdp > 2.0 and cpi < 2.5:
        return 'Expansion'
    if gdp > 2.0 and cpi >= 2.5:
        return 'Overheating'
    if gdp <= 1.0 and cpi >= 3.0:
        return 'Stagflation'
    if gdp <= 1.0 and cpi < 3.0:
        return 'Recession'
    # fallback to "Slowdown" mapped to Recession-ish allocation
    return 'Slowdown'


def model_a_allocation_for_regime(regime):
    # Using the allocation scheme you provided + cautious tilt
    if regime == 'Expansion':
        return {'SPY': 0.50, 'VXUS': 0.15, 'TLT': 0.20, 'GLD': 0.05, 'BIL': 0.10}
    if regime == 'Overheating':
        return {'SPY': 0.40, 'VXUS': 0.10, 'TLT': 0.20, 'GLD': 0.15, 'BIL': 0.15}
    if regime == 'Recession':
        return {'SPY': 0.20, 'VXUS': 0.10, 'TLT': 0.50, 'GLD': 0.10, 'BIL': 0.10}
    if regime == 'Stagflation':
        return {'SPY': 0.10, 'VXUS': 0.05, 'TLT': 0.30, 'GLD': 0.40, 'BIL': 0.15}
    # Slowdown / Default (cautious)
    return {'SPY': 0.30, 'VXUS': 0.10, 'TLT': 0.35, 'GLD': 0.15, 'BIL': 0.10}


def run_model_a(monthly_prices, start_date, end_date, regime_series=None, manual_regime=None):
    # monthly_prices: DataFrame with monthly close prices
    months = monthly_prices.index
    assets = monthly_prices.columns.tolist()

    portfolio_vals = pd.Series(index=months, dtype=float)
    weights_history = pd.DataFrame(index=months, columns=assets).fillna(0)

    cash_asset = 'BIL' if 'BIL' in assets else None

    # simple simulation: start with 1.0 capital
    capital = 1.0
    portfolio_vals.iloc[0] = capital

    for i, date in enumerate(months):
        # choose regime
        if manual_regime is not None:
            regime = manual_regime
        else:
            regime = regime_series.loc[date] if (regime_series is not None and date in regime_series.index) else 'Slowdown'
        alloc = model_a_allocation_for_regime(regime)
        # ensure all assets are present
        weights = {a: alloc.get(a, 0.0) for a in assets}
        weights_history.loc[date] = pd.Series(weights)

        if i == 0:
            # set starting capital
            prev_prices = monthly_prices.iloc[0]
        else:
            prev_prices = monthly_prices.iloc[i-1]

        # compute returns between previous and current month
        if i == 0:
            monthly_ret = pd.Series(0.0, index=assets)
        else:
            monthly_ret = (monthly_prices.iloc[i] / prev_prices) - 1
        # portfolio return
        port_ret = sum([monthly_ret[a] * weights[a] for a in assets])
        capital = capital * (1 + port_ret)
        portfolio_vals.iloc[i] = capital

    return portfolio_vals, weights_history


# Momentum model helper

def compute_moving_averages(price, short=50, long=200):
    ma_short = price.rolling(window=short, min_periods=1).mean()
    ma_long = price.rolling(window=long, min_periods=1).mean()
    return ma_short, ma_long


def run_model_b(daily_prices, weekly_review_day='MON', max_positions=3, min_cash=0.2):
    # daily_prices: DataFrame
    prices = daily_prices.copy()
    returns = prices.pct_change().fillna(0)

    # generate weekly review dates (Mondays) within index
    mondays = prices.resample('W-MON').last().index

    # signal table and portfolio
    portfolio_value = pd.Series(index=mondays, dtype=float)
    position_history = {}
    trade_log = []

    capital = 1.0
    current_positions = {}

    for i, date in enumerate(mondays):
        # compute MAs on data up to date
        snapshot = prices.loc[:date]
        signals = {}
        for col in prices.columns:
            ma50, ma200 = compute_moving_averages(snapshot[col])
            # simple rule: buy if latest ma50 > ma200
            if ma50.iloc[-1] > ma200.iloc[-1]:
                signals[col] = 'BUY'
            else:
                signals[col] = 'SELL'

        # pick BUY signals
        buy_list = [s for s, sig in signals.items() if sig == 'BUY']
        buy_list = [b for b in buy_list if b != 'USO']  # example: exclude oil if wanted
        # pick top up to max_positions by recent momentum (90d returns)
        momentums = {}
        for b in buy_list:
            window = snapshot[b].iloc[-90:]
            if len(window) < 2:
                momentums[b] = 0
            else:
                momentums[b] = window.pct_change().dropna().add(1).prod() - 1
        # sort
        sorted_buy = sorted(momentums.items(), key=lambda x: x[1], reverse=True)
        picks = [p[0] for p in sorted_buy][:max_positions]

        # allocate equally among picks, respect min_cash
        allocable = 1 - min_cash
        if len(picks) > 0:
            w = allocable / len(picks)
        else:
            w = 0
        weights = {col: 0.0 for col in prices.columns}
        for p in picks:
            weights[p] = w
        weights['CASH'] = 1 - sum(weights.values())

        # compute portfolio return from previous mondays value to this
        if i == 0:
            portfolio_value.iloc[i] = capital
        else:
            prev_date = mondays[i - 1]

            # find the nearest available trading dates
            if date not in prices.index:
                # find the most recent trading day before this Monday
                valid_idx = prices.index[prices.index <= date]
                if len(valid_idx) == 0:
                    continue
                date = valid_idx[-1]
            if prev_date not in prices.index:
                valid_prev = prices.index[prices.index <= prev_date]
                if len(valid_prev) == 0:
                    continue
                prev_date = valid_prev[-1]

            # compute period returns safely
            period_rets = (prices.loc[date] / prices.loc[prev_date]) - 1
            port_ret = sum(
                [period_rets.get(a, 0.0) * w for a, w in weights.items() if a != 'CASH']
            )
            capital *= 1 + port_ret
            portfolio_value.iloc[i] = capital


        position_history[date] = weights
        # simple trade log
        for p in picks:
            trade_log.append({'date': date, 'ticker': p, 'action': 'BUY', 'weight': weights[p]})

    trade_df = pd.DataFrame(trade_log)
    weights_df = pd.DataFrame(position_history).T.fillna(0)
    return portfolio_value, weights_df, trade_df

# ---------------------- Streamlit App ----------------------

st.set_page_config(layout='wide', page_title='Macro + Momentum Demo')

st.title('Macro Allocation (Model A)  + Momentum (Model B) — Demo Framework')

# Sidebar: user inputs
st.sidebar.header('Settings')
use_yfinance = st.sidebar.checkbox('Use yfinance for prices (recommended)', value=True)

end_date = st.sidebar.date_input('End Date', value=datetime.today().date())
start_date = st.sidebar.date_input('Start Date', value=(datetime.today() - timedelta(days=365*3)).date())

st.sidebar.markdown('---')
st.sidebar.subheader('Macro Inputs (auto or manual)')
# default macro values derived from your pasted data — user can edit
default_macro = {
    'US_GDP': 3.8,
    'US_CPI': 3.0,
    'US_Unemp': 4.3,
    'US_10y': 4.13,
}

gdp = st.sidebar.number_input('US GDP % (annual)', value=default_macro['US_GDP'], format="%.2f")
cpi = st.sidebar.number_input('US CPI YoY %', value=default_macro['US_CPI'], format="%.2f")
unemp = st.sidebar.number_input('US Unemployment %', value=default_macro['US_Unemp'], format="%.2f")
y10 = st.sidebar.number_input('US 10y Yield %', value=default_macro['US_10y'], format="%.2f")

auto_regime = classify_regime(gdp, cpi, unemp, y10)
manual_override = st.sidebar.selectbox('Force regime (leave as Auto to use classifier)', options=['Auto', 'Expansion', 'Overheating', 'Recession', 'Stagflation', 'Slowdown'], index=0)
regime_to_use = None if manual_override == 'Auto' else manual_override

st.sidebar.markdown('---')

# Tickers used
st.sidebar.subheader('Tickers / Instruments')
model_a_tickers = st.sidebar.text_area('Model A tickers (comma separated)', value='SPY,VXUS,TLT,GLD,BIL')
model_b_tickers = st.sidebar.text_area('Model B tickers (comma separated)', value='SPY,QQQ,GLD,TLT,USO')

# Parse tickers
ma_tick = [t.strip().upper() for t in model_a_tickers.split(',') if t.strip()]
mb_tick = [t.strip().upper() for t in model_b_tickers.split(',') if t.strip()]
all_tickers = sorted(list(set(ma_tick + mb_tick)))

# Download data
with st.spinner('Downloading price data...'):
    price_data = download_prices(all_tickers, start_date, end_date)

st.write('### Price Data (sample)')
st.dataframe(price_data.tail())

# Prepare monthly and daily frames
monthly_prices = resample_monthly(price_data)
daily_prices = price_data.copy()

# Model A run
st.write('## Model A — Macro Allocation (Monthly Rebalance)')
col1, col2 = st.columns([1, 1])
with col1:
    st.write('**Regime classifier result (from inputs):**', auto_regime)
    st.write('**Regime used:**', regime_to_use if regime_to_use else auto_regime)

with st.spinner('Running Model A backtest...'):
    # simple regime series: use same regime for all months
    regime_series = pd.Series(index=monthly_prices.index, data=[auto_regime]*len(monthly_prices))
    if regime_to_use:
        regime_series = pd.Series(index=monthly_prices.index, data=[regime_to_use]*len(monthly_prices))

    port_a_vals, weights_hist = run_model_a(monthly_prices[ma_tick], start_date, end_date, regime_series=regime_series, manual_regime=regime_to_use)

# Metrics Model A
rets_a = port_a_vals.pct_change().fillna(0)
cagr_a = cagr(rets_a, periods_per_year=12)
sharpe_a = sharpe_ratio(rets_a, rf=0.0, periods_per_year=12)
maxdd_a = max_drawdown(rets_a)

col1, col2, col3 = st.columns(3)
col1.metric('Model A — CAGR (annual)', f"{cagr_a:.2%}")
col2.metric('Sharpe (ann)', f"{sharpe_a:.2f}")
col3.metric('Max Drawdown', f"{maxdd_a:.2%}")

# Plot Model A equity curve
fig_a = px.line(x=port_a_vals.index, y=port_a_vals.values, labels={'x': 'Date', 'y': 'Portfolio Value'}, title='Model A — Portfolio Value (start=1)')
st.plotly_chart(fig_a, use_container_width=True)

# Allocation stacked bar
weights_plot = weights_hist.copy()
weights_plot.index = weights_plot.index.strftime('%Y-%m')
weights_plot = weights_plot[ma_tick]
fig_stack = go.Figure()
for col in weights_plot.columns:
    fig_stack.add_trace(go.Bar(name=col, x=weights_plot.index, y=weights_plot[col]))
fig_stack.update_layout(barmode='stack', title='Monthly Allocation History')
st.plotly_chart(fig_stack, use_container_width=True)

# Model B run
st.write('## Model B — Momentum / Trend (Weekly Rebalance)')
with st.spinner('Running Model B backtest...'):
    port_b_vals, weights_b, trades_b = run_model_b(daily_prices[mb_tick])

# Metrics Model B
rets_b = port_b_vals.pct_change().fillna(0)
cagr_b = cagr(rets_b, periods_per_year=52)
sharpe_b = sharpe_ratio(rets_b, rf=0.0, periods_per_year=52)
maxdd_b = max_drawdown(rets_b)

col1, col2, col3 = st.columns(3)
col1.metric('Model B — CAGR (annual)', f"{cagr_b:.2%}")
col2.metric('Sharpe (ann)', f"{sharpe_b:.2f}")
col3.metric('Max Drawdown', f"{maxdd_b:.2%}")

# Plot Model B equity curve
fig_b = px.line(x=port_b_vals.index, y=port_b_vals.values, labels={'x': 'Date', 'y': 'Portfolio Value'}, title='Model B — Portfolio Value (start=1)')
st.plotly_chart(fig_b, use_container_width=True)

st.write('### Model B — Weekly Signal Table (latest 20)')
if not trades_b.empty:
    st.dataframe(trades_b.sort_values('date', ascending=False).head(20))
else:
    st.write('No trades generated.')

# Combined summary
st.write('## Combined Summary')
combined = pd.DataFrame({
    'Model': ['Model A', 'Model B'],
    'CAGR': [cagr_a, cagr_b],
    'Sharpe': [sharpe_a, sharpe_b],
    'MaxDD': [maxdd_a, maxdd_b]
})
st.dataframe(
    combined.style.format({'CAGR': '{:.2%}', 'Sharpe': '{:.2f}', 'MaxDD': '{:.2%}'}),
    use_container_width=True
)


st.markdown('---')
st.write('**How to use / next steps:**')
st.write('- Edit tickers and macro inputs in the sidebar.\n- Use the "Force regime" selector to test specific regime allocations.\n- Replace the simple classifier with your own macro pipeline if you want more sophisticated regime logic.\n- Export results by copying tables or serializing to CSV (you can add buttons to export).')

st.write('**Notes / Limitations:**')
st.write('- This demo uses rule-of-thumb regime classification and simple monthly/weekly rebalances.\n- Slippage, transaction costs, taxes, and exact execution prices are not modeled.\n- For production-quality backtests, consider vectorized libraries or dedicated backtest engines.')

st.write('Done — tweak in the sidebar and re-run. Happy to expand any part (e.g. add transaction costs, trade-level P&L, or interactive charts).')
