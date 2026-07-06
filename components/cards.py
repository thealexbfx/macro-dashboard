import streamlit as st

PILLAR_COLORS = {
    "Growth": "#16A34A",
    "Inflation": "#DC2626",
    "Labor": "#2563EB",
    "Policy": "#7E22CE",
    "Liquidity": "#F59E0B",
}

PILLAR_ICONS = {
    "Growth": "↗",
    "Inflation": "◇",
    "Labor": "◎",
    "Policy": "▦",
    "Liquidity": "◊",
}


def render_html(html: str):
    st.markdown(html, unsafe_allow_html=True)


def render_pillar_card(name, status, score, description):
    color = PILLAR_COLORS.get(name, "#2563EB")
    icon = PILLAR_ICONS.get(name, "●")

    html = f"""
<div class="pillar-card">
  <div class="pillar-top">
    <div class="pillar-icon" style="background:{color};">{icon}</div>
    <div>
      <div class="pillar-name">{name}</div>
      <div class="pillar-status" style="color:{color};">{status}</div>
    </div>
  </div>

  <div class="pillar-score">{score:.2f}</div>
  <div class="small-label">Model Score</div>

  <svg class="pillar-spark-svg" viewBox="0 0 220 42" preserveAspectRatio="none">
    <polyline points="0,30 15,25 30,28 45,20 60,24 75,18 90,15 105,20 120,17 135,22 150,19 165,24 180,21 195,18 220,16"
      fill="none" stroke="{color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
    <linearGradient id="g-{name}" x1="0" x2="0" y1="0" y2="1">
      <stop offset="0%" stop-color="{color}" stop-opacity=".18"/>
      <stop offset="100%" stop-color="{color}" stop-opacity="0"/>
    </linearGradient>
    <polygon points="0,42 0,30 15,25 30,28 45,20 60,24 75,18 90,15 105,20 120,17 135,22 150,19 165,24 180,21 195,18 220,16 220,42"
      fill="url(#g-{name})"/>
  </svg>

  <div class="pillar-description">{description}</div>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)


def render_country_card(country, regime, growth, inflation, policy):
    html = f"""
<div class="country-card">
  <h3>{country}</h3>
  <div class="regime-pill">{regime}</div>
  <div class="country-grid">
    <div><span>Growth</span><b>{growth}</b></div>
    <div><span>Inflation</span><b>{inflation}</b></div>
    <div><span>Policy</span><b>{policy}</b></div>
  </div>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)