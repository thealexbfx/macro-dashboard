import pandas as pd


def build_sparkline_svg(df, positive=True, width=120, height=44):
    if df is None or df.empty or "value" not in df.columns:
        return ""

    spark_df = df.dropna().tail(30).copy()

    if len(spark_df) < 2:
        return ""

    spark_df["date"] = pd.to_datetime(spark_df["date"])
    values = spark_df["value"].astype(float).tolist()

    min_val = min(values)
    max_val = max(values)
    value_range = max_val - min_val if max_val != min_val else 1

    padding_x = 4
    padding_y = 8

    points = []

    for i, row in spark_df.reset_index(drop=True).iterrows():
        x = padding_x + (i / (len(spark_df) - 1)) * (width - padding_x * 2)
        y = padding_y + (
            1 - ((row["value"] - min_val) / value_range)
        ) * (height - padding_y * 2)
        points.append((x, y))

    line_color = "#22c55e" if positive else "#ef4444"

    # Line
    line_path = "M " + " L ".join(
        f"{x:.2f},{y:.2f}" for x, y in points
    )

    # Area
    bottom_y = height - padding_y

    area_path = (
        f"M {points[0][0]:.2f},{bottom_y:.2f} "
        + " L ".join(f"{x:.2f},{y:.2f}" for x, y in points)
        + f" L {points[-1][0]:.2f},{bottom_y:.2f} Z"
    )

    gradient_id = "sparkGreen" if positive else "sparkRed"

    return (
        f'<svg class="sparkline-svg" viewBox="0 0 {width} {height}" preserveAspectRatio="none">'
        f'<defs>'
        f'<linearGradient id="{gradient_id}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{line_color}" stop-opacity="0.35"/>'
        f'<stop offset="100%" stop-color="{line_color}" stop-opacity="0.02"/>'
        f'</linearGradient>'
        f'</defs>'
        f'<path d="{area_path}" fill="url(#{gradient_id})"/>'
        f'<path d="{line_path}" fill="none" stroke="{line_color}" stroke-width="3" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
        f'</svg>'
    )