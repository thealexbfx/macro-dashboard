from indicators.usa import (
    get_usa_interest_rate_data,
    get_usa_policy_rate_6m_change_data,
    get_usa_real_policy_rate_data,
    get_usa_2yr_policy_gap_data,
)


def inspect_series(name, data):
    print()
    print("=" * 80)
    print(name)
    print("=" * 80)

    print(data.tail(10).to_string(index=False))
    print()
    print(f"Rows: {len(data)}")
    print(f"First date: {data['date'].min()}")
    print(f"Latest date: {data['date'].max()}")
    print(f"Missing values: {data['value'].isna().sum()}")

    date_differences = (
        data["date"]
        .sort_values()
        .diff()
        .dropna()
        .value_counts()
        .head(5)
    )

    print("Most common date gaps:")
    print(date_differences.to_string())


inspect_series(
    "Federal Reserve Target Upper Bound",
    get_usa_interest_rate_data(),
)

inspect_series(
    "Policy Rate — Six-Month Change",
    get_usa_policy_rate_6m_change_data(),
)

inspect_series(
    "Real Policy Rate",
    get_usa_real_policy_rate_data(),
)

inspect_series(
    "Two-Year Policy Gap",
    get_usa_2yr_policy_gap_data(),
)