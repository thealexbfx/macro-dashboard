from pathlib import Path

import streamlit as st


NAV_ITEMS = {
    "Dashboard": [
        ("Home", "Global Macro Monitor"),
    ],
    "Decisions": [
        ("ActiveIdeas", "Active Ideas"),
        ("ResearchWorkspace", "Research Workspace"),
    ],
    "Macro Engine": [
        ("MacroEngineUSA", "United States"),
        ("MacroEngineEuro", "Euro Area"),
        ("MacroEngineUK", "United Kingdom"),
        ("MacroEngineJapan", "Japan"),
    ],
    "Historical Research": [
        ("HistoricalRegimeExplorer", "Regime Explorer"),
        ("RegimeMonitor", "Regime Monitor"),
    ],
    "Research Tools": [
        ("CentralBankWatch", "Central Bank Watch"),
        ("Calendar", "Calendar"),
        ("ResearchNotes", "Research Notes"),
        ("GlobalMacroView", "Global Macro Outlook"),
    ],
    "Economic + Market Data": [
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


def _load_critical_sidebar_css() -> str:
    project_root = Path(__file__).resolve().parents[1]
    styles_dir = project_root / "styles"

    critical_files = [
        styles_dir / "base.css",
        styles_dir / "sidebar.css",
    ]

    css_parts = []

    for css_path in critical_files:
        if css_path.exists():
            css_parts.append(css_path.read_text(encoding="utf-8"))

    return "\n".join(css_parts)


def _nav_link(page_key: str, label: str, active_page: str) -> str:
    active_class = " active" if page_key == active_page else ""

    return (
        f'<a class="ml-nav-link{active_class}" '
        f'href="?page={page_key}" target="_self">'
        f"{label}</a>"
    )


def render_sidebar(active_page: str = "Home") -> None:
    nav_html = ""

    for section, items in NAV_ITEMS.items():
        nav_html += f'<div class="ml-nav-section">{section}</div>'

        for page_key, label in items:
            nav_html += _nav_link(page_key, label, active_page)

    critical_css = _load_critical_sidebar_css()

    st.html(
        f"""
        <style>
            {critical_css}

            /*
            Emergency fallback: the navigation must never appear as
            ordinary blue browser links, even before other styles load.
            */
            .ml-sidebar {{
                position: fixed;
                top: 0;
                left: 0;
                width: 270px;
                height: 100vh;
                overflow-y: auto;
                padding: 26px 18px;
                background: #071729;
            }}

            .ml-nav-link {{
                display: block;
                color: #E2E8F0 !important;
                text-decoration: none !important;
            }}
        </style>

        <input
            type="checkbox"
            id="ml-menu-toggle"
            class="ml-menu-toggle"
        >

        <label for="ml-menu-toggle" class="ml-mobile-menu-btn">
            ☰
        </label>

        <label
            for="ml-menu-toggle"
            class="ml-mobile-backdrop"
        ></label>

        <aside class="ml-sidebar">
            <label for="ml-menu-toggle" class="ml-mobile-close">
                ×
            </label>

            <div class="ml-logo">
                Macro<span>Lens</span>
            </div>

            {nav_html}
        </aside>
        """
    )


def render_top_strip(page_title: str) -> None:
    st.markdown(
        f"""
        <div class="top-strip">
            <div>{page_title}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )