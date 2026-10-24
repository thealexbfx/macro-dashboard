import streamlit as st


NAV_ITEMS = {
    "Dashboard": [
        ("HowItWorks", "How MacroLens Works"),
        ("MacroEngineGlobal", "Global Macro Monitor"),
    ],

    "Investigate markets": [
        ("ActiveIdeas", "Active Ideas"),
        ("ResearchWorkspace", "Research Workspace"),
       ## ("DecisionHistory", "Decision History"),
    ],

    "Regional model views": [
        ("MacroEngineUSA", "United States"),
        ("MacroEngineEuro", "Euro Area"),
        ("MacroEngineUK", "United Kingdom"),
        ("MacroEngineJapan", "Japan"),
    ],

    "Historical evidence": [
        ("HistoricalRegimeExplorer", "Regime Explorer"),

    ],

    "Coming soon": [
        ("RegimeMonitor", "Regime Monitor"),
        ("CentralBankWatch", "Central Bank Watch"),
        ("Calendar", "Calendar"),
        ("ResearchNotes", "Research Notes"),
        ("GlobalMacroView", "Global Macro Outlook"),
    ],

    "Data explorer": [
        ("UnitedStates", "United States"),
        ("EuroArea", "Euro Area"),
        ("UnitedKingdom", "United Kingdom"),
        ("Japan", "Japan"),
        ("RatesBonds", "Rates & Bonds"),
        ("Equities", "Equities"),
        ("Commodities", "Commodities"),
        ("FX", "FX"),
        ("Crypto", "Crypto"),
    ],
}


def _nav_link(page_key: str, label: str, active_page: str) -> str:
    active_class = " active" if page_key == active_page else ""
    current = ' aria-current="page"' if page_key == active_page else ""
    return f'<a class="ml-nav-link{active_class}" {current} href="?page={page_key}" target="_self">{label}</a>'


def render_sidebar(active_page: str = "HowItWorks"):
    nav_html = ""

    for section in ["Dashboard", "Investigate markets", "Regional model views", "Historical evidence", "Data explorer", "Coming soon"]:
        items = NAV_ITEMS[section]
        nav_html += f'<div class="ml-nav-section">{section}</div>'
        for page_key, label in items:
            nav_html += _nav_link(page_key, label, active_page)

    st.html(
        f"""
        <input type="checkbox" id="ml-menu-toggle" class="ml-menu-toggle" aria-label="Open navigation menu">

        <label for="ml-menu-toggle" class="ml-mobile-menu-btn">
            ☰
        </label>

        <label for="ml-menu-toggle" class="ml-mobile-backdrop"></label>

        <nav class="ml-sidebar" aria-label="Main navigation">
            <label for="ml-menu-toggle" class="ml-mobile-close">×</label>

            <div class="ml-logo">Macro<span>Lens</span></div>
            {nav_html}
        </nav>
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
