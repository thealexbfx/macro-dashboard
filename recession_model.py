import pandas as pd
from statsmodels.tsa.api import VAR
import matplotlib.pyplot as plt
import numpy as np
import warnings

warnings.filterwarnings("ignore")

# -----------------------------
# 1. Load data
# -----------------------------
file_path = r"C:\Users\algba\OneDrive\Documents\Trading-Investing\macro_dashboard\us_macro_2020_2025.csv"
df = pd.read_csv(file_path)
df['Date'] = pd.to_datetime(df['Date'])
df.set_index('Date', inplace=True)
df = df.apply(pd.to_numeric, errors='coerce')
df = df.ffill().bfill()

# -----------------------------
# 2. Key variables
# -----------------------------
KEY_VARS = ['CPI_YoY', 'Unemployment_Rate', 'GDP_Growth_QoQ', 'ISM_Manufacturing_PMI', 'ISM_Services_PMI']
data = df[[v for v in KEY_VARS if v in df.columns]]

# -----------------------------
# 3. Difference data for stationarity
# -----------------------------
data_diff = data.diff().dropna()

# -----------------------------
# 4. Safe max lag calculation
# -----------------------------
T, k = data_diff.shape
max_lag_feasible = 1
for p in range(1, 12):
    if T - p > k * (k * p + 1):
        max_lag_feasible = p
    else:
        break

print(f"Using safe maximum lag: {max_lag_feasible}")

# -----------------------------
# 5. Fit VAR model
# -----------------------------
model = VAR(data_diff)
results = model.fit(maxlags=max_lag_feasible, ic='aic')

# -----------------------------
# 6. Forecast 12 months
# -----------------------------
n_forecast = 12
lag_order = results.k_ar
forecast_input = data_diff.values[-lag_order:]
forecast_diff = results.forecast(y=forecast_input, steps=n_forecast)

# Convert back to levels
forecast_df = pd.DataFrame(forecast_diff, columns=data.columns)
forecast_df = data.iloc[-1] + forecast_df.cumsum()
forecast_df.index = pd.date_range(start=data.index[-1] + pd.offsets.MonthBegin(1),
                                  periods=n_forecast, freq='MS')

# -----------------------------
# 7. Compute Recession Probability
# -----------------------------
# Rule-based proxy
def compute_recession_prob(df):
    prob = []
    for i in range(len(df)):
        p = 0
        # GDP contraction
        if df['GDP_Growth_QoQ'].iloc[i] < 0:
            p += 0.4
        # Unemployment rising vs last month
        if i > 0 and df['Unemployment_Rate'].iloc[i] > df['Unemployment_Rate'].iloc[i-1]:
            p += 0.3
        # PMI below 50
        if df['ISM_Manufacturing_PMI'].iloc[i] < 50 or df['ISM_Services_PMI'].iloc[i] < 50:
            p += 0.3
        # Cap probability at 0–1
        prob.append(min(max(p, 0), 1))
    return prob

forecast_df['Recession_Prob'] = compute_recession_prob(forecast_df)

# -----------------------------
# 8. Output table
# -----------------------------
print("\n----------------------------------------")
print(f"12-Month VAR Forecast Table (from {data.index[-1].strftime('%b %Y')})")
print("----------------------------------------")
print(forecast_df.round(2))

# -----------------------------
# 9. Plot historical + forecast
# -----------------------------
plt.style.use('classic')  # use default style to avoid seaborn issues
for col in data.columns:
    fig, ax1 = plt.subplots(figsize=(10,4))
    ax1.plot(data.index, data[col], label='Historical', marker='o')
    ax1.plot(forecast_df.index, forecast_df[col], label='Forecast', marker='x')
    ax1.set_xlabel('Date')
    ax1.set_ylabel(col)
    ax1.legend(loc='upper left')

    # Recession probability secondary axis
    ax2 = ax1.twinx()
    ax2.plot(forecast_df.index, forecast_df['Recession_Prob'], label='Recession Prob', color='red', linestyle='--')
    ax2.set_ylabel('Recession Probability')
    ax2.set_ylim(0,1)
    ax2.legend(loc='upper right')

    plt.title(f"{col} Forecast + Recession Probability")
    plt.tight_layout()
    plt.show()

print("\n----------------------------------------")
print("Forecasting and plotting complete.")
print("----------------------------------------")
