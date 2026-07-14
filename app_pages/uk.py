from app_pages.economy_page import render_economy_page
from economy_data.uk import (
    UK_CATEGORY_MAP,
    UK_ECONOMY_MAP,
    UK_PAGE_DESCRIPTION,
)


def render_uk_page():
    render_economy_page(
        economy_map=UK_ECONOMY_MAP,
        category_map=UK_CATEGORY_MAP,
        page_key="uk",
        country_name="United Kingdom",
        page_description=UK_PAGE_DESCRIPTION,
    )