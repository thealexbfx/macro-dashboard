from app_pages.market_page import render_market_page
from market_data.equities import (
    EQUITIES_CATEGORY_MAP,
    EQUITIES_COMPARE_MAP,
    EQUITIES_MAP,
)


def render_equities_page():
    render_market_page(
        market_map=EQUITIES_MAP,
        category_map=EQUITIES_CATEGORY_MAP,
        compare_map=EQUITIES_COMPARE_MAP,
        page_key="equities",
        asset_label="Equity",
    )