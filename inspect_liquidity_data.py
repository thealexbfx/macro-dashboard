from indicators.usa import (
    get_usa_fed_total_assets_data,
    get_usa_net_fed_liquidity_13w_change_data,
    get_usa_overnight_reverse_repo_data,
    get_usa_reserve_balances_13w_change_data,
    get_usa_reserve_balances_data,
    get_usa_treasury_general_account_data,
)


def show_series(name, data):
    print()
    print("=" * 80)
    print(name)
    print("=" * 80)
    print(data.tail(10).to_string(index=False))
    print()
    print("Rows:", len(data))
    print("First date:", data["date"].min())
    print("Latest date:", data["date"].max())
    print("Missing values:", data["value"].isna().sum())


show_series(
    "Fed Total Assets",
    get_usa_fed_total_assets_data(),
)

show_series(
    "Treasury General Account",
    get_usa_treasury_general_account_data(),
)

show_series(
    "Overnight Reverse Repo",
    get_usa_overnight_reverse_repo_data(),
)

show_series(
    "Reserve Balances",
    get_usa_reserve_balances_data(),
)

show_series(
    "Net Fed Liquidity — 13-Week Change",
    get_usa_net_fed_liquidity_13w_change_data(),
)

show_series(
    "Reserve Balances — 13-Week Change",
    get_usa_reserve_balances_13w_change_data(),
)