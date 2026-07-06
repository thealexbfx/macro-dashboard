import streamlit as st
from pathlib import Path
from app_pages.home_market_data import get_home_market_snapshot
import datetime as dt


PILLARS = [
    ("Growth", "Improving", 0.68, "#16A34A", "Activity momentum is firming across key indicators."),
    ("Inflation", "Elevated", 0.74, "#DC2626", "Price pressure remains above target despite cooling from cycle highs."),
    ("Labor", "Stable", 0.56, "#2563EB", "Labor conditions remain resilient, but momentum is no longer accelerating."),
    ("Policy", "Restrictive", 0.82, "#7E22CE", "Central-bank policy remains tight relative to the growth backdrop."),
    ("Liquidity", "Neutral", 0.49, "#F59E0B", "Liquidity conditions are mixed, with no clear easing impulse yet."),
]

from pathlib import Path
import base64

BASE_DIR = Path(__file__).resolve().parent.parent

def load_image_base64(filename):
    image_path = BASE_DIR / "components" / filename

    with open(image_path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()

def sparkline(color):
    return f'''
<svg class="dash-spark" viewBox="0 0 220 42" preserveAspectRatio="none">
<polyline points="0,30 15,25 30,28 45,20 60,24 75,18 90,15 105,20 120,17 135,22 150,19 165,24 180,21 195,18 220,16"
fill="none" stroke="{color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
'''


def build_pillars():
    html = ""
    for name, status, score, color, desc in PILLARS:
        html += f'''
<div class="dash-pillar-card">
<div class="dash-pillar-top no-icon">
<div>
<div class="dash-pillar-name">{name}</div>
<div class="dash-pillar-status" style="color:{color};">{status}</div>
</div>
</div>
<div class="dash-pillar-score">{score:.2f}</div>
<div class="dash-small-label">Model Score</div>
{sparkline(color)}
<div class="dash-pillar-desc">{desc}</div>
</div>
'''
    return html

def build_svg_points(df, width=96, height=42, pad=5):
    if df is None or df.empty or "value" not in df.columns:
        return "0,22 12,22 24,22 36,22 48,22 60,22 72,22 84,22 96,22"

    values = df["value"].dropna().tail(20).tolist()

    if len(values) < 2:
        return "0,22 12,22 24,22 36,22 48,22 60,22 72,22 84,22 96,22"

    min_v = min(values)
    max_v = max(values)

    if max_v == min_v:
        return "0,22 12,22 24,22 36,22 48,22 60,22 72,22 84,22 96,22"

    points = []

    for i, v in enumerate(values):
        x = (i / (len(values) - 1)) * width
        y = height - pad - ((v - min_v) / (max_v - min_v)) * (height - 2 * pad)
        points.append(f"{x:.1f},{y:.1f}")

    return " ".join(points)

def build_market_rows():
    rows = ""

    for i, item in enumerate(get_home_market_snapshot()):
        change = item.get("change_pct")
        points = build_svg_points(item.get("sparkline_df"))

        if change is None:
            cls = "neutral"
            txt = ""
            color = "#94A3B8"
        elif change > 0:
            cls = "pos"
            txt = f"+{change:.2f}%"
            color = "#16A34A"
        elif change < 0:
            cls = "neg"
            txt = f"{change:.2f}%"
            color = "#DC2626"
        else:
            cls = "neutral"
            txt = f"{change:+.2f}%"
            color = "#64748B"

        area = f"0,42 {points} 96,42"

        rows += f'''
<div class="dash-market-card">
  <div class="market-name">{item["label"]}</div>
  <div class="market-value">{item["value"]}</div>
  <div class="market-change {cls}">{txt}</div>

  <svg class="market-area-spark" viewBox="0 0 96 42" preserveAspectRatio="none">
    <defs>
      <linearGradient id="market-grad-{i}" x1="0" x2="0" y1="0" y2="1">
        <stop offset="0%" stop-color="{color}" stop-opacity="0.16"/>
        <stop offset="100%" stop-color="{color}" stop-opacity="0"/>
      </linearGradient>
    </defs>
    <polygon points="{area}" fill="url(#market-grad-{i})"/>
    <polyline points="{points}" fill="none" stroke="{color}" stroke-width="1.8"
      stroke-linecap="round" stroke-linejoin="round"/>
  </svg>
</div>
'''
    return rows


def render_home_page():
    template_path = Path("templates/home.html")
    html = template_path.read_text(encoding="utf-8")

    today = dt.date.today().strftime("%B %d, %Y").replace(" 0", " ")
    world_map = load_image_base64("global_macro_map.png")

    html = html.replace("{{TODAY}}", today)
    html = html.replace("{{WORLD_MAP}}", world_map)
    html = html.replace("{{PILLARS}}", build_pillars())
    html = html.replace("{{MARKET_ROWS}}", build_market_rows())

    st.markdown(html, unsafe_allow_html=True)
    