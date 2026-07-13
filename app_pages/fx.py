from app_pages.market_page import render_market_page
from market_data.fx import (
    FX_CATEGORY_MAP,
    FX_COMPARE_MAP,
    FX_MAP,
)


def render_fx_page():
    render_market_page(
        market_map=FX_MAP,
        category_map=FX_CATEGORY_MAP,
        compare_map=FX_COMPARE_MAP,
        page_key="fx",
        asset_label="Currency Pair",
    )