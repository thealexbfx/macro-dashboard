import streamlit as st
import pandas as pd
import datetime as dt

from components.charts import plot_chart

def render_date_controls(df, timeframe):
    earliest_date = df["date"].min().date()
    latest_date = df["date"].max().date()

    if timeframe != "MAX":
        years = int(timeframe.replace("Y", ""))
        default_start_date = max(
            earliest_date,
            latest_date - dt.timedelta(days=365 * years)
        )
    else:
        default_start_date = earliest_date

    date_col1, date_col2 = st.columns(2)

    with date_col1:
        start_date = st.date_input(
            "Start Date",
            default_start_date,
            min_value=earliest_date,
            max_value=latest_date
        )

    with date_col2:
        end_date = st.date_input(
            "End Date",
            latest_date,
            min_value=earliest_date,
            max_value=latest_date
        )

    if start_date > end_date:
        st.warning("Start date must be before end date.")
        st.stop()

    return start_date, end_date
    
def detect_quarterly_data(df_filtered):
    if len(df_filtered) <= 1:
        return False

    avg_days = (
        df_filtered["date"]
        .diff()
        .dropna()
        .dt.days
        .mean()
    )

    return avg_days >= 80

def filter_by_dates(df, start_date, end_date):
    return df[
        (df["date"] >= pd.to_datetime(start_date)) &
        (df["date"] <= pd.to_datetime(end_date))
    ]
    
def display_market_chart(fig, source_text=None, site_text="macrolensresearch.com"):
    if fig is None:
        return

    if source_text:
        fig.add_annotation(
            text=source_text,
            xref="paper",
            yref="paper",
            x=0,
            y=-0.24,
            showarrow=False,
            xanchor="left",
            font=dict(size=11, color="gray"),
        )

        fig.add_annotation(
            text=site_text,
            xref="paper",
            yref="paper",
            x=0,
            y=-0.30,
            showarrow=False,
            xanchor="left",
            font=dict(size=11, color="gray"),
        )

    fig.update_layout(margin=dict(l=40, r=30, t=70, b=110))

    st.plotly_chart(fig, use_container_width=True)
    
def build_market_chart(df_filtered, title, chart_type, delta_type, quarterly=False):
    delta_type_arg = None if delta_type == "Off" else delta_type.lower()
    hover_style = "delta" if delta_type_arg is not None else "none"

    fig = plot_chart(
        df_filtered,
        title,
        chart_type,
        hover_style=hover_style,
        delta_type=delta_type_arg,
        date_format="quarterly" if quarterly else "daily",
        show_markers=False,
    )

    if quarterly:
        tickvals = df_filtered[df_filtered["date"].dt.quarter == 4]["date"]
        ticktext = (
            df_filtered[df_filtered["date"].dt.quarter == 4]["date"]
            .dt.to_period("Q")
            .apply(lambda x: f"Q{x.quarter} {x.year}")
        )
        fig.update_xaxes(tickmode="array", tickvals=tickvals, ticktext=ticktext)

    fig.update_layout(
        hoverlabel=dict(
            font_size=13,
            font_color="black",
            font_family="Arial",
        )
    )

    return fig