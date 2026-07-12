import streamlit as st


NAV_ITEMS = {
    "Dashboard": [("Home", "Overview")],
    "Research": [
        ("GlobalMacroView", "Global Macro Outlook"),
        ("RegimeMonitor", "Regime Monitor"),
        ("CentralBankWatch", "Central Bank Watch"),
        ("ResearchNotes", "Research Notes"),
        ("Calendar", "Calendar"),
    ],
    "Economies": [
        ("UnitedStates", "United States"),
        ("EuroArea", "Euro Area"),
        ("UnitedKingdom", "United Kingdom"),
        ("Japan", "Japan"),
    ],
    "Markets": [
        ("RatesBonds", "Rates & Bonds"),
        ("Equities", "Equities"),
        ("Commodities", "Commodities"),
        ("FX", "FX"),
        ("Crypto", "Crypto"),
    ],
}


def _nav_link(page_key: str, label: str, active_page: str) -> str:
    active_class = " active" if page_key == active_page else ""
    return f'<a class="ml-nav-link{active_class}" href="?page={page_key}" target="_self">{label}</a>'


def render_sidebar(active_page: str = "Home"):
    nav_html = ""

    for section, items in NAV_ITEMS.items():
        nav_html += f'<div class="ml-nav-section">{section}</div>'
        for page_key, label in items:
            nav_html += _nav_link(page_key, label, active_page)

    st.html(
        f"""
        <input type="checkbox" id="ml-menu-toggle" class="ml-menu-toggle">

        <label for="ml-menu-toggle" class="ml-mobile-menu-btn">
            ☰
        </label>

        <label for="ml-menu-toggle" class="ml-mobile-backdrop"></label>

        <aside class="ml-sidebar">
            <label for="ml-menu-toggle" class="ml-mobile-close">×</label>

            <div class="ml-logo">Macro<span>Lens</span></div>
            <div class="ml-sublogo">RESEARCH</div>
            {nav_html}
        </aside>
        """
    )


def render_top_strip(page_title: str):
    st.markdown(
        f"""
        <div class="top-strip">
            <div>{page_title}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )