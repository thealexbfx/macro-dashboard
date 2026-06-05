# ============================================
# apple_forecast_no_arima.py
# Forecast Apple (AAPL) stock price using Prophet and XGBoost
# ============================================

import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import timedelta

# --- 1. Load Data ---
print("Downloading Apple (AAPL) historical data...")
data = yf.download("AAPL", start="2015-01-01", end="2025-01-01")
data = data[['Close']].reset_index()
data.columns = ['ds', 'y']

# --- Train/Test Split ---
train = data.iloc[:-90]
test = data.iloc[-90:]

# ============================================
# 2. Prophet Model
# ============================================
from prophet import Prophet

print("Fitting Prophet model...")
prophet_model = Prophet(daily_seasonality=True)
prophet_model.fit(train)

future = prophet_model.make_future_dataframe(periods=90)
prophet_forecast = prophet_model.predict(future)

prophet_pred = prophet_forecast[['ds', 'yhat']].set_index('ds').iloc[-90:]
prophet_pred = prophet_pred['yhat']

# ============================================
# 3. XGBoost Model
# ============================================
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

print("Training XGBoost model...")
df = data.copy()
df['lag1'] = df['y'].shift(1)
df['lag2'] = df['y'].shift(2)
df['rolling_mean_5'] = df['y'].rolling(5).mean()
df = df.dropna()

X = df[['lag1', 'lag2', 'rolling_mean_5']]
y = df['y']

X_train, X_test = X.iloc[:-90], X.iloc[-90:]
y_train, y_test = y.iloc[:-90], y.iloc[-90:]

xgb_model = XGBRegressor(n_estimators=500, learning_rate=0.05, max_depth=4)
xgb_model.fit(X_train, y_train)
xgb_pred = pd.Series(xgb_model.predict(X_test), index=data['ds'].iloc[-90:])

# ============================================
# 4. Evaluation
# ============================================
def evaluate(y_true, y_pred, model_name):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    print(f"{model_name} — MAE: {mae:.2f}, RMSE: {rmse:.2f}")
    return mae, rmse

print("\n--- Forecast Evaluation (Last 90 Days) ---")
evaluate(test['y'], prophet_pred, "Prophet")
evaluate(test['y'], xgb_pred, "XGBoost")

# ============================================
# 5. Visualization (Plotly)
# ============================================
print("Generating forecast comparison chart...")

fig = go.Figure()

# Actual
fig.add_trace(go.Scatter(
    x=data['ds'], y=data['y'], name="Actual", line=dict(color='black', width=2)
))

# Forecasts
fig.add_trace(go.Scatter(
    x=prophet_pred.index, y=prophet_pred, name="Prophet Forecast", line=dict(dash='dot')
))
fig.add_trace(go.Scatter(
    x=xgb_pred.index, y=xgb_pred, name="XGBoost Forecast", line=dict(dash='dashdot')
))

fig.update_layout(
    title="AAPL Stock Price Forecast — Prophet vs XGBoost",
    xaxis_title="Date",
    yaxis_title="Price (USD)",
    template="plotly_white",
    legend=dict(x=0, y=1, bgcolor="rgba(0,0,0,0)")
)

fig.show()

# ============================================
# End of Script
# ============================================
