import numpy as np
import matplotlib.pyplot as plt

# Parameters
years = 20
monthly_dca = 100
annual_cagr = 0.07
dip_purchases_per_year = 2.67
total_dip_purchases = int(dip_purchases_per_year * years)

# --- Monthly DCA ---
months = years * 12
dca_values = []
for m in range(months):
    # Each monthly contribution grows for remaining months
    fv = monthly_dca * ((1 + annual_cagr)**((months - m)/12))
    dca_values.append(fv)
dca_total = np.cumsum(dca_values)

# --- Buy-the-Dip ---
dip_values = []
# Assume dip purchases are evenly spaced through the 20 years
for i in range(total_dip_purchases):
    year_of_purchase = i * years / total_dip_purchases
    years_remaining = years - year_of_purchase
    fv = 100 * ((1 + annual_cagr) ** years_remaining)
    dip_values.append(fv)
dip_cumulative = np.cumsum(dip_values)

# --- Hybrid: DCA + Dip ---
hybrid_cumulative = np.cumsum(dca_values[:total_dip_purchases]) + dip_cumulative

# --- Plot ---
plt.figure(figsize=(10,6))
plt.plot(np.linspace(0, years, len(dca_total)), dca_total, label='Monthly DCA (£100/month)')
plt.plot(np.linspace(0, years, len(dip_cumulative)), dip_cumulative, label='Buy-the-Dip (£100 per trigger)')
plt.plot(np.linspace(0, years, len(dip_cumulative)), hybrid_cumulative, label='Hybrid DCA + Buy-the-Dip')
plt.xlabel('Years')
plt.ylabel('Portfolio Value (£)')
plt.title('20-Year Portfolio Simulation: DCA vs Buy-the-Dip')
plt.legend()
plt.grid(True)
plt.show()
