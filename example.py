import pandas as pd
import numpy as np
from scipy.stats import linregress

print("🔍 Checking consistency for: AAPL")

# Simulate some fake price data
dates = pd.date_range("2010-01-01", periods=4000, freq="D")
values = np.linspace(100, 300, len(dates)) + np.random.normal(0, 10, len(dates))
df_chart = pd.DataFrame({"date": dates, "value": values})

# ✅ Ensure date column is proper datetime type
df_chart["date"] = pd.to_datetime(df_chart["date"])

# ---- Filter logic ----
three_years_ago = df_chart["date"].max() - pd.DateOffset(years=3)
df_chart = df_chart[df_chart["date"] >= three_years_ago]

# ---- Summary Stats (3Y Window) ----
n_obs = len(df_chart)
mean_val = df_chart["value"].mean()
latest_val = df_chart["value"].iloc[-1]
min_val = df_chart["value"].min()
max_val = df_chart["value"].max()
start_val = df_chart["value"].iloc[0]
change_since_start = latest_val - start_val
position_pct = (latest_val - min_val) / (max_val - min_val) * 100 if max_val != min_val else 50
slope, _, _, _, _ = linregress(range(n_obs), df_chart["value"])
volatility = ((max_val - min_val) / mean_val * 100) if mean_val != 0 else np.nan

# ---- Print Everything ----
print(f"Date range used: {df_chart['date'].iloc[0].date()} → {df_chart['date'].iloc[-1].date()}")
print(f"Number of obs: {n_obs}")
print(f"Mean: {mean_val:.2f}")
print(f"Latest: {latest_val:.2f}")
print(f"Min: {min_val:.2f}")
print(f"Max: {max_val:.2f}")
print(f"Start: {start_val:.2f}")
print(f"Change since start: {change_since_start:+.2f}")
print(f"Position %: {position_pct:.2f}%")
print(f"Slope: {slope:.6f}")
print(f"Volatility: {volatility:.2f}%")

print("\nFormulas used:")
print("  change_since_start = latest_val - start_val")
print("  position_pct = (latest_val - min_val) / (max_val - min_val) * 100")
print("  volatility = (max_val - min_val) / mean_val * 100")
print("  slope = linregress(range(n_obs), df_filtered['value'])[0]")
