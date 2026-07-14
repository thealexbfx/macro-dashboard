from app_pages.economy_page import render_economy_page
from economy_data.usa import (
    USA_CATEGORY_MAP,
    USA_ECONOMY_MAP,
    USA_PAGE_DESCRIPTION,
)


def render_usa_page():
    render_economy_page(
        economy_map=USA_ECONOMY_MAP,
        category_map=USA_CATEGORY_MAP,
        page_key="usa",
        country_name="United States",
        page_description=USA_PAGE_DESCRIPTION,
    )