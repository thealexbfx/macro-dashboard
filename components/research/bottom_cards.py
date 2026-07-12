import streamlit as st


def render_bottom_cards(cards):
    html_parts = ['<div class="ml-info-card-grid">']

    for card in cards:
        html_parts.append('<div class="ml-info-card">')
        html_parts.append(f'<div class="ml-info-card-title">{card["title"]}</div>')
        html_parts.append('<div class="ml-info-card-body">')

        if card["type"] == "list":
            for item in card["items"]:
                html_parts.append(
                    f'<div class="ml-info-row">'
                    f'<span class="ml-info-dot">•</span>'
                    f'<span>{item}</span>'
                    f'</div>'
                )

        elif card["type"] == "changes":
            for period, value in card["items"].items():
                value_str = str(value)

                if value_str.startswith("+"):
                    value_class = "positive"
                elif value_str.startswith("-"):
                    value_class = "negative"
                else:
                    value_class = "neutral"

                html_parts.append(
                    f'<div class="ml-info-row-between">'
                    f'<span>{period}</span>'
                    f'<strong class="{value_class}">{value}</strong>'
                    f'</div>'
                )

        html_parts.append("</div>")
        html_parts.append("</div>")

    html_parts.append("</div>")

    st.markdown("".join(html_parts), unsafe_allow_html=True)