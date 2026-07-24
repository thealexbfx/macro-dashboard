"""Inspect raw USA inflation data loaders."""

from indicators.usa import (
    get_usa_cpi_yoy_data,
    get_usa_core_cpi_yoy_data,
    get_usa_pce_yoy_data,
    get_usa_core_pce_yoy_data,
    get_usa_ppi_yoy_data,
    get_usa_core_ppi_yoy_data,
    get_usa_average_hourly_earnings_yoy_data,
    get_usa_eci_total_compensation_yoy_data,
    get_usa_eci_wages_salaries_yoy_data,
)


LOADERS = {
    "CPI YoY": get_usa_cpi_yoy_data,
    "Core CPI YoY": get_usa_core_cpi_yoy_data,
    "PCE YoY": get_usa_pce_yoy_data,
    "Core PCE YoY": get_usa_core_pce_yoy_data,
    "PPI YoY": get_usa_ppi_yoy_data,
    "Core PPI YoY": get_usa_core_ppi_yoy_data,
    "Average Hourly Earnings YoY": (
        get_usa_average_hourly_earnings_yoy_data
    ),
    "ECI Total Compensation YoY": (
        get_usa_eci_total_compensation_yoy_data
    ),
    "ECI Wages & Salaries YoY": (
        get_usa_eci_wages_salaries_yoy_data
    ),
}


for name, loader in LOADERS.items():
    print("\n" + "=" * 70)
    print(name)
    print("=" * 70)

    try:
        data = loader()

        print(f"Type:       {type(data).__name__}")
        print(f"Columns:    {list(data.columns)}")
        print(f"Rows:       {len(data)}")

        if not data.empty:
            print(f"First date: {data['date'].iloc[0]}")
            print(f"Last date:  {data['date'].iloc[-1]}")
            print("\nLatest five observations:")
            print(data.tail().to_string(index=False))
        else:
            print("The loader returned no observations.")

    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")