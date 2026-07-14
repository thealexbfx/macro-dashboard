from app_pages.market_page import render_market_page
from market_data.rates_bonds import (
    RATES_BONDS_CATEGORY_MAP,
    RATES_BONDS_COMPARE_MAP,
    RATES_BONDS_MAP,
)


def render_rates_bonds_page():
    render_market_page(
        market_map=RATES_BONDS_MAP,
        category_map=RATES_BONDS_CATEGORY_MAP,
        compare_map=RATES_BONDS_COMPARE_MAP,
        page_key="rates_bonds",
        asset_label="Bond Yield",
    )