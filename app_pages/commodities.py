from app_pages.market_page import render_market_page
from market_data.commodities import (
    COMMODITY_CATEGORY_MAP,
    COMMODITY_COMPARE_MAP,
    COMMODITY_MAP,
)


def render_commodities_page():
    render_market_page(
        market_map=COMMODITY_MAP,
        category_map=COMMODITY_CATEGORY_MAP,
        compare_map=COMMODITY_COMPARE_MAP,
        page_key="commodity",
        asset_label="Commodity",
    )