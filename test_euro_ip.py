# test_euro_ip_debug.py

from data.eurostat import get_eurostat_series

# 1) Pull Eurostat index level
df_index = get_eurostat_series(
    "sts_inpr_m",
    {
        "geo": "EA20",
        "indic_bt": "PRD",
        "nace_r2": "B-D",
        "s_adj": "SCA",
        "unit": "I15",
        "freq": "M",
    }
)

print("\n=== INDEX LEVEL SERIES ===")
print(df_index.tail(10))

# 2) Manually calculate MoM from index
df_calc = df_index.copy()
df_calc["mom_calc"] = df_calc["value"].pct_change() * 100

print("\n=== CALCULATED MOM FROM INDEX ===")
print(df_calc.tail(10))

# 3) Pull Eurostat MoM series directly
df_mom = get_eurostat_series(
    "sts_inpr_m",
    {
        "geo": "EA20",
        "indic_bt": "PRD",
        "nace_r2": "B-D",
        "s_adj": "SCA",
        "unit": "PCH_PRE",
        "freq": "M",
    }
)

print("\n=== DIRECT EUROSTAT MOM SERIES ===")
print(df_mom.tail(10))

# 4) Compare latest
print("\n=== LATEST COMPARISON ===")
print("Index latest:", df_index.iloc[-1]["date"], df_index.iloc[-1]["value"])
print("Calculated MoM latest:", df_calc.iloc[-1]["date"], round(df_calc.iloc[-1]["mom_calc"], 3))
print("Direct MoM latest:", df_mom.iloc[-1]["date"], df_mom.iloc[-1]["value"])