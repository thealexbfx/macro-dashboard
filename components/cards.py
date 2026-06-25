import streamlit as st


PILLAR_COLORS = {
    "Growth": "#16a34a",
    "Inflation": "#dc2626",
    "Labor": "#2563eb",
    "Policy": "#7e22ce",
    "Liquidity": "#f59e0b",
}

def render_html(html: str):
    st.markdown(html, unsafe_allow_html=True)


def render_pillar_card(name, status, score, description):
    color = PILLAR_COLORS.get(name, "#2563eb")
    width = max(5, min(100, int(score * 100)))

    render_html(f"""
    <div class="ml-card pillar-card">
        <div class="pillar-name" style="color:{color};">{name}</div>
        <div class="pillar-status">{status}</div>
        <div class="pillar-score">{score:.2f}</div>
        <div class="small-label">Model score</div>
        <div class="mini-line">
            <div class="mini-line-fill" style="width:{width}%; background:{color};"></div>
        </div>
        <div class="insight-box">{description}</div>
    </div>
    """)


def render_market_tile(label, value, change=None):
    change_html = ""

    if change is not None:
        color = "#16a34a" if change > 0 else "#dc2626" if change < 0 else "#64748b"
        change_html = (
            f'<div style="font-size:13px; font-weight:900; color:{color}; margin-top:5px;">'
            f'{change:+.2f}%'
            f'</div>'
        )

    html = f"""
    <div class="ml-card" style="min-height:94px;">
        <div class="small-label">{label}</div>
        <div style="font-size:25px; font-weight:900; letter-spacing:-0.04em; margin-top:6px;">
            {value}
        </div>
        {change_html}
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)


def render_country_card(country, regime, growth, inflation, policy):
    render_html(f"""
    <div class="ml-card country-card">
        <h3>{country}</h3>
        <div class="regime-pill">{regime}</div>
        <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px;">
            <div>
                <div class="small-label">Growth</div>
                <b>{growth}</b>
            </div>
            <div>
                <div class="small-label">Inflation</div>
                <b>{inflation}</b>
            </div>
            <div>
                <div class="small-label">Policy</div>
                <b>{policy}</b>
            </div>
        </div>
    </div>
    """)


def render_framework_step(number, title, text):
    render_html(f"""
    <div class="framework-step">
        <b>{number}. {title}</b>
        <p>{text}</p>
    </div>
    """)