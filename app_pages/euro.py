from app_pages.economy_page import render_economy_page
from economy_data.euro import (
    EURO_CATEGORY_MAP,
    EURO_ECONOMY_MAP,
    EURO_PAGE_DESCRIPTION,
)


def render_euro_page():
    render_economy_page(
        economy_map=EURO_ECONOMY_MAP,
        category_map=EURO_CATEGORY_MAP,
        page_key="euro",
        country_name="Euro Area",
        page_description=EURO_PAGE_DESCRIPTION,
    )