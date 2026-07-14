from app_pages.economy_page import render_economy_page
from economy_data.japan import (
    JAPAN_CATEGORY_MAP,
    JAPAN_ECONOMY_MAP,
    JAPAN_PAGE_DESCRIPTION,
)


def render_japan_page():
    render_economy_page(
        economy_map=JAPAN_ECONOMY_MAP,
        category_map=JAPAN_CATEGORY_MAP,
        page_key="japan",
        country_name="Japan",
        page_description=JAPAN_PAGE_DESCRIPTION,
    )