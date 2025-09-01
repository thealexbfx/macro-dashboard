import plotly.graph_objects as go

# Example yields
maturities = ["2Y", "10Y"]

# Yields 1 month ago
yields_past = [5.0, 5.5]

# Yields now
yields_now = [4.0, 5.0]

# Spread for reference
spread_past = yields_past[1] - yields_past[0]
spread_now = yields_now[1] - yields_now[0]

fig = go.Figure()

# 1 month ago
fig.add_trace(go.Scatter(
    x=maturities, y=yields_past,
    mode='lines+markers',
    name='1 Month Ago',
    line=dict(color='red', width=3)
))

# Now
fig.add_trace(go.Scatter(
    x=maturities, y=yields_now,
    mode='lines+markers',
    name='Now',
    line=dict(color='blue', width=3)
))

# Add annotation for spread
fig.add_annotation(x="10Y", y=yields_now[1],
                   text=f"Spread Now: {spread_now:.2f}%",
                   showarrow=True, arrowhead=2, ax=-50, ay=-40)

fig.add_annotation(x="10Y", y=yields_past[1],
                   text=f"Spread 1M Ago: {spread_past:.2f}%",
                   showarrow=True, arrowhead=2, ax=-50, ay=40)

fig.update_layout(
    title="Bull Steepener Example: 2Y Falls Faster than 10Y",
    xaxis_title="Maturity",
    yaxis_title="Yield (%)",
    yaxis=dict(range=[3.5, 6]),
    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
)

fig.show()
