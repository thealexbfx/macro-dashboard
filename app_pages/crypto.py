from app_pages.market_page import render_market_page
from market_data.crypto import (
    CRYPTO_CATEGORY_MAP,
    CRYPTO_COMPARE_MAP,
    CRYPTO_MAP,
)


def render_crypto_page():
    render_market_page(
        market_map=CRYPTO_MAP,
        category_map=CRYPTO_CATEGORY_MAP,
        compare_map=CRYPTO_COMPARE_MAP,
        page_key="crypto",
        asset_label="Cryptocurrency",
    )